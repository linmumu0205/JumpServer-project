import requests
import time
##import warnings
##warnings.filterwarnings("ignore")  #忽略SSL证书认证

##删除v3上现有的所有授权规则
def read_permissions(jms_url, token):
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    response = requests.get(url=jms_url + "/api/v1/perms/asset-permissions/?limit=100", headers=headers,verify=False)

    if response.status_code == 200 or response.status_code == 201:
        print("获取授权规则请求成功")
        permissions_id_list = []
        permissions_data = response.json() # 将响应的JSON数据解析为字典
        permissions_results = permissions_data.get('results', [])
        for permission in permissions_results:
            permissions_id = permission.get("id")  # 提取授权 ID
            if permissions_id:
                permissions_id_list.append(permissions_id) # 将授权规则的 ID 添加到列表中
                if len(permissions_id_list) >= 100:
                    break
        #permissions_id_list_limit = permissions_id_list[:10] #不使用切片，切片是先把所有数据读取一遍写入内存后，再切前100个数据写入新列表
        return permissions_id_list 
    else:
        print("请求失败，状态码:", response.status_code)
        print(response.text)
        return None

def create_permissions_spm(jms_url,token,):
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    parms = {
        "resources": permissions_id_list
    }
    response = requests.post(url=jms_url + "/api/v1/common/resources/cache/", headers=headers, json=parms,verify=False)
    print(response.text)
    if response.status_code == 200:
        spm_info = response.json()
        spm_id = spm_info.get('spm', None)
        if spm_id:
            print(f"SPM创建成功,SPM ID: {spm_id}")
            return spm_id
        else:
            print("未能获取SPM ID信息")
    else:
        print(f"SPM创建失败,状态码:{response.status_code}")

def delete_permissions(jms_url, token, spm_id):
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    print(spm_id)
    #url=f"{jms_url}/assets/assets/?asset=&node=&spm={spm_id}"
    url = f"{jms_url}/api/v1/perms/asset-permissions/?spm={spm_id}"
    response = requests.delete(url=url, headers=headers,verify=False)
    if response.status_code == 204:
        print("SPM删除成功")
    else:
        print(f"删除SPM失败,状态码：{response.status_code}")


if __name__ == '__main__':
    jms_url = "http://10.150.249.31"
    token = "2gnWN9n39W62XeUF5obaCA85IfyDHoexkKEY"
    for i in range(100):
        permissions_id_list = read_permissions(jms_url, token)
        print(f"列表{i}:{permissions_id_list}")
        if  permissions_id_list: # 如果列表不为空
            spm_id = create_permissions_spm(jms_url,token)
            delete_permissions(jms_url,token,spm_id)
            time.sleep(3)
            print("正在休息中，请稍等…………")
            print(f"id:{i} 此批次授权已经删除")
            continue
        else:
            print("授权已经全部删除")
            break