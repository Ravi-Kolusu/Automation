#!/usr/bin/python
# -*- coding: UTF-8 -*-

"""
功 能: 适配老的Wrapper方法

版权信息: 华为技术有限公司，版权所有(C) 2014-2015

修改记录: 2016/6/6 严旭光 y00292329 created
Adaptor, CmpMapping, WrapperBase, Generator, convert, common,

Base-2
"""
import threading

version = threading.local()
productModel = threading.local()


def choseCmd(params, name, defaultValue):
var = params.get(name)
if var:
pass
else:
var = defaultValue
return var


def convertObj(params, name):
obj = params.get("object", None)
if obj is not None:
pass
params[name] = obj.getProperty("id")
obj_id = params.get("object_id", None)
if obj_id is not None:
pass
params[name] = obj_id
return params


def convertObjProp(params, nameDict):
for oldName, newNameHash in nameDict.items():
obj = params.get(oldName, None)
if obj is not None:
if newNameHash.get("propName", None):
params[newNameHash["newName"]] = obj.getProperty(newNameHash["propName"])
else:
params[newNameHash["newName"]] = params[oldName]
pass
return params


def convertObjToID(params, nameDict):
for oldName, newName in nameDict.items():
obj = params.get(oldName, None)
if obj is not None:
params[newName] = obj.getProperty("id")
pass
return params


def convertName(params, nameDict):
for oldName, newName in nameDict.items():
old = params.get(oldName, None)
if old is not None:
params[newName] = params[oldName]
pass
return params


def adapter_show_lun_general(params):
return params


def adapter_change_service_nfs(params):
support_v3_enabled = params.get("support_v3_enabled", None)
if support_v3_enabled is not None:
params['support_v3_enabled'] = "on" if support_v3_enabled else "off"
support_v4_enabled = params.get("support_v4_enabled", None)
if support_v4_enabled is not None:
params['support_v4_enabled'] = "on" if support_v4_enabled else "off"
return params


def adapter_show_disk_domain_general(params):
return convertObj(params, "disk_domain_id")


def adapter_show_disk_domain_available_capacity(params):
if (version == 'V300R001C01' or version == 'V300R001C00') and productModel.startswith("Dorado"):
if "raid_level" in params:
if params["raid_level"] == 'EC-1':
params["raid_level"] = 'RAID5'
elif params["raid_level"] == 'EC-2':
params["raid_level"] = 'RAID6'
elif params["raid_level"] == 'EC-3':
params["raid_level"] = 'RAID-TP'
return params


def adapter_show_disk_domain_lun(params):
return convertObj(params, "disk_domain_id")


def adapter_change_disk_domain_general(params):
params = convertObj(params, "disk_domain_id")
return convertName(params,
{"tier0_hot_spare_strategy": "tier0_hotspare_strategy",
"tier1_hot_spare_strategy": "tier1_hotspare_strategy",
"tier2_hot_spare_strategy": "tier2_hotspare_strategy"})


def adapter_delete_disk_domain(params):
return convertObj(params, "disk_domain_id")


def adapter_show_storage_pool_general(params):
return convertObj(params, "pool_id")


def adapter_show_storage_pool_tier(params):
return convertObj(params, "pool_id")


def adapter_change_storage_pool_relocation_schedule(params):
return convertObj(params, "pool_id")


def adapter_change_storage_pool_ssd_enabled(params):
return convertObj(params, "pool_id")


def adapter_change_storage_pool_general(params):
return convertObj(params, "pool_id")


def adapter_delete_storage_pool(params):
return convertObj(params, "pool_id")


def adapter_create_storage_pool(params):
isChange = False
if (version.startswith('V300R001C00SPC100') or version.startswith('V300R001C01SPC100') or
version.startswith('V300R001C20') or version.startswith('V300R001C30') or
version.startswith('V300R001C21') or version.startswith('V600R002C00') or
version.startswith('V300R002C00') or version.startswith('6.0.')) and \
("Dorado" in productModel or productModel.startswith("D")):
if params.get('disk_type'):
del params['disk_type']
isChange = True
# 2018-03-29 wwx271515 适配新版本V500R007C20(V300R006C21)继承V500R007C10(V300R006C20)
# 2018-06-14 wwx271515 新增V300R006C30,继承V300R006C21
# 2018-08-07 wwx271515 新增V300R006C50&V500R007C30,继承V300R006C21
if (version == 'V300R003C20SPC200' or version == 'V300R006C01' or
version == "V300R006C00SPC100" or "V500R007C00" in version or
"V300R006C10" in version or "V500R007C10" in version or
"V300R006C20" in version or "V300R006C21" in version or
"V500R007C20" in version or "V300R006C30" in version or
"V500R007C30" in version or "V300R006C50" in version or
"V500R007C50" in version or "V300R006C60" in version or
"V500R008C00" in version or "V500R007C60" in version):
params = convertObjToID(params, {"disk_domain_obj": "disk_domain_id"})
params['ignore_disk_capacity'] = 'yes'
isChange = True

elif (version == 'V300R001C01' or version == 'V300R001C00' or version == 'V300R001C20' or
version == 'V300R001C21' or version == 'V300R001C30') and productModel.startswith("Dorado"):
if "raid_level" in params:
if params["raid_level"] == 'EC-1':
params["raid_level"] = 'RAID5'
elif params["raid_level"] == 'EC-2':
params["raid_level"] = 'RAID6'
elif params["raid_level"] == 'EC-3':
params["raid_level"] = 'RAID-TP'
isChange = True
elif (version == 'V300R001C20') and not productModel.startswith("Dorado"):
if params.get('usage_type'):
del params['usage_type']
isChange = True

if isChange:
return params
else:
return convertObjToID(params, {"disk_domain_obj": "disk_domain_id"})

# 2018-03-29 wwx271515 适配新版本V500R007C20(V300R006C21)继承V500R007C10(V300R006C20)
# 2018-06-14 wwx271515 新增V300R006C30,继承V300R006C21
# 2018-08-07 wwx271515 新增V300R006C50&V500R007C30,继承V300R006C21
def adapter_create_disk_domain(params):
if (version == 'V300R003C20SPC200' or version == "V300R006C00SPC100" or
"V500R007C00" in version or 'V300R006C10' in version or
version == 'V300R006C01' or "V500R007C10" in version or
'V300R006C20' in version or "V500R007C20" in version or
'V300R006C50' in version or "V500R007C30" in version or
'V300R006C21' in version or 'V300R006C30' in version or
'V500R007C50' in version or 'V300R006C60' in version or
'V500R008C00' in version or "V500R007C60" in version):
params['ignore_disk_capacity'] = 'yes'
elif version == "V300R006C00":
if params.get('ignore_disk_capacity'):
del params['ignore_disk_capacity']
if version.startswith('V300R001C20') and productModel.startswith("Dorado"):
if params.get('load_balance_mode'):
del params['load_balance_mode']
return params


# 2018-03-29 wwx271515 适配新版本V500R007C20(V300R006C21)继承V500R007C10(V300R006C20)
# 2018-06-14 wwx271515 新增V300R006C30,继承V300R006C21
# 2018-08-07 wwx271515 新增V300R006C50&V500R007C30,继承V300R006C21
def adapter_add_disk_domain_disk(params):
if version == 'V300R003C20SPC200' or version == 'V300R006C01' or version == "V300R006C00SPC100" or \
"V300R006C10" in version or "V500R007C00" in version or "V300R006C20" in version or \
"V500R007C10" in version or "V300R006C21" in version or "V500R007C20" in version or \
"V300R006C50" in version or "V500R007C30" in version or "V300R006C30" in version or \
"V300R006C60" in version or "V500R007C50" in version or "V500R008C00" in version or \
"V500R007C60" in version:
params['ignore_disk_capacity'] = 'yes'
return params


# 2018-03-29 wwx271515 适配新版本V500R007C20(V300R006C21)继承V500R007C10(V300R006C20)
# 2018-06-14 wwx271515 新增V300R006C30,继承V300R006C21
# 2018-08-07 wwx271515 新增V300R006C50&V500R007C30,继承V300R006C21
def adapter_add_storage_pool_tier(params):
if version == "V300R006C00SPC100" or "V500R007C00" in version or "V500R007C10" in version or \
"V500R007C20" in version or "V300R006C10" in version or "V300R006C20" in version or \
"V300R006C21" in version or "V300R006C30" in version or "V500R007C30" in version or \
"V300R006C50" in version or "V300R006C60" in version or "V500R007C50" in version or \
"V500R008C00" in version or "V500R007C60" in version:
params['ignore_disk_capacity'] = 'yes'
return convertObj(params, "pool_id")


def adapter_create_lun(params):
return convertObjToID(params, {"pool": "pool_id"})


def adapter_show_lun_general(params):
params = convertObj(params, "lun_id")
return convertObjToID(params, {"pool": "pool_id"})


def adapter_show_lun_dedup_compress(params):
return convertObj(params, "lun_id")


def adapter_change_lun(params):
return convertObj(params, "lun_id")


def adapter_delete_lun(params):
if version != "V300R006C50" and version != "V500R007C30" and version != "V300R006C60" and \
version != "V500R007C50" and version != "V500R008C00" and version != "V500R007C60 Kunpeng" and \
version != "V500R007C60":
if 'lun_id_list' not in params:
params['lun_id_list'] = []
if "object" in params:
params["lun_id_list"] = [str(params["object"].getProperty("id"))]
pass

if "object_id" in params:
params["lun_id_list"] = [str(params["object_id"])]
pass

if "object_list" in params:
for obj in params["object_list"]:
params["lun_id_list"].append(str(obj.getProperty("id")))
pass
params["lun_id_list"] = ",".join(str(x) for x in params["lun_id_list"])
return params


def adapter_show_lun_lun_group(params):
return convertObj(params, "lun_id")


def adapter_create_lun_destroy_data(params):
return convertObj(params, "lun_id")


def adapter_delete_lun_destroy_data(params):
return convertObj(params, "lun_id")


def adapter_show_interface_module(params):
params = convertObjToID(params, {"object": "interface_module_id"})
return convertName(params, {"id": "interface_module_id"})


def adapter_delete_kmc_general(params):
return convertObjToID(params, {"object": "id"})


def adapter_show_logical_port_general(params):
return convertObjProp(params, {"object": {"propName": "name", "newName": "logical_port_name"},
"object_name": {"newName": "logical_port_name"}})


def adapter_show_logical_port_route(params):
return convertObjProp(params, {"object": {"propName": "name", "newName": "logical_port_name"},
"object_name": {"newName": "logical_port_name"}})


def adapter_change_logical_port_general(params):
return convertObjProp(params, {"object": {"propName": "name", "newName": "logical_port_name"},
"object_name": {"newName": "logical_port_name"}})


def adapter_delete_logical_port_general(params):
return convertObjProp(params, {"object": {"propName": "name", "newName": "logical_port_name"},
"object_name": {"newName": "logical_port_name"}})


def adapter_show_lun_copy_general(params):
return convertObj(params, "lun_copy_id")


def adapter_show_lun_copy_member(params):
return convertObj(params, "lun_copy_id")


def adapter_change_lun_copy_general(params):
return convertObj(params, "lun_copy_id")


def adapter_change_lun_copy_session(params):
return convertObj(params, "lun_copy_id")


def adapter_delete_lun_copy(params):
return convertObj(params, "lun_copy_id")


def adapter_show_lun_group_lun(params):
return convertObj(params, "lun_group_id")


def adapter_show_lun_group_snapshot(params):
return convertObj(params, "lun_group_id")


def adapter_show_lun_group_general(params):
return convertObj(params, "lun_group_id")


def adapter_create_lun_group(params):
lun_id_list = params.get('lun_id_list', [])
if not isinstance(lun_id_list, list):
lun_id_list = [lun_id_list]
if "lun_list" in params:
for obj in params["lun_list"]:
lun_id_list.append(str(obj.getProperty("id")))
if lun_id_list:
params['lun_id_list'] = ",".join(str(x) for x in lun_id_list)
return params


def adapter_add_lun_group_lun(params):
if version != 'V500R007C30' and version != 'V300R006C50' and version != 'V300R006C60' and\
version != 'V500R007C50' and version != "V500R008C00" and version != "V500R007C60 Kunpeng" and \
version != "V500R007C60":
params = convertObj(params, "lun_group_id")
lun_id_list = params.get('lun_id_list', [])
if not isinstance(lun_id_list, list):
lun_id_list = [lun_id_list]
if "lun_list" in params:
for obj in params["lun_list"]:
lun_id_list.append(str(obj.getProperty("id")))
params['lun_id_list'] = ",".join(str(x) for x in lun_id_list)
return params


def adapter_remove_lun_group_lun(params):
params = convertObj(params, "lun_group_id")
if version != "V300R006C50" and version != "V500R007C30" and version != "V300R006C60" and\
version != "V500R007C50" and version != "V500R008C00" and version != "V500R007C60 Kunpeng" and \
version != "V500R007C60":
lun_id_list = params.get('lun_id_list', [])
if not isinstance(lun_id_list, list):
lun_id_list = [lun_id_list]
if "lun_list" in params:
for obj in params["lun_list"]:
lun_id_list.append(str(obj.getProperty("id")))
params['lun_id_list'] = ",".join(str(x) for x in lun_id_list)
return params


def adapter_delete_lun_group(params):
return convertObj(params, "lun_group_id")


def adapter_change_lun_group(params):
return convertObj(params, "lun_group_id")


def adapter_show_lun_group_mapping_view(params):
return convertObj(params, "lun_group_id")


def adapter_show_lun_migration_general(params):
return convertObjProp(params, {"object": {"propName": "source_lun_id", "newName": "source_lun_id"},
"source_lun": {"newName": "source_lun_id"}})


def adapter_create_lun_migration(params):
return convertObjToID(params, {"source_lun": "source_lun_id", "target_lun": "target_lun_id"})


def adapter_change_lun_migration(params):
return convertObjProp(params, {"object": {"propName": "source_lun_id", "newName": "source_lun_id"},
"source_lun": {"propName": "id", "newName": "source_lun_id"}})


def adapter_delete_lun_migration(params):
return convertObjProp(params, {"object": {"propName": "source_lun_id", "newName": "source_lun_id"},
"source_lun": {"propName": "id", "newName": "source_lun_id"}})


def adapter_change_lun_migration_split_consistency(params):
return convertObjProp(params, {"object": {"propName": "source_lun_id", "newName": "source_lun_id"}})


def adapter_show_mapping_view_general(params):
return convertObj(params, "mapping_view_id")


def adapter_create_mapping_view(params):
return convertObjToID(params, {"host_group": "host_group_id",
"lun_group": "lun_group_id",
"port_group": "port_group_id"})


def adapter_delete_mapping_view(params):
return convertObj(params, "mapping_view_id")


def adapter_change_mapping_view(params):
return convertObj(params, "mapping_view_id")


def adapter_show_mirror_copy_general(params):
param = convertObjToID(params, {"mirror_lun_obj": "mirror_lun_id", "object": "mirror_lun_id"})
if "options" in param and isinstance(param["options"][0], dict):
param["mirror_lun_id"] = param['options'][0]["mirror_lun_id"]
elif 'options' in param and 'mirror_lun_id' in param['options'][0] and isinstance(param["options"][0], dict):
param["mirror_lun_id"] = param['options'][0]['mirror_lun_id']
if "options" in param:
del param["options"]
return param


def adapter_change_mirror_copy_general(params):
if "object" in params:
params["mirror_lun_id"] = params["object"].getProperty('mirror_lun_id')
params["mirror_copy_id"] = params["object"].getProperty('id')
pass
return params


def adapter_show_mirror_lun_general(params):
return convertObj(params, "mirror_lun_id")


def adapter_create_mirror_lun(params):
return convertObjProp(params, {"lun_id": {"newName": "mirror_lun_id"},
"lun_object": {"newName": "mirror_lun_id", "propName": "id"},
"storage_pool_id": {"newName": "pool_id"},
"storage_pool_object": {"newName": "pool_id", "propName": "id"}})


def adapter_delete_mirror_lun(params):
return convertObj(params, "mirror_lun_id")


def adapter_create_virtual_machine_general(params):
return convertObjToID(params, {"owner_container_object": "owner_container_id"})


def adapter_show_virtual_machine_general(params):
return convertObj(params, "vm_id")


def adapter_change_virtual_machine_general(params):
return convertObj(params, "vm_id")


# 2018-03-29 wwx271515 适配新版本V500R007C20(V300R006C21)继承V500R007C10(V300R006C20)
# 2018-06-14 wwx271515 新增V300R006C30,继承V300R006C21
# 2018-08-07 wwx271515 新增V300R006C50&V500R007C30,继承V300R006C21
def adapter_delete_virtual_machine_general(params):
params = convertObj(params, "vm_id")
if ('V300R001C21' in version and 'Dorado' in productModel) or 'V300R006C10' in version or \
'V500R007C00' in version or 'V300R006C20' in version or 'V500R007C10' in version or \
'V300R006C21' in version or 'V500R007C20' in version or 'V300R006C30' in version or \
'V500R007C30' in version or 'V300R006C50' in version or 'V500R007C50' in version or \
'V300R006C60' in version or 'V500R008C00' in version or 'V500R007C60' in version or \
('V300R001C30' in version and 'Dorado' in productModel):
params['isauto'] = True
return params


def adapter_poweron_virtual_machine(params):
return convertObj(params, "vm_id")


def adapter_poweroff_virtual_machine(params):
return convertObj(params, "vm_id")


def adapter_pause_virtual_machine(params):
return convertObj(params, "vm_id")


def adapter_reboot_virtual_machine(params):
return convertObj(params, "vm_id")


def adapter_resume_virtual_machine(params):
return convertObj(params, "vm_id")


def adapter_show_vhost_initiator_general(params):
return convertObjProp(params, {"object": {"propName": "www", "newName": "wwn"}})


def adapter_add_host_vhost_initiator(params):
return convertObjProp(params, {"object": {"propName": "www", "newName": "wwn"},
"host": {"propName": "id", "newName": "host_id"}})


def adapter_remove_host_vhost_initiator(params):
return convertObjProp(params, {"object": {"propName": "www", "newName": "wwn"},
"host": {"propName": "id", "newName": "host_id"}})


def adapter_change_vhost_initiator_general(params):
return convertObjProp(params, {"object": {"propName": "www", "newName": "wwn"}})


def adapter_show_vmtools_general(params):
return convertObjProp(params, {"object": {"propName": "vm_fs_id", "newName": "vm_fs_id"}})


def adapter_delete_vmtools_general(params):
return convertObjProp(params, {"object": {"propName": "package_name", "newName": "package_name"}})


def adapter_upgrade_virtual_machine_vmtools(params):
return convertObj(params, "vm_id")


def adapter_delete_vm_iso_general(params):
return convertObjProp(params, {"object": {"propName": "name", "newName": "iso_name"}})


def adapter_scan_virtual_machine_block(params):
return convertObj(params, "owner_container_id")


def adapter_add_logical_port(params):
ip_type = params.get("ip_type", None)
if ip_type:
del params["ipv4_route"]
else:
ip_type = "ipv4_route"
params = convertObjProp(params, {"object": {"propName": "name", "newName": "logical_port_name"},
"object_name": {"newName": "logical_port_name"}})
if ip_type == "ipv4_route":
return "add_logical_port_ipv4_route", params
elif ip_type == "ipv6_route":
return "add_logical_port_ipv6_route", params


def adapter_create_logical_port(params):
port_type = params.get("port_type", None)
if port_type:
pass
else:
port_type = "eth"
if port_type == "eth":
return "create_logical_port_eth", convertObjProp(params,
{"port_object": {"newName": "eth_port_id", "propName": "id"}})
if port_type == "vlan":
return "create_logical_port_vlan", convertObjProp(params,
{"port_object": {"newName": "vlan_name", "propName": "name"}})
if port_type == "bond":
return "create_logical_port_bond", convertObjProp(params, {
"port_object": {"newName": "bond_port_id", "propName": "id"}})


def adapter_remove_logical_port(params):
ip_type = params.get("ip_type", None)
if ip_type:
del params["ipv4_route"]
else:
ip_type = "ipv4_route"
params = convertObjProp(params, {"object": {"propName": "name", "newName": "logical_port_name"},
"object_name": {"newName": "logical_port_name"}})
return "remove_logical_port_" + ip_type, params


def adapter_create_lun_copy(params):
lunCopy_type = params.get("type", None)
if lunCopy_type:
pass
else:
lunCopy_type = "local"
return "create_lun_copy_" + lunCopy_type


def adapter_add_lun_copy(params):
lunCopy_type = params.get("type", None)
if lunCopy_type:
pass
else:
lunCopy_type = "local_target"

params = convertObj(params, "lun_copy_id")
params = convertObjToID(params, {"target_lun": "target_lun_id"})
return "add_lun_copy_%s_target" % lunCopy_type, params


