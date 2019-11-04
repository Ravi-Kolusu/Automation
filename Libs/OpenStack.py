#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
功 能: OpenStack management主机类, 提供主机操作相关接口，如: 创建分区， 创建文件系统等.
"""

import sys
import re
import uuid
import base64
import time

from Linux import Linux
from UniAutos.Exception.UniAutosException import UniAutosException
from UniAutos.Component.Volume.Huawei.OpenStack import Volume
from UniAutos.Component.OpenStackSnapshot.Huawei.OpenStack import Snapshot
from UniAutos.Component.OpenStackSnapshot.Huawei.ShareSnapshot import ShareSnapshot
from UniAutos.Component.OpenStackSnapshot.Huawei.VolumeSnapshot import VolumeSnapshot
from UniAutos.Component.OpenStackShare.Huawei.OpenStack import Share
from UniAutos.Component.Instance.Huawei.OpenStack import Instance
from UniAutos.Component.VolumeType.Huawei.OpenStack import VolumeType
from UniAutos.Component.QosType.Huawei.OpenStack import QosType
from UniAutos.Component.ShareType.Huawei.OpenStack import ShareType
from UniAutos.Component.OpenstackUtility.Huawei.OpenStack import Utility
from UniAutos.Component.ConsisGroup.Huawei.OpenStack import ConsisGroup
from UniAutos.Component.ShareServer.Huawei.OpenStack import ShareServer
from UniAutos.Util.Time import sleep

class OpenStack(Linux):
    def __init__(self, username, password, params):
        """OpenStack management主机类，继承于Host类，该类主要包含OpenStack management主机相关操作于属性
        -下面的Components类属于Esx主机类，包含Nice Name与Component Class Name:

        Nice Name Component Class Name
        ================================================================
        TO be added

        -构造函数参数:
        Args:
        username (str): SRM登陆使用的用户名, 建议使用root用户.
        password (str): username的登陆密码.
        params (dict): 其他参数, 如下定义:
        params = {"protocol": (str),
        "port": (str),
        "ipv4_address": (str),
        "ipv6_address": (str),
        "os": (str),
        "type": (str)}
        params键值对说明:
        protocol (str): 通信协议，可选，取值范围:
        ["storSSH", "standSSH", "local", "telnet", "xml-rpc"]
        port (int): 通信端口，可选
        ipv4_address (str): 主机的ipv4地址，key与ipv6_address必选其一
        ipv6_address (str): 主机的ipv6地址，key与ipv4_address必选其一
        os (str): 主机操作系统类型，可选
        type (str): 连接的类型

        Returns:
        srmObj (instance): srmObj.

        Raises:
        None.

        Examples:
        None.

        """
        super(OpenStack, self).__init__(username, password, params)
        ipAddress = ""
        if "ipv4_address" in params and params["ipv4_address"]:
        ipAddress = params["ipv4_address"]
        elif "ipv6_address" in params and params["ipv6_address"]:
        ipAddress = params["ipv6_address"]
        else:
        raise UniAutosException("The IP address of SRM should be passed "
        +"in while creating SRM device object")

        group = re.match('http:\/\/(.*):.*', params['auth_url'], re.I)

        if group:
        params['auth_url'].replace(group.group(1), ipAddress)

        module = "UniAutos.Wrapper.Tool.OpenStack.OpenStack"
        __import__(module)
        moduleClass = getattr(sys.modules[module], "OpenStack")
        openStackWrapperObj = moduleClass()
        self.registerToolWrapper(host=self, wrapper=openStackWrapperObj)

        for objType in self.classDict.itervalues():
        self.markDirty(objType)

        self.testBedId = ''
        self.os = 'OpenStack'


        def _encode_name(self, id):
        pre_name = id.split("-")[0]
        cmdline = {'command': ['echo', '"print ', 'hash(\'%s\')"' % id ,
        '| /usr/bin/python']}
        res = self.run(cmdline)
        vol_encoded = str(res['stdout'])
        if vol_encoded.startswith('-'):
        newuuid = pre_name + vol_encoded
        else:
        newuuid = pre_name + '-' + vol_encoded
        return newuuid
        # uuid_str = id.replace("-", "")
        # vol_uuid = uuid.UUID('urn:uuid:%s' % uuid_str)
        # vol_encoded = base64.urlsafe_b64encode(vol_uuid.bytes)
        # newuuid = vol_encoded.replace("=", "")
        # return newuuid

        def encode_pyhermetro_cg_name(self, id):
        newuuid = self._encode_name(id)
        return newuuid

        def createVolume(self, size, name=None, volumeType=None, sourceVolid=None, snapshotId=None,
        imageId=None, description=None, availabilityZone=None, metadata=None):

        """获得Volume对性的静态属性列表。

        Args:
        volumeId str Volume id
        name str Volume name
        size str Volume size
        volumeType str Volume type
        sourceVolid str Creates volume from volume ID
        snapshotId str Creates volume from snapshot ID
        imageId str Creates volume from image ID
        description str Volume description
        availabilityZone str Availability zone for volume
        metadata str Metadata key and value pairs
        replication_status str Replication status
        replica_driver_data str Replication pair id and remote lun id

        """

        return Volume.create(self, size, name, volumeType, sourceVolid, snapshotId, imageId,
        description, availabilityZone, metadata)

        def createImage(self, object, name=None, diskformat=None):

        """获得Volume对性的静态属性列表。

        Args:
        name Str Image name
        diskformat Str Format type

        """

        return object.createImage(name, diskformat)

        def removeVolume(self, volumes, force=None):

        """获得Volume的静态属性列表。

        Args:
        volumes objects Volume Objects

        Changes:
        2015-10-16 l00251491 Created
        """

        result=''
        for volume in volumes:
        result = volume.remove(force)
        return result

        def extendVolume(self, object, extendSize ):

        """获得Volume对性的静态属性列表。

        Args:
        object Object Volume Object
        extendSize str Volume extend size

        """

        return object.extend(extendSize)

        def manageVolume(self, host, identifier, idType=None, name=None, description=None, volumeType=None,
        availabilityZone=None, metadata=None, bootable=None):

        """获得Volume对性的静态属性列表。

        Args:
        host str Cinder host on which the existing volume resides
        identifier str Name or other Identifier for existing volume
        idType str Type of backend device identifier provided
        name str Volume name (Default=None)
        description str Volume description (Default=None)
        volumeType str Volume type (Default=None)
        availabilityZone str Availability zone for volume
        metadata str Metadata key=value pairs (Default=None)
        bootable str Specifies that the newly created volume should be marked as bootable

        """

        return Volume.manage(self, host, identifier, idType, name, description, volumeType,
        availabilityZone, metadata, bootable)

        def unmanageVolume(self, object):

        """获得 Share 对性的静态属性列表。

        Args:
        object obj Volume

        """

        return object.unmanage(object)

        def createSnapshot(self, object, objectId=None, objectName=None,name=None,
        force=None, description=None, metadata=None):

        """获得Snapshot对性的静态属性列表。

        Args:
        object obj Volume/Share
        objectId str Volume id/Share id
        objectName str Volume name/Share name
        name str Snapshot name
        force str Snapshot type
        description str Snapshot description
        metadata str Metadata key and value pairs

        """
        object_pros = object.getProperties()
        if object_pros.get('share_proto'):
        return ShareSnapshot.create(self, object, objectId, objectName,
        name, force, description, metadata)
        else:
        return VolumeSnapshot.create(self, object, objectId, objectName,
        name, force, description, metadata)

        def removeSnapshot(self,snapshots):

        """获得Snapshot的静态属性列表。

        Args:
        volumes objects Volume Objects

        Changes:
        2015-10-16 l00251491 Created
        """

        result = ''
        for snapshot in snapshots:
        result = snapshot.remove()
        return result

        def manageSnapshot(self, object, identifier, idType=None, name=None, description=None, metadata=None):

        """获得Snapshot对性的静态属性列表。

        Args:
        object obj Volume or Share object
        identifier str Name or other Identifier for existing Snapshot
        idType str Type of backend device identifier provided
        name str Snapshot name (Default=None)
        description str Snapshot description (Default=None)
        metadata str Metadata key=value pairs (Default=None)
        """

        object_pros = object.getProperties()
        if object_pros.get('share_proto'):
        return ShareSnapshot.manage(self, object, identifier, idType, name, description, metadata)
        else:
        return VolumeSnapshot.manage(self, object, identifier, idType, name, description, metadata)

        def unmanageSnapshot(self, objectType, object,identifier=None):

        """获得 Snapshot 对性的静态属性列表。

        Args:
        object obj Snapshot
        objectType str cinder/manila

        """

        return object.unmanage(object,identifier)

        def createShare(self, shareProtocol, size, name=None, shareType=None, snapshotId=None, shareNetwork=None, public=None,
        description=None, availabilityZone=None, metadata=None, consistencyGroup=None):

        """获得Share对性的静态属性列表。

        Args:
        Share_id str Share id
        name str Share name
        size str Share size
        shareProtocol str Share use protocol
        shareType str Share type
        shareNetwork str Optional network info ID or name
        snapshotId str Creates share from snapshot ID
        consistencyGroup str Optional consistency group name or ID in which to create the share
        description str Share description
        availabilityZone str Availability zone for Share
        metadata str Metadata key and value pairs
        public str Level of visibility for share

        """

        return Share.create(self, shareProtocol, size, name, shareType, snapshotId, shareNetwork, public,
        description, availabilityZone, metadata, consistencyGroup)

        def removeShare(self,shares):

        """获得 Share 的静态属性列表。

        Args:
        shares objects Share Objects

        Changes:
        2015-10-23 l00251491 Created
        """

        result = ''
        for share in shares:
        result = share.remove()
        return result

        def removeShareServer(self, shareServers):

        """获得 Share 的静态属性列表。

        Args:
        shares objects Share Objects

        Changes:
        2015-12-08 h00248497 Created
        """

        result = ''
        for shareServer in shareServers:
        result = shareServer.remove()
        return result

        def extendShare(self, object, extendSize ):

        """获得 Share 对性的静态属性列表。

        Args:
        object Object Share Object
        extendSize str Share extend size

        """

        return object[0].extend(extendSize)

        def shrinkShare(self, object, shrinkSize ):

        """获得 Share 对性的静态属性列表。

        Args:
        object Object Share Object
        shrinkSize str Share shrink size

        """

        return object[0].shrink(shrinkSize)

        def manageShare(self, serviceHost, protocol, exportPath, name=None, shareType=None, description=None,
        driverOptions=None):

        """获得 Share 对性的静态属性列表。

        Args:
        serviceHost str manage-share service host
        protocol str Protocol of the share to manage
        exportPath str Share export path
        name str Optional share name
        shareType str Optional share type assigned to share
        description str Optional share description
        driverOptions str Driver option key=value pairs

        """

        return Share.manage(self, serviceHost, protocol, exportPath, name, shareType, description, driverOptions)

        def unmanageShare(self, object):

        """获得 Share 对性的静态属性列表。

        Args:
        object obj Share

        """

        return object.unmanage(object)

        def resetShare(self, objects):
        """重置volume或share状态为available。

        Args:
        objects list Volume or Share Objects

        Changes:
        2016-02-25 g00289391 Created
        """
        result = ''
        for object in objects:
        result = object.reset()
        return result

        def allowAccess(self, share, accessType, accessTo, accessLevel=None):

        """获得 Share 对性的静态属性列表。

        Args:
        share str Share object
        accessType str Access rule type
        accessTo str Value that defines access
        accessLevel str Share access level

        """

        return share.allow(share, accessType, accessTo, accessLevel)

        def denyAccess(self, share, id):

        """获得 Share 对性的静态属性列表。

        Args:
        share str Share object
        id str ID of the access rule to be deleted

        """

        return share.deny(share, id)

        def createInstance(self, name, flavor, image, imageWith=None, bootVolume=None, snapshot=None, minCount=None,
        maxCount=None, meta=None, file=None, keyName=None, userData=None, availabilityZone=None, securityGroups=None,
        blockDeviceMapping=None, blockDevice=None, swap=None, ephemeral = None, hint=None, nic=None, configDrive = None,
        poll=None, adminPass=None):
        """获得 Instance 对性的静态属性列表。

        Args:
        id str Instance id
        name str Instance name
        flavor str Create instance use the flavor Name or ID
        image str Create instance use the image Name or ID
        imageWith str Image metadata property
        bootVolume str Volume ID to boot from
        snapshot str Snapshot ID to boot from
        minCount str Boot at least servers
        maxCount str Boot up to servers
        meta str Record arbitrary key/value metadata to /meta_data.json on the metadata server
        file str Store arbitrary files from locally to on the new server
        keyName str Key name of keypair that should be created earlier with the command keypair-add
        userData str user data file to pass to be exposed by the metadata server
        availabilityZone str The availability zone for server placement
        securityGroups str Comma separated list of security group names
        blockDeviceMapping str Block device mapping in the format
        blockDevice str Block device mapping with the keys
        swap str Create and attach a local swap block device
        ephemeral str Create and attach a local ephemeral block
        hint str Send arbitrary key/value pairs to the scheduler for custom use
        nic str Create a NIC on the server
        configDrive str Enable config drive
        poll str Report the new server boot progress until it completes
        adminPass str Admin password for the instance

        Returns:

        Raises:

        Examples:
        None

        Changes:
        2015-10-26 l00251491 Created

        """

        return Instance.create(self, name, flavor, image, imageWith, bootVolume, snapshot, minCount, maxCount,
        meta, file, keyName, userData, availabilityZone, securityGroups, blockDeviceMapping, blockDevice,
        swap, ephemeral, hint, nic, configDrive, poll, adminPass)

        def terminateInstance(self,instances):

        """获得 Instance 的静态属性列表。

        Args:
        instances objects Instance Objects

        Changes:
        2015-10-26 l00251491 Created
        """

        result = ''
        for instance in instances:
        result = instance.terminate()
        return result

        def attachInstance(self, server, volume, device=None):
        """在主机上下发命令挂载卷
        Args:
        server Instance Name or ID of server
        volume Volume ID of the volume to attach
        device str Name of the device
        """

        return server.attach(server, volume, device)

        def detachInstance(self, server, volume):
        """在主机上下发命令挂载卷
        Args:
        server Instance Name or ID of server
        volume Volume ID of the volume to attach
        """

        return server.detach(server, volume)

        def checkZone(self, host, switch, storage):
        """用于检查挂载卷后智能划域是否正常

        Args:
        host obj Host device
        switch obj Switch device
        storage obj Storage device

        Changes:
        2015-11-28 l00251491 Created

        """
        return Instance.check(self, host, switch, storage)

        def createVolumeType(self, name, isPublic=None, description=None):

        """获得VolumeType对性的静态属性列表。

        Args:
        name str VolumeType name
        isPublic str Make type accessible to the public (default true)
        description str Description of new volume type

        """

        return VolumeType.create(self, name, isPublic, description)

        def removeVolumeType(self, volumetypes):

        """获得VolumeType对性的静态属性列表。

        Args:
        volumetypes str VolumeType Objects

        """

        result = ''
        for volumetype in volumetypes:
        result = volumetype.remove()
        return result

        def linkSmartTier(self, vtype, action, capkey=None, capvalue=None, attributekey=None, attributevalue=None):

        """新增VolumeType属性列表。

        Args:
        vtype str VolumeType obj
        action str The action
        capkey str Capabilities Key
        capvalue str Capabilities Value
        attributekey str Attribute Key
        attributevalue str Attribute Value

        """

        if ((capkey is None and capvalue) or (capkey and capvalue is None)
        or (attributekey is None and attributevalue) or (attributekey and attributevalue is None )):
        self.logger.info('Error capabilities input error')
        return "ERROR"
        return vtype.useSmartx(vtype, action, capkey, capvalue, attributekey, attributevalue)

        def unlinkSmartTier(self, vtype, action, capkey=None, capvalue=None, attributekey=None, attributevalue=None):

        """ 移除VolumeType属性列表。

        Args:
        vtype str VolumeType obj
        action str The action
        capkey str Capabilities Key
        capvalue str Capabilities Value
        attributekey str Attribute Key
        attributevalue str Attribute Value

        """

        if ((capkey is None and capvalue) or (capkey and capvalue is None)
        or (attributekey is None and attributevalue) or (attributekey and attributevalue is None )):
        self.logger.info('Error capabilities input error')
        return "ERROR"

        return vtype.useSmartx(vtype, action, capkey, capvalue, attributekey, attributevalue)

        def changeSmartTier(self, vtype, action, capkey=None, capvalue=None, attributekey=None, attributevalue=None):

        """修改VolumeType属性列表。

        Args:
        vtype str VolumeType obj
        action str The action
        capkey str Capabilities Key
        capvalue str Capabilities Value
        attributekey str Attribute Key
        attributevalue str Attribute Value

        """

        if ((capkey is None and capvalue) or (capkey and capvalue is None)
        or (attributekey is None and attributevalue) or (attributekey and attributevalue is None )):
        self.logger.info('Error capabilities input error')
        return "ERROR"

        return vtype.useSmartx(vtype, action, capkey, capvalue, attributekey, attributevalue)

        def linkSmartCache(self, vtype, action, capkey=None, capvalue=None, attributekey=None, attributevalue=None):

        """新增VolumeType属性列表。

        Args:
        vtype str VolumeType obj
        action str The action
        capkey str Capabilities Key
        capvalue str Capabilities Value
        attributekey str Attribute Key
        attributevalue str Attribute Value

        """

        if ((capkey is None and capvalue) or (capkey and capvalue is None)
        or (attributekey is None and attributevalue) or (attributekey and attributevalue is None )):
        self.logger.info('Error capabilities input error')
        return "ERROR"

        return vtype.useSmartx(vtype, action, capkey, capvalue, attributekey, attributevalue)

        def unlinkSmartCache(self, vtype, action, capkey=None, capvalue=None, attributekey=None, attributevalue=None):

        """ 移除VolumeType属性列表。

        Args:
        vtype str VolumeType obj
        action str The action
        capkey str Capabilities Key
        capvalue str Capabilities Value
        attributekey str Attribute Key
        attributevalue str Attribute Value

        """

        if ((capkey is None and capvalue) or (capkey and capvalue is None)
        or (attributekey is None and attributevalue) or (attributekey and attributevalue is None )):
        self.logger.info('Error capabilities input error')
        return "ERROR"

        return vtype.useSmartx(vtype, action, capkey, capvalue, attributekey, attributevalue)

        def changeSmartCache(self, vtype, action, capkey=None, capvalue=None, attributekey=None, attributevalue=None):

        """修改VolumeType属性列表。

        Args:
        vtype str VolumeType obj
        action str The action
        capkey str Capabilities Key
        capvalue str Capabilities Value
        attributekey str Attribute Key
        attributevalue str Attribute Value

        """

        if ((capkey is None and capvalue) or (capkey and capvalue is None)
        or (attributekey is None and attributevalue) or (attributekey and attributevalue is None )):
        self.logger.info('Error capabilities input error')
        return "ERROR"

        return vtype.useSmartx(vtype, action, capkey, capvalue, attributekey, attributevalue)

        def linkSmartPartition(self, vtype, action, capkey=None, capvalue=None, attributekey=None, attributevalue=None):

        """新增VolumeType属性列表。

        Args:
        vtype str VolumeType obj
        action str The action
        capkey str Capabilities Key
        capvalue str Capabilities Value
        attributekey str Attribute Key
        attributevalue str Attribute Value

        """

        if ((capkey is None and capvalue) or (capkey and capvalue is None)
        or (attributekey is None and attributevalue) or (attributekey and attributevalue is None )):
        self.logger.info('Error capabilities input error')
        return "ERROR"

        return vtype.useSmartx(vtype, action, capkey, capvalue, attributekey, attributevalue)

        def unlinkSmartPartition(self, vtype, action, capkey=None, capvalue=None, attributekey=None, attributevalue=None):

        """ 移除VolumeType属性列表。

        Args:
        vtype str VolumeType obj
        action str The action
        capkey str Capabilities Key
        capvalue str Capabilities Value
        attributekey str Attribute Key
        attributevalue str Attribute Value

        """

        if ((capkey is None and capvalue) or (capkey and capvalue is None)
        or (attributekey is None and attributevalue) or (attributekey and attributevalue is None )):
        self.logger.info('Error capabilities input error')
        return "ERROR"

        return vtype.useSmartx(vtype, action, capkey, capvalue, attributekey, attributevalue)

        def changeSmartPartition(self, vtype, action, capkey=None, capvalue=None, attributekey=None, attributevalue=None):

        """修改VolumeType属性列表。

        Args:
        vtype str VolumeType obj
        action str The action
        capkey str Capabilities Key
        capvalue str Capabilities Value
        attributekey str Attribute Key
        attributevalue str Attribute Value

        """

        if ((capkey is None and capvalue) or (capkey and capvalue is None)
        or (attributekey is None and attributevalue) or (attributekey and attributevalue is None )):
        self.logger.info('Error capabilities input error')
        return "ERROR"

        return vtype.useSmartx(vtype, action, capkey, capvalue, attributekey, attributevalue)

        def linkSmartThin(self, vtype, action, capkey=None, capvalue=None, attributekey=None, attributevalue=None):

        """新增VolumeType属性列表。

        Args:
        vtype str VolumeType obj
        action str The action
        capkey str Capabilities Key
        capvalue str Capabilities Value
        attributekey str Attribute Key
        attributevalue str Attribute Value

        """

        if ((capkey is None and capvalue) or (capkey and capvalue is None)
        or (attributekey is None and attributevalue) or (attributekey and attributevalue is None )):
        self.logger.info('Error capabilities input error')
        return "ERROR"

        return vtype.useSmartx(vtype, action, capkey, capvalue, attributekey, attributevalue)

        def unlinkSmartThin(self, vtype, action, capkey=None, capvalue=None, attributekey=None, attributevalue=None):

        """ 移除VolumeType属性列表。

        Args:
        vtype str VolumeType obj
        action str The action
        capkey str Capabilities Key
        capvalue str Capabilities Value
        attributekey str Attribute Key
        attributevalue str Attribute Value

        """

        if ((capkey is None and capvalue) or (capkey and capvalue is None)
        or (attributekey is None and attributevalue) or (attributekey and attributevalue is None )):
        self.logger.info('Error capabilities input error')
        return "ERROR"

        return vtype.useSmartx(vtype, action, capkey, capvalue, attributekey, attributevalue)

        def changeSmartThin(self, vtype, action, capkey=None, capvalue=None, attributekey=None, attributevalue=None):

        """修改VolumeType属性列表。

        Args:
        vtype str VolumeType obj
        action str The action
        capkey str Capabilities Key
        capvalue str Capabilities Value
        attributekey str Attribute Key
        attributevalue str Attribute Value

        """

        if ((capkey is None and capvalue) or (capkey and capvalue is None)
        or (attributekey is None and attributevalue) or (attributekey and attributevalue is None )):
        self.logger.info('Error capabilities input error')
        return "ERROR"

        return vtype.useSmartx(vtype, action, capkey, capvalue, attributekey, attributevalue)

        def linkSmartThick(self, vtype, action, capkey=None, capvalue=None, attributekey=None, attributevalue=None):

        """新增VolumeType属性列表。

        Args:
        vtype str VolumeType obj
        action str The action
        capkey str Capabilities Key
        capvalue str Capabilities Value
        attributekey str Attribute Key
        attributevalue str Attribute Value

        """

        if ((capkey is None and capvalue) or (capkey and capvalue is None)
        or (attributekey is None and attributevalue) or (attributekey and attributevalue is None )):
        self.logger.info('Error capabilities input error')
        return "ERROR"

        return vtype.useSmartx(vtype, action, capkey, capvalue, attributekey, attributevalue)

        def unlinkSmartThick(self, vtype, action, capkey=None, capvalue=None, attributekey=None, attributevalue=None):

        """ 移除VolumeType属性列表。

        Args:
        vtype str VolumeType obj
        action str The action
        capkey str Capabilities Key
        capvalue str Capabilities Value
        attributekey str Attribute Key
        attributevalue str Attribute Value

        """

        if ((capkey is None and capvalue) or (capkey and capvalue is None)
        or (attributekey is None and attributevalue) or (attributekey and attributevalue is None )):
        self.logger.info('Error capabilities input error')
        return "ERROR"

        return vtype.useSmartx(vtype, action, capkey, capvalue, attributekey, attributevalue)

        def changeSmartThick(self, vtype, action, capkey=None, capvalue=None, attributekey=None, attributevalue=None):

        """修改VolumeType属性列表。

        Args:
        vtype str VolumeType obj
        action str The action
        capkey str Capabilities Key
        capvalue str Capabilities Value
        attributekey str Attribute Key
        attributevalue str Attribute Value

        """

        if ((capkey is None and capvalue) or (capkey and capvalue is None)
        or (attributekey is None and attributevalue) or (attributekey and attributevalue is None )):
        self.logger.info('Error capabilities input error')
        return "ERROR"
        return vtype.useSmartx(vtype, action, capkey, capvalue, attributekey, attributevalue)

        def createQosType(self, name, keyValueArg):

        """创建VolumeType属性列表。

        Args:
        name str QosType name
        keyValueArg dict {'key':'value','key':'value',...}

        """
        typecnt=0
        for key in keyValueArg:
        if (key is None and keyValueArg[key]) or (key and keyValueArg[key]is None):
        self.logger.info('Error capabilities input error')
        return "ERROR"
        if key == 'IOType':
        typecnt+=1
        if typecnt>1:
        self.logger.info('Error IOType params input %d times ' % typecnt)
        return "ERROR"

        return QosType.create(self, name, keyValueArg)

        def changeQosType(self, object, action, keyValueArg):

        """修改QosType属性列表。

        Args:
        object obj QosType Object
        action str QosType Change type
        keyValueArg dict {'key':'value','key':'value',...}

        """
        typecnt=0
        for key in keyValueArg:
        if (key is None and keyValueArg[key]) or (key and keyValueArg[key]is None):
        self.logger.info('Error params the key or value input error')
        return "ERROR"
        if key == 'IOType':
        typecnt+=1
        if typecnt>1:
        self.logger.info('Error IOType params input %d times ' % typecnt)
        return "ERROR"

        return object.change(object, action, keyValueArg)

        def linkShareQosType(self, shareType, action, capkey=None, capvalue=None, keyValueArg=None):

        """创建VolumeType属性列表。

        Args:
        shareType obj shareType Object
        action str The action
        capkey str Capabilities Key
        capvalue str Capabilities Value
        keyValueArg dict {'key':'value','key':'value',...}

        """
        typecnt=0
        if (capkey is None and capvalue) or (capkey and capvalue is None):
        self.logger.info('Error capabilities input error')
        return "ERROR"
        for key in keyValueArg:
        if (key is None and keyValueArg[key]) or (key and keyValueArg[key]is None):
        self.logger.info('Error capabilities input error')
        return "ERROR"
        if key == 'IOType':
        typecnt+=1
        if typecnt>1:
        self.logger.info('Error IOType params input %d times ' % typecnt)
        return "ERROR"

        return shareType.useSmartx(shareType, action, capkey, capvalue, keyValueArg=keyValueArg)

        def unlinkQosType(self, object, action, keyValueArg):

        """修改QosType属性列表。

        Args:
        object obj QosType Object
        action str QosType Change type
        keyValueArg dict {'key':'value','key':'value',...}

        """
        typecnt=0
        for key in keyValueArg:
        if (key is None and keyValueArg[key]) or (key and keyValueArg[key]is None):
        self.logger.info('Error params the key or value input error')
        return "ERROR"
        if key == 'IOType':
        typecnt+=1
        if typecnt>1:
        self.logger.info('Error IOType params input %d times ' % typecnt)
        return "ERROR"

        return object.change(object, action, keyValueArg)

        def removeQosType(self, qostypes):

        """获得VolumeType对性的静态属性列表。

        Args:
        qostypes obj VolumeType Objects

        """

        result=''
        for qostype in qostypes:
        result = qostype.remove()
        return result

        def associateQosType(self, qosType, volumeType):
        """绑定VolumeType与QoSType。

        Args:
        qosType obj QosType Objects
        volumeType obj VolumeType Objects
        """
        return qosType.associate(qosType, volumeType)

        def disassociateQosType(self, qosType, volumeType):
        """绑定VolumeType与QoSType。

        Args:
        qosType obj QosType Objects
        volumeType obj VolumeType Objects
        """
        return qosType.disassociate(qosType, volumeType)

        def findAssociateQosType(self, volumeType):
        """通过VolumeType查询到绑定的QoSType。

        Args：
        volumeType obj VolumeType Objects
        """

        qosTypes=self.find('qostype')
        for qosType in qosTypes:
        associate=qosType.findAssociate(qosType)
        if associate and volumeType.getProperties().get('id')==associate[0].get('id'):
        return qosType
        self.logger.info('The VolumeType not associate the QosType')
        return None

        def linkHyperMetro(self, vtype, action, capkey=None, capvalue=None, attributekey=None, attributevalue=None):

        """修改VolumeType属性列表。

        Args:
        vtype str VolumeType obj
        action str The action
        capkey str Capabilities Key
        capvalue str Capabilities Value
        attributekey str Attribute Key
        attributevalue str Attribute Value

        """

        if ((capkey is None and capvalue) or (capkey and capvalue is None)
        or (attributekey is None and attributevalue) or (attributekey and attributevalue is None )):
        self.logger.info('Error capabilities input error')
        return "ERROR"
        return vtype.useSmartx(vtype, action, capkey, capvalue, attributekey, attributevalue)

        def unlinkHyperMetro(self, vtype, action, capkey=None, capvalue=None, attributekey=None, attributevalue=None):

        """修改VolumeType属性列表。

        Args:
        vtype str VolumeType obj
        action str The action
        capkey str Capabilities Key
        capvalue str Capabilities Value
        attributekey str Attribute Key
        attributevalue str Attribute Value

        """

        if ((capkey is None and capvalue) or (capkey and capvalue is None)
        or (attributekey is None and attributevalue) or (attributekey and attributevalue is None )):
        self.logger.info('Error capabilities input error')
        return "ERROR"
        return vtype.useSmartx(vtype, action, capkey, capvalue, attributekey, attributevalue)

        def checkVolumeType(self,object,storageDevice):
        """检查Volume具有的Volume属性在阵列上是否具有。

        Args:
        object Volume Volume Objects
        storageDevice Device OceaStore Device

        Returns:
        {key:True/False,key:True/False,....}

        Raises:
        None

        Changes:
        2015-11-04 l00251491 Created
        """

        result={}
        extraSpecs=''
        volume_info=object.getProperties()
        volumeTypeName = volume_info.get('volume_type')
        volumeId=object.getProperties().get('id')
        lunName=self._encode_name(volumeId)

        if volumeTypeName:
        volumeType=self.find('volumetype', criteria={'name' : volumeTypeName})
        extra_info=volumeType[0].getProperties()
        extraSpecs=extra_info['extra_specs']

        if extraSpecs != '{}':
        extraSpecs = re.sub("u'", "'", extraSpecs)
        else:
        path = self.get_file_path(self)
        file = self.getXmlfile('LUNType', 'cinder', filePath=path)
        result=volumeType[0].checkSmartXNULL(lunName, file.get('LUNType'), storageDevice)

        Lun=storageDevice.find('lun', criteria={'name' : lunName}, forceSync=True)[0]

        if re.search(r'capabilities:smarttier\': \' true', extraSpecs):
        smarttier=volumeType[0].checkSmartTier(Lun,extraSpecs,storageDevice)
        result['smarttier']=smarttier

        if re.search(r'capabilities:smartcache\': \' true', extraSpecs):
        smartcache=volumeType[0].checkSmartCache(Lun,extraSpecs,storageDevice)
        result['smartcache']=smartcache

        if re.search(r'capabilities:smartpartition\': \' true', extraSpecs):
        smartpartition=volumeType[0].checkSmartPartition(Lun,extraSpecs,storageDevice)
        result['smartpartition']=smartpartition

        if re.search(r'capabilities:thin_provisioning_support\': \' true', extraSpecs):
        if re.search(r'capabilities:thick_provisioning_support\': \' true', extraSpecs):
        self.logger.error('SmartThin and SmartThick can not exist on the same time')
        smartthin=volumeType[0].checkSmartThin(Lun,extraSpecs,storageDevice)
        result['smartthin']=smartthin

        if re.search(r'capabilities:thick_provisioning_support\': \' true', extraSpecs):
        if re.search(r'capabilities:thin_provisioning_support\': \' true', extraSpecs):
        self.logger.error('SmartThick and SmartThin can not exist on the same time')
        smartthick=volumeType[0].checkSmartThick(Lun,extraSpecs,storageDevice)
        result['smartthick']=smartthick

        if not result:
        path = self.get_file_path(self)
        file = self.getXmlfile('LUNType', 'cinder', filePath=path)
        result=volumeType[0].checkSmartXNULL(lunName, file.get('LUNType'), storageDevice)

        qosType=self.findAssociateQosType(volumeType[0])
        specs = ''
        if qosType:
        specs=qosType.getProperties()['specs']
        if specs:
        smartqos = True
        specs = re.sub("u'", "'", specs)
        smartqos=qosType.checkSmartQos(lunName,specs,storageDevice)
        self.logger.info('SmartQos not achieve on the OceanStore\'s Autos')
        result['smartqos']=smartqos
        return result

        def retypeVolume(self, object, objecttype, migrationPolicy=None):
        """获得VolumeType对性的静态属性列表。

        Args:
        object obj Volume object
        objecttype obj Volume Type object
        migrationPolicy str Migration policy during retype of volume

        """

        return object.retype(object, objecttype, migrationPolicy)

        def createShareType(self, name, specDriverHandlesShareServers, isPublic=None, snapshotSupport=None):

        """获得ShareType对性的静态属性列表。

        Args:
        name str ShareType name
        specDriverHandlesShareServers str Required extra specification
        isPublic str Make type accessible to the public
        snapshotSupport str Description of new share type

        """

        return ShareType.create(self, name, specDriverHandlesShareServers, isPublic, snapshotSupport)

        def removeShareType(self, sharetypes):

        """获得VolumeType对性的静态属性列表。

        Args:
        volumetypes str VolumeType Objects

        """

        result = ''
        for sharetype in sharetypes:
        result = sharetype.remove()
        return result



        def linkSmartDedupe(self, vtype, action, capkey=None, capvalue=None, attributekey=None, attributevalue=None):

        """新增VolumeType属性列表。

        Args:
        vtype str VolumeType obj
        action str The action
        capkey str Capabilities Key
        capvalue str Capabilities Value
        attributekey str Attribute Key
        attributevalue str Attribute Value

        """

        if ((capkey is None and capvalue) or (capkey and capvalue is None)
        or (attributekey is None and attributevalue) or (attributekey and attributevalue is None )):
        self.logger.info('Error capabilities input error')
        return "ERROR"

        return vtype.useSmartx(vtype, action, capkey, capvalue, attributekey, attributevalue)

        def unlinkSmartDedupe(self, vtype, action, capkey=None, capvalue=None, attributekey=None, attributevalue=None):

        """ 移除VolumeType属性列表。

        Args:
        vtype str VolumeType obj
        action str The action
        capkey str Capabilities Key
        capvalue str Capabilities Value
        attributekey str Attribute Key
        attributevalue str Attribute Value

        """

        if ((capkey is None and capvalue) or (capkey and capvalue is None)
        or (attributekey is None and attributevalue) or (attributekey and attributevalue is None )):
        self.logger.info('Error capabilities input error')
        return "ERROR"

        return vtype.useSmartx(vtype, action, capkey, capvalue, attributekey, attributevalue)

        def changeSmartDedupe(self, vtype, action, capkey=None, capvalue=None, attributekey=None, attributevalue=None):

        """修改VolumeType属性列表。

        Args:
        vtype str VolumeType obj
        action str The action
        capkey str Capabilities Key
        capvalue str Capabilities Value
        attributekey str Attribute Key
        attributevalue str Attribute Value

        """

        if ((capkey is None and capvalue) or (capkey and capvalue is None)
        or (attributekey is None and attributevalue) or (attributekey and attributevalue is None )):
        self.logger.info('Error capabilities input error')
        return "ERROR"

        return vtype.useSmartx(vtype, action, capkey, capvalue, attributekey, attributevalue)

        def linkSmartCompression(self, vtype, action, capkey=None, capvalue=None, attributekey=None, attributevalue=None):

        """新增VolumeType属性列表。

        Args:
        vtype str VolumeType obj
        action str The action
        capkey str Capabilities Key
        capvalue str Capabilities Value
        attributekey str Attribute Key
        attributevalue str Attribute Value

        """

        if ((capkey is None and capvalue) or (capkey and capvalue is None)
        or (attributekey is None and attributevalue) or (attributekey and attributevalue is None )):
        self.logger.info('Error capabilities input error')
        return "ERROR"

        return vtype.useSmartx(vtype, action, capkey, capvalue, attributekey, attributevalue)

        def unlinkSmartCompression(self, vtype, action, capkey=None, capvalue=None, attributekey=None, attributevalue=None):

        """ 移除VolumeType属性列表。

        Args:
        vtype str VolumeType obj
        action str The action
        capkey str Capabilities Key
        capvalue str Capabilities Value
        attributekey str Attribute Key
        attributevalue str Attribute Value

        """

        if ((capkey is None and capvalue) or (capkey and capvalue is None)
        or (attributekey is None and attributevalue) or (attributekey and attributevalue is None )):
        self.logger.info('Error capabilities input error')
        return "ERROR"

        return vtype.useSmartx(vtype, action, capkey, capvalue, attributekey, attributevalue)

        def changeSmartCompression(self, vtype, action, capkey=None, capvalue=None, attributekey=None, attributevalue=None):

        """修改VolumeType属性列表。

        Args:
        vtype str VolumeType obj
        action str The action
        capkey str Capabilities Key
        capvalue str Capabilities Value
        attributekey str Attribute Key
        attributevalue str Attribute Value

        """

        if ((capkey is None and capvalue) or (capkey and capvalue is None)
        or (attributekey is None and attributevalue) or (attributekey and attributevalue is None )):
        self.logger.info('Error capabilities input error')
        return "ERROR"
        return vtype.useSmartx(vtype, action, capkey, capvalue, attributekey, attributevalue)

        def checkShareType(self,object,storageDevice):
        """检查ShareType具有的ShareType属性在阵列上是否具有。

        Args:
        object Share Share Objects
        storageDevice Device OceaStore Device

        Returns:
        {key:True/False,key:True/False,....}

        Raises:
        None

        Changes:
        2015-11-04 l00251491 Created
        """


        share = object.getProperties()
        shareTypeId = share.get('share_type')
        shareId = share.get('id')
        shareInfo = self.find('share',criteria={'id' : shareId})[0]
        shareLocation = shareInfo.getProperty('export_locations')
        shareLocationList = shareLocation.split(',')
        sharePath = ''
        for key in shareLocationList:
        if '\\' in key or '/' in key:
        sharePath = key
        shareStorageId = sharePath.split("share")[1]
        shareName = "share"+shareStorageId
        result={}
        if shareTypeId:
        shareType=self.find('sharetype', criteria={'id' : shareTypeId})
        extraSpecs=shareType[0].getProperties()['all_extra_specs']

        extraSpecs = re.sub("u'", "'", extraSpecs)

        if re.search(r'capabilities:huawei_smarttier : true', extraSpecs):
        smarttier=shareType[0].checkSmartTier(shareName,extraSpecs,storageDevice)
        result['smarttier']=smarttier

        if re.search(r'capabilities:huawei_smartcache : true', extraSpecs):
        smartcache=shareType[0].checkSmartCache(shareName,extraSpecs,storageDevice)
        result['smartcache']=smartcache

        if re.search(r'capabilities:huawei_smartpartition : true', extraSpecs):
        smartpartition=shareType[0].checkSmartPartition(shareName,extraSpecs,storageDevice)
        result['smartpartition']=smartpartition

        if re.search(r'capabilities:thin_provisioning : true', extraSpecs):
        smartthin=shareType[0].checkSmartThin(shareName,extraSpecs,storageDevice)
        result['smartthin']=smartthin

        elif re.search(r'capabilities:thin_provisioning : ', extraSpecs):
        smartthick=shareType[0].checkSmartThick(shareName,extraSpecs,storageDevice)
        result['smartthick']=smartthick

        if re.search(r'capabilities:dedupe : true', extraSpecs):
        smartdedupe=shareType[0].checkSmartDedupe(shareName,extraSpecs,storageDevice)
        result['smartdedupe']=smartdedupe

        if re.search(r'capabilities:compression : true', extraSpecs):
        # smartcompression=shareType[0].checkSmartCompression(shareName,extraSpecs,storageDevice)
        smartcompression=True
        result['smartcompression']=smartcompression

        if re.search(r'capabilities:qos\ : true', extraSpecs):
        smartqos=shareType[0].checkSmartQos(shareName,extraSpecs,storageDevice)
        result['smartqos']=smartqos
        return result

        def createConsisGroup(self, volumeTypes, name=None, description=None, availabilityZone=None):

        """获得ConsisGroup对性的静态属性列表。

        Args:
        volumeTypes obj Volume types
        name str Name of a consistency group
        description str Description of a consistency group
        availabilityZone str Availability zone for volume

        """

        return ConsisGroup.create(self, volumeTypes, name, description, availabilityZone)

        def removeConsisGroup(self, consisGroups, force=None):

        """删除ConsisGroup。

        Args:
        consisGroups obj VolumeType Objects
        force str force remove

        """

        result=''
        for consisGroup in consisGroups:
        result = consisGroup.remove(force)
        return result

        def updateConsisGroup(self, consisGroup, name=None, description=None, addVolumes=None, removeVolumes=None):

        """获得ConsisGroup对性的静态属性列表。
        Args:
        consisGroup obj Name or ID of a consistency group
        name str New name for consistency group
        description str New description for consistency group
        addVolumes str UUID of one or more volumes to be added to the consistencygroup
        removeVolumes str UUID of one or more volumes to be removed to the consistencygroup

        """

        return consisGroup.update(consisGroup, name, description, addVolumes, removeVolumes)


        def getXmlfile(self, key, fileType, filename=None, filePath=None):
        """主机上配置Xml文件信息获取

        Args:
        key str Get key from file
        fileType str File type ('cinder'/'manila')
        filename str config filename
        filePath str config filepath

        Changes:
        2015-11-16 l00251491 Created
        """
        return Utility.getfile(self, key, fileType, filename, filePath)

        def changeCinderXml(self, key, value, filename=None, filePath=None):
        """用于修改/etc/cinder目录下的.xml配置文件

        Args:
        key str the key to be modified
        value str value of the key
        filename str config filename
        filePath str config filepath

        Changes:
        2015-11-10 g00289391 Created

        """
        return Utility.change(self, key, value, 'cinder', filename, filePath)

        def changeManilaXml(self, key, value, filename=None, filePath=None):
        """用于修改/etc/manila目录下的.xml配置文件

        Args:
        key str the key to be modified
        value str value of the key
        filename str config filename
        filePath str config filepath

        Changes:
        2015-11-10 g00289391 Created

        """
        return Utility.change(self, key, value, 'manila', filename, filePath)

        def rebootService(self, serviceType):
        """用于重启cinder或者manila服务

        Args:
        serviceType str serviceType, must be cinder or manila

        Changes:
        2015-11-19 g00289391 Created

        """
        return Utility.reboot(self, serviceType)

        def checkService(self, serviceType):
        """用于检查cinder或者manila服务状态是否正常

        Args:
        serviceType str serviceType, must be cinder or manila

        Changes:
        2015-11-19 g00289391 Created

        """
        return Utility.check(self, serviceType)

        def failoverReplica(self, object, tgt_id):

        """复制卷的倒换操作。

        Args:
        object obj volume
        Changes:
        2016-02-22 g00289391 Created
        """
        return object.failover(object, tgt_id)

        def failbackReplica(self, object, tgt_id):

        """复制卷的倒回操作。

        Args:
        object obj volume
        Changes:
        2016-02-22 g00289391 Created
        """
        return object.failback(object, tgt_id)

        def enableReplica(self, object):

        """启用复制卷。

        Args:
        object obj volume
        Changes:
        2016-02-22 g00289391 Created
        """
        return object.enable()

        def disableReplica(self, object):

        """停用复制卷。

        Args:
        object obj volume
        Changes:
        2016-02-22 g00289391 Created
        """
        return object.disable()

        def listtargetReplica(self, object):

        """获得可用作复制的后端列表，无可用后端时返回空。

        Args:
        object obj volume
        Changes:
        2012-02-22 g00289391 Created
        """
        return object.listtarget()

        def getpairidReplica(self, object):
        """获取复制pairid。

        Args:
        object obj volume
        Changes:
        2016-02-22 g00289391 Created
        """
        pair_info = object.getProperty('os-volume-replication:driver_data')
        pair_dict = eval(pair_info)
        pair_id = pair_dict['pair_id']
        return pair_id

        def getrmtidReplica(self, object):
        """获取复制远端lunid。

        Args:
        object obj volume

        Changes:
        2016-02-22 g00289391 Created
        """
        pair_info = object.getProperty('os-volume-replication:driver_data')
        pair_dict = eval(pair_info)
        rmt_lun_id = pair_dict['rmt_lun_id']
        return rmt_lun_id

        def setkeyVolumeType(self, vtype, key, value):
        """设置卷类型。

        Args:
        vtype obj Volumetype
        key str key of volumetype
        value str value of volumetype

        Changes:
        2016-02-22 g00289391 Created
        """
        return vtype.setkey(vtype, key, value)

        def resetVolume(self, volumes, state=None, attachStatus=None, migrationStatus=None):
        """重置volume或share状态为available。

        Args:
        objects list Volume or Share Objects

        Changes:
        2016-02-25 g00289391 Created
        """
        result = []
        for volume in volumes:
        result.append(volume.reset(state, attachStatus, migrationStatus))
        return result

        def resetObject(self, objects, state=None, attachStatus=None, migrationStatus=None):
        """重置volume或share状态为available。

        Args:
        objects list Volume or Share Objects

        Changes:
        2016-02-25 g00289391 Created
        """
        result = []
        for object in objects:
        result.append(object.reset(state, attachStatus, migrationStatus))
        return result

        def migrateVolume(self, object, host, forceHostCopy=None, lockVolume=None):

        """获得Volume对性的静态属性列表。

        Args:
        host str Cinder host on which the existing volume resides
        object obj Volume object

        """

        return Volume.migrate(object, host, forceHostCopy, lockVolume)

        def get_backend(self, device):
        # 后端名称
        cmdline = {
        'command': ['cinder', 'service-list',
        '| grep cinder-volume|grep up',
        "|awk '{print $4}'"]
        }
        res = device.run(cmdline)
        serv_lines = device.split(res['stdout'])
        backend = serv_lines[0]
        backendName = backend.split('@')[1]
        return backendName

        def get_file_path(self, device, backendName=None):
        if not backendName:
        backendName = self.get_backend(device)
        cmdline = {'command':
        [r"sed -n '/\["+backendName+r"\]/,/\[/p' /etc/cinder/cinder.conf |"
        r"awk -F = '/cinder_huawei_conf_file\s\=\s/{print $2}'"]}
        ret = device.run(cmdline)
        pathInfo = ret.get('stdout')
        path = pathInfo.lstrip()
        return path

        def waitDelFinish(self, device, delType, delTypeId=None, timeOut=6, seconds=2):
        """删除后判断删除是否完成。判断条件：如果没有删除完成等待30s，如果删除完成直接退出

        Args:
        delType str volume/share/volumeType/shareType/Intance.....
        device dev OpenStack/oceanStore/switch Device
        delTypeId str volume/share/volumeType/shareType/Intance..... ID
        """
        num = timeOut/seconds
        for i in range(0,num):
        if device.find(delType, forceSync=True):
        time.sleep(seconds)
        else:
        return True

        def initialOpenStack(self, OpenStackType, openStack, oceanStore=None, switch=None):
        """清理OpenStack环境。

        Args:
        OpenStackType str Cinder/Manila
        openStack dev OpenStack Device
        oceanStore dev oceanStore Device
        switch dev switch Device
        """

        """清理环境"""

        self.logger.info("Step 1 : Clean the system Start.")

        """删除快照"""
        if OpenStackType.lower()=='cinder':
        delSnapshot = openStack.find('volumesnapshot')
        if delSnapshot:
        openStack.removeSnapshot(delSnapshot)
        self.waitDelFinish (openStack, 'volumesnapshot', 30, 3)

        elif OpenStackType.lower()=='manila':
        delSnapshot = openStack.find('sharesnapshot')
        if delSnapshot:
        openStack.removeSnapshot(delSnapshot)
        self.waitDelFinish (openStack, 'sharesnapshot', 30, 3)
        else:
        self.logger.error('Error OpenStackType input error at the delSnapshot')

        """移除双活卷"""
        if OpenStackType.lower()=='cinder':
        consisGroups = openStack.find('consisGroup')
        if consisGroups:
        for consisGroup in consisGroups:
        volumes = openStack.find('volume', criteria={'consistencygroup_id' : consisGroup.getProperty('id')})
        for findVolume in volumes:
        openStack.updateConsisGroup(consisGroup, removeVolumes=findVolume.getProperty('id') )

        """解挂在卷"""
        if OpenStackType.lower()=='cinder':
        detachVolumes = openStack.find('volume')
        for detachVolume in detachVolumes:
        attachInfo = detachVolume.getProperties()
        if attachInfo['status'] == 'in-use':
        detachInstance = openStack.find('instance',
        criteria={'id' : eval(attachInfo['attachments'])[0]['server_id']})
        openStack.detachInstance(detachInstance[0], detachVolume)
        # try:
        # openStack.waitForPropertyValue([detachVolume], {'status' : 'available'}, timeout=120, interval=10)
        # except:
        # pass

        """删除卷"""
        if OpenStackType.lower()=='cinder':
        delVolume = openStack.find('volume')
        if delVolume:
        openStack.removeVolume(delVolume)
        self.waitDelFinish (openStack, 'volume')
        elif OpenStackType.lower()=='manila':
        delShare = openStack.find('share')
        if delShare:
        openStack.removeVolume(delShare)
        self.waitDelFinish (openStack, 'share')
        else:
        self.logger.error('Error OpenStackType input error at the delVolume/delShare')


        """删除一致性组"""
        if OpenStackType.lower()=='cinder':
        delConsisGroup = openStack.find('consisGroup')
        if delConsisGroup:
        openStack.removeConsisGroup(delConsisGroup, force='True')
        self.waitDelFinish (openStack, 'consisGroup')

        """删除卷类型 """
        if OpenStackType.lower()=='cinder':
        delVolumetype = openStack.find('volumeType')
        if delVolumetype:
        openStack.removeVolumeType(delVolumetype)
        self.waitDelFinish (openStack, 'volumeType')
        elif OpenStackType.lower()=='manila':
        delSharetype = openStack.find('shareType')
        if delSharetype:
        openStack.removeVolume(delSharetype)
        self.waitDelFinish (openStack, 'shareType')

        """清除后创建默认的shareType"""
        openStack.createShareType('default',specDriverHandlesShareServers='false',snapshotSupport='true')
        else:
        self.logger.error('Error OpenStackType input error at the delVolumetype/delSharetype')

        """删除Qos类型"""
        delQostype = openStack.find('qosType')
        if delQostype:
        openStack.removeQosType(delQostype)
        self.waitDelFinish (openStack, 'qosType')

        def setupEnableComponents(self):
        """此方法为内部方法，用于定义个'Nice name'映射到相应的component class

        Args:
        None.

        Returns:
        None.

        Raises:
        None.

        Examples:
        None.

        """
        self.addType('Volume', 'UniAutos.Component.Volume.Huawei.OpenStack.Volume')
        self.addType('Share', 'UniAutos.Component.OpenStackShare.Huawei.OpenStack.Share')
        self.addType('Snapshot', 'UniAutos.Component.OpenStackSnapshot.Huawei.OpenStack.Snapshot')
        self.addType('VolumeSnapshot', 'UniAutos.Component.OpenStackSnapshot.Huawei.VolumeSnapshot.VolumeSnapshot')
        self.addType('ShareSnapshot', 'UniAutos.Component.OpenStackSnapshot.Huawei.ShareSnapshot.ShareSnapshot')
        self.addType('Instance', 'UniAutos.Component.Instance.Huawei.OpenStack.Instance')
        self.addType('VolumeType', 'UniAutos.Component.VolumeType.Huawei.OpenStack.VolumeType')
        self.addType('ShareType', 'UniAutos.Component.ShareType.Huawei.OpenStack.ShareType')
        self.addType('QosType', 'UniAutos.Component.QosType.Huawei.OpenStack.QosType')
        self.addType('ConsisGroup', 'UniAutos.Component.ConsisGroup.Huawei.OpenStack.ConsisGroup')
        self.addType('ShareServer', 'UniAutos.Component.ShareServer.Huawei.OpenStack.ShareServer')
        return

===========================================================================================

OpenStack::

# !/usr/bin/python
# -*- coding: utf-8 -*-

"""
功 能: OpenStack management主机类, 提供主机操作相关接口，如: 创建分区， 创建文件系统等.
"""

import sys
import re
import uuid
import base64
import time

from UniAutos.Device.Host.Linux import Linux
from UniAutos.Exception.UniAutosException import UniAutosException
from UniAutos.Component.Volume.Huawei.OpenStack import Volume
from UniAutos.Component.OpenStackSnapshot.Huawei.OpenStack import Snapshot
from UniAutos.Component.OpenStackSnapshot.Huawei.ShareSnapshot import ShareSnapshot
from UniAutos.Component.OpenStackSnapshot.Huawei.VolumeSnapshot import VolumeSnapshot
from UniAutos.Component.OpenStackShare.Huawei.OpenStack import Share
from UniAutos.Component.Instance.Huawei.OpenStack import Instance
from UniAutos.Component.VolumeType.Huawei.OpenStack import VolumeType
from UniAutos.Component.QosType.Huawei.OpenStack import QosType
from UniAutos.Component.ShareType.Huawei.OpenStack import ShareType
from UniAutos.Component.OpenstackUtility.Huawei.OpenStack import Utility
from UniAutos.Component.ConsisGroup.Huawei.OpenStack import ConsisGroup
from UniAutos.Component.ShareServer.Huawei.OpenStack import ShareServer
from UniAutos.Util.Time import sleep


class OpenStack(Linux):


def __init__(self, username, password, params):
    """OpenStack management主机类，继承于Host类，该类主要包含OpenStack management主机相关操作于属性
    -下面的Components类属于Esx主机类，包含Nice Name与Component Class Name:

    Nice Name Component Class Name
    ================================================================
    TO be added

    -构造函数参数:
    Args:
    username (str): SRM登陆使用的用户名, 建议使用root用户.
    password (str): username的登陆密码.
    params (dict): 其他参数, 如下定义:
    params = {"protocol": (str),
    "port": (str),
    "ipv4_address": (str),
    "ipv6_address": (str),
    "os": (str),
    "type": (str)}
    params键值对说明:
    protocol (str): 通信协议，可选，取值范围:
    ["storSSH", "standSSH", "local", "telnet", "xml-rpc"]
    port (int): 通信端口，可选
    ipv4_address (str): 主机的ipv4地址，key与ipv6_address必选其一
    ipv6_address (str): 主机的ipv6地址，key与ipv4_address必选其一
    os (str): 主机操作系统类型，可选
    type (str): 连接的类型

    Returns:
    srmObj (instance): srmObj.

    Raises:
    None.

    Examples:
    None.

    """


super(OpenStack, self).__init__(username, password, params)

ipAddress = ""
if "ipv4_address" in params and params["ipv4_address"]:
    ipAddress = params["ipv4_address"]
elif "ipv6_address" in params and params["ipv6_address"]:
    ipAddress = params["ipv6_address"]
else:
raise UniAutosException("The IP address of SRM should be passed "
                        + "in while creating SRM device object")

group = re.match('http:\/\/(.*):.*', params['auth_url'], re.I)

if group:
    params['auth_url'].replace(group.group(1), ipAddress)

module = "UniAutos.Wrapper.Tool.OpenStack.OpenStack"
__import__(module)
moduleClass = getattr(sys.modules[module], "OpenStack")
openStackWrapperObj = moduleClass()
self.registerToolWrapper(host=self, wrapper=openStackWrapperObj)

for objType in self.classDict.itervalues():
    self.markDirty(objType)

self.testBedId = ''
self.os = 'OpenStack'


def _encode_name(self, id):
    pre_name = id.split("-")[0]


cmdline = {'command': ['echo', '"print ', 'hash(\'%s\')"' % id,
                       '| /usr/bin/python']}
res = self.run(cmdline)
vol_encoded = str(res['stdout'])
if vol_encoded.startswith('-'):
    newuuid = pre_name + vol_encoded
else:
    newuuid = pre_name + '-' + vol_encoded
return newuuid


# uuid_str = id.replace("-", "")
# vol_uuid = uuid.UUID('urn:uuid:%s' % uuid_str)
# vol_encoded = base64.urlsafe_b64encode(vol_uuid.bytes)
# newuuid = vol_encoded.replace("=", "")
# return newuuid

def encode_pyhermetro_cg_name(self, id):
    newuuid = self._encode_name(id)


return newuuid


def createVolume(self, size, name=None, volumeType=None, sourceVolid=None, snapshotId=None,
                 imageId=None, description=None, availabilityZone=None, metadata=None):


"""获得Volume对性的静态属性列表。

