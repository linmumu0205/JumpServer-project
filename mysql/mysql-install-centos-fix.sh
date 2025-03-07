#!/bin/bash
## 脚本已验证os系统：centos7、centos stream8、centos stream9；
##
## 对于CentOS Stream 8-9 系统需要：
## - ln -s /usr/lib64/libncurses.so.6 /usr/lib64/libncurses.so.5
## - yum install ncurses-compat-libs -y
## 对于CentOS Stream 9 系统还需要：
## - 关闭selinux
## - yum install ncurses* -y
## - ln -s /usr/lib64/libncurses.so.6 /usr/lib64/libncurses.so.5
## - ln -s /usr/lib64/libtinfo.so.6 /usr/lib64/libtinfo.so.5
## - yum install chkconfig -y
## 对于 Ubuntu 系统增加：
## - sudo apt-get update
## - sudo apt-get install libncurses5

# 用户输入配置
read -p "请输入mysql的基础安装路径(如/usr/local/mysql)： " mysqlbasedir
default_mysqlbasedir=/usr/local/mysql
if [[ ! "$mysqlbasedir" =~ ^/ ]]; then
    mysqlbasedir="$default_mysqlbasedir"
fi

read -p "请输入mysql的数据存放路径(如/data/mysqldata)： " mysqldatadir
default_mysqldatadir=/data/mysqldata
if [[ ! "$mysqldatadir" =~ ^/ ]]; then
    mysqldatadir="$default_mysqldatadir"
fi

read -p "请输入mysql的server-id(主从架构下id注意区分，必须为数字)： " id
read -p "请输入mysql的数据起始位置(主从架构下起始位注意区分，可以填1或者2)： " offset

# 下载MySQL依赖包
echo "安装前置依赖包--------------------------------------------"
yum install libaio -y || { echo "依赖包安装失败，退出脚本"; exit 1; }

# 创建mysql目录和用户
mkdir -p ${mysqlbasedir}
mkdir -p ${mysqldatadir}
groupadd mysql
useradd -g mysql mysql
chown mysql.mysql ${mysqldatadir}

# 下载MySQL编译包
echo "下载MySQL编译包--------------------------------------------"
if [ -e mysql-5.7.36-linux-glibc2.12-x86_64.tar.gz ]; then
    echo "File mysql-5.7.36-linux-glibc2.12-x86_64.tar.gz exists."
    echo "mysql包已存在。。。"
    sleep 5
else
    echo "File mysql-5.7.36-linux-glibc2.12-x86_64.tar.gz does not exist."
    echo "准备下载MySQL编译包。。。"
    wget -q --tries=3 http://dev.mysql.com/get/Downloads/MySQL-5.7/mysql-5.7.36-linux-glibc2.12-x86_64.tar.gz --no-check-certificate || { echo "下载失败，退出脚本"; exit 1; }
fi

# 解压MySQL并移动文件
echo "解压MySQL并开始安装--------------------------------------------"
tar -zxvf mysql-5.7.36-linux-glibc2.12-x86_64.tar.gz -C ${mysqlbasedir} || { echo "解压失败，退出脚本"; exit 1; }
cd ${mysqlbasedir}/mysql-5.7.36-linux-glibc2.12-x86_64/
mv * ${mysqlbasedir}/
cd ${mysqlbasedir}
rm -rf mysql-5.7.36-linux-glibc2.12-x86_64/

# 配置MySQL的my.cnf文件
echo "配置my.cnf默认配置文件--------------------------------------------"
cat > ${mysqlbasedir}/support-files/my_default.conf <<EOF
[mysqld]
character-set-server=utf8
basedir = ${mysqlbasedir}
datadir = ${mysqldatadir}
log-error = ${mysqlbasedir}/mysqld.log
port = 3306
socket = /tmp/mysql.sock
pid-file = /tmp/mysqld.pid

default-storage-engine = INNODB
lower_case_table_names = 1

innodb_buffer_pool_size = 4096M
innodb_buffer_pool_instances = 4
innodb_log_file_size = 1024M
tmp_table_size = 16M
max_heap_table_size = 16M
key_buffer_size = 192K

symbolic-links = 0
query_cache_size = 16M
thread_cache_size = 8
table_open_cache = 128
max_connections = 600
innodb_file_per_table = 1
bind-address = 0.0.0.0

sql_mode = STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_AUTO_CREATE_USER,NO_ENGINE_SUBSTITUTION

server-id = ${id} # 本机序列号
log-bin = mysql-bin
binlog-do-db = jumpserver
replicate-do-db = jumpserver
expire_logs_days = 30

log-slave-updates
slave-skip-errors = all
sync_binlog = 1
auto_increment_increment = 2
auto_increment_offset = ${offset}
skip-name-resolve = 1