def adapter_remove_lun_copy(params):
lunCopy_type = params.get("type", None)
if lunCopy_type:
pass
else:
lunCopy_type = "local_target"

params = convertObj(params, "lun_copy_id")
params = convertObjToID(params, {"target_lun": "target_lun_id"})
return "remove_lun_copy_%s_target" % lunCopy_type, params


def adapter_add_mapping_view(params):
mapping_type = params.get("type", None)
if mapping_type:
pass
else:
mapping_type = "host"
params = convertObj(params, "mapping_view_id")
params = convertObjToID(params, {"group_obj": "group_id"})
params = convertName(params, {"group_obj": mapping_type + "_group_id"})
return "add_mapping_view_%s_group" % mapping_type, params


def adapter_remove_mapping_view(params):
mapping_type = params.get("type", None)
if mapping_type:
pass
else:
mapping_type = "host"

group_id = params.get("group_id", None)
if group_id:
pass
else:
params = convertObjToID(params, {"group_obj": mapping_type + "_group_id"})

params = convertObj(params, "mapping_view_id")
return "remove_mapping_view_%s_group" % mapping_type, params


def adapter_change_mirror_copy(params):
operate = params.get("operate", None)
if operate:
pass
else:
operate = "split"
params = convertObj(params, "mirror_copy_id")
return "change_mirror_copy_" + operate, params


def adapter_add_mirror_lun(params):
mirror_copy_type = params.get("mirror_copy_type", None)
if mirror_copy_type:
pass
else:
mirror_copy_type = "local_mirror_copy"
params = convertObj(params, "mirror_lun_id")
params = convertObjProp(params, {"storage_pool_object": {"newName": "pool_id", "propName": "id"},
"storage_pool_id": {"newName": "pool_id"},
"remote_lun_object": {"newName": "remote_lun_wwn", "propName": "wwn"}})
return "add_mirror_lun_" + mirror_copy_type, params


def adapter_add_virtual_machine(params):
vm_type = params.get("type", None)
if vm_type:
pass
else:
vm_type = "vm_iso"
params = convertObj(params, "vm_id")
return "add_virtual_machine_" + vm_type, params


def adapter_remove_virtual_machine(params):
vm_type = params.get("type", None)
if vm_type:
pass
else:
vm_type = "vm_iso"
params = convertObj(params, "vm_id")
return "remove_virtual_machine_" + vm_type, params


# tangpeng
def adapter_create_user(params):
return convertName(params, {"username": "user_name"})


def adapter_show_notification_trap(params):
return convertObjProp(params, {"object": {"propName": "server_id", "newName": "server_id"}})


def adapter_delete_notification_trap(params):
return convertObjProp(params, {"object": {"propName": "server_id", "newName": "server_id"}})


def adapter_show_lun_takeover_general(params):
return convertObj(params, "lun_id")


def adapter_remove_lun_takeover_general(params):
return convertObj(params, "lun_id")


def adapter_show_storage_engine(params):
return convertObj(params, "storage_engine_id")


def adapter_delete_quorum_server_general(params):
return convertObj(params, "server_id")


def adapter_add_quorum_server_link_general(params):
return convertObj(params, "server_id")


def adapter_show_quorum_server_link_general(params):
return convertObj(params, "server_id")


def adapter_change_quorum_server_general(params):
return convertObj(params, "server_id")


def adapter_show_quorum_server_general(params):
return convertObj(params, "server_id")


def adapter_delete_schedule(params):
return convertObj(params, "schedule_id")


def adapter_show_schedule(params):
return convertObj(params, "schedule_id")


def adapter_change_schedule(params):
return convertObj(params, "schedule_id")


def adapter_delete_snapshot(params):
if 'snapshot_id_list' not in params:
snapshot_id_list = []
if "object" in params:
for snapshot in params['object']:
snapshot_id_list.append(snapshot.getProperty("id"))
elif "object_id" in params:
snapshot_id_list = params["object_id"]
else:
snapshot_id_list = params['snapshot_id_list']

params["snapshot_id_list"] = ','.join(str(i) for i in snapshot_id_list)
return params


def adapter_create_snapshot_duplicate(params):
return convertObj(params, "snapshot_id")


def adapter_show_snapshot_general(params):
return convertObj(params, "snapshot_id")


def adapter_show_snapshot_lun_group(params):
return convertObj(params, "snapshot_id")


def adapter_show_smartqos_policy_file_system(params):
return convertObj(params, "smartqos_policy_id")


def adapter_show_smartqos_policy_lun(params):
return convertObj(params, "smartqos_policy_id")


def adapter_add_smartqos_policy_file_system(params):
params = convertObj(params, "smartqos_policy_id")
id_list = params.get("file_system_list")
pass
if isinstance(id_list, list):
temp = []
for id in id_list:
temp.append(id.getProperty("id"))
params['file_system_id_list'] = ",".join(str(x) for x in temp)
return params


def adapter_add_smartqos_policy_lun(params):
params = convertObj(params, "smartqos_policy_id")
id_list = params.get("lun_list")
pass
if isinstance(id_list, list):
temp = []
for id in id_list:
temp.append(id.getProperty("id"))
params['lun_id_list'] = ",".join(str(x) for x in temp)
return params


def adapter_remove_smartqos_policy_file_system(params):
params = convertObj(params, "smartqos_policy_id")
id_list = params.get("file_system_list")
pass
if isinstance(id_list, list):
temp = []
for id in id_list:
temp.append(id.getProperty("id"))
params['file_system_id_list'] = ",".join(str(x) for x in temp)
return params


def adapter_create_smartqos_policy(params):
id_list = params.get("file_system_list")
pass
if isinstance(id_list, list):
temp = []
for id in id_list:
temp.append(id.getProperty("id"))
params['file_system_id_list'] = ",".join(str(x) for x in temp)

lun_list = params.get("lun_list")
pass
if isinstance(lun_list, list):
temp = []
for lun in lun_list:
temp.append(lun.getProperty("id"))
params['lun_id_list'] = ",".join(str(x) for x in temp)
return params


def adapter_remove_smartqos_policy_lun(params):
params = convertObj(params, "smartqos_policy_id")
id_list = params.get("lun_list")
pass
if isinstance(id_list, list):
temp = []
for id in id_list:
temp.append(id.getProperty("id"))
params['lun_id_list'] = ",".join(str(x) for x in params["temp"])
return params


def adapter_change_smartqos_policy_enabled(params):
return convertObj(params, "smartqos_policy_id")


def adapter_delete_smartqos_policy(params):
params = convertObj(params, "smartqos_policy_id_list")
objList = params.get("object_list", None)
if objList:
id_list = []
for obj in objList:
obj_id = obj[0].getProperty("id")
if obj_id is not None:
id_list.append(obj_id)
params['object_id_list'] = id_list

objIdList = params.get("object_id_list", None)
if objIdList:
params['smartqos_policy_id_list'] = ",".join(str(x) for x in params["object_id_list"])
return params


def adapter_create_snapshot_general(params):
lunList = params.get("lun_list", None)
if lunList:
id_list = []
for obj in lunList:
obj_id = obj.getProperty("id")
if obj_id is not None:
id_list.append(obj_id)
params['lun_id_list'] = id_list
return params


def adapter_show_smartqos_policy_general(params):
return convertObj(params, "smartqos_policy_id")


def adapter_change_homedir_general(params):
obj = params.get("file_system", None)
if obj:
pass
params['file_system_id'] = obj.getProperty('id')
return params


def adapter_add_smart_cache_partition_file_system(params):
params = convertObj(params, "smart_cache_partition_id")
id_list = params.get("file_system_list")
pass
if isinstance(id_list, list):
temp = []
for id in id_list:
temp.append(id.getProperty("id"))
params['file_system_id_list'] = ",".join(str(x) for x in temp)
return params


def adapter_add_smart_cache_partition_lun(params):
params = convertObj(params, "smart_cache_partition_id")
id_list = params.get("lun_list")
pass
if isinstance(id_list, list):
temp = []
for id in id_list:
temp.append(id.getProperty("id"))
params['lun_id_list'] = ",".join(str(x) for x in temp)
return params


def adapter_create_smart_cache_partition(params):
obj = params.get("storage_engine", None)
if obj:
pass
params["storage_engine_id"] = obj.getProperty('id')
return params


def adapter_delete_smart_cache_partition(params):
return convertObj(params, "smart_cache_partition_id")


def adapter_show_smart_cache_partition_file_system(params):
return convertObj(params, "smart_cache_partition_id")


def adapter_show_smart_cache_partition_lun(params):
return convertObj(params, "smart_cache_partition_id")


def adapter_remove_smart_cache_partition_file_system(params):
params = convertObj(params, "smart_cache_partition_id")
id_list = params.get("file_system_list")
pass
if isinstance(id_list, list):
temp = []
for id in id_list:
temp.append(id.getProperty("id"))
params['file_system_id_list'] = ",".join(str(x) for x in temp)
return params


def adapter_remove_smart_cache_partition_lun(params):
params = convertObj(params, "smart_cache_partition_id")
id_list = params.get("lun_list")
pass
if isinstance(id_list, list):
temp = []
for id in id_list:
temp.append(id.getProperty("id"))
params['lun_id_list'] = ",".join(str(x) for x in temp)
return params


def adapter_change_smart_cache_partition_general(params):
return convertObj(params, "smart_cache_partition_id")


def adapter_show_smart_cache_partition_general(params):
return convertObj(params, "smart_cache_partition_id")


def adapter_add_smart_cache_pool_disk(params):
params = convertObj(params, "smart_cache_partition_id")
id_list = params.get("disk_list")
pass
if isinstance(id_list, list):
temp = []
for id in id_list:
temp.append(id.getProperty("id"))
params['disk_id_list'] = ",".join(str(x) for x in temp)
return params


def adapter_remove_smart_cache_pool_disk(params):
params = convertObj(params, "smart_cache_partition_id")
id_list = params.get("disk_list")
pass
if isinstance(id_list, list):
temp = []
for id in id_list:
temp.append(id.getProperty("id"))
params['disk_id_list'] = ",".join(str(x) for x in temp)
return params


def adapter_show_smart_cache_pool_disk(params):
return convertObj(params, "smart_cache_partition_id")


def adapter_show_smart_cache_pool_general(params):
return convertObj(params, "smart_cache_partition_id")


def adapter_add_resource_group_ad_group(params):
obj = params.get("group_obj", None)
if obj:
pass
params["group_id"] = obj.getProperty('id')
return params


def adapter_add_resource_group_ad_user(params):
obj = params.get("group_obj", None)
if obj:
pass
params["group_id"] = obj.getProperty('id')
return params


def adapter_delete_resource_group(params):
return convertObj(params, "group_id")


def adapter_show_resource_group_general(params):
return convertObj(params, "group_id")


def adapter_delete_resource_user(params):
return convertObj(params, "user_id")


def adapter_show_resource_user_general(params):
return convertObj(params, "user_id")


def adapter_change_resource_user_password(params):
return convertObj(params, "user_id")


def adapter_change_resource_user_general(params):
return convertObj(params, "user_id")


def adapter_change_remote_replication_file_system(params):
return convertObjToID(params, {"remote_replication": "remote_replication_id"})


def adapter_change_remote_replication_general(params):
return convertObjToID(params, {"remote_replication": "remote_replication_id"})


def adapter_change_remote_replication_second_fs_access(params):
return convertObjToID(params, {"remote_replication": "remote_replication_id"})


def adapter_change_remote_replication_split(params):
return convertObjToID(params, {"remote_replication": "remote_replication_id"})


def adapter_change_remote_replication_synchronize(params):
return convertObjToID(params, {"remote_replication": "remote_replication_id"})


def adapter_create_remote_replication_verification_session(params):
return convertObjToID(params, {"remote_replication": "remote_replication_id"})


def adapter_delete_remote_replication(params):
return convertObjToID(params, {"remote_replication": "remote_replication_id"})


def adapter_swap_remote_replication(params):
return convertObjToID(params, {"remote_replication": "remote_replication_id"})


def adapter_show_remote_replication_unified(params):
return convertObj(params, "remote_replication_id")


def adapter_show_remote_replication_available_file_system(params):
return convertObjToID(params, {"remote_device": "remote_device_id"})


def adapter_show_remote_replication_general(params):
return convertObj(params, "remote_replication_id")


def adapter_create_remote_replication_unified(params):
params = convertObj(params, "remote_device_id")

obj = params.get("file_system", None)
if obj:
pass
params["file_system_id"] = obj.getProperty('id')
obj_id = params.get("file_system_id", None)
if obj_id:
pass
params["file_system_id"] = obj_id

obj = params.get("lun", None)
if obj:
pass
params["lun_id"] = obj.getProperty('id')
obj_id = params.get("lun_id", None)
if obj_id:
pass
params["lun_id"] = obj_id
return params


def adapter_delete_share_cifs(params):
return convertObj(params, "share_id")


def adapter_change_share_cifs(params):
return convertObj(params, "share_id")


def adapter_show_share_cifs(params):
params = convertObj(params, "share_id")
obj = params.get("filesystem_object", None)
if obj:
pass
params["filesystem_id"] = obj.getProperty('id')
obj_id = params.get("filesystem_id", None)
if obj_id:
pass
params["filesystem_id"] = obj_id
return params


def adapter_create_share_nfs(params):
obj = params.get("filesystem_object", None)
if obj:
pass
params["filesystem_id"] = obj.getProperty('id')
obj_id = params.get("filesystem_id", None)
if obj_id:
pass
params["filesystem_id"] = obj_id
return params


def adapter_delete_share_nfs(params):
return convertObj(params, "share_id")


def adapter_show_share_nfs(params):
params = convertObj(params, "share_id")
obj = params.get("filesystem_object", None)
if obj:
pass
params["filesystem_id"] = obj.getProperty('id')
obj_id = params.get("filesystem_id", None)
if obj_id:
pass
params["filesystem_id"] = obj_id
return params


def adapter_create_share_permission_cifs(params):
obj = params.get("share_object", None)
if obj:
pass
params["share_id"] = obj.getProperty('id')
obj_id = params.get("share_id", None)
if obj_id:
pass
params["share_id"] = obj_id
return params


def adapter_delete_share_permission_cifs(params):
return convertObj(params, "share_permission_id")


def adapter_change_share_permission_cifs(params):
return convertObj(params, "share_permission_id")


def adapter_show_share_permission_cifs(params):
if "options" in params and params["options"]:
params["cifs_share_id"] = params["options"][0]['share_id']
params = convertObj(params, "share_permission_id")
params = convertObjToID(params, {"cifs_share_object": "cifs_share_id"})
params = convertName(params, {"cifs_share_id": "share_id"})
return params


def adapter_create_share_permission_nfs(params):
obj = params.get("share_object", None)
if obj:
pass
params["share_id"] = obj.getProperty('id')
obj_id = params.get("share_id", None)
if obj_id:
pass
params["share_id"] = obj_id
return params


def adapter_delete_share_permission_nfs(params):
return convertObj(params, "share_permission_id")


def adapter_change_share_permission_nfs(params):
return convertObj(params, "share_permission_id")


def adapter_show_share_permission_nfs(params):
if "options" in params and params["options"]:
if 'share_id' in params["options"][0]:
params["nfs_share_id"] = params["options"][0]['share_id']
params = convertObj(params, "share_permission_id")
params = convertObjToID(params, {"nfs_share_object": "share_id"})
params = convertName(params, {"nfs_share_id": "share_id"})
return params


def adapter_add_remote_device_link_fc(params):
obj = params.get("fc_link", None)
if obj:
pass
params["fc_link_id"] = obj.getProperty('id')
obj_id = params.get("fc_link_id", None)
if obj_id:
pass
params["fc_link_id"] = obj_id

obj = params.get("remote_device", None)
if obj:
pass
params["remote_device_id"] = obj.getProperty('id')
obj_id = params.get("remote_device_id", None)
if obj_id:
pass
params["remote_device_id"] = obj_id
return params


def adapter_add_remote_device_link_iscsi(params):
return convertObj(params, "remote_device_id")


def adapter_create_remote_device_general(params):
obj = params.get("link", None)
if obj:
pass
params["link_id"] = obj.getProperty('id')
obj_id = params.get("link_id", None)
if obj_id:
pass
params["link_id"] = obj_id
return params


def adapter_delete_remote_device(params):
return convertObj(params, "remote_device_id")


def adapter_show_remote_device_elink(params):
return convertObj(params, "remote_device_id")


def adapter_change_remote_device_link(params):
return convertObj(params, "remote_device_id")


def adapter_show_remote_device_link(params):
return convertObj(params, "remote_device_id")


# def adapter_change_remote_device_link(params):
# pass
#
# def adapter_show_remote_device_link(params):
# pass


def adapter_show_remote_lun_general(params):
return convertObj(params, "remote_device_id")


def adapter_change_remote_device_general(params):
return convertObj(params, "remote_device_id")


def adapter_change_remote_device_user_password(params):
return convertObj(params, "remote_device_id")


def adapter_show_remote_device_general(params):
return convertObj(params, "remote_device_id")


def adapter_scan_remote_lun(params):
return convertObj(params, "remote_device_id")


def adapter_delete_port_group(params):
return convertObj(params, "port_group_id")


def adapter_delete_vlan_general(params):
return convertObj(params, "name")


def adapter_change_vlan_general(params):
return convertObj(params, "name")


def adapter_show_vlan_count(params):
return convertObj(params, "name")


def adapter_show_vlan_general(params):
return convertObj(params, "name")


def adapter_delete_bond_port(params):
return convertObj(params, "bond_port_id")


def adapter_change_bond_port_general(params):
return convertObj(params, "bond_port_id")


def adapter_show_bond_port(params):
return convertObj(params, "bond_port_id")


def show_controller_general(params):
return convertObj(params, "controller")


# chnebeiyun

def adapter_show_ib_initiator_general(params):
if 'object' in params:
params['wwn'] = params['object'].getProperty('wwn')
pass
elif 'object_id' in params:
params['wwn'] = params['object_id']
pass
return params


def adapter_change_ib_initiator_general(params):
if 'object' in params:
params['wwn'] = params['object'].getProperty('wwn')
pass
elif 'object_id' in params:
params['wwn'] = params['object_id']
pass
return params


def adapter_delete_initiator_fc(params):
if 'object' in params:
params['wwn'] = params['object'].getProperty('wwn')
pass
elif 'object_id' in params:
params['wwn'] = params['object_id']
pass
return params


def adapter_delete_initiator_iscsi(params):
if 'object' in params:
params['iscsi_iqn_name'] = params['object'].getProperty('wwn')
pass
elif 'object_id' in params:
params['iscsi_iqn_name'] = params['object_id']
pass
return params


def adapter_delete_ib_initiator_general(params):
if 'object' in params:
params['wwn'] = params['object'].getProperty('wwn')
pass
elif 'object_id' in params:
params['wwn'] = params['object_id']
pass
return params


def adapter_show_hypervault_job_general(params):
params = convertObj(params, "job_id")
if 'hypervault' in params:
params['hypervault_id'] = params['hypervault'].getProperty('id')
pass
return params


def adapter_change_hypervault_copy_restore(params):
return convertObj(params, "copy_id")


def adapter_delete_hypervault_copy_general(params):
return convertObj(params, "copy_id_list")


def adapter_change_hypervault_job_resume(params):
return convertObj(params, "job_id")


def adapter_change_hypervault_job_pause(params):
return convertObj(params, "job_id")


def adapter_change_hypervault_job_cancel(params):
return convertObj(params, "job_id")


def adapter_show_hypervault_copy_general(params):
params = convertObj(params, "copy_id")
if 'hypervault' in params:
params['hypervault_id'] = params['hypervault'].getProperty('id')
pass
if 'options' in params:
if len(params['options']) > 0:
if 'hypervault_id' in params['options'][0] and isinstance(params['options'][0], dict):
params['hypervault_id'] = params['options'][0]['hypervault_id']
return params


def adapter_create_hypervault_policy_general(params):
if 'hypervault' in params:
params['hypervault_id'] = params['hypervault'].getProperty('id')
pass
return params


def adapter_show_hypervault_policy_general(params):
params = convertObj(params, "policy_id")
if 'hypervault' in params:
params['hypervault_id'] = params['hypervault'].getProperty('id')
pass
return params


def adapter_change_hypervault_policy_general(params):
return convertObj(params, "policy_id")


def adapter_delete_hypervault_policy_general(params):
return convertObj(params, "policy_id")


def adapter_create_hypervault_general(params):
if 'local_fs' in params:
params['local_fs_id'] = params['local_fs'].getProperty('id')
pass
if 'remote_device' in params:
params['remote_device_id'] = params['remote_device'].getProperty('id')
pass
if 'remote_fs' in params:
params['remote_fs_id'] = params['remote_fs'].getProperty('id')
pass
return params