Args:
volumeId str Volume id
name str Volume name
size str Volume size
volumeType str Volume type
sourceVolid str Creates volume from volume ID
snapshotId str Creates volume from snapshot ID
imageId str Creates volume from image ID
description str Volume description
availabilityZone str Availability zone for volume
metadata str Metadata key and value pairs
replication_status str Replication status
replica_driver_data str Replication pair id and remote lun id

"""

return Volume.create(self, size, name, volumeType, sourceVolid, snapshotId, imageId,
                     description, availabilityZone, metadata)


def createImage(self, object, name=None, diskformat=None):


"""获得Volume对性的静态属性列表。

Args:
name Str Image name
diskformat Str Format type

"""

return object.createImage(name, diskformat)


def removeVolume(self, volumes, force=None):


"""获得Volume的静态属性列表。

Args:
volumes objects Volume Objects

Changes:
2015-10-16 l00251491 Created
"""

result = ''
for volume in volumes:
    result = volume.remove(force)
return result


def extendVolume(self, object, extendSize):


"""获得Volume对性的静态属性列表。

Args:
object Object Volume Object
extendSize str Volume extend size

"""

return object.extend(extendSize)


def manageVolume(self, host, identifier, idType=None, name=None, description=None, volumeType=None,
                 availabilityZone=None, metadata=None, bootable=None):


"""获得Volume对性的静态属性列表。

