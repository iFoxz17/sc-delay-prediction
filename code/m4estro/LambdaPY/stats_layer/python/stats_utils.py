from numbers import Number
from typing import List, Tuple
import numpy as np
import scipy.stats as stats

def compute_gamma_mean(shape: float, scale: float, loc: float) -> float:
    assert isinstance(shape, Number)
    assert isinstance(scale, Number)
    assert isinstance(loc, Number), "Location parameter must be a number"

    gamma = stats.gamma(a=shape, scale=scale, loc=loc)
    return float(gamma.mean())

def compute_gamma_ci(shape: float, scale: float, loc: float, confidence_level: float) -> Tuple[float, float]:
    assert isinstance(shape, Number)
    assert isinstance(scale, Number)
    assert isinstance(loc, Number)
    assert isinstance(confidence_level, Number) and 0 < confidence_level < 1, "Confidence level must be between 0 and 1"

    gamma = stats.gamma(a=shape, scale=scale, loc=loc)

    alpha: float = 1 - confidence_level
    lower_bound: float = float(gamma.ppf(alpha / 2))
    upper_bound: float = float(gamma.ppf(1 - alpha / 2))

    return lower_bound, upper_bound

def compute_sample_ci(x: List[float], confidence_level: float) -> Tuple[float, float]:
    assert isinstance(confidence_level, Number) and 0 < confidence_level < 1, "Confidence level must be between 0 and 1"

    alpha: float = 1 - confidence_level

    lower_bound: float = float(np.percentile(x, alpha / 2 * 100))
    upper_bound: float = float(np.percentile(x, (1 - alpha / 2) * 100))

    return lower_bound, upper_bound