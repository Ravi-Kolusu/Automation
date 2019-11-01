#!/bin/bash

LOG(){
echo [$(date +"%Y-%m-%d %H:%M:%S.%6N")][$$]$@
}

for i in {1..1000};
do
LOG "[NODE FAULT Iteration:${i}]"

PID=`pidof eds`
if [ -z $PID ]; then
LOG " EDS process not found. Existing !!!"
break
fi
LOG " EDS KILL ..."; kill -9 `pidof eds`;
LOG " Waiting for 600 sec ..."; sleep 600;

PID=`pidof eds`
if [ -z $PID ]; then
LOG " EDS process not found. Existing !!!"
break
fi
LOG " APPCTL RESTART ..."; cd /opt/dsware/eds/eds-f/script; ./appctl.sh stop fsa; LOG " Waiting for 40 sec ..."; sleep 40; ./appctl.sh start fsa; cd /root;
LOG " Waiting for 600 sec ..."; sleep 600;

done;
exit 0r