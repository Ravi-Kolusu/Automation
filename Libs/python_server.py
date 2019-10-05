import requests
import json
import os, sys
import subprocess
import socket
from datetime import datetime
from flask import Flask, request, Response, jsonify

if sys.platform == 'linux2':
    filename = '/opt/data/log/app_' + socket.gethostname() + '.log'

def write_log(log):
    with open(filename, 'a') as f:
        f.write(datetime.now().strftime("[%d-%m-%y-%H:%M:%S:%f]")+str(log)+'\n')
        f.flush()
