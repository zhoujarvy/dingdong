"""通用工具：时间、编码与令牌生成。"""
import secrets
from datetime import datetime, timedelta

# 6 位终端编码字符集：大写字母 + 数字，去掉易混淆的 0/O/1/I
CODE_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
CODE_LENGTH = 6


def now_str() -> str:
    """当前本地时间，格式 YYYY-MM-DD HH:MM:SS"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def gen_terminal_code() -> str:
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))


def gen_api_key() -> str:
    return "dd_" + secrets.token_hex(16)


def gen_access_token() -> str:
    return secrets.token_hex(16)


def gen_admin_token() -> str:
    return secrets.token_hex(24)


def days_ago_str(days: int) -> str:
    return (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")


def today_start_str() -> str:
    return datetime.now().strftime("%Y-%m-%d") + " 00:00:00"
