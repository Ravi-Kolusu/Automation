
# -*- coding: utf-8 -*-

"""
功 能: SNMP Trap的基本操作接口

版权信息: 华为技术有限公司，版权所有(C) 2014-2015
"""

import traceback
import uuid
import time

from pysnmp.entity import engine, config
from pysnmp.carrier.asynsock.dgram import udp
from pysnmp.entity.rfc3413 import ntfrcv

from UniAutos.Wrapper.Api.SnmpBase import SnmpBase
from UniAutos.Util.Threads import Threads
from UniAutos.Util.Time import sleep


class SnmpTrap(SnmpBase):

def __init__(self,
listenerIp,
listenerPort=162,
snmpVer='v3',
userName=None,
userDefineMibsDir=None,
communityData=('storage_public', 'storage_private'),
authKey=None,
privKey=None,
authProtocol=None,
privProtocol=None):
"""Constructor of SnmpTrap class

Args:
listenerIp (str) : Trap listener ip address. Don't use loopback ip address, such as 127.0.0.x
listenerPort (int) : (Optional)Trap listener port. Default: 162
snmpVer (str) : (Optional)SNMP version. Values: v1/v2c/v3. Default: v3
userName (str) : (Optional)SNMP username for v3
userDefineMibDir (str) : (Optional)User define mib files location. Auto detect file pattern: *mib.py. Default: None
communityData (tuple) : (Optional)Read-write community. Default: ('storage_public', 'storage_private')
authKey (str) : (Optional)Authenticate password. Default: None
privKey (str) : (Optional)Privacy password. Default: None
authProtocol (str) : (Optional)Authenticate protocol. Values: MD5/SHA/NONE. Default: NONE
privProtocol (str) : (Optional)Privacy protocol. Values: AES128/AES192/AES256/DES/3DES/NONE. Default: NONE

Returns:
Instance of SnmpTrap class

Raises:
None

Examples:
None

"""

super(SnmpTrap, self).__init__(userDefineMibsDir=userDefineMibsDir)

self.trapMessage = []
self.__trapJobId = None
self.__snmpEngine = engine.SnmpEngine()

config.addSocketTransport(
self.__snmpEngine,
udp.domainName,
udp.UdpTransport().openServerMode((listenerIp, listenerPort))
)

if snmpVer == 'v3':
config.addV3User(
self.__snmpEngine,
userName=userName,
authKey=authKey,
privKey=privKey,
authProtocol=self.getAuthProtocolType(authProtocol),
privProtocol=self.getPrivProtocolType(privProtocol)
)
else:
# a single arg is considered as a community name
communityName = communityData[0]
communityIndex = communityData[1] if len(communityData) == 2 else None

config.addV1System(self.__snmpEngine, communityIndex, communityName)

ntfrcv.NotificationReceiver(self.__snmpEngine, self.__receiveMessage)

def __startEngine(self, snmpEngine):
"""Start snmp trap listener engine
"""

try:
snmpEngine.transportDispatcher.runDispatcher()
except Exception:
snmpEngine.transportDispatcher.closeDispatcher()
self.logger.warn('Unable to run snmp trap listener.\n%s' % traceback.format_exc())

def __receiveMessage(self, snmpEngine, stateReference, contextEngineId, contextName, varBinds, cbCtx):
"""Callback function for ntfrcv.NotificationReceiver
"""

result = self.parseResult(None, None, None, varBinds)
if not isinstance(result, dict):
self.trapMessage.append(result)
return
for key, val in result.items():
if key == '0':
newOid = '%s.%s' % (val.pop('snmpTrapOID'), val['sysUpTime'])
snmpTrapNodeName = '%s::%s.%s' % self.oid2MibName(newOid)
self.trapMessage.append({snmpTrapNodeName: val})
return
#如果前面没有return判定为没有期望数据，抛出异常
self.trapMessage.append(result)
raise 'Invalid snmp trap message.'

