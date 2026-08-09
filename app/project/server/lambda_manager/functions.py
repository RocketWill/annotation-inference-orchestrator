'''
Date: 2021-12-15 10:18:21
Company: Luokung Technology Corp.
LastEditors: Will Cheng Yong chengyong@pku.edu.cn
LastEditTime: 2022-10-11 15:51:47
'''
import time
import json
import base64
from datetime import datetime
import traceback

from flask import render_template, Blueprint, jsonify, request
from flask_cors import cross_origin

from project.server import celery as CELERY
from tasks import lambda_function
from views import LambdaGateway, AnnoGateway, DBTask
from frame_provider import FrameProvider
from logger import logger
import time
from utils import get_image

lambda_blueprint = Blueprint("lambda", __name__,)

def fetch_jobs():
    i = CELERY.control.inspect()
    reserved = [item for sublist in i.reserved().values() for item in sublist]
    active = [item for sublist in i.active().values() for item in sublist]
    reserved.extend(active)
    return reserved

def validate_task(task_id):
    jobs = fetch_jobs()
    for job in jobs:
        task = job['args'][2]['function']['task']
        if task_id == task:
            return False
    return True

@cross_origin
@lambda_blueprint.route("/delete/<task_id>", methods=["DELETE"])
def delete_auto_annos(task_id):
    anno_gateway = AnnoGateway()
    response = {"code": 200, "message": "删除任务自动化标注 {} 成功".format(task_id), "result": None}
    if request.method == "DELETE":
        try:
            resp = anno_gateway.delete(task_id)
            if resp["code"] != 200: raise
        except:
            response.update({"code": 500, "message": "删除任务自动化标注 {} 失败".format(task_id)})
            logger.error("DELETE /delete/{} error fail.".format(task_id))
        return jsonify(response), response["code"]

@cross_origin
@lambda_blueprint.route("/functions", methods=["GET"])
def list_functions():
    response = {"code": 200, "message": "ok", "result": []}
    try:
        gateway = LambdaGateway()
        nuclio_response = gateway.list()
        response.update({"result": [nr.to_dict() for nr in nuclio_response]})
    except Exception as e:
        logger.error("GET /functions error: {}".format(traceback.format_exc()))
        response.update({"code": 500, "message": "Could not fetch models.", "result": []})
    return jsonify(response), response["code"]

@cross_origin
@lambda_blueprint.route("/functions/<func_id>", methods=["GET", "POST"])
def function(func_id):
    gateway = LambdaGateway()
    anno_gateway = AnnoGateway()
    response = {"code": 200, "message": "ok", "result": []}
    if request.method == "GET":
        try:
            nuclio_response = gateway.get(func_id)
            response.update({"result": nuclio_response.to_dict()})
        except:
            logger.error("GET /functions/{0} error: {1}".format(func_id, traceback.format_exc()))
            response.update({"code": 500, "message": "Could not fetch function [{}].".format(func_id), "result": None})
        return jsonify(response), response["code"]

    elif request.method == "POST":
        payload = {}
        body = json.loads(request.data.decode('utf-8'))
        cleanup = body.get("cleanup", False)
        task_id = body.get("task")
        frame_id = body.get("frame")
        mapping = body.get("mapping")
        threshold = body.get("threshold", 0.6)
        if not task_id or frame_id is None or not mapping:
            response = {"code": 412, "message": "Could not find task or frame."}
            return jsonify(response), 412
        try:
            db_task_data, code, message = anno_gateway.get(task_id)
            # could not get task details
            if code == 500:
                response = {"code": 500, "message": "Could not get task {} information.".format(task_id)}
                return jsonify(response), 500
            db_task = DBTask(db_task_data)
            quality = "original" if db_task.original_chunk_type == "video" else "compressed"
            frame_provider = FrameProvider(db_task)
            payload.update({
                "image": get_image(frame_provider, frame_id, quality),
                "threshold": threshold
            })
            nuclio_response = gateway.invoke(func_id, payload)
            results = []
            for res in nuclio_response['result']:
                label = res["label"]
                if not mapping.get(label):
                    continue
                if label in mapping:
                    results.append({
                        "confidence": res["confidence"],
                        "label": mapping[label],
                        "points": res["points"],
                        "type": res["type"]
                    })
            response.update({"result": results})
            return jsonify(response), 200
        except Exception as e:
            logger.error("POST /functions/{0} error: {1}".format(func_id, traceback.format_exc()))
            response = {"code": 500, "message": str(e)}
            return jsonify(response), 500

