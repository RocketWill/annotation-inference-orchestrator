'''
Date: 2021-12-16 14:00:23
Company: Luokung Technology Corp.
LastEditors: error: git config user.name && git config user.email & please set dead value or install git
LastEditTime: 2022-10-12 02:30:31
'''
import base64

import open3d as o3d
import numpy as np
import cv2

from models import DimensionType

def rotate_image(image, angle):
    height, width = image.shape[:2]
    image_center = (width/2, height/2)
    matrix = cv2.getRotationMatrix2D(image_center, angle, 1.)
    abs_cos = abs(matrix[0,0])
    abs_sin = abs(matrix[0,1])
    bound_w = int(height * abs_sin + width * abs_cos)
    bound_h = int(height * abs_cos + width * abs_sin)
    matrix[0, 2] += bound_w/2 - image_center[0]
    matrix[1, 2] += bound_h/2 - image_center[1]
    matrix = cv2.warpAffine(image, matrix, (bound_w, bound_h))
    return matrix

def get_image(frame_provider, frame, quality):
    """_summary_
    get image or point data, convert to base64 string
    """
    if quality is None or quality == "original":
        quality = frame_provider.Quality.ORIGINAL
    elif  quality == "compressed":
        quality = frame_provider.Quality.COMPRESSED
    else:
        raise ValueError("unsupport quality")

    image = frame_provider.get_frame(frame, quality=quality)
    if frame_provider.dimension == DimensionType.DIM_3D:
        pcd = o3d.io.read_point_cloud(image[0])
        xyz = np.asarray(pcd.points, dtype=np.float32)
        colors = np.asarray(pcd.colors, dtype=np.float32)  # make sure pcd shape is (N, 4)
        if len(colors) == 0:
            intensity = np.zeros((1, len(xyz)))
        else:
            intensity = colors[:, 0].reshape(1, -1)
        points = np.append(xyz, intensity.T, axis=1)
        points_bytes = points.tobytes()
        return base64.b64encode(points_bytes).decode('utf-8')

    return base64.b64encode(image[0].getvalue()).decode('utf-8')