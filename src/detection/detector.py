from abc import ABC, abstractmethod


class PersonDetector(ABC):

    @abstractmethod
    def infer(self, frame):
        """
        Run person detection on one frame.

        Returns:
            A list of standardized person detections.
        """
        pass