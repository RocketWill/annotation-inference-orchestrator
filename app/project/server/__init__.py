'''
Date: 2021-12-11 12:50:17
LastEditors: Will Cheng Yong
LastEditTime: 2022-01-06 19:44:47
FilePath: /cvat/flask-celery/project/server/__init__.py
'''
import os

from flask import Flask
from celery import Celery

def create_app(script_info=None):

    # instantiate the app
    app = Flask(
        __name__,
        static_folder="./static",
    )

    # set config
    app_settings = os.getenv("APP_SETTINGS")
    app.config.from_object(app_settings)
    # shell context for flask cli
    app.shell_context_processor({"app": app})

    return app

def make_celery(app):
    celery = Celery(
        app.name,
        backend=os.environ["CELERY_WORKER"],
        broker =os.environ["CELERY_BACKEND"]
    )
    default_config = 'project.server.celery_conf'
    celery.config_from_object(default_config)
    return celery

app = create_app()
celery = make_celery(app)