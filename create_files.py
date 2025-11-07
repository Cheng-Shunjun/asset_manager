#!/usr/bin/env python3

import os
import sys

def create_directory_structure():
    """创建项目目录结构"""
    
    # 项目根目录
    base_dir = "project_management"
    
    # 目录结构定义
    structure = {
        "": [  # 根目录文件
            "main.py",
            "config.py",
            "requirements.txt",
            "README.md"
        ],
        "database": [
            "__init__.py",
            "database.py",
            "models.py"
        ],
        "auth": [
            "__init__.py", 
            "auth.py",
            "sessions.py"
        ],
        "routes": [
            "__init__.py",
            "auth_routes.py",
            "project_routes.py", 
            "report_routes.py",
            "user_routes.py",
            "file_routes.py"
        ],
        "services": [
            "__init__.py",
            "project_service.py",
            "report_service.py",
            "file_service.py"
        ],
        "utils": [
            "__init__.py",
            "helpers.py",
            "validators.py"
        ],
        "static": [],  # 空目录，用于静态文件
        "templates": []  # 空目录，用于模板文件
    }
    
    print("开始创建项目目录结构...")
    
    # 创建基础目录
    if not os.path.exists(base_dir):
        os.makedirs(base_dir)
        print(f"✅ 创建根目录: {base_dir}")
    else:
        print(f"📁 根目录已存在: {base_dir}")
    
    # 创建所有子目录和文件
    for directory, files in structure.items():
        dir_path = os.path.join(base_dir, directory)
        
        # 创建目录
        if directory and not os.path.exists(dir_path):
            os.makedirs(dir_path)
            print(f"✅ 创建目录: {dir_path}")
        elif directory:
            print(f"📁 目录已存在: {dir_path}")
        
        # 创建文件
        for file in files:
            file_path = os.path.join(dir_path, file)
            if not os.path.exists(file_path):
                with open(file_path, 'w', encoding='utf-8') as f:
                    # 为特定文件添加基本内容
                    if file == "__init__.py":
                        f.write('"""Package initialization"""\n')


try:
    create_directory_structure()
    # create_main_file()
    # create_config_file()
    
    print("\n" + "=" * 50)
    print("🎊 所有文件创建完成！")
    print("\n下一步:")
    print("1. cd project_management")
    print("2. 将你的代码复制到对应的模块中")
    print("3. python main.py 运行应用")
    
except Exception as e:
    print(f"❌ 创建过程中出现错误: {e}")
    sys.exit(1)