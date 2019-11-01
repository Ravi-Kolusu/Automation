#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
功 能：Svp Windows和Linux虚拟机的宿主机
"""

from UniAutos.Device.Host.Linux import Linux


class SvpIpmi(Linux):
def __init__(self, username, password, params):
super(SvpIpmi, self).__init__(username, password, params)
self.os = 'Linux'
