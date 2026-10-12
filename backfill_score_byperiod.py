# -*- coding: utf-8 -*-
"""
一次性回填: 用 Rundown events 的 score 覆盖 soccer_eu_score。
Rundown 的 score 带各阶段比分数组, 按 event_id upsert 覆盖同一行即可补齐。

只写 score 表, 不碰 odds(不按全盘口拉, 不烧赔率配额)。
用法:
  python backfill_score_byperiod.py                # 自动扫描有比赛的日期
  python backfill_score_byperiod.py 2026-06-25 ... # 只回填指定日期
"""
import sys
import datetime as dt

import config
from rundown_etl import api_get, parse_event, batch_upsert, SQL_SCORE, DB, log


def scan_dates(sport_id, start="2026-06-11", end="2026-07-19"):
    """扫描区间内每天, 返回有 events 的日期。"""
    s = dt.date.fromisoformat(start)
    e = dt.date.fromisoformat(end)
    out = []
    d = s
    while d <= e:
        ds = d.isoformat()
        try:
            data = api_get(f"/sports/{sport_id}/events/{ds}",
                           params={"offset": config.DATE_OFFSET})
            if data.get("events"):
                out.append(ds)
        except Exception as ex:
            log(f"  扫描 {ds} 失败: {ex}")
        d += dt.timedelta(days=1)
    return out


def backfill_one(conn, sport_id, date_str):
    # market_ids=[] -> 单次请求, 只回默认全场盘口, 我们只取 score, 不写 odds
    data = api_get(f"/sports/{sport_id}/events/{date_str}",
                   params={"offset": config.DATE_OFFSET})
    events = data.get("events") or []
    score_rows = []
    filled = 0
    for ev in events:
        _, sc = parse_event(ev)
        score_rows.append(sc)
        # sc[10]/sc[11] 是 by_period 的 JSON 串(见 parse_event 顺序)
        if sc[10] not in (None, "null") or sc[11] not in (None, "null"):
            filled += 1
    batch_upsert(conn, SQL_SCORE, score_rows, f"sport_id={sport_id} {date_str} score")
    log(f"  sport_id={sport_id} {date_str}: {len(events)} 场, 其中 {filled} 场含 by_period")
    return len(events), filled


def main():
    conn = DB()
    total_ev = total_filled = 0
    try:
        # 旧世界杯/足球回填脚本只处理足球，避免把 NFL/NBA 写进足球比分表。
        for sport_id in (sport for sport in config.SPORT_IDS if sport not in (2, 4)):
            dates = sys.argv[1:] or scan_dates(sport_id)
            log(f"sport_id={sport_id} 待回填日期 {len(dates)} 个: {dates[0]} ... {dates[-1]}"
                if dates else f"sport_id={sport_id} 无日期")
            for d in dates:
                n, f = backfill_one(conn, sport_id, d)
                total_ev += n
                total_filled += f
    finally:
        conn.close()
    log(f"完成: 共 {total_ev} 场写回, {total_filled} 场带各阶段比分数组。")


if __name__ == "__main__":
    main()
