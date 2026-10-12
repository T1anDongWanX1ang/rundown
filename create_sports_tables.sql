-- polymarket_data: 从五大联赛赛程/比分表复制结构，使用当前可用的 SSD。
CREATE TABLE IF NOT EXISTS `nfl_schedule` (
  `event_id` varchar(64) NOT NULL COMMENT "赛事唯一ID",
  `event_uuid` varchar(64) NULL COMMENT "赛事UUID",
  `espn_uid` varchar(64) NULL COMMENT "ESPN UID",
  `sport_id` int NULL COMMENT "运动ID(11英超/12法甲/13德甲/14西甲/15意甲)",
  `league_code` varchar(16) NULL COMMENT "联赛标识 EPL/FRA1/GER1/ESP1/ITA1",
  `event_date` datetime NULL COMMENT "开赛时间(UTC)",
  `season_type` varchar(64) NULL COMMENT "赛季阶段, 如 2026-27 LALIGA",
  `season_year` int NULL COMMENT "赛季年份",
  `event_name` varchar(256) NULL COMMENT "赛事名称",
  `conference_competition` boolean NULL COMMENT "是否分区赛",
  `attendance` int NULL DEFAULT "0" COMMENT "观众数",
  `team_home_id` bigint NULL COMMENT "主队ID",
  `team_home_name` varchar(128) NULL COMMENT "主队名",
  `team_home_abbr` varchar(32) NULL COMMENT "主队缩写",
  `team_home_record` varchar(32) NULL COMMENT "主队战绩",
  `team_away_id` bigint NULL COMMENT "客队ID",
  `team_away_name` varchar(128) NULL COMMENT "客队名",
  `team_away_abbr` varchar(32) NULL COMMENT "客队缩写",
  `team_away_record` varchar(32) NULL COMMENT "客队战绩",
  `venue_name` varchar(128) NULL COMMENT "球场名",
  `venue_location` varchar(128) NULL COMMENT "球场城市",
  `broadcast` varchar(64) NULL COMMENT "转播方",
  `source_updated_at` datetime NULL COMMENT "源数据更新时间",
  `etl_time` datetime NULL DEFAULT CURRENT_TIMESTAMP COMMENT "入库时间"
) ENGINE=OLAP
UNIQUE KEY(`event_id`)
COMMENT 'NFL赛程表'
DISTRIBUTED BY HASH(`event_id`) BUCKETS 8
PROPERTIES (
"replication_allocation" = "tag.location.default: 1",
"min_load_replica_num" = "-1",
"is_being_synced" = "false",
"storage_medium" = "ssd",
"storage_format" = "V2",
"inverted_index_storage_format" = "V2",
"enable_unique_key_merge_on_write" = "true",
"light_schema_change" = "true",
"disable_auto_compaction" = "false",
"binlog.enable" = "false",
"binlog.ttl_seconds" = "86400",
"binlog.max_bytes" = "9223372036854775807",
"binlog.max_history_nums" = "9223372036854775807",
"enable_single_replica_compaction" = "false",
"group_commit_interval_ms" = "10000",
"group_commit_data_bytes" = "134217728",
"enable_mow_light_delete" = "false"
);;

