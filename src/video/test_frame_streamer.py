import time

from src.config.settings import load_config
from src.config.validator import ConfigValidator
from src.video.camera_manager import CameraManager
from src.video.multi_camera_manager import MultiCameraManager
from src.video.frame_streamer import FrameStreamer


def main():

    print("Testing frame streamer...")

    # --------------------------------------------------
    # Load configuration
    # --------------------------------------------------

    config = load_config()

    ConfigValidator.validate(config)

    camera_manager = CameraManager(
        config["cameras"]
    )

    enabled_cameras = (
        camera_manager.get_enabled_cameras()
    )

    print()
    print(
        f"Enabled cameras: "
        f"{len(enabled_cameras)}"
    )

    # --------------------------------------------------
    # Create multi-camera manager
    # --------------------------------------------------

    manager = MultiCameraManager(
        cameras=enabled_cameras,
        inference_config=config["inference"],
        tracking_config=config["tracking"],
        counting_config=config["counting"],
        processing_config=config["processing"],
    )

    try:

        # --------------------------------------------------
        # Start cameras
        # --------------------------------------------------

        manager.setup()

        print(
            "All camera workers started."
        )

        # --------------------------------------------------
        # Wait for annotated frames
        # --------------------------------------------------

        print()
        print(
            "Waiting for AI-annotated frames..."
        )

        start_time = time.time()
        timeout = 30

        selected_camera = None

        while (
            time.time() - start_time
            < timeout
        ):

            for camera_id in manager.get_camera_ids():

                worker = manager.workers[
                    camera_id
                ]

                frame = (
                    worker
                    .get_latest_annotated_frame()
                )

                if frame is not None:

                    selected_camera = camera_id
                    break

            if selected_camera is not None:
                break

            time.sleep(0.5)

        if selected_camera is None:

            raise AssertionError(
                "No AI-annotated frame became "
                "available within the timeout."
            )

        print(
            f"Annotated frame available from: "
            f"{selected_camera}"
        )

        # --------------------------------------------------
        # Create streamer
        # --------------------------------------------------

        worker = manager.workers[
            selected_camera
        ]

        streamer = FrameStreamer(
            worker=worker,
            jpeg_quality=80,
            stream_fps=10,
        )

        print()
        print(
            "FrameStreamer created."
        )

        # --------------------------------------------------
        # Read first streamed frame
        # --------------------------------------------------

        generator = streamer.generate()

        first_chunk = next(generator)

        print()
        print(
            f"First stream chunk size: "
            f"{len(first_chunk)} bytes"
        )

        # --------------------------------------------------
        # Validate MJPEG structure
        # --------------------------------------------------

        if not first_chunk.startswith(
            b"--frame\r\n"
        ):

            raise AssertionError(
                "Stream does not start with "
                "the MJPEG frame boundary."
            )

        if (
            b"Content-Type: image/jpeg"
            not in first_chunk
        ):

            raise AssertionError(
                "Stream chunk does not "
                "contain JPEG content type."
            )

        if (
            b"\xff\xd8"
            not in first_chunk
        ):

            raise AssertionError(
                "Stream chunk does not "
                "contain JPEG start marker."
            )

        if (
            b"\xff\xd9"
            not in first_chunk
        ):

            raise AssertionError(
                "Stream chunk does not "
                "contain JPEG end marker."
            )

        print(
            "MJPEG frame structure: PASS"
        )

        # --------------------------------------------------
        # Read second streamed frame
        # --------------------------------------------------

        start_time = time.time()

        second_chunk = next(generator)

        elapsed = time.time() - start_time

        print()
        print(
            f"Second stream chunk size: "
            f"{len(second_chunk)} bytes"
        )

        print(
            f"Time between stream frames: "
            f"{elapsed:.3f} seconds"
        )

        if not second_chunk.startswith(
            b"--frame\r\n"
        ):

            raise AssertionError(
                "Second stream chunk is invalid."
            )

        if (
            b"Content-Type: image/jpeg"
            not in second_chunk
        ):

            raise AssertionError(
                "Second stream chunk does not "
                "contain JPEG content type."
            )

        if (
            b"\xff\xd8"
            not in second_chunk
            or b"\xff\xd9"
            not in second_chunk
        ):

            raise AssertionError(
                "Second stream chunk does not "
                "contain valid JPEG data."
            )

        print(
            "Continuous frame generation: PASS"
        )

        # --------------------------------------------------
        # Validate configuration
        # --------------------------------------------------

        if streamer.jpeg_quality != 80:

            raise AssertionError(
                "Incorrect JPEG quality."
            )

        if streamer.stream_fps != 10:

            raise AssertionError(
                "Incorrect stream FPS."
            )

        print(
            "Streamer configuration: PASS"
        )

        # --------------------------------------------------
        # Final result
        # --------------------------------------------------

        print()
        print(
            "Frame streamer test successful."
        )

    finally:

        manager.release()

        print()
        print(
            "All camera workers stopped."
        )


if __name__ == "__main__":

    main()