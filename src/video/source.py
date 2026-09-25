from abc import ABC, abstractmethod


class VideoSource(ABC):

    @abstractmethod
    def open(self):
        pass

    @abstractmethod
    def read(self):
        pass

    @abstractmethod
    def is_opened(self):
        pass

    @abstractmethod
    def release(self):
        pass