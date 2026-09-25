import cv2

from src.video.source import VideoSource


class FileVideoSource(VideoSource):

    def __init__(
        self,
        path: str,
        loop: bool = False,
    ):

        self.path = path
        self.loop = loop
        self.cap = None

    def open(self):

        self.cap = cv2.VideoCapture(
            self.path
        )

    def read(self):

        if self.cap is None:
            return False, None

        success, frame = self.cap.read()

        if success:
            return True, frame

        # End of file reached
        if self.loop:

            self.cap.set(
                cv2.CAP_PROP_POS_FRAMES,
                0,
            )

            success, frame = self.cap.read()

            if success:
                return True, frame

        return False, None

    def is_opened(self):

        return (
            self.cap is not None
            and self.cap.isOpened()
        )

    def release(self):

        if self.cap is not None:

            self.cap.release()
            self.cap = None