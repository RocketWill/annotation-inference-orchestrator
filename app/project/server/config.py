'''
Date: 2021-12-22 01:58:23
Company: Luokung Technology Corp.
LastEditors: Will Cheng Yong
LastEditTime: 2022-01-06 02:16:50
'''
class DevelopmentConfig():
    TESTING = False
    WTF_CSRF_ENABLED = False


class TestingConfig():
    TESTING = True
    WTF_CSRF_ENABLED = False
    PRESERVE_CONTEXT_ON_EXCEPTION = False


class ProductionConfig():
    DEBUG = False
    TESTING = False
    WTF_CSRF_ENABLED = True
    PRESERVE_CONTEXT_ON_EXCEPTION = False
