'''
Date: 2021-12-15 11:07:12
Company: Luokung Technology Corp.
LastEditors: Will Cheng Yong chengyong@pku.edu.cn
LastEditTime: 2022-10-13 10:07:07
'''
from flask_cors import CORS

from project.server import app
from logger import logger
from project.server.lambda_manager.functions import lambda_blueprint

app.config.from_object("project.server.config.ProductionConfig")
app.register_blueprint(lambda_blueprint, url_prefix='/api/v1/lambda')

cors = CORS(app)
logger.info("Init flask app.")

if __name__ == "__main__":
    # cli()
    app.run()
