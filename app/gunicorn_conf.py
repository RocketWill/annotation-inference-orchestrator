'''
Date: 2022-01-05 23:57:15
Company: Luokung Technology Corp.
LastEditors: Will Cheng Yong chengyong@pku.edu.cn
LastEditTime: 2022-10-13 10:00:25
'''
import os
import warnings

warnings.filterwarnings("ignore")

bind = os.environ['GUNICORN_BIND'] or '0.0.0.0:5000'
backlog = 2048
workers = os.environ['GUNICORN_WORKERS'] or 10
worker_class="sync"
worker_connections = 1000
timeout = os.environ['GUNICORN_TIMEOUT'] or 30
keepalive = os.environ['GUNICORN_KEEPALIVE'] or 4
spew = False
debug=True
pidfile = os.environ['GUNICORN_PIDFILE'] or 'pid.txt'
umask = 0
user = None
group = None
tmp_upload_dir = None
errorlog = os.environ['GUNICORN_ERRORLOG'] or 'error.log'
loglevel = os.environ['GUNICORN_LOGLEVEL'] or 'debug'
accesslog = '-'
proc_name = None

def post_fork(server, worker):
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def pre_fork(server, worker):
    pass

def pre_exec(server):
    server.log.info("Forked child, re-executing.")

def when_ready(server):
    server.log.info("Server is ready. Spawning workers")

def worker_int(worker):
    worker.log.info("worker received INT or QUIT signal")

    ## get traceback info
    import threading, sys, traceback
    id2name = {th.ident: th.name for th in threading.enumerate()}
    code = []
    for threadId, stack in sys._current_frames().items():
        code.append("\n# Thread: %s(%d)" % (id2name.get(threadId,""),
            threadId))
        for filename, lineno, name, line in traceback.extract_stack(stack):
            code.append('File: "%s", line %d, in %s' % (filename,
                lineno, name))
            if line:
                code.append("  %s" % (line.strip()))
    worker.log.debug("\n".join(code))

def worker_abort(worker):
    worker.log.info("worker received SIGABRT signal")
