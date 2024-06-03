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
    url = f"{config.jms_url}/users/users"
    try:
        resp = requests.get(url, headers=make_headers(config), verify=False)
        resp.raise_for_status()
        users = resp.json()  # 获取用户信息
        if isinstance(users, list) and users:  # 确保 users 是非空列表
            user_info = [
                {
                    'uuid': user['id'],
                    'name': user['name'],
                    'username': user['username'],
                    'source': user['source']['value']
                }
                for user in users
            ]
            print("获取用户列表成功:")
            for user in user_info:
                print(
                    f"用户ID: {user['uuid']}, 用户名: {user['username']}, 姓名: {user['name']}, 来源: {user['source']}")
            return user_info
        else:
            print("用户列表为空")
            return None
    except requests.exceptions.RequestException as e:
        print(f"请求用户列表时发生错误: {e}")
        return None

def delete_users_by_source(config, source):
    url = f"{config.jms_url}/users/users"
    try:
        resp = requests.get(url, headers=make_headers(config), verify=False)
        resp.raise_for_status()
        users = resp.json()
        if isinstance(users, list) and users:
            users_to_delete = [user for user in users if user['source']['value'] == source]
            if not users_to_delete:
                print(f"没有找到来源为 {source} 的用户")
                return

            # 打印即将删除的用户列表
            print(f"即将删除来源为 {source} 的用户:")
            for user in users_to_delete:
                print(f"用户ID: {user['id']}, 用户名: {user['username']}")

            # 批量删除用户
            delete_count = 0
            for user in users_to_delete:
                user_id = user['id']
                username = user['username']
                delete_url = f"{config.jms_url}/users/users/{user_id}"
                delete_resp = requests.delete(delete_url, headers=make_headers(config), verify=False)
                if delete_resp.status_code == 204:
                    print(f"成功删除用户，ID: {user_id}，NAME: {username}")
                    delete_count += 1
                else:
                    print(f"删除用户失败，ID: {user_id}，NAME: {username}")
            # 输出删除用户的总数量
            print(f"成功删除了 {delete_count} 个来源为 {source} 的用户")
        else:
            print("用户列表为空")
    except requests.exceptions.RequestException as e:
        print(f"请求删除用户时发生错误: {e}")

def main():
    jms_config = JMSConfig(
        jms_url='http://10.1.12.27/api/v1',
        token='b525e8305efddeaa807b33e3c58c148889247273',
        jms_org='00000000-0000-0000-0000-000000000002'
    )

    source = input("请输入要删除的用户来源: ")  # 获取用户输入的来源
    get_user_list(jms_config)  # 打印当前用户列表
    delete_users_by_source(jms_config, source)  # 删除指定来源的用户


if __name__ == '__main__':
    main()
