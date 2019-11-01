#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
功 能：Svp Windows和Linux虚拟机的宿主机
"""

from UniAutos.Device.Host.Linux import Linux


class SvpMaster(Linux):
def __init__(self, username, password, params):
super(SvpMaster, self).__init__(username, password, params)
self.os = 'Linux'
self.superUser = params.get('super_username')
self.superPassword = params.get('super_password')

