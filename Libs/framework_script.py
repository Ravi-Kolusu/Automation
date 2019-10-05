#!/usr/bin/python
# -*- coding: UTF-8-*-

__author__ = "Raviteja kolusu"
__date__ = "30th Sep 2019"
__version__ = 1.0
__license__ = "private"

import numpy
import paramiko
import os
import sys
import re
import time
import argparse
import traceback
from argparse import RawDescriptionHelpFormatter
from xml.etree.ElementTree import ParseError

import hashlib
import datetime

def getLibAbsPath(currentPath, depth):
    """Get an absolute path relative depth
    Args:
        currentPath (str): current file's directory abs
    """
    libPath = currentPath
    while depth:
        libPath = os.path.split(libPath)[0]
        depth -= 1
    return libPath

def initLibPath():
    """
    init lib path, append lib path into python path
    """
    libHash = {'lib':1, 'sample':1, 'Tests':3, 'scripts':5, 'UtilityLibraries':3}
    binPath = os.path.split(os.path.realpath(__file__))[0]
    for key in libHash:
        sys.path.append(os.path.join(getLibAbsPath(binPath, libHash[key]), key))

# Initialize the library path of the current execution machine
initLibPath()
if sys.version_info >= (3, 0):
    raise RuntimeError('You need python 2.7')

"""
def execute_main(mainConfig):
    
    #Args:
    #   mainConfig(dict):
        
    
    testBedInfo = {}
    if "testbed_file" in mainConfig:
        testBedInfo = XmlToDict.getConfigFileRawData(mainConfig["testbed_file"])["testbedinfo"]
    testSetRawData = XmlToDict.getConfigFileRawData(mainConfig["test_set_file"])
    testSetInfo = testSetRawData["opt"]["test_set"]
"""