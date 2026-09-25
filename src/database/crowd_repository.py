from src.database.database import Database, postgres_timestamp


class CrowdRepository:

    def __init__(self, database: Database):
        self.database = database

    def save_result(
        self,
        camera_id: str,
        total_people: int | None,
        result_timestamp: str,
    ):
        self.database.execute(
            """
            INSERT INTO crowd_results (
                camera_id,
                total_people,
                result_timestamp
            )
            VALUES (%s, %s, %s)
            """,
            (
                camera_id,
                total_people,
                postgres_timestamp(result_timestamp),
            ),
        )

    def get_latest(self, camera_id: str):
        return self.database.fetch_one(
            """
            SELECT
                id,
                camera_id,
                total_people,
                result_timestamp
            FROM crowd_results
            WHERE camera_id = %s
            ORDER BY id DESC
            LIMIT 1
            """,
            (camera_id,),
        )

    def get_recent(
        self,
        camera_id: str,
        limit: int = 100,
    ):
        return self.database.fetch_all(
            """
            SELECT
                id,
                camera_id,
                total_people,
                result_timestamp
            FROM crowd_results
            WHERE camera_id = %s
            ORDER BY id DESC
            LIMIT %s
            """,
            (
                camera_id,
                limit,
            ),
        )

    def get_history(
        self,
        camera_id: str,
        start_timestamp: str | None = None,
        end_timestamp: str | None = None,
        limit: int = 1000,
    ):
        clauses = ["camera_id = %s"]
        parameters = [camera_id]

        if start_timestamp is not None:
            clauses.append("result_timestamp >= %s")
            parameters.append(postgres_timestamp(start_timestamp))

        if end_timestamp is not None:
            clauses.append("result_timestamp <= %s")
            parameters.append(postgres_timestamp(end_timestamp))

        parameters.append(limit)

        return self.database.fetch_all(
            f"""
            SELECT
                id,
                camera_id,
                total_people,
                result_timestamp
            FROM crowd_results
            WHERE {" AND ".join(clauses)}
            ORDER BY result_timestamp ASC, id ASC
            LIMIT %s
            """,
            tuple(parameters),
        )

    def get_analytics(
        self,
        camera_id: str,
        start_timestamp: str | None = None,
        end_timestamp: str | None = None,
    ):
        clauses = ["camera_id = %s"]
        parameters = [camera_id]

        if start_timestamp is not None:
            clauses.append("result_timestamp >= %s")
            parameters.append(postgres_timestamp(start_timestamp))

        if end_timestamp is not None:
            clauses.append("result_timestamp <= %s")
            parameters.append(postgres_timestamp(end_timestamp))

        summary = self.database.fetch_one(
            f"""
            SELECT
                COUNT(*) AS total_observations,
                MIN(total_people) AS minimum_count,
                MAX(total_people) AS maximum_count,
                AVG(total_people) AS average_count
            FROM crowd_results
            WHERE {" AND ".join(clauses)}
            """,
            tuple(parameters),
        )
        peak = self.database.fetch_one(
            f"""
            SELECT total_people AS peak_count, result_timestamp AS peak_timestamp
            FROM crowd_results
            WHERE {" AND ".join(clauses)}
            ORDER BY total_people DESC, result_timestamp ASC, id ASC
            LIMIT 1
            """,
            tuple(parameters),
        )
        return {
            **dict(summary),
            **(dict(peak) if peak else {}),
        }
