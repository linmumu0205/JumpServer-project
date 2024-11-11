# -*- coding: utf-8 -*-
#
import argparse
import os
import time
import traceback
from datetime import datetime
import MySQLdb
import pytz
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
# mysql
host = DB_HOST
port = DB_PORT
username = DB_USER
password = DB_PASSWORD
db_name = DB_NAME
charset = 'utf8'
mysql_connect = MySQLdb.connect(host=host, port=port, user=username, password=password, db=db_name, charset=charset)
# es
# hosts = 'http://jumpserver:Jump6077@10.10.101.138:9200'  # 需要修改成真实es的地址
hosts = 'http://10.1.12.103:9200/'
kwargs = {'verify_certs': None}
index = 'jumpserver'  # 需要修改成真实索引
doc_type = '_doc'
es = Elasticsearch(hosts=hosts, max_retries=0, **kwargs)

def make_data(command):
    data = dict(
        user=command["user"], asset=command["asset"],
        system_user=command["system_user"], input=command["input"],
        output=command["output"], risk_level=command["risk_level"],
        session=command["session"], timestamp=command["timestamp"],
        org_id=command["org_id"]
    )
    data["@timestamp"] = datetime.fromtimestamp(command['timestamp'], tz=pytz.UTC)
    return data

def bulk_save(command_set, raise_on_error=True):
    actions = []
    for command in command_set:
        data = dict(
            _index=index,
            _type=doc_type,
            _source=make_data(command),
        )
        actions.append(data)
    return bulk(es, actions, index=index, raise_on_error=raise_on_error)

def get_mysql(start_time=None, end_time=None):
    filter_sql = "SELECT * FROM terminal_command"
    if start_time and end_time:
        start_time_arr = time.strptime(start_time, "%Y-%m-%d")
        start_timeStamp = int(time.mktime(start_time_arr))
        end_time_arr = time.strptime(end_time, "%Y-%m-%d")
        end_timeStamp = int(time.mktime(end_time_arr))
        filter_sql += " WHERE timestamp >= {0} and timestamp <= {1}".format(start_timeStamp, end_timeStamp)
    print('*' * 20)
    print('导出开始')
    print('*' * 20)
    try:
        count = 0
        bulk_size = 5000
        while True:
            st = time.time()
            sql = filter_sql+" limit {0} offset {1}".format(bulk_size, count)
            print("Create Commands SQL: {}".format(sql))
            cursor = mysql_connect.cursor(cursorclass=MySQLdb.cursors.DictCursor)
            cursor.execute(sql)
            commands = cursor.fetchall()
            if not commands:
                break
            bulk_save(commands)
            print("Create Commands: {}-{} using: {:.2f}s".format(
                count, count + len(commands), time.time() - st
            ))
            count += len(commands)
    except Exception as e:
        print('*' * 20)
        print('导出出错')
        print(e)
        print('*' * 20)
        traceback.print_exc(e)
    else:
        print('*' * 20)
        print('导出完成')
        print('*' * 20)
    finally:
        mysql_connect.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description=""
    )
    parser.add_argument('start', type=str, help='开始时间')
    parser.add_argument('end', type=str, help='结束时间')
    args = parser.parse_args()
    start = args.start
    end = args.end
    get_mysql(start, end)
