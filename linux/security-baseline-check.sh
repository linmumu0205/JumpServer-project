#!/bin/bash

# Linux系统安全基线检查脚本
# 用于检查系统安全配置并生成安全评估报告

# 检查是否以root权限运行
if [ "$(id -u)" -ne 0 ]; then 
    echo "请使用root权限运行此脚本"
    exit 1
fi

# 定义颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 创建报告目录和文件
REPORT_DIR="/var/log/security-baseline"
REPORT_FILE="${REPORT_DIR}/security-check-$(date +%Y%m%d-%H%M%S).log"
mkdir -p "$REPORT_DIR" 2>/dev/null
touch "$REPORT_FILE" 2>/dev/null || {
    echo "${RED}无法创建报告文件，请检查权限${NC}"
    exit 1
}

# 记录检查结果的函数
log_result() {
    local level=$1
    local check_item=$2
    local result=$3
    local suggestion=$4
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    case $level in
        "HIGH") local color=$RED ;;
        "MEDIUM") local color=$YELLOW ;;
        "LOW") local color=$GREEN ;;
        *) local color=$NC ;;
    esac
    
    echo -e "${color}[${level}] ${check_item}\n结果: ${result}\n建议: ${suggestion}${NC}\n" | tee -a "$REPORT_FILE"
}

# 1. 检查密码策略
check_password_policy() {
    echo "正在检查密码策略..."
    
    # 检查密码最小长度
    local min_length=$(grep '^PASS_MIN_LEN' /etc/login.defs | awk '{print $2}')
    if [ -z "$min_length" ] || [ "$min_length" -lt 8 ]; then
        log_result "HIGH" "密码最小长度" "当前设置: ${min_length:-未设置}" "建议将密码最小长度设置为8个字符以上"
    fi
    
    # 检查密码复杂度要求
    if [ -f "/etc/pam.d/common-password" ]; then
        if ! grep -q "pam_pwquality.so" /etc/pam.d/common-password; then
            log_result "HIGH" "密码复杂度" "未启用密码复杂度检查" "建议安装并配置pam_pwquality模块"
        fi
    fi
}

# 2. 检查系统用户和权限
check_user_permissions() {
    echo "正在检查用户权限..."
    
    # 检查root账户SSH登录设置
    if grep -q "^PermitRootLogin yes" /etc/ssh/sshd_config 2>/dev/null; then
        log_result "HIGH" "Root SSH登录" "允许root直接SSH登录" "建议禁用root直接SSH登录，使用普通用户+sudo方式"
    fi
    
    # 检查空密码账户
    local empty_pass=$(awk -F: '($2 == "") {print $1}' /etc/shadow 2>/dev/null)
    if [ ! -z "$empty_pass" ]; then
        log_result "HIGH" "空密码账户" "发现空密码账户: $empty_pass" "建议为所有账户设置强密码"
    fi
}

# 3. 检查系统服务
check_system_services() {
    echo "正在检查系统服务..."
    
    # 检查不必要的服务
    services="telnet rsh rlogin rexec"
    for service in $services; do
        if systemctl is-active --quiet "$service" 2>/dev/null; then
            log_result "HIGH" "危险服务" "服务 $service 正在运行" "建议停用并禁用该服务"
        fi
    done
    
    # 检查防火墙状态
    if ! systemctl is-active --quiet firewalld && ! systemctl is-active --quiet ufw; then
        log_result "HIGH" "防火墙" "系统防火墙未启用" "建议启用并正确配置防火墙"
    fi
}

# 4. 检查文件系统安全
check_filesystem_security() {
    echo "正在检查文件系统安全..."
    
    # 检查重要目录权限
    local important_dirs="/etc /bin /sbin /usr/bin /usr/sbin"
    for dir in $important_dirs; do
        local perms=$(stat -c "%a" "$dir" 2>/dev/null)
        if [ "$perms" != "755" ]; then
            log_result "MEDIUM" "目录权限" "$dir 权限: $perms" "建议设置权限为755"
        fi
    done
    
    # 检查SUID/SGID文件
    echo "检查SUID/SGID文件..."
    find / -type f \( -perm -4000 -o -perm -2000 \) -exec ls -l {} \; 2>/dev/null | \
    while read -r line; do
        log_result "MEDIUM" "SUID/SGID文件" "发现SUID/SGID文件: $line" "请检查这些文件是否必要"
    done
}

