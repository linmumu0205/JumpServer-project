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


def delete_permissions(config, permission_info):
    global delete_url, permission_id
    url = f"{config.jms_url}/perms/asset-permissions/"
    try:
        for permission in permission_info:
            permission_id = permission['id']
            delete_url = f"{url}{permission_id}/"
        resp = requests.delete(delete_url, headers=make_headers(config), verify=False)
        resp.raise_for_status()
        print(f"成功删除权限：{permission_id}")
    except requests.exceptions.RequestException as e:
        print(f"删除权限时发生错误: {e}")
        return None


def main():
    jms_config = JMSConfig(
        jms_url='http://10.1.12.27/api/v1',
        token='b525e8305efddeaa807b33e3c58c148889247273',
        jms_org='00000000-0000-0000-0000-000000000002'
    )


if __name__ == '__main__':
    main()
