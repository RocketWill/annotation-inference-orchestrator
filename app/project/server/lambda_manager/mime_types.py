'''
Date: 2021-12-20 11:22:50
Company: Luokung Technology Corp.
LastEditors: Will Cheng Yong
LastEditTime: 2021-12-20 11:22:44
'''
import os
import mimetypes


_SCRIPT_DIR = os.path.realpath(os.path.dirname(__file__))
MEDIA_MIMETYPES_FILES = [
    os.path.join(_SCRIPT_DIR, "media.mimetypes"),
]
mimetypes.init(files=MEDIA_MIMETYPES_FILES)