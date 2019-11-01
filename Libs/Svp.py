
#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
功 能：高端存储svp类，Linux虚拟机, 可操作阵列cli，exit后退出到linux虚拟机
"""

from UniAutos.Device.Host.Controller.OceanStor import OceanStor

class Svp(OceanStor):

def __init__(self, username, password, params):
super(Svp, self).__init__(username, password, params)
self.os = 'Svp'
self.updateRunningVersion()
self.vmUsername = 'root'
self.vmPassword = params.get('linux_root')