# 5. 检查网络安全配置
check_network_security() {
    echo "正在检查网络安全配置..."
    
    # 检查SSH配置
    if [ -f "/etc/ssh/sshd_config" ]; then
        # 检查SSH协议版本
        if grep -q "^Protocol 1" /etc/ssh/sshd_config; then
            log_result "HIGH" "SSH协议版本" "使用不安全的SSH协议版本1" "建议只使用SSH协议版本2"
        fi
        
        # 检查SSH密钥认证
        if ! grep -q "^PubkeyAuthentication yes" /etc/ssh/sshd_config; then
            log_result "MEDIUM" "SSH密钥认证" "未启用SSH密钥认证" "建议启用SSH密钥认证"
        fi
    fi
    
    # 检查开放端口
    local open_ports=$(netstat -tuln | grep LISTEN)
    if [ ! -z "$open_ports" ]; then
        log_result "MEDIUM" "开放端口" "系统开放的端口:\n$open_ports" "请检查这些端口是否必要"
    fi
}

# 6. 检查系统日志配置
check_system_logging() {
    echo "正在检查系统日志配置..."
    
    # 检查rsyslog服务
    if ! systemctl is-active --quiet rsyslog; then
        log_result "MEDIUM" "系统日志服务" "rsyslog服务未运行" "建议启用rsyslog服务"
    fi
    
    # 检查日志文件权限
    local log_files="/var/log/syslog /var/log/auth.log /var/log/secure"
    for log in $log_files; do
        if [ -f "$log" ]; then
            local perms=$(stat -c "%a" "$log")
            if [ "$perms" != "640" ]; then
                log_result "MEDIUM" "日志文件权限" "$log 权限: $perms" "建议设置权限为640"
            fi
        fi
    done
}

# 7. 检查SELinux/AppArmor状态
check_mac_status() {
    echo "正在检查SELinux/AppArmor状态..."
    
    # 检查SELinux状态
    if command -v getenforce >/dev/null 2>&1; then
        local selinux_status=$(getenforce 2>/dev/null)
        if [ "$selinux_status" = "Disabled" ] || [ "$selinux_status" = "Permissive" ]; then
            log_result "HIGH" "SELinux状态" "当前状态: $selinux_status" "建议启用SELinux并设置为Enforcing模式"
        fi
    fi
    
    # 检查AppArmor状态
    if command -v aa-status >/dev/null 2>&1; then
        if ! aa-status >/dev/null 2>&1; then
            log_result "HIGH" "AppArmor状态" "AppArmor未正确运行" "建议启用并正确配置AppArmor"
        fi
    fi
}

# 8. 检查系统内核参数安全配置
check_kernel_parameters() {
    echo "正在检查系统内核参数安全配置..."
    
    # 检查IP转发
    local ip_forward=$(sysctl -n net.ipv4.ip_forward 2>/dev/null)
    if [ "$ip_forward" = "1" ]; then
        log_result "MEDIUM" "IP转发" "IP转发已启用" "如非必要，建议禁用IP转发功能"
    fi
    
    # 检查ICMP重定向
    local icmp_redirect=$(sysctl -n net.ipv4.conf.all.accept_redirects 2>/dev/null)
    if [ "$icmp_redirect" = "1" ]; then
        log_result "MEDIUM" "ICMP重定向" "接受ICMP重定向已启用" "建议禁用ICMP重定向以防止路由劫持"
    fi
    
    # 检查源路由
    local source_routing=$(sysctl -n net.ipv4.conf.all.accept_source_route 2>/dev/null)
    if [ "$source_routing" = "1" ]; then
        log_result "HIGH" "源路由" "接受源路由已启用" "建议禁用源路由以防止IP欺骗攻击"
    fi
    
    # 检查SYN Cookie保护
    local syn_cookies=$(sysctl -n net.ipv4.tcp_syncookies 2>/dev/null)
    if [ "$syn_cookies" = "0" ]; then
        log_result "HIGH" "SYN Cookie保护" "SYN Cookie保护未启用" "建议启用SYN Cookie以防止SYN洪水攻击"
    fi
}