@cross_origin
@lambda_blueprint.route("/requests", methods=["GET", "POST"])
def requests():
    response = {"code": 200, "message": "ok", "result": []}
    if request.method == "GET":
        task_status_results = []
        try:
            task_ids = [job["id"] for job in fetch_jobs()]
            for task_id in task_ids:
                task_result = CELERY.AsyncResult(task_id)
                result = task_result.result
                if result:
                    result["id"] = task_id
                else:
                    result = {'ended': None, 'enqueued': None, 'exec_info': None, 'function': {'id': None, 'task': None, 'threshold': 0.5}, 'id': task_id, 'progress': 50, 'started': None, 'status': "PROGRESS"}
                result["status"] = task_result.status if task_result.status else "PROGRESS"
                task_status_results.append(result)
            response.update({"result": task_status_results})
        except Exception as e:
            logger.error("GET /requests error: {}".format(traceback.format_exc()))
            response.update({"code": 200, "message": "Fetch tasks status fail."})
        return jsonify(response), response["code"]

    elif request.method == "POST":
        anno_gateway = AnnoGateway()
        response = {"code": 202, "message": "ok", "result": {}}
        body = json.loads(request.data.decode('utf-8'))
        cleanup = body.get("cleanup", False)
        function = body.get("function")
        task_id = body.get("task")
        mapping = body.get("mapping")  # {'car (小汽车)': '车车', 'motorcycle (摩托车)': '车车'}
        threshold = body.get("threshold", 0.6)

        if not task_id or not function or not mapping:
            message = "Could not find task, function or mapping."
            logger.error("POST /requests error: {}".format(message))
            response.update({"code": 412, "message": message})
            return jsonify(response), 412

        if not validate_task(task_id):
            message = "Task {} already in queue.".format(task_id)
            logger.error("POST /requests error: {}".format(message))
            response.update({"code": 412, "message": message, "result": None})
            return jsonify(response), 412

        if cleanup:
            try:
                resp = anno_gateway.delete(task_id)
                if resp["code"] != 200: raise
            except:
                response.update({"code": 500, "message": "Could not clean previous annotations.", "result": None})
                return jsonify(response), 500

        db_task_data, code, message = anno_gateway.get(task_id)
        if code == 500: # could not get task details
            message = "Could not get task {} information.".format(task_id)
            logger.error("POST /requests error: {}".format(message))
            response = {"code": 500, "message": message, "result": None}
            return jsonify(response), 500

        info = {
            "ended": None,
            "enqueued": datetime.now(),
            "exec_info": None,
            "function": {
                "id": function,
                "task": task_id,
                "threshold": threshold
            },
            "id": None,
            "progress": 0,
            "started": None,
            "status": None
        }

        try:
            logger.error(lambda_function)
            task = lambda_function.delay(function, db_task_data, info, mapping)
            logger.error(task)
            info.update({"id": task.id})
            response.update({"result": info})
        except Exception as e:
            logger.error("POST /requests error: {}".format(traceback.format_exc()))
            response.update({"code": 500, "message": "Could not process auto annotation on Task {}".format(task_id), "result": None})
        return jsonify(response), response["code"]

@cross_origin
@lambda_blueprint.route("/requests/<task_id>", methods=["GET", "DELETE"])
def task_status(task_id):
    response = {"code": 200, "message": "ok", "result": {}}
    if request.method == "GET":
        try:
            task_result = CELERY.AsyncResult(task_id)
            result = task_result.result
            result["id"] = task_id
            result["status"] = task_result.status
            response.update({"result": result})
        except Exception as e:
            logger.error(traceback.format_exc())
            info = {'ended': None, 'enqueued': None, 'exec_info': None, 'function': {'id': None, 'task': None, 'threshold': 0.5}, 'id': task_id, 'progress': 50, 'started': None, 'status': "PROGRESS"}
            response.update({"code": 200, "message": "Could not get status of Task {}".format(task_id), "result": info})
        return jsonify(response), response["code"]
    elif request.method == "DELETE":
        anno_gateway = AnnoGateway()
        response.update({"result": None})
        try:
            task_result = CELERY.AsyncResult(task_id)
            result = task_result.result
            lkdi_task_id = result["function"]['task']
            task_result.revoke(terminate=True, signal='SIGUSR1')

            result["id"] = task_id
            result["status"] = "SUCCESS"
            response.update({"message": "Cancel task {} successfully.".format(task_id), "result": result})
            # delete annos in lkdi task
            # delete_resp = anno_gateway.delete(lkdi_task_id)
            # logger.error(delete_resp)
            # if delete_resp["code"] != 200: raise ValueError("Delete fail.")

        except Exception as e:
            logger.error(e)
            response.update({"message": "Could not cancel task {}.".format(task_id)})
        return jsonify(response), response["code"]