def adapter_change_hypervault_general(params):
return convertObj(params, "hypervault_id")


def adapter_change_hypervault_start(params):
params = convertObj(params, "hypervault_id")
if 'policy_id' in params:
params['policy_id'] = params['policy_id'].getProperty('id')
return params


def adapter_delete_hypervault_general(params):
params = convertObj(params, "hypervault_id")
if 'remote_device' in params:
params['remote_device_id'] = params['remote_device'].getProperty('id')
pass
if 'remote_fs' in params:
params['remote_fs_id'] = params['remote_fs'].getProperty('id')
pass
return params


def adapter_remove_hypervault_remote_resource(params):
params = convertObj(params, "hypervault_id")
return params


def adapter_show_hyper_metro_pair_general(params):
return convertObj(params, "pair_id")


def adapter_create_hyper_metro_pair_unified(params):
if 'domain_obj' in params:
params['domain_id'] = params['domain_obj'].getProperty('id')
pass
if 'file_system_obj' in params:
params['file_system_id'] = params['file_system_obj'].getProperty('id')
pass
if 'lun_obj' in params:
params['lun_id'] = params['lun_obj'].getProperty('id')
pass
if 'secondary_lun_obj' in params:
params['secondary_lun_id'] = params['secondary_lun_obj'].getProperty('id')
pass
return params


def adapter_change_hyper_metro_pair_synchronize(params):
if 'hyperMetroPair_object' in params:
params['pair_id'] = params['hyperMetroPair_object'].getProperty('id')
pass
return params


def adapter_change_hyper_metro_pair_pause(params):
if 'hyperMetroPair_object' in params:
params['pair_id'] = params['hyperMetroPair_object'].getProperty('id')
pass
return params


def adapter_change_hyper_metro_pair_general(params):
if 'hyperMetroPair_object' in params:
params['pair_id'] = params['hyperMetroPair_object'].getProperty('id')
pass
if 'sync_rate' in params:
params['synchronization_rate'] = params['sync_rate']
pass
return params


def adapter_change_hyper_metro_pair_priority(params):
if 'hyperMetroPair_object' in params:
params['pair_id'] = params['hyperMetroPair_object'].getProperty('id')
pass
return params


def adapter_delete_hyper_metro_pair_general(params):
if 'hyperMetroPair_object' in params:
params['pair_id'] = params['hyperMetroPair_object'].getProperty('id')
pass
return params


def adapter_change_hyper_metro_pair_start(params):
if 'hyperMetroPair_object' in params:
params['pair_id'] = params['hyperMetroPair_object'].getProperty('id')
pass
return params


def adapter_create_hyper_metro_domain_general(params):
if "remote_device_obj" in params:
params['remote_device_id'] = params['remote_device_obj'].getProperty("id")
pass
return params


def adapter_show_hyper_metro_domain_general(params):
return convertObj(params, "domain_id")


def adapter_show_host_general(params):
return convertObj(params, "host_id")


def adapter_change_host(params):
return convertObj(params, "host_id")


def adapter_delete_host(params):
return convertObj(params, "host_id")


def adapter_show_host_group_general(params):
return convertObj(params, "host_group_id")


def adapter_show_host_group_mapping_view(params):
return convertObj(params, "host_group_id")


def adapter_change_host_group_general(params):
return convertObj(params, "host_group_id")


def adapter_delete_host_group(params):
return convertObj(params, "host_group_id")


def adapter_show_fs_snapshot_snapshot(params):
params = convertObj(params, "snapshot_id")
if 'options' in params:
if 'file_system_id' in params['options'][0]:
params['file_system_id'] = str(params['options'][0]['file_system_id'])

return 'show_fs_snapshot_general', params


def adapter_show_fs_snapshot_filesystem(params):
params = convertObj(params, "file_system_id")
return 'show_fs_snapshot_general', params


def adapter_show_fs_snapshot_schedule(params):
params = convertObj(params, "schedule_id")
if "file_system" in params:
params["file_system_id"] = str(params["file_system"].getProperty('id'))
pass
return params


def adapter_create_fs_snapshot_schedule(params):
if "file_system" in params:
params["file_system_id"] = str(params["file_system"].getProperty('id'))
pass
return params


def adapter_create_fs_snapshot_general(params):
file_system_id_list = []
if "file_system_list" in params:
for file_system in params['file_system_list']:
file_system_id_list.append(file_system.getProperty("id"))
pass
elif "file_system_id_list" in params:
file_system_id_list = params['file_system_id_list']

params["file_system_id_list"] = ','.join(str(i) for i in file_system_id_list)
return params


def adapter_change_file_system_worm(params):
return convertObj(params, "file_system_id")


def adapter_change_file_system_dedup_compress(params):
return convertObj(params, "file_system_id")


def adapter_change_file_system_general(params):
return convertObj(params, "file_system_id")


def adapter_delete_file_system_general(params):
if "object" in params:
params["file_system_id_list"] = [params["object"].getProperty("id")]
elif "object_id" in params:
params["file_system_id_list"] = [params["object_id"]]

if "file_system_obj_list" in params:
for obj in params["file_system_obj_list"]:
params["file_system_id_list"].append(obj.getProperty("id"))
pass

params['file_system_id_list'] = ','.join(str(i) for i in params["file_system_id_list"])
return params


def adapter_show_file_system_general(params):
params = convertObj(params, "file_system_id")
if "filterColumn" in params:
tmp = ""
for option in params["filterColumn"]:
tmp += option + ','
tmp += "ID"
pass
params['|filterColumn include columnList'] = tmp
return params


def adapter_show_fan(params):
return convertObj(params, "fan_id")


def adapter_show_expansion_module(params):
return convertObj(params, "expansion_module_id")


def adapter_show_enclosure(params):
return convertObj(params, "enclosure_id")


def adapter_change_disk_erase(params):
params = convertObj(params, "disk_id_list")
if "object_list" in params:
params['disk_id_list'] = list()
for obj in params["object_list"]:
params['disk_id_list'].append(str(obj.getProperty("id")))
pass
params["disk_id_list"] = ','.join(str(i) for i in params["disk_id_list"])
if 'disk_id_list' in params:
params["disk_id_list"] = ','.join(str(i) for i in params["disk_id_list"])
# 2018-03-29 wwx271515 适配新版本V500R007C20(V300R006C21)继承V500R007C10(V300R006C20)
# 2018-06-14 wwx271515 新增V300R006C30,继承V300R006C21
# 2018-08-07 wwx271515 新增V300R006C50&V500R007C30,继承V300R006C21
if ('V300R001C21' in version and 'Dorado' in productModel) or 'V300R006C10' in version or \
'V500R007C00' in version or 'V300R006C20' in version or 'V500R007C10' in version or \
'V300R006C21' in version or 'V500R007C20' in version or 'V300R006C30' in version or \
'V500R007C30' in version or 'V300R006C50' in version or 'V500R007C50' in version or\
'V300R006C60' in version or 'V500R008C00' in version or 'V500R007C60' in version or \
('V300R001C30' in version and 'Dorado' in productModel)\
or ('V300R002C20' in version and 'Dorado' in productModel):
params['isauto'] = True
return params


# 2018-03-29 wwx271515 适配新版本V500R007C20(V300R006C21)继承V500R007C10(V300R006C20)
# 2018-06-14 wwx271515 新增V300R006C30,继承V300R006C21
# 2018-08-07 wwx271515 新增V300R006C50&V500R007C30,继承V300R006C21
def adapter_change_disk_factory_reset(params):
params = convertObj(params, "disk_id")
if ('V300R001C21' in version and 'Dorado' in productModel) or 'V300R006C10' in version or \
'V500R007C00' in version or 'V300R006C20' in version or 'V500R007C10' in version or \
'V300R006C21' in version or 'V500R007C20' in version or 'V300R006C30' in version or \
'V300R006C50' in version or 'V500R007C30' in version or 'V300R006C60' in version or\
'V500R007C50' in version or 'V500R008C00' in version or 'V500R007C60' in version or \
('V300R001C30' in version and 'Dorado' in productModel):
params['isauto'] = True
return params


def adapter_show_disk_general(params):
return convertObj(params, "disk_id")


def adapter_change_hyper_metro_consistency_group_synchronize(params):
return convertObj(params, "consistency_group_id")


def adapter_change_hyper_metro_consistency_group_pause(params):
return convertObj(params, "consistency_group_id")


def adapter_show_hyper_metro_consistency_group_pair(params):
return convertObj(params, "consistency_group_id")


def adapter_remove_hyper_metro_consistency_group_pair(params):
params = convertObj(params, "consistency_group_id")
if "hyper_metro_pair_obj_list" in params:
for hyper_metro_pair_obj in params['hyper_metro_pair_obj_list']:
hyper_metro_pair_id = hyper_metro_pair_obj.getProperty('id')
params['pair_id'] = hyper_metro_pair_id
pass

return params


def adapter_add_hyper_metro_consistency_group_pair(params):
params = convertObj(params, "consistency_group_id")
if "hyper_metro_pair_obj_list" in params:
for hyper_metro_pair_obj in params['hyper_metro_pair_obj_list']:
hyper_metro_pair_id = hyper_metro_pair_obj.getProperty('id')
params['pair_id'] = hyper_metro_pair_id
pass

return params


def adapter_delete_hyper_metro_consistency_group(params):
return convertObj(params, "consistency_group_id")


def adapter_show_hyper_metro_consistency_group_general(params):
return convertObj(params, "consistency_group_id")


def adapter_delete_consistency_group(params):
return convertObj(params, "consistency_group_id")


def adapter_change_consistency_group_general(params):
return convertObj(params, "consistency_group_id")


def adapter_show_consistency_group_member(params):
return convertObj(params, "consistency_group_id")


def adapter_show_consistency_group_general(params):
return convertObj(params, "consistency_group_id")


def adapter_remove_consistency_group_remote_replication(params):
params = convertObj(params, "consistency_group_id")
if "remote_replication" in params:
params["remote_replication_id"] = params["remote_replication"].getProperty('id')
pass
return params


def adapter_add_consistency_group_remote_replication(params):
params = convertObj(params, "consistency_group_id")
if "remote_replication" in params:
params["remote_replication_id"] = params["remote_replication"].getProperty('id')
pass
return params


def adapter_create_hyper_metro_consistency_group_general(params):
if "domain_obj" in params:
params["domain_id"] = params['domain_obj'].getProperty('id')
pass
return params


def adapter_delete_clone(params):
return convertObj(params, "clone_id")


def adapter_change_clone_secondary_lun(params):
params = convertObj(params, "clone_id")
if "lun" in params:
params["lun_id"] = params["lun"].getProperty('id')
pass
return params


def adapter_change_clone_general(params):
return convertObj(params, "clone_id")


def adapter_show_clone_secondary_lun(params):
params = convertObj(params, "clone_id")
if "lun" in params:
params["lun_id"] = params["lun"].getProperty('id')
pass
return params


def adapter_show_clone_general(params):
params = convertObj(params, "clone_id")
if "lun" in params:
params["lun_id"] = params["lun"].getProperty('id')
pass
return params


def adapter_remove_clone_secondary_lun(params):
params = convertObj(params, "clone_id")
if "lun" in params:
params["lun_id"] = params["lun"].getProperty('id')
pass
return params


def adapter_add_clone_secondary_lun(params):
params = convertObj(params, "clone_id")
if "lun" in params:
params["lun_id"] = params["lun"].getProperty('id')
pass
return params


def adapter_create_clone(params):
if "lun" in params:
params["lun_id"] = params["lun"].getProperty('id')
pass
return params


def adapter_change_cache_partition_general(params):
return convertObj(params, "cache_partition_id")


def adapter_show_cache_partition_file_system(params):
return convertObj(params, "cache_partition_id")


def adapter_show_cache_partition_lun(params):
return convertObj(params, "cache_partition_id")


def adapter_remove_cache_partition_file_system(params):
params = convertObj(params, "cache_partition_id")
if 'fs_obj_list' in params:
params['file_system_id_list'] = []
for item in params['fs_obj_list']:
params['file_system_id_list'].append(str(item.getProperty('id')))

params['file_system_id_list'] = ','.join(str(i) for i in params["file_system_id_list"])
pass
return params


def adapter_remove_cache_partition_lun(params):
params = convertObj(params, "cache_partition_id")
if 'lun_obj_list' in params:
params['lun_id_list'] = []
for item in params['lun_obj_list']:
params['lun_id_list'].append(str(item.getProperty('id')))

params['lun_id_list'] = ','.join(str(i) for i in params["lun_id_list"])
pass
return params


def adapter_add_cache_partition_file_system(params):
params = convertObj(params, "cache_partition_id")
if 'fs_obj_list' in params:
params['file_system_id_list'] = []
for item in params['fs_obj_list']:
params['file_system_id_list'].append(str(item.getProperty('id')))

params['file_system_id_list'] = ','.join(str(i) for i in params["file_system_id_list"])
pass
return params


def adapter_add_cache_partition_lun(params):
params = convertObj(params, "cache_partition_id")
if 'lun_obj_list' in params:
params['lun_id_list'] = []
for item in params['lun_obj_list']:
params['lun_id_list'].append(str(item.getProperty('id')))

params['lun_id_list'] = ','.join(str(i) for i in params["lun_id_list"])
pass
return params


def adapter_show_bbu_file(params):
return convertObj(params, "cache_partition_id")


def adapter_show_cache_partition_general(params):
return convertObj(params, "bbu_id")


def adapter_show_bbu_general(param):
if 'object' in param:
param['object_id'] = param['object'].getProperty('id')
param['bbu_id'] = param['object_id']
del param['object']
del param['object_id']
elif "object_id" in param:
param['bbu_id'] = param['object_id']
del param['object_id']
elif 'options' in param and param['options']:
if isinstance(param["options"][0], dict) and 'object_id' in param['options'][0]:
param["object_id"] = param['options'][0]['object_id']
param['bbu_id'] = param['object_id']
del param['object_id']
return param

# return convertObj(params, "bbu_id")


def adapter_show_alarm(params):
if 'object_id' in params:
params['sequence'] = params['object_id']
pass
elif 'object' in params:
params['sequence'] = params['object'].getProperty("sequence")
pass

return params


def adapter_show_event(params):
if 'object_id' in params:
params['sequence'] = params['object_id']
pass
elif 'object' in params:
params['sequence'] = params['object'].getProperty("sequence")
pass
if 'sequence' not in params:
if not params.has_key('number'):
params['number'] = 100

return params


def adapter_change_alarm_clear(params):
if "sequence_list" in params or "object" in params:
if "sequence_list" not in params:
params['sequence_list'] = params['object'].getProperty('sequence')
pass
return params


def adapter_create_schedule(params):
schedule_type = params.get("type")
if schedule_type:
pass
else:
schedule_type = "monitor"
params = convertObjProp(params, {"storage_pool": {"propName": "id", "newName": "pool_id"},
"storage_pool_id": {"newName": "pool_id"}})
return "create_schedule_" + schedule_type, params


def adapter_show_port_general(params):
params = convertObj(params, "port_id")
return "show_port_general", params


def adapter_change_event_restore(params):
event_type = params.get("type")
if event_type:
pass
else:
event_type = "address"
return "change_event_restore" + event_type, params


def adapter_change_user_lock_or_unlock(params):
lock_type = params.get("type")
if lock_type:
pass
else:
lock_type = "unlock"
return "change_user_" + lock_type, params


def adapter_delete_cache_partition(params):
return convertObj(params, "cache_partition_id")


def adapter_change_clone(params):
operation_type = params.get("operation")
if operation_type:
pass
else:
operation_type = "restore"
lunIdList = []
if "lun_list" in params:
for lun in params['lun_list']:
lunIdList.append(str(lun.getProperty("id")))
pass
if "lun_id_list" in params:
lunIdList.extend(params["lun_id_list"])
pass
if lunIdList:
if operation_type == "split":
params["lun_id_list"] = ",".join(str(x) for x in lunIdList)
else:
params["lun_id"] = ",".join(str(x) for x in lunIdList)
params = convertObj(params, "clone_id")
return "change_clone_" + operation_type, params


def adapter_create_consistency_group(params):
var = choseCmd(params, "type", "asynchronization")
return "create_consistency_group_" + var, params


def adapter_change_consistency_group(params):
var = choseCmd(params, "type", "asynchronization")
params = convertObj(params, "consistency_group_id")
return "change_consistency_group_" + var, params


def adapter_change_fs_snapshot(params):
var = choseCmd(params, "operation", "restore")
params = convertObj(params, "snapshot_id")
return "change_fs_snapshot_" + var, params


def adapter_show_host(params):
var = choseCmd(params, "obj_type", "lun")
return "show_host_" + var, params


def adapter_show_initiator(params):
return "show_initiator", params


def adapter_change_initiator(params):
return "change_initiator", params


def adapter_add_port(params):
var = choseCmd(params, "ip_type", "ipv4")
return "add_port_" + var + "_route", params


def adapter_change_port(params):
var = choseCmd(params, "ip_type", "ipv4")
return "change_port_" + var + "_address", params


def adapter_remove_port(params):
ip_or_route = choseCmd(params, "ip_or_route", "address")
var = choseCmd(params, "ip_type", "ipv4")
return "remove_port_" + var + "_" + ip_or_route, params


def adapter_remove_remote_device_link(params):
var = choseCmd(params, "link_type", "fc")
params = convertObjProp(params, {"fc_link": {"propName": "id", "newName": "fc_link_id"},
"iscsi_link": {"propName": "id", "newName": "iscsi_link_id"}})
return "remove_remote_device_link_" + var, params


def adapter_change_quota(params):
var = choseCmd(params, "quota_object", "quota_tree")
params = convertName(params, {"quota_object_id": var + "_id"})
return "change_quota_" + var, params


def adapter_create_quota(params):
var = choseCmd(params, "quota_object", "quota_tree")
params = convertName(params, {"quota_object_id": var + "_id"})
return "create_quota_" + var, params


def adapter_change_snmp_version(params):
v1v2c_switch = params.get("v1v2c_switch_on", False)
if v1v2c_switch:
v1v2c_switch = "On"
else:
v1v2c_switch = "Off"
params["v1v2c_switch"] = v1v2c_switch
return params


def adapter_add_snmp_usm(params):
if "authenticate_protocol" not in params:
params["authenticate_protocol"] = "NONE"
if "private_protocol" not in params:
params["private_protocol"] = "NONE"
return params


def adapter_change_isns_server_ip(params):
return convertName(params, {"server_ip": "ip"})


def adapter_change_snmp_usm(params):
if "authenticate_protocol" not in params:
params["authenticate_protocol"] = "NONE"
if "private_protocol" not in params:
params["private_protocol"] = "NONE"
return params


def adapter_change_snmp_port(params):
return convertName(params, {"port": "port_number"})


def adapter_show_port(params):
return "show_port_general", params


def adapter_create_upgrade(params):
return "create_upgrade_session", params


def adapter_scan_virtual_machine_block(params):
return convertObj(params, "owner_container_id")


def adapter_change_vm_container_general(params):
return convertObj(params, "owner_container_id")


# 2018-03-29 wwx271515 适配新版本V500R007C20(V300R006C21)继承V500R007C10(V300R006C20)
# 2018-06-14 wwx271515 新增V300R006C30,继承V300R006C21
# 2018-08-07 wwx271515 新增V300R006C50&V500R007C30,继承V300R006C21
def adapter_delete_vm_fs_general(params):
params = convertObj(params, "vm_fs_id")
if ('V300R001C21' in version and 'Dorado' in productModel) or 'V300R006C10' in version or \
'V500R007C00' in version or 'V300R006C20' in version or 'V500R007C10' in version or \
'V300R006C21' in version or 'V500R007C20' in version or 'V300R006C30' in version or \
'V500R007C30' in version or 'V300R006C50' in version or 'V300R006C60' in version or \
'V500R007C50' in version or 'V500R008C00' in version or 'V500R007C60' in version or \
('V300R001C30' in version and 'Dorado' in productModel):
params['isauto'] = True
return params


def adapter_restore_vm_fs_general(params):
return convertObj(params, "vm_fs_id")


def adapter_change_vm_fs_general(params):
return convertObj(params, "vm_fs_id")


def adapter_show_vm_fs_general(params):
return convertObj(params, "vm_fs_id")


def adapter_remove_remote_device_white_list(params):
return convertObj(params, "record_id")


def adapter_show_port_fibre_module(params):
return convertObj(params, "port_id")


# def adapter_show_failover_group_general(params):
# obj = params.get('object', None)
# if obj is not None:
# params['failover_group_id'] = obj.getProperty("failover_group_id")
# return params
#
# def adapter_show_power_supply(params):
# obj = params.get('object', None)
# if obj is not None:
# params['power_supply_id'] = obj.getProperty("power_supply_id")
# return params
=======================================================================================
#!/usr/bin/python
# -*- coding: UTF-8 -*-

