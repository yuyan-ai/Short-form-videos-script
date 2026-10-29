"""读取本地环境配置，不输出密钥。"""
import os
from pathlib import Path
from urllib.parse import urlsplit
from dataclasses import dataclass, field

def load_env(path):
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition("=")
        if not sep:
            raise ValueError(".env格式错误：每行应为NAME=value")
        os.environ.setdefault(key.strip(), value.strip().strip(chr(34)).strip(chr(39)))
@dataclass
class ModelConfig:
    api_key: str = field(repr=False)
    base_url: str
    model: str
    timeout: float = 45
    @classmethod
    def from_env(cls, path):
        load_env(path)
        values = [os.getenv(k, "").strip() for k in ("LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL")]
        if not all(values) or values[0] == "replace-me":
            raise ValueError("请在项目根目录.env填写LLM_API_KEY、LLM_BASE_URL、LLM_MODEL")
        url = urlsplit(values[1])
        if url.scheme != "https" or not url.hostname or url.username or url.password or url.query or url.fragment:
            raise ValueError("LLM_BASE_URL必须是无凭证或查询参数的HTTPS地址")
        timeout = float(os.getenv("LLM_TIMEOUT_SECONDS", "45"))
        if not 1 <= timeout <= 120:
            raise ValueError("超时须为1到120秒")
        return cls(*values, timeout)
