# -*- coding: utf-8 -*-
"""
连接与运行配置。可被环境变量覆盖，方便生产部署时不落明文。
同目录下若有 .env 文件会自动加载(需安装 python-dotenv)。
"""
import os

# 自动加载同目录 .env(未安装 python-dotenv 时静默跳过, 仍走系统环境变量)
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
except ImportError:
    pass

# ---- Rundown API ----
RUNDOWN_API_KEY = os.getenv("RUNDOWN_API_KEY", "")
RUNDOWN_BASE = os.getenv("RUNDOWN_BASE", "https://therundown.io/api/v2")
# 五大联赛 (11-15)、NFL (2)、NBA (4)。
SPORT_IDS = tuple(
    int(x) for x in os.getenv("RUNDOWN_SPORT_IDS", "11,12,13,14,15,2,4").split(",")
    if str(x).strip()
)
if not SPORT_IDS:
    raise ValueError("RUNDOWN_SPORT_IDS 至少需要包含一个 sport_id")
# 供旧的单赛事辅助脚本兼容；主程序仅使用 SPORT_IDS。
SPORT_ID = SPORT_IDS[0]
DATE_OFFSET = os.getenv("RUNDOWN_OFFSET", "300")       # 日期边界偏移(分钟), 300=美中部

# ---- Doris (MySQL 协议) ----
DORIS = {
    "host": os.getenv("DORIS_HOST", os.getenv("MYSQL_HOST", "35.215.99.34")),
    "port": int(os.getenv("DORIS_PORT", os.getenv("MYSQL_PORT", "13214"))),
    "user": os.getenv("DORIS_USER", os.getenv("MYSQL_USER", "tele")),
    "password": os.getenv("DORIS_PASSWORD", os.getenv("MYSQL_PASSWORD", "")),
    "database": os.getenv("DORIS_DB", os.getenv("MYSQL_DB", "polymarket_data")),
    "charset": "utf8mb4",
}

# ---- 调度 ----
SCORE_INTERVAL = int(os.getenv("SCORE_INTERVAL", "60"))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "200"))
# NFL 比赛可能持续超过四小时，统一给赛时六小时窗口。
LIVE_WINDOW_MINUTES = int(os.getenv("LIVE_WINDOW_MINUTES", "360"))
DAILY_TIMEZONE = os.getenv("DAILY_TIMEZONE", "Asia/Shanghai")
