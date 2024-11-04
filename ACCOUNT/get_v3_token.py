import requests
import warnings
warnings.filterwarnings("ignore")  # 忽略SSL证书认证

##调用接口,获取token信息
def get_token(jms_url,username,password):
    headers = {
        'Content-Type': 'application/json',
    }
    payload = {
    "username": f'{username}',
    "password": f'{password}'
    }
    response = requests.post(url=jms_url + "/api/v1/authentication/auth/", headers=headers, json=payload,verify=False)

    if response.status_code == 200 or 201:
        print("获取token请求成功")
        data = response.json()  # 将响应的JSON数据解析为字典
        specific_field_value_token = data.get("token")  # 替换为实际字段名
        print("token的值:", specific_field_value_token)
    else:
        print("请求失败，状态码:", response.status_code)
        print(response.text)

if __name__ == '__main__':
    jms_url = "https://192.168.31.152"
    username = "user123"
    password = "jumpserver"
    get_token(jms_url,username,password)