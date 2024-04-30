import abc

import numpy as np

"""
https://en.wikipedia.org/wiki/Moving_average
https://en.wikipedia.org/wiki/Exponential_smoothing
"""

class MovingAverage(abc.ABC):

    @abc.abstractmethod
    def update(self, value: float) -> float:
        raise NotImplemented


class SimpleMovingAverage(MovingAverage):

    def __init__(self, n_samples: int):
        self.n_samples = n_samples
        self.buffer = np.zeros((n_samples,))
        self.pos = 0
        self.sma = 0

    def update(self, value: float) -> float:
        oldest_value = self.buffer[self.pos]

        self.buffer[self.pos] = value
        self.pos = (self.pos + 1) % self.n_samples

        self.sma += (value - oldest_value) / self.n_samples

        return self.sma

class ExponentialMovingAverage(MovingAverage):

    def __init__(self, alpha: float):
        self.ema: int | None = None
        self.alpha = alpha

    def update(self, value: float) -> float:
        if self.ema is None:
            self.ema = value
        else:
            self.ema = self.alpha * value + (1 - self.alpha) * self.ema
        return self.ema
