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

kubectl delete all --all --namespace=elk
kubectl delete pvc --all --namespace=elk
kubectl delete configmap --all --namespace=elk


# 删除 tigera-operator 命名空间中的所有 Evicted Pod
kubectl delete pod -n tigera-operator --field-selector=status.phase=Failed

# 重启副本集 交替重启
kubectl rollout restart statefulset/elasticsearch -n elk

# 重启kibana pod
kubectl rollout restart deployment/kibana -n elk

# 创建elasticsearch超级用户
kubectl exec -it elasticsearch-0 -n elk -- /bin/bash
elasticsearch-users useradd admin -p Admin123! -r superuser
#进入kibana pod写入用户信息
kubectl exec -it kibana-6cb8f98b9b-h8262 -n elk -- /bin/bash
echo "elasticsearch.username: admin" >> /usr/share/kibana/config/kibana.yml
echo "elasticsearch.password: Admin123!" >> /usr/share/kibana/config/kibana.yml

#Elasticsearch 直接在 StatefulSet 更新elasticsearch的xpack
kubectl edit statefulset elasticsearch -n elk
#  在 spec.template.spec.containers.args 里添加 xpack.security.enabled=true
#  找到 containers: 下面的 args: 部分（如果没有，添加 args:），然后修改
spec:
  template:
    spec:
      containers:
        - name: elasticsearch
          args:
            - "elasticsearch"
            - "-E xpack.security.enabled=true"
#保存后重启elasticsearch
kubectl rollout restart statefulset/elasticsearch -n elk

# 上述配置追加到kibans.yml
kubectl edit deployment kibana -n elk
# 追加下面内容
elasticsearch.username: "elastic"
elasticsearch.password: "your-password"
# 保存后重启kibana
kubectl rollout restart deployment/kibana -n elk
