# 世界杯 ETL 数据表结构说明（对接文档）

> 数据库：Doris（MySQL 协议），库 `polymarket_data`，连接 `35.215.99.34:13214`。
> 写入程序：`rundown_etl.py`。所有表均为 **UNIQUE KEY upsert**：同一业务主键重复写不会涨行，只覆盖最新值。
> 数据源有两条：**Rundown API**（赛程/赔率/比分全量）与 **ESPN scoreboard**（免费比分 + 两家 provider 赔率）。两者写入同一批表，通过 `event_id` 对齐到同一行。

---

## 一、表清单与用途

| 表名 | 用途 | 写入子命令 |
|------|------|-----------|
| `wc_worldcup_schedule` | 赛程主表：每场比赛一行（队伍、场地、时间） | `daily` |
| `wc_worldcup_score`    | 比分表：随比赛进程刷新的比分/状态 | `daily` / `live`(ESPN) / `live-rundown` |
| `wc_worldcup_odds`     | 赔率表：各盘口各家 sportsbook 的报价 | `daily` / `live`(ESPN) / `live-rundown` / `live-rundown-odds` |
| `wc_worldcup_affiliate`| 博彩平台（sportsbook）字典表 | `affiliates` |

`event_id` 是贯穿四表的核心键（除 affiliate 表）。Rundown 与 ESPN 通过 `schedule.espn_uid` 映射，让 ESPN 比分写回与 Rundown 同一 `event_id`、同一行。

---

## 二、`wc_worldcup_schedule` 赛程主表

每场比赛一行。建议唯一键：`event_id`。

| 字段 | 类型建议 | 说明 |
|------|---------|------|
| `event_id` | VARCHAR | Rundown 赛事 ID，主键，贯穿各表 |
| `event_uuid` | VARCHAR | Rundown 赛事 UUID |
| `espn_uid` | VARCHAR | ESPN 赛事 UID，用于 ESPN↔Rundown 对齐（如 `s:600~l:...~e:数字id`） |
| `sport_id` | INT | 运动项目 ID，世界杯固定 18 |
| `event_date` | DATETIME | 开球时间（UTC，`YYYY-MM-DD HH:MM:SS`） |
| `season_type` | VARCHAR | 赛季阶段（如小组赛/淘汰赛标识，源串原样） |
| `season_year` | INT | 赛季年份 |
| `event_name` | VARCHAR | 赛事名称 |
| `conference_competition` | BOOL | 是否洲际/分区赛标识（源布尔） |
| `attendance` | INT | 观众人数，缺省 0 |
| `team_home_id` | INT | 主队 ID |
| `team_home_name` | VARCHAR | 主队名 |
| `team_home_abbr` | VARCHAR | 主队缩写 |
| `team_home_record` | VARCHAR | 主队战绩串（如 `2-1-0`） |
| `team_away_id` | INT | 客队 ID |
| `team_away_name` | VARCHAR | 客队名 |
| `team_away_abbr` | VARCHAR | 客队缩写 |
| `team_away_record` | VARCHAR | 客队战绩串 |
| `venue_name` | VARCHAR | 球场名 |
| `venue_location` | VARCHAR | 球场所在地（城市, 国家） |
| `broadcast` | VARCHAR | 转播方（逗号分隔多家） |
| `source_updated_at` | DATETIME | 源数据更新时间（UTC） |

---

## 三、`wc_worldcup_score` 比分表

随比赛进程高频刷新（ESPN 线赛时每 30s）。建议唯一键：`event_id`（每场一行，覆盖更新）。

| 字段 | 类型建议 | 说明 |
|------|---------|------|
| `event_id` | VARCHAR | 对齐 schedule，主键 |
| `sport_id` | INT | 固定 18 |
| `event_status` | VARCHAR | 比赛状态机读值，见下方状态说明 |
| `event_status_detail` | VARCHAR | 状态可读详情（如 `2nd Half`、比分牌文字） |
| `team_id_home` | INT | 主队 ID |
| `team_id_away` | INT | 客队 ID |
| `score_home` | INT | 主队得分，缺省 0 |
| `score_away` | INT | 客队得分，缺省 0 |
| `winner_home` | TINYINT | 主队是否胜：1=是 0=否 NULL=未定 |
| `winner_away` | TINYINT | 客队是否胜：1=是 0=否 NULL=未定 |
| `score_home_by_period` | VARCHAR/JSON | 主队各阶段比分，JSON 数组串（如 `[1,2]`） |
| `score_away_by_period` | VARCHAR/JSON | 客队各阶段比分，JSON 数组串 |
| `game_clock` | INT | 比赛进行秒数 |
| `display_clock` | VARCHAR | 可读比赛时钟（如 `45:00`、`90'+2`） |
| `game_period` | INT | 当前阶段编号（1=上半场 2=下半场…） |
| `venue_name` | VARCHAR | 球场名 |
| `venue_location` | VARCHAR | 球场所在地 |
| `broadcast` | VARCHAR | 转播方 |
| `score_updated_at` | DATETIME | 比分更新时间（UTC） |

