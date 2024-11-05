import concurrent.futures
import requests
import time
import datetime
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from httpsig.requests_auth import HTTPSignatureAuth

def create_headers():
    gmt_form = '%a, %d %b %Y %H:%M:%S GMT'
    headers = {
        'Accept': 'application/json',
        # 组织id，多组织设置成 全局组织ID：00000000-0000-0000-0000-000000000000
        'X-JMS-ORG': '00000000-0000-0000-0000-000000000002',
        'Date': datetime.datetime.utcnow().strftime(gmt_form)
    }
    return headers

def get_auth(key_id, secret_id):
    signature_headers = ['(request-target)', 'accept', 'date']
    auth = HTTPSignatureAuth(key_id=key_id, secret=secret_id, algorithm='hmac-sha256', headers=signature_headers)
    return auth

def fetch_page(url, auth, page_num):
    headers = create_headers()
    try:
        response = requests.get(f"{url}?page={page_num}", auth=auth, headers=headers, verify=False)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"请求用户列表时发生错误: {e}")
        return None

def get_user_info(jms_url, auth):
    url = jms_url + '/api/v1/users/users/'
    headers = create_headers()
    try:
        response = requests.get(url, auth=auth, headers=headers, verify=False)
        response.raise_for_status()
        data = response.json()
#        print("Initial response data:", data)  # 调试输出

        # 确定返回的数据是字典还是列表
        if isinstance(data, list):
            total_pages = 1
            results = data
        elif isinstance(data, dict):
            total_pages = data.get('total_pages', 1)
            results = data.get('results', [])
        else:
            print("Unexpected data format")
            return None

        # 多线程获取所有页面的数据
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(fetch_page, url, auth, page_num) for page_num in range(1, total_pages + 1)]
            users = results  # 存储初始请求结果
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                if result and isinstance(result, dict):  # 确保 result 是字典并包含 results 键
                    users.extend(result.get('results', []))

        user_ids = [{'id': user['id'], 'name': user['name']} for user in users]
        # user_ids = [user['id'] for user in users]
        return user_ids

    except requests.exceptions.RequestException as e:
        print(f"请求用户列表时发生错误: {e}")
        return None


def fetch_user_assets(jms_url, auth, user_id):
    url = jms_url + f"/api/v1/perms/users/{user_id}/assets/"
    headers = create_headers()
    try:
        response = requests.get(url, auth=auth, headers=headers, verify=False)
        response.raise_for_status()
        result = response.json()
        if isinstance(result, list) and not result:
            return user_id
        return None
    except requests.exceptions.RequestException as e:
        print(f"请求用户资产时发生错误 (user_id={user_id}): {e}")
        return None

def get_user_assets(jms_url, auth):
    user_ids = get_user_info(jms_url, auth)
    if not user_ids:
        return None

    ids_delete = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch_user_assets, jms_url, auth, user_id): user_id for user_id in user_ids}
        for future in concurrent.futures.as_completed(futures):
            user_id = future.result()
            if user_id:
                ids_delete.append(user_id)

    return ids_delete

def delete_user_id(jms_url, auth, user):
    user_id = user['id']
    user_name = user['name']
    url = jms_url + f'/api/v1/users/users/{user_id}/'
    headers = create_headers()
    try:
        response = requests.delete(url, auth=auth, headers=headers, verify=False)
        response.raise_for_status()
        print(f"正在删除用户: {user_name} ({user_id})")
        return user_id
    except requests.exceptions.RequestException as e:
        print(f"删除用户 {user_name} ({user_id}) 时发生错误: {e}")
        return None

def delete_users(jms_url, auth):
    user_info = get_user_info(jms_url, auth)
    if not user_info:
        print("没有用户需要删除")
        return None

    deleted_users = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(delete_user_id, jms_url, auth, user): user for user in user_info}
        for future in concurrent.futures.as_completed(futures):
            try:
                result = future.result()
                if result:
                    user = futures[future]
                    deleted_users.append(f"{result} ({user['name']})")
            except Exception as e:
                print(f"执行任务时发生错误: {e}")

    if not deleted_users:
        print("没有用户被删除或删除过程出错")
    return deleted_users

if __name__ == '__main__':

    start_time = time.time()
    # JumpServer访问地址
    jms_url = 'http://192.168.250.12:8080'
    # JumpServer 用户API Key
    key_id = '17c11bf6-3958-4982-aed8-8fb619262c5f'
    secret_id = 'zEavOowY2FIZC7VhXDcxDj4PylQDnjWmpBoM'
    auth = get_auth(key_id, secret_id)
    delete_users(jms_url, auth)

    end_time = time.time()
    total_time = end_time - start_time
    total_minutes = total_time / 60
    print(f"程序运行时间：{total_minutes:.2f} 分钟")
