import pytest
from model.alpha import AlphaType
from core.calculator.tfst.alpha.alpha_calculator import AlphaCalculator
from core.calculator.tfst.alpha.alpha_const_calculator import AlphaConstCalculator
from core.calculator.tfst.alpha.alpha_exp_calculator import AlphaExpCalculator
from core.calculator.tfst.alpha.alpha_markov_calculator import AlphaMarkovCalculator

from core.initializer.alpha_initializer import AlphaInitializer

def test_initialize_const():
    alpha_const_value = 0.5
    alpha_exp_tt_weight = 0.3  # irrelevant here
    initializer = AlphaInitializer(alpha_const_value, alpha_exp_tt_weight)
    calc = initializer.initialize(AlphaType.CONST)
    assert isinstance(calc, AlphaConstCalculator)
    assert calc.alpha == alpha_const_value

def test_initialize_exp():
    alpha_const_value = 0.5  # irrelevant here
    alpha_exp_tt_weight = 0.3
    initializer = AlphaInitializer(alpha_const_value, alpha_exp_tt_weight)
    calc = initializer.initialize(AlphaType.EXP)
    assert isinstance(calc, AlphaExpCalculator)
    assert calc.tt_weight == alpha_exp_tt_weight

def test_initialize_markov():
    alpha_const_value = 0.5  # irrelevant here
    alpha_exp_tt_weight = 0.3  # irrelevant here
    initializer = AlphaInitializer(alpha_const_value, alpha_exp_tt_weight)
    calc = initializer.initialize(AlphaType.MARKOV)
    assert isinstance(calc, AlphaMarkovCalculator)

def test_initialize_invalid_alpha_type():
    alpha_const_value = 0.5
    alpha_exp_tt_weight = 0.3
    initializer = AlphaInitializer(alpha_const_value, alpha_exp_tt_weight)
    with pytest.raises(ValueError):
        # Pass an invalid enum value (not in AlphaType)
        initializer.initialize("INVALID_TYPE")  # type: ignore
