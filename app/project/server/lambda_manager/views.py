'''
Date: 2021-12-14 15:49:16
Company: Luokung Technology Corp.
LastEditors: Will Cheng Yong chengyong@pku.edu.cn
LastEditTime: 2022-10-13 13:53:00
'''
import os
import base64
import json
from enum import Enum

import requests

from models import DimensionType
from logger import logger

settings = {
    "NUCLIO_SCHEME": os.environ['NUCLIO_SCHEME'],
    "NUCLIO_HOST": os.environ['NUCLIO_HOST'],
    "NUCLIO_PORT": os.environ['NUCLIO_PORT'],
    "NUCLIO_PROJECT_NAME": os.environ['NUCLIO_PROJECT_NAME'],
    "NUCLIO_DEFAULT_TIMEOUT": os.environ['NUCLIO_DEFAULT_TIMEOUT'],

    "ANNOSERVER_SCHEME": os.environ['ANNOSERVER_SCHEME'],
    "ANNOSERVER_HOST": os.environ['ANNOSERVER_HOST'],
    "ANNOSERVER_PORT": os.environ['ANNOSERVER_PORT'],
    "ANNOSERVER_DEFAULT_TIMEOUT": os.environ['ANNOSERVER_DEFAULT_TIMEOUT']
}

class DBTask:
    def __init__(self, data):
        self.chunk_size = data.get("chunk_size", 72)
        self.size = data.get("size")
        self.image_quality = data.get("image_quality", 70)
        self.start_frame = data.get("start_frame", 0)
        self.stop_frame = data.get("stop_frame")
        self.data_id = data.get("data_id")
        self.original_chunk_type = data.get("original_chunk_type", "imageset")
        self.compressed_chunk_type = data.get("compressed_chunk_type", "imageset")
        self.original_path = data.get("original_path")
        self.compressed_path = data.get("compressed_path")
        self.labels = data.get("labels")
        self.pcd_list = data.get("pcd_list", [])
        self.dim = data.get("dim", DimensionType.DIM_2D)
        logger.debug("Init DB task completed!")

    def get_original_chunk_path(self, id):
        if self.dim == DimensionType.DIM_3D:
            return self.pcd_list[id]
        return os.path.join(self.compressed_path, str(id) + ".mp4")
    def get_compressed_chunk_path(self, id):
        if self.dim == DimensionType.DIM_3D:
            return self.pcd_list[id]
        return os.path.join(self.compressed_path, str(id) + ".zip")

class AnnoGateway:

    def __init__(self, scheme=None, host=None, port=None):
        self.scheme = scheme
        self.host = host
        self.port = port

    def _http(self, method="get", scheme=None, host=None, port=None,
        url=None, headers=None, data=None):
        ANNO_GATEWAY = '{scheme}://{host}:{port}'.format(
            scheme=self.scheme or settings["ANNOSERVER_SCHEME"],
            host=self.host or settings['ANNOSERVER_HOST'],
            port=self.port or settings['ANNOSERVER_PORT']
        )

        ANNOSERVER_TIMEOUT = int(settings['ANNOSERVER_DEFAULT_TIMEOUT']) or 60
        if url:
            url = "{}{}".format(ANNO_GATEWAY, url)
        else:
            url = ANNO_GATEWAY
        reply = getattr(requests, method)(url, timeout=ANNOSERVER_TIMEOUT, json=data)
        reply.raise_for_status()
        response = reply.json()
        return response

    def _mapping_labels(self, labels):
        label_mapping = {}
        for label in labels:
            # label_mapping[label["name"]] = label["id"]
            #change to cn_name
            cn_name = label.get('cn_name')
            label_mapping[cn_name] = label["id"]
        return label_mapping

    def save(self, task_id, payload: list):
        url = "/auto/{}/save".format(task_id)
        return self._http(method="post", url=url, data=payload)

    def delete(self, task_id):
        url = "/auto/{}/delete".format(task_id)
        return self._http(method="delete", url=url)

    def delete_models_annos(self, task_id, model_names: list):
        url = "/auto/{}/deleteModelsData".format(task_id)
        return self._http(method="delete", url=url, data=model_names)

    def get(self, task_id):
        response = self._http(url="/auto/{}/data".format(task_id))
        code = response.get("code")
        message = response.get("msg")
        data = response.get("data")
        original_chunk_type = data.get("data_original_chunk_type")
        if original_chunk_type in ["IMAGE"]:
            original_chunk_type = "imageset"
        elif original_chunk_type == "VIDEO":
            original_chunk_type = "video"

        compressed_chunk_type = data.get("data_compressed_chunk_type")
        if compressed_chunk_type in ["IMAGE", "VIDEO"]:
            compressed_chunk_type = "imageset"

        path = data.get("path")
        original_path = os.path.join(path, "compressed")
        compressed_path = os.path.join(path, "compressed") # original path is the same as compressed path for now
        pcd_files = data.get("pcd_list", [])
        dim = DimensionType.DIM_2D
        if original_chunk_type in ["THREE", "chunk"] or compressed_chunk_type in ["THREE", "chunk"]:
            original_path = path
            compressed_path = path
            pcd_files = sorted(pcd_files, key=lambda d: d['frame'])
            pcd_files = [os.path.join(path, pcd_file['path']) for pcd_file in pcd_files]
            dim = DimensionType.DIM_3D
        db_task_data = {
            "chunk_size": data.get("chunk_size", 72),
            "size": data.get("size"),
            "original_chunk_type": original_chunk_type,
            "compressed_chunk_type": compressed_chunk_type,
            "start_frame": 0,
            "stop_frame": data.get("size") - 1,
            "original_path": original_path,
            "compressed_path": compressed_path,
            "labels": self._mapping_labels(data.get("labels")),
            "pcd_list": pcd_files,
            "dim": dim,
        }
        return db_task_data, code, message

    def get_calib(self, task_id, number):
        response = self._http(url="/data/{}/find2DCameraParamDatas?number={}".format(task_id, number))
        code = response.get("code")
        message = response.get("msg")
        data = response.get("data")
        if not data or code != 200:
            return False, {}
        return True, data


