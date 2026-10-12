# -*- coding: utf-8 -*-
"""Rundown 赛程与比分 ETL。所有时间写入 Doris 时均为 UTC。"""
import argparse
import datetime as dt
import json
import os
import threading
import time
from zoneinfo import ZoneInfo

import pymysql
import requests

import config

TABLES = {
    2: ("nfl_schedule", "nfl_score"),
    4: ("nba_schedule", "nba_score"),
}
TERMINAL_STATUSES = {
    "STATUS_FINAL", "STATUS_FULL_TIME", "STATUS_FINAL_AET", "STATUS_FINAL_PEN",
    "STATUS_CANCELED", "STATUS_POSTPONED", "STATUS_ABANDONED", "STATUS_FORFEIT",
}
TERMINAL_PARTS = ("FINAL", "FULL_TIME", "AET", "PEN", "CANCEL", "POSTPON", "ABANDON", "FORFEIT")
SCHEDULE_COLUMNS = (
    "event_id,event_uuid,espn_uid,sport_id,event_date,season_type,season_year,"
    "event_name,conference_competition,attendance,team_home_id,team_home_name,"
    "team_home_abbr,team_home_record,team_away_id,team_away_name,team_away_abbr,"
    "team_away_record,venue_name,venue_location,broadcast,source_updated_at"
)
SCORE_COLUMNS = (
    "event_id,sport_id,event_status,event_status_detail,team_id_home,team_id_away,"
    "score_home,score_away,winner_home,winner_away,score_home_by_period,"
    "score_away_by_period,game_clock,display_clock,game_period,venue_name,"
    "venue_location,broadcast,score_updated_at"
)


def log(message):
    print(f"[{dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}", flush=True)


def table_pair(sport_id):
    if sport_id in TABLES:
        return TABLES[sport_id]
    if sport_id in config.SPORT_IDS:
        return "soccer_eu_schedule", "soccer_eu_score"
    raise ValueError(f"未配置 sport_id={sport_id} 的目标表")


def api_get(path, params=None, retries=3, timeout=40):
    url = config.RUNDOWN_BASE.rstrip("/") + path
    for attempt in range(1, retries + 1):
        try:
            response = requests.get(url, headers={"X-TheRundown-Key": config.RUNDOWN_API_KEY},
                                    params=params or {}, timeout=timeout)
            if response.status_code == 200:
                return response.json()
            if response.status_code not in (429, 500, 502, 503, 504):
                raise RuntimeError(f"GET {path} -> {response.status_code}: {response.text[:160]}")
            error = f"HTTP {response.status_code}"
        except requests.RequestException as exc:
            error = str(exc)
        if attempt < retries:
            wait = min(2 ** attempt, 30)
            log(f"  {path} {error}，{wait}s 后重试({attempt}/{retries})")
            time.sleep(wait)
    raise RuntimeError(f"GET {path} 失败: {error}")


class DB:
    def __init__(self):
        self.conn = None
        self.connect()

    def connect(self, retries=6):
        last = None
        for attempt in range(retries):
            try:
                self.conn = pymysql.connect(**config.DORIS, autocommit=True, connect_timeout=15,
                                            read_timeout=90, write_timeout=90)
                return
            except pymysql.err.MySQLError as exc:
                last = exc
                if attempt < retries - 1:
                    time.sleep(min(2 ** attempt, 20))
        raise RuntimeError(f"无法连接 Doris: {last}")

    def execute_many(self, sql, rows):
        for attempt in range(3):
            try:
                with self.conn.cursor() as cur:
                    cur.executemany(sql, rows)
                return
            except (pymysql.err.OperationalError, pymysql.err.InterfaceError):
                if attempt == 2:
                    raise
                log(f"  Doris 写入断连，重连重试({attempt + 1}/3)")
                self.connect()

    def query(self, sql, params=None):
        for attempt in range(3):
            try:
                with self.conn.cursor() as cur:
                    cur.execute(sql, params)
                    return cur.fetchall()
            except (pymysql.err.OperationalError, pymysql.err.InterfaceError):
                if attempt == 2:
                    raise
                log(f"  Doris 查询断连，重连重试({attempt + 1}/3)")
                self.connect()

    def close(self):
        if self.conn:
            self.conn.close()


