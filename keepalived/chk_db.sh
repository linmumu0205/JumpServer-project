#!/bin/bash

# MySQL和Redis端口
MYSQL_PORT=3306
REDIS_PORT=6379

# 检查MySQL端口
if ! ss -nlpt | grep -q ":$MYSQL_PORT"; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') - MySQL端口($MYSQL_PORT)无法访问" >> /var/log/keepalived-check.log
    exit 1
fi

# 检查Redis端口
if ! ss -nlpt | grep -q ":$REDIS_PORT"; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Redis端口($REDIS_PORT)无法访问" >> /var/log/keepalived-check.log
    exit 1
fi

# 所有端口正常
echo "$(date '+%Y-%m-%d %H:%M:%S') - 所有服务端口正常开放" >> /var/log/keepalived-check.log
exit 0