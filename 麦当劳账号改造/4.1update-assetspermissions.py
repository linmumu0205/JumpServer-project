#   账号存在跳过创建、未存在发送请求
#   授权未存在则创建、授权存在则对比资产更新
import json
import pandas as pd
import warnings
import requests
import os
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

def check_existing_permission(config, name, user_info):
    permissions = get_asset_permissions(config)
    if permissions:
        for permission in permissions:
            if permission['name'] == name and user_info['username'] in permission['name']:
                return True
    return False


def create_asset_permissions(config, users_info, assets_info):
    url = f"{config.jms_url}/perms/asset-permissions/"
    print(f"请求url:{url}")
    default_actions = ["connect", "upload", "download", "copy", "paste", "delete"]
    for user_info in users_info:
        name = user_info['username']
        user_id = user_info['uuid']
        assets = [asset['id'] for asset in assets_info]
        accounts = ['js_' + name]

        if check_existing_permission(config, name, user_info):
            print(f"用户 {name} 的授权已存在，检查是否需要更新...")
            existing_permission = get_existing_permission(config, name, user_info)
            existing_assets = existing_permission.get('assets', [])
            if set(existing_assets) == set(assets):
                print(f"用户 {name} 的授权中资产数量未发生变化，跳过更新")
                continue
            else:
                print(f"用户 {name} 的授权中资产数量发生变化，开始更新授权...")
                update_asset_permissions(config, existing_permission, assets, user_info)
                continue

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

def get_existing_permission(config, name, user_info):
    permissions = get_asset_permissions(config)
    if permissions:
        for permission in permissions:
            if permission['name'] == name and user_info['username'] in permission['name']:
                return permission
    return None

def update_asset_permissions(config, existing_permission, new_assets, user_info):
    permission_id = existing_permission['uuid']
    url = f"{config.jms_url}/perms/asset-permissions/{permission_id}/"
    existing_assets = existing_permission.get('assets', [])
    added_assets = list(set(new_assets) - set(existing_assets))

    name = user_info['username']
    user_id = user_info['uuid']
    accounts = ['js_' + name]

    if added_assets:
        print(f"为用户 {name} 发现新增资产: {added_assets}")
        date_start = datetime.datetime.now()
        date_expired = datetime.datetime.now() + timedelta(days=365 * 100)
        default_actions = ["connect", "upload", "download", "copy", "paste", "delete"]
        data = {
            'name': name,
            'assets': existing_assets + added_assets,
            'nodes': [],
            'accounts': accounts,
            'actions': default_actions,
            'is_active': True,
            'users': [user_id],
            'date_start': str(date_start),
            'date_expired': str(date_expired)
        }

        print(f"为用户 {name} 准备发送的数据: {data}")
        try:
            resp = requests.put(url, headers=make_headers(config), json=data, verify=False)
            resp.raise_for_status()
            print(f"为用户 {name} 更新授权成功: {resp.text}")
        except requests.exceptions.RequestException as e:
            print(f"为用户 {name} 更新授权时发生错误: {e}")
    else:
        print(f"为用户 {name} 未发现新增资产，无需更新授权")



def read_excel_accounts(file_name):
    try:
        df = pd.read_excel(file_name, engine='openpyxl')
        accounts = df.to_dict(orient='records')
        return accounts
    except FileNotFoundError:
        print(f"找不到文件: {file_name}")

def _init_jms_data(config, accounts):
    windows_assets = []
    original_assets = []
    all_assets = get_assets_list(config)
    for asset in all_assets:
        if asset.get('platform', {}).get('name') == 'Windows':
            windows_assets.append(asset)
        elif asset.get('platform', {}).get('name') == 'OriginalAppPro':
            original_assets.append(asset)

    print(f"获取Windows资产成功: 共{len(windows_assets)}个")
    for asset in windows_assets:
        create_account(config, asset['id'], accounts)

    print(f"获取OriginalAppPro资产成功: 共{len(original_assets)}个")
    for asset in original_assets:
        create_account(config, asset['id'], accounts)

def create_account(config, asset_id, accounts):
    url = f"{config.jms_url}/accounts/accounts/"
    print(f"请求 URL: {url}")

    for account in accounts:
        existing_account = check_existing_account(config, asset_id, account["username"])
        if existing_account:
            print(f"账号 {account['username']} 已存在于资产 {asset_id} 下，跳过创建")
            continue

        payload = {
            "name": account["name"],
            "username": account["username"],
            "secret_type": "password",
            "secret": account["secret"],
            "asset": asset_id,
            "privileged": True,
            "push_now": False,
            "is_active": True,
        }
        print(f"请求负载: {payload}")

        try:
            resp = requests.post(url, json=payload, headers=make_headers(config), verify=False)
            print(f"响应状态码: {resp.status_code}")
            if resp.status_code >= 300:
                print(f'[错误] {resp.text}')
            else:
                print(f"账号 {account['username']} 创建成功")
        except Exception as err:
            print(f'[错误] {err}')
            return

def check_existing_account(config, asset_id, username):
    url = f"{config.jms_url}/accounts/accounts/"
    params = {
        "asset": asset_id,
        "username": username
    }
    try:
        resp = requests.get(url, params=params, headers=make_headers(config), verify=False)
        if resp.status_code == 200:
            accounts = resp.json()
            if accounts:
                return accounts[0]
    except Exception as err:
        print(f'[错误] {err}')
    return None

def main():
    jms_config = JMSConfig(
        jms_url='http://10.1.12.27/api/v1',
        token='b525e8305efddeaa807b33e3c58c148889247273',
        jms_org='00000000-0000-0000-0000-000000000002'
    )
    excel_file = "accounts_info.xlsx"
    accounts = read_excel_accounts(os.path.join(os.getcwd(), excel_file))
    _init_jms_data(jms_config, accounts)
    users = get_user_list(jms_config)
    assets = get_assets_list(jms_config)
    if users and assets:
        create_asset_permissions(jms_config, users, assets)
    else:
        print("无法获取资产或用户信息")

if __name__ == '__main__':
    main()
