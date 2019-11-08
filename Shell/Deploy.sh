#!/bin/bash
readonly dfv_user=dfvmanager
readonly dfv_group=dfvgroup
clear_all_comp_suc=true
clear_error_detail="[ERROR]"
readonly components=("kmm-server_" "litetask4dr_" "dlm4dr_" "ccdb4dr_" "cm4dr_" "replication_" "vbs_"
"eds_" "cfg_" "fsm_" "fsm-agent_" "fsa-p_" "fma_" "ibase_" "ismcli_" "nma_" "nms_" "pma_"
"pms_" "omm_c_" "ha_" "oam-gaussdb_" "ek_" "beats_" "dlm_" "ccdb_" "litetask_"
"xnetproxy_" "cm_" "snm_" "zk_" "oam-ftds-agent_" "device-manager_" "oam-console_" "fdsa_"
"sysconfig_" "plogagent_" "plogclient_" "plogmanager_" "plogserver_" "snmpagent_")

log_path=/var/log/installtool.log
log_backup()
{
	log_size=`ls -l $log_path | awk '{ print $5 }'`
	maxsize=$((1024*1024*10))
	if [ $log_size -gt $maxsize ]; then
		mv $log_file $log_file.backup
	fi
}
log()
{
	content=[`date '+%Y-%m-%d %H:%M:%S'`]" "$@
	echo $content
	echo $content >> $log_path
}
clear_components_in_order()
{
	log "Current packages in /root/"
	log `ls /root`
	rm -rf /root/*.tar.gz
	for component in ${components[@]}
	do
		log $component
		component_dir=`ls /root | grep -v tar.gz | grep ${component} | sort -r | head -1`
		component_dir="/root/"$component_dir
		if [ -d $component_dir -a -f "$component_dir/action/appctl.sh" ]
		then
			clear_current_comp_suc=true
			log $component_dir" appctl.sh stop"
			sh $component_dir/action/appctl.sh stop 1>>$log_path 2>&1
			ret=$?
			if [ $ret -ne 0 ]; then
				log "[ERROR] Stop $component failed. Check $log_path and contact who's responsible."
				clear_all_comp_suc=false
				clear_current_comp_suc=false
				clear_error_detail=$clear_error_detail" Stop $component failed;"
				exit $ret
			fi
			log $component_dir" appctl.sh uninstall"
			sh $component_dir/action/appctl.sh uninstall 1>>$log_path 2>&1
			ret=$?
			if [ $ret -ne 0 ]; then
				log "[ERROR] Uninstall $component failed. Check $log_path and contact who's responsible."
				clear_all_comp_suc=false
				clear_current_comp_suc=false
				clear_error_detail=$clear_error_detail" Uninstall $component failed;"
				exit $ret
			fi
			if [ $clear_current_comp_suc == "true" ]; then
				log "rm -rf $component_dir"
				chattr -a $component_dir
				rm -rf $component_dir
				log "rm -rf /root/$component*"
				chattr -a /root/$component*
				rm -rf /root/$component* #upgrade scenes
			fi
		fi
	done
}
check_clear_result()
{
	if [ $clear_all_comp_suc == "false" ]; then
		log $clear_error_detail
		log "[ERROR] Some components clear failed. Check $log_path and contact who's responsible."
		exit 1
	fi
}
kill_process()
{
	echo "Process $1 will be killed"
	pid=`ps -ef | grep $1 | grep -v grep | awk '{print $2}'`
	if [ ! -z $pid ]; then
		log "$1 process remain, need clear: kill -9 $pid"
		kill -9 ${pid}
	fi
}
force_clear_deploymanager()
{
	sh /opt/admin/servicetool/bin/servicetool.sh stop
	kill_process "/opt/admin/gaussdb/app/bin/gaussdb"
	kill_process "/opt/admin/jre/bin/java"
	kill_process "/opt/admin/nginx/sbin/nginx"

	rm -rf /home/OpenJDK*
	rm -rf /opt/admin/version
	rm -rf /tmp/FusionDeployInstall
	rm -rf /opt/admin
	rm -rf /opt/servicetool
	rm -rf /home/FusionStorage_deploymanager*
	rm -rf /home/$dfv_user/FusionStorage_deploymanager*

	log "Start clear user: dbadmin, admin"
	userdel -rf dbadmin
	userdel -rf fdadmin
	userdel -rf admin
	groupdel ops
	rm -rf /home/admin
	rm -rf /home/dbadmin

	userdel -rf $dfv_user
	groupdel $dfv_group
	rm -rf /home/$dfv_user
}
uninstall_deploymanager()
{
	deploy_in_home=`ls /home | grep FusionStorage_deploymanager | grep -v tar.gz`
	log "dir in /home: "$deploy_in_home
	if [ -f /home/$deploy_in_home/action/uninstall.sh ]; then
		log "Start uninstall ServiceTool"
		sh /home/$deploy_in_home/action/uninstall.sh >> $log_path
		log "Uninstall ServiceTool succeed"
	else
		log "No need uninstall ServiceTool in /home. ServiceTool package not exist"
	fi
	#远端的安装文件拷贝到了/home/dfvmanager目录中
	deploy_in_dfvmanager=`ls /home/$dfv_user | grep FusionStorage_deploymanager | grep -v tar.gz`
	log "dir in /home/$dfv_user: "$deploy_in_dfvmanager
	if [ -f /home/$dfv_user/$deploy_in_dfvmanager/action/uninstall.sh ]; then
		log "Start uninstall ServiceTool"
		sh /home/$dfv_user/$deploy_in_dfvmanager/action/uninstall.sh >> $log_path
		log "Uninstall ServiceTool succeed"
	else
		log "No need uninstall ServiceTool in /home/$dfv_user/. ServiceTool package not exist"
	fi
}
clear_clouda()
{
	log "Begin clear clouda"
	if [ -d /root/clouda_1.0.0/action -a -f /root/clouda_1.0.0/action/stop.sh ]
	then
		sh /root/clouda_1.0.0/action/stop.sh
		log "Clear clouda success"
	else
		log "No need clear clouda"
	fi
	rpm -qa | grep clouda
	if [ $? -eq 0 ];then
		log "Info: clouda rpm package already exists, try to remove it. [Line:${LINENO}]"
		rpm -e clouda
		[[ $? -ne 0 ]] && log "Error: failed to remove clouda rpm package. [Line:${LINENO}]" && return 1
	fi
	#删除/opt/clouda目录下除了清理脚本以外的其他内容
	rm -rf `find /opt/clouda/* ! -name 'clear_*.sh'`
	chattr -a /root/clouda_1.0.0
	rm -rf /root/clouda_1.0.0*
}
clear_ha_resource()
{
	log "Clear ha resources begin"
	readonly OAM_U_HA_PATH="/opt/dfv/oam/public/ha/"
	readonly OAM_U_HA_PLUGIN_PATH="/opt/dfv/oam/oam-u/ha/ha/module"

	rm -rf $OAM_U_HA_PATH/conf/serviceTool.xml
	rm -rf $OAM_U_HA_PATH/syncconf/hasync_mod.xml
	rm -rf $OAM_U_HA_PATH/script/serviceTool.sh

	rm -rf $OAM_U_HA_PLUGIN_PATH/harm/plugin/conf/serviceTool.xml
	rm -rf $OAM_U_HA_PLUGIN_PATH/hasync/plugin/conf/hasync_mod.xml
	rm -rf $OAM_U_HA_PLUGIN_PATH/harm/plugin/script/serviceTool.sh
	log "Clear ha resources success"
}
main()
{
	#Should be removed after 2019.03.15
	rm -rf /var/log/servicetool
	log_backup
	clear_clouda
	uninstall_deploymanager
	force_clear_deploymanager
	clear_ha_resource
	clear_components_in_order
	check_clear_result
	log "Clear success"
	log "Please manually clean up the '/opt/clouda' directory to completely uninstall FusionStorage: rm -rf /opt/clouda"
	exit 0
}
main