# 9. 检查定时任务安全
check_cron_jobs() {
    echo "正在检查定时任务安全..."
    
    # 检查定时任务文件权限
    local cron_files="/etc/crontab /etc/cron.d /etc/cron.daily /etc/cron.weekly /etc/cron.monthly"
    for cron in $cron_files; do
        if [ -e "$cron" ]; then
            local perms=$(stat -c "%a" "$cron")
            if [ "$perms" != "644" ] && [ "$perms" != "755" ]; then
                log_result "MEDIUM" "定时任务权限" "$cron 权限: $perms" "建议设置适当的权限（644或755）"
            fi
        fi
    done
    
    # 检查可疑的定时任务
    if [ -f "/etc/crontab" ]; then
        local suspicious=$(grep -E "(wget|curl|nc|bash.*http)" /etc/crontab)
        if [ ! -z "$suspicious" ]; then
            log_result "HIGH" "可疑定时任务" "发现可疑命令: $suspicious" "建议检查这些定时任务的合法性"
        fi
    fi
}

# 10. 检查系统账户配置
check_system_accounts() {
    echo "正在检查系统账户配置..."
    
    # 检查系统账户shell配置
    local system_accounts=$(awk -F: '$3 < 1000 && $1 != "root" {print $1}' /etc/passwd)
    for account in $system_accounts; do
        local shell=$(grep "^$account:" /etc/passwd | cut -d: -f7)
        if [ "$shell" != "/sbin/nologin" ] && [ "$shell" != "/bin/false" ]; then
            log_result "HIGH" "系统账户Shell" "账户 $account 使用可登录的shell: $shell" "建议将系统账户的shell设置为/sbin/nologin或/bin/false"
        fi
    done
    
    # 检查UID为0的账户
    local root_accounts=$(awk -F: '$3 == 0 {print $1}' /etc/passwd)
    if [ "$(echo "$root_accounts" | wc -l)" -gt 1 ]; then
        log_result "HIGH" "Root权限账户" "发现多个UID为0的账户: $root_accounts" "系统中只应该有一个root账户"
    fi
}

# 11. 检查关键文件完整性
check_file_integrity() {
    echo "正在检查关键文件完整性..."
    
    # 检查关键系统文件权限
    local critical_files="/etc/passwd /etc/shadow /etc/group /etc/gshadow /etc/sudoers"
    for file in $critical_files; do
        if [ -f "$file" ]; then
            local perms=$(stat -c "%a" "$file")
            case "$file" in
                "/etc/passwd") [ "$perms" != "644" ] && log_result "HIGH" "文件权限" "$file 权限: $perms" "建议设置权限为644" ;;
                "/etc/shadow") [ "$perms" != "400" ] && [ "$perms" != "000" ] && log_result "HIGH" "文件权限" "$file 权限: $perms" "建议设置权限为400" ;;
                "/etc/group") [ "$perms" != "644" ] && log_result "HIGH" "文件权限" "$file 权限: $perms" "建议设置权限为644" ;;
                "/etc/gshadow") [ "$perms" != "400" ] && log_result "HIGH" "文件权限" "$file 权限: $perms" "建议设置权限为400" ;;
                "/etc/sudoers") [ "$perms" != "440" ] && log_result "HIGH" "文件权限" "$file 权限: $perms" "建议设置权限为440" ;;
            esac
        fi
    done
    
    # 检查关键文件是否被修改
    if command -v md5sum >/dev/null 2>&1; then
        for file in $critical_files; do
            if [ -f "$file" ] && [ -f "${file}.md5" ]; then
                local current_md5=$(md5sum "$file" | cut -d' ' -f1)
                local stored_md5=$(cat "${file}.md5")
                if [ "$current_md5" != "$stored_md5" ]; then
                    log_result "HIGH" "文件完整性" "$file MD5校验不匹配" "文件可能被篡改，请检查"
                fi
            fi
        done
    fi
}

# 主函数
main() {
    echo -e "${GREEN}开始进行Linux系统安全基线检查...${NC}\n"
    echo "检查结果将保存到: $REPORT_FILE"
    echo "-----------------------------------------"
    
    # 执行各项检查
    check_password_policy
    check_user_permissions
    check_system_services
    check_filesystem_security
    check_network_security
    check_system_logging
    check_mac_status
    check_kernel_parameters
    check_cron_jobs
    check_system_accounts
    check_file_integrity
    
    echo -e "\n${GREEN}安全基线检查完成！${NC}"
    echo "详细报告已保存到: $REPORT_FILE"
    echo "请仔细阅读报告并根据建议进行系统加固"
}

# 运行主函数
main

# 设置脚本权限
chmod +x "$0"