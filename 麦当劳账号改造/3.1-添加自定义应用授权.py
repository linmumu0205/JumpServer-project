#   为用户创建多类型资产授权
import json
import warnings
import requests
import datetime
from datetime import timedelta

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

def get_assets_list(config):
    url = f"{config.jms_url}/assets/assets/"
    resp = requests.get(url, headers=make_headers(config), verify=False)
    assets_list = resp.json()
    windows_assets = [asset for asset in assets_list if asset.get('platform', {}).get('name') == 'Windows']
    original_assets = [asset for asset in assets_list if asset.get('platform', {}).get('name') == 'OriginalAppPro']
    all_assets = windows_assets + original_assets
    for asset in all_assets:
        print(f"资产名称: {asset['name']}, 资产ID: {asset['id']}, 系统平台: {asset.get('platform', {}).get('name')}")
    return all_assets

def get_user_list(config):
    url = f"{config.jms_url}/users/users"
    try:
        resp = requests.get(url, headers=make_headers(config), verify=False)
        resp.raise_for_status()
        users = resp.json()
        if users:
            user_info = [{'uuid': user['id'], 'username': user['name']} for user in users]
            return user_info
        else:
            return None
    except requests.exceptions.RequestException as e:
        print(f"请求用户列表时发生错误: {e}")
        return None

def get_asset_permissions(config):
    url = f"{config.jms_url}/perms/asset-permissions/"
    try:
        resp = requests.get(url, headers=make_headers(config), verify=False)
        resp.raise_for_status()
        permissions = resp.json()
        if permissions:
            permission_info = []
            for permission in permissions:
                info = {
                    'uuid': permission['id'],
                    'name': permission['name'],
                    'user': permission['users'],
                    'asset': permission['assets'],
                    'accounts': permission['accounts']
                }
                permission_info.append(info)
            return permission_info
        else:
            return None
    except requests.exceptions.RequestException as e:
        print(f"请求资产授权时发生错误: {e}")
        return None

def create_asset_permissions(config, users_info, assets_info):
    url = f"{config.jms_url}/perms/asset-permissions/"
    print(f"请求url:{url}")
    default_actions = ["connect", "upload", "download", "copy", "paste", "delete"]

    for user_info in users_info:
        name = user_info['username']
        user_id = user_info['uuid']
        assets = [asset['id'] for asset in assets_info]
        accounts = ['js_' + name]

        date_start = datetime.datetime.now()
        date_expired = datetime.datetime.now() + timedelta(days=365 * 100)
        data = {
            'name': name, 'assets': assets, 'nodes': [], 'accounts': accounts,
            'actions': default_actions, 'is_active': True, 'users': [user_id],
            'date_start': str(date_start), 'date_expired': str(date_expired)
        }

        print("为用户创建授权，请求体：", data)
        try:
            resp = requests.post(url, headers=make_headers(config), json=data, verify=False)
            resp.raise_for_status()
            print(f"为用户 {name} 创建授权成功")
        except requests.exceptions.RequestException as e:
            print(f"为用户 {name} 创建授权时发生错误: {e}")


def main():
    jms_config = JMSConfig(
        jms_url='http://10.1.12.27/api/v1',
        token='b525e8305efddeaa807b33e3c58c148889247273',
        jms_org='00000000-0000-0000-0000-000000000002'
    )
    permissions = get_asset_permissions(jms_config)
    users = get_user_list(jms_config)
    assets = get_assets_list(jms_config)
    if permissions and users:
        print(f"该组织授权共计 {len(permissions)} 条。该组织用户共计{len(users)} 个。")
    else:
        print(f"无法获取资产或用户信息")
    if assets and users:
        create_asset_permissions(jms_config, users, assets)
    else:
        print("无法获取资产或用户信息")

if __name__ == '__main__':
    main()