### event_status 取值（重要，两条线口径不同）
状态名形如 `STATUS_SCHEDULED` / `STATUS_FIRST_HALF` / `STATUS_HALFTIME` / `STATUS_SECOND_HALF` / `STATUS_FULL_TIME` / `STATUS_FINAL` / `STATUS_CANCELED` / `STATUS_POSTPONED`。

- 未开打：`STATUS_SCHEDULED`
- 进行中：上半场/中场/下半场/加时等
- 已结束：`STATUS_FULL_TIME`（全场踢完）、`STATUS_FINAL`（最终）、加时/点球完赛、取消、延期
- **注意**：ESPN 比分线会把 `STATUS_FULL_TIME` 仍按“进行中”继续抓（为捕捉加时/点球/结算）；而 Rundown 赔率线把 `STATUS_FULL_TIME` 当“已结束”不再抓赔率。两条线对 FULL_TIME 的口径不同是有意为之。

---

## 四、`wc_worldcup_odds` 赔率表

行数最多的表。一行 = 某场某盘口某选项某家 sportsbook 的一个报价。
业务唯一键建议：`(event_id, market_id, period_id, participant_id, line_id, affiliate_id)`。

| 字段 | 类型建议 | 说明 |
|------|---------|------|
| `event_id` | VARCHAR | 对齐 schedule |
| `market_id` | INT | 盘口类型 ID，见下表 |
| `period_id` | INT | 时段：0=全场，半场盘口非 0 |
| `participant_id` | VARCHAR | 投注选项 ID：队伍盘=team_id；结果盘=固定编号（3=平局/Draw，9=Over，10=Under） |
| `line_id` | VARCHAR | 盘口线 ID。Rundown 为其哈希；ESPN 为合成串 `espn_*`（如 `espn_ml_h`），保证幂等覆盖且不撞 Rundown 行 |
| `affiliate_id` | INT | sportsbook ID，关联 affiliate 表。ESPN provider 映射：100→19，2000→27 |
| `market_name` | VARCHAR | 盘口名（如 moneyline/handicap/totals） |
| `participant_type` | VARCHAR | 选项类型：`TYPE_TEAM`（队伍）/ `TYPE_RESULT`（平局、大小球等） |
| `participant_name` | VARCHAR | 选项名（队名 / Draw / Over / Under） |
| `line_value` | VARCHAR | 盘口值：让球的让分（如 `-0.5`）、大小球的盘线（如 `2.5`）；胜平负为 NULL |
| `price_id` | VARCHAR | Rundown 报价 ID；ESPN 无此值为 NULL |
| `price` | DECIMAL | 赔率值（美式赔率，如 `-150` / `+200`） |
| `price_delta` | DECIMAL | 相对上次的赔率变动；ESPN 无此值为 NULL |
| `is_main_line` | BOOL | 是否主线盘 |
| `price_updated_at` | DATETIME | 报价更新时间（UTC） |
| `closed_at` | DATETIME | 盘口封盘时间（UTC），未封为 NULL |

### market_id 盘口对照（世界杯实测有报价的）
全场：1 胜平负 / 2 让球 / 3 总进球 / 9 净胜球区间 / 36 总进球数 / 330 平局退款 / 331 双重机会 / 333 比分组合 / 335 具体比分 / 342 胜负+双方进球 / 343 半场结果 / 405 首位进球者 / 410 任意进球者
半场：4 胜平负 / 5 让球 / 6 总进球 / 358 大小1.5 / 366 大小2.5 / 368 大小0.5 / 377 大小3.5

> ESPN 赔率线只稳定产出全场三类（period_id=0）：1 胜平负、2 让球、3 大小球。
> Rundown 赔率线只保留 `affiliate_id ∈ {22, 23}`（可配置），赛时档拉全盘口、未来档只拉主盘 1/2/3。

---

## 五、`wc_worldcup_affiliate` 博彩平台字典

| 字段 | 类型建议 | 说明 |
|------|---------|------|
| `affiliate_id` | INT | sportsbook ID，主键，被 odds.affiliate_id 引用 |
| `affiliate_name` | VARCHAR | 平台名 |
| `affiliate_url` | VARCHAR | 平台链接 |
| `status` | VARCHAR | 状态 |

---

## 六、对接注意事项

1. **时间统一 UTC**：所有 `*_at`、`event_date` 均为 UTC，`YYYY-MM-DD HH:MM:SS`。Rundown 按 `DATE_OFFSET`（默认 300 分钟，美中部）划分“日期桶”，按日期查询时注意凌晨开球的比赛可能落在前一天桶。
2. **upsert 语义**：四表都靠 UNIQUE KEY 去重，读取方拿到的是每个业务键的最新值，不是时序流水。如需历史赔率走势，需在写入侧改为追加或另建时序表（当前不保留历史）。
3. **比分与赔率来源分离**：比分主要由免费 ESPN 线写；赔率有 Rundown（22/23 两家全盘口）和 ESPN（19/27 两家三盘口）两路，靠 `event_id` 汇到同表。
4. **score by_period 是 JSON 串**：`score_home_by_period` / `score_away_by_period` 存的是 JSON 数组字符串，读取需 parse。
5. **NULL 含义**：`winner_*` NULL=胜负未定；`line_value` NULL=该盘口无盘线（如纯胜平负）；`closed_at` NULL=未封盘。
