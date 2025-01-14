# -*- coding: utf-8 -*-
# __author: linmy
# data: 2024/12/11

import argparse
import os
import time
from datetime import datetime
import pymysql
import pytz
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
import logging
import ssl

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 从配置文件加载数据库和 Elasticsearch 配置
config = {
    "DB_HOST": os.getenv("DB_HOST", "10.1.12.94"),
    "DB_PORT": int(os.getenv("DB_PORT", 3306)),
    "DB_USER": os.getenv("DB_USER", "jumpserver"),
    "DB_PASSWORD": os.getenv("DB_PASSWORD", "123456"),
    "DB_NAME": os.getenv("DB_NAME", "jumpserver"),
    "DB_CHARSET": 'utf8',
    "ES_HOST": os.getenv("ES_HOST", "http://10.1.12.120:9200"),  # 使用 https
    "ES_USER": os.getenv("ES_USER", "elastic"),
    "ES_PASSWORD": os.getenv("ES_PASSWORD", "#In2431535"),
    "ES_INDEX": 'jumpserver'  # 基础索引名
}

# 初始化 Elasticsearch 客户端
es = Elasticsearch(
    hosts=[config["ES_HOST"]],
    basic_auth=(config["ES_USER"], config["ES_PASSWORD"]),
    verify_certs=False
)


def create_index_with_mapping(index_name):
    """
    如果索引不存在，创建索引并设置映射
    """
    mapping = {
        "mappings": {
            "properties": {
                "session": {"type": "keyword"},
                "org_id": {"type": "keyword"},
                "user": {"type": "text"},
                "asset": {"type": "text"},
                "account": {"type": "text"},
                "input": {"type": "text"},
                "output": {"type": "text"},
                "risk_level": {"type": "text"},
                "timestamp": {"type": "date"},
                "@timestamp": {"type": "date"}
            }
        }
    }

    if not es.indices.exists(index=index_name):
        try:
            es.indices.create(index=index_name, body=mapping)
            logging.info(f"索引 {index_name} 创建成功，映射已应用。")
        except Exception as e:
            logging.error(f"索引 {index_name} 创建失败: {e}")
            raise


def make_data(command):
    """
    构造 Elasticsearch 文档并创建索引
    """
    index_date = datetime.fromtimestamp(command["timestamp"], tz=pytz.UTC).strftime('%Y-%m-%d')
    index_name = f"{config['ES_INDEX']}-{index_date}"

    # 调用创建索引函数
    create_index_with_mapping(index_name)

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
    return index_name, data


def bulk_save(command_set, raise_on_error=True, max_retries=3):
    """
    批量保存到 Elasticsearch
    """
    actions = []
    for command in command_set:
        index_name, data = make_data(command)
        action = {
            "_index": index_name,
            "_source": data,
        }
        actions.append(action)

    for attempt in range(max_retries + 1):
        try:
            return bulk(es, actions, raise_on_error=raise_on_error)
        except Exception as e:
            if attempt < max_retries:
                logging.warning(f"批量保存失败，尝试重试 ({attempt + 1}/{max_retries}): {e}")
                time.sleep(2)
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
        mysql_connect = pymysql.connect(
            host=config["DB_HOST"], port=config["DB_PORT"], user=config["DB_USER"],
            password=config["DB_PASSWORD"], db=config["DB_NAME"], charset=config["DB_CHARSET"]
        )
        cursor = mysql_connect.cursor()
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

    try:
        start = int(time.mktime(datetime.strptime(args.start, "%Y-%m-%d").timetuple()))
        end = int(time.mktime(datetime.strptime(args.end, "%Y-%m-%d").timetuple()))
    except ValueError:
        logging.error("日期格式错误，请输入有效的日期 (格式: YYYY-MM-DD)")
        exit(1)

    try:
        es_info = es.info()
        logging.info(f"Elasticsearch 连接成功: {es_info}")
    except Exception as e:
        logging.error(f"Elasticsearch 连接失败: {e}")
        exit(1)

    get_mysql(start, end)
