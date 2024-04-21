import requests
import openpyxl
import threading

##删除v3上所有资产账号列表
##def delete_old_asset_permissions(private_token,):
##    headers = {
##        'Content-Type': 'application/json',
##        'Authorization': f'Bearer {private_token}'
##    }

##直接sql ： delete from accounts_account;

##创建资产账号的接口 
def bind_asset_systemuser(username,asset_id,asset_name,secret,privileged="false"):
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {private_token}',
        'X-JMS-ORG': '00000000-0000-0000-0000-000000000002'
    }
    payload = {
        "name": asset_name + username,               
        "username": username,
        "secret_type": "password",               
        "secret": secret,
        "asset": asset_id,
        "is_active": "true", 
        "push_now": "false",
        "privileged": privileged
    }
    response = requests.post(url=jms_url + "/api/v1/accounts/accounts/", headers=headers, json=payload)
    if response.status_code == 200 or response.status_code == 201:
        print("绑定资产账号成功")
        print(asset_name,asset_name + username,username)
    else:
        print("请求失败，状态码:", response.status_code)
        print(response.text,asset_name,asset_name + username,username,asset_id)    


##在资产上绑定探测结果为success的资产账号密码
def create_success_systemuser(ws, idx, row):
    asset_name, asset_id, username, secret, result = row[1], row[0], row[6], row[7], row[11]
    if "success" in result:
        if username == "root" or username == "administrator":
            bind_asset_systemuser(username,asset_id,asset_name,secret,privileged="true")
        else:
            bind_asset_systemuser(username,asset_id,asset_name,secret)
        


##启用多线程进行绑定
def create_systemuser_threading(file_path):
    wb = openpyxl.load_workbook(file_path)
    ws = wb.active

    threads = [] # 创建一个空列表，用于存储线程对象
    # values_only=True参数表示只获取单元格的值而不是整个单元格对象
    # threading.Thread创建一个线程对象，target参数是要执行的目标函数,args参数是传递给目标函数的参数
    # 将创建的线程对象添加到threads列表中
    # 启动线程，开始执行目标函数
    for idx, row in enumerate(ws.iter_rows(values_only=True), start=1):
        thread = threading.Thread(target=create_success_systemuser, args=(ws, idx, row))
        threads.append(thread)
        thread.start()

    # 等待所有线程执行完毕,以确保主线程在所有子线程执行完毕之前不会结束
    for thread in threads:
        thread.join()

 
if __name__ == '__main__':
    jms_url = "http://10.1.12.40"
    private_token = "BJN6kbmua5vdQKztHBCcQbLCpOQbmeLbmMSL"
    file_path = "/opt/jumpserver/JumpServer-Asset-2024-03-12-result.xlsx"
    create_systemuser_threading(file_path)