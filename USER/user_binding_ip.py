import json
import warnings
import requests

warnings.filterwarnings("ignore")  # 忽略 SSL 证书认证

class JMSConfig:
    def __init__(self, jms_url, token, jms_org):
        self.jms_url = jms_url
        self.token = token
        self.jms_org = jms_org

def make_headers(config):
    return {
        'Authorization': f'Token {config.token}',
        'Content-Type': 'application/json',
        'X-JMS-ORG': config.jms_org,
    }

def get_user_list(config):
    """获取所有用户的信息"""
    url = f"{config.jms_url}/users/users"
    try:
        resp = requests.get(url, headers=make_headers(config), verify=False)
        resp.raise_for_status()
        users = resp.json()
        if users:
            user_info = [{'uuid': user['id'], 'username': user['username'], 'name': user['name']} for user in users]
            return user_info
        else:
            return None
    except requests.exceptions.RequestException as e:
        print(f"请求用户列表时发生错误: {e}")
        return None

def get_user_uuids_by_usernames(config, usernames):
    """通过用户名获取对应的 UUID 列表"""
    user_list = get_user_list(config)
    if not user_list:
        print("无法获取用户列表。")
        return []

    user_uuids = []
    for username in usernames:
        matching_users = [user['uuid'] for user in user_list if user['username'] == username]
        if matching_users:
            user_uuids.extend(matching_users)
        else:
            print(f"未找到用户名为 {username} 的用户。")

    return user_uuids

def create_login_acl(config, acl_name, usernames, ip_group):
    """创建登录 ACL 规则"""
    url = f"{config.jms_url}/acls/login-acls/"

    # 获取用户 UUID 列表
    user_uuids = get_user_uuids_by_usernames(config, usernames)

    # 构造请求体
    data = {
        "name": acl_name,
        "priority": 50,  # 默认优先级
        "action": {
            "value": "accept",
            "label": "接受"
        },
        "comment": "",  # 留空备注
        "created_by": "自动脚本",  # 可修改为需要的创建者名称
        "reviewers": [],  # 无 reviewers
        "users": {
            "type": "ids",
            "ids": user_uuids
        },
        "rules": {
            "ip_group": ip_group,  # 用户输入的 IP 列表
            "time_period": [
                {
                    "id": i,
                    "value": "00:00~00:00"
                } for i in range(7)  # 7 天默认通配符时间段
            ]
        },
        "is_active": True  # 激活状态
    }

    try:
        # 打印请求数据，以确保格式正确
        print("请求体数据:", json.dumps(data, indent=2, ensure_ascii=False))

        # 发送 POST 请求
        resp = requests.post(url, headers=make_headers(config), json=data, verify=False)
        resp.raise_for_status()  # 如果返回的状态码不是 2xx，会抛出异常

        if resp.status_code == 201:
            print(f"成功创建 ACL 规则 '{acl_name}'")
        else:
            print(f"创建 ACL 规则失败，响应状态码: {resp.status_code}")
            print("响应内容:", resp.text)
    except requests.exceptions.RequestException as e:
        print(f"请求时发生错误: {e}")

def main():
    # 初始化 JMS 配置
    jms_config = JMSConfig(
        jms_url='http://10.1.12.27/api/v1',
        token='b525e8305efddeaa807b33e3c58c148889247273',
        jms_org='00000000-0000-0000-0000-000000000002'
    )

    # 输入 ACL 规则名称
    acl_name = input("请输入 ACL 规则名称: ").strip()

    # 输入用户名，多个用户名用逗号分隔
    users_input = input("请输入关联的用户名，多个用户名用逗号分隔: ").strip()
    usernames = [user.strip() for user in users_input.split(",") if user.strip()]

    # 输入 IP 列表，多个 IP 用逗号分隔
    ip_group_input = input("请输入 IP 列表，多个 IP 用逗号分隔: ").strip()
    ip_group = [ip.strip() for ip in ip_group_input.split(",") if ip.strip()]

    # 调用创建 ACL 函数
    if usernames and ip_group:
        create_login_acl(jms_config, acl_name, usernames, ip_group)
    else:
        print("用户名和 IP 列表均不能为空。")

if __name__ == '__main__':
    main()
