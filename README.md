# Rundown 赛程与比分 ETL

支持五大联赛（sport_id 11–15）、NFL（2）和 NBA（4）。只写赛程与比分；不会写入赔率表。

## 准备

需要 Python 3.9+ 和 Doris 数据库访问权限。首次配置时将 `.env.example` 复制为 `.env`，填入 key 和数据库连接；已有 `.env` 时不要覆盖。

```bash
./run.sh setup
```

新环境先在 `polymarket_data` 执行 `create_sports_tables.sql`，创建 NFL/NBA 的赛程与比分表。现有 prod 环境已建好。

## 启动与调度

```bash
./run.sh start   # 后台常驻：每天一次未来七天赛程；赛时每 60 秒比分
./run.sh status
./run.sh stop
```

启动后立即执行当天的赛程任务；同一个上海自然日重启不会重复执行。完成日期记录在 `.state/last_daily_date`。每日任务失败会每 15 分钟重试。比分轮询只针对赛程表中已开球、未终结且处于六小时窗口内的比赛；没有符合条件的比赛时不请求 Rundown。API 按日期返回赛事，因此同一天的多场比赛共用一次请求，落库时只保留目标比赛。

单次手动执行：

```bash
./run.sh daily              # 从当前时刻起未来 7×24 小时
./run.sh daily 2026-10-12   # 指定一个 Rundown API 日期
./.venv/bin/python rundown_etl.py daily --sport-id 2 --sport-id 4
./run.sh live --once        # 只轮询当前赛时比赛一次
```

服务器 systemd 模板为 `worldcup-live.service`，其 `ExecStart` 使用 `serve` 命令。部署更新后需要重新安装服务文件并重启服务才能应用新调度。
