import psutil
import select
import numpy as np
import os
import logging.config
from collections import OrderedDict
import matplotlib
matplotlib.rcParams['figure.max_open_warning'] = 100

def create_stamp():
    from datetime import datetime
    import time
    return datetime.fromtimestamp(time.time()).strftime('%Y%m%d_%H%M%S')   

_LOG_DIR = os.path.join(os.getcwd(), 'logs')
_LOG_FILE = create_stamp() + '.log'

def set_logging_config(console_level="WARNING", log_level="DEBUG"):
    '''
    level = ['INFO'|'DEBUG'|'WARNING'|'ERROR'|etc.]
    '''
    logging.config.dictConfig({
        'version': 1,
        'formatters': {
            'standard': {
                'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
            },
        },
        'handlers': {
            "console": {
                "class": "logging.StreamHandler",
                "level": console_level,
                "formatter": "standard",
                "stream": "ext://sys.stdout"
            },
            'file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': log_level,
                'formatter': 'standard',
                'filename': os.path.join(_LOG_DIR,_LOG_FILE),
                'mode': 'a',
                'maxBytes': 10485760,
                'backupCount': 5,
            },
        },
        "loggers": {
            "": {
                "handlers": ['console', 'file'],
                'level': log_level,
                'propagate': True
            }
        }
    })

if not os.path.exists(_LOG_DIR):
    os.makedirs(_LOG_DIR)

def _get_running_procs():
    procs = []
    for pid in psutil.pids():
        p = psutil.Process(pid)
        pdict = p.as_dict(attrs=['pid', 'name', 'username'])
        if pdict['name'] == 'Python':
            procs.append(p)
    return procs

def _kill_all_child_procs():
    procs = _get_running_procs()
    pids = [proc.pid for proc in procs]
    for p in procs:
        if p.ppid() in pids:
            if procs[pids.index(p.ppid())].ppid() in pids:
                p.kill()

def connect_socket(HOST, PORT):
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((HOST, PORT))
    return s

def socket_poll(s):
    inputready, o, e = select.select([s],[],[], 0.0)
    return len(inputready)>0

def ask_socket(s, cmd):
    import time
    '''query socket and return response'''
    #empty socket buffer
    if socket_poll(s):
        s.recv(1024)
    s.sendall(cmd.encode())
    while not socket_poll(s):
        time.sleep(.01)
    data = b''
    while socket_poll(s):
        data += s.recv(1024)
    try:
        ans = eval(data)
    except (IndentationError, SyntaxError, NameError, TypeError):
        ans = data.decode()
    return ans

def read_pipe(pipe):
    data = pipe.recv()
    try:
        ans = eval(data)
    except (NameError, IndentationError, SyntaxError, TypeError):
        ans = data
    return ans

def ask_pipe(pipe, cmd):
    pipe.send(cmd)
    return read_pipe(pipe)

def flush_pipe(pipe):
    while pipe.poll():
        pipe.recv()

def get_array(start, stop, step):
    if (stop-start)<0:
        step = -step
    return np.arange(start, stop+step, step)