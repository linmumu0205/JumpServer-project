#!/bin/bash
##脚本编写中。。。。
##脚本已验证os系统：centos7、centos stream8、centos stream9；
##
##centos stream8-9系统需要额外添加
##ln -s /usr/lib64/libncurses.so.6 /usr/lib64/libncurses.so.5
##yum install ncurses-compat-libs -y
##
##centos stream9系统需要额外添加
##关闭selinux
##yum install ncurses* -y
##ln -s /usr/lib64/libncurses.so.6 /usr/lib64/libncurses.so.5
##ln -s /usr/lib64/libtinfo.so.6 /usr/lib64/libtinfo.so.5
##yum install chkconfig -y
##ubuntu系统增加
##sudo apt-get update
##sudo apt-get install libncurses5

read -p "请输入mysql的基础安装路径(如/usr/local/mysql)： " mysqlbasedir
default_mysqlbasedir=/usr/local/mysql
if [ -z "$mysqlbasedir" ]; then
    mysqlbasedir="$default_mysqlbasedir"
else
    if [[ "$mysqlbasedir" =~ ^[/] ]]; then
      echo "取值成功，继续执行脚本。。。"
    else
      echo "您输入的路径不符合，需要以/开头，退出脚本。。。"
      exit 1
    fi    
fi

read -p "请输入mysql的数据存放路径(如/data/mysqldata)： " mysqldatadir
default_mysqldatadir=/data/mysqldata
if [ -z "$mysqldatadir" ]; then
    mysqldatadir="$default_mysqldatadir"
else
    if [[ "$mysqldatadir" =~ ^[/] ]]; then
      echo "取值成功，继续执行脚本。。。"
    else
      echo "您输入的路径不符合，需要以/开头，退出脚本。。。"
      exit 1
    fi    
fi

read -p "请输入mysql的server-id(主从架构下id注意区分，必须为数字)： " id
read -p "请输入mysql的数据起始位置(主从架构下起始位注意区分，可以填1或者2)： " offset

##下载mysql前置依赖包
echo "下载mysql前置依赖包--------------------------------------------"
#yum install libaio -y
sleep 5
mkdir -p ${mysqlbasedir}
mkdir -p ${mysqldatadir}
groupadd mysql
useradd -g mysql mysql
chown mysql.mysql ${mysqldatadir}

##下载mysql编译包
echo "下载mysql编译包--------------------------------------------"
##wget http://dev.mysql.com/get/Downloads/MySQL-5.7/mysql-5.7.36-linux-glibc2.12-x86_64.tar.gz --no-check-certificate
if [ -e mysql-5.7.36-linux-glibc2.12-x86_64.tar.gz ]; then
    echo "File mysql-5.7.36-linux-glibc2.12-x86_64.tar.gz exists."
    echo "mysql包已存在。。。"
    sleep 5
else
    echo "File mysql-5.7.36-linux-glibc2.12-x86_64.tar.gz does not exist."
    echo "准备下载mysql编译包。。。"
    wget http://dev.mysql.com/get/Downloads/MySQL-5.7/mysql-5.7.36-linux-glibc2.12-x86_64.tar.gz --no-check-certificate
    sleep 5
fi

if [ -e mysql-5.7.36-linux-glibc2.12-x86_64.tar.gz ]; then
    echo "File mysql-5.7.36-linux-glibc2.12-x86_64.tar.gz exists."
    echo "mysql包已下载。。。"
    sleep 5
else
    echo "File mysql-5.7.36-linux-glibc2.12-x86_64.tar.gz does not exist."
    echo "脚本退出"
    exit 1
fi

##开始编译安装
tar -zxvf mysql-5.7.36-linux-glibc2.12-x86_64.tar.gz -C ${mysqlbasedir}
sleep 15
cd ${mysqlbasedir}
cd mysql-5.7.36-linux-glibc2.12-x86_64/
mv * ${mysqlbasedir}/
cd ${mysqlbasedir}
rm -rf mysql-5.7.36-linux-glibc2.12-x86_64/
cd ${mysqlbasedir}/support-files

##写入my.cnf默认配置文件
echo "配置my.cnf默认配置文件--------------------------------------------"
cat > my_default.conf <<EOF
[mysqld]
character-set-server=utf8
basedir =${mysqlbasedir}
datadir=${mysqldatadir}
log-error=${mysqlbasedir}/mysqld.log
port = 3306
socket=/tmp/mysql.sock
pid-file=/tmp/mysqld.pid
#skip-grant-tables = 1

default-storage-engine=INNODB
character_set_server=utf8
lower_case_table_names=1    #不区分大小写

##以下配置对应分配4G内存设置
innodb_buffer_pool_size=4096M
innodb_buffer_pool_instances=4
innodb_log_file_size=1024M
tmp_table_size=16M
max_heap_table_size=16M
key_buffer_size=192K

symbolic-links=0
query_cache_size=16M
thread_cache_size=8
table_open_cache=128
max_connections=600
innodb_file_per_table=1
bind-address=0.0.0.0    #允许远程访问此数据库
 
sql_mode=STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_AUTO_CREATE_USER,NO_ENGINE_SUBSTITUTION
 
server-id=${id} #本机序列号，1代表Master
log-bin=mysql-bin   #打开二进制日志
binlog-do-db=jumpserver
replicate-do-db=jumpserver  #需要复制的数据库
binlog-ignore-db=mysql
binlog-ignore-db=information_schema
binlog-ignore-db=performance_schema
binlog-ignore-db=sys
expire_logs_days=30 # 自动清理 3 天前的log文件 可根据需要修改

