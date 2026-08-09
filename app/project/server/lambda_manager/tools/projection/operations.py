'''
Author: Will Cheng Yong chengyong@pku.edu.cn
Date: 2022-10-11 15:41:04
LastEditors: Will Cheng Yong chengyong@pku.edu.cn
LastEditTime: 2022-10-11 15:41:40
FilePath: /lkdi-auto-annotation/server/flask-celery/project/server/lambda_manager/tools/projection/operations.py
Description:

Copyright (c) 2022 by Will Cheng Yong chengyong@pku.edu.cn, All Rights Reserved.
'''
import math
from typing import Union, List

import numpy as np

from interfaces import Vector3, Calib, Box3D


Num = Union[int, float]

import math
from typing import Union, List

from interfaces import Vector3, Calib, Box3D


Num = Union[int, float]

def mat(matrix: List[Num], s: int, x: int, y: int) -> Num:
    return matrix[x * s + y]

def vector4_to_3(vector: List[Num]) -> List[Num]:
    ret = []
    for i in range(len(vector)):
        if (i + 1) % 4 != 0:
            ret.append(vector[i])

    return ret

def vector3_normalize(vector: List[Num]) -> List[Num]:
    ret = []
    for i in range(len(vector) // 3):
        ret.append(vector[i * 3 + 0] / vector[i * 3 + 2])
        ret.append(vector[i * 3 + 1] / vector[i * 3 + 2])

    return ret;

def matmul_t(matrix1: List[Num], matrix2: List[Num], vector_length: int) -> List[Num]:
    ret = [0] * (len(matrix1) // vector_length) * (len(matrix2) // vector_length)
    result_length = len(matrix1) // vector_length
    for vi in range(len(matrix2) // vector_length):
        for r in range(len(matrix1) // vector_length):
            for i in range(vector_length):
                ret[vi * result_length + r] += \
                    matrix1[r * vector_length + i] * matrix2[vi * vector_length + i]

    return ret

def matmul(matrix1: List[Num], matrix2: List[Num], vector_length: int) -> List[Num]:
    rows = len(matrix1) // vector_length
    cols = len(matrix2) // vector_length
    ret = [0] * rows * cols
    for row in range(rows):
        for col in range(cols):
            for i in range(vector_length):
                ret[row * cols + col] += \
                    matrix1[row * vector_length + i] * matrix2[i * cols + col]

    return ret

def euler_angle_to_rotate_matrix(euler: Vector3, trans: Vector3, order: str = 'ZYX') -> List[Num]:
    theta = [euler.x, euler.y, euler.z]
    R_x = [
        1, 0, 0,
        0, math.cos(theta[0]), -math.sin(theta[0]),
        0, math.sin(theta[0]), math.cos(theta[0]),
    ]
    R_y = [
        math.cos(theta[1]), 0, math.sin(theta[1]),
        0, 1, 0,
        -math.sin(theta[1]), 0, math.cos(theta[1])
    ]
    R_z = [
        math.cos(theta[2]), -math.sin(theta[2]), 0,
        math.sin(theta[2]), math.cos(theta[2]), 0,
        0, 0, 1
    ]
    matrices = {
        'Z': R_z,
        'Y': R_y,
        'X': R_x,
    }
    R = matmul(matrices[order[2]], matmul(matrices[order[1]], matrices[order[0]], 3), 3)

    return [
        mat(R, 3, 0, 0), mat(R, 3, 0, 1), mat(R, 3, 0, 2), trans.x,
        mat(R, 3, 1, 0), mat(R, 3, 1, 1), mat(R, 3, 1, 2), trans.y,
        mat(R, 3, 2, 0), mat(R, 3, 2, 1), mat(R, 3, 2, 2), trans.z,
        0, 0, 0, 1,
    ]

def box_to_corner(box: Box3D) -> List[Num]:
    """
            6 -------- 7
           /|         /|
          2 -------- 3 .
          | |        | |
          . 5 -------- 4
          |/         |/
          1 -------- 0
          Front Face: 0,1,2,3
          Back Face:  4,5,6,7
    """
    trans_matrix = euler_angle_to_rotate_matrix(box.rotation, box.position)
    xc = box.scale.x / 2
    yc = box.scale.y / 2
    zc = box.scale.z / 2

    local_coord = [
        xc, yc, -zc, 1, xc, -yc, -zc, 1,   # front-left-bottom, front-right-bottom
        xc, -yc, zc, 1, xc, yc, zc, 1,     # front-right-top,   front-left-top

        -xc, yc, -zc, 1, -xc, -yc, -zc, 1, # rear-left-bottom,  rear-right-bottom
        -xc, -yc, zc, 1, -xc, yc, zc, 1,   # rear-right-top,    rear-left-top
    ]
    world_coord = matmul_t(trans_matrix, local_coord, 4)

    return world_coord

def points3d_homo_to_camera(points3d: List[Num], calib: Calib) -> List[Num]:
    camera_position_homo = matmul_t(calib.extrinsic, points3d, 4)

    return camera_position_homo

def corner_to_box(points3d: List[Num]):
    ROW = 4
    assert len(points3d) == 8 * ROW, 'Cuboid corner: Invalid length of points.'
    position = Vector3(x = 0, y = 0, z = 0)
    scale = Vector3(x = 0, y = 0, z = 0)
    rotation = Vector3(x = 0, y = 0, z = 0)

    for i in range(8):
        position.x += points3d[i * ROW]
        position.y += points3d[i * ROW + 1]
        position.z += points3d[i * ROW + 2]
    position.x /= 8
    position.y /= 8
    position.z /= 8

    scale.x = math.sqrt((points3d[0] - points3d[ROW]) * (points3d[0] - points3d[ROW]) + \
        (points3d[1] - points3d[ROW + 1]) * (points3d[1] - points3d[ROW + 1]) + \
        (points3d[2] - points3d[ROW + 2]) * (points3d[2] - points3d[ROW + 2]))
    scale.y = math.sqrt((points3d[0] - points3d[ROW * 3]) * (points3d[0] - points3d[ROW * 3]) + \
        (points3d[1] - points3d[ROW * 3 + 1]) * (points3d[1] - points3d[ROW * 3 + 1]) + \
        (points3d[2] - points3d[ROW * 3 + 2]) * (points3d[2] - points3d[ROW * 3 + 2])    )
    scale.z = math.sqrt((points3d[0] - points3d[ROW * 4]) * (points3d[0] - points3d[ROW * 4]) + \
        (points3d[1] - points3d[ROW * 4 + 1]) * (points3d[1] - points3d[ROW * 4 + 1]) + \
        (points3d[2] - points3d[ROW * 4 + 2]) * (points3d[2] - points3d[ROW * 4 + 2]))

    rotation.y = math.atan2(points3d[2] - points3d[ROW * 4 + 2],
                            points3d[0] - points3d[ROW * 4]) # atan2(z, x)
    rotation.x = math.atan2(points3d[2] - points3d[ROW * 3 + 2],
                            points3d[1] - points3d[ROW * 3 + 1])
    rotation.z = math.atan2(points3d[1 * ROW + 1] - points3d[ROW * 5 + 1],
                            points3d[1 * ROW] - points3d[ROW * 5])
    return Box3D(position=position, scale=scale, rotation=rotation)

def points_cam_to_image(pointsCam: List[Num], calib: Calib) -> List[Num]:
    points_cam_vec3 = vector4_to_3(pointsCam)
    points_img = matmul_t(calib.intrinsic, points_cam_vec3, 3)
    points_img_norm = vector3_normalize(points_img)

    return points_img_norm

def lidar_box_to_cam_box(box: Box3D, calib: Calib) -> Box3D:
    box_corner_lidar = box_to_corner(box)
    box_corner_cam = points3d_homo_to_camera(box_corner_lidar, calib)
    box_cam = corner_to_box(box_corner_cam)

    return box_cam

def point_in_rect(bl, tr, p) :
   if (p[0] > bl[0] and p[0] < tr[0] and p[1] > bl[1] and p[1] < tr[1]) :
      return True
   else :
      return False

def lider_box_to_image(box: Box3D, calib: Calib, size) -> List[Num]:
    box_corner_lidar = box_to_corner(box)
    box_corner_cam = points3d_homo_to_camera(box_corner_lidar, calib)
    points_img_norm = points_cam_to_image(box_corner_cam, calib)

    def get_rect(points):
        points = np.asarray(points).reshape(-1, 2)
        minx, maxx = np.amin(points[:, 0]), np.amax(points[:, 0])
        miny, maxy = np.amin(points[:, 1]), np.amax(points[:, 1])
        return [minx, miny, maxx, maxy]

    for i in range(len(points_img_norm) // 2):
        ptx = points_img_norm[i * 2]
        pty = points_img_norm[i * 2 + 1]
        if point_in_rect((0,0), (size), (ptx, pty)):
            return points_img_norm, get_rect(points_img_norm)
    return [], []
