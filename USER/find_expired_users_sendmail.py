# -*- coding: utf-8 -*-
# __author:linmy
# data:2024/12/16

import json
import warnings
from datetime import datetime, timezone
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests

warnings.filterwarnings("ignore")  # 忽略SSL证书认证

class JMSConfig:
    def __init__(self, jms_url, token, jms_org):
        self.jms_url = jms_url
        self.token = token
        self.jms_org = jms_org

class EmailConfig:
    def __init__(self, smtp_server, smtp_port, sender_email, sender_password):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.sender_email = sender_email
        self.sender_password = sender_password

def make_headers(config):
    """
    生成HTTP请求头
    """
    return {
        'Authorization': f'Token {config.token}',
        'Content-Type': 'application/json',
        'X-JMS-ORG': config.jms_org,
    }


def get_user_list(config):
    """
    获取所有用户的信息
    :param config: JMSConfig 对象
    :return: 用户信息列表
    """
    url = f"{config.jms_url}/users/users/"
    try:
        resp = requests.get(url, headers=make_headers(config), verify=False)
        resp.raise_for_status()
        users = resp.json()
        print("所有用户信息已获取，正在筛选即将过期的用户...")
        if users:
            user_info = [
                {
                    'uuid': user['id'],
                    'username': user['username'],
                    'name': user['name'],
                    'email': user.get('email', '未提供'),
                    'date_expired': user.get('date_expired')
                }
                for user in users
            ]
            return user_info
        else:
            print("未获取到任何用户信息。")
            return []
    except requests.exceptions.RequestException as e:
        print(f"请求用户列表时发生错误: {e}")
        return []


def filter_users_by_expiry(user_list, days=7):
    """
    筛选出过期时间在指定天数内的用户
    :param user_list: 用户信息列表
    :param days: 剩余天数阈值，默认为7天
    :return: 符合条件的用户列表
    """
    soon_expiring_users = []
    today = datetime.now(timezone.utc)

    for user in user_list:
        date_expired_str = user.get('date_expired')
        if date_expired_str:
            try:
                date_expired = datetime.strptime(date_expired_str, "%Y/%m/%d %H:%M:%S %z")
                days_to_expire = (date_expired - today).days

                if 0 <= days_to_expire <= days:
                    user['days_to_expire'] = days_to_expire  # 添加剩余天数信息
                    soon_expiring_users.append(user)
            except ValueError:
                print(f"用户 {user['username']} 的过期时间格式不正确: {date_expired_str}")
        else:
            print(f"用户 {user['username']} 未提供过期时间。")

    return soon_expiring_users


def send_email(email_config, recipient_email, subject, body):
    """
    发送邮件
    :param email_config: EmailConfig 配置
    :param recipient_email: 接收方邮箱地址
    :param subject: 邮件主题
    :param body: 邮件正文
    """
    try:
        # 创建邮件内容
        msg = MIMEMultipart()
        msg['From'] = email_config.sender_email
        msg['To'] = recipient_email
        msg['Subject'] = subject

        # 添加邮件正文
        msg.attach(MIMEText(body, 'plain'))

        # 连接SMTP服务器并发送邮件
        with smtplib.SMTP(email_config.smtp_server, email_config.smtp_port) as server:
            server.starttls()
            server.login(email_config.sender_email, email_config.sender_password)
            server.sendmail(email_config.sender_email, recipient_email, msg.as_string())
            print(f"邮件已发送至 {recipient_email}")
    except Exception as e:
        print(f"发送邮件至 {recipient_email} 时发生错误: {e}")


def notify_users(email_config, soon_expiring_users):
    """
    通知即将过期的用户
    :param email_config: EmailConfig 配置
    :param soon_expiring_users: 即将过期的用户列表
    """
    for user in soon_expiring_users:
        if user['email'] == '未提供':
            print(f"用户 {user['username']} 未提供邮箱，无法发送通知。")
            continue

        subject = "JumpServer账户即将过期通知"
        body = (
            f"尊敬的 {user['name']} ({user['username']}),\n\n"
            f"您的JumpServer账户将于 {user['date_expired']} 过期。\n"
            f"距离过期还有 {user['days_to_expire']} 天，请及时更新账户或联系管理员。\n\n"
            f"此邮件为自动发送，请勿回复。\n\n"
            f"祝好！\n系统管理员"
        )
        send_email(email_config, user['email'], subject, body)


def main():
    # 初始化JMS配置
    jms_config = JMSConfig(
        jms_url='http://10.1.12.27/api/v1',
        token='b525e8305efddeaa807b33e3c58c148889247273',
        jms_org='00000000-0000-0000-0000-000000000002'
    )

    # 初始化邮件配置
    email_config = EmailConfig(
        smtp_server='smtp.qq.com',
        smtp_port=25,
        sender_email='xxxxx@qq.com',
        sender_password='rpnxxxzanbxxxxxx'  #smtp授权码或账号密码
    )

    # 获取所有用户信息
    users = get_user_list(jms_config)
    if not users:
        print("未获取到用户信息，程序退出。")
        return

    # 筛选即将过期的用户
    soon_expiring_users = filter_users_by_expiry(users, days=7)

    # 通知即将过期的用户
    if soon_expiring_users:
        notify_users(email_config, soon_expiring_users)
    else:
        print("没有用户的过期时间在7天内。")


if __name__ == '__main__':
    main()
