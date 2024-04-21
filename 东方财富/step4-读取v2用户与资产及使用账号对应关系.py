import pymysql
import pandas as pd

# 连接数据库
connection = pymysql.connect(
    host='10.150.249.11',
    user='root',
    password='jumpserver',
    database='jumpserver',
    charset='utf8mb3'
)

try:
    # 创建一个空的DataFrame，用于存储查询结果
    df = pd.DataFrame(columns=['User ID', 'User Name', 'Real Name', 'assetpermission_id', 'Asset IP', 'Asset Hostname', 'Asset ID', 'Systemuser Name', 'Systemuser UserName', 'Systemuser ID'])

    # 每次查询1000条数据，直到所有数据查询完毕
    offset = 0
    limit = 100
    while True:
        # 执行SQL查询
        with connection.cursor() as cursor:
            sql_query = f"""
            SELECT
                main_1.user_id,
                main_1.user_name,
                main_1.real_name,
                GROUP_CONCAT(DISTINCT main_1.assetpermission_id ) AS assetpermission_id,
                GROUP_CONCAT(DISTINCT assets_asset.ip ) AS asset_ip,
                GROUP_CONCAT(DISTINCT assets_asset.hostname ) AS asset_hostname,
                GROUP_CONCAT(DISTINCT assets_asset.id ) AS asset_id,
                GROUP_CONCAT(DISTINCT assets_systemuser.name ) AS assets_systemuser_name,
                GROUP_CONCAT(DISTINCT assets_systemuser.username ) AS assets_systemuser_username,
                GROUP_CONCAT(DISTINCT assets_systemuser.id ) AS assets_systemuser_id
            FROM
                (
                SELECT
                    uu.id AS user_id,
                    uu.NAME AS user_name,
                    uu.username AS real_name,
                    pau.assetpermission_id
                FROM
                    users_user uu
                    LEFT JOIN perms_assetpermission_users pau ON ( uu.id = pau.user_id )
                WHERE
                    uu.role <> "App"
                    AND uu.created_by <> "System" UNION
                SELECT
                    us.id AS user_id,
                    us.NAME AS user_name,
                    us.username AS real_name,
                    paug.assetpermission_id
                FROM
                    perms_assetpermission_user_groups paug
                    INNER JOIN users_usergroup uu ON ( paug.usergroup_id = uu.id )
                    INNER JOIN users_user_groups uug ON ( uu.id = uug.usergroup_id )
                    INNER JOIN users_user us ON ( us.id = uug.user_id )
                ) main_1
                LEFT JOIN (
                SELECT
                    paa.assetpermission_id AS permission_id,
                    paa.asset_id AS asset_id
                FROM
                    perms_assetpermission_assets paa UNION
                SELECT
                    pan.assetpermission_id AS permission_id,
                    aan.asset_id AS asset_id
                FROM
                    perms_assetpermission_nodes pan
                    INNER JOIN assets_asset_nodes aan ON ( pan.node_id = aan.node_id )
                ) main_2 ON ( main_1.assetpermission_id = main_2.permission_id )
                LEFT JOIN (
                SELECT
                    pasu.assetpermission_id AS permission3_id,
                    pasu.systemuser_id AS systemuser_id
                FROM
                    perms_assetpermission_system_users pasu 
                ) main_3 ON ( main_1.assetpermission_id = main_3.permission3_id )
                LEFT JOIN assets_asset ON ( main_2.asset_id = assets_asset.id )
                LEFT JOIN assets_systemuser ON ( main_3.systemuser_id = assets_systemuser.id )
            WHERE
                main_2.asset_id IS NOT NULL
            GROUP BY
                main_1.user_id,
                main_1.user_name,
                main_1.real_name
            ORDER BY 
                main_1.user_name
            LIMIT {offset}, {limit};
            """
            cursor.execute(sql_query)
            result = cursor.fetchall()

            # 如果没有查询到数据，则退出循环
            if not result:
                break

            # 将查询结果转换为DataFrame，并添加到总的DataFrame中
            batch_df = pd.DataFrame(result, columns=['User ID', 'User Name', 'Real Name', 'assetpermission_id', 'Asset IP', 'Asset Hostname', 'Asset ID', 'Systemuser Name', 'Systemuser UserName', 'Systemuser ID'])
            df = pd.concat([df, batch_df], ignore_index=True)

        # 更新偏移量，准备下一次查询
        offset += limit

finally:
    # 关闭数据库连接
    connection.close()

# 将结果保存为Excel文件
df.to_excel('C:\\Users\\35952\\Desktop\\mysql-result.xlsx', index=False)