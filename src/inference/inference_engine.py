from abc import ABC, abstractmethod


class InferenceEngine(ABC):

    @abstractmethod
    def infer(self, frame):
        """
        Run AI inference on one frame.

        Returns:
            list[Detection]
        """
        pass