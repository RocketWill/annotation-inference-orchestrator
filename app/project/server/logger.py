'''
Date: 2021-12-28 22:17:05
Company: Luokung Technology Corp.
LastEditors: Will Cheng Yong
LastEditTime: 2021-12-28 22:21:45
'''
import os
import pathlib
import logging.config

project_root = pathlib.Path().resolve() # /app
logger_config = os.path.join(project_root, "logger_cfg.cfg")
logging.config.fileConfig(logger_config)
logger = logging.getLogger('Admin_Client')