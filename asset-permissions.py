import json
import warnings
import requests
import datetime
from datetime import timedelta
warnings.filterwarnings("ignore")  # 忽略SSL证书认证
from httpsig.requests_auth import HTTPSignatureAuth

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
# 获取全部用户并获取用户id、account
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
# 通过匹配获取需要授权的资产
def get_assets_list(config):
    url = f"{config.jms_url}/assets/assets/"
    resp = requests.get(url, headers=make_headers(config), verify=False)
    assets_list = resp.json()
    # 仅打印出需要更新密码的windows资产
    windows_assets = [asset for asset in assets_list if asset.get('platform', {}).get('name') == 'Windows']
    if windows_assets:
        print(f"获取windows资产成功: 共{len(windows_assets)}个")
    else:
        print("未找到符合条件的Windows资产")
    for asset in windows_assets:
        print(f"资产名称: {asset['name']}, 资产ID: {asset['id']}, 系统平台: {asset.get('platform', {}).get('name')}")
    return windows_assets

def _init_jms_data(config):
    # 初始化数据
    windows_assets = get_assets_list(config)
    assets_info = {asset['name']: asset['id'] for asset in windows_assets}
    print(f"获取windows资产成功: 共{len(assets_info)}个")
    users_info = get_user_list(config)
    if users_info:
        print(f"获取用户信息成功: 共{len(users_info)}个")
    else:
        print("未找到用户信息")
def get_asset_permissions(config):
    url = f"{config.jms_url}/perms/asset-permissions/"
    try:
        resp = requests.get(url, headers=make_headers(config), verify=False)
        resp.raise_for_status()
        #return resp.json() # 获取授权全部信息不做处理
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
# 为上面获取到的用户创建授权
def creat_asset_permissions(config, users_info, assets_info):
    url = f"{config.jms_url}/perms/asset-permissions/"
    print(f"请求url:{url}")
    default_actions = ["connect", "upload", "download", "copy", "paste", "delete"]

    for user_info in users_info:
        name = user_info['username']
        user_id = user_info['uuid']
        # 从 users_info 和 assets_info 中获取用户、资产和账户信息
        assets = [asset['id'] for asset in assets_info]
        accounts = ['js_' + name]  # 这里假设账户信息与用户名相同

        date_start = datetime.datetime.now()
        date_expired = datetime.datetime.now() + timedelta(days=365 * 100)
        data = {
            'name': name, 'assets': assets, 'nodes': [], 'accounts': accounts,
            'actions': default_actions, 'is_active': True, 'users': [user_id],
            'date_start': str(date_start), 'date_expired': str(date_expired)
        }

        # 打印请求体
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
    windows_assets = get_assets_list(jms_config)
    users_info = get_user_list(jms_config)
    if permissions and users:
        print(f"该组织授权共计 {len(permissions)} 条。该组织用户共计{len(users)} 个。")
        # print("成功获取资产授权如下：", permissions)
        # print("成功获取用户如下：", users)
    else:
        print(f"无法获取资产或用户信息")
    if windows_assets and users_info:
        creat_asset_permissions(jms_config, users_info, windows_assets)
    else:
        print("无法获取资产或用户信息")

if __name__ == '__main__':
    main()
