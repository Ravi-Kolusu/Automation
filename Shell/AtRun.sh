#!/bin/bash

dir=$1
filename=$2
atlog=./AT_Log.log
at=/home/testTools/AT_Tools
cat $atlog >> ./AT_Log.bak.log
rm -rf $atlog
echo > edit.log
while true;
do
check(){
	${at}/AT_Read -p ${dir} -f ${filename}
	[ -s $atlog ] && echo "There is error in $atlog" && exit 1
	# num='cat ${atlog} |grep "\[" |wc -l'
	# [ ! $num -eq 0 ]&& exit 1
}
#create
${at}/AT_Create -p ${dir} -f ${filename} -c 5 -L 600m -H 2g
[ -s $atlog ] && echo "There is error in $atlog" && exit 1
check
#Truncate to
${at}/AT_Truncate -p ${dir} -f ${filename} -s 100k
[ -s $atlog ] && echo "There is error in $atlog" && exit 1
check
#edit -a
${at}/AT_Edit -p ${dir} -f ${filename} -a 16k
[ -s $atlog ] && echo "There is error in $atlog" && exit 1
check
#Truncate to
${at}/AT_Truncate -p ${dir} -f ${filename} -s 2m
[ -s $atlog ] && echo "There is error in $atlog" && exit 1
check
#edit -a
${at}/AT_Edit -p ${dir} -f ${filename} -e 50 >> edit.log
[ -s $atlog ] && echo "There is error in $atlog" && exit 1
check
done