Args:
host str Cinder host on which the existing volume resides
identifier str Name or other Identifier for existing volume
idType str Type of backend device identifier provided
name str Volume name (Default=None)
description str Volume description (Default=None)
volumeType str Volume type (Default=None)
availabilityZone str Availability zone for volume
metadata str Metadata key=value pairs (Default=None)
bootable str Specifies that the newly created volume should be marked as bootable

"""

return Volume.manage(self, host, identifier, idType, name, description, volumeType,
                     availabilityZone, metadata, bootable)


def unmanageVolume(self, object):


"""获得 Share 对性的静态属性列表。

Args:
object obj Volume

"""

return object.unmanage(object)


def createSnapshot(self, object, objectId=None, objectName=None, name=None,
                   force=None, description=None, metadata=None):


"""获得Snapshot对性的静态属性列表。

Args:
object obj Volume/Share
objectId str Volume id/Share id
objectName str Volume name/Share name
name str Snapshot name
force str Snapshot type
description str Snapshot description
metadata str Metadata key and value pairs

"""
object_pros = object.getProperties()
if object_pros.get('share_proto'):
    return ShareSnapshot.create(self, object, objectId, objectName,
                                name, force, description, metadata)
else:
    return VolumeSnapshot.create(self, object, objectId, objectName,
                                 name, force, description, metadata)


def removeSnapshot(self, snapshots):


"""获得Snapshot的静态属性列表。

