#!/bin/bash
###
 # @Author: Will Cheng Yong chengyong@pku.edu.cn
 # @Date: 2022-10-12 17:49:23
 # @LastEditors: Will Cheng Yong chengyong@pku.edu.cn
 # @LastEditTime: 2022-10-13 10:05:43
 # @FilePath: /lkdi-auto-annotation/app/dockerfiles/auto_anno_entrypoint.sh
 # @Description:
 #
 # Copyright (c) 2022 by Will Cheng Yong chengyong@pku.edu.cn, All Rights Reserved.
###

# start flask app and celery

WORK_DIR="${WORK_DIR:-/app}"
ENV_FILE="${ENV_FILE:-env.sh}"

cd "${WORK_DIR}"
source "${ENV_FILE}"
gunicorn -c gunicorn_conf.py manage:app &
celery worker --app=project.server.lambda_manager.tasks.celery --loglevel=info
