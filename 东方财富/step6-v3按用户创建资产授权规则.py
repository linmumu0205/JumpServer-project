import requests
import openpyxl
import json

##根据v2结果创建资产授权规则
def create_asset_permissions(token,user_name,user_id,asset_id,system_user_name):
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}'
    }
    payload = {
        "name": user_name+"_permission",                   
        "users": [user_id],                      
        "assets": asset_id, 
        "accounts": ["@INPUT","@SPEC"] + system_user_name, 
        "actions": ["all"],          
        "comment": user_name+"_permission",
        "is_active": "true"                  
    }
    response = requests.post(url=jms_url + "/api/v1/perms/asset-permissions/", headers=headers, json=payload)
    ##print(response.text)
    if response.status_code == 200 or response.status_code == 201:
        print("创建授权规则成功")
    else:
        print("请求失败，状态码:", response.status_code)
        print(response.text)

def read_permissions_excel(file_path):
    wb = openpyxl.load_workbook(file_path)
    ws = wb.active

    for idx, row in enumerate(ws.iter_rows(values_only=True), start=1):
        user_name, user_id, asset_id, system_user_name = row[1], row[0], row[6], row[8]
        # 将换行符替换为空字符串
        asset_id = asset_id.replace("\n", "")
        # 删除多余的空格
        asset_id = asset_id.replace(" ", "")
        # 使用 split() 方法将字符串分割成多个子串，并去除逗号
        substrings1 = asset_id.split(',')
        # 使用列表推导式将子串格式化为所需格式
        formatted_asset_ids = [f"{substring}" for substring in substrings1]
        print(formatted_asset_ids)
        
        substrings2 = system_user_name.split(',')
        formatted_system_user_name = [substring.strip() for substring in substrings2]  # 去除空格
        print(formatted_system_user_name)
        create_asset_permissions(token,user_name,user_id,formatted_asset_ids,formatted_system_user_name)
          

if __name__ == "__main__":
    jms_url = "http://10.150.249.32"
    token = "v0rn59mGibFzzzMsJbiHXwquPmLSzlp0NIKS"
    file_path = "C:\\Users\\35952\\Desktop\\mysql-result.xlsx"
    read_permissions_excel(file_path)