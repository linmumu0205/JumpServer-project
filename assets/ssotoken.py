# -*- coding: utf-8 -*-
# __author:linmy
# data:2024/12/26
import requests
import json
import datetime
from httpsig.requests_auth import HTTPSignatureAuth
import urllib3

# 忽略 InsecureRequestWarning 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def get_auth(KeyID, SecretID):
    signature_headers = ['(request-target)', 'accept', 'date']
    auth = HTTPSignatureAuth(key_id=KeyID, secret=SecretID, algorithm='hmac-sha256', headers=signature_headers)
    return auth


def post_connection_token(jms_url, auth, user_id, asset_id):
    url = f"{jms_url}/api/v1/authentication/connection-token/"
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'X-JMS-ORG': '00000000-0000-0000-0000-000000000002',
        'Date': datetime.datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
    }

    data = {
        "protocol": "rdp",
        "user": user_id,
        "asset": asset_id,
        "account": "administrator1",
        "connect_method": "web_cli",
        "connect_options": {
            "charset": "default",
            "disableautohash": False,
            "resolution": "auto",
            "backspaceAsCtrlH": False,
            "appletConnectMethod": "web",
            "reusable": False,
            "file_name_conflict_resolution": "replace",
            "terminal_theme_name": "Default"
        }
    }

    try:
        response = requests.post(url, auth=auth, headers=headers, json=data, verify=False)
        response.raise_for_status()
        response_data = response.json()

        if 'id' in response_data:
            connection_id = response_data['id']
            timestamp = int(datetime.datetime.now().timestamp() * 1000)
            connection_url = f"/lion/connect/?disableautohash=false&token={connection_id}&_={timestamp}"
            return connection_url
        else:
            print("ID not found in response.")
            return None
    except requests.exceptions.RequestException as e:
        print(f"An error: {e}")
        return None


def sso_auth(jms_url, connection_url, KeyID, SecretID):
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'X-JMS-ORG': '00000000-0000-0000-0000-000000000002',
        'Date': datetime.datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
    }
    url = f"{jms_url}/api/v1/authentication/sso/login-url/"
    data = {
        "username": "admin",  # 请根据实际情况修改用户名
        "next": connection_url
    }
    auth = get_auth(KeyID, SecretID)

    response = requests.post(url, auth=auth, headers=headers, json=data, verify=False)
    response.raise_for_status()
    response_data = response.json()
    print(response_data)


if __name__ == '__main__':
    jms_url = 'https://192.168.75.166'
    # AK SK
    KeyID = '26d58dbd-8ea9-4bd1-bd96-4c734e187c07'
    SecretID = 'eQD6VWKtm5XDjJEwkhSUPsouHY4lZ7WFtZzw'

    auth = get_auth(KeyID, SecretID)
    # 用户id
    user_id = 'b3e7822d-ee31-47ca-9fb1-e42f67ccc338'
    # 资产id
    asset_id = '9bc52f94-6838-408b-86c4-2809630b06d3'

    connection_url = post_connection_token(jms_url, auth, user_id, asset_id)
    # connection_url="/luna/connect?asset=e8201fac-b067-48d9-ae59-1a0e42f12072"
    if connection_url:
        sso_auth(jms_url, connection_url, KeyID, SecretID)
