#!/usr/bin/python
# -*- coding: UTF-8 -*-

"""
功 能:

版权信息: 华为技术有限公司，版权所有(C) 2014-2015

修改记录: 2016/5/17 严旭光 y00292329 created

"""
try:
import pymongo
UniAutosDB = pymongo.MongoClient(host="10.183.100.106").UniAutos
except:
pass


class Dryrun(object):
def __init__(self):
pass

def dryrun(self, methodName, cmdTemplate, params, option=None):
view = cmdTemplate.get("view", ["admincli"])[0]
for item in UniAutosDB[view].find({"cmd": methodName}):
flag = True
for key in params.keys():
if key in item["params"]:
continue
flag = False
break
if flag:
return item["response"]
return None

def insertData(self, methodName, cmdTemplate, params,response):
view = cmdTemplate.get("view", ["admincli"])[0]
UniAutosDB[view].insert({"cmd": methodName, "params": params.keys(), "response": response})