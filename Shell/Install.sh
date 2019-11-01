#!/bin/bash
#!/usr/bin/expect
readonly LOCAL_PATH="$(cd "$(dirname "$0")"; pwd)"
readonly DSWARE_SOFT="/opt/fusionstorage/repository/deploymanager_pkg/DSwareSoft"
readonly HA_PROPERTIES="/home/HAInfoFromInstallTool.properties"
readonly SERVICE_TOOL_PORT=6098
readonly NETWORK_CONFIG="/opt/network/network_config.ini"
readonly log_file="/var/log/installtool.log"
readonly process_file="/home/process.log"
readonly PRIMARY="primary"
readonly SINGLE="single"
readonly DOUBLE="double"
readonly dfv_group="dfvgroup"
readonly fdadmin_user=fdadmin
readonly ops_group=ops
readonly OAM_U_HA_PATH="/opt/dfv/oam/public/ha/"
readonly OAM_U_HA_RUN_PATH="/opt/dfv/oam/oam-u/ha/ha/module/"
readonly OAM_U_HA_PLUGIN_PATH="${OAM_U_HA_RUN_PATH}/harm/plugin"
readonly OAM_U_HA_STOP_PATH="${OAM_U_HA_RUN_PATH}/hacom/script/"
readonly OAM_U_HA_SYNC_PATH="${OAM_U_HA_RUN_PATH}/hasync/plugin/conf/"
readonly STR_KY_A="_fMZ88MzCLH_QdRvDRwu3w=="
readonly CYPT_PY_NAME="python27"
readonly Process_DeployManager="Deploy Manager"
readonly Process_MicroPackage="Micro Package"
readonly Process_Clouda="Clouda"
readonly Process_Num25="25"
readonly Process_Num38="38"
readonly Process_Num39="39"
readonly Process_Num40="40"
readonly Process_Num77="77"
readonly Process_Num78="78"
readonly Process_Num79="79"
readonly Process_Num80="80"
readonly CURL="curl"


