# -*- coding: utf-8 -*-
# __author:linmy
# data:2024/12/9

import argparse
import os
import time
import traceback
from datetime import datetime
import MySQLdb
import pytz
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk

# MySQL 配置
host = os.getenv("DB_HOST", "10.1.12.74")
port = int(os.getenv("DB_PORT", 3306))
username = os.getenv("DB_USER", "root")
password = os.getenv("DB_PASSWORD", "123456")
db_name = os.getenv("DB_NAME", "jumpserver")
charset = 'utf8'

# Elasticsearch 配置
es_host = os.getenv("ES_HOST", "http://10.1.12.120:9200")
es_user = os.getenv("ES_USER", "elastic")
es_password = os.getenv("ES_PASSWORD", "#In2431535")
index = 'test'  # 真实索引

es = Elasticsearch(
    hosts=[es_host],
    basic_auth=(es_user, es_password),  # 使用 basic_auth 替代 http_auth
    verify_certs=False
)


def make_data(command):
    """
    构造 Elasticsearch 文档
    """
    data = {
        "user": command["user"],
        "asset": command["asset"],
        "account": command["account"],
        "input": command["input"],
        "output": command["output"],
        "risk_level": command["risk_level"],
        "session": command["session"],
        "timestamp": command["timestamp"],
        "org_id": command["org_id"],
        "@timestamp": datetime.fromtimestamp(command["timestamp"], tz=pytz.UTC).isoformat(),
    }
    return data


def bulk_save(command_set, raise_on_error=True):
    """
    批量保存到 Elasticsearch
    """
    actions = []
    for command in command_set:
        data = {
            "_index": index,
            "_source": make_data(command),
        }
        actions.append(data)
    return bulk(es, actions, index=index, raise_on_error=raise_on_error)


def get_mysql(start_time=None, end_time=None):
    """
    从 MySQL 获取数据并写入 Elasticsearch
    """
    filter_sql = "SELECT * FROM terminal_command WHERE timestamp >= %s AND timestamp <= %s"
    print(f"开始导出数据，时间范围：{start_time} 至 {end_time} (Unix 时间戳格式)")

    try:
        mysql_connect = MySQLdb.connect(
            host=host, port=port, user=username, password=password, db=db_name, charset=charset
        )
        cursor = mysql_connect.cursor(cursorclass=MySQLdb.cursors.DictCursor)
        count = 0
        bulk_size = 5000

        while True:
            sql = filter_sql + " LIMIT %s OFFSET %s"
            print(f"正在执行 SQL: {sql} 参数: {start_time}, {end_time}, {bulk_size}, {count}")
            cursor.execute(sql, (start_time, end_time, bulk_size, count))
            commands = cursor.fetchall()

            if not commands:
                print("已完成所有数据的读取，未查询到符合条件的数据。")
                break

            print(f"读取到 {len(commands)} 条数据，开始写入 Elasticsearch...")
            bulk_save(commands)
            print(f"已写入 Elasticsearch 的数据条数：{count + len(commands)}")
            count += len(commands)

    except MySQLdb.OperationalError as db_err:
        print(f"MySQL 数据库连接错误：{db_err}")
    except Exception as e:
        print("导出数据时发生错误:", e)
        traceback.print_exc()
    finally:
        try:
            mysql_connect.close()
            print("MySQL 连接已关闭")
        except NameError:
            print("MySQL 连接尚未建立，无法关闭")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Data migration script")
    parser.add_argument('start', type=str, help='Start date (YYYY-MM-DD)')
    parser.add_argument('end', type=str, help='End date (YYYY-MM-DD)')
    args = parser.parse_args()

    # 将输入的日期转换为 Unix 时间戳
    try:
        start = int(time.mktime(datetime.strptime(args.start, "%Y-%m-%d").timetuple()))
        end = int(time.mktime(datetime.strptime(args.end, "%Y-%m-%d").timetuple()))
    except ValueError:
        print("日期格式错误，请输入有效的日期 (格式: YYYY-MM-DD)")
        exit(1)

    get_mysql(start, end)

# 执行格式
# python es3.py 2024-12-01 2024-12-08
