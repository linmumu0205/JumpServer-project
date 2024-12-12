# -*- coding: utf-8 -*-
# __author:linmy
# data:2024/12/11

import argparse
import os
import time
import traceback
from datetime import datetime
import pymysql  # 使用 pymysql 替代 MySQLdb
import pytz
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
import logging
import ssl

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 从配置文件加载数据库和 Elasticsearch 配置
config = {
    "DB_HOST": os.getenv("DB_HOST", "10.1.12.74"),
    "DB_PORT": int(os.getenv("DB_PORT", 3306)),
    "DB_USER": os.getenv("DB_USER", "root"),
    "DB_PASSWORD": os.getenv("DB_PASSWORD", "123456"),
    "DB_NAME": os.getenv("DB_NAME", "jumpserver"),
    "DB_CHARSET": 'utf8',
    "ES_HOST": os.getenv("ES_HOST", "http://10.1.12.120:9200"),  # 使用 https
    "ES_USER": os.getenv("ES_USER", "elastic"),
    "ES_PASSWORD": os.getenv("ES_PASSWORD", "#In2431535"),
    "ES_INDEX": 'test'  # 真实索引
}

# 检查 pymysql 版本
import pymysql

logging.info(f"Using pymysql version: {pymysql.__version__}")

# 配置 SSL
#ssl_context = ssl.create_default_context()
#ssl_context.check_hostname = False
#ssl_context.verify_mode = ssl.CERT_NONE

# 初始化 Elasticsearch 客户端
es = Elasticsearch(
    hosts=[config["ES_HOST"]],
    basic_auth=(config["ES_USER"], config["ES_PASSWORD"]),  # 使用 basic_auth 替代 http_auth
    verify_certs=False,
    #ssl_context=ssl_context
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


def bulk_save(command_set, raise_on_error=True, max_retries=3):
    """
    批量保存到 Elasticsearch
    """
    actions = []
    for command in command_set:
        data = {
            "_index": config["ES_INDEX"],
            "_source": make_data(command),
        }
        actions.append(data)

    for attempt in range(max_retries + 1):
        try:
            return bulk(es, actions, index=config["ES_INDEX"], raise_on_error=raise_on_error)
        except Exception as e:
            if attempt < max_retries:
                logging.warning(f"批量保存失败，尝试重试 ({attempt + 1}/{max_retries}): {e}")
                time.sleep(2)  # 等待2秒后重试
            else:
                logging.error(f"批量保存失败，达到最大重试次数: {e}")
                raise


def get_mysql(start_time=None, end_time=None):
    """
    从 MySQL 获取数据并写入 Elasticsearch
    """
    filter_sql = "SELECT * FROM terminal_command WHERE timestamp >= %s AND timestamp <= %s"
    logging.info(f"开始导出数据，时间范围：{start_time} 至 {end_time} (Unix 时间戳格式)")

    try:
        # 使用 pymysql 连接 MySQL 数据库
        mysql_connect = pymysql.connect(
            host=config["DB_HOST"], port=config["DB_PORT"], user=config["DB_USER"], password=config["DB_PASSWORD"], db=config["DB_NAME"] ,charset = config["DB_CHARSET"]
        )
        cursor = mysql_connect.cursor()  # 使用默认游标类
        count = 0
        bulk_size = 5000

        while True:
            sql = filter_sql + " LIMIT %s OFFSET %s"
            logging.info(f"正在执行 SQL: {sql} 参数: {start_time}, {end_time}, {bulk_size}, {count}")
            cursor.execute(sql, (start_time, end_time, bulk_size, count))
            commands = cursor.fetchall()

            if not commands:
                logging.info("已完成所有数据的读取，未查询到符合条件的数据。")
                break

            # 将结果转换为字典
            commands = [dict(zip([col[0] for col in cursor.description], row)) for row in commands]

            logging.info(f"读取到 {len(commands)} 条数据，开始写入 Elasticsearch...")
            bulk_save(commands)
            logging.info(f"已写入 Elasticsearch 的数据条数：{count + len(commands)}")
            count += len(commands)

    except pymysql.MySQLError as db_err:
        logging.error(f"MySQL 数据库连接错误：{db_err}")
        exit(1)
    except Exception as e:
        logging.error("导出数据时发生错误:", exc_info=True)
    finally:
        try:
            mysql_connect.close()
            logging.info("MySQL 连接已关闭")
        except NameError:
            logging.warning("MySQL 连接尚未建立，无法关闭")


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
        logging.error("日期格式错误，请输入有效的日期 (格式: YYYY-MM-DD)")
        exit(1)

    # 测试 Elasticsearch 连接
    try:
        es_info = es.info()
        logging.info(f"Elasticsearch 连接成功: {es_info}")
    except Exception as e:
        logging.error(f"Elasticsearch 连接失败: {e}")
        exit(1)

    # 开始数据迁移
    get_mysql(start, end)
