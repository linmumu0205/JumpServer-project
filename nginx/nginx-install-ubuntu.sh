#!/bin/bash
##脚本已完成，测试正常。。。。
##脚本已验证os系统：ubuntu22.04、
##依赖包变动：libpcre3-dev、zlib1g-dev、libssl-dev、libperl-dev

##读取后端server1和server2实际地址
##读取第一个地址
read -p "请输入server1地址： " server1

##读取第二个地址
echo "是否有第二个server? (Y/N):"
read choice
if [ "$choice" = "Y" ] || [ "$choice" = "y" ]; then
    echo "You chose to continue."
    read -p "请输入server2地址： " server2
else
    echo "不存在server2"
fi

echo "下载nginx编译包--------------------------------------------"
mkdir -p /opt/src
cd /opt/src
apt install wget -y
wget http://nginx.org/download/nginx-1.23.3.tar.gz --no-check-certificate
if [ -e nginx-1.23.3.tar.gz ]; then
    echo "File nginx-1.23.3.tar.gz exists."
    echo "nginx包已下载。。。"
    sleep 5
else
    echo "File nginx-1.23.3.tar.gz does not exist."
    echo "脚本退出"
    exit 1
fi

tar -zxvf nginx-1.23.3.tar.gz
sleep 3
 
##下载健康检查插件
echo "下载nginx健康检查插件--------------------------------------------"
cd /opt/src
apt install unzip -y
wget https://codeload.github.com/yaoweibin/nginx_upstream_check_module/zip/master --no-check-certificate
if [ -e master ]; then
    echo "File master exists."
    echo "nginx健康检查包已下载。。。"
    sleep 5
else
    echo "File master does not exist."
    echo "脚本退出"
    exit 1
fi

unzip master
sleep 3
 
##安装健康检查插件
echo "安装nginx健康检查插件--------------------------------------------"
apt install patch -y
sleep 3
cd /opt/src/nginx-1.23.3
patch -p1 < /opt/src/nginx_upstream_check_module-master/check_1.20.1+.patch
 
##编译nginx
echo "开始进行nginx编译安装--------------------------------------------"
apt -y install gcc libpcre3-dev zlib1g-dev openssl libssl-dev libperl-dev
##编译需要安装的模块：--with-stream --with-stream_ssl_module  ///nginx转发TCP连接模块
##                    --with-http_realip_module  允许我们改变客户端请求头中客户端IP地址值
##                    --with-http_ssl_module             使nginx支持https访问
##                    --with-http_v2_module                    //启用http2 
 
useradd nginx
./configure --prefix=/usr/local/nginx --with-http_perl_module --with-http_stub_status_module --with-http_realip_module --with-http_ssl_module --with-stream --with-stream_ssl_module --with-http_v2_module --add-module=/opt/src/nginx_upstream_check_module-master
sleep 15
make
sleep 15
make install
sleep 5
ln -s /usr/local/nginx/sbin/nginx /usr/local/sbin/ ##系统命令补全
 
##开放防火墙
echo "开始配置防火墙策略--------------------------------------------"
firewall-cmd --permanent --zone=public --add-port=80/tcp
firewall-cmd --permanent --zone=public --add-port=443/tcp
firewall-cmd --reload
 
#nginx -s reload ##重载配置
#nginx -t ##测试配置
 
 
##配置systemctl管理
echo "开始配置systemd管理nginx服务--------------------------------------------"
cat > /lib/systemd/system/nginx.service <<"EOF"
[Unit]
Description=nginx
After=network.target
[Service]
Type=forking
PIDFile=/usr/local/nginx/logs/nginx.pid
ExecStart=/usr/local/nginx/sbin/nginx
ExecrReload=/bin/kill -s HUP $MAINPID
ExecrStop=/bin/kill -s QUIT $MAINPID
PrivateTmp=true
[Install]
WantedBy=multi-user.target
EOF
  
chmod 754 /lib/systemd/system/nginx.service     #赋权，除了root以外的用户都不能修改
systemctl enable nginx

##配置jms额外配置
echo "开始配置nginx.conf文件--------------------------------------------"
mv /usr/local/nginx/conf/nginx.conf /usr/local/nginx/conf/nginx-123.conf
cat > /usr/local/nginx/conf/nginx.conf <<"EOF"
user  nginx;
worker_processes  auto;
 
error_log  /usr/local/nginx/logs/error.log notice;
pid        /usr/local/nginx/logs/nginx.pid;
 
 
events {
    worker_connections  1024;
}
 