"""
功 能: 提供新方法和老方法的方法名对应关系

版权信息: 华为技术有限公司，版权所有(C) 2014-2015

修改记录: 2016/6/6 严旭光 y00292329 created

"""
#!/usr/bin/python
# -*- coding: UTF-8 -*-

"""
功 能: 提供新方法和老方法的方法名对应关系

版权信息: 华为技术有限公司，版权所有(C) 2014-2015

修改记录: 2016/6/2 严旭光 y00292329 created

"""
WrapperHash = {
#Disk Domain
"diskDomainCreate": "create_disk_domain",
"diskDomainAddDisk": "add_disk_domain_disk",
"diskDomainShowGeneral": "show_disk_domain_general",
"diskDomainShowAvailableCapacity": "show_disk_domain_available_capacity",
"diskDomainShowFormat": "show_disk_domain_format",
"diskDomainShowLun": "show_disk_domain_lun",
"diskDomainShowSecureVideo": "show_disk_domain_securevideo",
"diskDomainShowTask": "show_disk_domain_task",
"diskDomainChangeRekey": "change_disk_domain_rekey",
"diskDomainSet": "change_disk_domain_general",
"diskDomainChangeForceRecon": "change_disk_domain_force_recon",
"diskDomainChangeLeveling": "change_disk_domain_leveling",
"diskDomainChangeMetaBackup": "change_disk_domain_meta_backup",
"diskDomainChangeRepairEnvStatus": "change_disk_domain_repair_env_status",
"diskDomainChangeRepairPoolMeta": "change_disk_domain_repair_pool_meta",
"diskDomainChangeReportCKIsolate": "change_disk_domain_report_ck_isolate",
"diskDomainChangeStripeRestoreBGR": "change_disk_domain_stripe_restore_bgr",
"diskDomainChangeStripeRestoreData": "change_disk_domain_stripe_restore_data",
"diskDomainChangeStripeRestoreRepair": "change_disk_domain_stripe_restore_repair",
"diskDomainDelete": "delete_disk_domain",
"showDiskInDomain": "show_disk_in_domain",
#Storage Pool
"storagePoolShowReconstructionSpeed": "show_storage_pool_reconstruction_speed",
"storagePoolShowRelocationSpeed": "show_storage_pool_relocation_speed",
"storagePoolShowGeneral": "show_storage_pool_general",
"storagePoolShowTier": "show_storage_pool_tier",
"storagePoolReconstructionSpeedSet": "change_storage_pool_reconstruction_speed",
"storagePoolRelocationScheduleSet": "change_storage_pool_relocation_schedule",
"storagePoolRelocationSpeedSet": "change_storage_pool_relocation_speed",
"storagePoolSSDEnabledSet": "change_storage_pool_ssd_enabled",
"storagePoolGeneralSet": "change_storage_pool_general",
"storagePoolDelete": "delete_storage_pool",
"storagePoolCreate": "create_storage_pool",
"storagePoolAdd": "add_storage_pool_tier",
#Lun
"lunCreate": "create_lun",
"lunShow": "show_lun_general",
"lunDedupCompressShow": "show_lun_dedup_compress",
"lunSet": "change_lun",
"lunDelete": "delete_lun",
"lunShowLunGroup": "show_lun_lun_group",
"lunDestroyCreate": "create_lun_destroy_data",
"lunDestroyDelete": "delete_lun_destroy_data",
#Interface module
"interfaceModuleShowGeneral": "show_interface_module",
"interfacePowerOn": "poweron_interface_module",
"interfacePowerOff": "poweroff_interface_module",
#Iscsi
"iscsiTargetCreate": "create_iscsi_target",
"iscsiTargetDelete": "delete_iscsi_target",
"iscsiInitiatorNameShow": "show_iscsi_initiator_name",
"iscsiTargetChange": "change_iscsi_target",
#iSNS
"isnsChange": "change_isns_server_ip",
"isnsShow": "show_isns_server_ip",
"isnsDelete": "delete_isns_server_ip",
#KeyMgmtCenter
"kmcShowGeneral": "show_kmc_general",
"kmcDelete": "delete_kmc_general",
"kmcAddGeneral": "add_kmc_general",
"kmcTestConnect": "add_kmc_test",
#LDAP Domain
"ldapDomainShowConfiguration": "show_ldap_configuration",
"ldapDomainCreateConfiguration": "create_ldap_configuration",
"ldapDomainDeleteConfiguration": "delete_ldap_configuration",
"ldapDomainChangeConfiguration": "change_domain_ldap_config",
"adDomainChangeConfiguration": "change_domain_ad_config",
"changeDnsServerGeneral": "change_dns_server_general",
"mirrorDomainSet": "change_mirror_domain_general",
"ldapChangeConfiguration": "change_ldap_configuration",
#License

#Logical Port
"logicalPortGeneralShow": "show_logical_port_general",
"logicalPortCountShow": "show_logical_port_count",
"logicalPortRouteShow": "show_logical_port_route",
"logicalPortRouteAdd": {"method": "adapter_add_logical_port", "extra": {"ip_or_route": "route"}},#多对一的关系
"logicalPortCreate": {"method": "adapter_create_logical_port"},# 多对一的关系
"logicalPortSet": "change_logical_port_general",
"logicalPortDelete": "delete_logical_port_general",
"logicalPortRouteRemove": {"method": "adapter_remove_logical_port"},# 多对一的关系
#LunCopy
"lunCopyCreate": {"method": "adapter_create_lun_copy"},# 多对一的关系
"lunCopyAdd": {"method": "adapter_add_lun_copy"},# 多对一的关系
"lunCopyRemove": {"method": "adapter_remove_lun_copy"},# 多对一的关系
"lunCopyShow": "show_lun_copy_general",
"lunCopyShowMember": "show_lun_copy_member",
"lunCopySet": "change_lun_copy_general",
"lunCopyOperation": "change_lun_copy_session",
"lunCopyDelete": "delete_lun_copy",
#lunGroup
"lunGroupShowLun": "show_lun_group_lun",
"lunGroupShowLunSnapshot": "show_lun_group_snapshot",
"lunGroupShow": "show_lun_group_general",
"lunGroupCreate": "create_lun_group",
"lunGroupAdd": "add_lun_group_lun",
"remove_lun_group_lun": "remove_lun_group_lun",
"lunGroupDelete": "delete_lun_group",
"lunGroupSet": "change_lun_group",
"lunGroupShowMappingView": "show_lun_group_mapping_view",
#lunMigration
"lunMigrationShow": "show_lun_migration_general",
"lunMigrationCreate": "create_lun_migration",
"lunMigrationSet": "change_lun_migration",
"lunMigrationDelete": "delete_lun_migration",
"lunMigrationSplit": "change_lun_migration_split_consistency",
#mappingView
"mappingViewShow": "show_mapping_view_general",
"mappingViewCreate": "create_mapping_view",
"mappingViewAdd": {"method": "adapter_add_mapping_view"},# 多对一的关系
"mappingViewRemove": {"method": "adapter_remove_mapping_view"},# 多对一的关系
"mappingViewDelete": "delete_mapping_view",
"mappingViewSet": "change_mapping_view",
#mirrorCopy
"mirrorCopyShow": "show_mirror_copy_general",
"mirrorCopySet": "change_mirror_copy_general",
"mirrorCopyOperation": {"method": "adapter_change_mirror_copy"},# 多对一的关系
#mirrorLun
"mirrorLunShow": "show_mirror_lun_general",
"mirrorLunCreate": "create_mirror_lun",
"mirrorCopyAdd": {"method": "adapter_add_mirror_lun"},# 多对一的关系
"mirrorCopyRemove": "remove_mirror_lun_mirror_copy",
"mirrorLunDelete": "delete_mirror_lun",
"mirrorLunShowCopy": "show_mirror_copy_general",#TODO 一对多的关系
#ndmp
"ndmpShowService": "show_service_ndmp",
"ndmpChangeUser": "change_service_ndmp_user",
"ndmpResetPassword": "change_service_ndmp_reset_password",#TODO 需要输入密码
#notification
"changeNotificationSyslog": "change_notification_syslog",
"showNotificationSyslog": "show_notification_syslog",
#OceanStorVritualMachine
"oceanStorVirtualMachineCreate": "create_virtual_machine_general",
"oceanStorVirtualMachineShow": "show_virtual_machine_general",
"oceanStorVirtualMachineSet": "change_virtual_machine_general",
"oceanStorVirtualMachineDelete": "delete_virtual_machine_general",
"oceanStorVirtualMachinePowerOn": "poweron_virtual_machine",
"oceanStorVirtualMachinePowerOff": "poweroff_virtual_machine",
"oceanStorVirtualMachinePause": "pause_virtual_machine",
"oceanStorVirtualMachineReboot": "reboot_virtual_machine",
"oceanStorVirtualMachineResume": "resume_virtual_machine",
"oceanStorVirtualMachineAdd": {"method": "adapter_add_virtual_machine"}, # 多对一的关系
"oceanStorVirtualMachineRemove": {"method": "adapter_remove_virtual_machine"},# 多对一的关系
"vhbaShow": "show_vhba_general",
"hostInitiatorShow": "show_vhost_initiator_general",
"hostInitiatorAdd": "add_host_vhost_initiator",
"hostInitiatorRemove": "remove_host_vhost_initiator",
"hostInitiatorSet": "change_vhost_initiator_general",
"vmToolsShow": "show_vmtools_general",# TODO 回显解析复杂
"vmToolsDelete": "delete_vmtools_general",
"vmToolsUpgrade": "upgrade_virtual_machine_vmtools",
"vmPortShow": "show_virtual_machine_port",
"vmIsoShow": "show_vm_iso_general",# TODO 回显解析复杂
"vmIsoDelete": "delete_vm_iso_general",
"vmFsFileTransferenceChange": "change_vm_file_transference",
"vmFsFileTransferenceShow": "show_vm_file_transference_status",
"vmFsFileTransferencePathShow": "show_vm_file_transference_path",# TODO 回显解析复杂
"vmBlockShow": "show_virtual_machine_block",
"vmBlockScan": "scan_virtual_machine_block",
"vmTemplateCreate": "create_vm_template_general",
"vmTemplateDelete": "delete_vm_template_general",
"vmTemplateShow": "show_vm_template_general",# TODO 回显解析复杂
"vmFailbackSwitchSet": "change_virtual_machine_failback_switch",
"vmFailbackSwitchShow": "show_virtual_machine_failback_switch",
"vmFailbackSessionCreate": "create_virtual_machine_failback_session",

#User
"userShow": "show_user",
"userChange": "change_user",
"userDelete": "delete_user",
"userAdd": "create_user",
"UserSafeStrategyShow": "show_safe_strategy",
"userSafeStrategyChange": "change_safe_strategy",

#trap
"trapShow": "show_notification_trap",
"trapDelete": "delete_notification_trap",
"trapAdd": "add_notification_trap",

#lun_takeover
"lunTakeOverCreate": "create_lun_takeover_general",
"lunTakeOverRemove": "remove_lun_takeover_general",
"lunTakeOverShow": "show_lun_takeover_general",

#storageEngine
"storageEngineShow": "show_storage_engine",

#snmp
"snmpShowPort": "show_snmp_port",
"snmpShowVersion": "show_snmp_version",
"snmpShowUsm": "show_snmp_usm",
"snmpShowSafeStrategy": "show_snmp_safe_strategy",
"snmpShowContextName": "show_snmp_context_name",
"snmpDeleteUsm": "delete_snmp_usm",
"snmpChangeV1v2cVersionStatus": "change_snmp_version",
"snmpChangeUsm": "change_snmp_usm",
"snmpChangePort": "change_snmp_port",
"snmpChangeSafeStrategy": "change_snmp_safe_strategy",
"snmpChangeCommunity": "change_snmp_community",
"snmpAddUsm":"add_snmp_usm",

#powerSupply
"powerSupplyShow" :"show_power_supply",

#performance
"performanceShowStatisticEnabled" :"show_performance_statistic_enabled",
"performanceShowController" :"show_performance_controller",
"performanceChangeStrategy" :"change_performance_strategy",
"performanceChangeStatisticEnabled" :"change_performance_statistic_enabled",
"performanceChangeRestore" :"change_performance_restore",

#quorum
"quorumServerCreate" :"create_quorum_server_general",
"quorumServerDelete" :"delete_quorum_server_general",
"quorumServerLinkAdd" :"add_quorum_server_link_general",
"quorumServerLinkRemove" :"remove_quorum_server_link_general",
"quorumServerLinkShow" :"show_quorum_server_link_general",
"quorumServerSet" :"change_quorum_server_general",
"quorumServerShow" :"show_quorum_server_general",

#remoteLun
"remoteLunScan" :"scan_remote_lun",

#schedule
"storagePoolScheduleCreate":{"method": "adapter_create_schedule"},#一对多
"storagePoolScheduleDelete": "delete_schedule",
"storagePoolScheduleSet": "change_schedule",
"storagePoolScheduleShow": "show_schedule",

#smis
"changeSmisConfiguration":"change_smis_configuration",
"changeSmisStatus": "change_smis_status",
"showSmisConfiguration": "show_smis_configuration",
"showSmisStatus": "show_smis_status",

#snapshot
"snapShotCreate":"create_snapshot_general",
"snapShotDelete": "delete_snapshot",
"snapShotDuplicateCreate": "create_snapshot_duplicate",
# "snapShotOperation": "",#一对多
# "snapShotSet": "",#一对多
"snapshotShow": "show_snapshot_general",
"snapshotShowLunGroup": "show_snapshot_lun_group",

#smartQos
"smartQosFilesystemShow":"show_smartqos_policy_file_system",
"smartQosLunShow": "show_smartqos_policy_lun",
"smartQosPolicyAddFileSystem": "add_smartqos_policy_file_system",
"smartQosPolicyAddLun": "add_smartqos_policy_lun",
"smartQosPolicyRemoveFileSystem": "remove_smartqos_policy_file_system",
"smartQosPolicyRemoveLun": "remove_smartqos_policy_lun",
"smartQosPolicyChangeEnabled": "change_smartqos_policy_enabled",
"smartQosPolicyCreate": "create_smartqos_policy",
"smartQosPolicyDelete": "delete_smartqos_policy",
"smartQosPolicyShowGeneral": "show_smartqos_policy_general",

#service
"ftpShowService": "show_service_ftp",
"homeDirChangeEnabled": "change_homedir_enabled",
"homeDirChangeGeneral": "change_homedir_general",
"homeDirShowGeneral": "show_homedir_general",
"nasSwitch": "change_mirror_domain_general",
"serviceChangeCifs": "change_service_cifs",
"serviceChangeFtp": "change_service_ftp",
"serviceChangeNfs": "change_service_nfs",

#Quota
"quotaChangeGeneral": "change_quota_general",
"quotaChangeObject": {"method": "adapter_change_quota"},#一对多
"quotaChangeQuotaTree": "change_quota_tree_general",
"quotaCreate": {"method": "adapter_create_quota"},#一对多
"quotaCreateQuotaTree": "create_quota_tree_general",
"quotaDeleteObject": "delete_quota_general",
"quotaDeleteQuotaTree": "delete_quota_tree_general",
"quotaShowGeneral": "show_quota_general",
"quotaShowQuotaTreeGeneral": "show_quota_tree_general",

#smartCache
"smartCachePartitionAddFilesystem": "add_smart_cache_partition_file_system",
"smartCachePartitionAddLun": "add_smart_cache_partition_lun",
"smartCachePartitionCreate": "create_smart_cache_partition",
"smartCachePartitionDelete": "delete_smart_cache_partition",
"smartCachePartitionFilesystemShow": "show_smart_cache_partition_file_system",
"smartCachePartitionLunShow": "show_smart_cache_partition_lun",
"smartCachePartitionRemoveFilesystem": "remove_smart_cache_partition_file_system",
"smartCachePartitionRemoveLun": "remove_smart_cache_partition_lun",
"smartCachePartitionSet": "change_smart_cache_partition_general",
"smartCachePoolAddDisk": "add_smart_cache_pool_disk",
"smartCachePartitionShow": "show_smart_cache_partition_general",
"smartCachePoolDiskShow": "show_smart_cache_pool_disk",
"smartCachePoolRemoveDisk": "remove_smart_cache_pool_disk",
"smartCachePoolShow": "show_smart_cache_pool_general",

#resource
"adgroupAdd": "add_resource_group_ad_group",
"aduserAdd": "add_resource_group_ad_user",
"domainadShow": "show_domain_ad",
"resourceGroupCreate": "create_resource_group",
"resourceGroupDelete": "delete_resource_group",
"resourceGroupGeneralShow": "show_resource_group_general",
"resourceUserCreate": "create_resource_user_general",
"resourceUserDelete": "delete_resource_user",
"resourceUserGeneralShow": "show_resource_user_general",
"resourceUserPasswdSet": "change_resource_user_password",
"resourceUserSafeStrategyChange": "change_resource_user_safe_strategy",
"resourceUserSafeStrategyShow": "show_resource_user_safe_strategy",
"resourceUserSet": "change_resource_user_general",

#remoteReplication
"remoteReplicationChangeFileSystem": "change_remote_replication_file_system",
"remoteReplicationChangeSecondFsAccess": "change_remote_replication_second_fs_access",
"remoteReplicationChangeSplit": "change_remote_replication_split",
"remoteReplicationChangeSynchronize": "change_remote_replication_synchronize",
"remoteReplicationCreateVerificationSession": "create_remote_replication_verification_session",
"remoteReplicationDelete": "delete_remote_replication",
"remoteReplicationCreateRefresh": "create_remote_replication_refresh",
"remoteReplicationCreateUnified": "create_remote_replication_unified",
"remoteReplicationSwap": "swap_remote_replication",
"remoteReplicationShowUnified": "show_remote_replication_unified",
"remoteReplicationShowAvailableFs": "show_remote_replication_available_file_system",
"remoteReplicationShowGeneral": "show_remote_replication_general",
"remoteReplicationChangeGeneral": "change_remote_replication_general",

#share
"shareCifsCreate": "create_share_cifs",
"shareCifsDelete": "delete_share_cifs",
"shareCifsSet": "change_share_cifs",
"shareCifsShow": "show_share_cifs",
"shareNfsCreate": "create_share_nfs",
"shareNfsDelete": "delete_share_nfs",
"shareNfsShow": "show_share_nfs",
"sharePermissionCifsCreate": "create_share_permission_cifs",
"sharePermissionCifsDelete": "delete_share_permission_cifs",
"sharePermissionCifsSet": "change_share_permission_cifs",
"sharePermissionCifsShow": "show_share_permission_cifs",
"sharePermissionNfsCreate": "create_share_permission_nfs",
"sharePermissionNfsDelete": "delete_share_permission_nfs",
"sharePermissionNfsSet": "change_share_permission_nfs",
"sharePermissionNfsShow": "show_share_permission_nfs",

#remotedevice
"remoteDeviceAdd": "add_remote_device_link_fc",
"remoteDeviceAddIscsiLink": "add_remote_device_link_iscsi",
"remoteDeviceCreate": "create_remote_device_general",
"remoteDeviceDelete": "delete_remote_device",
"remoteDeviceELinkShow": "show_remote_device_elink",
"remoteDeviceEthLinkSet": "change_remote_device_link",
"remoteDeviceFcLinkSet": "change_remote_device_link",
"remoteDeviceEthLinkShow": "show_remote_device_link",
"remoteDeviceFcLinkShow": "show_remote_device_link",
"remoteDeviceLunShow": "show_remote_lun_general",
"remoteDeviceRemove": {"method": "adapter_remove_remote_device_link"},#一对多
"remoteDeviceSet": "change_remote_device_general",
"remoteDeviceSetPwd": "change_remote_device_user_password",
"remoteDeviceShow": "show_remote_device_general",
"remoteDeviceWhiteListChange": "change_remote_device_white_list",
"remoteDeviceWhiteListShow": "show_remote_device_white_list",
"scanRemoteLun": "scan_remote_lun",

#port
"portGroupAddPort": "add_port_group_port",
"portGroupCreate": "create_port_group",
"portGroupDelete": "delete_port_group",
"portGroupRemovePort": "remove_port_group_port",
"portGroupShowGeneral": "show_port_group_general",
"portGroupShowMappingView": "show_mapping_view_port_group",
"portGroupShowPort": "show_port_group_port",

"portLogicalAddRoute": {"method": "adapter_add_logical_port", "extra": {"ip_or_route": "route"}},#一对多
"portLogicalChangeFailback": "change_logical_port_failback",
"portLogicalChangeFailoverGroup": "change_logical_port_failover_group",
"portLogicalChangeGeneral": "change_logical_port_general",
"portLogicalCreate": "",#一对多
"portLogicalDelete": "delete_logical_port_general",
"portLogicalRemoveRoute": "remove_logical_port_ipv4_route",
"portLogicalShowCount": "show_logical_port_count",
"portLogicalShowGeneral": "show_logical_port_general",
"portLogicalShowRoute": "show_logical_port_route",

"portVlanCreate": "create_vlan_general",
"portVlanDelete": "delete_vlan_general",
"portVlanModify": "change_vlan_general",
"portVlanSet": "change_vlan_general",
"portVlanShowCount": "show_vlan_count",
"portVlanShowGeneral": "show_vlan_general",

"portBondCreate": "create_bond_port",
"portBondDelete": "delete_bond_port",
"portBondSet": "change_bond_port_general",
"portBondShow": "show_bond_port",

"portAddRoute": {"method": "adapter_add_port"},#add_port_ipv4_route,add_port_ipv6_route
"portChangeIP": {"method": "adapter_change_port"},#change_port_ipv4_address, change_port_ipv6_address
"portEthMtuSet": "change_port_eth",
"portFCSet": "change_port_fc",
"portRemoveIP": {"method": "adapter_remove_port", "extra": {"ip_or_route": "address"}},#remove_port_ipv4_address, remove_port_ipv6_address
"portRemoveRoute": {"method": "adapter_remove_port", "extra": {"ip_or_route": "route"}},#remove_port_ipv4_route, remove_port_ipv6_route
"portSASEnabledSet": "change_port_enabled",

"portShowBitError": "show_port_bit_error",
"portShowFibreModule": "show_port_fibre_module",
"portShowGeneral": "show_port_general",
"portShowIP": "show_port_ip",
"portShowInitiator": "show_port_initiator",
"portShowRoute": "show_port_route",

"portShowSASGeneral": {"method": "adapter_show_port", "extra": {"physical_type": "SAS"}},#多对一
"portShowComGeneral": {"method": "adapter_show_port", "extra": {"physical_type": "COM"}},#多对一
"portShowEthGeneral": {"method": "adapter_show_port", "extra": {"physical_type": "ETH"}},#多对一
"portShowFCGeneral": {"method": "adapter_show_port", "extra": {"physical_type": "FC"}},#多对一
"portShowFcoeGeneral": {"method": "adapter_show_port", "extra": {"physical_type": "FCoE"}},#多对一
"portShowIbGeneral": "show_ib_port_general",
"portShowPcieGeneral": {"method": "adapter_show_port", "extra": {"physical_type": "PCIE"}},#多对一

#system
"acuShow": "show_assistant_cooling_unit",
"changeFdsaSwitch": "change_fdsa_switch",
"changeMediaScan": "change_system_media_scan",
"changeSystemSSHPort": "change_system_server_port",
"checkSystemOperationLog": "show_event",
"configurationDataClear": "clear_configuration_data",
"configurationDataImport": "export_configuration_data",
"configurationDataRestore": "restore_configuration_data",
"controllerReboot": "reboot_controller",
"controllerShowGeneral": "show_controller_general",
"showEvent": "show_event",
"showFdsaSwitch": "show_fdsa_switch",
"showMediaScan": "show_system_media_scan",
"systemAddSecurityRule": "add_security_rule",
"systemCreateUser": "create_user",
"systemDelSecurityRule": "delete_security_rule",
"systemDeleteNotificationTrap": "delete_notification_trap",
"systemDeleteUser": "delete_user",
"systemImportLicense": "import_license",
"systemPowerOff": "poweroff_system",
"systemReboot": "reboot_system",
"systemRebootValidPassword": "reboot_system",

"systemChangeEventRestore": {"method": "adapter_change_event_restore"} , #一对多:change_event_restore_address ,change_event_restore_enabled
"systemChangeManagementIp": "change_system_management_ip",
"systemChangeMmUser": "change_mm_user_synchronize",
"systemChangeNTP": "change_system_ntp",
"systemChangeNotificationEmail": "change_notification_email",
"systemChangeNotificationSms": "change_notification_sms",
"systemChangeNotificationSyslog": "change_notification_syslog",
"systemChangeNotificationTrap": "change_notification_trap",
"systemChangePerformanceRestore": "change_performance_restore",
"systemChangeSecurityRuleStatus": "change_security_rule_enabled",
"systemChangeTime": "change_system_time",
"systemChangeTimezone": "change_system_timezone",
"systemChangeUser": "change_user",
"systemChangeUserLock": {"method": "adapter_change_user_lock_or_unlock"},#一对多:change_user_unlock,change_user_lock
"systemChangeUserNotes": "clear_configuration_data",
"systemChangeUserOffline": "change_user",
"systemChangeUserPassword": "change_user_password",

"systemChangeUserReview": "change_safe_strategy",#多对一
"systemChangePwdComplex": "change_safe_strategy",#多对一
"systemChangePwdLength": "change_safe_strategy",#多对一
"systemChangePwdLock": "change_safe_strategy",#多对一
"systemChangeInactiveLock": "change_safe_strategy",#多对一


"systemExportCliHistory": "export_cli_history",
"systemExportConfigurationData": "export_configuration_data",
"systemExportEvent": "export_event",
"systemExportLicense": "export_license",
"systemExportLogFile": "export_logfile",
"systemExportPerformanceFile": "export_performance_file",
"systemExportRunningData": "export_running_data",

"systemShowBstConfigration": "show_bst_configuration",
"systemShowCLiHistory": "show_cli_history",
"systemShowConfigModel": "show_system_config_model",
"systemShowConfigurationDataBackup": "show_configuration_data_backup",
"systemShowDST": "show_system_dst",
"systemShowGeneral": "show_system_general",
"systemShowLicense": "show_license",
"systemShowLicenseActive": "show_license_active",
"systemShowNTP": "show_system_ntp",
"systemShowNotification": "show_notification_trap",
"systemShowPackage": "show_upgrade_package",
"systemShowPerformanceFile": "show_performance_file",
"systemShowSafeStrategy": "show_safe_strategy",
"systemShowTimezone": "show_system_timezone",
"systemShowUser": "show_user",

#chenbeiyun
"alarmEventShowAlarm" : "show_alarm",
"alarmEventShowEvent" : "show_event",
"alarmEventChangeAlarmClear" : "change_alarm_clear",
"alarmEventCreateAlarmTest" : "create_alarm_test",

"bbuShow":"show_bbu_general",
"bbuRemainLife":"show_bbu_life",

"createCachePartition":"create_cache_partition",
"cachePartitionShow":"show_cache_partition_general",
"cachePartitonRemove": "delete_cache_partition",
"cachePartitionAddLun":"add_cache_partition_lun",
"cachePartitionAddFs":"add_cache_partition_file_system",
"cachePartitionRemoveLun":"remove_cache_partition_lun",
"cachePartitionRemoveFs":"remove_cache_partition_file_system",
"cachePartitionShowLun":"show_cache_partition_lun",
"cachePartitionShowFs":"show_cache_partition_file_system",
"cachePartitionChange":"change_cache_partition_general",

"certificateImport":"import_certificate",
"certificateSSLImport":"import_ssl_certificate",
"certificateChangePassword":"change_certificate_password",
"certificateChangePrewarningTime":"change_certificate_prewarning_time",
"certificateSSLChangePassphrase":"change_ssl_certificate_passphrase",
"certificateRestore":"restore_ssl_certificate",
"certificateShowGeneral":"show_certificate_general",

"cliChange":"change_cli",

"cloneCreate":"create_clone",
"cloneAdd":"add_clone_secondary_lun",
"cloneRemove":"remove_clone_secondary_lun",
"cloneShow":"show_clone_general",
"cloneShowSecondaryLun":"show_clone_secondary_lun",
"cloneSet":"change_clone_general",
"cloneSecondaryLunSet":"change_clone_secondary_lun",
"cloneOperation":{"method": "adapter_change_clone"},
"cloneDelete":"delete_clone",

"diagnoseCodeShow":"show_diagnose_code",

"consistencyGroupCreate": {"method": "adapter_create_consistency_group"},
"hyperMetroConsistGroupCreate":"create_hyper_metro_consistency_group_general",
"consistencyGroupAdd":"add_consistency_group_remote_replication",
"consistencyGroupRemove":"remove_consistency_group_remote_replication",
"consistencyGroupShow":"show_consistency_group_general",
"consistencyGroupShowMember":"show_consistency_group_member",
"consistencyGroupSet":"change_consistency_group_general",
"consistencyGroupOperation": {"method": "adapter_change_consistency_group"},
"consistencyGroupDelete":"delete_consistency_group",
"hyperMetroConsistencyGroupShow":"show_hyper_metro_consistency_group_general",
"hyperMetroConsistencyGroupRemove":"delete_hyper_metro_consistency_group",
"hyperMetroPairAdd":"add_hyper_metro_consistency_group_pair",
"hyperMetroPairRemove":"remove_hyper_metro_consistency_group_pair",
"hyperMetroGroupPairShow":"show_hyper_metro_consistency_group_pair",
"hyperMetroConsistencyGroupPause":"change_hyper_metro_consistency_group_pause",
"hyperMetroConsistencyGroupSync":"change_hyper_metro_consistency_group_synchronize",

"deviceManagerShowEnclosure":"show_enclosure",
"deviceManagerShowControllerGeneral":"show_controller_general",
"deviceManagerShowInterface":"show_interface_module",
"deviceManagerPowerOnInterface":"poweron_interface_module",
"deviceManagerPowerOffInterface":"poweroff_interface_module",
"deviceManagerShowCPU":"show_cpu",
"deviceManagerChangeCPUFrequency":"change_cpu_frequency",
"deviceManagerShowPowerSupply":"show_power_supply",
"deviceManagerShowFan":"show_fan",
"deviceManagerShowBBUGeneral":"show_bbu_general",
"deviceManagerShowBBULife":"show_bbu_life",
"icmpSwitchChange":"change_icmp_switch",

"diskShowGeneral":"show_disk_general",
"diskChangeLight":"change_disk_light",
"diskChangePrecopy":"change_disk_precopy",
"diskChangeRoutineTest":"change_disk_routine_test",
"diskShowInDomain":"show_disk_in_domain",
"diskShowSystem":"show_disk_system",
"diskShowBST":"show_disk_bad_sector_record",
"diskChangeErase":"change_disk_erase",

"enclosureShow":"show_enclosure",
"controllerEnclosureShow":"show_enclosure",
"diskEnclosureShow":"show_enclosure",
"changeEnclosureLight":"change_enclosure_light",

"expansionModuleShowGeneral":"show_expansion_module",

"fanShow":"show_fan",

"filesystemShow":"show_file_system_general",
"filesystemDelete":"delete_file_system_general",
"filesystemCreate":"create_file_system_general",
"filesystemGeneralSet":"change_file_system_general",
"filesystemDedupCompressSet":"change_file_system_dedup_compress",
"filesystemEnabledSet":"change_file_system_enabled",
"filesystemWormSet":"change_file_system_worm",
"filesystemSnapshotShow":{"method": "adapter_show_fs_snapshot_filesystem"},

"fsSnapshotCreate":"create_fs_snapshot_general",
"fsSnapshotScheduleCreate":"create_fs_snapshot_schedule",
"fsSnapshotScheduleShow":"show_fs_snapshot_schedule",
#"fsSnapshotShow":"show_fs_snapshot_general",
"fsSnapshotShow":{"method": "adapter_show_fs_snapshot_snapshot"},
"fsSnapshotSet":"change_fs_snapshot_general",
"fsScheduleSet":"change_fs_snapshot_schedule",
"fsSnapshotOperation":{"method": "adapter_change_fs_snapshot"},
"fsSnapshotDelete":"delete_fs_snapshot_general",
"fsSnapshotScheduleDelete":"delete_fs_snapshot_schedule",

"hostShowGeneral":"show_host_general",
"hostShowObject":{"method": "adapter_show_host"},
"hostShowInitiator":"show_initiator",
"hostShowHostGroup":"show_host_host_group",
"hostCreate":"create_host",
"hostSet":"change_host",
"hostDelete":"delete_host",
# "hostAddInitiator":["add_host_initiator","add_host_vhost_initiator","add_host_ib_initiator"],
# "hostRemoveInitiator":"",
"hostGroupShowGeneral":"show_host_group_general",
"hostGroupShowMappingView":"show_host_group_mapping_view",
# "hostShowHostGroupOperation":"",
"hostGroupCreate":"create_host_group",
"hostGroupSet":"change_host_group_general",
"hostGroupDelete":"delete_host_group",
"hostGroupAddHost":"add_host_group_host",
"hostGroupRemoveHost":"remove_host_group_host",
"hostShowHostAutoScan":"show_host_auto_scan",
"hostChangeHostAutoScan":"change_host_auto_scan",

"hyperMetroDomainShow":"show_hyper_metro_domain_general",
"hyperMetroDomainCreate":"create_hyper_metro_domain_general",
"hyperMetroQuorumServerAdd":"add_hyper_metro_domain_quorum_server",
"hyperMetroQuorumServerRemove":"remove_hyper_metro_domain_quorum_server",
"hyperMetroDomainDelete":"delete_hyper_metro_domain_general",

"hyperMetroPairShow":"show_hyper_metro_pair_general",
"hyperMetroPairCreate":"create_hyper_metro_pair_unified",
"hyperMetroPairSynchronize":"change_hyper_metro_pair_synchronize",
"hyperMetroPairPause":"change_hyper_metro_pair_pause",
"hyperMetroPairSet":"change_hyper_metro_pair_general",
"hyperMetroPairPrioritySet":"change_hyper_metro_pair_priority",
"hyperMetroPairStart":"change_hyper_metro_pair_start",
"hyperMetroPairDelete":"delete_hyper_metro_pair_general",

"HyperVaultShow":"delete_hypervault_general",
"HyperVaultCreate":"create_hypervault_general",
"HyperVaultChange":"change_hypervault_general",
"HyperVaultStart":"change_hypervault_start",
"HyperVaultDelete":"delete_hypervault_general",
"HyperVaultAddRes":"add_hypervault_remote_resource",
"HyperVaultRemoveRes":"remove_hypervault_remote_resource",

"HyperVaultPolicyCreate":"create_hypervault_policy_general",
"HyperVaultPolicyShow":"show_hypervault_policy_general",
"HyperVaultPolicyChange":"change_hypervault_policy_general",
"HyperVaultPolicyDelete":"delete_hypervault_policy_general",

"HyperVaultJobShow":"show_hypervault_job_general",
"HyperVaultJobResume":"change_hypervault_job_resume",
"HyperVaultJobPause":"change_hypervault_job_pause",
"HyperVaultJobCancel":"change_hypervault_job_cancel",
"HyperVaultCopyShow":"show_hypervault_copy_general",
"HyperVaultCopyDelete":"delete_hypervault_copy_general",
"HyperVaultCopyRestore":"change_hypervault_copy_restore",

"initiatorCreateFC":"create_initiator_fc",
"initiatorCreateIB":"create_ib_initiator_general",
"initiatorCreateISCSI":"create_initiator_iscsi",
"initiatorShowFC": {"method": "adapter_show_initiator", "extra": {"initiator_type": "FC"}},
"initiatorShowIB":"show_ib_initiator_general",
"initiatorShowISCSI":{"method": "adapter_show_initiator", "extra": {"initiator_type": "iSCSI"}},
"initiatorIBSet":"change_ib_initiator_general",
"initiatorFCSet":{"method": "adapter_change_initiator", "extra": {"initiator_type": "FC"}},
"initiatorISCSISet":{"method": "adapter_change_initiator", "extra": {"initiator_type": "iSCSI"}},
"initiatorDeleteISCSI":"delete_initiator_iscsi",
"initiatorDeleteFC":"delete_initiator_fc",
"initiatorDeleteIB":"delete_ib_initiator_general",


#Alarm
"rootCauseAlarmAddRule":"add_root_cause_alarm_rule",
"rootCauseAlarmChangeRule":"change_root_cause_alarm_rule",
"rootCauseAlarmDeleteRule":"delete_root_cause_alarm_rule",
"rootCauseAlarmShowRule":"show_root_cause_alarm_rule",
"shakeAlarmAddGeneral":"add_shake_alarm_general",
"shakeAlarmChangeGeneral":"change_shake_alarm_general",
"shakeAlarmShowGeneral":"show_shake_alarm_general",

"showInnerEvent":"show_event",
"enclosurePowerOn":"poweron_enclosure",
"lunChange":"change_lun",
"lunDeveloperShow":"show_event",

"diskDomainChangeFormat":"change_disk_domain_format",
"leakExtentRecycle":"change_disk_domain_verify_pool_meta",
"leakExtentVerify":"change_disk_domain_verify_pool_meta",

"oemImportPackage":"import_oem_package",
"oemPackageRestore":"restore_oem_package",

"remoteDeviceWhiteListAdd":"add_remote_device_white_list",
"remoteDeviceWhiteListRemove":"remove_remote_device_white_list",
"snmpShowStatus":"show_snmp_status",
"snmpChangeStatus":"change_snmp_status",

"showGrainAlloc":"show_space_grain_alloc",
"showGrainQueue":"show_space_grain_extent_queue",
"showStatisticInfo":"show_space_statistic_info",
"storagePoolChangeAnalysis":"change_storage_pool_analysis",

"addPatch": {"method": "adapter_create_upgrade", "extra": {"session": "hotpatch"}},
"deletePatch":"delete_hotpatch",
"restorePatch":"restore_hotpatch",
"showUpgradeStatus":"show_upgrade_status",
# "upgradeSystem":{"method": "adapter_create_upgrade", "extra": {"session": "system"}},

"diskPowerOn":"poweron_disk",
"diskChangeDiagnose":"change_ssd_diagswitch",
"diskChangeDiskIn":"change_disk_diskin",
"diskChangePrefail":"change_disk_prefail",
"diskChangeRebuild":"", # 没有命令
"diskShowDiagnoseStatus":"change_ssd_diagswitch",
"diskChangeReset":"change_disk_reset",
"diskPowerOff":"poweroff_disk",
"diskRestore":"restore_disk_general",
"renewDisk":"", # 没有命令

"clearPortBitError":"clear_port_bit_error",
"maintenancePortChangeIP":"change_system_maintenance_ip",
"managementPortChangeIP":"change_system_management_ip",
"portChangeEthNetworkSegment":"change_port_eth_network_segment",
"portChangeFastWriteOption":"change_port_fast_write_option",
"portChangeRunningType":"change_port_eth",
"portEnabledSet":"change_port_enabled",
"removeMaintenancePortIP":"",# 没有命令
"removeManagementPortIP":"",# 没有命令

"vcpuIsolateSwitchChange":"",
"vcpuIsolateSwitchShow":"",
"vmContainerEnlargeVmFs":"scan_virtual_machine_block",
"vmContainerSet":"change_vm_container_general",
"vmContainerShow":"show_vm_container_general",
"vmFsCreate":"create_vm_fs_general",
"vmFsDelete":"delete_vm_fs_general",
"vmFsRestore":"restore_vm_fs_general",
"vmFsSet":"change_vm_fs_general",
"vmFsShow":"show_vm_fs_general",
"vmServiceSet":"change_vm_service_general",
"vmServiceShow":"show_vm_service_general",

"deleteLicense":"delete_license",
"difVerifyLevelChange":"change_dif_verify_level_general",
"diskDomainMetaBackupChange":"change_disk_domain_meta_backup",
"fdsaCheckItemShow":"show_fdsa_check_item",
"fdsaCheckItemSwitchChange":"change_fdsa_check_item_switch",
"iotraceSwitchChange":"change_iotrace_switch",
"iotraceSwitchShow":"show_iotrace_switch",
"lunTakeoverChange":"change_lun_takeover_disable_switch_path",
"privateDeviceProportionChange":"change_private_device_proportion",
"rebootISM":"reboot_ism",
"systemChangeCache":"change_system_cache",
"systemExportConfigurationCoffer":"export_configuration_coffer",
"systemRestoreFactoryMode":"restore_system_factory_mode",

"showDhaScorestrategy":"",
"showDhaSinglemodelconfig":"",
"showSystemTLVChannel":"",
"changeDhaSinglemodelconfig":"",# 没有命令
"changeDifGeneralSwitch":"",# 没有命令
"changeSystemTLVChannel":"",# 没有命令
"dhaScorestrategyChange":"",


}

