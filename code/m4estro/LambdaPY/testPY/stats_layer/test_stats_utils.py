import pytest
import numpy as np
import scipy.stats as stats
from numbers import Number

from stats_utils import compute_gamma_ci, compute_sample_ci

def test_compute_gamma_ci_valid():
    shape, scale, loc = 2.0, 3.0, 0.0
    ci_95 = compute_gamma_ci(shape, scale, loc, 0.95)
    lower, upper = ci_95
    assert lower < upper
    expected_lower = stats.gamma.ppf(0.025, a=shape, scale=scale, loc=loc)
    expected_upper = stats.gamma.ppf(0.975, a=shape, scale=scale, loc=loc)
    assert np.isclose(lower, expected_lower, rtol=1e-6)
    assert np.isclose(upper, expected_upper, rtol=1e-6)

def test_compute_gamma_ci_invalid_confidence():
    # confidence_level outside (0,1)
    with pytest.raises(AssertionError):
        compute_gamma_ci(2, 3, 0, -0.1)
    with pytest.raises(AssertionError):
        compute_gamma_ci(2, 3, 0, 1)
    with pytest.raises(AssertionError):
        compute_gamma_ci(2, 3, 0, 2)

def test_compute_gamma_ci_invalid_types():
    with pytest.raises(AssertionError):
        compute_gamma_ci("shape", 3, 0, 0.95)       # type: ignore
    with pytest.raises(AssertionError):
        compute_gamma_ci(2, None, 0, 0.95)          # type: ignore
    with pytest.raises(AssertionError):
        compute_gamma_ci(2, 3, {}, 0.95)            # type: ignore
    with pytest.raises(AssertionError):
        compute_gamma_ci(2, 3, 0, "0.95")           # type: ignore

def test_compute_sample_ci_valid():
    np.random.seed(0)
    samples = stats.gamma.rvs(a=2, scale=3, size=10000)
    ci_95 = compute_sample_ci(samples, 0.95)        # type: ignore
    lower, upper = ci_95
    assert lower < upper
    assert np.isclose(lower, np.percentile(samples, 2.5), rtol=1e-3)
    assert np.isclose(upper, np.percentile(samples, 97.5), rtol=1e-3)

def test_compute_sample_ci_invalid_confidence():
    with pytest.raises(AssertionError):
        compute_sample_ci([1, 2, 3], -0.2)
    with pytest.raises(AssertionError):
        compute_sample_ci([1, 2, 3], 1)
    with pytest.raises(AssertionError):
        compute_sample_ci([1, 2, 3], 5)
    with pytest.raises(AssertionError):
        compute_sample_ci([1, 2, 3], "0.95")        # type: ignore

def test_compute_sample_ci_empty_list():
    # np.percentile raises IndexError on empty input
    with pytest.raises(IndexError):
        compute_sample_ci([], 0.95)
