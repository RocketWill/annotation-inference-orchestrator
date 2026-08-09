'''
Date: 2022-01-05 19:58:41
Company: Luokung Technology Corp.
LastEditors: Will Cheng Yong
LastEditTime: 2022-01-05 22:53:03
'''
import os

CELERY_BROKER_URL     = os.environ["CELERY_WORKER"]
CELERY_RESULT_BACKEND = os.environ["CELERY_BACKEND"]

# 时区
CELERY_TIMEZONE = "Asia/Shanghai"

# celery任务执行结果的超时时间
CELERY_TASK_RESULT_EXPIRES = 24 * 60 * 60

# 单个任务的运行时间限制，否则会被杀死
CELERYD_TASK_TIME_LIMIT = 6000

# 关闭限速
CELERY_DISABLE_RATE_LIMITS = True

# celery worker的并发数
CELERYD_CONCURRENCY = 20

# celery worker 每次去BROKER中预取任务的数量
CELERYD_PREFETCH_MULTIPLIER = 4

# 每个worker执行了多少任务就会死掉，默认是无限的
# CELERYD_MAX_TASKS_PER_CHILD = 40

# 设置默认的队列名称，如果一个消息不符合其他的队列就会放在默认队列里面，如果什么都不设置的话，数据都会发送到默认的队列中
CELERY_DEFAULT_QUEUE = "default"