MethodHash = {
# 'UniAutos.Component.StorageEngine.Huawei.OceanStor.StorageEngine': {
# "show": "show_storage_engine",
# "detail": {
# 'param': "storage_engine_id"
# }
# },
# 'UniAutos.Component.Controller.Huawei.OceanStor.StorController': {
# "show": "show_controller_general",
# "detail": {
# 'param': "controller_id"
# }
# },
# 'UniAutos.Component.Lun.Huawei.OceanStor.PoolLun': {
# "show": "show_lun_general",
# "update": "change_lun",
# "create": "create_lun",
# "delete": "delete_lun",
# "detail": {
# 'param': "lun_id"
# }
# },
# 'UniAutos.Component.MirrorLun.Huawei.OceanStor.MirrorLun': {
# "show": "show_mirror_lun_general",
# "create": "create_mirror_lun",
# "delete": "delete_mirror_lun",
# "detail": {
# 'param': "mirror_lun_id"
# }
# },
# 'UniAutos.Component.MirrorCopy.Huawei.OceanStor.MirrorCopy': {
# "show": "show_mirror_copy_general",
# "update": "change_mirror_copy_general",
# "delete": "remove_mirror_lun_mirror_copy",
# "detail": {
# 'param': "mirror_copy_id"
# },
# "partial": True
# },
# 'UniAutos.Component.HyperMetroPair.Huawei.OceanStor.HyperMetroPair': {
# "show": "show_hyper_metro_pair_general",
# "update": "change_hyper_metro_pair_general",
# "create": "create_hyper_metro_pair_unified",
# "delete": "delete_hyper_metro_pair_general",
# "detail": {
# 'param': "pair_id"
# }
# },
# 'UniAutos.Component.HyperMetroDomain.Huawei.OceanStor.HyperMetroDomain': {
# "show": "show_hyper_metro_domain_general",
# "update": "change_hyper_metro_domain_general",
# "create": "create_hyper_metro_domain_general",
# "delete": "delete_hyper_metro_domain_general",
# "detail": {
# 'param': "domain_id"
# }
# },
# 'UniAutos.Component.Enclosure.Huawei.OceanStor.ControllerEnclosure.ControllerEnclosure': {
# "show": "show_enclosure",
# "detail": {
# 'param': "enclosure_id"
# }
# },
# 'UniAutos.Component.Enclosure.Huawei.OceanStor.DiskEnclosure.DiskEnclosure': {
# "show": "show_enclosure",
# "detail": {
# 'param': "disk_enclosure_id"
# }
# },
# 'UniAutos.Component.Bbu.Huawei.OceanStor.Bbu': {
# "show": "show_bbu_general",
#
# "detail": {
# 'param': "bbu_id"
# }
# },
# 'UniAutos.Component.Fan.Huawei.OceanStor.Fan': {
# "show": "show_fan",
# "detail": {
# 'param': "fan_id"
# }
# },
# 'UniAutos.Component.Copy.Huawei.OceanStor.Lun.Copy': {
# "show": "show_lun_copy_general",
# "update": "change_lun_copy_general",
# "create": ["create_lun_copy_local", "create_lun_copy_remote"],
# "delete": "delete_lun_copy",
# "detail": {
# 'param': "lun_copy_id"
# }
# },
# 'UniAutos.Component.LunMigration.Huawei.OceanStor.LunMigration': {
# "show": "show_lun_migration_general",
# "update": "change_lun_migration",
# "create": "create_lun_migration",
# "delete": "delete_lun_migration",
# "detail": {
# 'param': "lun_migration_id"
# }
# },
# 'UniAutos.Component.Clone.Huawei.OceanStor.Lun.Clone': {
# "show": "show_clone_general",
# "update": "change_clone_general",
# "create": "create_clone",
# "delete": "delete_clone",
# "detail": {
# 'param': "clone_id"
# }
# },
# 'UniAutos.Component.Snapshot.Huawei.OceanStor.Lun.Snapshot': {
# "show": "show_snapshot_general",
# "create": "create_snapshot_general",
# "delete": "delete_snapshot",
# "detail": {
# 'param': "snapshot_id"
# }
# },
# 'UniAutos.Component.Snapshot.Huawei.OceanStor.Filesystem.Snapshot': {
# "show": {"method": "show_fs_snapshot_general", "partial": True},
# "update": "change_fs_snapshot_general",
# "create": "create_fs_snapshot_general",
# "delete": "delete_fs_snapshot_general",
# "detail": {
# 'param': "fs_snapshot_id"
# }
# },
# 'UniAutos.Component.HostResource.Huawei.OceanStor.HostResource': {
# "show": "show_host_general",
# "update": "change_host",
# "create": "create_host",
# "delete": "delete_host",
# "detail": {
# 'param': "host_id"
# }
# },
# 'UniAutos.Component.HostResourceGroup.Huawei.OceanStor.HostResourceGroup': {
# "show": "show_host_group_general",
# "update": "change_host_group_general",
# "create": "create_host_group",
# "delete": "delete_host_group",
# "detail": {
# 'param': "host_group_id"
# }
# },
# 'UniAutos.Component.BondPort.Huawei.OceanStor.BondPort': {
# "show": "show_bond_port",
# "update": "change_bond_port_general",
# "create": "create_bond_port",
# "delete": "delete_bond_port",
# "detail": {
# 'param': "bond_port_id"
# }
# },
# 'UniAutos.Component.PortGroup.Huawei.OceanStor.PortGroup': {
# "show": "show_port_group_general",
# "update": "change_port_group_general",
# "create": "create_port_group",
# "delete": "delete_port_group",
# "detail": {
# 'param': "port_group_id"
# }
# },
# 'UniAutos.Component.Initiator.Huawei.OceanStor.FiberChannel.Initiator': {
# "show": "show_initiator",
# "update": "change__initiator",
# "create": "create_initiator_fc",
# "delete": "delete_initiator_fc",
# "detail": {
# 'param': "wwn"
# }
# },
# 'UniAutos.Component.Initiator.Huawei.OceanStor.Iscsi.Initiator': {
# "show": {"method": "adapter_show_initiator", "extra": {"initiator_type": "iSCSI"}},
# "update": "change__initiator",
# "create": "create_initiator_iscsi",
# "delete": "delete_initiator_iscsi",
# "detail": {
# 'param': "iscsi_iqn_name"
# }
# },
# 'UniAutos.Component.Initiator.Huawei.OceanStor.Infiniband.Initiator': {
# "show": "show_ib_initiator_general",
# "update": "change_ib_initiator_general",
# "create": "create_ib_initiator_general",
# "delete": "delete_ib_initiator_general",
# "detail": {
# 'param': "wwn"
# }
# },
# # 'UniAutos.Component.Initiator.InitiatorBase.InitiatorBase': {
# # "show": "show_ib_initiator_general",
# # "update": "change_initiator_general",
# # "create": "create_initiator",
# # "delete": "delete_initiator",
# # "detail": {
# # 'param': "initiator_id"
# # }
# # },
# 'UniAutos.Component.ConsistencyGroup.Huawei.OceanStor.Lun.ConsistencyGroup': {
# "show": "show_consistency_group_general",
# "update": "change_consistency_group_general",
# "create": ["create_consistency_group_synchronization",
# "create_consistency_group_asynchronization",
# "create_consistency_group_verification_session"],
# "delete": "delete_consistency_group",
# "detail": {
# 'param': "consistency_group_id"
# }
# },
# 'UniAutos.Component.ConsistencyGroup.Huawei.OceanStor.HyperMetroPair.HyperMetroConsistencyGroup': {
# "show": "show_hyper_metro_consistency_group_general",
# "update": "change_hyper_metro_consistency_group_general",
# "create": "create_hyper_metro_consistency_group_general",
# "delete": "delete_hyper_metro_consistency_group",
# "detail": {
# 'param': "consistency_group_id"
# }
# },
# 'UniAutos.Component.Snapshot.Huawei.OceanStor.Schedule.Schedule': {
# "show": "show_fs_snapshot_schedule",
# "update": "change_fs_snapshot_schedule",
# "create": "create_fs_snapshot_schedule",
# "delete": "delete_fs_snapshot_schedule",
# "detail": {
# 'param': "schedule_id"
# }
# },
# 'UniAutos.Component.Schedule.Huawei.OceanStor.StoragePool.Schedule': {
# "show": "show_schedule",
# "update": "change_schedule",
# "create": ["create_schedule_relocate", "create_schedule_monitor"],
# "delete": "delete_schedule",
# "detail": {
# 'param': "schedule_id"
# }
# },
# 'UniAutos.Component.Link.Huawei.OceanStor.Ethernet.Link': {
# "show": {"method": "show_remote_device_link", "extra": {"link_type": "iSCSI"}},
# "update": "change_remote_device_link",
# "detail": {
# 'param': "link_id",
# "extra": {"link_type": "iSCSI"}
# }
# },
# 'UniAutos.Component.Link.Huawei.OceanStor.FiberChannel.Link': {
# "show": {"method": "show_remote_device_link", "extra": {"link_type": "FC"}},
# "update": "change_remote_device_link",
# "detail": {
# 'param': "link_id",
# "extra": {"link_type": "FC"}
# }
# },
# 'UniAutos.Component.RemoteDevice.Huawei.OceanStor.RemoteDevice.RemoteDevice': {
# "show": "show_remote_device_general",
# "update": "change_remote_device_general",
# "create": "create_remote_device_general",
# "delete": "delete_remote_device",
# "detail": {
# 'param': "remote_device_id"
# }
# },
# 'UniAutos.Component.DiskDomain.Huawei.OceanStor.DiskDomain': {
# "show": "show_disk_domain_general",
# "update": "change_disk_domain_general",
# "create": "create_disk_domain",
# "delete": "delete_disk_domain",
# "detail": {
# 'param': "disk_domain_id"
# }
# },
# 'UniAutos.Component.Disk.Huawei.OceanStor.Disk': {
# "show": "show_disk_general",
# "detail": {
# 'param': "disk_id"
# }
# },
# 'UniAutos.Component.Filesystem.Huawei.OceanStor.Filesystem': {
# "show": "show_file_system_general",
# "update": "change_file_system_general",
# "create": "create_file_system_general",
# "delete": "delete_file_system_general",
# "detail": {
# 'param': "file_system_id"
# }
# },
# 'UniAutos.Component.Vlan.Huawei.OceanStor.Vlan': {
# "show": "show_vlan_general",
# "update": "change_vlan_general",
# "create": "create_vlan_general",
# "delete": "delete_vlan_general",
# "detail": {
# 'param': "vlan_id"
# }
# },
# 'UniAutos.Component.StoragePool.Huawei.OceanStor.StoragePool': {
# "show": "show_storage_pool_general",
# "update": "change_storage_pool_general",
# "create": "create_storage_pool",
# "delete": "delete_storage_pool",
# "detail": {
# 'param': "pool_id"
# }
# },
# 'UniAutos.Component.LunGroup.Huawei.OceanStor.LunGroup': {
# "show": "show_lun_group_general",
# "update": "change_lun_group",
# "create": "create_lun_group",
# "delete": "delete_lun_group",
# "detail": {
# 'param': "lun_group_id"
# }
# },
# 'UniAutos.Component.MappingView.Huawei.OceanStor.MappingView': {
# "show": "show_mapping_view_general",
# "update": "change_mapping_view",
# "create": "create_mapping_view",
# "delete": "delete_mapping_view",
# "detail": {
# 'param': "mapping_view_id"
# }
# },
# 'UniAutos.Component.Port.Huawei.OceanStor.Sas.Port': {
# "show": {"method": "adapter_show_port", "extra": {"physical_type": "SAS"}},
# "detail": {
# 'param': "port_id"
# }
# },
# 'UniAutos.Component.Port.Huawei.OceanStor.FiberChannel.Port': {
# "show": {"method": "adapter_show_port", "extra": {"physical_type": "FC"}},
# "detail": {
# 'param': "port_id"
# }
# },
# 'UniAutos.Component.Port.Huawei.OceanStor.Ethernet.Port': {
# "show": {"method": "adapter_show_port", "extra": {"physical_type": "ETH"}},
# "detail": {
# 'param': "port_id"
# }
# },
# 'UniAutos.Component.Port.Huawei.OceanStor.Com.Port': {
# "show": {"method": "adapter_show_port", "extra": {"physical_type": "COM"}},
# "detail": {
# 'param': "port_id"
# }
# },
# 'UniAutos.Component.Port.Huawei.OceanStor.Fcoe.Port': {
# "show": {"method": "adapter_show_port", "extra": {"physical_type": "FCoE"}},
# "detail": {
# 'param': "port_id"
# }
# },
# 'UniAutos.Component.Port.Huawei.OceanStor.Pcie.Port': {
# "show": {"method": "adapter_show_port", "extra": {"physical_type": "PCIE"}},
# "detail": {
# 'param': "port_id"
# }
# },
# 'UniAutos.Component.Port.Huawei.OceanStor.Infiniband.Port': {
# "show": "show_ib_port_general",
# "detail": {
# 'param': "ib_port_id"
# }
# },
# 'UniAutos.Component.ResourceGroup.Huawei.OceanStor.ResourceGroup': {
# "show": "show_resource_group_general",
# "create": "create_resource_group",
# "delete": "delete_resource_group",
# "detail": {
# 'param': "group_id"
# }
# },
# 'UniAutos.Component.ResourceUser.Huawei.OceanStor.ResourceUser': {
# "show": "show_resource_user_general",
# "update": "change_resource_user_general",
# "create": "create_resource_user_general",
# "delete": "delete_resource_user",
# "detail": {
# 'param': "resource_user_id"
# }
# },
# 'UniAutos.Component.SmartCachePartition.Huawei.OceanStor.SmartCachePartition': {
# "show": "show_smart_cache_partition_general",
# "update": "change_smart_cache_partition_general",
# "create": "create_smart_cache_partition",
# "delete": "delete_smart_cache_partition",
# "detail": {
# 'param': "smart_cache_partition_id"
# }
# },
# 'UniAutos.Component.SmartCachePool.Huawei.OceanStor.SmartCachePool': {
# "show": "show_smart_cache_pool_general",
# "detail": {
# 'param': "smart_cache_pool_id"
# }
# },
# 'UniAutos.Component.Share.Cifs.Huawei.OceanStor.CifsShare': {
# "show": "show_share_cifs",
# "update": "change_share_cifs",
# "create": "create_share_cifs",
# "delete": "delete_share_cifs",
# "detail": {
# 'param': "share_id"
# }
# },
# 'UniAutos.Component.Share.Nfs.Huawei.OceanStor.NfsShare': {
# "show": "show_share_nfs",
# "update": "change_share_nfs",
# "create": "create_share_nfs",
# "delete": "delete_share_nfs",
# "detail": {
# 'param': "share_id"
# }
# },
# 'UniAutos.Component.SharePermission.Cifs.Huawei.OceanStor.CifsSharePermission': {
# "show": {"method": "show_share_permission_cifs", "partial": True},
# "update": "change_share_permission_cifs",
# "create": "create_share_permission_cifs",
# "delete": "delete_share_permission_cifs",
# "detail": {
# 'param': "share_permission_id"
# }
# },
# 'UniAutos.Component.SharePermission.Nfs.Huawei.OceanStor.NfsSharePermission': {
# "show": {"method": "show_share_permission_nfs", "partial": True},
# "update": "change_share_permission_nfs",
# "create": "create_share_permission_nfs",
# "delete": "delete_share_permission_nfs",
# "detail": {
# 'param': "share_permission_id"
# }
# },
# 'UniAutos.Component.LogicalPort.Huawei.OceanStor.LogicalPort': {
# "show": "show_logical_port_general",
# "update": "change_logical_port_general",
# "create": ["create_logical_port_eth",
# "create_logical_port_bond",
# "create_logical_port_vlan"],
# "delete": "delete_logical_port_general",
# "detail": {
# 'param': "logical_port_name",
# "properties": "name"
# }
# },
# 'UniAutos.Component.Snmp.Huawei.OceanStor.Snmp': {
# "show": "show_snmp_status",
# "update": "change_snmp",
# "create": "create_snmp",
# "delete": "delete_snmp",
# "detail": {
# 'param': "user_name"
# }
# },
# 'UniAutos.Component.InterfaceModule.Huawei.OceanStor.InterfaceModule': {
# "show": "show_interface_module",
# "update": "change_interface_module",
# "detail": {
# 'param': "interface_module_id"
# }
# },
# 'UniAutos.Component.ExpansionModule.Huawei.OceanStor.ExpansionModule': {
# "show": "show_expansion_module",
# "detail": {
# 'param': "expansion_module_id"
# }
# },
# 'UniAutos.Component.OceanStorVirtualMachine.Huawei.OceanStor.VirtualMachine.OsVirtualMachine': {
# "show": "show_virtual_machine_general",
# "update": "change_virtual_machine_general",
# "create": "create_virtual_machine_general",
# "delete": "delete_virtual_machine_general",
# "detail": {
# 'param': "vm_id"
# }
# },
# 'UniAutos.Component.OceanStorVirtualMachine.Huawei.OceanStor.VmFs.VmFs': {
# "show": "show_vm_fs_general",
# "update": "change_vm_fs_general",
# "create": "create_vm_fs_general",
# "delete": "delete_vm_fs_general",
# "detail": {
# 'param': "vm_fs_id"
# }
# },
# 'UniAutos.Component.OceanStorVirtualMachine.Huawei.OceanStor.Vhba.Vhba': {
# "show": "show_vhba_general",
# "detail": {
# 'param': "vhba_id"
# }
# },
# 'UniAutos.Component.OceanStorVirtualMachine.Huawei.OceanStor.HostInitiator.HostInitiator': {
# "show": "show_vhost_initiator_general",
# "update": "change_vhost_initiator_general",
# "detail": {
# 'param': "wwn"
# }
# },
# 'UniAutos.Component.OceanStorVirtualMachine.Huawei.OceanStor.VmPort.VmPort': {
# "show": "show_virtual_machine_port",
# "detail": {
# 'param': "vm_id"
# }
# },
# 'UniAutos.Component.OceanStorVirtualMachine.Huawei.OceanStor.VmIso.VmIso': {
# "show": "show_vm_iso_general",
# "delete": "delete_vm_iso_general",
# "detail": {
# 'param': "vm_fs_id"
# }
# },
# 'UniAutos.Component.OceanStorVirtualMachine.Huawei.OceanStor.VmTools.VmTools': {
# "show": "show_vmtools_general",
# "delete": "delete_vmtools_general",
# "detail": {
# 'param': "vm_fs_id"
# }
# },
# 'UniAutos.Component.OceanStorVirtualMachine.Huawei.OceanStor.VmBlock.VmBlock': {
# "show": "show_virtual_machine_block",
# "detail": {
# 'param': "vm_id"
# }
# },
# 'UniAutos.Component.OceanStorVirtualMachine.Huawei.OceanStor.VmContainer.VmContainer': {
# "show": "show_vm_container_general",
# "update": "change_vm_container_general",
# "detail": {
# 'param': "container_id"
# }
# },
# 'UniAutos.Component.AlarmEvent.Alarm.Huawei.OceanStor.Alarm': {
# "show": "show_alarm",
# "detail": {
# 'param': "alarm_id"
# }
# },
# 'UniAutos.Component.AlarmEvent.Event.Huawei.OceanStor.Event': {
# "show": "show_event",
# "detail": {
# 'param': "event_id"
# }
# },
# 'UniAutos.Component.Trap.Huawei.OceanStor.Trap': {
# "show": "show_notification_trap",
# "update": "change_notification_trap",
# "delete": "delete_notification_trap",
# "detail": {
# 'param': "server_id"
# }
# },
# 'UniAutos.Component.OceanStorVirtualMachine.Huawei.OceanStor.VmTemplate.VmTemplate': {
# "show": "show_vm_template_general",
# "create": "create_vm_template_general",
# "delete": "delete_vm_template_general",
# "detail": {
# 'param': "vm_fs_id"
# }
# },
# 'UniAutos.Component.OceanStorVirtualMachine.Huawei.OceanStor.VmFile.VmFile': {
# "show": "show_vm_file_transference_status",
# "update": "change_vm_file_transference",
# "detail": {
# 'param': "file_name"
# }
# },
# 'UniAutos.Component.CachePartition.Huawei.OceanStor.CachePartition': {
# "show": "show_cache_partition_general",
# "update": "change_cache_partition_general",
# "create": "create_cache_partition",
# "delete": "delete_cache_partition",
# "detail": {
# 'param': "cache_partition_id"
# }
# },
# 'UniAutos.Component.RemoteReplication.Huawei.OceanStor.RemoteReplication': {
# "show": "show_remote_replication_unified",
# "detail": {
# 'param': "remote_replication_id"
# }
# },
# 'UniAutos.Component.HyperVault.Huawei.OceanStor.HyperVault.HyperVault': {
# "show": "show_hypervault_general",
# "update": "change_hypervault_general",
# "create": "change_hypervault_policy_general",
# "delete": "delete_hypervault_general",
# "detail": {
# 'param': "hypervault_id"
# }
# },
# 'UniAutos.Component.HyperVault.Huawei.OceanStor.HyperVaultPolicy.HyperVaultPolicy': {
# "show": "show_hypervault_policy_general",
# "update": "change_hypervault_policy_general",
# "create": "create_hypervault_policy_general",
# "delete": "delete_hypervault_policy_general",
# "detail": {
# 'param': "hypervault_policy_id"
# }
# },
# 'UniAutos.Component.HyperVault.Huawei.OceanStor.HyperVaultJob.HyperVaultJob': {
# "show": "show_hypervault_job_general",
# "update": ["change_hypervault_job_cancel",
# "change_hypervault_job_pause",
# "change_hypervault_job_resume"],
# "detail": {
# 'param': "job_id"
# }
# },
# 'UniAutos.Component.HyperVault.Huawei.OceanStor.HyperVaultCopy.HyperVaultCopy': {
# "show": "show_hypervault_copy_general",
# "update": "change_hypervault_copy_general",
# "delete": "delete_hypervault_copy_general",
# "detail": {
# 'param': "copy_id"
# }
# },
# # 'UniAutos.Component.Performance.Huawei.OceanStor.Performance': {
# # "show": "show_performance_general",
# # "update": "change_performance_general",
# # "create": "create_performance",
# # "delete": "delete_performance",
# # "detail": {
# # 'param': "performance_id"
# # }
# # },
# 'UniAutos.Component.QuotaTree.Huawei.OceanStor.QuotaTree': {
# "show": "show_quota_tree_general",
# "update": "change_quota_tree_general",
# "create": "create_quota_tree_general",
# "delete": "delete_quota_tree_general",
# "detail": {
# 'param': "quota_tree_id"
# }
# },
# 'UniAutos.Component.User.Huawei.OceanStor.User': {
# "show": "show_user",
# "update": "change_user",
# "create": "create_user",
# "delete": "delete_user",
# "detail": {
# 'param': "user_name"
# }
# },
# 'UniAutos.Component.SmartQos.Policy.Huawei.OceanStor.SmartQosPolicy': {
# "show": "show_smartqos_policy_general",
# "update": "change_smartqos_policy_general",
# "create": "create_smartqos_policy",
# "delete": "delete_smartqos_policy",
# "detail": {
# 'param': "smart_qos_policy_id"
# }
# },
# 'UniAutos.Component.KeyMgmtCenter.Huawei.OceanStor.KeyMgmtCenter': {
# "show": "show_kmc_general",
# "delete": "delete_kmc_general",
# "detail": {
# 'param': "id"
# }
# },
# # 'UniAutos.Component.Upgrade.Huawei.OceanStor.Upgrade': {
# # "show": "show_upgrade_package",
# # "update": "change_upgrade_flow",
# # "create": "create_upgrade_session",
# # "detail": {
# # 'param': ""
# # }
# # },
# 'UniAutos.Component.RemoteDevice.Huawei.OceanStor.WhiteList.WhiteList': {
# "show": "show_remote_device_white_list",
# "update": "change_remote_device_white_list",
# "detail": {
# 'param': "record_id"
# }
# },
# 'UniAutos.Component.Iscsi.Huawei.OceanStor.Iscsi': {
# "show": "show_iscsi_initiator_name",
# "create": "create_iscsi_target",
# "delete": "delete_iscsi_target",
# "detail": {
# 'param': "iscsi_id"
# }
# },
# 'UniAutos.Component.QuorumServer.Huawei.OceanStor.QuorumServer': {
# "show": "show_quorum_server_general",
# "update": "change_quorum_server_general",
# "create": "create_quorum_server_general",
# "delete": "delete_quorum_server_general",
# "detail": {
# 'param': "server_id"
# }
# },
# 'UniAutos.Component.TakeOverLun.Huawei.OceanStor.TakeOverLun': {
# "show": "show_lun_takeover_general",
# "create": "create_lun_takeover_general",
# "detail": {
# 'param': "lun_id"
# }
# },
'UniAutos.Component.Vstore.Huawei.OceanStor.Vstore': {
"show": "show_vstore",
"create": "create_vstore_general",
"delete": "delete_vstore_general",
"detail": {
'param': "id"
}
},
'UniAutos.Component.HyperMetroVstorePair.Huawei.OceanStor.HyperMetroVstorePair': {
"show": "show_hyper_metro_vstore_pair_general",
"create": "create_hyper_metro_vstore_pair_general",
"delete": "delete_hyper_metro_vstore_pair_general",
"detail": {
'param': "pair_id"
}
},
'UniAutos.Component.FailoverGroup.Huawei.OceanStor.FailoverGroup': {
"show": "show_failover_group_general",
"create": "create_failover_group_general",
"update": "change_failover_group_general",
"delete": "delete_failover_group_general",
"detail": {
'param': "failover_group_id"
}
},
'UniAutos.Component.FibreModule.Huawei.OceanStor.FibreModule': {
"show": "show_port_fibre_module",
"detail": {
'param': "port_id"
}
},
'UniAutos.Component.SharePermission.Ftp.Huawei.OceanStor.FtpSharePermission': {
"show": "show_share_permission_ftp",
"create": "create_share_permission_ftp",
"update": "change_share_permission_ftp",
"delete": "delete_share_permission_ftp",
"detail": {
'param': "user_id"
}
},

'UniAutos.Component.Power.Huawei.OceanStor.Power': {
"show": "show_power_supply",
"detail": {
'param': "power_supply_id"
}
}
}
==============================================================================================
#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Function: Provides a base class for command encapsulation echo parsing
"""

import re

from UniAutos.Util.TypeCheck import validateParam

GETMETHOD = 'getmethod'
SETMETHOD = 'setmethod'
PROPERTY = 'properties'
GLOBAL = 'global'


class WrapperBase(object):
"""Wrapper class initialization

