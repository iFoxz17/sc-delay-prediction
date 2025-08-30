import pytest

from hist_service.shipment_time.calculator.ast_calculator import ASTCalculator

from hist_service.shipment_time.dto.shipment_time_gamma_dto import ShipmentTimeGammaDTO
from hist_service.shipment_time.dto.shipment_time_sample_dto import ShipmentTimeSampleDTO
from hist_service.shipment_time.dto.shipment_time_dist_dto import ShipmentTimeDistDTO

from hist_service.shipment_time.dto.ast_dto import AST_DTO

import scipy.stats as stats
import numpy as np

def test_dispatch_time_gamma_returns_ast_dto():
    calculator = ASTCalculator()
    dto = ShipmentTimeGammaDTO(
        site_id=1,
        site_location="Test Location",
        supplier_id=10,
        manufacturer_supplier_id=100,
        supplier_name="Test Supplier",
        carrier_id=5,
        carrier_name="Test Carrier",
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
    result = calculator.ast(dto)

    assert isinstance(result, AST_DTO)
    assert np.isclose(result.value, gamma.mean())

def test_dispatch_time_sample_returns_ast_dto():
    calculator = ASTCalculator()
    dto = ShipmentTimeSampleDTO(
        site_id=2,
        site_location="Sample Location",
        supplier_id=20,
        manufacturer_supplier_id=200,
        supplier_name="Sample Supplier",
        carrier_id=10,
        carrier_name="Sample Carrier",
        x=[1.0, 2.0, 3.0, 4.0, 5.0],
        mean=3.0,
        std_dev=1.0,
        n=5,
        median=3.0
    )
    result = calculator.ast(dto)
    assert isinstance(result, AST_DTO)
    assert np.isclose(result.value, np.mean(dto.x))

def test_dispatch_time_raises_value_error_for_unknown_dto():
    class UnknownDTO(ShipmentTimeDistDTO):
        pass

    calculator = ASTCalculator()
    dto = UnknownDTO(site_id=0, site_location="", supplier_id=1, manufacturer_supplier_id=300, supplier_name="", carrier_id=0, carrier_name="test", mean=0, std_dev=0, n=0)

    with pytest.raises(ValueError) as excinfo:
        calculator.ast(dto)