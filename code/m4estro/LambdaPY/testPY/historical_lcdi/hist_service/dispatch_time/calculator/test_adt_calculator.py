import pytest

from hist_service.dispatch_time.calculator.adt_calculator import ADTCalculator

from hist_service.dispatch_time.dto.dispatch_time_gamma_dto import DispatchTimeGammaDTO
from hist_service.dispatch_time.dto.dispatch_time_sample_dto import DispatchTimeSampleDTO
from hist_service.dispatch_time.dto.dispatch_time_dist_dto import DispatchTimeDistDTO

from hist_service.dispatch_time.dto.adt_dto import ADT_DTO

import scipy.stats as stats
import numpy as np

def test_adt_gamma_returns_adt_dto():
    calculator = ADTCalculator()
    dto = DispatchTimeGammaDTO(
        site_id=1,
        site_location="Test Location",
        supplier_id=10,
        manufacturer_supplier_id=100,
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
    result = calculator.adt(dto)

    assert isinstance(result, ADT_DTO)
    assert np.isclose(result.value, gamma.mean())

def test_adt_sample_returns_adt_dto():
    calculator = ADTCalculator()
    dto = DispatchTimeSampleDTO(
        site_id=2,
        site_location="Sample Location",
        manufacturer_supplier_id=200,
        supplier_id=20,
        supplier_name="Sample Supplier",
        x=[1.0, 2.0, 3.0, 4.0, 5.0],
        mean=3.0,
        std_dev=1.0,
        n=5,
        median=3.0
    )
    result = calculator.adt(dto)
    assert isinstance(result, ADT_DTO)
    assert np.isclose(result.value, np.mean(dto.x))

def test_adt_raises_value_error_for_unknown_dto():
    class UnknownDTO(DispatchTimeDistDTO):
        pass

    calculator = ADTCalculator()
    dto = UnknownDTO(site_id=0, site_location="", manufacturer_supplier_id=200, supplier_id=1, supplier_name="", mean=0, std_dev=0, n=0)

    with pytest.raises(ValueError) as excinfo:
        calculator.adt(dto)