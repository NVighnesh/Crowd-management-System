class CameraManager:

    def __init__(self, cameras):
        self.cameras = cameras
        self._camera_map = {
            camera["id"]: camera
            for camera in cameras
        }
        self._validate()

    def _validate(self):
        if not isinstance(self.cameras, list):
            raise ValueError("Cameras configuration must be a list.")

        if len(self._camera_map) != len(self.cameras):
            raise ValueError("Duplicate camera IDs detected.")

    def get_all_cameras(self):
        return list(self.cameras)

    def get_enabled_cameras(self):
        return [
            camera
            for camera in self.cameras
            if camera.get("enabled", True)
        ]

    def get_camera(self, camera_id: str):
        return self._camera_map.get(camera_id)

    def has_camera(self, camera_id: str):
        return camera_id in self._camera_map

    def get_camera_ids(self):
        return list(self._camera_map.keys())

    def get_enabled_camera_ids(self):
        return [
            camera["id"]
            for camera in self.get_enabled_cameras()
        ]

    def replace_cameras(self, cameras):
        """
        Replace the current camera configuration and rebuild
        the internal camera lookup map.
        """
        self.cameras = list(cameras)

        self._camera_map = {
            camera["id"]: camera
            for camera in self.cameras
        }

        self._validate()