import os

def secure_filename(filename: str) -> str:
    """安全的文件名"""
    if not filename:
        return ""
    return "".join(c for c in filename if c.isalnum() or c in ".-_ ").rstrip()

def get_file_extension(filename: str) -> str:
    """获取文件扩展名"""
    if not filename or '.' not in filename:
        return ""
    return filename.rsplit('.', 1)[-1].lower()

def format_file_size(size_bytes: int) -> str:
    """格式化文件大小"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.2f} {size_names[i]}"

def is_allowed_file(filename: str, allowed_extensions: set) -> bool:
    """检查文件类型是否允许"""
    if not filename:
        return False
    return get_file_extension(filename) in allowed_extensions