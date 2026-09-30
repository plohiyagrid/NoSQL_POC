from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

from cassandra.cluster import Cluster
from cassandra.query import SimpleStatement

from app.config import CassandraConfig, load_config
from app.models import ActivityLog


class ActivityLogRepository:
    """Cassandra data access layer for user activity logs."""

    def __init__(self, config: CassandraConfig | None = None) -> None:
        self.config = config or load_config()
        self._cluster: Cluster | None = None
        self._session = None
        self._prepared: dict[str, object] = {}

    def connect(self) -> None:
        if self._session is not None:
            return

        if self._cluster is None:
            self._cluster = Cluster(
                contact_points=list(self.config.hosts),
                port=self.config.port,
                connect_timeout=self.config.connect_timeout,
            )
        self._session = self._cluster.connect(self.config.keyspace)
        self._prepare_statements()

    def close(self) -> None:
        if self._cluster is not None:
            self._cluster.shutdown()
        self._cluster = None
        self._session = None
        self._prepared.clear()

    def __enter__(self) -> "ActivityLogRepository":
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def apply_schema(self, schema_path: Path | None = None) -> None:
        """Apply CQL schema file. Connects without keyspace first."""
        path = schema_path or Path(__file__).resolve().parent.parent / "schema" / "schema.cql"
        statements = self._parse_cql_file(path)

        if self._cluster is None:
            self._cluster = Cluster(
                contact_points=list(self.config.hosts),
                port=self.config.port,
                connect_timeout=self.config.connect_timeout,
            )

        bootstrap_session = self._cluster.connect()
        try:
            for statement in statements:
                bootstrap_session.execute(SimpleStatement(statement))
        finally:
            bootstrap_session.shutdown()

        self.connect()

    def insert_activity(
        self,
        user_id: UUID,
        activity_type: str,
        timestamp: datetime | None = None,
        activity_id: UUID | None = None,
        details: str | None = None,
        ttl_seconds: int | None = None,
    ) -> ActivityLog:
        self._ensure_connected()

        log = ActivityLog(
            user_id=user_id,
            activity_id=activity_id or uuid4(),
            activity_type=activity_type,
            timestamp=timestamp or datetime.utcnow(),
            details=details,
        )

        ttl = ttl_seconds if ttl_seconds is not None else self.config.default_ttl_seconds
        self._session.execute(
            self._prepared["insert"],
            (
                log.user_id,
                log.timestamp,
                log.activity_id,
                log.activity_type,
                log.details,
                ttl,
            ),
        )
        return log

    def get_all_activities(self, user_id: UUID) -> list[ActivityLog]:
        """Return all activities for a user, newest first."""
        self._ensure_connected()
        rows = self._session.execute(self._prepared["select_all"], (user_id,))
        return [self._row_to_log(row) for row in rows]

    def get_recent_activities(self, user_id: UUID, limit: int = 10) -> list[ActivityLog]:
        """Return the N most recent activities for a user."""
        self._ensure_connected()
        rows = self._session.execute(self._prepared["select_recent"], (user_id, limit))
        return [self._row_to_log(row) for row in rows]

    def get_activities_in_range(
        self,
        user_id: UUID,
        start: datetime,
        end: datetime,
    ) -> list[ActivityLog]:
        """Return activities for a user within [start, end], newest first."""
        self._ensure_connected()
        rows = self._session.execute(
            self._prepared["select_range"],
            (user_id, end, start),
        )
        return [self._row_to_log(row) for row in rows]

    def _prepare_statements(self) -> None:
        assert self._session is not None

        self._prepared["insert"] = self._session.prepare(
            """
            INSERT INTO user_activity_logs
                (user_id, activity_timestamp, activity_id, activity_type, details)
            VALUES (?, ?, ?, ?, ?)
            USING TTL ?
            """
        )
        self._prepared["insert"].consistency_level = self.config.write_consistency

        self._prepared["select_all"] = self._session.prepare(
            """
            SELECT user_id, activity_timestamp, activity_id, activity_type, details
            FROM user_activity_logs
            WHERE user_id = ?
            """
        )
        self._prepared["select_all"].consistency_level = self.config.read_consistency

        self._prepared["select_recent"] = self._session.prepare(
            """
            SELECT user_id, activity_timestamp, activity_id, activity_type, details
            FROM user_activity_logs
            WHERE user_id = ?
            LIMIT ?
            """
        )
        self._prepared["select_recent"].consistency_level = self.config.read_consistency

        self._prepared["select_range"] = self._session.prepare(
            """
            SELECT user_id, activity_timestamp, activity_id, activity_type, details
            FROM user_activity_logs
            WHERE user_id = ?
              AND activity_timestamp <= ?
              AND activity_timestamp >= ?
            """
        )
        self._prepared["select_range"].consistency_level = self.config.read_consistency

    def _ensure_connected(self) -> None:
        if self._session is None:
            raise RuntimeError("Repository is not connected. Call connect() first.")

    @staticmethod
    def _row_to_log(row) -> ActivityLog:
        return ActivityLog(
            user_id=row.user_id,
            activity_id=row.activity_id,
            activity_type=row.activity_type,
            timestamp=row.activity_timestamp,
            details=row.details,
        )

    @staticmethod
    def _parse_cql_file(path: Path) -> list[str]:
        statements: list[str] = []
        buffer: list[str] = []

        for raw_line in path.read_text().splitlines():
            stripped = raw_line.strip()
            if not stripped or stripped.startswith("--"):
                continue

            code_line = stripped.split("--", 1)[0].strip()
            buffer.append(raw_line)
            if code_line.endswith(";"):
                statements.append("\n".join(buffer))
                buffer = []

        return statements
