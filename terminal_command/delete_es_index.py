from datetime import datetime
from elasticsearch7 import Elasticsearch

def delete_docs_by_time_range(index, start_date_str, end_date_str):
    # 将日期字符串转换为 datetime 对象，并假设一天的时间范围
    start_time_dt = datetime.strptime(start_date_str, "%Y-%m-%d")
    end_time_dt = datetime.strptime(end_date_str, "%Y-%m-%d").replace(hour=23, minute=59, second=59)

    # 将 datetime 对象转换为 Unix 时间戳（毫秒）
    start_timestamp = int(start_time_dt.timestamp()) * 1000
    end_timestamp = int(end_time_dt.timestamp()) * 1000

    # Elasticsearch 查询
    query = {
        "query": {
            "range": {
                "@timestamp": {
                    "gte": start_timestamp,
                    "lte": end_timestamp
                }
            }
        }
    }

    # 删除文档
    es = Elasticsearch("http://elastic:L5ieauiPO2xLbDpoI0zHngDn@10.76.27.32:9200")
    es.delete_by_query(index=index, body=query)
    print(f"Documents from {start_date_str} to {end_date_str} deleted.")

# 使用示例
index_name = "jumpserver"
start_date = "2024-04-01"
end_date = "2024-05-01"

delete_docs_by_time_range(index_name, start_date, end_date)
