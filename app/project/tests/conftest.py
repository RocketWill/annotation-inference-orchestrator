'''
Date: 2021-12-22 01:58:23
Company: Luokung Technology Corp.
LastEditors: Will Cheng Yong
LastEditTime: 2021-12-30 00:37:07
'''
import pytest

from project.server import create_app

@pytest.fixture(scope="module")
def test_app():
    app = create_app()
    app.config.from_object("project.server.config.TestingConfig")
    with app.app_context():
        yield app  # testing happens here