Args:
volumes objects Volume Objects

Changes:
2015-10-16 l00251491 Created
"""

result = ''
for snapshot in snapshots:
    result = snapshot.remove()
return result


def manageSnapshot(self, object, identifier, idType=None, name=None, description=None, metadata=None):


"""获得Snapshot对性的静态属性列表。

Args:
object obj Volume or Share object
identifier str Name or other Identifier for existing Snapshot
idType str Type of backend device identifier provided
name str Snapshot name (Default=None)
description str Snapshot description (Default=None)
metadata str Metadata key=value pairs (Default=None)
"""

object_pros = object.getProperties()
if object_pros.get('share_proto'):
    return ShareSnapshot.manage(self, object, identifier, idType, name, description, metadata)
else:
    return VolumeSnapshot.manage(self, object, identifier, idType, name, description, metadata)


def unmanageSnapshot(self, objectType, object, identifier=None):


"""获得 Snapshot 对性的静态属性列表。

Args:
object obj Snapshot
objectType str cinder/manila

"""

return object.unmanage(object, identifier)


def createShare(self, shareProtocol, size, name=None, shareType=None, snapshotId=None, shareNetwork=None, public=None,
                description=None, availabilityZone=None, metadata=None, consistencyGroup=None):


"""获得Share对性的静态属性列表。

