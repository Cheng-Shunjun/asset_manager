# auto_import_qualifications.py
import os
import sqlite3
import re

def auto_import_qualifications(db_path='db.sqlite3'):
    """自动扫描证书目录并导入到数据库（先删除所有现有数据）"""
    
    # 证书目录
    upload_dir = "./static/uploads/company_qualifications/"
    
    # 连接到数据库
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    try:
        # 检查目录是否存在
        if not os.path.exists(upload_dir):
            print(f"错误: 目录 {upload_dir} 不存在")
            return
        
        # 获取目录中的所有文件
        files = [f for f in os.listdir(upload_dir) if os.path.isfile(os.path.join(upload_dir, f))]
        
        if not files:
            print("目录中没有找到文件")
            return
        
        print(f"在 {upload_dir} 中找到 {len(files)} 个文件")
        
        # 1. 先删除所有现有数据
        c.execute("DELETE FROM company_qualifications")
        deleted_count = c.rowcount
        print(f"已删除 {deleted_count} 条现有记录")
        
        # 2. 导入新数据
        imported_count = 0
        skipped_count = 0
        
        for filename in files:
            # 只处理常见的证书文件格式
            if not filename.lower().endswith(('.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png')):
                print(f"跳过不支持的文件格式: {filename}")
                skipped_count += 1
                continue
            
            file_path = os.path.join(upload_dir, filename)
            
            # 根据文件名解析证书信息
            certificate_info = parse_certificate_info(filename)
            
            if certificate_info:
                # 插入数据库
                c.execute("""
                    INSERT INTO company_qualifications 
                    (certificate_name, category, owner, file_path, file_name, uploader_username)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    certificate_info['certificate_name'],
                    certificate_info['category'],
                    certificate_info['owner'],
                    file_path,
                    filename,
                    'admin'
                ))
                
                print(f"✓ 导入: {certificate_info['certificate_name']} ({certificate_info['category']})")
                imported_count += 1
            else:
                print(f"✗ 无法解析文件名: {filename}")
                skipped_count += 1
        
        # 提交事务
        conn.commit()
        
        print(f"\n导入完成!")
        print(f"删除旧资质记录: {deleted_count} 条")
        print(f"成功导入: {imported_count} 个新资质文件")
        print(f"跳过: {skipped_count} 个资质文件")
        
    except Exception as e:
        print(f"导入过程中发生错误: {e}")
        conn.rollback()
    finally:
        conn.close()

def parse_certificate_info(filename):
    """根据文件名解析证书信息"""
    
    # 首先检查是否包含"营业执照"
    if '营业执照' in filename:
        return {
            'certificate_name': '公司营业执照',
            'category': '营业执照',
            'owner': '公司法人'
        }
    
    # 移除文件扩展名
    name_without_ext = os.path.splitext(filename)[0]
    
    # 定义其他匹配规则
    patterns = [
        (r'^(资产评估师证书)_(.+)$', '资产评估师'),
        (r'^(房地产估价师证书)_(.+)$', '房地产估价师'),
        (r'^(土地估价师证书)_(.+)$', '土地估价师'),
        (r'^(.+)_(资产评估师证书)$', '资产评估师'),
        (r'^(.+)_(房地产估价师证书)$', '房地产估价师'),
        (r'^(.+)_(土地估价师证书)$', '土地估价师'),
    ]
    
    for pattern, category in patterns:
        match = re.match(pattern, name_without_ext)
        if match:
            name = match.group(2) if pattern.startswith('^(.+)_') else match.group(2)
            return {
                'certificate_name': f'{category}证书 - {name}',
                'category': category,
                'owner': name
            }
    
    # 如果无法匹配任何模式，使用默认处理
    return {
        'certificate_name': f'资质证书 - {name_without_ext}',
        'category': '其他',
        'owner': '公司'
    }

if __name__ == "__main__":
    auto_import_qualifications()