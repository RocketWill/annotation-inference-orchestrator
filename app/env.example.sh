#!/usr/bin/env bash

# Copy this file to app/env.sh and adjust the values for your environment.

# Logging
export LOG_ROOT="${PWD}"

# Gunicorn
export GUNICORN_BIND="0.0.0.0:5000"
export GUNICORN_WORKERS=4
export GUNICORN_TIMEOUT=30
export GUNICORN_KEEPALIVE=4
export GUNICORN_PIDFILE="pid.txt"
export GUNICORN_LOGLEVEL="info"
export GUNICORN_ERRORLOG="error.log"

# Celery and RabbitMQ
export CELERY_WORKER="amqp://rabbitmq:5672"
export CELERY_BACKEND="amqp://rabbitmq:5672"

# Python modules
export PYTHONPATH="${PYTHONPATH}:${PWD}/project/server"
export PYTHONPATH="${PYTHONPATH}:${PWD}/project/server/lambda_manager"
export PYTHONPATH="${PYTHONPATH}:${PWD}/project/server/lambda_manager/tools/projection"

# Nuclio dashboard API
export NUCLIO_PROJECT_NAME="annotation-models"
export NUCLIO_SCHEME="http"
export NUCLIO_HOST="nuclio-dashboard"
export NUCLIO_PORT=8070
export NUCLIO_DEFAULT_TIMEOUT=30

# Annotation platform backend
export ANNOSERVER_SCHEME="http"
export ANNOSERVER_HOST="annotation-server"
export ANNOSERVER_PORT=8080
export ANNOSERVER_DEFAULT_TIMEOUT=60