Args:
Share_id str Share id
name str Share name
size str Share size
shareProtocol str Share use protocol
shareType str Share type
shareNetwork str Optional network info ID or name
snapshotId str Creates share from snapshot ID
consistencyGroup str Optional consistency group name or ID in which to create the share
description str Share description
availabilityZone str Availability zone for Share
metadata str Metadata key and value pairs
public str Level of visibility for share

"""

return Share.create(self, shareProtocol, size, name, shareType, snapshotId, shareNetwork, public,
                    description, availabilityZone, metadata, consistencyGroup)


def removeShare(self, shares):


"""获得 Share 的静态属性列表。

Args:
shares objects Share Objects

Changes:
2015-10-23 l00251491 Created
"""

result = ''
for share in shares:
    result = share.remove()
return result


def removeShareServer(self, shareServers):


"""获得 Share 的静态属性列表。

Args:
shares objects Share Objects

Changes:
2015-12-08 h00248497 Created
"""

result = ''
for shareServer in shareServers:
    result = shareServer.remove()
return result


def extendShare(self, object, extendSize):


"""获得 Share 对性的静态属性列表。

Args:
object Object Share Object
extendSize str Share extend size

"""

return object[0].extend(extendSize)


def shrinkShare(self, object, shrinkSize):


"""获得 Share 对性的静态属性列表。

Args:
object Object Share Object
shrinkSize str Share shrink size

"""

return object[0].shrink(shrinkSize)


def manageShare(self, serviceHost, protocol, exportPath, name=None, shareType=None, description=None,
                driverOptions=None):


"""获得 Share 对性的静态属性列表。

Args:
serviceHost str manage-share service host
protocol str Protocol of the share to manage
exportPath str Share export path
name str Optional share name
shareType str Optional share type assigned to share
description str Optional share description
driverOptions str Driver option key=value pairs

"""

return Share.manage(self, serviceHost, protocol, exportPath, name, shareType, description, driverOptions)


def unmanageShare(self, object):


"""获得 Share 对性的静态属性列表。

Args:
object obj Share

"""

return object.unmanage(object)


def resetShare(self, objects):
    """重置volume或share状态为available。

    Args:
    objects list Volume or Share Objects

    Changes:
    2016-02-25 g00289391 Created
    """


result = ''
for object in objects:
    result = object.reset()
return result


def allowAccess(self, share, accessType, accessTo, accessLevel=None):


"""获得 Share 对性的静态属性列表。

Args:
share str Share object
accessType str Access rule type
accessTo str Value that defines access
accessLevel str Share access level

"""

return share.allow(share, accessType, accessTo, accessLevel)


def denyAccess(self, share, id):


"""获得 Share 对性的静态属性列表。

Args:
share str Share object
id str ID of the access rule to be deleted

