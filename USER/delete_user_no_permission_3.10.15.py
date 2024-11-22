import time
from datetime import datetime
import requests
from httpsig.requests_auth import HTTPSignatureAuth
import urllib3
# 禁用 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_auth(KeyID, SecretID):  #认证信息
    signature_headers = ['(request-target)', 'accept', 'date']
    auth = HTTPSignatureAuth(key_id=KeyID, secret=SecretID, algorithm='hmac-sha256', headers=signature_headers)
    return auth

def get_all_users(jms_url, headers, auth):  #此方法是分页后获取所有信息写入users中
    # 初始化获取数据的参数
    params = {
        "offset": 0,
        "limit": 100,
        "display": 1,
        "draw": 1
    }
    users = []  # 用于存储所有用户
    # 初始请求
    while True:
        response_users = requests.get(url=jms_url + '/users/users/',headers=headers,auth=auth,verify=False,params=params)
        # 检查请求是否成功
        if response_users.status_code != 200:
            print(f"请求失败，状态码：{response_users.status_code}")
            break
        # 获取返回的 JSON 数据
        data = response_users.json()
        # 将当前页的数据添加到 users 列表中
        users.extend(data["results"])
        # 检查是否有下一页
        next_url = data.get("next")
        if not next_url:
            break  # 没有下一页，退出循环
        # 如果有下一页，更新请求参数
        # 从返回的 next_url 提取新的 offset，继续请求
        params["offset"] += params["limit"]
    #print(users)
    users_id=[]
    for item in users:
        users_id.append(item['id'])
    return users_id

def getuser_asset(jms_url, headers, auth,user_id):
    try:
        URL=jms_url + f'/perms/users/{user_id}/assets/'
        response = requests.get(url=URL,headers=headers,auth=auth,verify=False)
        response.raise_for_status()
        #print(response.text)
        if response.text.strip() == '[]':
            print(f"{user_id}这个用户需要删除！！！")
            delete_user(jms_url, headers, auth,user_id)
        else:
            print('这个用户有授权，无需删除。')
    except requests.exceptions.RequestException as e:
        print(f"请求用户资产时发生错误 : {e}")
        return None

def delete_user(jms_url, headers, auth,user_id):
    try:
        URL = jms_url + f'/users/users/{user_id}/'
        response = requests.delete(url=URL, headers=headers, auth=auth, verify=False)
        response.raise_for_status()
        print(f"正在删除用户:  ({user_id})")
        return user_id
    except requests.exceptions.RequestException as e:
        print(f"删除用户 {user_id}) 时发生错误: {e}")
        return None

if __name__ == '__main__':
    start_time = time.time()
    jms_url = "http://10.1.12.50/api/v1"
    gmt_form = '%a, %d %b %Y %H:%M:%S GMT'
    headers = {
        'Accept': 'application/json',
        'X-JMS-ORG': '00000000-0000-0000-0000-000000000002',
        'Date': datetime.utcnow().strftime(gmt_form)
    }
    KeyID = 'd30755da-82d0-441e-aad3-92fbb28f432a'
    SecretID = 'vKBci2KeWJp8LmjE5WtDc7XbpF8AjmsX0bzu'
    auth = get_auth(KeyID, SecretID)
    users_id = get_all_users(jms_url, headers, auth)
    for user_id in users_id:
        getuser_asset(jms_url, headers, auth, user_id)
    end_time = time.time()
    total_time = end_time - start_time
    total_minutes = total_time / 60
    print(f"程序运行时间：{total_minutes:.2f} 分钟")