stream {
    log_format  proxy  '$remote_addr [$time_local] '
                       '$protocol $status $bytes_sent $bytes_received '
                       '$session_time "$upstream_addr" '
                       '"$upstream_bytes_sent" "$upstream_bytes_received" "$upstream_connect_time"';
 
    access_log /usr/local/nginx/logs/access.log  proxy;
 
    open_log_file_cache off;
 
    include /usr/local/nginx/conf/stream.d/*.conf;
}
 
http {
    include       /usr/local/nginx/conf/mime.types;
    default_type  application/octet-stream;
 
    log_format  main  '$remote_addr - $remote_user [$time_local] "$request" '
                      '$status $body_bytes_sent "$http_referer" '
                      '"$http_user_agent" "$http_x_forwarded_for"'
 
                      '"$upstream_addr"'
 
                      '"$upstream_bytes_sent" "$upstream_bytes_received" "$upstream_connect_time"'
 
    access_log  /usr/local/nginx/logs/access.log  main;
     
    proxy_headers_hash_max_size 51200;
    proxy_headers_hash_bucket_size 6400;
     
    sendfile        on;
    #tcp_nopush     on;
 
    keepalive_timeout  65;
 
    #gzip  on;
 
    include /usr/local/nginx/conf/conf.d/*.conf;
}
EOF

echo "开始配置/conf.d/lb_http_server.conf文件----------------------------"
mkdir -p /usr/local/nginx/conf/conf.d
cat > /usr/local/nginx/conf/conf.d/lb_http_server.conf <<"EOF"
upstream http_server {
  ip_hash;
  server 10.1.12.182:80;
  server 10.1.14.25:80;
  #以10s为一个周期，每隔10snginx会自动向上游服务器发送一次请求，如果超过5s超时且达到3次，则该服务器标记为不可用；
  #如果请求次数有一次以上没有超时，这标记为可用  
  check interval=10000 rise=1 fall=3 timeout=5000 type=http;
  check_http_send "GET / HTTP/1.0\r\n\r\n";
  check_http_expect_alive http_2xx http_3xx;
}
 
server {
  listen 80;
  server_name 10.1.12.116;
#  return 301 https://$server_name$request_uri;
#  return 301 https://$host$request_uri;
#
  client_max_body_size 5000m;
    
   location / {
    proxy_pass http://http_server;
    proxy_buffering off;
    proxy_request_buffering off;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection $http_connection;
    proxy_set_header X-Forwarded-For $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;  # 如果上层还有其他 slb 需要使用 $proxy_add_x_forwarded_for 获取真实 ip
 
    proxy_ignore_client_abort on;
    proxy_connect_timeout 600;
    proxy_send_timeout 600;
    proxy_read_timeout 600;
    send_timeout 6000;
  }
 
}
 
server {
  listen 443 ssl http2;
  server_name 10.1.12.116;
  server_tokens off;
  ssl_certificate cert/server.crt;      # 修改 server.crt 为你的证书 (pem, crt 格式均可), 不要改路径 certs/
  ssl_certificate_key cert/server.key;  # 修改 server.crt 为你的证书密钥文件, 不要改路径 certs/
  ssl_session_timeout 1d;
  ssl_session_cache shared:MozSSL:10m;
  ssl_session_tickets off;
  ssl_protocols TLSv1.1 TLSv1.2;
  ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE:ECDH:AES:HIGH:!NULL:!aNULL:!MD5:!ADH:!RC4:!DH:!DHE:!DES:!ECDHE-RSA-DES-CBC3-SHA;
  add_header Strict-Transport-Security "max-age=31536000" always;
  ssl_prefer_server_ciphers off;
 
  client_max_body_size 5000m;
 
location / {
   proxy_pass http://http_server;
   proxy_buffering off;
   proxy_request_buffering off;
   proxy_http_version 1.1;
   proxy_set_header Host $host;
   proxy_set_header Upgrade $http_upgrade;
   proxy_set_header Connection $http_connection;
   proxy_set_header X-Forwarded-For $remote_addr;
   proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;  # 如果上层还有其他 slb 需要使用 $proxy_add_x_forwarded_for 获取真实 ip
 
   proxy_ignore_client_abort on;
   proxy_connect_timeout 600;
   proxy_send_timeout 600;
   proxy_read_timeout 600;
   send_timeout 6000;
 }
}
EOF

##通过sed命令，修改server1和server2
if [ -v server2 ]; then
    echo "server2 is defined..........."
    sed -i  "s/10.1.12.182/${server1}/g" /usr/local/nginx/conf/conf.d/lb_http_server.conf
    sed -i  "s/10.1.14.25/${server2}/g" /usr/local/nginx/conf/conf.d/lb_http_server.conf
else
    echo "server2 is not defined.........."
    sed -i  "s/10.1.12.182/${server1}/g" /usr/local/nginx/conf/conf.d/lb_http_server.conf
    sed -i '/10.1.14.25/d' /usr/local/nginx/conf/conf.d/lb_http_server.conf
fi

echo "开始配置/stream.d/jms.conf文件-------------------------------------"
mkdir -p /usr/local/nginx/conf/stream.d
cat > /usr/local/nginx/conf/stream.d/jms.conf <<"EOF"
upstream ssh_server {
    server 10.1.12.182:2222;
    server 10.1.14.25:2222;
}
 
server {
    listen 2222;
    proxy_pass  ssh_server;
    proxy_protocol on;
    ##set_real_ip_from 192.168.250.0/24;
    proxy_connect_timeout 30s;
}
 
upstream rdp_server {
    server 10.1.12.182:3389;
    server 10.1.14.25:3389;
}
 
server {
    listen 3389;
    proxy_pass rdp_server;
    proxy_connect_timeout 30s;
}
 
 
upstream mysql_server {
    server 10.1.12.182:33060;
    server 10.1.14.25:33060;
}
 
server {
    listen 33060;
    proxy_pass mysql_server;
    proxy_connect_timeout 30s;
}
 
upstream mariadb_server {
    server 10.1.12.182:33061;
    server 10.1.14.25:33061;
}
 
server {
    listen 33061;
    proxy_pass mariadb_server;
    proxy_connect_timeout 30s;
}
 
upstream redis_server {
    server 10.1.12.182:63790;
    server 10.1.14.25:63790;
}
 
server {
    listen 63790;
    proxy_pass redis_server;
    proxy_connect_timeout 30s;
}
 
upstream pg_server {
    server 10.1.12.182:54320;
    server 10.1.14.25:54320;
}
 
server {
    listen 54320;
    proxy_pass pg_server;
    proxy_connect_timeout 30s;
}
EOF

##通过sed命令，修改server1和server2
if [ -v server2 ]; then
    echo "server2 is defined..........."
    sed -i  "s/10.1.12.182/${server1}/g" /usr/local/nginx/conf/stream.d/jms.conf
    sed -i  "s/10.1.14.25/${server2}/g" /usr/local/nginx/conf/stream.d/jms.conf
else
    echo "server2 is not defined.........."
    sed -i  "s/10.1.12.182/${server1}/g" /usr/local/nginx/conf/stream.d/jms.conf
    sed -i '/10.1.14.25/d' /usr/local/nginx/conf/stream.d/jms.conf
fi

echo "开始配置ssl证书相关文件-------------------------------------"
mkdir -p /usr/local/nginx/conf/cert
cat > /usr/local/nginx/conf/cert/server.crt <<EOF
-----BEGIN CERTIFICATE-----
MIIDtDCCApwCCQC70xxmpUL+9zANBgkqhkiG9w0BAQUFADCBmzELMAkGA1UEBhMC
Q04xEDAOBgNVBAgMB0JlaWppbmcxEDAOBgNVBAcMB0JlaWppbmcxFDASBgNVBAoM
C0R1aVpoYW4uSW5jMQ0wCwYDVQQLDARUZWNoMRwwGgYDVQQDDBN0ZXN0Lmp1bXBz
ZXJ2ZXIub3JnMSUwIwYJKoZIhvcNAQkBFhZzdXBwb3J0QGp1bXBzZXJ2ZXIub3Jn
MB4XDTE5MDExNzA5MjYwNFoXDTI5MDExNDA5MjYwNFowgZsxCzAJBgNVBAYTAkNO
MRAwDgYDVQQIDAdCZWlqaW5nMRAwDgYDVQQHDAdCZWlqaW5nMRQwEgYDVQQKDAtE
dWlaaGFuLkluYzENMAsGA1UECwwEVGVjaDEcMBoGA1UEAwwTdGVzdC5qdW1wc2Vy
dmVyLm9yZzElMCMGCSqGSIb3DQEJARYWc3VwcG9ydEBqdW1wc2VydmVyLm9yZzCC
ASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBAKOEMGaqwjlNTTDtJkQpQH/5
0QbvXWr+Q82ihPnFV685uQsj6vLFjD4gksdehENbMnPjpVDZCvzfhBOqahLZsvM6
7ea0S1RFtX0t7rwErn3DOs5MYxU1bVyss1Ahf+bvOWgwaQpxkOmynOe4wxEqC2OJ
mQEzhb9sPo+tF52yMKtoQdkLVzf1Ci9HkVfwwAytejktnYwhzKR65GYHjMb9j7+p
z2dp3n6QKz0R9mnkEj6d6zRaFWT4sE5TMJt4DmHSwSP43c58rAbL8wyqWV9lifRr
RevHzGgFE3ep1Y53fm4jVCK5jY17CtV8g9iP8b0ttL2qr9jvNec37kGONpYjkl8C
AwEAATANBgkqhkiG9w0BAQUFAAOCAQEAdsI48hcuVz65dK1JYaoezM/PmVTD17Nx
l9QeRWANALro/nV8UOtMFGVBPFFzji+BsLKol6o8BCdpw72nfRNIPsNFFCrCgbft
2eNNc0hFHqbfwjT6E03JLb42BU5is+x2U8/Krg90Yt5XF0LoHm9lr24Kb31/wBKx
Ilb7mpC/TPd4p2V+QG46t6Ji4Q+DufihupgobG3PgcaOtPzT51HAlrL7R8OmDciB
o3h1ALD6CsvSK38SkFo6yc3lckjlfg/q0LZLeSEAAKerzL2j/DPw3hTUwMhFmTt5
PWL26PfEUlv6wwUi/9Soa7B9QM0XEa9ib5PAWbIRCG4VxOG8fl57UA==
-----END CERTIFICATE-----
EOF

cat > /usr/local/nginx/conf/cert/server.key <<EOF
-----BEGIN RSA PRIVATE KEY-----
MIIEowIBAAKCAQEAo4QwZqrCOU1NMO0mRClAf/nRBu9dav5DzaKE+cVXrzm5CyPq
8sWMPiCSx16EQ1syc+OlUNkK/N+EE6pqEtmy8zrt5rRLVEW1fS3uvASufcM6zkxj
FTVtXKyzUCF/5u85aDBpCnGQ6bKc57jDESoLY4mZATOFv2w+j60XnbIwq2hB2QtX
N/UKL0eRV/DADK16OS2djCHMpHrkZgeMxv2Pv6nPZ2nefpArPRH2aeQSPp3rNFoV
ZPiwTlMwm3gOYdLBI/jdznysBsvzDKpZX2WJ9GtF68fMaAUTd6nVjnd+biNUIrmN
jXsK1XyD2I/xvS20vaqv2O815zfuQY42liOSXwIDAQABAoIBAHmpj0G0Z9Ku23I9
4Szx7JXL0GTykHVdPiGwfHRDCtzLfAz36oY7yf8nyU4h2xMqtb1YcdZXxz8jJ2hi
cY4ZAHbNL9lp6GqJe2HqXSjz6siUDBsW5toO6JH9xWUnp7yx3erRqjYlDYd0aB5Z
cHpC6DplVLx6E1e8OEg6p8mjnWbKeUAYAjw5ib3Cpn/VIY+ehuuDIwpfEKLct1yc
dWTJUqOhKOHxEPMdfmgaqqFi5XsDwC+aK4kXOvmLOYYvwH9DummcRckY7WOVF4yS
vKThEs60xOYViAtKLan47XhDqBaUcLWfK09OC9X87OXlUFh9nxdrZ6cwLcmYOL2Q
ZDYqf7ECgYEA0HvB6S87I5p2eaFLRS3ZYcHo75ooGAoUSDSkf2UBqznVWQrhQgUY
TOFf+/RQnDGY/tLbd338nhuOae2qtaY5iaFnbFVe0H4gDoIqM6tYCcJ0SXSvWTFk
E5Jso0O/yPGudztc2LBYpN6TTKbmANFBbq/zsDWFigFYXYjmDw/voFsCgYEAyMjE
vWb29VEELyWaBGUs3ryezvMA/Leli7uD3VwcVzLUIlhoTFESjooZeQlIHoYDuFX5
aHjF2U4sLJ2lft+3nbBVfdW7s4FZtsX7QM5IfcVVj8PTvM2uMWxOxA6L/DPIin01
PiCnEe7Xz/7ypEXS7cu4SNHwZu9toNcEUFsQtU0CgYBmtCDBm+fZUTV+E6w95ylI
lDsJFfscZJK7Q1up+ntI+5OTat2vJU1kSj57o062s2Q4XG2LPwBcbxzIKDHJjJqZ
p26ImsG7mfZ2zz6093rGTAn3Sck7+i3fymlEQJLRDeYxjIffo3f3uEH+J9X0nyFJ
wtocezFO2/zJDzCuSN52MwKBgQCRCAysrzJV0xaNo8CTyi1WGrMv03H0Ggd3XpSK
kd1a0zlOMcPs1GbuFSz/M8gnXDBVt6x3XT20kPXxqFIBykGMovGt+nQh3p5aGro5
fof4aVE7jn1klMFtq8ldbxCItTL3bifGX7muh3LWKFdGd7U71XqhBxx6jhoHIylX
jeAMxQKBgAYSePmWULgXazuqTM0VeyiVOYlBmoD5WOZPBmX3KBs3FQmaVJmCdJBx
m8eudLlU2FSjPqEYOFqkH+bIMh6GsIAy09FlCyC9GhkiU8cMETa3S1MQsXAf9JP7
5+/8/MoppyBaDEjbYNp3kAB0AcsSNgc2tbkquoKeyPG6xWabvhxb
-----END RSA PRIVATE KEY-----
EOF

##测试nginx语法并启动。
nginx -t

systemctl start nginx

echo "安装脚本执行成功----------------------------------------"
exit 0
