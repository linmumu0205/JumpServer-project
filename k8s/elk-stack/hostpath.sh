#!/bin/bash

# 创建 Elasticsearch PV 目录
mkdir -p /data/elk/elasticsearch-0
mkdir -p /data/elk/elasticsearch-1

# 创建 Logstash PV 目录
mkdir -p /data/elk/logstash/data
mkdir -p /data/elk/logstash/pipeline

# 赋予权限
chmod -R 777 /data/elk/

# 输出信息
echo "PV 目录已创建："
ls -ld /data/elk/*

# 应用 PV 配置
kubectl apply -f pv-with-elk.yaml

# 确认 PV 是否创建成功
kubectl get pv -n elk


##快捷删除操作

#kubectl delete all --all --namespace=elk
#kubectl delete pvc --all --namespace=elk
#kubectl delete configmap --all --namespace=elk
