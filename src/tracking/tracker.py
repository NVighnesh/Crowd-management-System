from abc import abstractmethod

from src.inference.inference_engine import InferenceEngine


class PersonTracker(InferenceEngine):

    @abstractmethod
    def reset(self):
        """Reset tracker state."""
        pass