"""

return share.deny(share, id)


def createInstance(self, name, flavor, image, imageWith=None, bootVolume=None, snapshot=None, minCount=None,
                   maxCount=None, meta=None, file=None, keyName=None, userData=None, availabilityZone=None,
                   securityGroups=None,
                   blockDeviceMapping=None, blockDevice=None, swap=None, ephemeral=None, hint=None, nic=None,
                   configDrive=None,
                   poll=None, adminPass=None):
    """获得 Instance 对性的静态属性列表。

    Args:
    id str Instance id
    name str Instance name
    flavor str Create instance use the flavor Name or ID
    image str Create instance use the image Name or ID
    imageWith str Image metadata property
    bootVolume str Volume ID to boot from
    snapshot str Snapshot ID to boot from
    minCount str Boot at least servers
    maxCount str Boot up to servers
    meta str Record arbitrary key/value metadata to /meta_data.json on the metadata server
    file str Store arbitrary files from locally to on the new server
    keyName str Key name of keypair that should be created earlier with the command keypair-add
    userData str user data file to pass to be exposed by the metadata server
    availabilityZone str The availability zone for server placement
    securityGroups str Comma separated list of security group names
    blockDeviceMapping str Block device mapping in the format
    blockDevice str Block device mapping with the keys
    swap str Create and attach a local swap block device
    ephemeral str Create and attach a local ephemeral block
    hint str Send arbitrary key/value pairs to the scheduler for custom use
    nic str Create a NIC on the server
    configDrive str Enable config drive
    poll str Report the new server boot progress until it completes
    adminPass str Admin password for the instance

    Returns:

    Raises:

    Examples:
    None

    Changes:
    2015-10-26 l00251491 Created

    """


return Instance.create(self, name, flavor, image, imageWith, bootVolume, snapshot, minCount, maxCount,
                       meta, file, keyName, userData, availabilityZone, securityGroups, blockDeviceMapping, blockDevice,
                       swap, ephemeral, hint, nic, configDrive, poll, adminPass)


def terminateInstance(self, instances):


"""获得 Instance 的静态属性列表。

Args:
instances objects Instance Objects

Changes:
2015-10-26 l00251491 Created
"""

result = ''
for instance in instances:
    result = instance.terminate()
return result

def attachInstance(self, server, volume, device=None):
"""在主机上下发命令挂载卷
Args:
server Instance Name or ID of server
volume Volume ID of the volume to attach
device str Name of the device
"""

return server.attach(server, volume, device)

def detachInstance(self, server, volume):
"""在主机上下发命令挂载卷
Args:
server Instance Name or ID of server
volume Volume ID of the volume to attach
"""

return server.detach(server, volume)

def checkZone(self, host, switch, storage):
"""用于检查挂载卷后智能划域是否正常

Args:
host obj Host device
switch obj Switch device
storage obj Storage device

Changes:
2015-11-28 l00251491 Created

"""
return Instance.check(self, host, switch, storage)

def createVolumeType(self, name, isPublic=None, description=None):

"""获得VolumeType对性的静态属性列表。

Args:
name str VolumeType name
isPublic str Make type accessible to the public (default true)
description str Description of new volume type

"""

return VolumeType.create(self, name, isPublic, description)

def removeVolumeType(self, volumetypes):

"""获得VolumeType对性的静态属性列表。

Args:
volumetypes str VolumeType Objects

"""

result = ''
for volumetype in volumetypes:
result = volumetype.remove()
return result

def linkSmartTier(self, vtype, action, capkey=None, capvalue=None, attributekey=None, attributevalue=None):

"""新增VolumeType属性列表。

Args:
vtype str VolumeType obj
action str The action
capkey str Capabilities Key
capvalue str Capabilities Value
attributekey str Attribute Key
attributevalue str Attribute Value

"""

if ((capkey is None and capvalue) or (capkey and capvalue is None)
or (attributekey is None and attributevalue) or (attributekey and attributevalue is None )):
self.logger.info('Error capabilities input error')
return "ERROR"
return vtype.useSmartx(vtype, action, capkey, capvalue, attributekey, attributevalue)

def unlinkSmartTier(self, vtype, action, capkey=None, capvalue=None, attributekey=None, attributevalue=None):

""" 移除VolumeType属性列表。

Args:
vtype str VolumeType obj
action str The action
capkey str Capabilities Key
capvalue str Capabilities Value
attributekey str Attribute Key
attributevalue str Attribute Value

"""

if ((capkey is None and capvalue) or (capkey and capvalue is None)
or (attributekey is None and attributevalue) or (attributekey and attributevalue is None )):
self.logger.info('Error capabilities input error')
return "ERROR"

return vtype.useSmartx(vtype, action, capkey, capvalue, attributekey, attributevalue)

def changeSmartTier(self, vtype, action, capkey=None, capvalue=None, attributekey=None, attributevalue=None):

"""修改VolumeType属性列表。

Args:
vtype str VolumeType obj
action str The action
capkey str Capabilities Key
capvalue str Capabilities Value
attributekey str Attribute Key
attributevalue str Attribute Value

"""

if ((capkey is None and capvalue) or (capkey and capvalue is None)
or (attributekey is None and attributevalue) or (attributekey and attributevalue is None )):
self.logger.info('Error capabilities input error')
return "ERROR"

return vtype.useSmartx(vtype, action, capkey, capvalue, attributekey, attributevalue)

def linkSmartCache(self, vtype, action, capkey=None, capvalue=None, attributekey=None, attributevalue=None):

"""新增VolumeType属性列表。

Args:
vtype str VolumeType obj
action str The action
capkey str Capabilities Key
capvalue str Capabilities Value
attributekey str Attribute Key
attributevalue str Attribute Value

"""

if ((capkey is None and capvalue) or (capkey and capvalue is None)
or (attributekey is None and attributevalue) or (attributekey and attributevalue is None )):
self.logger.info('Error capabilities input error')
return "ERROR"

return vtype.useSmartx(vtype, action, capkey, capvalue, attributekey, attributevalue)

def unlinkSmartCache(self, vtype, action, capkey=None, capvalue=None, attributekey=None, attributevalue=None):

""" 移除VolumeType属性列表。

Args:
vtype str VolumeType obj
action str The action
capkey str Capabilities Key
capvalue str Capabilities Value
attributekey str Attribute Key
attributevalue str Attribute Value

"""

if ((capkey is None and capvalue) or (capkey and capvalue is None)
or (attributekey is None and attributevalue) or (attributekey and attributevalue is None )):
self.logger.info('Error capabilities input error')
return "ERROR"

return vtype.useSmartx(vtype, action, capkey, capvalue, attributekey, attributevalue)

def changeSmartCache(self, vtype, action, capkey=None, capvalue=None, attributekey=None, attributevalue=None):

"""修改VolumeType属性列表。

Args:
vtype str VolumeType obj
action str The action
capkey str Capabilities Key
capvalue str Capabilities Value
attributekey str Attribute Key
attributevalue str Attribute Value

"""

if ((capkey is None and capvalue) or (capkey and capvalue is None)
or (attributekey is None and attributevalue) or (attributekey and attributevalue is None )):
self.logger.info('Error capabilities input error')
return "ERROR"

return vtype.useSmartx(vtype, action, capkey, capvalue, attributekey, attributevalue)

def linkSmartPartition(self, vtype, action, capkey=None, capvalue=None, attributekey=None, attributevalue=None):

"""新增VolumeType属性列表。

Args:
vtype str VolumeType obj
action str The action
capkey str Capabilities Key
capvalue str Capabilities Value
attributekey str Attribute Key
attributevalue str Attribute Value

"""

if ((capkey is None and capvalue) or (capkey and capvalue is None)
or (attributekey is None and attributevalue) or (attributekey and attributevalue is None )):
self.logger.info('Error capabilities input error')
return "ERROR"

return vtype.useSmartx(vtype, action, capkey, capvalue, attributekey, attributevalue)

def unlinkSmartPartition(self, vtype, action, capkey=None, capvalue=None, attributekey=None, attributevalue=None):

""" 移除VolumeType属性列表。

Args:
vtype str VolumeType obj
action str The action
capkey str Capabilities Key
capvalue str Capabilities Value
attributekey str Attribute Key
attributevalue str Attribute Value

"""

if ((capkey is None and capvalue) or (capkey and capvalue is None)
or (attributekey is None and attributevalue) or (attributekey and attributevalue is None )):
self.logger.info('Error capabilities input error')
return "ERROR"

return vtype.useSmartx(vtype, action, capkey, capvalue, attributekey, attributevalue)

def changeSmartPartition(self, vtype, action, capkey=None, capvalue=None, attributekey=None, attributevalue=None):

"""修改VolumeType属性列表。

Args:
vtype str VolumeType obj
action str The action
capkey str Capabilities Key
capvalue str Capabilities Value
attributekey str Attribute Key
attributevalue str Attribute Value

"""

if ((capkey is None and capvalue) or (capkey and capvalue is None)
or (attributekey is None and attributevalue) or (attributekey and attributevalue is None )):
self.logger.info('Error capabilities input error')
return "ERROR"

return vtype.useSmartx(vtype, action, capkey, capvalue, attributekey, attributevalue)

def linkSmartThin(self, vtype, action, capkey=None, capvalue=None, attributekey=None, attributevalue=None):

"""新增VolumeType属性列表。

Args:
vtype str VolumeType obj
action str The action
capkey str Capabilities Key
capvalue str Capabilities Value
attributekey str Attribute Key
attributevalue str Attribute Value

"""

if ((capkey is None and capvalue) or (capkey and capvalue is None)
or (attributekey is None and attributevalue) or (attributekey and attributevalue is None )):
self.logger.info('Error capabilities input error')
return "ERROR"

return vtype.useSmartx(vtype, action, capkey, capvalue, attributekey, attributevalue)

def unlinkSmartThin(self, vtype, action, capkey=None, capvalue=None, attributekey=None, attributevalue=None):

""" 移除VolumeType属性列表。

Args:
vtype str VolumeType obj
action str The action
capkey str Capabilities Key
capvalue str Capabilities Value
attributekey str Attribute Key
attributevalue str Attribute Value

"""

if ((capkey is None and capvalue) or (capkey and capvalue is None)
or (attributekey is None and attributevalue) or (attributekey and attributevalue is None )):
self.logger.info('Error capabilities input error')
return "ERROR"

return vtype.useSmartx(vtype, action, capkey, capvalue, attributekey, attributevalue)

def changeSmartThin(self, vtype, action, capkey=None, capvalue=None, attributekey=None, attributevalue=None):

"""修改VolumeType属性列表。

Args:
vtype str VolumeType obj
action str The action
capkey str Capabilities Key
capvalue str Capabilities Value
attributekey str Attribute Key
attributevalue str Attribute Value

"""

if ((capkey is None and capvalue) or (capkey and capvalue is None)
or (attributekey is None and attributevalue) or (attributekey and attributevalue is None )):
self.logger.info('Error capabilities input error')
return "ERROR"

return vtype.useSmartx(vtype, action, capkey, capvalue, attributekey, attributevalue)

def linkSmartThick(self, vtype, action, capkey=None, capvalue=None, attributekey=None, attributevalue=None):

"""新增VolumeType属性列表。

Args:
vtype str VolumeType obj
action str The action
capkey str Capabilities Key
capvalue str Capabilities Value
attributekey str Attribute Key
attributevalue str Attribute Value

"""

if ((capkey is None and capvalue) or (capkey and capvalue is None)
or (attributekey is None and attributevalue) or (attributekey and attributevalue is None )):
self.logger.info('Error capabilities input error')
return "ERROR"

return vtype.useSmartx(vtype, action, capkey, capvalue, attributekey, attributevalue)

def unlinkSmartThick(self, vtype, action, capkey=None, capvalue=None, attributekey=None, attributevalue=None):

""" 移除VolumeType属性列表。

Args:
vtype str VolumeType obj
action str The action
capkey str Capabilities Key
capvalue str Capabilities Value
attributekey str Attribute Key
attributevalue str Attribute Value

"""

if ((capkey is None and capvalue) or (capkey and capvalue is None)
or (attributekey is None and attributevalue) or (attributekey and attributevalue is None )):
self.logger.info('Error capabilities input error')
return "ERROR"

return vtype.useSmartx(vtype, action, capkey, capvalue, attributekey, attributevalue)

def changeSmartThick(self, vtype, action, capkey=None, capvalue=None, attributekey=None, attributevalue=None):

"""修改VolumeType属性列表。

Args:
vtype str VolumeType obj
action str The action
capkey str Capabilities Key
capvalue str Capabilities Value
attributekey str Attribute Key
attributevalue str Attribute Value

"""

if ((capkey is None and capvalue) or (capkey and capvalue is None)
or (attributekey is None and attributevalue) or (attributekey and attributevalue is None )):
self.logger.info('Error capabilities input error')
return "ERROR"
return vtype.useSmartx(vtype, action, capkey, capvalue, attributekey, attributevalue)

def createQosType(self, name, keyValueArg):

"""创建VolumeType属性列表。

Args:
name str QosType name
keyValueArg dict {'key':'value','key':'value',...}

"""
typecnt=0
for key in keyValueArg:
if (key is None and keyValueArg[key]) or (key and keyValueArg[key]is None):
self.logger.info('Error capabilities input error')
return "ERROR"
if key == 'IOType':
typecnt+=1
if typecnt>1:
self.logger.info('Error IOType params input %d times ' % typecnt)
return "ERROR"

return QosType.create(self, name, keyValueArg)

def changeQosType(self, object, action, keyValueArg):

"""修改QosType属性列表。

Args:
object obj QosType Object
action str QosType Change type
keyValueArg dict {'key':'value','key':'value',...}

