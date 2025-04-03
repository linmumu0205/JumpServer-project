#!/bin/bash

# 定义输入输出文件
OLD_CONFIG="old_config.txt"
TEMPLATE="new_config_template.txt"
OUTPUT="jumpserver.conf"

# 创建安全临时文件
TMP_OLD=$(mktemp)
TMP_NEW=$(mktemp)

# 退出时清理临时文件
cleanup() {
    rm -f "$TMP_OLD" "$TMP_NEW"
}
trap cleanup EXIT

# 1. 处理模板文件：保留所有注释和结构
cp "$TEMPLATE" "$TMP_NEW"

# 2. 提取旧配置中的有效参数（非注释且非空行）
grep -E '^[^#][^=]*=.+' "$OLD_CONFIG" | while IFS= read -r line; do
    # 移除行尾注释并清理空白字符
    line=$(echo "$line" | sed 's/[[:space:]]*#.*$//')
    echo "$line"
done > "$TMP_OLD"

# 3. 构建参数映射
declare -A old_params
while IFS='=' read -r key value; do
    key=$(echo "$key" | sed 's/[[:space:]]*$//')
    value=$(echo "$value" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    # 跳过空键或空值
    [ -n "$key" ] && [ -n "$value" ] && old_params["$key"]="$value"
done < "$TMP_OLD"

# 4. 安全替换模板中的参数
for key in "${!old_params[@]}"; do
    # 转义特殊字符
    escaped_key=$(printf '%s\n' "$key" | sed 's/[\/&]/\\&/g')
    escaped_value=$(printf '%s\n' "${old_params[$key]}" | sed 's/[\/&]/\\&/g')
    
    # 检查键是否在模板中存在
    if grep -q "^[[:space:]]*${escaped_key}=" "$TMP_NEW"; then
        # 使用安全的分隔符替换值
        sed -i "s|^\([[:space:]]*${escaped_key}=\).*|\1${escaped_value}|" "$TMP_NEW"
        unset old_params["$key"]
    fi
done

# 5. 添加旧版特有配置到文件末尾
if [ ${#old_params[@]} -ne 0 ]; then
    {
        echo ""
        echo "################################## 旧版额外配置 ###################################"
        for key in "${!old_params[@]}"; do
            echo "$key=${old_params[$key]}"
        done
        echo "# 注：以上为旧版特有配置，请检查新版兼容性"
        echo ""
    } >> "$TMP_NEW"
fi

# 6. 生成最终输出并检查大小
cat "$TMP_NEW" > "$OUTPUT"
[ -s "$OUTPUT" ] || { echo "错误：输出文件为空"; exit 1; }

echo "配置转换成功完成，结果已保存到 $OUTPUT"
exit 0