CREATE TABLE IF NOT EXISTS `nfl_score` (
  `event_id` varchar(64) NOT NULL COMMENT "赛事ID",
  `sport_id` int NULL COMMENT "运动ID",
  `league_code` varchar(16) NULL COMMENT "联赛标识 EPL/FRA1/GER1/ESP1/ITA1",
  `event_status` varchar(32) NULL COMMENT "STATUS_SCHEDULED/IN_PROGRESS/FINAL",
  `event_status_detail` varchar(64) NULL COMMENT "状态详情",
  `team_id_home` bigint NULL COMMENT "主队ID",
  `team_id_away` bigint NULL COMMENT "客队ID",
  `score_home` int NULL DEFAULT "0" COMMENT "主队总比分",
  `score_away` int NULL DEFAULT "0" COMMENT "客队总比分",
  `winner_home` tinyint NULL COMMENT "主队是否获胜 0/1",
  `winner_away` tinyint NULL COMMENT "客队是否获胜 0/1",
  `score_home_by_period` varchar(128) NULL COMMENT "主队分段比分JSON, 如 [1,0]",
  `score_away_by_period` varchar(128) NULL COMMENT "客队分段比分JSON",
  `game_clock` int NULL COMMENT "比赛时钟(秒)",
  `display_clock` varchar(32) NULL COMMENT "显示时钟, 如 45'",
  `game_period` int NULL COMMENT "比赛阶段 0未开始/1上半/2下半",
  `venue_name` varchar(128) NULL COMMENT "球场名",
  `venue_location` varchar(128) NULL COMMENT "球场城市",
  `broadcast` varchar(64) NULL COMMENT "转播方",
  `score_updated_at` datetime NULL COMMENT "比分更新时间",
  `etl_time` datetime NULL DEFAULT CURRENT_TIMESTAMP COMMENT "入库时间"
) ENGINE=OLAP
UNIQUE KEY(`event_id`)
COMMENT 'NFL比分表'
DISTRIBUTED BY HASH(`event_id`) BUCKETS 8
PROPERTIES (
"replication_allocation" = "tag.location.default: 1",
"min_load_replica_num" = "-1",
"is_being_synced" = "false",
"storage_medium" = "ssd",
"storage_format" = "V2",
"inverted_index_storage_format" = "V2",
"enable_unique_key_merge_on_write" = "true",
"light_schema_change" = "true",
"disable_auto_compaction" = "false",
"binlog.enable" = "false",
"binlog.ttl_seconds" = "86400",
"binlog.max_bytes" = "9223372036854775807",
"binlog.max_history_nums" = "9223372036854775807",
"enable_single_replica_compaction" = "false",
"group_commit_interval_ms" = "10000",
"group_commit_data_bytes" = "134217728",
"enable_mow_light_delete" = "false"
);;

CREATE TABLE IF NOT EXISTS `nba_schedule` (
  `event_id` varchar(64) NOT NULL COMMENT "赛事唯一ID",
  `event_uuid` varchar(64) NULL COMMENT "赛事UUID",
  `espn_uid` varchar(64) NULL COMMENT "ESPN UID",
  `sport_id` int NULL COMMENT "运动ID(11英超/12法甲/13德甲/14西甲/15意甲)",
  `league_code` varchar(16) NULL COMMENT "联赛标识 EPL/FRA1/GER1/ESP1/ITA1",
  `event_date` datetime NULL COMMENT "开赛时间(UTC)",
  `season_type` varchar(64) NULL COMMENT "赛季阶段, 如 2026-27 LALIGA",
  `season_year` int NULL COMMENT "赛季年份",
  `event_name` varchar(256) NULL COMMENT "赛事名称",
  `conference_competition` boolean NULL COMMENT "是否分区赛",
  `attendance` int NULL DEFAULT "0" COMMENT "观众数",
  `team_home_id` bigint NULL COMMENT "主队ID",
  `team_home_name` varchar(128) NULL COMMENT "主队名",
  `team_home_abbr` varchar(32) NULL COMMENT "主队缩写",
  `team_home_record` varchar(32) NULL COMMENT "主队战绩",
  `team_away_id` bigint NULL COMMENT "客队ID",
  `team_away_name` varchar(128) NULL COMMENT "客队名",
  `team_away_abbr` varchar(32) NULL COMMENT "客队缩写",
  `team_away_record` varchar(32) NULL COMMENT "客队战绩",
  `venue_name` varchar(128) NULL COMMENT "球场名",
  `venue_location` varchar(128) NULL COMMENT "球场城市",
  `broadcast` varchar(64) NULL COMMENT "转播方",
  `source_updated_at` datetime NULL COMMENT "源数据更新时间",
  `etl_time` datetime NULL DEFAULT CURRENT_TIMESTAMP COMMENT "入库时间"
) ENGINE=OLAP
UNIQUE KEY(`event_id`)
COMMENT 'NBA赛程表'
DISTRIBUTED BY HASH(`event_id`) BUCKETS 8
PROPERTIES (
"replication_allocation" = "tag.location.default: 1",
"min_load_replica_num" = "-1",
"is_being_synced" = "false",
"storage_medium" = "ssd",
"storage_format" = "V2",
"inverted_index_storage_format" = "V2",
"enable_unique_key_merge_on_write" = "true",
"light_schema_change" = "true",
"disable_auto_compaction" = "false",
"binlog.enable" = "false",
"binlog.ttl_seconds" = "86400",
"binlog.max_bytes" = "9223372036854775807",
"binlog.max_history_nums" = "9223372036854775807",
"enable_single_replica_compaction" = "false",
"group_commit_interval_ms" = "10000",
"group_commit_data_bytes" = "134217728",
"enable_mow_light_delete" = "false"
);;

