#   优化创建账号逻辑同时匹配多类型资产
#   即将账号创建到多类型资产下
import json
import pandas as pd
import warnings
import requests
import os

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

#   获取资产列表并仅匹配Windows和OriginalAppPro资产
def get_assets_list(config):
    url = f"{config.jms_url}/assets/assets/"
    resp = requests.get(url, headers=make_headers(config), verify=False)
    assets_list = resp.json()
    # 获取Windows和OriginalAppPro资产
    windows_assets = [asset for asset in assets_list if asset.get('platform', {}).get('name') == 'Windows']
    original_assets = [asset for asset in assets_list if asset.get('platform', {}).get('name') == 'OriginalAppPro']
    # 打印Windows资产
    for asset in windows_assets:
        print(f"Windows资产名称: {asset['name']}, 资产ID: {asset['id']}, 系统平台: {asset.get('platform', {}).get('name')}")
    # 打印OriginalAppPro资产
    for asset in original_assets:
        print(f"OriginalAppPro资产名称: {asset['name']}, 资产ID: {asset['id']}, 系统平台: {asset.get('platform', {}).get('name')}")
    # 返回两种类型的资产列表
    return windows_assets + original_assets

#   读取从远程应用下获取的账号excel
def read_excel_accounts(file_name):
    try:
        df = pd.read_excel(file_name, engine='openpyxl')
        accounts = df.to_dict(orient='records')
        return accounts
    except FileNotFoundError:
        print(f"找不到文件: {file_name}")

def _init_jms_data(config, accounts):
    # 初始化数据
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

#   当账号存在时不再发请求
def create_account(config, asset_id, accounts):
    # 构建请求 URL并从初始化数据中拿需要创建账号的资产id
    url = f"{config.jms_url}/accounts/accounts/"
    print(f"请求 URL: {url}")  # 打印请求 URL

    for account in accounts:
        # 检查账号是否已存在
        existing_account = check_existing_account(config, asset_id, account["username"])
        if existing_account:
            print(f"账号 {account['username']} 已存在于资产 {asset_id} 下，跳过创建")
            continue

        # 构建请求数据
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
        print(f"请求负载: {payload}")  # 打印请求负载

        # 发送 Post 请求创建账号
        try:
            resp = requests.post(url, json=payload, headers=make_headers(config), verify=False)
            print(f"响应状态码: {resp.status_code}")  # 打印响应状态码
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
                return accounts[0]  # 返回第一个找到的账号
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

if __name__ == '__main__':
    main()
