"""依赖声明完整性检查。

起因：镜像里后端启动连续失败三次，原因都是「本地 venv 被别的包间接装上了、
但 requirements.txt 没写」——greenlet、requests、python-multipart。
本地跑 uvicorn 永远发现不了，只有干净镜像会暴露，所以这条检查必须常驻。

局限也要说清楚：静态 import 差集抓不到 FastAPI 的隐式可选依赖（python-multipart
是我们构建路由时才发现的），所以下面除了差集，还把已知的隐式项逐个钉死。
"""
import ast
import pathlib
import re
import sys

SERVER = pathlib.Path(__file__).resolve().parents[1]
APP_DIR = SERVER / "app"
# kb/ 也得扫：retriever 用 pymilvus、candidates 用 requests，都发生在后端启动链路上。
# 只扫 app/ 时这些依赖看不见，才逼得下面把 requests 手工钉死。
KB_DIR = SERVER / "kb"
REQ_TEXT = (SERVER / "requirements.txt").read_text(encoding="utf-8")

# import 名与 pip 包名不一致的情况
MODULE_TO_PKG = {"jwt": "PyJWT", "pydantic_settings": "pydantic-settings",
                 "langchain_core": "langchain-core", "langchain_openai": "langchain-openai"}

# utils/sms.py 里包在 try/except ImportError 中，属于可选云厂商 SDK，不声明也能启动
OPTIONAL_MODULES = {"alibabacloud_dysmsapi20170525", "alibabacloud_tea_openapi"}

LOCAL_PACKAGES = {"app", "kb", "config", "models", "schemas", "database", "deps",
                  "routers", "services", "utils", "ai"}


def _declared_packages() -> set:
    out = set()
    for line in REQ_TEXT.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"^([A-Za-z0-9_.\-]+)", line)
        if m:
            out.add(m.group(1).lower())
    return out


def _imported_modules() -> set:
    mods = set()
    for d in (APP_DIR, KB_DIR):
        for f in d.rglob("*.py"):
            try:
                tree = ast.parse(f.read_text(encoding="utf-8"))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for a in node.names:
                        mods.add(a.name.split(".")[0])
                elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                    mods.add(node.module.split(".")[0])
    stdlib = set(sys.stdlib_module_names)
    return {m for m in mods if m not in stdlib and m not in LOCAL_PACKAGES and not m.startswith("_")}


def test_代码里import的第三方包都必须在requirements里声明():
    declared = _declared_packages()
    missing = []
    for mod in sorted(_imported_modules()):
        if mod in OPTIONAL_MODULES:
            continue
        pkg = MODULE_TO_PKG.get(mod, mod)
        if pkg.lower() not in declared:
            missing.append(f"{mod} → {pkg}")
    assert not missing, (
        f"以下依赖代码在用但没声明，镜像里会 ModuleNotFoundError / ImportError：{missing}。"
        "本地 venv 里可能是被别的包间接装上的，所以本地跑得通不代表镜像跑得通。"
    )


def test_隐式依赖必须显式列出():
    """这三项不是我们代码里 import 的，静态检查抓不到，只能钉死。"""
    declared = _declared_packages()
    assert "requests" in declared, "image_service/route_service/kb.candidates 用 requests 调高德"
    assert "python-multipart" in declared, "头像上传用 UploadFile，FastAPI 运行时强制要求"


def test_sqlalchemy必须带asyncio_extra():
    """裸 sqlalchemy 不带 greenlet，SQLAlchemy 的 asyncio 模块导入即报错。"""
    assert re.search(r"(?m)^sqlalchemy\[asyncio\]", REQ_TEXT), (
        "必须写 sqlalchemy[asyncio]，否则镜像里 from sqlalchemy.ext.asyncio import ... 直接 ImportError"
    )


def test_不引入未使用的依赖():
    """requirements 里声明了但代码没用的包，会让镜像构建变慢、漏洞面变大。"""
    used = {MODULE_TO_PKG.get(m, m).lower() for m in _imported_modules()}
    # 下面几项 app/ 不会直接 import，但确实必需：
    #   uvicorn 是启动命令；python-multipart 由 FastAPI 运行时要求；
    #   aiomysql / aiosqlite 通过数据库 URL 字符串（mysql+aiomysql://）被 SQLAlchemy 加载
    used |= {"uvicorn", "python-multipart", "aiomysql", "aiosqlite"}
    unused = sorted(p for p in _declared_packages() if p not in used)
    assert not unused, f"requirements 里声明了但全项目没用到：{unused}"