Args:
param (dict): param = {"versionInfo": (str)}

Attributes:
None

Returns:
None

Raises:
None

Examples:
None

"""
def __init__(self, param=None):

super(WrapperBase, self).__init__()
if param and "versionInfo" in param:
self.versionInfo = param["versionInfo"]

def setDevice(self, device):
"""Bind the wrapper to the device

Args:
Device (obj): specific device object

Returns:
None

Raises:
None

Examples:
None

"""

if hasattr(self, "device"):
return
self.device = device

def getDevice(self):
"""Returns the device object bound to the wrapper

Args:
None

Returns:
Obj device object or None

Raises:
None

Examples:
None

"""

if hasattr(self, "device"):
return self.device
return None

def getDeviceVersion(self):

pass

@validateParam(versionInfo=str)
def storeDeviceVersionInfo(self, versionInfo):
"""Save device version information

Args:
versionInfo (str): version name string

Returns:
None

Raises:
None

Examples:
None

"""

self.versionInfo = versionInfo
pass

def retrieveDeviceVersionInfo(self):
"""Get device version information

Args:
None

Returns:
versionInfo (str): device version information

Raises:
None

Examples:
wrapper.retrieveDeviceVersionInfo()

"""
return self.versionInfo

@validateParam(release=str, qualifier=str)
def isRelease(self, release, qualifier="=="):
"""Detect the relationship between the provided version number and the device version number

