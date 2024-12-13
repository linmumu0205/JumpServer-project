from pathlib import Path

def print_directory_structure_with_pathlib(start_path, indent=0):
    """
    使用 pathlib 输出目录结构
    :param start_path: 起始路径
    :param indent: 缩进级别
    """
    path = Path(start_path)
    for item in path.iterdir():
        print("  " * indent + "|-- " + item.name)
        if item.is_dir():  # 如果是目录，则递归调用
            print_directory_structure_with_pathlib(item, indent + 1)

if __name__ == "__main__":
    path = input("请输入需要展示结构的目录路径：")  # 用户输入路径
    if Path(path).exists():
        print(f"目录结构（{path}）：")
        print_directory_structure_with_pathlib(path)
    else:
        print("输入的路径不存在！")
