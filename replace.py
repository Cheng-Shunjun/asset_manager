import os

def replace_in_filenames(directory, old_str, new_str):
    """
    替换目录下所有文件名中的指定字符串
    
    Args:
        directory: 目录路径
        old_str: 要替换的旧字符串
        new_str: 替换后的新字符串
    """
    if not os.path.exists(directory):
        print(f"目录 {directory} 不存在")
        return
    
    for filename in os.listdir(directory):
        old_path = os.path.join(directory, filename)
        
        if os.path.isfile(old_path):
            # 替换文件名中的字符串
            new_filename = filename.replace(old_str, new_str)
            
            if new_filename != filename:  # 只有当文件名确实改变时才重命名
                new_path = os.path.join(directory, new_filename)
                os.rename(old_path, new_path)
                print(f"重命名: {filename} -> {new_filename}")

# 使用示例
replace_in_filenames("./", "证书证书", "证书")