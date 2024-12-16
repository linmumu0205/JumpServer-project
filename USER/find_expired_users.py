# -*- coding: utf-8 -*-
# __author: linmy
# date: 2024/12/16

import json
import warnings
from datetime import datetime, timezone
import requests

warnings.filterwarnings("ignore")  # 忽略SSL证书认证


class JMSConfig:
    def __init__(self, jms_url, token, jms_org):
        self.jms_url = jms_url
        self.token = token
        self.jms_org = jms_org


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
    # 获取当前时间，并设置为 offset-aware（带时区信息），默认使用 UTC+0
    today = datetime.now(timezone.utc)

    for user in user_list:
        date_expired_str = user.get('date_expired')
        if date_expired_str:
            try:
                # 使用 strptime 解析带时区的日期格式
                date_expired = datetime.strptime(date_expired_str, "%Y/%m/%d %H:%M:%S %z")
                # 计算剩余天数
                days_to_expire = (date_expired - today).days

                if 0 <= days_to_expire <= days:
                    user['days_to_expire'] = days_to_expire  # 添加剩余天数信息
                    soon_expiring_users.append(user)
            except ValueError:
                print(f"用户 {user['username']} 的过期时间格式不正确: {date_expired_str}")
        else:
            print(f"用户 {user['username']} 未提供过期时间。")

    return soon_expiring_users


def print_soon_expiring_users(users):
    """
    打印即将过期的用户信息
    """
    if users:
        print("\n以下用户的过期时间在7天内：\n")
        for user in users:
            print(
                f"用户名: {user['username']}, 邮箱: {user['email']}, "
                f"剩余天数: {user['days_to_expire']} 天, 过期时间: {user['date_expired']}"
            )
    else:
        print("没有用户的过期时间在7天内。")


def main():
    # 初始化JMS配置
    jms_config = JMSConfig(
        jms_url='http://10.1.12.27/api/v1',
        token='b525e8305efddeaa807b33e3c58c148889247273',
        jms_org='00000000-0000-0000-0000-000000000002'
    )

    # 获取所有用户信息
    users = get_user_list(jms_config)
    if not users:
        print("未获取到用户信息，程序退出。")
        return

    # 筛选即将过期的用户
    soon_expiring_users = filter_users_by_expiry(users, days=7)

    # 打印结果
    print_soon_expiring_users(soon_expiring_users)


if __name__ == '__main__':
    main()