log_backup()
{
	log_size=`ls -l $log_file | awk '{ print $5 }'`
	maxsize=$((1024*1024*10))
	if [ $log_size -gt $maxsize ]; then
		mv $log_file $log_file.backup
	fi
}
init()
{
	if [ ! -f ${log_file} ]; then
		log "$log_file doesn't exist,creat it."
		mkdir -p /var/log/
		touch ${log_file}
	fi
	log_backup

	log "Initializing configuration."
	if [ ! -f ${HA_PROPERTIES} ]; then
		log "$HA_PROPERTIES doesn't exist"
		exit 1
	fi

	old_servicetool=`ls /home | grep FusionStorage_deploymanager | grep -v tar.gz`
	new_servicetool=`ls ${DSWARE_SOFT} | grep FusionStorage_deploymanager | grep \`uname -m\`| awk -F '.tar.gz' '{print $1}'`
	evs_dir=`ls ${DSWARE_SOFT} | grep FusionStorage | grep 8.0.| awk -F '.tar.gz' '{print $1}'`
	if [ -n "${evs_dir}" ];then
		rm -rf $DSWARE_SOFT/$evs_dir
	fi

	source ${HA_PROPERTIES}

	if [ -z ${service_float_ip} ]; then
		log "$HA_PROPERTIES exist but service_float_ip not exist"
	fi

	if [ -z ${manager_float_ip} ]; then
		log "$HA_PROPERTIES exist but manager_float_ip not exist"
	fi

	if [ "X${service_local_port}" != "X${service_remote_port}" ];then
		log "$service_local_port is diff with $service_remote_port"
	fi

	if [ "X${manager_local_port}" != "X${manager_remote_port}" ];then
		log "$manager_local_port is diff with $manager_remote_port"
	fi

	if [ "X${service_local_ip}" == "X${manager_local_ip}" ];then
		log "single plane"
		external_ethname=""
		service_gateway=""
		service_mask=""
	else
		log "double plane"
		external_ethname=${service_local_port}
	fi

	if [ -z "${local_sn}" ];then
		local_sn="-"
	else
		local_sn=${local_sn}
	fi

	if [ -z "${remote_sn}" ];then
		remote_sn="-"
	else
		remote_sn=${remote_sn}
	fi

	service_active_ip=${service_local_ip}
	service_standby_ip=${service_remote_ip}
	manager_active_ip=${manager_local_ip}
	manager_standby_ip=${manager_remote_ip}
	float_ip_for_ha=${manager_float_ip}
	install_ha="true"
	forbid_switch="true"
	if [ $ha_role != "${PRIMARY}" -a ${ha_mode} == "${DOUBLE}" ]; then
		service_active_ip=${service_remote_ip}
		service_standby_ip=${service_local_ip}
		manager_active_ip=${manager_remote_ip}
		manager_standby_ip=${manager_local_ip}
	fi

	if [ ${ha_mode} == "${SINGLE}" ]; then
		manager_standby_ip="--"
		float_ip_for_ha=${manager_active_ip}
		float_ip_for_gauss="127.0.0.1"
		install_ha="true"
		forbid_switch="false"
	fi

	test=`cat ${HA_PROPERTIES} | grep active_ip`
	if [ -z $test ]; then
		echo "active_ip=${manager_active_ip}" >> $HA_PROPERTIES
	fi
	test=`cat ${HA_PROPERTIES} | grep standby_ip`
	if [ -z $test ]; then
		echo "standby_ip=${manager_standby_ip}" >> $HA_PROPERTIES
	fi
	test=`cat ${HA_PROPERTIES} | grep float_ip_for_ha`
	if [ -z $test ]; then
		echo "float_ip_for_ha=${float_ip_for_ha}" >> $HA_PROPERTIES
	fi
	test=`cat ${HA_PROPERTIES} | grep install_ha`
	if [ -z $test ]; then
		echo "install_ha=${install_ha}" >> $HA_PROPERTIES
	fi
	test=`cat ${HA_PROPERTIES} | grep service_ip_list`
	if [ -z $test ]; then
		if [ ${ha_mode} == "${DOUBLE}" ];then
			echo "service_ip_list=${manager_active_ip},${manager_standby_ip}" >> ${HA_PROPERTIES}
		fi
		if [ ${ha_mode} == "${SINGLE}" ];then
			echo "service_ip_list=${manager_local_ip}" >> ${HA_PROPERTIES}
		fi
	fi

	test=`cat ${HA_PROPERTIES} | grep internal_ethname`
	if [ -z $test ]; then
		echo "internal_ethname=${manager_local_port}" >> $HA_PROPERTIES
	fi

	test=`cat ${HA_PROPERTIES} | grep external_ethname`
	if [ -z $test ]; then
		echo "external_ethname=${external_ethname}" >> $HA_PROPERTIES
	fi
	test=`cat ${HA_PROPERTIES} | grep external_service_gateway`
	if [ -z $test ]; then
		echo "external_service_gateway=${service_gateway}" >> $HA_PROPERTIES
	fi
	test=`cat ${HA_PROPERTIES} | grep external_service_mask`
	if [ -z $test ]; then
		echo "external_service_mask=${service_mask}" >> $HA_PROPERTIES
	fi
	test=`cat ${HA_PROPERTIES} | grep external_service_float_ip`
	if [ -z $test ]; then
		echo "external_service_float_ip=${service_float_ip}" >> $HA_PROPERTIES
	fi
	test=`cat ${HA_PROPERTIES} | grep local_cabinet`
	if [ -z $test ]; then
		echo "local_cabinet=1" >> $HA_PROPERTIES
		local_cabinet="1"
	fi
	if [ -z ${local_cabinet} ]; then
		local_cabinet="1"
	fi
	test=`cat ${HA_PROPERTIES} | grep remote_cabinet`
	if [ -z $test ]; then
		echo "remote_cabinet=1" >> $HA_PROPERTIES
		remote_cabinet="1"
	fi
	if [ -z ${remote_cabinet} ]; then
		remote_cabinet="1"
	fi
	test=`cat ${HA_PROPERTIES} | grep forbid_switch`
	if [ -z $test ]; then
		echo "forbid_switch=${forbid_switch}" >> $HA_PROPERTIES
	fi

	initUser

	URL_BASE="https://127.0.0.1":${SERVICE_TOOL_PORT}
#URL_BASE="https://"${manager_local_ip}:${SERVICE_TOOL_PORT}
	log "Init configuration succeed."
}

