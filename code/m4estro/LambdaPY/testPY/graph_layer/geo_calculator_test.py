import pytest
from geo_calculator import GeoCalculator

@pytest.fixture
def calculator():
    return GeoCalculator()

def test_geodesic_distance_basic(calculator):
    # Distance between Paris (48.8566, 2.3522) and London (51.5074, -0.1278)
    dist = calculator.geodesic_distance(48.8566, 2.3522, 51.5074, -0.1278)
    assert isinstance(dist, float)
    # Roughly 343 km
    assert 340 < dist < 350

def test_bearing_basic(calculator):
    # Bearing from Paris to London ~ 330 degrees
    bearing = calculator.bearing(48.8566, 2.3522, 51.5074, -0.1278)
    assert isinstance(bearing, float)
    assert 320 < bearing < 340

def test_move_basic(calculator):
    # Move 100 km north from Paris
    new_lat, new_lon = calculator.move(48.8566, 2.3522, 100, 0)
    assert isinstance(new_lat, float) and isinstance(new_lon, float)
    assert new_lat > 48.8566

def test_input_validation_geodesic_distance(calculator):
    # latitudes outside valid range
    with pytest.raises(AssertionError):
        calculator.geodesic_distance(-91, 0, 0, 0)
    with pytest.raises(AssertionError):
        calculator.geodesic_distance(0, 0, 91, 0)

def test_input_validation_bearing(calculator):
    with pytest.raises(AssertionError):
        calculator.bearing(0, -181, 0, 0)
    with pytest.raises(AssertionError):
        calculator.bearing(0, 0, 0, 181)

def test_input_validation_move(calculator):
    with pytest.raises(AssertionError):
        calculator.move(0, 0, -1, 0)
    with pytest.raises(AssertionError):
        calculator.move(0, 0, 10, 360)
