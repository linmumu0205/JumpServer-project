#!/bin/bash

# 系统清理脚本
# 用于清理Linux系统中的临时文件、日志和缓存

# 检查是否以root权限运行
if [ "$EUID" -ne 0 ]; then 
    echo "请使用root权限运行此脚本"
    exit 1
fi

# 定义颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 创建日志文件
LOG_FILE="/var/log/system-cleanup-$(date +%Y%m%d-%H%M%S).log"
touch "$LOG_FILE" 2>/dev/null || {
    echo "${RED}无法创建日志文件，请检查权限${NC}"
    exit 1
}

# 记录日志的函数
log_message() {
    local level=$1
    local message=$2
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    case $level in
        "INFO") local color=$GREEN ;;
        "WARN") local color=$YELLOW ;;
        "ERROR") local color=$RED ;;
        *) local color=$NC ;;
    esac
    echo -e "${color}${timestamp} - [${level}] ${message}${NC}" | tee -a "$LOG_FILE"
}

# 错误处理函数
handle_error() {
    local exit_code=$?
    local error_message=$1
    if [ $exit_code -ne 0 ]; then
        log_message "ERROR" "${error_message}：$exit_code"
        return 1
    fi
    return 0
}

# 显示进度条
show_progress() {
    local current=$1
    local total=$2
    local width=50
    local percentage=$((current * 100 / total))
    local filled=$((width * current / total))
    local empty=$((width - filled))
    printf "\r进度: [%${filled}s%${empty}s] %d%%" "" "" "$percentage"
}

# 获取目录大小
get_dir_size() {
    local dir=$1
    if [ -d "$dir" ]; then
        du -sh "$dir" 2>/dev/null | cut -f1
    else
        echo "0"
    fi
}

# 显示清理前的磁盘使用情况
log_message "INFO" "清理前的磁盘使用情况："
df -h / | tail -n 1

# 清理前确认
echo -e "${YELLOW}警告：此脚本将清理系统中的临时文件和旧日志文件${NC}"
read -p "是否继续？(y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    log_message "INFO" "用户取消操作"
    exit 0
fi

# 开始清理操作
log_message "INFO" "开始系统清理"
total_steps=7
current_step=0

# 1. 清理系统日志
current_step=$((current_step + 1))
show_progress $current_step $total_steps
log_message "INFO" "清理系统日志文件..."
find /var/log -type f \( -name "*.gz" -o -name "*.old" -o -name "*.1" -o -name "*.2" -o -name "*.3" -o -name "*.4" -o -name "*.5" \) -delete 2>/dev/null || handle_error "清理系统日志失败"
for log_file in /var/log/{syslog,auth.log,messages,kern.log}; do
    if [ -f "$log_file" ]; then
        cp /dev/null "$log_file" 2>/dev/null || handle_error "清空 $log_file 失败"
    fi
done
log_message "INFO" "系统日志清理完成"

# 2. 清理临时文件
current_step=$((current_step + 1))
show_progress $current_step $total_steps
log_message "INFO" "清理临时文件..."
find /tmp -type f -atime +7 -delete 2>/dev/null || handle_error "清理临时文件失败"
find /tmp -type d -empty -delete 2>/dev/null
log_message "INFO" "临时文件清理完成"

# 3. 清理软件包缓存
current_step=$((current_step + 1))
show_progress $current_step $total_steps
if command -v apt-get &> /dev/null; then
    log_message "INFO" "清理APT缓存..."
    apt-get clean || handle_error "清理APT缓存失败"
    apt-get autoremove -y || handle_error "自动移除未使用的包失败"
    log_message "INFO" "APT缓存清理完成"
fi

if command -v yum &> /dev/null; then
    log_message "INFO" "清理YUM缓存..."
    yum clean all || handle_error "清理YUM缓存失败"
    log_message "INFO" "YUM缓存清理完成"
fi

# 4. 清理Docker缓存（如果安装了Docker）
current_step=$((current_step + 1))
show_progress $current_step $total_steps
if command -v docker &> /dev/null; then
    log_message "INFO" "清理Docker缓存..."
    docker system prune -af || handle_error "清理Docker缓存失败"
    log_message "INFO" "Docker缓存清理完成"
fi

# 5. 清理旧内核
current_step=$((current_step + 1))
show_progress $current_step $total_steps
if command -v apt-get &> /dev/null; then
    log_message "INFO" "清理旧内核..."
    current_kernel=$(uname -r)
    dpkg --list | grep 'linux-image' | awk '{ print $2 }' | grep -v "$current_kernel" | while read -r kernel; do
        apt-get purge -y "$kernel" || handle_error "清理内核 $kernel 失败"
    done
    log_message "INFO" "旧内核清理完成"
fi

# 6. 清理系统缓存
current_step=$((current_step + 1))
show_progress $current_step $total_steps
log_message "INFO" "清理系统缓存..."
sync || handle_error "同步文件系统失败"
echo 3 > /proc/sys/vm/drop_caches 2>/dev/null || handle_error "清理系统缓存失败"
log_message "INFO" "系统缓存清理完成"

# 7. 清理用户缓存
current_step=$((current_step + 1))
show_progress $current_step $total_steps
log_message "INFO" "清理用户缓存..."
find /home -type f -name ".cache" -exec rm -rf {} + 2>/dev/null || handle_error "清理用户缓存失败"
log_message "INFO" "用户缓存清理完成"

# 显示清理后的磁盘使用情况
echo -e "\n${GREEN}清理后的磁盘使用情况：${NC}"
df -h / | tail -n 1

# 计算节省的空间
log_message "INFO" "系统清理完成"
echo -e "\n${GREEN}清理日志已保存到: $LOG_FILE${NC}"
echo "请检查系统状态确保一切正常"

# 设置脚本权限
chmod +x "$0"