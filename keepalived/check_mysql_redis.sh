#!/bin/bash

# Keepalived 检测脚本：监控MySQL和Redis服务端口状态
# 如果任一服务端口无法访问，返回非零值，触发Keepalived故障转移

# 日志文件路径
LOG_FILE="$(dirname $0)/keepalived-check.log"
LOG_DIR=$(dirname "$LOG_FILE")

# 记录日志的函数
log_message() {
    local level=$1
    local message=$2
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "${timestamp} - [${level}] ${message}" >> "$LOG_FILE"
}

# MySQL连接参数
MYSQL_HOST="127.0.0.1"
MYSQL_PORT="3306"

# Redis连接参数
REDIS_HOST="127.0.0.1"
REDIS_PORT="6379"

# 检查端口是否开放
check_port() {
    local host=$1
    local port=$2
    local service_name=$3
    
    # 使用nc命令检查端口是否开放
    nc -z -w 1 "$host" "$port" &>/dev/null
    
    if [ $? -eq 0 ]; then
        log_message "INFO" "${service_name}端口($port)开放正常"
        return 0
    else
        log_message "ERROR" "${service_name}端口($port)无法访问"
        return 1
    fi
}

# 主函数
main() {
    # 检查日志目录是否存在，不存在则创建
    if [ ! -d "$LOG_DIR" ]; then
        mkdir -p "$LOG_DIR" 2>/dev/null || {
            echo "无法创建日志目录，请检查权限"
            exit 1
        }
    fi
    
    # 检查日志文件是否存在，不存在则创建
    if [ ! -f "$LOG_FILE" ]; then
        touch "$LOG_FILE" 2>/dev/null || {
            echo "无法创建日志文件，请检查权限"
            exit 1
        }
    fi
    
    log_message "INFO" "开始检查服务端口状态"
    
    # 检查MySQL端口
    check_port "$MYSQL_HOST" "$MYSQL_PORT" "MySQL"
    mysql_status=$?
    
    # 检查Redis端口
    check_port "$REDIS_HOST" "$REDIS_PORT" "Redis"
    redis_status=$?
    
    # 如果任一服务端口异常，返回非零值
    if [ $mysql_status -ne 0 ] || [ $redis_status -ne 0 ]; then
        log_message "ERROR" "服务端口检查失败，触发Keepalived故障转移"
        exit 1
    fi
    
    log_message "INFO" "所有服务端口正常开放"
    exit 0
}

# 执行主函数
main