#!/bin/bash

# Start rabbitmq docker

MAIN_PORT=5672
HTTP_API_PORT=15672

docker run --rm -it \
--hostname lkdi-mq \
--name lkdi-mg \
-p ${MAIN_PORT}:5672 \
-p ${HTTP_API_PORT}:15672 \
rabbitmq:3-management