"""
typecnt=0
for key in keyValueArg:
if (key is None and keyValueArg[key]) or (key and keyValueArg[key]is None):
self.logger.info('Error params the key or value input error')
return "ERROR"
if key == 'IOType':
typecnt+=1
if typecnt>1:
self.logger.info('Error IOType params input %d times ' % typecnt)
return "ERROR"

return object.change(object, action, keyValueArg)

def linkShareQosType(self, shareType, action, capkey=None, capvalue=None, keyValueArg=None):

"""创建VolumeType属性列表。

Args:
shareType obj shareType Object
action str The action
capkey str Capabilities Key
capvalue str Capabilities Value
keyValueArg dict {'key':'value','key':'value',...}

"""
typecnt=0
if (capkey is None and capvalue) or (capkey and capvalue is None):
self.logger.info('Error capabilities input error')
return "ERROR"
for key in keyValueArg:
if (key is None and keyValueArg[key]) or (key and keyValueArg[key]is None):
self.logger.info('Error capabilities input error')
return "ERROR"
if key == 'IOType':
typecnt+=1
if typecnt>1:
self.logger.info('Error IOType params input %d times ' % typecnt)
return "ERROR"

return shareType.useSmartx(shareType, action, capkey, capvalue, keyValueArg=keyValueArg)

def unlinkQosType(self, object, action, keyValueArg):

"""修改QosType属性列表。

Args:
object obj QosType Object
action str QosType Change type
keyValueArg dict {'key':'value','key':'value',...}

"""
typecnt=0
for key in keyValueArg:
if (key is None and keyValueArg[key]) or (key and keyValueArg[key]is None):
self.logger.info('Error params the key or value input error')
return "ERROR"
if key == 'IOType':
typecnt+=1
if typecnt>1:
self.logger.info('Error IOType params input %d times ' % typecnt)
return "ERROR"

return object.change(object, action, keyValueArg)

def removeQosType(self, qostypes):

"""获得VolumeType对性的静态属性列表。

Args:
qostypes obj VolumeType Objects

"""

result=''
for qostype in qostypes:
result = qostype.remove()
return result

def associateQosType(self, qosType, volumeType):
"""绑定VolumeType与QoSType。

Args:
qosType obj QosType Objects
volumeType obj VolumeType Objects
"""
return qosType.associate(qosType, volumeType)

def disassociateQosType(self, qosType, volumeType):
"""绑定VolumeType与QoSType。

Args:
qosType obj QosType Objects
volumeType obj VolumeType Objects
"""
return qosType.disassociate(qosType, volumeType)

def findAssociateQosType(self, volumeType):
"""通过VolumeType查询到绑定的QoSType。

Args：
volumeType obj VolumeType Objects
"""

qosTypes=self.find('qostype')
for qosType in qosTypes:
associate=qosType.findAssociate(qosType)
if associate and volumeType.getProperties().get('id')==associate[0].get('id'):
return qosType
self.logger.info('The VolumeType not associate the QosType')
return None

def linkHyperMetro(self, vtype, action, capkey=None, capvalue=None, attributekey=None, attributevalue=None):

"""修改VolumeType属性列表。

Args:
vtype str VolumeType obj
action str The action
capkey str Capabilities Key
capvalue str Capabilities Value
attributekey str Attribute Key
attributevalue str Attribute Value

"""

if ((capkey is None and capvalue) or (capkey and capvalue is None)
or (attributekey is None and attributevalue) or (attributekey and attributevalue is None )):
self.logger.info('Error capabilities input error')
return "ERROR"
return vtype.useSmartx(vtype, action, capkey, capvalue, attributekey, attributevalue)

def unlinkHyperMetro(self, vtype, action, capkey=None, capvalue=None, attributekey=None, attributevalue=None):

"""修改VolumeType属性列表。

Args:
vtype str VolumeType obj
action str The action
capkey str Capabilities Key
capvalue str Capabilities Value
attributekey str Attribute Key
attributevalue str Attribute Value

"""

if ((capkey is None and capvalue) or (capkey and capvalue is None)
or (attributekey is None and attributevalue) or (attributekey and attributevalue is None )):
self.logger.info('Error capabilities input error')
return "ERROR"
return vtype.useSmartx(vtype, action, capkey, capvalue, attributekey, attributevalue)

def checkVolumeType(self,object,storageDevice):
"""检查Volume具有的Volume属性在阵列上是否具有。

Args:
object Volume Volume Objects
storageDevice Device OceaStore Device

Returns:
{key:True/False,key:True/False,....}

Raises:
None

Changes:
2015-11-04 l00251491 Created
"""

result={}
extraSpecs=''
volume_info=object.getProperties()
volumeTypeName = volume_info.get('volume_type')
volumeId=object.getProperties().get('id')
lunName=self._encode_name(volumeId)

if volumeTypeName:
volumeType=self.find('volumetype', criteria={'name' : volumeTypeName})
extra_info=volumeType[0].getProperties()
extraSpecs=extra_info['extra_specs']

if extraSpecs != '{}':
extraSpecs = re.sub("u'", "'", extraSpecs)
else:
path = self.get_file_path(self)
file = self.getXmlfile('LUNType', 'cinder', filePath=path)
result=volumeType[0].checkSmartXNULL(lunName, file.get('LUNType'), storageDevice)

Lun=storageDevice.find('lun', criteria={'name' : lunName}, forceSync=True)[0]

if re.search(r'capabilities:smarttier\': \' true', extraSpecs):
smarttier=volumeType[0].checkSmartTier(Lun,extraSpecs,storageDevice)
result['smarttier']=smarttier

if re.search(r'capabilities:smartcache\': \' true', extraSpecs):
smartcache=volumeType[0].checkSmartCache(Lun,extraSpecs,storageDevice)
result['smartcache']=smartcache

if re.search(r'capabilities:smartpartition\': \' true', extraSpecs):
smartpartition=volumeType[0].checkSmartPartition(Lun,extraSpecs,storageDevice)
result['smartpartition']=smartpartition

if re.search(r'capabilities:thin_provisioning_support\': \' true', extraSpecs):
if re.search(r'capabilities:thick_provisioning_support\': \' true', extraSpecs):
self.logger.error('SmartThin and SmartThick can not exist on the same time')
smartthin=volumeType[0].checkSmartThin(Lun,extraSpecs,storageDevice)
result['smartthin']=smartthin

if re.search(r'capabilities:thick_provisioning_support\': \' true', extraSpecs):
if re.search(r'capabilities:thin_provisioning_support\': \' true', extraSpecs):
self.logger.error('SmartThick and SmartThin can not exist on the same time')
smartthick=volumeType[0].checkSmartThick(Lun,extraSpecs,storageDevice)
result['smartthick']=smartthick

if not result:
path = self.get_file_path(self)
file = self.getXmlfile('LUNType', 'cinder', filePath=path)
result=volumeType[0].checkSmartXNULL(lunName, file.get('LUNType'), storageDevice)

qosType=self.findAssociateQosType(volumeType[0])
specs = ''
if qosType:
specs=qosType.getProperties()['specs']
if specs:
smartqos = True
specs = re.sub("u'", "'", specs)
smartqos=qosType.checkSmartQos(lunName,specs,storageDevice)
self.logger.info('SmartQos not achieve on the OceanStore\'s Autos')
result['smartqos']=smartqos
return result

def retypeVolume(self, object, objecttype, migrationPolicy=None):
"""获得VolumeType对性的静态属性列表。

Args:
object obj Volume object
objecttype obj Volume Type object
migrationPolicy str Migration policy during retype of volume

"""

return object.retype(object, objecttype, migrationPolicy)

def createShareType(self, name, specDriverHandlesShareServers, isPublic=None, snapshotSupport=None):

"""获得ShareType对性的静态属性列表。

Args:
name str ShareType name
specDriverHandlesShareServers str Required extra specification
isPublic str Make type accessible to the public
snapshotSupport str Description of new share type

"""

return ShareType.create(self, name, specDriverHandlesShareServers, isPublic, snapshotSupport)

def removeShareType(self, sharetypes):

"""获得VolumeType对性的静态属性列表。

Args:
volumetypes str VolumeType Objects

"""

result = ''
for sharetype in sharetypes:
result = sharetype.remove()
return result



def linkSmartDedupe(self, vtype, action, capkey=None, capvalue=None, attributekey=None, attributevalue=None):

"""新增VolumeType属性列表。

Args:
vtype str VolumeType obj
action str The action
capkey str Capabilities Key
capvalue str Capabilities Value
attributekey str Attribute Key
attributevalue str Attribute Value

"""

if ((capkey is None and capvalue) or (capkey and capvalue is None)
or (attributekey is None and attributevalue) or (attributekey and attributevalue is None )):
self.logger.info('Error capabilities input error')
return "ERROR"

return vtype.useSmartx(vtype, action, capkey, capvalue, attributekey, attributevalue)

def unlinkSmartDedupe(self, vtype, action, capkey=None, capvalue=None, attributekey=None, attributevalue=None):

""" 移除VolumeType属性列表。

Args:
vtype str VolumeType obj
action str The action
capkey str Capabilities Key
capvalue str Capabilities Value
attributekey str Attribute Key
attributevalue str Attribute Value

"""

if ((capkey is None and capvalue) or (capkey and capvalue is None)
or (attributekey is None and attributevalue) or (attributekey and attributevalue is None )):
self.logger.info('Error capabilities input error')
return "ERROR"

return vtype.useSmartx(vtype, action, capkey, capvalue, attributekey, attributevalue)

def changeSmartDedupe(self, vtype, action, capkey=None, capvalue=None, attributekey=None, attributevalue=None):

"""修改VolumeType属性列表。

Args:
vtype str VolumeType obj
action str The action
capkey str Capabilities Key
capvalue str Capabilities Value
attributekey str Attribute Key
attributevalue str Attribute Value

"""

if ((capkey is None and capvalue) or (capkey and capvalue is None)
or (attributekey is None and attributevalue) or (attributekey and attributevalue is None )):
self.logger.info('Error capabilities input error')
return "ERROR"

return vtype.useSmartx(vtype, action, capkey, capvalue, attributekey, attributevalue)

def linkSmartCompression(self, vtype, action, capkey=None, capvalue=None, attributekey=None, attributevalue=None):

"""新增VolumeType属性列表。

Args:
vtype str VolumeType obj
action str The action
capkey str Capabilities Key
capvalue str Capabilities Value
attributekey str Attribute Key
attributevalue str Attribute Value

"""

if ((capkey is None and capvalue) or (capkey and capvalue is None)
or (attributekey is None and attributevalue) or (attributekey and attributevalue is None )):
self.logger.info('Error capabilities input error')
return "ERROR"

return vtype.useSmartx(vtype, action, capkey, capvalue, attributekey, attributevalue)

def unlinkSmartCompression(self, vtype, action, capkey=None, capvalue=None, attributekey=None, attributevalue=None):

""" 移除VolumeType属性列表。

Args:
vtype str VolumeType obj
action str The action
capkey str Capabilities Key
capvalue str Capabilities Value
attributekey str Attribute Key
attributevalue str Attribute Value

"""

if ((capkey is None and capvalue) or (capkey and capvalue is None)
or (attributekey is None and attributevalue) or (attributekey and attributevalue is None )):
self.logger.info('Error capabilities input error')
return "ERROR"

return vtype.useSmartx(vtype, action, capkey, capvalue, attributekey, attributevalue)

def changeSmartCompression(self, vtype, action, capkey=None, capvalue=None, attributekey=None, attributevalue=None):

"""修改VolumeType属性列表。

Args:
vtype str VolumeType obj
action str The action
capkey str Capabilities Key
capvalue str Capabilities Value
attributekey str Attribute Key
attributevalue str Attribute Value

"""

if ((capkey is None and capvalue) or (capkey and capvalue is None)
or (attributekey is None and attributevalue) or (attributekey and attributevalue is None )):
self.logger.info('Error capabilities input error')
return "ERROR"
return vtype.useSmartx(vtype, action, capkey, capvalue, attributekey, attributevalue)

def checkShareType(self,object,storageDevice):
"""检查ShareType具有的ShareType属性在阵列上是否具有。

Args:
object Share Share Objects
storageDevice Device OceaStore Device

Returns:
{key:True/False,key:True/False,....}

Raises:
None

