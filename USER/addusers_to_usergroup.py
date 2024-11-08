import json
import warnings
import requests

warnings.filterwarnings("ignore")  # 忽略SSL证书认证

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
    """通过用户名获取对应的UUID列表"""
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

def add_user_to_group_relation(config, group_id, user_uuid):
    """将单个用户添加到指定的用户组中"""
    url = f"{config.jms_url}/users/users-groups-relations/"

    # 构造请求体
    data = {
        "user": user_uuid,
        "usergroup": group_id
    }

    try:
        # 打印请求数据，以确保格式正确
        print("请求体数据:", json.dumps(data, indent=2))

        # 发送 PATCH 请求
        resp = requests.post(url, headers=make_headers(config), json=data, verify=False)
        resp.raise_for_status()  # 如果返回的状态码不是 2xx，会抛出异常

        if resp.status_code in (200, 201):
            print(f"成功将用户 {user_uuid} 添加到用户组 {group_id} 中")
        else:
            print(f"更新用户组失败，响应状态码: {resp.status_code}")
            print("响应内容:", resp.text)
    except requests.exceptions.RequestException as e:
        print(f"请求时发生错误: {e}")

def main():
    # 初始化JMS配置
    jms_config = JMSConfig(
        jms_url='http://10.1.12.27/api/v1',
        token='b525e8305efddeaa807b33e3c58c148889247273',
        jms_org='00000000-0000-0000-0000-000000000002'
    )

    # 输入信息
    group_id = input("请输入用户组ID: ").strip()
    users_input = input("请输入要添加到用户组中的用户名，多个用户名用逗号分隔: ").strip()
    usernames = [user.strip() for user in users_input.split(",") if user.strip()]

    # 获取用户UUID列表
    user_uuids = get_user_uuids_by_usernames(jms_config, usernames)

    # 逐个将用户添加到用户组关系中
    if user_uuids:
        for user_uuid in user_uuids:
            add_user_to_group_relation(jms_config, group_id, user_uuid)
    else:
        print("没有找到有效的用户UUID。")

if __name__ == '__main__':
    main()
