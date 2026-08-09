'''
Date: 2022-01-05 20:09:15
Company: Luokung Technology Corp.
LastEditors: error: git config user.name && git config user.email & please set dead value or install git
LastEditTime: 2022-10-12 02:36:42
'''
import math
from datetime import datetime
import uuid
import traceback
from typing import List

from project.server import celery
from project.server.lambda_manager.views import LambdaGateway, AnnoGateway, DBTask
from frame_provider import FrameProvider
from models import DimensionType
from tools.projection.utils import get_box3d, get_calib
from tools.projection.operations import lider_box_to_image
from logger import logger
from utils import get_image

class Results:
    def __init__(self, task_id, mapping: dict, labels: dict, func_id: str, dim: DimensionType.DIM_2D):
        self.results = []
        self.task_id = task_id
        self.mapping = mapping
        self.labels = labels
        self.gateway = AnnoGateway()
        self.func_id = func_id
        self.dim = dim
        self.client_id = 0

    def _create_projections(self, frame: int, points: List[float]):
        """
        points: [position, rotation, scale]
        """
        if self.dim == DimensionType.DIM_3D:
            status, camera_params = self.gateway.get_calib(self.task_id, frame)
            if not status: return
            projections = []
            for file_name, calib_data in camera_params.items():
                width, height = calib_data['width'], calib_data['height']
                context_index = calib_data['order']
                calib = get_calib(calib_data)
                box3d = get_box3d(points)
                cuboid, rect = lider_box_to_image(box3d, calib, size=[height, width])
                if len(cuboid) == 0:
                    continue
                for anno_type, pro_pts in {"cuboid": cuboid, "rectangle": rect}.items():
                    projections.append({
                        "frame": frame,
                        "type": anno_type,
                        "occluded": False,
                        "points": ",".join([str(pt) for pt in pro_pts]),
                        "z_order": 0,
                        "group": 0,
                        "attributes": [],
                        "source": "auto",
                        "id": str(uuid.uuid1()),
                        "amountPoints": -1,
                        "rotation": 0,
                        "contextIndex": context_index,
                        "modified2d": False,
                    })

            return projections

    def _save_annos(self, frame: int, annotations: list):
        for _, anno in enumerate(annotations):
            self.client_id += 1
            label_name = anno.get("label")
            task_label_name = self.mapping.get(label_name)
            if not task_label_name:
                continue
            label_id = self.labels.get(task_label_name)
            if not label_id:
                continue

            points = anno["points"]
            if self.dim == DimensionType.DIM_3D:
                # xyzwhlr -> [position, rotation, scale]
                points = anno["points"][:3] + [0, 0, anno["points"][6]] + anno["points"][3:6] + ([0] * 7)
                projections = self._create_projections(frame, points)
                for projection in projections:
                    projection.update({
                        "clientProjID": self.client_id,
                        "modelId": self.func_id,
                        "label_id": label_id,
                    })
                self.results += projections

            self.results.append(
                {
                    "frame": frame,
                    "label_id": label_id,
                    "type": anno["type"],
                    "occluded": False,
                    "points": ",".join([str(pt) for pt in points]),
                    "z_order": 0,
                    "group": 0,
                    "attributes": [],
                    "source": "auto",
                    "id": str(uuid.uuid1()),
                    "modelId": self.func_id,

                    "amountPoints": anno.get("amount_points", None),
                    "rotation": 0,
                    "clientProjID": self.client_id,
                    "contextIndex": -1,
                    "modified2d": False,
                }
            )
        if (frame + 1) % 30 == 0:
            save_status = self.submit()

    def submit(self):
        if len(self.results) < 1:
            return
        # import json
        # import time
        # with open("{}.json".format(time.time()), "w") as o:
        #     json.dump(self.results, o, indent=4)
        # self.results = []
        # return True
        response = self.gateway.save(self.task_id, self.results)
        if response["code"] != 200:
            print("Save frames results fail.")
            self.results = []
            return False
        else:
            print("Save frames results successfully.")
            self.results = []
            return True

    def append_annos(self, frame: int, annotations: list):
        self._save_annos(frame, annotations)

@celery.task(name="lambda")
def lambda_function(func_id, db_data, info, mapping):
    try:
        db_task = DBTask(db_data)
        info.update({"started": datetime.now()})
        lambda_function.update_state(state="STARTED", meta=info)

        gateway = LambdaGateway()
        anno_gateway = AnnoGateway()
        payload = {"threshold": 0.5}
        info["started"] = datetime.now()
        info["function"]["threshold"] = payload["threshold"]
        quality = "original" if db_task.original_chunk_type == "video" else "compressed"

        results = Results(info["function"]["task"], mapping, db_task.labels, func_id, dim=db_task.dim)
        frame_provider = FrameProvider(db_task)
        for frame_idx in range(db_task.size):
            if (frame_idx+1) % 1 == 0:
                print("{} / {}".format(frame_idx+1, db_task.size))
            try:
                image_string = get_image(frame_provider, frame_idx, quality)
            except Exception as e:
                # skip error image
                logger.error("Task: {0}, get image index {1} error.".format(info["function"]["task"], frame_idx))
                continue
            payload.update({
                "image": image_string
            })
            # image = frame_provider.get_frame(frame_idx, quality=FrameProvider.Quality.COMPRESSED, out_type=FrameProvider.Type.NUMPY_ARRAY)
            # import cv2
            # cv2.imwrite("{}.jpg".format(frame_idx), image[0])
            response = gateway.invoke(func_id, payload)
            results.append_annos(frame_idx, response["result"])
            info.update({"progress": math.ceil((frame_idx+1)/db_task.size*100)})
            lambda_function.update_state(state="PROGRESS", meta=info)
        # flush remain results
        save_status = results.submit()
        info.update({"ended": datetime.now(), "progress": 100})
        lambda_function.update_state(state="SUCCESS", meta=info)
    except Exception as e:
        logger.error("Task: {0}, {1}".format(info["function"]["task"], traceback.format_exc()))
        lambda_function.update_state(state="FAILURE", meta=info)
        try:
            resp = anno_gateway.delete_models_annos(info["function"]["task"], [func_id]) # delete auto annos by this func_id
            if resp["code"] == 200:
                info.update({"ended": datetime.now(), "exec_info": "删除标注成功"})
            else:
                info.update({"ended": datetime.now(), "exec_info": "删除标注失败"})
        except:
            info.update({"ended": datetime.now(), "exec_info": "删除标注失败"})

    return info