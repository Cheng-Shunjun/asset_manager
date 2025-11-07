from fastapi import HTTPException
from fastapi.responses import RedirectResponse
import os
from utils.helpers import secure_filename

class FileService:
    async def add_contract_files(self, project_id, contract_files, user, db):
        """添加合同文件（支持多文件）"""
        try:
            # 检查项目状态
            c = db.cursor()
            c.execute("SELECT status FROM projects WHERE id = ?", (project_id,))
            result = c.fetchone()
            
            if not result:
                raise HTTPException(status_code=404, detail="项目不存在")
            
            status = result[0]
            if status in ['completed', 'paused', 'cancelled']:
                raise HTTPException(status_code=400, detail=f"项目状态为{status}，无法添加文件")
            
            # 保存文件
            contract_paths = []
            for contract_file in contract_files:
                if contract_file.filename:
                    contract_filename = secure_filename(contract_file.filename)
                    contract_path = os.path.join('static/uploads', contract_filename)
                    with open(contract_path, "wb") as f:
                        content = await contract_file.read()
                        f.write(content)
                    contract_paths.append(contract_path)
            
            if contract_paths:
                # 获取现有的合同文件
                c.execute("SELECT contract_file FROM projects WHERE id = ?", (project_id,))
                result = c.fetchone()
                existing_files = result[0] if result and result[0] else ""
                
                # 更新数据库
                if existing_files:
                    new_files = existing_files + "," + ",".join(contract_paths)
                else:
                    new_files = ",".join(contract_paths)
                
                c.execute("UPDATE projects SET contract_file = ? WHERE id = ?", (new_files, project_id))
                db.commit()
            
            return RedirectResponse(url=f"/project/{project_id}", status_code=303)
            
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"添加合同文件失败: {str(e)}")

    async def delete_file(self, file_path: str, db):
        """删除文件"""
        try:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
                return True
            return False
        except Exception as e:
            print(f"删除文件失败 {file_path}: {e}")
            return False

    async def get_file_info(self, file_path: str):
        """获取文件信息"""
        try:
            if os.path.exists(file_path):
                file_stats = os.stat(file_path)
                return {
                    "size": file_stats.st_size,
                    "created_time": file_stats.st_ctime,
                    "modified_time": file_stats.st_mtime
                }
            return None
        except Exception as e:
            print(f"获取文件信息失败 {file_path}: {e}")
            return None

    async def validate_file_type(self, filename: str, allowed_extensions: set):
        """验证文件类型"""
        if not filename:
            return False
        
        file_ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
        return file_ext in allowed_extensions

    async def validate_file_size(self, file_content: bytes, max_size_mb: int = 10):
        """验证文件大小"""
        max_size_bytes = max_size_mb * 1024 * 1024  # 转换为字节
        return len(file_content) <= max_size_bytes

    async def save_uploaded_file(self, file, upload_dir: str = 'static/uploads'):
        """保存上传的文件"""
        try:
            if not file.filename:
                return None
            
            # 确保上传目录存在
            os.makedirs(upload_dir, exist_ok=True)
            
            # 生成安全的文件名
            safe_filename = secure_filename(file.filename)
            file_path = os.path.join(upload_dir, safe_filename)
            
            # 保存文件
            content = await file.read()
            with open(file_path, "wb") as f:
                f.write(content)
            
            return file_path
            
        except Exception as e:
            print(f"保存文件失败: {e}")
            return None

    async def cleanup_orphaned_files(self, db):
        """清理孤立的文件（没有数据库记录的文件）"""
        try:
            c = db.cursor()
            
            # 获取所有在数据库中记录的文件路径
            c.execute("SELECT contract_file FROM projects WHERE contract_file IS NOT NULL AND contract_file != ''")
            project_files = []
            for row in c.fetchall():
                if row[0]:
                    project_files.extend([f.strip() for f in row[0].split(',') if f.strip()])
            
            c.execute("SELECT file_path FROM report_files")
            report_files = [row[0] for row in c.fetchall() if row[0]]
            
            # 合并所有数据库中的文件路径
            db_files = set(project_files + report_files)
            
            # 获取上传目录中的所有文件
            upload_dir = 'static/uploads'
            if not os.path.exists(upload_dir):
                return
            
            all_files = set()
            for root, dirs, files in os.walk(upload_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    all_files.add(file_path)
            
            # 找出孤立的文件（在文件系统中但不在数据库中）
            orphaned_files = all_files - db_files
            
            # 删除孤立的文件
            deleted_count = 0
            for file_path in orphaned_files:
                try:
                    os.remove(file_path)
                    deleted_count += 1
                    print(f"🗑️ 删除孤立文件: {file_path}")
                except Exception as e:
                    print(f"⚠️ 删除孤立文件失败 {file_path}: {e}")
            
            print(f"🧹 清理完成，删除了 {deleted_count} 个孤立文件")
            return deleted_count
            
        except Exception as e:
            print(f"清理孤立文件失败: {e}")
            return 0