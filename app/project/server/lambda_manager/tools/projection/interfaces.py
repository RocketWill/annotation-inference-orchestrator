'''
Author: Will Cheng Yong chengyong@pku.edu.cn
Date: 2022-10-11 15:41:04
LastEditors: Will Cheng Yong chengyong@pku.edu.cn
LastEditTime: 2022-10-11 15:41:30
FilePath: /lkdi-auto-annotation/server/flask-celery/project/server/lambda_manager/tools/projection/interfaces.py
Description:

Copyright (c) 2022 by Will Cheng Yong chengyong@pku.edu.cn, All Rights Reserved.
'''
from dataclasses import dataclass
from typing import List

@dataclass
class Vector3:
    x: float
    y: float
    z: float

@dataclass
class Calib:
    extrinsic: List[float]
    intrinsic: List[float]

@dataclass
class Box2D:
    x: float
    y: float
    width: float
    height: float

@dataclass
class Box3D:
    position: Vector3
    scale: Vector3
    rotation: Vector3