log-slave-updates
slave-skip-errors=all
sync_binlog=1
auto_increment_increment=2
auto_increment_offset=${offset} #与主库保持不同，可与server-id保持一致
skip-name-resolve   #禁止MySQL对外部连接进行DNS解析，使用这一选项可以消除MySQL进行DNS解析的时间。
 
[mysql]
default-character-set=utf8
 
[mysql.server]
default-character-set=utf8
EOF

##开始编译mysql，进行安装
echo "开始编译mysql--------------------------------------------"
touch ${mysqlbasedir}/mysqld.log
chown mysql.mysql ${mysqlbasedir}/mysqld.log
cd ${mysqlbasedir}
bin/mysqld --initialize --user=mysql --basedir=${mysqlbasedir}/ --datadir=${mysqldatadir}/ >> /tmp/mysql-install.log 2>&1
sleep 10
cp ${mysqlbasedir}/support-files/my_default.conf /etc/my.cnf
cp ${mysqlbasedir}/support-files/mysql.server /etc/init.d/mysql
chmod 755 /etc/init.d/mysql 
chkconfig --add mysql
chkconfig --list mysql
cd ${mysqlbasedir}
bin/mysqld_safe --user=mysql &
sleep 3
bin/mysql_ssl_rsa_setup --datadir ${mysqldatadir}
sleep 3
##echo "export PATH=/usr/local/mysql/bin:$PATH" >>/etc/profile
cat >> /etc/profile <<"EOF"
export PATH=/usr/local/mysql/bin:$PATH
EOF


sed -i "s,/usr/local/mysql,${mysqlbasedir},g" /etc/profile
source /etc/profile
sleep 3
/etc/init.d/mysql restart

#放行firewall端口
#firewall-cmd --permanent --zone=public --add-port=3306/tcp
#firewall-cmd --reload

/etc/init.d/mysql stop
##配置systemd管理mysqld服务
echo "配置systemd管理mysqld服务-------------------------------------"
cat > /etc/systemd/system/mysqld.service <<EOF
[Unit]
Description=MySQL Server
Documentation=man:mysqld(8)
Documentation=http://dev.mysql.com/doc/refman/en/using-systemd.html
After=network.target
After=syslog.target

[Install]
WantedBy=multi-user.target

[Service]
User=mysql
Group=mysql
Type=forking
PIDFile=/tmp/mysqld.pid
TimeoutSec=0

# Execute pre and post scripts as root
PermissionsStartOnly=true

# Start main service
ExecStart=/etc/init.d/mysql start

# Stop main service
ExecStop=/etc/init.d/mysql stop

# Sets open_files_limit
@LimitNOFILE = 5000

Restart=on-failure
RestartPreventExitStatus=1
PrivateTmp=false
EOF

systemctl daemon-reload 
systemctl stop mysqld 
systemctl start mysqld
systemctl enable mysqld

##开始配置mysql基础账号
echo "开始配置mysql基础账号--------------------------------------------"
##取安装日志中的随机密码
mysql_pass=`cat /tmp/mysql-install.log |grep password |awk '{print $NF}'`
/usr/local/mysql/bin/mysql -uroot -p"${mysql_pass}" --connect-expired-password -e "alter user 'root'@'localhost' identified by 'jumpserver';"
/usr/local/mysql/bin/mysql -uroot -p"jumpserver" --connect-expired-password -e "update mysql.user set host ='%' where user='root' and host='localhost';"
/usr/local/mysql/bin/mysql -uroot -p"jumpserver" --connect-expired-password -e "grant all privileges on *.* to root@'%' identified by 'jumpserver';"
/usr/local/mysql/bin/mysql -uroot -p"jumpserver" --connect-expired-password -e "flush privileges;" 

echo "开始配置mysql数据库--------------------------------------------"
/usr/local/mysql/bin/mysql -uroot -p"jumpserver" --connect-expired-password -e "create database jumpserver default character set utf8 collate utf8_bin;"
/usr/local/mysql/bin/mysql -uroot -p"jumpserver" --connect-expired-password -e "show create database jumpserver;"

##开始配置mysql主从相关配置
echo "开始配置mysql主从相关配置--------------------------------------------"
/usr/local/mysql/bin/mysql -uroot -p"jumpserver" --connect-expired-password -e "show master status\G"

echo "后续配置主从可参考："
echo "/usr/local/mysql/bin/mysql -uroot -p\"jumpserver\" --connect-expired-password -e \"change master to master_host='192.168.1.183',\""
echo "/usr/local/mysql/bin/mysql -uroot -p\"jumpserver\" --connect-expired-password -e \"master_user='root',\"" 
echo "/usr/local/mysql/bin/mysql -uroot -p\"jumpserver\" --connect-expired-password -e \"master_password='jumpserver',\"" 
echo "/usr/local/mysql/bin/mysql -uroot -p\"jumpserver\" --connect-expired-password -e \"master_log_file='mysql-bin.000004',\"" 
echo "/usr/local/mysql/bin/mysql -uroot -p\"jumpserver\" --connect-expired-password -e \"master_log_pos=106;\""
echo "/usr/local/mysql/bin/mysql -uroot -p\"jumpserver\" --connect-expired-password -e \"start slave;\""
echo "/usr/local/mysql/bin/mysql -uroot -p\"jumpserver\" --connect-expired-password -e \"show slave status \G\""
ln -s /usr/local/mysql/bin/mysql /usr/local/bin/mysql

echo "安装脚本执行成功----------------------------------------"
exit 0


##mysql编译安装后，卸载相关告示
##1.来到mysql源路径，执行命令 ./uninstall.sh
##2.删除mysql安装路径
##3.删除mysql数据路径，以及配置文件my.cnf相关
##4.删除mysql用户和组