Changes:
2015-11-04 l00251491 Created
"""


share = object.getProperties()
shareTypeId = share.get('share_type')
shareId = share.get('id')
shareInfo = self.find('share',criteria={'id' : shareId})[0]
shareLocation = shareInfo.getProperty('export_locations')
shareLocationList = shareLocation.split(',')
sharePath = ''
for key in shareLocationList:
if '\\' in key or '/' in key:
sharePath = key
shareStorageId = sharePath.split("share")[1]
shareName = "share"+shareStorageId
result={}
if shareTypeId:
shareType=self.find('sharetype', criteria={'id' : shareTypeId})
extraSpecs=shareType[0].getProperties()['all_extra_specs']

extraSpecs = re.sub("u'", "'", extraSpecs)

if re.search(r'capabilities:huawei_smarttier : true', extraSpecs):
smarttier=shareType[0].checkSmartTier(shareName,extraSpecs,storageDevice)
result['smarttier']=smarttier

if re.search(r'capabilities:huawei_smartcache : true', extraSpecs):
smartcache=shareType[0].checkSmartCache(shareName,extraSpecs,storageDevice)
result['smartcache']=smartcache

if re.search(r'capabilities:huawei_smartpartition : true', extraSpecs):
smartpartition=shareType[0].checkSmartPartition(shareName,extraSpecs,storageDevice)
result['smartpartition']=smartpartition

if re.search(r'capabilities:thin_provisioning : true', extraSpecs):
smartthin=shareType[0].checkSmartThin(shareName,extraSpecs,storageDevice)
result['smartthin']=smartthin

elif re.search(r'capabilities:thin_provisioning : ', extraSpecs):
smartthick=shareType[0].checkSmartThick(shareName,extraSpecs,storageDevice)
result['smartthick']=smartthick

if re.search(r'capabilities:dedupe : true', extraSpecs):
smartdedupe=shareType[0].checkSmartDedupe(shareName,extraSpecs,storageDevice)
result['smartdedupe']=smartdedupe

if re.search(r'capabilities:compression : true', extraSpecs):
# smartcompression=shareType[0].checkSmartCompression(shareName,extraSpecs,storageDevice)
smartcompression=True
result['smartcompression']=smartcompression

if re.search(r'capabilities:qos\ : true', extraSpecs):
smartqos=shareType[0].checkSmartQos(shareName,extraSpecs,storageDevice)
result['smartqos']=smartqos
return result

def createConsisGroup(self, volumeTypes, name=None, description=None, availabilityZone=None):

"""获得ConsisGroup对性的静态属性列表。

Args:
volumeTypes obj Volume types
name str Name of a consistency group
description str Description of a consistency group
availabilityZone str Availability zone for volume

"""

return ConsisGroup.create(self, volumeTypes, name, description, availabilityZone)

def removeConsisGroup(self, consisGroups, force=None):

"""删除ConsisGroup。

Args:
consisGroups obj VolumeType Objects
force str force remove

"""

result=''
for consisGroup in consisGroups:
result = consisGroup.remove(force)
return result

def updateConsisGroup(self, consisGroup, name=None, description=None, addVolumes=None, removeVolumes=None):

"""获得ConsisGroup对性的静态属性列表。
Args:
consisGroup obj Name or ID of a consistency group
name str New name for consistency group
description str New description for consistency group
addVolumes str UUID of one or more volumes to be added to the consistencygroup
removeVolumes str UUID of one or more volumes to be removed to the consistencygroup

"""

return consisGroup.update(consisGroup, name, description, addVolumes, removeVolumes)


def getXmlfile(self, key, fileType, filename=None, filePath=None):
"""主机上配置Xml文件信息获取

Args:
key str Get key from file
fileType str File type ('cinder'/'manila')
filename str config filename
filePath str config filepath

Changes:
2015-11-16 l00251491 Created
"""
return Utility.getfile(self, key, fileType, filename, filePath)

def changeCinderXml(self, key, value, filename=None, filePath=None):
"""用于修改/etc/cinder目录下的.xml配置文件

Args:
key str the key to be modified
value str value of the key
filename str config filename
filePath str config filepath

Changes:
2015-11-10 g00289391 Created

"""
return Utility.change(self, key, value, 'cinder', filename, filePath)

def changeManilaXml(self, key, value, filename=None, filePath=None):
"""用于修改/etc/manila目录下的.xml配置文件

Args:
key str the key to be modified
value str value of the key
filename str config filename
filePath str config filepath

Changes:
2015-11-10 g00289391 Created

"""
return Utility.change(self, key, value, 'manila', filename, filePath)

def rebootService(self, serviceType):
"""用于重启cinder或者manila服务

Args:
serviceType str serviceType, must be cinder or manila

Changes:
2015-11-19 g00289391 Created

"""
return Utility.reboot(self, serviceType)

def checkService(self, serviceType):
"""用于检查cinder或者manila服务状态是否正常

Args:
serviceType str serviceType, must be cinder or manila

Changes:
2015-11-19 g00289391 Created

"""
return Utility.check(self, serviceType)

def failoverReplica(self, object, tgt_id):

"""复制卷的倒换操作。

Args:
object obj volume
Changes:
2016-02-22 g00289391 Created
"""
return object.failover(object, tgt_id)

def failbackReplica(self, object, tgt_id):

"""复制卷的倒回操作。

Args:
object obj volume
Changes:
2016-02-22 g00289391 Created
"""
return object.failback(object, tgt_id)

def enableReplica(self, object):

"""启用复制卷。

Args:
object obj volume
Changes:
2016-02-22 g00289391 Created
"""
return object.enable()

def disableReplica(self, object):

"""停用复制卷。

Args:
object obj volume
Changes:
2016-02-22 g00289391 Created
"""
return object.disable()

def listtargetReplica(self, object):

"""获得可用作复制的后端列表，无可用后端时返回空。

Args:
object obj volume
Changes:
2012-02-22 g00289391 Created
"""
return object.listtarget()

def getpairidReplica(self, object):
"""获取复制pairid。

Args:
object obj volume
Changes:
2016-02-22 g00289391 Created
"""
pair_info = object.getProperty('os-volume-replication:driver_data')
pair_dict = eval(pair_info)
pair_id = pair_dict['pair_id']
return pair_id

def getrmtidReplica(self, object):
"""获取复制远端lunid。

Args:
object obj volume

Changes:
2016-02-22 g00289391 Created
"""
pair_info = object.getProperty('os-volume-replication:driver_data')
pair_dict = eval(pair_info)
rmt_lun_id = pair_dict['rmt_lun_id']
return rmt_lun_id

def setkeyVolumeType(self, vtype, key, value):
"""设置卷类型。

Args:
vtype obj Volumetype
key str key of volumetype
value str value of volumetype

Changes:
2016-02-22 g00289391 Created
"""
return vtype.setkey(vtype, key, value)

def resetVolume(self, volumes, state=None, attachStatus=None, migrationStatus=None):
"""重置volume或share状态为available。

Args:
objects list Volume or Share Objects

Changes:
2016-02-25 g00289391 Created
"""
result = []
for volume in volumes:
result.append(volume.reset(state, attachStatus, migrationStatus))
return result

def resetObject(self, objects, state=None, attachStatus=None, migrationStatus=None):
"""重置volume或share状态为available。

Args:
objects list Volume or Share Objects

Changes:
2016-02-25 g00289391 Created
"""
result = []
for object in objects:
result.append(object.reset(state, attachStatus, migrationStatus))
return result

def migrateVolume(self, object, host, forceHostCopy=None, lockVolume=None):

"""获得Volume对性的静态属性列表。

Args:
host str Cinder host on which the existing volume resides
object obj Volume object

"""

return Volume.migrate(object, host, forceHostCopy, lockVolume)

def get_backend(self, device):
# 后端名称
cmdline = {
'command': ['cinder', 'service-list',
'| grep cinder-volume|grep up',
"|awk '{print $4}'"]
}
res = device.run(cmdline)
serv_lines = device.split(res['stdout'])
backend = serv_lines[0]
backendName = backend.split('@')[1]
return backendName

def get_file_path(self, device, backendName=None):
if not backendName:
backendName = self.get_backend(device)
cmdline = {'command':
[r"sed -n '/\["+backendName+r"\]/,/\[/p' /etc/cinder/cinder.conf |"
r"awk -F = '/cinder_huawei_conf_file\s\=\s/{print $2}'"]}
ret = device.run(cmdline)
pathInfo = ret.get('stdout')
path = pathInfo.lstrip()
return path

def waitDelFinish(self, device, delType, delTypeId=None, timeOut=6, seconds=2):
"""删除后判断删除是否完成。判断条件：如果没有删除完成等待30s，如果删除完成直接退出

Args:
delType str volume/share/volumeType/shareType/Intance.....
device dev OpenStack/oceanStore/switch Device
delTypeId str volume/share/volumeType/shareType/Intance..... ID
"""
num = timeOut/seconds
for i in range(0,num):
if device.find(delType, forceSync=True):
time.sleep(seconds)
else:
return True

def initialOpenStack(self, OpenStackType, openStack, oceanStore=None, switch=None):
"""清理OpenStack环境。

Args:
OpenStackType str Cinder/Manila
openStack dev OpenStack Device
oceanStore dev oceanStore Device
switch dev switch Device
"""

"""清理环境"""

self.logger.info("Step 1 : Clean the system Start.")

"""删除快照"""
if OpenStackType.lower()=='cinder':
delSnapshot = openStack.find('volumesnapshot')
if delSnapshot:
openStack.removeSnapshot(delSnapshot)
self.waitDelFinish (openStack, 'volumesnapshot', 30, 3)

elif OpenStackType.lower()=='manila':
delSnapshot = openStack.find('sharesnapshot')
if delSnapshot:
openStack.removeSnapshot(delSnapshot)
self.waitDelFinish (openStack, 'sharesnapshot', 30, 3)
else:
self.logger.error('Error OpenStackType input error at the delSnapshot')

"""移除双活卷"""
if OpenStackType.lower()=='cinder':
consisGroups = openStack.find('consisGroup')
if consisGroups:
for consisGroup in consisGroups:
volumes = openStack.find('volume', criteria={'consistencygroup_id' : consisGroup.getProperty('id')})
for findVolume in volumes:
openStack.updateConsisGroup(consisGroup, removeVolumes=findVolume.getProperty('id') )

"""解挂在卷"""
if OpenStackType.lower()=='cinder':
detachVolumes = openStack.find('volume')
for detachVolume in detachVolumes:
attachInfo = detachVolume.getProperties()
if attachInfo['status'] == 'in-use':
detachInstance = openStack.find('instance',
criteria={'id' : eval(attachInfo['attachments'])[0]['server_id']})
openStack.detachInstance(detachInstance[0], detachVolume)
# try:
# openStack.waitForPropertyValue([detachVolume], {'status' : 'available'}, timeout=120, interval=10)
# except:
# pass

"""删除卷"""
if OpenStackType.lower()=='cinder':
delVolume = openStack.find('volume')
if delVolume:
openStack.removeVolume(delVolume)
self.waitDelFinish (openStack, 'volume')
elif OpenStackType.lower()=='manila':
delShare = openStack.find('share')
if delShare:
openStack.removeVolume(delShare)
self.waitDelFinish (openStack, 'share')
else:
self.logger.error('Error OpenStackType input error at the delVolume/delShare')


"""删除一致性组"""
if OpenStackType.lower()=='cinder':
delConsisGroup = openStack.find('consisGroup')
if delConsisGroup:
openStack.removeConsisGroup(delConsisGroup, force='True')
self.waitDelFinish (openStack, 'consisGroup')

"""删除卷类型 """
if OpenStackType.lower()=='cinder':
delVolumetype = openStack.find('volumeType')
if delVolumetype:
openStack.removeVolumeType(delVolumetype)
self.waitDelFinish (openStack, 'volumeType')
elif OpenStackType.lower()=='manila':
delSharetype = openStack.find('shareType')
if delSharetype:
openStack.removeVolume(delSharetype)
self.waitDelFinish (openStack, 'shareType')

"""清除后创建默认的shareType"""
openStack.createShareType('default',specDriverHandlesShareServers='false',snapshotSupport='true')
else:
self.logger.error('Error OpenStackType input error at the delVolumetype/delSharetype')

"""删除Qos类型"""
delQostype = openStack.find('qosType')
if delQostype:
openStack.removeQosType(delQostype)
self.waitDelFinish (openStack, 'qosType')

def setupEnableComponents(self):
"""此方法为内部方法，用于定义个'Nice name'映射到相应的component class

Args:
None.

Returns:
None.

Raises:
None.

Examples:
None.

"""
self.addType('Volume', 'UniAutos.Component.Volume.Huawei.OpenStack.Volume')
self.addType('Share', 'UniAutos.Component.OpenStackShare.Huawei.OpenStack.Share')
self.addType('Snapshot', 'UniAutos.Component.OpenStackSnapshot.Huawei.OpenStack.Snapshot')
self.addType('VolumeSnapshot', 'UniAutos.Component.OpenStackSnapshot.Huawei.VolumeSnapshot.VolumeSnapshot')
self.addType('ShareSnapshot', 'UniAutos.Component.OpenStackSnapshot.Huawei.ShareSnapshot.ShareSnapshot')
self.addType('Instance', 'UniAutos.Component.Instance.Huawei.OpenStack.Instance')
self.addType('VolumeType', 'UniAutos.Component.VolumeType.Huawei.OpenStack.VolumeType')
self.addType('ShareType', 'UniAutos.Component.ShareType.Huawei.OpenStack.ShareType')
self.addType('QosType', 'UniAutos.Component.QosType.Huawei.OpenStack.QosType')
self.addType('ConsisGroup', 'UniAutos.Component.ConsisGroup.Huawei.OpenStack.ConsisGroup')
self.addType('ShareServer', 'UniAutos.Component.ShareServer.Huawei.OpenStack.ShareServer')
return