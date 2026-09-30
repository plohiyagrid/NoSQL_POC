import os
from dataclasses import dataclass

from cassandra import ConsistencyLevel
from dotenv import load_dotenv

load_dotenv()

CONSISTENCY_MAP = {
    "ONE": ConsistencyLevel.ONE,
    "QUORUM": ConsistencyLevel.QUORUM,
    "LOCAL_QUORUM": ConsistencyLevel.LOCAL_QUORUM,
    "LOCAL_ONE": ConsistencyLevel.LOCAL_ONE,
    "ALL": ConsistencyLevel.ALL,
}


@dataclass(frozen=True)
class CassandraConfig:
    hosts: tuple[str, ...]
    port: int
    keyspace: str
    connect_timeout: int
    write_consistency: ConsistencyLevel
    read_consistency: ConsistencyLevel
    default_ttl_seconds: int


def load_config() -> CassandraConfig:
    hosts = tuple(
        host.strip()
        for host in os.getenv("CASSANDRA_HOSTS", "127.0.0.1").split(",")
        if host.strip()
    )
    write_level = os.getenv("WRITE_CONSISTENCY", "QUORUM").upper()
    read_level = os.getenv("READ_CONSISTENCY", "ONE").upper()

    return CassandraConfig(
        hosts=hosts,
        port=int(os.getenv("CASSANDRA_PORT", "9042")),
        keyspace=os.getenv("CASSANDRA_KEYSPACE", "activity_logs"),
        connect_timeout=int(os.getenv("CASSANDRA_CONNECT_TIMEOUT", "30")),
        write_consistency=CONSISTENCY_MAP.get(write_level, ConsistencyLevel.QUORUM),
        read_consistency=CONSISTENCY_MAP.get(read_level, ConsistencyLevel.ONE),
        default_ttl_seconds=int(os.getenv("DEFAULT_TTL_SECONDS", "2592000")),
    )
