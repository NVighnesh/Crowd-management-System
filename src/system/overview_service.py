from src.system.overview import SystemOverview


class SystemOverviewService:

    def __init__(
        self,
        camera_manager,
        multi_camera_manager,
        database_service=None,
    ):

        self.camera_manager = camera_manager
        self.multi_camera_manager = (
            multi_camera_manager
        )
        self.database_service = database_service

    # --------------------------------------------------
    # Build complete system overview
    # --------------------------------------------------

    def get_overview(self):

        cameras = (
            self.camera_manager
            .get_enabled_cameras()
        )

        camera_data = []

        online_cameras = 0
        offline_cameras = 0
        stale_cameras = 0

        total_people = 0

        for camera in cameras:

            camera_id = camera["id"]

            worker = (
                self.multi_camera_manager
                .workers.get(camera_id)
            )

            if worker is None:
                offline_cameras += 1
                camera_data.append(
                    {
                        "camera_id": camera_id,
                        "camera_name": camera.get(
                            "name",
                            camera_id,
                        ),
                        "owner_id": camera.get("owner_id"),
                        "status": "OFFLINE",
                        "processing_status": "OFFLINE",
                        "last_error": "Camera worker is not running.",
                        "last_frame_time": None,
                        "last_inference_time": None,
                        "result_timestamp": None,
                        "age_seconds": None,
                        "fresh": False,
                        "total_people": None,
                        "zones": [],
                    }
                )
                continue

            status = worker.get_status()

            camera_status = status[
                "status"
            ]

            processing_status = status[
                "processing_status"
            ]

            if camera_status == "ONLINE":

                online_cameras += 1

            elif camera_status == "STALE":

                stale_cameras += 1

            else:

                offline_cameras += 1

            result_entry = (
                self.multi_camera_manager
                .get_latest_result_with_timestamp(
                    camera_id
                )
            )

            result = None
            result_timestamp = None
            age_seconds = None
            fresh = False

            if result_entry is not None:

                result = result_entry[
                    "result"
                ]

                result_timestamp = (
                    result_entry[
                        "timestamp"
                    ]
                )

                import time

                age_seconds = (
                    time.time()
                    - result_timestamp
                )

                max_result_age = (
                    self.multi_camera_manager
                    .processing_config[
                        "max_result_age_seconds"
                    ]
                )

                fresh = (
                    camera_status == "ONLINE"
                    and processing_status
                    not in {
                        "ERROR",
                        "STARTING",
                    }
                    and age_seconds
                    <= max_result_age
                )

                if result.total_people is not None:

                    total_people += (
                        result.total_people
                    )

            zones = []

            if result is not None:

                for zone in result.zones:

                    zones.append(
                        {
                            "zone_id": zone.zone_id,
                            "name": zone.name,
                            "count": zone.count,
                            "threshold": zone.threshold,
                            "status": zone.status,
                        }
                    )

            camera_data.append(
                {
                    "camera_id": camera_id,
                    "camera_name": camera.get(
                        "name",
                        camera_id,
                    ),
                    "owner_id": camera.get("owner_id"),
                    "status": camera_status,
                    "processing_status": (
                        processing_status
                    ),
                    "last_error": (
                        status["last_error"]
                    ),
                    "last_frame_time": (
                        status[
                            "last_frame_time"
                        ]
                    ),
                    "last_inference_time": (
                        status[
                            "last_inference_time"
                        ]
                    ),
                    "result_timestamp": (
                        result_timestamp
                    ),
                    "age_seconds": age_seconds,
                    "fresh": fresh,
                    "total_people": (
                        result.total_people
                        if result is not None
                        else None
                    ),
                    "zones": zones,
                }
            )

        alerts = (
            self.multi_camera_manager
            .get_all_alerts()
        )

        alert_data = []

        for alert in alerts:

            alert_data.append(
                {
                    "alert_id": alert.alert_id,
                    "camera_id": alert.camera_id,
                    "zone_id": alert.zone_id,
                    "zone_name": alert.zone_name,
                    "previous_status": (
                        alert.previous_status
                    ),
                    "current_status": (
                        alert.current_status
                    ),
                    "count": alert.count,
                    "threshold": alert.threshold,
                    "timestamp": (
                        alert.timestamp.isoformat()
                    ),
                    "alert_type": (
                        alert.alert_type
                    ),
                    "active": alert.active,
                    "resolved": alert.resolved,
                }
            )

        return SystemOverview(
            total_cameras=len(cameras),
            online_cameras=online_cameras,
            offline_cameras=offline_cameras,
            stale_cameras=stale_cameras,
            total_people=total_people,
            total_alerts=(
                self.database_service.get_alert_count()
                if self.database_service is not None
                else len(alert_data)
            ),
            cameras=camera_data,
            alerts=alert_data,
        )
