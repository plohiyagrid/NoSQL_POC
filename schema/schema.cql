-- User Activity Log System - Cassandra Schema
--
-- Query patterns supported:
--   1. Get all activities for a user
--   2. Get activities within a time range for a user
--   3. Get recent activities for a user (LIMIT)
--
-- Partition key: user_id  -> all of a user's logs live in one partition
-- Clustering key: activity_timestamp DESC, activity_id ASC
--   -> rows are stored newest-first within each partition

CREATE KEYSPACE IF NOT EXISTS activity_logs
WITH replication = {
    'class': 'SimpleStrategy',
    'replication_factor': 1
};

-- Production recommendation (multi-datacenter):
-- CREATE KEYSPACE activity_logs
-- WITH replication = {
--     'class': 'NetworkTopologyStrategy',
--     'dc1': 3,
--     'dc2': 3
-- };

USE activity_logs;

CREATE TABLE IF NOT EXISTS user_activity_logs (
    user_id             UUID,
    activity_timestamp  TIMESTAMP,
    activity_id         UUID,
    activity_type       TEXT,
    details             TEXT,
    PRIMARY KEY ((user_id), activity_timestamp, activity_id)
) WITH CLUSTERING ORDER BY (activity_timestamp DESC, activity_id ASC)
  AND default_time_to_live = 2592000
  AND gc_grace_seconds     = 864000;
