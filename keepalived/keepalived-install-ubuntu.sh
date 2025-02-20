#!/bin/bash
##脚本已完成，测试正常。。。。
##脚本已验证os系统：ubuntu22.04

read -p "请输入主备类型(MASTER/BACKUP): " state
if [ "$state" = "MASTER" ] || [ "$state" = "BACKUP" ]; then
    echo "取值成功，继续执行脚本。。。"
else
    echo "您输入的字符串不符合，退出脚本。。。"
    exit 1
fi

read -p "请输入网卡名： " interface
read -p "请输入route-id: " virtual_router_id
read -p "请输入权重优先级： " priority_value
read -p "请输入虚ip: " vip
read -p "请输入对端ip: " ip_address

sudo apt update
sudo apt install -y gcc make libssl-dev libpopt-dev libnl-3-dev libnl-route-3-dev libnfnetlink-dev pkg-config
sudo apt-get install libnl-genl-3-dev -y
sleep 5
#sudo apt install wget -y
##wget http://www.keepalived.org/software/keepalived-2.2.7.tar.gz --no-check-certificate
if [ -e keepalived-2.2.7.tar.gz ]; then
    echo "File keepalived-2.2.7.tar.gz exists."
    echo "keepalived包已下载。。。"
    sleep 5
else
    echo "File keepalived-2.2.7.tar.gz does not exist."
    echo "准备下载keepalived编译包。。。"
    wget http://www.keepalived.org/software/keepalived-2.2.7.tar.gz --no-check-certificate
    sleep 5
fi

if [ -e keepalived-2.2.7.tar.gz ]; then
    echo "File keepalived-2.2.7.tar.gz exists."
    echo "keepalived包已下载。。。"
    sleep 5
else
    echo "File keepalived-2.2.7.tar.gz does not exist."
    echo "脚本退出"
    exit 1
fi

tar -zxvf keepalived-2.2.7.tar.gz -C /root/
sleep 5
cd /root/keepalived-2.2.7
./configure --prefix=/usr/local/keepalived
sleep 10
make
sleep 15 
make install
sleep 15
#将keepalived配置成系统服务
#cp /usr/local/keepalived/etc/rc.d/init.d/keepalived /etc/init.d/（暂无）
#cp /usr/local/keepalived/etc/sysconfig/keepalived /etc/sysconfig/ 
mkdir -p /etc/keepalived/
cp /usr/local/keepalived/etc/keepalived/keepalived.conf.sample /etc/keepalived/keepalived.conf
cp /usr/local/keepalived/sbin/keepalived /usr/sbin/
#无需填写systemctl纳管文件

cat > /etc/keepalived/keepalived.conf <<EOF
! Configuration File for keepalived

global_defs {
   notification_email {
     test@test.com
   }
   notification_email_from admin@test.com
   smtp_server 127.0.0.1
   smtp_connect_timeout 30
   router_id JMS_HA
}

vrrp_script chk_jms {
  script "/etc/keepalived/web-check.sh"
  interval 3
  fall 1
  weight -20
}

vrrp_instance VI_1 {
    state ${state}  #主节点为MASTER，备节点为BACKUP，注意要用大写
    interface ${interface} #注意系统内网卡名配置，修改为对应的名称
    virtual_router_id ${virtual_router_id} #主备节点routerid一致
    priority ${priority_value} #主节点权重100，备节点权重小于100，例如90
    advert_int 1
    authentication {
        auth_type PASS
        auth_pass 1111
    }
    virtual_ipaddress {
        ${vip} #VIP
    }
    track_script {
     chk_jms
    }
}
EOF

echo "keepalived配置文件已完成，接下来是监听脚本。。。"

cat > /etc/keepalived/web-check.sh <<"EOF"
#!/bin/bash

counter=$(netstat -lntp|grep "\btcp\b" |egrep ":80 |:3306 |:6379 "|wc -l)
if [ "${counter}" -le 2 ]; then
   exit 1;
fi
EOF

chmod 755 /etc/keepalived/web-check.sh

##防火墙放开端口
#firewall-cmd --permanent --zone=public --add-protocol=vrrp
#firewall-cmd --reload
sudo ufw allow 112
sudo ufw allow to 224.0.0.18 comment 'VRRP Broadcast'
sudo ufw allow from "$ip_address" comment 'VRRP Router'

sudo ufw enable
sudo ufw status verbose

sudo systemctl daemon-reload
sudo systemctl enable keepalived
sudo systemctl start keepalived

echo "安装脚本执行成功----------------------------------------"
exit 0