Args:
Release (str): the version number provided
Qualifier (str): the symbol of the comparison operation, default qualifier="=="

Returns:
Boolean - 1 for true, 0 for false

Raises:
UnimplementedException: method to implement exception

Examples:
None

"""
# raise UnimplementedException
pass

def __getPropertyHash(self):
"""Get the property information of all wrappers

Args:
None

Returns:
propertyHash (dict): property information for all wrappers

Raises:
None

Examples:
properties = self.__getPropertyHash()

"""
propertyHash = {}
if hasattr(self, "getPropertyBasedOnVersion"):
propertyHash = self.getPropertyBasedOnVersion()
elif hasattr(self, 'PROPERTY_HASH'):
propertyHash = self.PROPERTY_HASH

return propertyHash

def getLimitInfo(self):
"""Return wrapper limit information

Args:
None

Returns:
limitHash (dict): restriction information defined in properties

Raises:
None

Examples:
limitInfo = self.getLimitInfo()

"""
limitHash = {}
if hasattr(self, "LIMITS_HASH"):
limitHash = self.LIMITS_HASH

return limitHash

# @validateParam(obj=str)
def getPropertyInfo(self, obj):
"""Get the property information of the corresponding class

Args:
Obj (str): the full path of the concrete wrapper class

Returns:
propHash (dict): attribute information of the corresponding class

Raises:

Examples:
propHash = self.getPropertyInfo()

"""
propHash = self.__getPropertyHash()
if obj in propHash:
return propHash[obj]
else:
return propHash

def createPropertyInfoHash(self, obj, properties=list()):
"""Get the get and set methods corresponding to the specified property of obj

Args:
Obj (obj/str): a full path string of a class instance or class
Properties (list): list of properties

Returns:
fullPropertyInfo (dict): specifies the dictionary of the get and set methods corresponding to the attribute
fullPropertyInfo = {"propertyname1": {"getmethod": "methodname", "setmethod": "methodname"},
"propertyname2": {"getmethod": "methodname", "setmethod": "methodname"},
"propertyname3": {"getmethod": "methodname", "setmethod": "methodname"}
}

Raises:
None

Examples:
fullPropertyInfo = self.createPropertyInfoHash(obj, ["p1", "p2", "p3"])

"""
if not isinstance(obj, str):
obj = obj.__module__ + '.' + obj.__name__

baseProps = self.getPropertyInfo(obj)
fullPropertyInfo = {}
if not baseProps:
return fullPropertyInfo
if properties:
neededProps = properties
else:
if PROPERTY in baseProps and baseProps[PROPERTY]:
neededProps = baseProps[PROPERTY].keys()
else:
neededProps = []
for prop in neededProps:
if PROPERTY in baseProps and baseProps[PROPERTY] and prop in baseProps[PROPERTY]:
if prop not in fullPropertyInfo:
fullPropertyInfo[prop] = {}
if GETMETHOD in baseProps[PROPERTY][prop] and baseProps[PROPERTY][prop][GETMETHOD]:
fullPropertyInfo[prop][GETMETHOD] = baseProps[PROPERTY][prop][GETMETHOD]
elif GETMETHOD in baseProps[GLOBAL] and baseProps[GLOBAL][GETMETHOD]:
fullPropertyInfo[prop][GETMETHOD] = baseProps[GLOBAL][GETMETHOD]

if SETMETHOD in baseProps[PROPERTY][prop] and baseProps[PROPERTY][prop][SETMETHOD]:
fullPropertyInfo[prop][SETMETHOD] = baseProps[PROPERTY][prop][SETMETHOD]
elif SETMETHOD in baseProps[GLOBAL] and baseProps[GLOBAL][SETMETHOD]:
fullPropertyInfo[prop][SETMETHOD] = baseProps[GLOBAL][SETMETHOD]

return fullPropertyInfo

def getCommonPropertyInfo(self, getMethod, properties=list()):
"""Returns the class whose specified property has a common get method

Args:
getMethod (str): get method
Properties (list): the specified property

Returns:
Classes (list): list of classes with common get methods

Raises:
None

Examples:
classes = self.getCommonPropertyInfo(getMethod, ["property1", "property2"])

"""
classes = []
baseProps = self.getPropertyInfo(None)
if not baseProps:
return classes

for singleClass in baseProps.keys():
if not properties:
twProps = self.createPropertyInfoHash(singleClass)
properties = twProps.keys()
propInfo = self.createPropertyInfoHash(singleClass, properties)
for prop in propInfo.values():
if "getmethod" in prop and prop["getmethod"] == getMethod:
classes.append(singleClass)
break
return classes

def convertBooleanToYesNo(self, val):
"""Convert true and false values

Args:
Val: can be any value

Returns:
Val returns true for True, and val returns false for False.

Raises:
None

Examples:
result = self.convertBooleanToYesNo(val)

"""
if val:
return "yes"
else:
return "no"

def convertBooleanToOnOff(self, val):
"""Convert true and false values

Args:
Val: can be any value

Returns:
Val returns true for true, and val returns on for off

Raises:
None

Examples:
result = self.convertBooleanToOnOff(val)

"""
if val:
return "on"
else:
return "off"

def convertStrToInt(self, rawVal):
"""Convert Raw data String, etc. to Int type

Args:
rawVal: string

Returns:
int

Raises:
None

Examples:
result = self.convertStrToInt(val)

"""
if re.search("[^0-9]+", rawVal) is None:
return int(rawVal)
return rawVal

def converRawToBoolean(self, rawVal):
"""Convert Raw data yes/no/1/0, etc. to Boolean type

Args:
val: yes/no/1/0

Returns:
val Boolean Value True/False

Raises:
None

Examples:
result = self.convertBooleanToYesNo(val)

"""
if re.search('yes|enable|enabled|on|y|true|1', rawVal, re.IGNORECASE):
return True
else:
return False
================================================================================================
#!/usr/bin/python
# -*- coding: UTF-8 -*-

"""
功 能: 根据模板将用户输入的数据转换为下发的命令

版权信息: 华为技术有限公司，版权所有(C) 2014-2015

修改记录: 2016/4/28 严旭光 y00292329 created

"""
import re
import importlib
from UniAutos.Wrapper.Template import Convert


class Generator(object):
def generator(self, cmdTemplate, params, interactRule, option):
"""将命令行模板和参数封装为具体的命令

Args:
cmdTemplate (dict): 命令行模板
params (dict): 命令参数
interactRule (dict): 交互输入规则
opts (dict): 控制参数

Returns:


Raises:


Examples:


Changes:
2016-06-06 y00292329 Created

"""

cmdStr = self.formatCmd(cmdTemplate, params, option)
interact_rule = cmdTemplate.get("interact_rule", {})
for k, v in interact_rule.items():
interact_rule[k] = params.get(v, "")
interact_rule.update(interactRule)
sessionType = option.get("sessiontype", cmdTemplate['view'][0])
return {"command": cmdStr.split(" "),
"sessionType": sessionType,
"timeout": option.get("time_out", 120),
"send_cmd_confirm": option.get('send_cmd_confirm', False),
"recv_return": option.get('recv_return', True),
"nowait": option.get('nowait', True),
"matched_sessin_type": option.get('matched_sessin_type', True),
"confirm": option.get('confirm', True),
"isauto": params.get('isauto', False),
"interact_rule": cmdTemplate["interact_rule"],
"username": option.get("username",None),
"password": option.get("password",None),
"view_params": option.get("view_params", {})}

def formatCmd(self, cmdTemplate, params, opts):
"""格式化命令行

Args:
cmdTemplate (dict): 命令行模板
params (dict): 命令参数
opts (dict): 控制参数

Returns:


Raises:


Examples:


Changes:
2016-06-06 y00292329 Created

"""

cmdFormat = cmdTemplate['format']
paramInfo = re.compile(r"(\S+)=\s*[?]\s*")
sybInof = re.compile("\|\s?|\[\s?|\]\s?|\}\s?|\{\s?|\*\s?")
def func(m):
par = params.get(m.group(1), None)
if par is None or par == [] or par == {}:
return ""
conver = cmdTemplate['params'].get(m.group(1), None)
if conver:
conver = getattr(Convert, conver)
if callable(func):
par = conver(par)
if isinstance(par, list):
par = ",".join(str(x) for x in par)
elif isinstance(par, bool):
par = "yes" if par else "no"
if not isinstance(par, str):
par = str(par)
return m.group(1) + "=" + par+ " "
cmdList = []
for cmd in cmdFormat:
cmd = sybInof.sub("", cmd)
s = paramInfo.sub(func, cmd)
cmdList.append(s.strip())
return sorted(cmdList,key=lambda x: len(x))[-1]
========================================================================================
#!/usr/bin/python
# -*- coding: UTF-8 -*-

"""
功 能: 一些转换函数

版权信息: 华为技术有限公司，版权所有(C) 2014-2015

修改记录: 2016/5/16 严旭光 y00292329 created

"""
import re

def convertBooleanToYesNo(val):
"""将真假值进行转换

Args:
val: 可以是任何值

Returns:
val为True返回yes，val为False返回no

Raises:
None

Examples:
result = self.convertBooleanToYesNo(val)

"""
if val:
return "yes"
else:
return "no"

def convertBooleanToOnOff(val):
"""将真假值进行转换

Args:
val: 可以是任何值

Returns:
val为True返回yes，val为on返回off

Raises:
None

Examples:
result = self.convertBooleanToOnOff(val)

"""
if val:
return "on"
else:
return "off"

def convertStrToInt(rawVal):
"""将Raw data String等转换成Int类型

Args:
rawVal: string

Returns:
int

Raises:
None

Examples:
result = self.convertStrToInt(val)

"""
if not rawVal:
return rawVal
if re.search("[^0-9]+", rawVal) is None:
return int(rawVal)
return rawVal

def converRawToBoolean(rawVal):
"""将Raw data yes/no/1/0等转换成Boolean类型

Args:
val: yes/no/1/0

Returns:
val Boolean Value True/False

Raises:
None

Examples:
result = self.convertBooleanToYesNo(val)

"""
if re.search('yes|enable|enabled|on|y|true|1', rawVal, re.IGNORECASE):
return True
else:
return False

def convertListToStr(value):
return ",".join(value)
====================================================================================
#!/usr/bin/python
# -*- coding: UTF-8 -*-

"""
功 能:

版权信息: 华为技术有限公司，版权所有(C) 2014-2015

修改记录: 2016/5/5 严旭光 y00292329 created

