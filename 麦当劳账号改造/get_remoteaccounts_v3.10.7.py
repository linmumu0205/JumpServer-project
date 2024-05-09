import json
import warnings
import requests
import pandas as pd
import os

warnings.filterwarnings("ignore")  # 忽略SSL证书认证

def read_account(jms_url, token):
    headers = {
        'Authorization': f'Token {token}',
        'Content-Type': 'application/json',
        'X-JMS-ORG': '00000000-0000-0000-0000-000000000004',
    }
    response = requests.get(url=jms_url, headers=headers, verify=False)
    #print("Response content:", response.text)  # 添加此行以打印响应内容

    if response.status_code == 200:
        data = response.json()
        return data  # 直接返回整个响应数据列表
    else:
        print(f"获取账号信息失败，状态码：{response.status_code}")

def save_to_excel(accounts_info):
    accounts_list = []
    for account in accounts_info:
        account_data = {
            'id': account['id'],
            'name': account['name'],
            'username': account['username'],
            'secret_type': account['secret_type']['label'],
            'secret': "Jumpserver01."
        }
        accounts_list.append(account_data)

    # 将账号信息保存至Excel表格
    df = pd.DataFrame(accounts_list)
    file_path = 'accounts_info2.xlsx'  # 修改保存文件路径为相对路径
    df.to_excel(file_path, index=False)
    print(f"账号信息已保存至 {file_path}")

if __name__ == '__main__':
    jms_url = 'http://10.1.12.27/api/v1/accounts/accounts/?asset=f4ad3809-7683-42fe-957e-5ec9554c1a9e'
    token = 'b525e8305efddeaa807b33e3c58c148889247273'
    #jms_url = 'http://10.1.12.87/api/v1/accounts/accounts/?asset=354a240a-07f7-4780-8c56-1110759631b0'
    #token = '0527d6b7f9932910c80d4a84fc3eefb082940946'
    # 调用read_account函数获取账号列表
    accounts_info = read_account(jms_url, token)
    if accounts_info:
        # 调用保存至Excel函数
        save_to_excel(accounts_info)
