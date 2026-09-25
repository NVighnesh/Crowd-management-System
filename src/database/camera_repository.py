from src.database.database import Database


class CameraRepository:

    def __init__(self, database: Database):
        self.database = database

    def save(
        self,
        camera_id: str,
        source_type: str,
        source: str,
        enabled: bool = True,
        camera_name: str = "",
        loop: bool = True,
        owner_id: str | None = None,
    ):
        self.database.execute(
            """
            INSERT INTO cameras (
                camera_id,
                camera_name,
                source_type,
                source,
                loop,
                enabled
                , owner_id
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT(camera_id)
            DO UPDATE SET
                camera_name = excluded.camera_name,
                source_type = excluded.source_type,
                source = excluded.source,
                loop = excluded.loop,
                enabled = excluded.enabled,
                owner_id = excluded.owner_id,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                camera_id,
                camera_name,
                source_type,
                source,
                loop,
                enabled,
                owner_id,
            ),
        )

    def get(self, camera_id: str):
        return self.database.fetch_one(
            """
            SELECT
                camera_id,
                camera_name,
                source_type,
                source,
                loop,
                enabled,
                owner_id,
                created_at,
                updated_at
            FROM cameras
            WHERE camera_id = %s
            """,
            (camera_id,),
        )

    def get_all(self):
        return self.database.fetch_all(
            """
            SELECT
                camera_id,
                camera_name,
                source_type,
                source,
                loop,
                enabled,
                owner_id,
                created_at,
                updated_at
            FROM cameras
            ORDER BY created_at ASC
            """
        )

    def get_enabled(self):
        return self.database.fetch_all(
            """
            SELECT
                camera_id,
                camera_name,
                source_type,
                source,
                loop,
                enabled,
                owner_id,
                created_at,
                updated_at
            FROM cameras
            WHERE enabled = TRUE
            ORDER BY created_at ASC
            """
        )

    def update(
        self,
        camera_id: str,
        camera_name: str,
        source_type: str,
        source: str,
        enabled: bool = True,
        loop: bool = True,
        owner_id: str | None = None,
    ):
        self.database.execute(
            """
            UPDATE cameras
            SET
                camera_name = %s,
                source_type = %s,
                source = %s,
                loop = %s,
                enabled = %s,
                owner_id = COALESCE(%s, owner_id),
                updated_at = CURRENT_TIMESTAMP
            WHERE camera_id = %s
            """,
            (
                camera_name,
                source_type,
                source,
                loop,
                enabled,
                owner_id,
                camera_id,
            ),
        )

    def delete(self, camera_id: str):
        self.database.execute(
            """
            DELETE FROM cameras
            WHERE camera_id = %s
            """,
            (camera_id,),
        )