class LambdaType(Enum):
    DETECTOR = "detector"
    INTERACTOR = "interactor"
    REID = "reid"
    TRACKER = "tracker"
    UNKNOWN = "unknown"

    def __str__(self):
        return self.value

class LambdaGateway:
    NUCLIO_ROOT_URL = '/api/functions'

    def _http(self, method="get", scheme=None, host=None, port=None,
        url=None, headers=None, data=None):

        NUCLIO_GATEWAY = '{}://{}:{}'.format(
            scheme or settings["NUCLIO_SCHEME"],
            host or settings['NUCLIO_HOST'],
            port or settings['NUCLIO_PORT'])
        extra_headers = {
            'x-nuclio-project-name': settings["NUCLIO_PROJECT_NAME"] or 'lkdi',
            'x-nuclio-function-namespace': 'nuclio',
        }
        if headers:
            extra_headers.update(headers)
        NUCLIO_TIMEOUT = int(settings['NUCLIO_DEFAULT_TIMEOUT']) or 30

        if url:
            url = "{}{}".format(NUCLIO_GATEWAY, url)
        else:
            url = NUCLIO_GATEWAY

        reply = getattr(requests, method)(url, headers=extra_headers,
            timeout=NUCLIO_TIMEOUT, json=data)
        reply.raise_for_status()
        response = reply.json()
        return response

    def list(self):
        data = self._http(url=self.NUCLIO_ROOT_URL)
        response = [LambdaFunction(self, item) for item in data.values()]
        return response
        return data

    def get(self, func_id):
        data = self._http(url=self.NUCLIO_ROOT_URL + '/' + func_id)
        response = LambdaFunction(self, data)
        return response

    def invoke(self, func, payload):
        # NOTE: it is overhead to invoke a function using nuclio
        # dashboard REST API. Better to call host.docker.internal:<port>
        # Look at https://github.com/docker/for-linux/issues/264.
        # host.docker.internal isn't supported by docker on Linux.
        # There are many workarounds but let's try to use the
        # simple solution.
        return self._http(method="post", url='/api/function_invocations',
            data=payload, headers={
                'x-nuclio-function-name': func,
                'x-nuclio-path': '/'
            })