def trap(self, cbFun, waitListenerReady=3, checkMsgNoDiffTimes=3, maxWaitTime=300, timeInterval=1):
"""Start/stop trap listener, run user define function to trigger event, and deal trap message, all in one function

Args:
cbFun (Func) : User define callback function. User can trigger Array event in the function
waitListenerReady (int) : (Optional)Max wait time for trap listener thread to ready. Unit: sec. Default: 3
checkMsgNoDiffTimes (int) : (Optional)Times to check whether trap message is complete. Unit: sec. Default: 3
maxWaitTime (int) : (Optional)Max wait time for trap listener to receive message. Unit: sec. Default: 300
timeInterval (int) : (Optional)Time interval of maxWaitTime. Unit: sec. Default: 1

Returns:
None or log error

Raises:
None

Examples:
# user define function
def simulateAlarm():
arrayHostObj.run({'command': ['change notification trap',
'server_id=3',
'trap_version=v3',
'server_ip=100.148.95.22',
'server_port=163',
'usm_user_name=xxx',
'function_test=yes']})

msg = snmpTrapObj.trap(simulateAlarm)
print msg

"""

if cbFun is None or not hasattr(cbFun, '__call__'):
return

self.start(waitListenerReady=waitListenerReady)

try:
cbFun()

checkTimes = 0
tmpMsg = str(self.trapMessage)
now = time.time()
while time.time() - now < int(maxWaitTime) and checkTimes < int(checkMsgNoDiffTimes):
trapMsg = str(self.trapMessage)
if tmpMsg != trapMsg:
checkTimes = 0
tmpMsg = trapMsg
else:
checkTimes = checkTimes + 1
sleep(timeInterval)
except Exception:
self.logger.error('User define callback function cause an error.\n%s' % traceback.print_exc())
finally:
self.stop()

return self.trapMessage

def start(self, waitListenerReady=3):
"""Start snmp trap listener

Args:
waitListenerReady (int) : (Optional)Max wait time for trap listener thread to ready. Unit: sec. Default: 3

Returns:
None or log error

Raises:
None

Examples:
snmpTrapObj.start() # maybe need more time to wait trap listener start
# simulate or trigger event in your code
snmpTrapObj.stop() # maybe need sleep before stop trap listener to receive all message
print snmpTrapObj.trapMessage

"""

self.__trapJobId = str(uuid.uuid4())
self.__snmpEngine.transportDispatcher.jobStarted(self.__trapJobId) # this job would never finish

# ip address error or ip already been bound will cause CarrierError
thread = Threads(self.__startEngine, self.__trapJobId, snmpEngine=self.__snmpEngine)

# sleep 1s, wait trap listener thread ready
thread.start()
sleep(2)

now = time.time()
while time.time() - now < waitListenerReady:
if thread.is_alive:
self.logger.info('SNMP trap listener is ready, trap job id: %s.' % self.__trapJobId)
return
else:
sleep(1)
if thread.errorMsg:
self.logger.error(thread.errorMsg)
self.logger.error('SNMP trap listener is not ready, trap job id: %s.' % self.__trapJobId)

def stop(self):
"""Stop snmp trap listener

Args:
None

Returns:
None

Raises:
None

Examples:
snmpTrapObj.start() # maybe need more time to wait trap listener start
# simulate or trigger event in your code
snmpTrapObj.stop() # maybe need sleep before stop trap listener to receive all message
print snmpTrapObj.trapMessage

Notice:
Be sure to stop snmp trap listener, or you can't get trap message next time until shutdown the listener port

"""

self.logger.info("stop trap listener, trap job id: %s" % self.__trapJobId)
if self.__trapJobId is None:
return
self.__snmpEngine.transportDispatcher.jobFinished(self.__trapJobId)
self.__snmpEngine.transportDispatcher.closeDispatcher()
self.__trapJobId = None
