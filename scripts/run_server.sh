#!/bin/bash

# Start Auto-annotation server

SERVER_ROOT="${SERVER_ROOT:-/path/to/server/root}"
UPLOAD_ROOT="${UPLOAD_ROOT:-/path/to/upload/dir}"
START_SCRIPT="${START_SCRIPT:-${SERVER_ROOT}/app/dockerfiles/auto_anno_entrypoint.sh}"
SERVER_IMAGE="${SERVER_IMAGE:-lkdi-auto-anno-server:local}"
PORT="${PORT:-10008}"

docker run -it \
--name=lkdi-auto-anno-server \
-p ${PORT}:5000 \
-v ${SERVER_ROOT}:/app \
-v ${UPLOAD_ROOT}:/workspace/uploadPath \
--mount type=bind,source=${START_SCRIPT},target=/run/entrypoint.sh \
"${SERVER_IMAGE}"