[mysql]
default-character-set = utf8
EOF

# 初始化数据库
echo "初始化MySQL数据库--------------------------------------------"
touch ${mysqlbasedir}/mysqld.log
chown mysql:mysql ${mysqlbasedir}/mysqld.log
cd ${mysqlbasedir}
bin/mysqld --initialize --user=mysql --basedir=${mysqlbasedir}/ --datadir=${mysqldatadir}/ >> /tmp/mysql-install.log 2>&1 || { echo "MySQL初始化失败，退出脚本"; exit 1; }
sleep 10

# 配置MySQL服务
cp ${mysqlbasedir}/support-files/my_default.conf /etc/my.cnf
cp ${mysqlbasedir}/support-files/mysql.server /etc/init.d/mysql
chmod 755 /etc/init.d/mysql
chkconfig --add mysql
chkconfig --list mysql || { echo "chkconfig命令失败"; exit 1; }

# 启动MySQL
cd ${mysqlbasedir}
bin/mysqld_safe --user=mysql &
sleep 3
bin/mysql_ssl_rsa_setup --datadir=${mysqldatadir}

# 更新环境变量
echo "配置系统环境变量--------------------------------------------"
echo "export PATH=${mysqlbasedir}/bin:\$PATH" >> /etc/profile
source /etc/profile
sleep 3

/etc/init.d/mysql restart || { echo "MySQL重启失败"; exit 1; }

# 防火墙设置
# 放行3306端口
# Uncomment below lines if needed
# firewall-cmd --permanent --zone=public --add-port=3306/tcp
# firewall-cmd --reload

# 配置systemd管理MySQL
echo "配置systemd管理mysqld服务-------------------------------------"
cat > /etc/systemd/system/mysqld.service <<EOF
[Unit]
Description=MySQL Server
Documentation=man:mysqld(8)
After=network.target

[Install]
WantedBy=multi-user.target

[Service]
User=mysql
Group=mysql
Type=forking
PIDFile=/tmp/mysqld.pid
ExecStart=/etc/init.d/mysql start
ExecStop=/etc/init.d/mysql stop
Restart=on-failure
LimitNOFILE=5000
EOF

systemctl daemon-reload
systemctl enable mysqld || { echo "启用systemd失败"; exit 1; }
systemctl start mysqld || { echo "MySQL启动失败"; exit 1; }

# 配置MySQL基础账号
echo "配置MySQL基础账号--------------------------------------------"
mysql_pass=$(grep -oP 'A temporary password is generated for root@localhost: \K.*' /tmp/mysql-install.log) || { echo "获取密码失败"; exit 1; }
echo "root的初始密码为：$mysql_pass"
mysql -uroot -p"${mysql_pass}" --connect-expired-password -e "ALTER USER 'root'@'localhost' IDENTIFIED BY 'jumpserver';"
mysql -uroot -p"jumpserver" --connect-expired-password -e "UPDATE mysql.user SET host = '%' WHERE user = 'root' AND host = 'localhost';"
mysql -uroot -p"jumpserver" --connect-expired-password -e "GRANT ALL PRIVILEGES ON *.* TO root@'%' IDENTIFIED BY 'jumpserver';"
mysql -uroot -p"jumpserver" --connect-expired-password -e "FLUSH PRIVILEGES;"

# 创建数据库
echo "创建数据库jumpserver--------------------------------------------"
mysql -uroot -p"jumpserver" --connect-expired-password -e "CREATE DATABASE jumpserver DEFAULT CHARACTER SET utf8 COLLATE utf8_bin;"
mysql -uroot -p"jumpserver" --connect-expired-password -e "SHOW CREATE DATABASE jumpserver;"

# 添加符号链接，确保mysql命令可以从任何地方访问
echo "创建MySQL命令符号链接-----------------------------------------"
ln -s ${mysqlbasedir}/bin/mysql /usr/local/bin/mysql || { echo "创建符号链接失败，退出脚本"; exit 1; }

# 输出主从配置命令
echo "主从配置参考--------------------------------------------"
mysql -uroot -p"jumpserver" --connect-expired-password -e "SHOW MASTER STATUS\G"
echo "参考命令如下："
echo "/usr/local/mysql/bin/mysql -uroot -p\"jumpserver\" --connect-expired-password -e \"CHANGE MASTER TO MASTER_HOST='192.168.1.183', MASTER_PORT=3306, MASTER_USER='replica', MASTER_PASSWORD='replica_pass', MASTER_LOG_FILE='mysql-bin.000001', MASTER_LOG_POS=107;\""

# 安装完成，提示用户
echo "MySQL安装并配置完成！请检查日志文件以确保一切正常。"
