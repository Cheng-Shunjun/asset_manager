"""密码安全工具模块

使用标准库 PBKDF2-SHA256 进行密码哈希,无第三方依赖。
哈希格式: pbkdf2_sha256$<iterations>$<salt_hex>$<hash_hex>
"""
import hashlib
import hmac
import secrets

ITERATIONS = 260_000
ALGORITHM = "pbkdf2_sha256"


def hash_password(password: str) -> str:
    """对明文密码进行哈希,返回可存储的字符串"""
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
    return f"{ALGORITHM}${ITERATIONS}${salt.hex()}${digest.hex()}"


def _pbkdf2(password: str, salt: bytes, iterations: int) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)


def verify_password(password: str, stored: str) -> bool:
    """校验明文密码与存储的哈希是否匹配(使用恒定时间比较)"""
    if not stored:
        return False

    parts = stored.split("$")
    if len(parts) == 4 and parts[0] == ALGORITHM:
        try:
            iterations = int(parts[1])
            salt = bytes.fromhex(parts[2])
            expected = bytes.fromhex(parts[3])
        except ValueError:
            return False
        actual = _pbkdf2(password, salt, iterations)
        return hmac.compare_digest(actual, expected)

    # 兼容旧版明文存储(登录成功后由调用方升级为哈希)
    return hmac.compare_digest(password.encode("utf-8"), stored.encode("utf-8"))


def is_hashed(stored: str) -> bool:
    """判断存储值是否已经是哈希格式"""
    parts = stored.split("$") if stored else []
    return len(parts) == 4 and parts[0] == ALGORITHM
