import json
import warnings
import requests
import pandas as pd  # 用于读取 Excel
import os

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
        #print("请求体数据:", json.dumps(data, indent=2, ensure_ascii=False))

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

def process_excel_and_create_acls(config, excel_filename="user-acls.xlsx"):
    """从 Excel 文件读取数据并批量创建 ACL 规则"""
    # 检查文件是否存在于当前目录
    excel_path = os.path.join(os.getcwd(), excel_filename)
    if not os.path.isfile(excel_path):
        print(f"文件 '{excel_filename}' 不存在于当前目录，请确认文件路径。")
        return

    try:
        # 读取 Excel 文件
        df = pd.read_excel(excel_path)

        # 遍历每一行数据
        for index, row in df.iterrows():
            acl_name = row['acl名称']
            usernames = row['用户名'].split(',')
            ip_group = row['ip列表'].split(',')

            # 去除多余空格
            usernames = [username.strip() for username in usernames]
            ip_group = [ip.strip() for ip in ip_group]

            # 调用创建 ACL 函数
            print(f"\n正在创建 ACL 规则：{acl_name}")
            create_login_acl(config, acl_name, usernames, ip_group)
            print(f"用户登录规则 '{acl_name}' 创建完成。\n")

    except Exception as e:
        print(f"处理 Excel 文件时发生错误: {e}")

def main():
    # 初始化 JMS 配置
    jms_config = JMSConfig(
        jms_url='http://10.1.12.27/api/v1',
        token='b525e8305efddeaa807b33e3c58c148889247273',
        jms_org='00000000-0000-0000-0000-000000000002'
    )

    # 从当前目录读取名为 'acl_rules.xlsx' 的 Excel 文件
    process_excel_and_create_acls(jms_config, excel_filename="user-acls.xlsx")

if __name__ == '__main__':
    main()
