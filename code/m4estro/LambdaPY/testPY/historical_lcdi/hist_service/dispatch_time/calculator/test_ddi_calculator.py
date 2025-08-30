import pytest

from hist_service.dispatch_time.calculator.ddi_calculator import DDICalculator

from hist_service.dispatch_time.dto.dispatch_time_gamma_dto import DispatchTimeGammaDTO
from hist_service.dispatch_time.dto.dispatch_time_sample_dto import DispatchTimeSampleDTO
from hist_service.dispatch_time.dto.dispatch_time_dist_dto import DispatchTimeDistDTO

from hist_service.dispatch_time.dto.ddi_dto import DDI_DTO

import scipy.stats as stats
import numpy as np

def test_adt_gamma_returns_ddi_dto():
    ci = 0.67
    calculator = DDICalculator(confidence_level=ci)
    dto = DispatchTimeGammaDTO(
        site_id=1,
        site_location="Test Location",
        manufacturer_supplier_id=100,
        supplier_id=10,
        supplier_name="Test Supplier",
        mean=1.0,
        std_dev=0.5,
        n=10,
        shape=2.0,
        loc=0.0,
        scale=1.0,
        skewness=0.1,
        kurtosis=3.0
    )
    gamma = stats.gamma(a=dto.shape, loc=dto.loc, scale=dto.scale)
    result = calculator.ddi(dto)

    alpha = 1 - ci
    l = gamma.ppf(alpha / 2)
    u = gamma.ppf(1 - alpha / 2)
    mean = gamma.mean()

    assert isinstance(result, DDI_DTO)
    assert np.isclose(result.lower, mean - l)
    assert np.isclose(result.upper, u - mean)

def test_adt_sample_returns_ddi_dto():
    ci = 0.67
    calculator = DDICalculator(confidence_level=ci)
    dto = DispatchTimeSampleDTO(
        site_id=2,
        site_location="Sample Location",
        supplier_id=20,
        manufacturer_supplier_id=200,
        supplier_name="Sample Supplier",
        x=[1.0, 2.0, 3.0, 4.0, 5.0],
        mean=3.0,
        std_dev=1.0,
        n=5,
        median=1.5
    )
    ci = 0.67
    result = calculator.ddi(dto)

    alpha = 1 - ci
    l = np.percentile(dto.x, alpha / 2 * 100)
    u = np.percentile(dto.x, (1 - alpha / 2) * 100)
    mean = np.mean(dto.x)

    assert isinstance(result, DDI_DTO)
    assert np.isclose(result.lower, mean - l)
    assert np.isclose(result.upper, u - mean)

def test_ddi_raises_value_error_for_unknown_dto():
    class UnknownDTO(DispatchTimeDistDTO):
        pass

    calculator = DDICalculator(confidence_level=0.95)
    dto = UnknownDTO(site_id=0, site_location="", supplier_id=1, manufacturer_supplier_id=200, supplier_name="", mean=0, std_dev=0, n=0)

    with pytest.raises(ValueError) as excinfo:
        calculator.ddi(dto)