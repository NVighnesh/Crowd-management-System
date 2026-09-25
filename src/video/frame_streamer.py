import time

import cv2


class FrameStreamer:

    def __init__(
        self,
        worker,
        jpeg_quality=80,
        stream_fps=10,
    ):

        if jpeg_quality < 1 or jpeg_quality > 100:
            raise ValueError(
                "jpeg_quality must be between 1 and 100."
            )

        if stream_fps <= 0:
            raise ValueError(
                "stream_fps must be greater than zero."
            )

        self.worker = worker
        self.jpeg_quality = jpeg_quality
        self.stream_fps = stream_fps

    # --------------------------------------------------
    # Generate MJPEG stream
    # --------------------------------------------------

    def generate(self):

        interval = 1.0 / self.stream_fps

        while True:

            frame = (
                self.worker
                .get_latest_annotated_frame()
            )

            if frame is None:

                time.sleep(0.1)
                continue

            success, encoded_frame = (
                cv2.imencode(
                    ".jpg",
                    frame,
                    [
                        cv2.IMWRITE_JPEG_QUALITY,
                        self.jpeg_quality,
                    ],
                )
            )

            if not success:

                time.sleep(interval)
                continue

            frame_bytes = (
                encoded_frame.tobytes()
            )

            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n"
                b"\r\n"
                + frame_bytes
                + b"\r\n"
            )

            time.sleep(interval)