class LambdaFunction:
    def __init__(self, gateway, data):
        # ID of the function (e.g. omz.public.yolo-v3)
        self.id = data['metadata']['name']
        # type of the function (e.g. detector, interactor)
        meta_anno = data['metadata']['annotations']
        kind = meta_anno.get('type')
        try:
            self.kind = LambdaType(kind)
        except ValueError:
            self.kind = LambdaType.UNKNOWN
        # dictionary of labels for the function (e.g. car, person)
        spec = json.loads(meta_anno.get('spec') or '[]')
        labels = [item['name'] for item in spec]
        if len(labels) != len(set(labels)):
            return (
                "`{}` lambda function has non-unique labels".format(self.id),
                404)
        self.labels = labels
        # state of the function
        self.state = data['status']['state']
        # description of the function
        self.description = data['spec']['description']
        # http port to access the serverless function
        self.port = data["status"].get("httpPort")
        # framework which is used for the function (e.g. tensorflow, openvino)
        self.framework = meta_anno.get('framework')
        # display name for the function
        self.name = meta_anno.get('name', self.id)
        # display supported shapes for the function
        self.shape = json.loads(meta_anno.get('shape', []))
        self.dimension = meta_anno.get('dimension', '2d')
        self.min_pos_points = int(meta_anno.get('min_pos_points', 1))
        self.min_neg_points = int(meta_anno.get('min_neg_points', -1))
        self.startswith_box = bool(meta_anno.get('startswith_box', False))
        self.animated_gif = meta_anno.get('animated_gif', '')
        self.help_message = meta_anno.get('help_message', '')
        self.gateway = gateway

    def to_dict(self):
        response = {
            'id': self.id,
            'kind': str(self.kind),
            'labels': self.labels,
            'description': self.description,
            'framework': self.framework,
            'name': self.name,
            'shape': self.shape,
            'dimension': self.dimension,
        }

        if self.kind is LambdaType.INTERACTOR:
            response.update({
                'min_pos_points': self.min_pos_points,
                'min_neg_points': self.min_neg_points,
                'startswith_box': self.startswith_box,
                'help_message': self.help_message,
                'animated_gif': self.animated_gif
            })

        if self.kind is LambdaType.TRACKER:
            response.update({
                'state': self.state
            })

        return response

    def invoke(self, db_task, data):
        try:
            payload = {}
            threshold = data.get("threshold")
            if threshold:
                payload.update({
                    "threshold": threshold,
                })
            quality = data.get("quality")
            mapping = data.get("mapping")

            if self.kind == LambdaType.DETECTOR:
                payload.update({
                    "image": self._get_image(db_task, data["frame"], quality)
                })
            elif self.kind == LambdaType.INTERACTOR:
                payload.update({
                    "image": self._get_image(db_task, data["frame"], quality),
                    "pos_points": data["pos_points"][2:] if self.startswith_box else data["pos_points"],
                    "neg_points": data["neg_points"],
                    "obj_bbox": data["pos_points"][0:2] if self.startswith_box else None
                })
            elif self.kind == LambdaType.REID:
                payload.update({
                    "image0": self._get_image(db_task, data["frame0"], quality),
                    "image1": self._get_image(db_task, data["frame1"], quality),
                    "boxes0": data["boxes0"],
                    "boxes1": data["boxes1"]
                })
                max_distance = data.get("max_distance")
                if max_distance:
                    payload.update({
                        "max_distance": max_distance
                    })
            elif self.kind == LambdaType.TRACKER:
                payload.update({
                    "image": self._get_image(db_task, data["frame"], quality),
                    "shapes": data.get("shapes", []),
                    "states": data.get("states", [])
                })
            else:
                return (
                    '`{}` lambda function has incorrect type: {}'
                    .format(self.id, self.kind),
                    500)
        except KeyError as err:
            return (
                "`{}` lambda function was called without mandatory argument: {}"
                .format(self.id, str(err)),
                400)

        response = self.gateway.invoke(self, payload)
        if self.kind == LambdaType.DETECTOR:
            if mapping:
                for item in response:
                    item["label"] = mapping.get(item["label"])
                response = [item for item in response if item["label"]]

        return response

    def _get_image(self, db_task, frame, quality):
        # if quality is None or quality == "original":
        #     quality = FrameProvider.Quality.ORIGINAL
        # elif  quality == "compressed":
        #     quality = FrameProvider.Quality.COMPRESSED
        # else:
        #     raise ValidationError(
        #         '`{}` lambda function was run '.format(self.id) +
        #         'with wrong arguments (quality={})'.format(quality),
        #         code=status.HTTP_400_BAD_REQUEST)

        # frame_provider = FrameProvider(db_task.data)
        # image = frame_provider.get_frame(frame, quality=quality)

        # return base64.b64encode(image[0].getvalue()).decode('utf-8')
        return None