CREATE TABLE IF NOT EXISTS `nba_score` (
  `event_id` varchar(64) NOT NULL COMMENT "赛事ID",
  `sport_id` int NULL COMMENT "运动ID",
  `league_code` varchar(16) NULL COMMENT "联赛标识 EPL/FRA1/GER1/ESP1/ITA1",
  `event_status` varchar(32) NULL COMMENT "STATUS_SCHEDULED/IN_PROGRESS/FINAL",
  `event_status_detail` varchar(64) NULL COMMENT "状态详情",
  `team_id_home` bigint NULL COMMENT "主队ID",
  `team_id_away` bigint NULL COMMENT "客队ID",
  `score_home` int NULL DEFAULT "0" COMMENT "主队总比分",
  `score_away` int NULL DEFAULT "0" COMMENT "客队总比分",
  `winner_home` tinyint NULL COMMENT "主队是否获胜 0/1",
  `winner_away` tinyint NULL COMMENT "客队是否获胜 0/1",
  `score_home_by_period` varchar(128) NULL COMMENT "主队分段比分JSON, 如 [1,0]",
  `score_away_by_period` varchar(128) NULL COMMENT "客队分段比分JSON",
  `game_clock` int NULL COMMENT "比赛时钟(秒)",
  `display_clock` varchar(32) NULL COMMENT "显示时钟, 如 45'",
  `game_period` int NULL COMMENT "比赛阶段 0未开始/1上半/2下半",
  `venue_name` varchar(128) NULL COMMENT "球场名",
  `venue_location` varchar(128) NULL COMMENT "球场城市",
  `broadcast` varchar(64) NULL COMMENT "转播方",
  `score_updated_at` datetime NULL COMMENT "比分更新时间",
  `etl_time` datetime NULL DEFAULT CURRENT_TIMESTAMP COMMENT "入库时间"
) ENGINE=OLAP
UNIQUE KEY(`event_id`)
COMMENT 'NBA比分表'
DISTRIBUTED BY HASH(`event_id`) BUCKETS 8
PROPERTIES (
"replication_allocation" = "tag.location.default: 1",
"min_load_replica_num" = "-1",
"is_being_synced" = "false",
"storage_medium" = "ssd",
"storage_format" = "V2",
"inverted_index_storage_format" = "V2",
"enable_unique_key_merge_on_write" = "true",
"light_schema_change" = "true",
"disable_auto_compaction" = "false",
"binlog.enable" = "false",
"binlog.ttl_seconds" = "86400",
"binlog.max_bytes" = "9223372036854775807",
"binlog.max_history_nums" = "9223372036854775807",
"enable_single_replica_compaction" = "false",
"group_commit_interval_ms" = "10000",
"group_commit_data_bytes" = "134217728",
"enable_mow_light_delete" = "false"
);;
