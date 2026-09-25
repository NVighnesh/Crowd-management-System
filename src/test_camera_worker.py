import time

from src.config.settings import load_config
from src.video.camera_manager import CameraManager
from src.video.camera_pipeline import CameraPipeline
from src.video.camera_worker import CameraWorker


def main():
    config = load_config()

    camera_manager = CameraManager(config["cameras"])

    cameras = camera_manager.get_enabled_cameras()

    if not cameras:
        print("No enabled cameras.")
        return

    camera = cameras[0]

    print(f"Testing camera: {camera['id']}")

    pipeline = CameraPipeline(
        camera_config=camera,
        inference_config=config["inference"],
        tracking_config=config["tracking"],
        counting_config=config["counting"],
        zones_config=camera["zones_config"],
    )

    pipeline.setup()

    worker = CameraWorker(pipeline)

    worker.start()

    print("Camera capture worker started.")
    print("Waiting for frames...")

    try:
        time.sleep(2)

        for i in range(5):
            result = worker.process_latest_frame()

            if result is None:
                print("No frame available.")
                time.sleep(0.1)
                continue

            print(
                f"Frame {i + 1}: "
                f"total_people={result.total_people}"
            )

            for zone in result.zones:
                print(
                    f"  {zone.zone_id}: "
                    f"{zone.count}/{zone.threshold} "
                    f"{zone.status}"
                )

            time.sleep(0.2)

    finally:
        worker.stop()
        pipeline.release()

        print("Camera worker stopped.")
        print("Test complete.")


if __name__ == "__main__":
    main()