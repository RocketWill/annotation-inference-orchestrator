'''
Author: Will Cheng Yong chengyong@pku.edu.cn
Date: 2022-10-11 15:41:04
LastEditors: Will Cheng Yong chengyong@pku.edu.cn
LastEditTime: 2022-10-11 15:41:46
FilePath: /lkdi-auto-annotation/server/flask-celery/project/server/lambda_manager/tools/projection/utils.py
Description:

Copyright (c) 2022 by Will Cheng Yong chengyong@pku.edu.cn, All Rights Reserved.
'''
from typing import Any, List

import numpy as np

from interfaces import Box2D, Box3D, Vector3, Calib


def get_box3d(points: List[float]) -> Box3D:
    """
    points: [position, rotation, scale]
    """
    return Box3D(
        position=Vector3(*points[:3]),
        rotation=Vector3(*points[3:6]),
        scale=Vector3(*points[6:9]),
    )

def get_calib(data: any) -> Calib:
    intrinsic = np.asarray(data['internal'])[:, :3].reshape(1, -1)[0].tolist()
    rm = np.asarray(data['r'])
    t = np.asarray(data['t'])
    extrinsic = np.append(rm, t.reshape(1, -1).T, axis=1)\
        .reshape(1, -1)[0].tolist() + [0, 0, 0, 1]

    return Calib(extrinsic=extrinsic, intrinsic=intrinsic)
