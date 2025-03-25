import applets
import json
import base64

import requests
from httpsig.requests_auth import HTTPSignatureAuth
from datetime import datetime


def get_auth(key_id, key_secret):
    signature_headers = ['(request-target)', 'accept', 'date']
    auth = HTTPSignatureAuth(key_id=key_id, secret=key_secret, algorithm='hmac-sha256',
                             headers=signature_headers)
    return auth


def get_header():
    gmt_form = '%a, %d %b %Y %H:%M:%S GMT'
    headers = {
        'Accept': 'application/json',
        'X-JMS-ORG': '00000000-0000-0000-0000-000000000002',
        'Date': datetime.utcnow().strftime(gmt_form)
    }
    return headers


class UserClient(object):

    def __init__(self, base_url, access_key, access_secret):
        self.base_url = base_url
        self.access_key = access_key
        self.access_secret = access_secret

    def create_token(self, **data):
        url = f"{self.base_url}/api/v1/authentication/super-connection-token/"
        auth = get_auth(self.access_key, self.access_secret)
        headers = get_header()
        resp = requests.post(url, headers=headers, auth=auth, json=data)
        return resp.json()

    def get_connect_token_auth_info(self, token):
        data = {
            "id": token,
            "expire_now": False,
        }
        url = f"{self.base_url}/api/v1/authentication/super-connection-token/secret/"
        access_key = self.access_key
        access_secret = self.access_secret
        auth = get_auth(access_key, access_secret)
        res = requests.post(url, headers=get_header(), auth=auth, json=data)
        return res.json()


def main():
    base_url = 'http://10.1.12.87:80' # 尹瑞
    access_key = '97551252-4008-4c11-8ce9-879f46c1eab5'
    access_secret = '6250a1e1-42e9-4710-b312-929d02aa583e'  # 由jms管理员生成
    user_client = UserClient(base_url, access_key, access_secret)
    data = {
        "user": "4ed72381-e5cc-4efb-a62c-f562634adc60",  # 使用发布机的用户id
        "asset": "1cbcf0ef-f97e-48ba-ac63-58dae589c6c8",  # 发布的远程应用资产的id
        "account": "null",  # 登录远程应用资产的账号,注意根据登录资产不同修改！
        "protocol": "rdp",  # 远程应用资产的协议
        "connect_method": "rdp",  # 远程应用连接方式
    }
    token = user_client.create_token(**data)
    print("create token: ", token['id'])
    print("================== get token detail ==================")
    detail = user_client.get_connect_token_auth_info(token['id'])
    print(json.dumps(detail, indent=2, ensure_ascii=False))
    print("================== get token base64 ==================")
    #print(applets.b64encode(json.dumps(detail).encode()).decode())
    print(base64.b64encode(json.dumps(detail).encode()).decode())

if __name__ == '__main__':
    main()