def to_dt(value):
    if not value:
        return None
    if isinstance(value, dt.datetime):
        if value.tzinfo is None:
            return value.strftime("%Y-%m-%d %H:%M:%S")
        return value.astimezone(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    try:
        value = str(value).replace("Z", "+00:00")
        parsed = dt.datetime.fromisoformat(value)
        if parsed.tzinfo:
            parsed = parsed.astimezone(dt.timezone.utc)
        return parsed.strftime("%Y-%m-%d %H:%M:%S")
    except (TypeError, ValueError):
        try:
            parsed = dt.datetime.strptime(value, "%Y-%m-%dT%H:%M:%S%z")
            return parsed.astimezone(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        except (TypeError, ValueError):
            return None


def to_int(value, default=None):
    try:
        return int(float(value)) if value is not None and value != "" else default
    except (TypeError, ValueError):
        return default


def parse_event(event):
    """只解析赛程和比分，不读取 markets、lines 或 sportsbook。"""
    home, away = {}, {}
    for team in event.get("teams_normalized") or event.get("teams") or []:
        if team.get("is_home"):
            home = team
        elif team.get("is_away"):
            away = team
    schedule = event.get("schedule") or {}
    score = event.get("score") or {}
    event_id = event.get("event_id")
    schedule_row = (
        event_id, event.get("event_uuid"), event.get("espn_uid"), to_int(event.get("sport_id")),
        to_dt(event.get("event_date")), schedule.get("season_type"),
        to_int(schedule.get("season_year")), schedule.get("event_name"),
        bool(schedule.get("conference_competition")), to_int(schedule.get("attendance"), 0),
        to_int(home.get("team_id")), home.get("name"), home.get("abbreviation"), home.get("record"),
        to_int(away.get("team_id")), away.get("name"), away.get("abbreviation"), away.get("record"),
        score.get("venue_name"), score.get("venue_location"), score.get("broadcast"),
        to_dt(score.get("updated_at")),
    )
    score_row = (
        event_id, to_int(event.get("sport_id")), score.get("event_status"),
        score.get("event_status_detail"), to_int(score.get("team_id_home")),
        to_int(score.get("team_id_away")), to_int(score.get("score_home"), 0),
        to_int(score.get("score_away"), 0), to_int(score.get("winner_home")),
        to_int(score.get("winner_away")),
        json.dumps(score.get("score_home_by_period")) if score.get("score_home_by_period") is not None else None,
        json.dumps(score.get("score_away_by_period")) if score.get("score_away_by_period") is not None else None,
        to_int(score.get("game_clock")), score.get("display_clock"), to_int(score.get("game_period")),
        score.get("venue_name"), score.get("venue_location"), score.get("broadcast"),
        to_dt(score.get("updated_at")),
    )
    return schedule_row, score_row


def insert_sql(table, columns):
    # table 只由固定映射生成；列名由本文件常量生成。
    names = columns.split(",")
    return f"INSERT INTO {table} ({columns}) VALUES ({','.join(['%s'] * len(names))})"


SQL_SCORE = insert_sql("soccer_eu_score", SCORE_COLUMNS)


def batch_upsert(conn, sql, rows, label):
    for start in range(0, len(rows), config.BATCH_SIZE):
        conn.execute_many(sql, rows[start:start + config.BATCH_SIZE])
    log(f"  {label}: 写入 {len(rows)} 行")
    return len(rows)


def fetch_events(sport_id, date_str):
    data = api_get(f"/sports/{sport_id}/events/{date_str}", params={"offset": config.DATE_OFFSET})
    events = data.get("events") or []
    if not isinstance(events, list):
        raise ValueError(f"sport_id={sport_id} {date_str} 的 events 字段不是列表")
    return events


def api_date(moment):
    return (moment.astimezone(dt.timezone.utc) - dt.timedelta(minutes=int(config.DATE_OFFSET))).date()


def future_dates(now=None):
    """覆盖从当前时刻起未来 7×24 小时；两端 API 日期均包含。"""
    now = now or dt.datetime.now(dt.timezone.utc)
    first = api_date(now)
    last = api_date(now + dt.timedelta(days=7))
    return [(first + dt.timedelta(days=n)).isoformat() for n in range((last - first).days + 1)]


def ingest_one_date(conn, sport_id, date_str, now=None, horizon=None):
    schedule_table, score_table = table_pair(sport_id)
    events = fetch_events(sport_id, date_str)
    schedules, scores = [], []
    for event in events:
        if not event.get("event_id"):
            continue
        when = to_dt(event.get("event_date"))
        if not when:
            continue
        kickoff = dt.datetime.strptime(when, "%Y-%m-%d %H:%M:%S").replace(tzinfo=dt.timezone.utc)
        if now and (kickoff < now or kickoff > horizon):
            continue
        schedule, score = parse_event(event)
        schedules.append(schedule)
        scores.append(score)
    batch_upsert(conn, insert_sql(schedule_table, SCHEDULE_COLUMNS), schedules,
                 f"{schedule_table} {date_str}")
    batch_upsert(conn, insert_sql(score_table, SCORE_COLUMNS), scores,
                 f"{score_table} {date_str}")
    return len(schedules)


def cmd_daily(conn, date=None, sport_ids=None):
    now = dt.datetime.now(dt.timezone.utc)
    window_dates = set(future_dates(now))
    horizon = now + dt.timedelta(days=7)
    total = 0
    sports = sport_ids or config.SPORT_IDS
    for sport_id in sports:
        if date:
            dates = [date]
        else:
            available = api_get(f"/sports/{sport_id}/dates").get("dates") or []
            candidate_dates = set()
            for value in available:
                parsed = to_dt(value)
                if parsed:
                    kickoff = dt.datetime.strptime(parsed, "%Y-%m-%d %H:%M:%S").replace(
                        tzinfo=dt.timezone.utc)
                    # /dates 可能只列一个 UTC 日期代表时间；凌晨与晚间比赛可能
                    # 分属两个 Rundown API 日期桶，因此两个桶都检查。
                    candidate_dates.add(api_date(kickoff).isoformat())
                    candidate_dates.add(kickoff.date().isoformat())
            dates = sorted(candidate_dates & window_dates)
        log(f"sport_id={sport_id}: 未来一周有比赛的 API 日期 {dates}")
        for day in dates:
            total += ingest_one_date(conn, sport_id, day, None if date else now,
                                     None if date else horizon)
    log(f"每日赛程完成: {len(sports)} 个 sport_id、{total} 场")


def terminal(status):
    return bool(status and (status in TERMINAL_STATUSES or any(p in status for p in TERMINAL_PARTS)))


def live_candidates(conn, now=None):
    """按已录入赛程开球时间找比赛；完赛后停止请求该比赛。"""
    now = now or dt.datetime.now(dt.timezone.utc)
    start = now - dt.timedelta(minutes=config.LIVE_WINDOW_MINUTES)
    result = {}
    for sport_id in config.SPORT_IDS:
        schedule_table, score_table = table_pair(sport_id)
        rows = conn.query(
            f"SELECT s.event_id,s.event_date,c.event_status FROM {schedule_table} s "
            f"LEFT JOIN {score_table} c ON s.event_id=c.event_id "
            "WHERE s.sport_id=%s AND s.event_date >= %s AND s.event_date <= %s",
            (sport_id, start.strftime("%Y-%m-%d %H:%M:%S"), now.strftime("%Y-%m-%d %H:%M:%S")),
        )
        for event_id, kickoff, status in rows:
            if terminal(status):
                continue
            when = kickoff.replace(tzinfo=dt.timezone.utc) if isinstance(kickoff, dt.datetime) else dt.datetime.strptime(
                to_dt(kickoff), "%Y-%m-%d %H:%M:%S").replace(tzinfo=dt.timezone.utc)
            bucket = api_date(when).isoformat()
            result.setdefault((sport_id, bucket), set()).add(str(event_id))
    return result


def cmd_live_once(conn):
    buckets = live_candidates(conn)
    if not buckets:
        log("赛时窗口没有未结束比赛，跳过 Rundown 请求")
        return 0
    total = 0
    for (sport_id, day), wanted in sorted(buckets.items()):
        _, score_table = table_pair(sport_id)
        events = fetch_events(sport_id, day)
        rows = [parse_event(event)[1] for event in events if str(event.get("event_id")) in wanted]
        total += batch_upsert(conn, insert_sql(score_table, SCORE_COLUMNS), rows,
                              f"{score_table} {day} 赛时比分")
        if len(rows) < len(wanted):
            log(f"  sport_id={sport_id} {day}: 目标 {len(wanted)} 场，API 返回 {len(rows)} 场")
    return total


def live_loop(stop):
    conn = None
    try:
        while not stop.is_set():
            started = time.monotonic()
            try:
                if conn is None:
                    conn = DB()
                cmd_live_once(conn)
            except Exception as exc:
                log(f"赛时比分轮询失败: {exc}")
                if conn:
                    conn.close()
                    conn = None
            stop.wait(max(1, config.SCORE_INTERVAL - (time.monotonic() - started)))
    finally:
        if conn:
            conn.close()


def daily_loop(stop):
    state_path = os.path.join(os.path.dirname(__file__), ".state", "last_daily_date")
    timezone = ZoneInfo(config.DAILY_TIMEZONE)
    retry_after = 0.0
    while not stop.is_set():
        today = dt.datetime.now(timezone).date().isoformat()
        try:
            with open(state_path, encoding="utf-8") as handle:
                done = handle.read().strip()
        except FileNotFoundError:
            done = None
        if done != today and time.monotonic() >= retry_after:
            conn = None
            try:
                conn = DB()
                cmd_daily(conn)
                os.makedirs(os.path.dirname(state_path), exist_ok=True)
                temp_path = state_path + ".tmp"
                with open(temp_path, "w", encoding="utf-8") as handle:
                    handle.write(today + "\n")
                os.replace(temp_path, state_path)
            except Exception as exc:
                log(f"每日赛程失败: {exc}；15 分钟后重试")
                retry_after = time.monotonic() + 900
            finally:
                if conn:
                    conn.close()
        stop.wait(60)


def main():
    parser = argparse.ArgumentParser(description="Rundown 赛程与比分 ETL")
    sub = parser.add_subparsers(dest="command", required=True)
    daily = sub.add_parser("daily", help="抓未来七天赛程和初始比分")
    daily.add_argument("--date", help="指定一个 API 日期 YYYY-MM-DD")
    daily.add_argument("--sport-id", type=int, action="append", help="只处理指定 sport_id，可重复")
    live = sub.add_parser("live", help="赛时每分钟抓未完赛比赛的比分")
    live.add_argument("--once", action="store_true")
    sub.add_parser("serve", help="常驻运行：每日赛程 + 赛时比分")
    args = parser.parse_args()
    if args.command == "daily":
        conn = DB()
        try:
            cmd_daily(conn, args.date, args.sport_id)
        finally:
            conn.close()
    elif args.command == "live" and args.once:
        conn = DB()
        try:
            cmd_live_once(conn)
        finally:
            conn.close()
    else:
        stop = threading.Event()
        try:
            if args.command == "serve":
                threading.Thread(target=daily_loop, args=(stop,), daemon=True).start()
            live_loop(stop)
        except KeyboardInterrupt:
            log("收到中断，退出")
        finally:
            stop.set()


if __name__ == "__main__":
    main()
