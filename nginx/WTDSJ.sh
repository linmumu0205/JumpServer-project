#!/bin/sh
export GCLUSTER_BASE=/home/billuser/gbase_client/gcluster # need modify
export GCLUSTER_HOME=$GCLUSTER_BASE/server
export GCLUSTER_SID=gcluster
export LD_LIBRARY_PATH=$GCLUSTER_HOME/lib/gbase/:$LD_LIBRARY_PATH
alias gccli='/home/billuser/gbase_client/gcluster/server/bin/gbase'

userpwd="mng/Jtpq!278@shzwops21"
#userpwd="mng/BKF-1123@shzwbcv1"
#userpwd="ob60/Hbr%34kd@SHWLW21"
#userpwd="UD/Rbzbyb1jzh!@shjfops21"
#userpwd="js/T2h4i6N#@newtdjf"

#循环处理请求
do_export(){
while read line
do
SEQ_ID=`echo $line | awk -F';' '{print $1}'`
BILL_ID=`echo $line | awk -F';' '{print $2}'`
ACC_ID=`echo $line | awk -F';' '{print $3}'`
MONTH=`echo $line | awk -F';' '{print $4}'`
BUSI_TYPE=`echo $line | awk -F';' '{print $5}'`
CHANNEL_ID=`echo $line | awk -F';' '{print $6}'`
SOURCE=`echo $line | awk -F';' '{print $7}'`
STATE=`echo $line | awk -F';' '{print $8}'`
INPUT_DATE=`echo $line | awk -F';' '{print $9}'`
START_DATE=`echo $line | awk -F';' '{print $10}'`
DONE_DATE=`echo $line | awk -F';' '{print $11}'`
FILE_NAME=`echo $line | awk -F';' '{print $12}'`
NOTES=`echo $line | awk -F';' '{print $13}'`
OP_ID=`echo $line | awk -F';' '{print $14}'`
ORG_ID=`echo $line | awk -F';' '{print $15}'`
EXT_1=`echo $line | awk -F';' '{print $16}'`
EXT_2=`echo $line | awk -F';' '{print $17}'`
EXT_3=`echo $line | awk -F';' '{print $18}'`
EXT_4=`echo $line | awk -F';' '{print $19}'`
SO_NBR=`echo $line | awk -F';' '{print $20}'`

#判断gbase是否有改用户的详单
gccli -h10.14.121.25 -ugbase -pBjhmdy3!<<EOF > cnt.txt
use sh_jf;
select count(*) from cdr_cs_${MONTH} where redo_flag >= 0 and dr_type = 92049 and call_type = 1 and user_number = ${BILL_ID};
quit
EOF
xdr_cnt=`grep -v count cnt.txt`

#有 继续处理导出，导出完更新请求表
file_name=`echo $BUSI_TYPE"-"$BILL_ID"-"$OP_ID"-"$MONTH"-"$SEQ_ID".csv"`
if [ $xdr_cnt -gt "0" ];then
gccli -h10.14.121.25 -ugbase -pBjhmdy3!<<EOF
use sh_jf;
set names utf8;
rmt:select opp_number,user_number,reserve3,date_format(start_time,'%Y/%m/%d %H:%i:%s'), toll_rate, duration from cdr_cs_${MONTH} where redo_flag >= 0 and dr_type = 92049 and call_type = 1 and user_number = ${BILL_ID} INTO OUTFILE '/data01/zhujq/${file_name}' FIELDS TERMINATED BY ',';
quit
EOF

# 输入文件
input_file=${file_name}

# 临时文件
temp_file="temp.txt"

# 处理每行数据
while IFS=, read -r col1 col2 col3 col4 col5 col6; do
    # 根据第5列的值进行替换
    if [ "$col5" == "1" ]; then
        new_col5="长途"
    elif [ "$col5" == "0" ]; then
        new_col5="本地"
    else
        new_col5="$col5"
    fi

    # 输出到临时文件
    echo "$col1,$col2,$col3,$col4,$new_col5,$col6" >> "$temp_file"
done < "$input_file"

# 替换原文件
mv "$temp_file" "$input_file"

sed -i '1i主叫号码,被叫号码,目的地号码,通话开始时间,本地/长途,时长' ${file_name}
EXT_3=`stat -c '%s' ${file_name}`

sqlplus  -S ${userpwd} << EOF 
UPDATE AID2.IMS_USAGE_REQUEST SET STATE = 2 WHERE SOURCE = 1 AND SEQ_ID = ${SEQ_ID} AND BILL_ID = '${BILL_ID}' AND MONTH = ${MONTH};
INSERT INTO AID2.IMS_USAGE_REQUEST(SEQ_ID, BILL_ID, ACC_ID, MONTH, BUSI_TYPE, CHANNEL_ID, SOURCE, STATE, INPUT_DATE, START_DATE, DONE_DATE, FILE_NAME, NOTES, OP_ID, ORG_ID, EXT_1, EXT_2, EXT_3, EXT_4, SO_NBR) 
VALUES(aid2.INSTANCE_SYC_BBOSS_JF_SEQ.NEXTVAL, '${BILL_ID}', ${ACC_ID}, ${MONTH}, 'ZNHGHR', ${CHANNEL_ID}, 2, 2, SYSDATE, TO_DATE('${START_DATE}', 'YYYYMMDDHH24MISS'), SYSDATE, '${file_name}.gz', '', ${OP_ID}, ${ORG_ID},null, '', '${EXT_3}', '0','${SO_NBR}');
commit;
quit;
EOF

#无  直接更新请求表
else
sqlplus  -S ${userpwd} << EOF
UPDATE AID2.IMS_USAGE_REQUEST SET source = 2 WHERE state = 0 AND SEQ_ID = ${SEQ_ID} AND BILL_ID = '${BILL_ID}' AND MONTH = ${MONTH};
commit;
quit;
EOF
fi
done < ZNHGHR.txt

mv ${file_name}  /data01/zhujq/ZNHGR_file/in
}

sqlplus  -S ${userpwd} << EOF 
set pagesize 0
set linesize 120
set termout off
set heading off
set head off
set trimspool off
set feedback off
set trimout off
set colsep ';'
spool /data01/zhujq/ZNHGHR.txt
SELECT SEQ_ID||';'|| BILL_ID||';'|| ACC_ID||';'|| MONTH||';'|| BUSI_TYPE||';'|| CHANNEL_ID||';'|| SOURCE||';'|| STATE||';'|| TO_CHAR(INPUT_DATE,'YYYYMMDDHH24MISS')||';'|| TO_CHAR(START_DATE,'YYYYMMDDHH24MISS')||';'|| TO_CHAR(DONE_DATE,'YYYYMMDDHH24MISS')||';'|| FILE_NAME||';'|| NOTES||';'|| OP_ID||';'|| ORG_ID||';'|| EXT_1||';'|| EXT_2||';'|| EXT_3||';'|| EXT_4||';'|| SO_NBR FROM AID2.IMS_USAGE_REQUEST WHERE BUSI_TYPE = 'ZNHGHR' AND SOURCE = 1 AND STATE = 0 ORDER BY CHANNEL_ID,MONTH,SEQ_ID DESC;
spool off
quit;
EOF


#判断文件是否有数据
if [[ -f ZNHGHR.txt && -s ZNHGHR.txt ]];then
 do_export 1
else
 echo "no"
fi