function initUser()
{
# #解压python包用于解密---使用系统自带的python，暂时取消解压缩
# tar -zxf ${DSWARE_SOFT}/${CYPT_PY_NAME}.tar.gz -C ${DSWARE_SOFT}/
	login_pwd=$(decryptPwd "${login_pwd}")
	if [ -z "${login_user_name}" ];then
		login_user_name="root"
		login_user_pwd="${login_pwd}"
	else
		login_user_name=$(decryptPwd "${login_user_name}")
		login_user_pwd=$(decryptPwd "${login_user_pwd}")
	fi

	if [ ${ha_mode} == "${DOUBLE}" ];then
		remote_login_pwd=$(decryptPwd "${remote_login_pwd}")
		if [ -z "${remote_login_user_name}" ];then
			remote_login_user_name="root"
			remote_login_user_pwd="${remote_login_pwd}"
		else
			remote_login_user_name=$(decryptPwd "${remote_login_user_name}")
			remote_login_user_pwd=$(decryptPwd "${remote_login_user_pwd}")
		fi
	else
		remote_login_pwd="${login_pwd}"
		remote_login_user_name="${login_user_name}"
		remote_login_user_pwd="${login_user_pwd}"
	fi
}

function decryptPwd()
{
	local crypt_str=$1
	if [ -n "${crypt_str}" ];then
		skey=$(python ${DSWARE_SOFT}/cryptApi.py sxor ${STR_KY_A} ${pk_b})
		#使用系统自带python
		decrypted_pwd=$(python ${DSWARE_SOFT}/cryptApi.py decrypt $crypt_str ${skey})
	else
		log "crypt_str is empty"
		exit 1
	fi
	echo "${decrypted_pwd}"
}
log()
{
	content=[`date '+%Y-%m-%d %H:%M:%S'`]" "$@
	echo $content
	echo $content >> ${log_file}
}
progress_log()
{
	content=`date '+%Y-%m-%d %H:%M:%S'`/$@
	echo $content >> ${process_file}
}
write_main_yml()
{
	if [ $ha_mode == "${SINGLE}" ]; then
		echo "TOOL_IP_LIST:"${manager_local_ip} > /home/$new_servicetool/vars/main.yml
		echo "TOOL_FLOAT_IP:"${manager_local_ip} >> /home/$new_servicetool/vars/main.yml
	else
		echo "TOOL_IP_LIST:"${manager_active_ip}","${manager_standby_ip} > /home/$new_servicetool/vars/main.yml
		echo "TOOL_FLOAT_IP:"${manager_float_ip} >> /home/$new_servicetool/vars/main.yml
	fi
	echo "ACTIVE_IP:"${manager_active_ip} >> /home/$new_servicetool/vars/main.yml
}
tar_new_pkg()
{
	log "Start tar ServicetTool package"
	cp /opt/fusionstorage/repository/deploymanager_pkg/DSwareSoft/$new_servicetool.tar.gz /home
	tar -xzf /home/$new_servicetool.tar.gz -C /home
	if [ $? -ne 0 ]; then
		progress_log "0/0/4/Deploy Manager"
		exit 1
	fi
	rm -rf /home/$new_servicetool.tar.gz >>/dev/null 2>&1
	log "Tar new_servicetool succeed return $?"
}
install_serviceTool()
{
	install_sh="/home/$new_servicetool/action/install.sh"
	if [ ! -f /home/$new_servicetool/action/install.sh ]; then
		log "/home/$new_servicetool/action/install.sh doesn't exist"
		progress_log "5/1/4/Deploy Manager"
		exit 1
	fi
	log "Start install ServiceTool"

	sed -i "s/read \"ROOT_PSWD\"/ROOT_PSWD=${remote_login_pwd}/" $install_sh
	sed -i "s/read \"DFV_PSWD\"/DFV_PSWD=${remote_login_user_pwd}/" $install_sh

	#double manager node
	sh /home/$new_servicetool/action/install.sh "" "" "${remote_login_user_name}">> ${log_file}
	ret=$?
	if [ $ret -ne 0 ]; then
		sed -i "s/ROOT_PSWD=${remote_login_pwd}/read \"ROOT_PSWD\"/" $install_sh
		sed -i "s/DFV_PSWD=${remote_login_user_pwd}/read \"DFV_PSWD\"/" $install_sh
		log "Install ServiceTool failed."
		progress_log "37/1/4/Deploy Manager"
		exit $ret
	fi

	default_psw=`head /dev/urandom | tr -dc A-Za-z0-9 | head -c 64`
	sed -i "s/DEFAULT_PWD/${default_psw}/" /opt/fusionstorage/deploymanager/servicetool/conf/pwd.ini
	if [ ${ha_mode} == "${DOUBLE}" ];then
		exec_cmd_remote "sed -i \"s/DEFAULT_PWD/${default_psw}/\" /opt/fusionstorage/deploymanager/servicetool/conf/pwd.ini"
	fi
	sed -i "s/ROOT_PSWD=${remote_login_pwd}/read \"ROOT_PSWD\"/" $install_sh
	sed -i "s/DFV_PSWD=${remote_login_user_pwd}/read \"DFV_PSWD\"/" $install_sh
	log "Install succeed"
}
send_curl_checkCloua_result()
{
	log "curl start: "$@
	result=`$@`
	log "Result: ${result}"
	if [ "${result}" != "success" ]; then
		log "Failed and exit 1"
		progress_log "50/1/4/Clouda"
		exit 1
	fi
}
send_curl_checkMircoPkg_result()
{
	log "Curl start: "$@
	result=`$@`
	log "Result: ${result}"
	if [ "${result}" != "success" ]; then
		log "Failed and exit 1"
		progress_log "57/0/4/Micro Package"
		exit 1
	fi
}
send_curl_checkTmplage_result()
{
	log "Curl start: "$@
	result=`$@`
	log "Result: ${result}"
	if [ "${result}" != "success" ]; then
		log "Failed and exit 1"
		progress_log "59/0/4/Micro Package"
		exit 1
	fi
}
send_curl_checkDeploy_result()
{
	log "Curl start: "$@
	result=`$@`
	log "Result: ${result}"
	if [ "${result}" != "success" ]; then
		log "Failed and exit 1"
		progress_log "60/0/4/Micro Package"
		exit 1
	fi
}
send_curl_wait_success()
{
	log "Start query: "$@
	while true
	do
		result=`$@`
		log "Result: ${result}"
		if [ "${result}" = "failed" ]; then
			log "Failed and exit 1"
			progress_log "53/1/4/Clouda"
			exit 1
		fi
		if [ "${result}" = "success" ]; then
			break
		fi
		sleep 10
		log "sleep 10s"
	done
}
#get remote config
get_remote_network_config()
{
	readonly remote_network_config=/home/network_config.ini
	readonly remote_host_name=/home/hostname
	expect ${DSWARE_SOFT}/scp_expect.exp ${manager_remote_ip} root ${login_pwd} "${remote_network_config}" "${NETWORK_CONFIG}" >> ${log_file} 2>&1
	expect ${DSWARE_SOFT}/scp_expect.exp ${manager_remote_ip} root ${login_pwd} "${remote_host_name}" "/etc/hostname" >> ${log_file} 2>&1
	remote_rack_number=`cat ${remote_network_config} | grep rack_number | awk -F '=' '{print $2}'`
	remote_slot_number=`cat ${remote_network_config} | grep slot_number | awk -F '=' '{print $2}'`
	remote_cabinet=`cat ${remote_network_config} | grep cabinet | awk -F '=' '{print $2}'`
	remote_sn=`cat ${remote_network_config} | grep sn | awk -F '=' '{print $2}'`
	remote_host=`cat ${remote_host_name}`
	rm -rf /home/hostname
	rm -rf /home/network_config.ini
}
curl_add_host_new()
{
	log "curl_add_host start"
	if [ ${ha_mode} == "${SINGLE}" ]; then
		param="[{\"name\": \"FSM01\", \"serialNumber\": \"${local_sn}\", \"subrack\": \"-\", \"slotNumber\": \"-\",
		\"role\": [\"management\"], \"authentication_mode\": \"password\",
		\"managementInternalIp\": \"$manager_local_ip\", \"rootPassword\": \"$login_pwd\", \"cabinet\": \"${local_cabinet}\",
		\"userName\": \"$login_user_name\", \"password\": \"$login_user_pwd\"}]"
	else
		param="[{\"name\": \"FSM01\", \"serialNumber\": \"${local_sn}\", \"subrack\": \"-\", \"slotNumber\": \"-\",
		\"role\": [\"management\"], \"authentication_mode\": \"password\",
		\"managementInternalIp\": \"$manager_local_ip\", \"rootPassword\": \"$login_pwd\", \"cabinet\": \"${local_cabinet}\",
		\"userName\": \"$login_user_name\", \"password\": \"$login_user_pwd\"},
		{\"name\": \"FSM02\", \"serialNumber\": \"${remote_sn}\", \"subrack\": \"-\", \"slotNumber\": \"-\",
		\"role\": [\"management\"], \"authentication_mode\": \"password\",
		\"managementInternalIp\": \"$manager_remote_ip\", \"rootPassword\": \"$remote_login_pwd\", \"cabinet\": \"${remote_cabinet}\",
		\"userName\": \"$remote_login_user_name\", \"password\": \"$remote_login_user_pwd\"}]"
	fi
	cmd="${CURL} -skX POST [ $manager_local_ip ] $URL_BASE/api/v2/curl/host/template"
	result=`${CURL} -skX POST -H 'Content-type: application/json' -d "${param}" $URL_BASE/api/v2/curl/host/template`
	log "Result: ${result}"
	if [ "${result}" != "success" ]; then
		log "Failed and exit 1"
		progress_log "43/1/4/Manager Node"
		exit 1
	fi
}
curl_install_clouda()
{
	log "install_clouda start"
	cmd="${CURL} -skX POST -d '' "$URL_BASE/api/v2/curl/host/installation
	send_curl_checkCloua_result $cmd
}
curl_wait_clouda_success()
{
	log "CloudA install status query: "
	cmd="${CURL} -skX GET "$URL_BASE/api/v2/curl/host/installation
	send_curl_wait_success $cmd
}
curl_upload_mirco_pkg()
{
	log "Upload deploy package start"

	deploy_pkg=`ls $DSWARE_SOFT | grep -i FusionStorage_x86_64 | grep tar.gz`
	if [ -z "${deploy_pkg}" ]; then
		deploy_pkg=`ls $DSWARE_SOFT | grep -i FusionStorage_aarch64 | grep tar.gz`
	fi
	if [ -z "${deploy_pkg}" ]; then
		deploy_pkg=`ls $DSWARE_SOFT | grep -i FusionStorage_noarch | grep tar.gz`
	fi
	if [ -z "${deploy_pkg}" ]; then
		deploy_pkg=`ls $DSWARE_SOFT | grep -i FusionStorage_8 | grep tar.gz`
	fi
	if [ -z "${deploy_pkg}" ]; then
		deploy_pkg=`ls $DSWARE_SOFT | grep -i FusionStorage_For_UVP | grep tar.gz`
	fi
	if [ -z "${deploy_pkg}" ]; then
		echo "Deploy package not exist, FusionStorage_x86_64*.tar.gz or FusionStorage_aarch64*.tar.gz or FusionStorage_noarch*.tar.gz or FusionStorage_8*.tar.gz or FusionStorage_For_UVP*.tar.gz"
		progress_log "56/1/4/Micro Package"
		exit 1
	fi
	log "Start upload package: "$deploy_pkg
	cmd="${CURL} -skX POST -d pkgPath="$DSWARE_SOFT/$deploy_pkg" "$URL_BASE/api/v2/curl/deploy/micro_package
	send_curl_checkMircoPkg_result $cmd
}
curl_upload_template()
{
	log "Upload deploy params to template start"

	cmd="${CURL} -skX POST -d '' "$URL_BASE/api/v2/curl/deploy/template
	send_curl_checkTmplage_result $cmd
}
curl_start_deploy()
{
	log "Start deploy manager components"
	cmd="${CURL} -skX POST -d '' "$URL_BASE/api/v2/curl/deploy/deploy_service
	send_curl_checkDeploy_result $cmd
}
curl_record_deploy_log()
{
	log "Deploy log: "
	cmd="${CURL} -skX GET "$URL_BASE/api/v2/curl/deploy/deploy_log
	result=`$cmd`
	log "${result}"
}
curl_wait_deploy_success()
{
	log "Deploy status query: "
	sleep 10
	log "sleep 10s"
	progress=60
	cmd="${CURL} -skX GET "$URL_BASE/api/v2/curl/deploy/deploy_service
	log "Start query: "$cmd
	while true
	do
		result=`$cmd`
		log "Result: ${result}"
		if [ "${result}" = "failed" ]; then
			log "Failed and exit 1"
			curl_record_deploy_log
			progress_log "65/1/4/Micro Package"
			exit 1
		fi
		if [ "${result}" = "success" ]; then
			break
		fi
		sleep 15
		log "sleep 15s"
		progress=$[progress+1]
		progress_log $progress"/1/2/Micro Package"
	done
	curl_record_deploy_log
}
clear_user()
{
	userdel -rf dmdbadmin
	userdel -rf admin
	groupdel ops
	rm -rf /home/admin
	rm -rf /home/dmdbadmin
}
restart_servicetool()
{
	if [ "$1"x == "status"x -a ${ha_mode}x == "${DOUBLE}"x ]; then
		sh /opt/fusionstorage/deploymanager/servicetool/bin/servicetool.sh start >> ${log_file}
	fi
	sh /opt/fusionstorage/deploymanager/servicetool/bin/servicetool.sh $1 >> ${log_file}
	count=1
	while true; do
		if [ $count -gt 150 ]; then
			log "Servicetool failed to start"
			progress_log "$2/1/4/${Process_DeployManager}"
			exit 1
		fi
		sh /opt/fusionstorage/deploymanager/servicetool/bin/servicetool.sh status
		ret=$?
		result=`${CURL} -skX GET -H 'Content-type: application/json' -m 5 --connect-timeout 5 $URL_BASE/api/v2/curl/deploy/tomcat_status`
		if [ "success"x = "${result}"x -a $ret -eq 0 ]; then
			log "Servicetool started successfully"
			break
		else
			log "Servicetool has not been started successfully : ${count}"
			sleep 2
			count=`expr $count + 1`
		fi
	done
	sleep 30
	#firewall-cmd --reload
}
function exec_cmd_remote()
{
	local cmd="$1"
	expect /home/$new_servicetool/action/ssh_expect_root.exp ${manager_remote_ip} ${remote_login_user_name} ${remote_login_user_pwd} ${remote_login_pwd} "$cmd" >> ${log_file} 2>&1
	if [ $? -ne 0 ]; then
		log "[Line:${LINENO}][Error] Failed to exec $cmd from remote node!"
		exit 1
	fi
	log "[Line:${LINENO}][Info] Success to exec $cmd from remote node!"
	return 0
}
function config_servicetool_monitor()
{
	if [ ${ha_mode} == "${SINGLE}" ]; then
		log "single, no need to config HA."
		return 0
	fi
	log "begin to set config HA."

	local HA_config_path="/home/$new_servicetool/action/"
	local HA_config_path_standby="/opt/fusionstorage/repository/deploymanager_pkg/dfvmanager/$new_servicetool/action/"

	#本机
	#先删除serviceTool.xml文件，防止命令执行失败
	rm -f ${OAM_U_HA_PATH}/conf/serviceTool.xml
	rm -f ${OAM_U_HA_PLUGIN_PATH}/conf/serviceTool.xml
	\cp -a "${HA_config_path}"/serviceTool.xml ${OAM_U_HA_PATH}/conf/
	\cp -a "${HA_config_path}"/serviceTool.xml ${OAM_U_HA_PLUGIN_PATH}/conf/
	\cp -a "${HA_config_path}"/deploymanager_sync.xml ${OAM_U_HA_PATH}/syncconf/
	\cp -a "${HA_config_path}"/deploymanager_sync.xml ${OAM_U_HA_SYNC_PATH}/
	\cp -a "${HA_config_path}"/serviceTool.sh ${OAM_U_HA_PATH}/script/
	\cp -a "${HA_config_path}"/serviceTool.sh ${OAM_U_HA_PLUGIN_PATH}/script/

	chown root:root ${OAM_U_HA_PATH}/syncconf/deploymanager_sync.xml
	chmod 640 ${OAM_U_HA_PATH}/syncconf/deploymanager_sync.xml
	chown root:root ${OAM_U_HA_SYNC_PATH}/deploymanager_sync.xml
	chmod 640 ${OAM_U_HA_SYNC_PATH}/deploymanager_sync.xml

	#远端
	if [ ${ha_mode} == "${DOUBLE}" ];then

		#拷贝文件
		#先删除serviceTool.xml文件，防止命令执行失败
		exec_cmd_remote "rm -f ${OAM_U_HA_PATH}/conf/serviceTool.xml"
		exec_cmd_remote "rm -f ${OAM_U_HA_PLUGIN_PATH}/conf/serviceTool.xml"
		exec_cmd_remote "\cp -a ${HA_config_path_standby}/serviceTool.xml ${OAM_U_HA_PATH}/conf/"
		exec_cmd_remote "\cp -a ${HA_config_path_standby}/serviceTool.xml ${OAM_U_HA_PLUGIN_PATH}/conf/"
		exec_cmd_remote "\cp -a ${HA_config_path_standby}/deploymanager_sync.xml ${OAM_U_HA_PATH}/syncconf/"
		exec_cmd_remote "\cp -a ${HA_config_path_standby}/serviceTool.sh ${OAM_U_HA_PATH}/script/"
		exec_cmd_remote "\cp -a ${HA_config_path_standby}/serviceTool.sh ${OAM_U_HA_PLUGIN_PATH}/script/"
		exec_cmd_remote "\cp -a ${HA_config_path_standby}/deploymanager_sync.xml ${OAM_U_HA_SYNC_PATH}/"

		exec_cmd_remote "chown root:root ${OAM_U_HA_PATH}/syncconf/deploymanager_sync.xml"
		exec_cmd_remote "chmod 640 ${OAM_U_HA_PATH}/syncconf/deploymanager_sync.xml"
		exec_cmd_remote "chown root:root ${OAM_U_HA_SYNC_PATH}/deploymanager_sync.xml"
		exec_cmd_remote "chmod 640 ${OAM_U_HA_SYNC_PATH}/deploymanager_sync.xml"

		#重启对端HA
		exec_cmd_remote "sh ${OAM_U_HA_STOP_PATH}/stop_ha_process.sh"
		if [ $? -ne 0 ]; then
			log "[Line:${LINENO}][Error] Failed to exec stop_ha_process.sh from remote node!"
			progress_log "100/1/4/Micro package"
			exit 1
		fi
	fi

	#重启本端HA
	sh ${OAM_U_HA_STOP_PATH}/stop_ha_process.sh >> ${log_file} 2>&1
	if [ $? -ne 0 ]; then
		log "[Line:${LINENO}][Error] Failed to exec stop_ha_process.sh !"
		progress_log "100/1/4/Micro package"
		exit 1
	fi
}
function bond_floatip_local()
{
	if [ ${ha_mode} == "${SINGLE}" ]; then
		log "single, no need to set floatIP."
		return 0
	fi
	log "begin to set floatIP."

	ethtool ${manager_local_port} | grep "Link detected: yes" >>${log_file} 2>&1
	if [ $? -ne 0 ];then
		ethtool ${manager_local_port} >>${log_file} 2>&1
		log "${manager_local_port%%:*} is not linked!"
		progress_log "3/1/4/Deploy Manager"
		exit 1
	fi
	floatIPInfo=$(ifconfig -a | grep " ${manager_float_ip} ")
	if [ "${floatIPInfo}" != "" ];then
		log "already bind float ip."
		return 0
	fi

	ping -c 3 ${manager_float_ip} >>${log_file} 2>&1
	if [ $? -eq 0 ]; then
		arp >>${log_file} 2>&1
		log "${manager_float_ip} has been used somewhere, please check whether if the floatIP is available!"
		progress_log "3/1/4/Deploy Manager"
		exit 1
	fi

	ifconfig "${manager_local_port}:u-mao" ${manager_float_ip} netmask ${manager_mask} 2>>${log_file}
	if [ $? -eq 0 ]; then
		arping -w 1 -A -I "${manager_local_port}:u-mao" $manager_float_ip
		log "set float IP success."
		return 0
	else
		log "set float IP failed!"
		progress_log "3/1/4/Deploy Manager"
		exit 1
	fi
}
post_install()
{
	chown $fdadmin_user:$ops_group $DSWARE_SOFT -R
	chmod 700 $DSWARE_SOFT -R
}
clear_no_use_files()
{
	if [ -f "/opt/fusionstorage/deploymanager/servicetool/conf/pwd.ini" ];then
		rm -rf /opt/fusionstorage/deploymanager/servicetool/conf/pwd.ini
	fi
	if [ ${ha_mode} == "${DOUBLE}" ];then
		exec_cmd_remote "rm -rf /opt/fusionstorage/deploymanager/servicetool/conf/pwd.ini"
	fi
}
main()
{
	init
	progress_log "0/0/2/Deploy Manager"
	tar_new_pkg
	progress_log "3/0/3/Deploy Manager"
	write_main_yml
	bond_floatip_local
	progress_log "3/1/2/Deploy Manager"
	install_serviceTool
	restart_servicetool status $Process_Num25
	post_install
	progress_log "40/1/3/Deploy Manager"
	progress_log "40/2/2/Manager Node"

	curl_add_host_new
	progress_log "45/2/3/Manager Node"
	progress_log "45/1/2/Clouda"
	curl_install_clouda
	curl_wait_clouda_success
	progress_log "55/1/3/Clouda"
	progress_log "55/0/2/Micro Package"

	curl_upload_mirco_pkg
	curl_upload_template
	progress_log "60/0/3/Micro Package"
	progress_log "60/1/2/Micro Package"
	curl_start_deploy
	curl_wait_deploy_success
	config_servicetool_monitor
	restart_servicetool stop $Process_Num80
	clear_no_use_files
	progress_log "100/1/3/Micro Package"
}
main
close 0