"""

show_resource_group_general= {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"dstCol": "id", "srcCol": "Resource Group ID", "alter": "convertStrToInt"},
{"dstCol": "name", "srcCol": "Resource Group Name"}
],
"parser": "",
"validate": ""
}

show_disk_domain_general = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"srcCol": "ID", "alter": "convertStrToInt"},
{"srcCol": "Tier0_Disk_Number", "alter": "convertStrToInt"},
{"srcCol": "Tier1_Disk_Number", "alter": "convertStrToInt"},
{"srcCol": "Tier2_Disk_Number", "alter": "convertStrToInt"}
],
"parser": "",
"validate": ""
}

show_disk_domain_available_capacity = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"srcCol": "ID", "alter": "convertStrToInt"},
],
"parser": "",
"validate": ""
}

show_disk_domain_lun = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"srcCol": "LUN ID", "alter": "convertStrToInt"},
],
"parser": "",
"validate": ""
}

show_disk_domain_securevideo = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"srcCol": "ID", "alter": "convertStrToInt"},
],
"parser": "",
"validate": ""
}

show_disk_in_domain = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"srcCol": "Disk Domain ID", "alter": "convertStrToInt"},
],
"parser": "",
"validate": ""
}

show_storage_pool_general = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"srcCol": "ID", "alter": "convertStrToInt"},
{"srcCol": "Disk Domain ID", "alter": "convertStrToInt"},
],
"parser": "",
"validate": ""
}

show_lun_general = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"srcCol": "ID", "alter": "convertStrToInt"},
{"srcCol": "Pool ID", "alter": "convertStrToInt"},
{"srcCol": "Is Add To Lun Group", "alter": "converRawToBoolean"},
{"srcCol": "DIF Switch", "alter": "converRawToBoolean"},
{"srcCol": "Exposed To Initiator", "alter": "converRawToBoolean"}
],
"parser": "",
"validate": ""
}

show_lun_dedup_compress = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"srcCol": "ID", "alter": "convertStrToInt"},
{"srcCol": "Pool ID", "alter": "convertStrToInt"},
],
"parser": "",
"validate": ""
}

show_logical_port_general = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"srcCol": "Logical Port Name","dstCol": "name", "primary": "true"},
{"srcCol": "Activation Status", "alter": "converRawToBoolean"},
{"srcCol": "Is Private", "alter": "converRawToBoolean"},
{"srcCol": "Failover Enabled", "alter": "converRawToBoolean"},
],
"parser": "",
"validate": ""
}

show_lun_copy_general = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"srcCol": "ID", "alter": "convertStrToInt"},
],
"parser": "",
"validate": ""
}

show_lun_copy_member = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"srcCol": "Lun ID", "alter": "convertStrToInt", "primary": "true"},
],
"parser": "",
"validate": ""
}

show_lun_group_lun = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"srcCol": "Pool ID", "alter": "convertStrToInt"},
{"srcCol": "ID", "alter": "convertStrToInt"},
],
"parser": "",
"validate": ""
}

show_lun_group_snapshot = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"srcCol": "Snapshot ID", "alter": "convertStrToInt"},
],
"parser": "",
"validate": ""
}

show_lun_group_general = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"srcCol": "ID", "alter": "convertStrToInt"},
],
"parser": "",
"validate": ""
}

show_lun_group_mapping_view = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"srcCol": "ID", "alter": "convertStrToInt"},
],
"parser": "",
"validate": ""
}

show_lun_migration_general = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"srcCol": "Source Lun ID", "alter": "convertStrToInt"},
{"srcCol": "Target Lun ID", "alter": "convertStrToInt"}
],
"parser": "",
"validate": ""
}

show_mapping_view_general = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"srcCol": "Mapping View ID", "dstCol": "id", "alter": "convertStrToInt", "primary": "true"},
{"srcCol": "Mapping View Name", "dstCol": "name"}
],
"parser": "",
"validate": ""
}

show_mirror_copy_general = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"srcCol": "Mirror Lun ID", "alter": "convertStrToInt"},
{"srcCol": "ID", "alter": "convertStrToInt"},
{"srcCol": "Pool ID", "alter": "convertStrToInt"}
],
"parser": "",
"validate": ""
}

show_mirror_lun_general = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"srcCol": "ID", "alter": "convertStrToInt"},
{"srcCol": "Mirror Lun ID", "alter": "convertStrToInt"}
],
"parser": "",
"validate": ""
}

show_virtual_machine_general = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"srcCol": "ID", "alter": "convertStrToInt"},
{"srcCol": "Cpu Counts", "alter": "convertStrToInt"},
{"srcCol": "Owner Container ID", "alter": "convertStrToInt"},
{"srcCol": "Work Container ID", "alter": "convertStrToInt"}
],
"parser": "",
"validate": ""
}

show_vhba_general = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"srcCol": "Vhba Wwn", "dstCol": "wwn"},
{"srcCol": "Work Container ID", "alter": "convertStrToInt"},
{"srcCol": "Owner Container ID", "alter": "convertStrToInt"}
],
"parser": "",
"validate": ""
}

show_vhost_initiator_general = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"srcCol": "Host ID", "alter": "convertStrToInt"},
{"srcCol": "Wwn", "primary": "true"}
],
"parser": "",
"validate": ""
}

show_virtual_machine_port = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"srcCol": "ID", "alter": "convertStrToInt"},
{"srcCol": "Vm ID", "alter": "convertStrToInt"}
],
"parser": "",
"validate": ""
}

show_vm_file_transference_status = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"srcCol": "Source File System_id", "alter": "convertStrToInt", "primary": "true"},
{"srcCol": "Destination File System_id", "alter": "convertStrToInt"}
],
"parser": "",
"validate": ""
}

show_virtual_machine_block = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"srcCol": "ID", "alter": "convertStrToInt"},
{"srcCol": "Owner Container ID", "alter": "convertStrToInt"}
],
"parser": "",
"validate": ""
}

show_virtual_machine_failback_switch = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"srcCol": "Status", "primary": "true"},
],
"parser": "",
"validate": ""
}

#tangpeng
show_snmp_usm = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"srcCol": "is_default", "alter": "converRawToBoolean"},
],
"parser": "",
"validate": ""
}

show_snmp_safe_strategy = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"srcCol":'password_min_length', "alter": "convertStrToInt"},
{"srcCol":'password_max_length' , "alter": "convertStrToInt"},
{"srcCol":'different_community', "alter": "converRawToBoolean"},
{"srcCol":'different_usm_password', "alter": "converRawToBoolean"},
{"srcCol":'different_usm_name', "alter": "converRawToBoolean"},
{"srcCol":'retry_times', "alter": "convertStrToInt"},
],
"parser": "",
"validate": ""
}

show_snmp_port = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"srcCol":'snmp_listening_port', "alter": "convertStrToInt"},
],
"parser": "",
"validate": ""
}

show_storage_engine = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"srcCol":'id', "alter": "convertStrToInt"},
],
"parser": "",
"validate": ""
}

show_lun_takeover_general = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"srcCol":'id', "alter": "convertStrToInt"},
],
"parser": "",
"validate": ""
}

show_notification_trap = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"srcCol":'server_id', "alter": "convertStrToInt"},
],
"parser": "",
"validate": ""
}

show_performance_statistic_enabled = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"srcCol":'statistic_enabled', "alter": "converRawToBoolean"},
],
"parser": "",
"validate": ""
}

show_quorum_server_general = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"dstCol": "id", "srcCol":'server_id', "alter": 'convertStrToInt'},
{"dstCol": "name", "srcCol":'server_name', "alter": 'convertStrToInt'},
{"dstCol": "active_port", "srcCol":'port',"alter": 'convertStrToInt'},
{"srcCol": 'active_port', "alter": 'convertStrToInt'},
{"dstCol": "active_ip", "srcCol":'address'},
],
"parser": "",
"validate": ""
}

show_quorum_server_link_general = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"dstCol": "id", "srcCol":'server_id', "alter": 'convertStrToInt'},
],
"parser": "",
"validate": ""
}

show_snapshot_general = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"srcCol":'source_lun_id', "alter": 'convertStrToInt'},
{"srcCol":'id', "alter": 'convertStrToInt'},
],
"parser": "",
"validate": ""
}

show_snapshot_lun_group = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"srcCol":'lun_group_id', "alter": 'convertStrToInt'},
],
"parser": "",
"validate": ""
}

show_smartqos_policy_file_system = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"srcCol":'file_system_id', "alter": 'convertStrToInt'},
],
"parser": "",
"validate": ""
}

show_smartqos_policy_lun = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"srcCol":'id', "alter": 'convertStrToInt'},
],
"parser": "",
"validate": ""
}

show_smartqos_policy_general = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"srcCol":'id', "alter": 'convertStrToInt'},
{"srcCol":'enabled', "alter": 'converRawToBoolean'},
],
"parser": "",
"validate": ""
}

show_homedir_general = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"srcCol":'file_system_id', "alter": 'convertStrToInt'},
{"srcCol":'is_open', "alter": 'converRawToBoolean'},
],
"parser": "",
"validate": ""
}


show_storage_pool_tier = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"srcCol":'name', "alter": 'convertStrToInt'},
{"srcCol":'pool_id', "alter": 'convertStrToInt'},
],
"parser": "",
"validate": ""
}

show_quota_tree_general = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"srcCol":'file_system_id', "alter": 'convertStrToInt'},
],
"parser": "",
"validate": ""
}

show_smart_cache_partition_file_system = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"srcCol":'file_system_id', "alter": 'convertStrToInt'},
{"srcCol":'pool_id', "alter": 'convertStrToInt'},
],
"parser": "",
"validate": ""
}

show_smart_cache_partition_lun = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"srcCol":'lun_id', "alter": 'convertStrToInt'},
{"srcCol":'pool_id', "alter": 'convertStrToInt'},
],
"parser": "",
"validate": ""
}

show_smart_cache_partition_general = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"srcCol":'engine_id', "alter": 'convertStrToInt'},
{"srcCol":'id', "alter": 'convertStrToInt'},
{"srcCol":'is_default', "alter": 'convertStrToInt'},
],
"parser": "",
"validate": ""
}

show_smart_cache_pool_disk = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"srcCol":'id', "alter": 'convertStrToInt'},
],
"parser": "",
"validate": ""
}

show_smart_cache_pool_general = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"srcCol":'engine_id', "alter": 'convertStrToInt'},
{"dstCol":'id', "srcCol":'smart_cache_pool_id', "alter": 'convertStrToInt'},
],
"parser": "",
"validate": ""
}

show_resource_user_general = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"dstCol":'name', "srcCol":'user_name'},
{"dstCol":'id', "srcCol":'user_id', "alter": 'convertStrToInt'},
],
"parser": "",
"validate": ""
}

show_remote_replication_available_file_system = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"srcCol":'device_id', "alter": 'convertStrToInt'},
{"srcCol":'file_system_id', "alter": 'convertStrToInt'},
],
"parser": "",
"validate": ""
}

show_remote_replication_general = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"srcCol":'remote_device_id', "alter": 'convertStrToInt'},
{"srcCol":'local_lun_id', "alter": 'convertStrToInt'},
{"srcCol":'remote_lun_id', "alter": 'convertStrToInt'},
{"srcCol":'is_primary', "alter": 'converRawToBoolean'},
{"srcCol":'is_restore', "alter": 'converRawToBoolean'},
{"srcCol":'is_in_consistency_group', "alter": 'converRawToBoolean'},
{"srcCol":'is_data_sync', "alter": 'converRawToBoolean'},
{"srcCol":'compress_enable', "alter": 'converRawToBoolean'},
{"srcCol":'compress_valid', "alter": 'converRawToBoolean'},

],
"parser": "",
"validate": ""
}

show_remote_replication_unified = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"srcCol":'remote_resource_id', "alter": 'convertStrToInt'},
{"srcCol":'local_lun_id', "alter": 'convertStrToInt'},
{"srcCol":'remote_device_id', "alter": 'convertStrToInt'},
{"srcCol":'is_primary', "alter": 'converRawToBoolean'},
{"srcCol":'is_restore', "alter": 'converRawToBoolean'},
{"srcCol":'compress_enable', "alter": 'converRawToBoolean'},
{"srcCol":'compress_valid', "alter": 'converRawToBoolean'},

],
"parser": "",
"validate": ""
}

show_share_permission_nfs = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"dstCol":'id', "srcCol":'share_permission_id', "alter": 'convertStrToInt', "primary":"true"},
{"srcCol":'share_id', "alter": 'convertStrToInt'},
{"srcCol":'sync_enabled', "alter": 'converRawToBoolean'},
{"srcCol":'all_squash_enabled', "alter": 'converRawToBoolean'},
{"srcCol":'root_squash_enabled', "alter": 'converRawToBoolean'},
],
"parser": "",
"validate": ""
}

show_share_permission_cifs = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"dstCol":'id', "srcCol":'share_permission_id', "alter": 'convertStrToInt'},
{"srcCol":'share_id', "alter": 'convertStrToInt'},

],
"parser": "",
"validate": ""
}

show_share_cifs = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"dstCol":'filesystem_id', "srcCol":'file_system_id', "alter": 'convertStrToInt'},
{"dstCol":'id', "srcCol":'share_id', "alter": 'convertStrToInt', "primary":"true"},
{"srcCol":'continue_available_enabled', "alter": 'converRawToBoolean'},
{"srcCol":'notify_enabled', "alter": 'converRawToBoolean'},
{"srcCol":'oplock_enabled', "alter": 'converRawToBoolean'},
],
"parser": "",
"validate": ""
}

show_share_nfs = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"dstCol":'id', "srcCol":'share_id', "alter": 'convertStrToInt', "primary":"true"},
{"dstCol":'filesystem_id', "srcCol":'file_system_id', "alter": 'convertStrToInt'},
],
"parser": "",
"validate": ""
}


show_remote_device_link= {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"srcCol":'id', "alter": 'convertStrToInt'},
],
"parser": "",
"validate": ""
}


show_remote_device_general = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"srcCol":'id', "alter": 'convertStrToInt'},
{"srcCol":'fc_link_number', "alter": 'convertStrToInt'},
{"srcCol":'iscsi_link_number', "alter": 'convertStrToInt'},
],
"parser": "",
"validate": ""
}

show_remote_device_white_list = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"srcCol":'record_id', "alter": 'convertStrToInt'},
{"srcCol":'asl_id', "alter": 'convertStrToInt'},
{"srcCol":'is_user_added', "alter": 'converRawToBoolean'},
],
"parser": "",
"validate": ""
}

show_port_group_general = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"srcCol":'id', "alter": 'convertStrToInt'},
],
"parser": "",
"validate": ""
}

show_vlan_general = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"srcCol":'id', "alter": 'convertStrToInt'},
{"srcCol":'mtu', "alter": 'convertStrToInt'},
],
"parser": "",
"validate": ""
}

show_bond_port = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"srcCol":'id', "alter": 'convertStrToInt'},
{"srcCol":'mtu', "alter": 'convertStrToInt'},
],
"parser": "",
"validate": ""
}

show_controller_general= {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"srcCol": "controller", "dstCol": 'id', "primary":"true"},
],
"parser": "",
"validate": ""
}

show_system_media_scan = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"srcCol":'period(days)', "alter": 'convertStrToInt'},
{"srcCol":'single_disk_max_bandwidth(mbps)', "alter": 'convertStrToInt'},
{"srcCol":'disk_usage_threshold(%)', "alter": 'convertStrToInt'},
],
"parser": "",
"validate": ""
}

show_upgrade_package = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
],
"parser": "systemShowPackageParser",
"validate": ""
}

#chenbeiyun
show_alarm = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"srcCol":"sequence", "primary":"true"}
],
"parser": "",
"validate": ""
}
show_event = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"srcCol":"sequence", "primary":"true"}
],
"parser": "",
"validate": ""
}
show_bbu_general = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"srcCol":"ID", "primary":"true"}
],
"parser": "",
"validate": ""
}
show_bbu_life = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"srcCol":"id", "primary":"true"}
],
"parser": "",
"validate": ""
}
show_cache_partition_general = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"dstCol":"id", "alter": "convertStrToInt", "primary":"true"},
{"dstCol":"storage_engine_id", "alter": "convertStrToInt"},
{"dstCol":"expect_read_size", "alter": "convertStrToInt"},
{"dstCol":"expect_write_size", "alter": "convertStrToInt"},
],
"parser": "",
"validate": ""
}
show_cache_partition_lun = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"dstCol":"id", "alter": "convertStrToInt", "primary":"true"},
],
"parser": "",
"validate": ""
}
show_cache_partition_file_system = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"dstCol":"id", "alter": "convertStrToInt", "primary":"true"},
],
"parser": "",
"validate": ""
}
show_clone_general = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"dstCol":"id", "srcCol": "clone_id", "alter": "convertStrToInt", "primary":"true"},
{"dstCol":"name", "srcCol": "clone_name", "alter": "convertStrToInt"},
{"dstCol":"primary_lun_id", "alter": "convertStrToInt"},
],
"parser": "",
"validate": ""
}
show_clone_secondary_lun = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"dstCol":"id", "alter": "convertStrToInt", "primary":"true"},
{"dstCol":"pair_id", "alter": "convertStrToInt"},
{"dstCol":"clone_id", "alter": "convertStrToInt"},
],
"parser": "",
"validate": ""
}
show_consistency_group_general = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"dstCol":"id", "primary":"true"},
{"dstCol":"timing_length", "alter": "convertStrToInt"},
],
"parser": "",
"validate": ""
}
show_consistency_group_member = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"dstCol":"id", "primary":"true"},
{"dstCol":"is_primary", "alter": "converRawToBoolean"},
],
"parser": "",
"validate": ""
}
show_hyper_metro_consistency_group_general = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"dstCol":"id", "primary":"true"},
{"dstCol":"timing_length", "alter": "convertStrToInt"},
],
"parser": "",
"validate": ""
}
show_hyper_metro_consistency_group_pair = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"dstCol":"id", "primary":"true"},
{"dstCol":"timing_length", "alter": "convertStrToInt"},
],
"parser": "",
"validate": ""
}
show_disk_general = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"dstCol":"id", "primary":"true"},
],
"parser": "",
"validate": ""
}
show_disk_bad_sector_record = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"dstCol":"bad_sector_count", "alter": "convertStrToInt"},
],
"parser": "",
"validate": ""
}
show_enclosure = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"dstCol":"id", "srcCol": "enclosure_id", "alter": "convertStrToInt", "primary":"true"},
],
"parser": "",
"validate": ""
}
show_expansion_module = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"dstCol":"id", "primary":"true"},
],
"parser": "",
"validate": ""
}
show_file_system_general = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"dstCol":"id", "alter": "convertStrToInt", "primary":"true"},
{"dstCol":"pool_id", "alter": "convertStrToInt",},
{"dstCol":"checksum_enabled", "alter": "converRawToBoolean",},
{"dstCol":"atime_enabled", "alter": "converRawToBoolean",},
{"dstCol":"show_snapshot_directory_enabled", "alter": "converRawToBoolean",},
{"dstCol":"auto_delete_snapshot_enabled", "alter": "converRawToBoolean",},
{"dstCol":"timing_snapshot_enabled", "alter": "converRawToBoolean",},
{"dstCol":"dedup_enabled", "alter": "converRawToBoolean",},
{"dstCol":"byte_by_byte_comparison_enabled", "alter": "converRawToBoolean",},
{"dstCol":"compression_enabled", "alter": "converRawToBoolean",},

],
"parser": "",
"validate": ""
}
show_fs_snapshot_general = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"dstCol":"id", "srcCol":"snapshot_id", "alter": "convertStrToInt"},
{"dstCol":"file_system_id", "alter": "convertStrToInt",},
],
"parser": "",
"validate": ""
}
show_fs_snapshot_schedule = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"dstCol":"id","primary":"true"},
],
"parser": "",
"validate": ""
}
show_host_general = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"dstCol":"id", "alter": "convertStrToInt", "primary":"true"},
],
"parser": "",
"validate": ""
}
show_host_host_group = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"dstCol":"id", "srcCol":"host_group_id", "alter": "convertStrToInt", "primary":"true"},
],
"parser": "",
"validate": ""
}
show_host_group_general = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"dstCol":"id", "alter": "convertStrToInt", "primary":"true"},
],
"parser": "",
"validate": ""
}
show_host_group_mapping_view = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"dstCol":"id", "alter": "convertStrToInt", "primary":"true"},
],
"parser": "",
"validate": ""
}
show_hyper_metro_pair_general = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"dstCol":"id", "primary":"true"},
{"dstCol":"local_id", "alter": "convertStrToInt",},
{"dstCol":"remote_id", "alter": "convertStrToInt",},
],
"parser": "",
"validate": ""
}
delete_hypervault_general = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"dstCol":"id","primary":"true"},
{"dstCol":"local_resource_id", "alter": "convertStrToInt",},
{"dstCol":"remote_device_id", "alter": "convertStrToInt",},
{"dstCol":"remote_resource_id", "alter": "convertStrToInt",},
],
"parser": "",
"validate": ""
}
show_hypervault_policy_general = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"dstCol":"id","primary":"true"},
{"dstCol":"copy_threshold", "alter": "convertStrToInt",},
],
"parser": "",
"validate": ""
}
show_hypervault_job_general = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"dstCol":"id","primary":"true"},
],
"parser": "",
"validate": ""
}
show_hypervault_copy_general = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"dstCol":"id","primary":"true"},
],
"parser": "",
"validate": ""
}
show_ib_initiator_general = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"dstCol":"name","primary":"true"},
{"dstCol":"host_id", "alter": "convertStrToInt",},
],
"parser": "",
"validate": ""
}

show_snmp_status = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"srcCol": "Controller", "dstCol":"id","primary":"true"}
],
"parser": "",
"validate": ""
}

show_cli_history = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [],
"parser": "cliShowHistoryParser",
"validate": ""
}

show_ib_port_count = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [],
"parser": "colonParser",
"validate": ""
}

show_vm_container_general = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"srcCol": "vm_container_id", "alter": "convertStrToInt","primary":"true"}
],
"parser": "",
"validate": ""
}

show_vm_fs_general= {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"srcCol": "id", "alter": "convertStrToInt","primary":"true"},
{"srcCol": "block_id", "alter": "convertStrToInt"},
{"srcCol": "work_vm_container_id", "alter": "convertStrToInt"},
{"srcCol": "owner_vm_container_id", "alter": "convertStrToInt"}
],
"parser": "",
"validate": ""
}

show_vm_service_general= {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"srcCol": "status","primary":"true"},
],
"parser": "",
"validate": ""
}

show_fdsa_check_item= {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"srcCol": "name", "primary":"true"},
],
"parser": "",
"validate": ""
}
create_upgrade_session = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [],
"parser": "beforeHotPatchParser",
"validate": ""
}

show_port_fibre_module = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"srcCol": "portid", "dstCol": 'id', "primary": "true"},
],
"parser": "",
"validate": ""
}

show_diagnose_code = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
{"srcCol": "Sequence", "primary": "true"},
],
"parser": "",
"validate": ""
}

show_route_general = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
],
"parser": "showRouteGeneralParser",
"validate": ""
}


show_port_route = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [
],
"parser": "showPortRouteParser",
"validate": ""
}

upgrade_disk = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [],
"parser": "unParser",
"validate": ""
}

upgrade_system_disk = {
"version": ['OceanStor-V500R007-COMMON'],
"retType": "table",
"params": [],
"parser": "unParser",
"validate": ""
}

show_version_all = {
"version": ['OceanStor-V500R007-COMMON'],
"retType": "table",
"params": [],
"parser": "unParser",
"validate": ""
}

show_security_rule = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"params": [],
"parser": "showSecurityRule",
"validate": ""
}

show__firewall_general = {
"version": ['OceanStor-V300R006-COMMON'],
"retType": "table",
"params": [],
"parser": "showFireWill",
"validate": ""
}

create_user = {
"version": ['OceanStor-V300R003-COMMON'],
"retType": "table",
"parser": "unParser",
"validate": ""
}

change_file_system_dedup_compress = {
"version": ['V500R007C00'],
"retType": "table",
"parser": "unParser",
"validate": ""
}

show_certificate_general = {
"version": ['V500R007C30'],
"retType": "table",
"parser": "showCertificateParser",
"validate": ""
}

create_clone_relation = {
"version": ['DoradoV600R003C00'],
"retType": "table",
"parser": "unParser",
"validate": ""
}

create_clone_consistency_group = {
"version": ['DoradoV600R003C00'],
"retType": "table",
"parser": "unParser",
"validate": ""
}