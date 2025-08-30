from typing import TYPE_CHECKING, Dict, List, Callable, Tuple, Optional

from core.calculator.tfst.pt.wmi.calculator.wmi_scores import WEATHER_SCORES, WEATHER_DESCRIPTIONS, TEMP_SCORE_FN
from core.calculator.tfst.pt.wmi.calculator.wmi_calculation_dto import WMICalculationDTO, By

if TYPE_CHECKING:
    from core.calculator.tfst.pt.wmi.calculator.wmi_calculation_input_dto import WMICalculationInputDTO

from logger import get_logger
logger = get_logger(__name__)

class WMICalculator:
    def __init__(self, 
                 weather_scores: Dict[str, float] = WEATHER_SCORES,
                 weather_description: Dict[str, str] = WEATHER_DESCRIPTIONS,
                 temp_score_fn: Callable[[float], float] = TEMP_SCORE_FN
                 ) -> None:
        self.weather_scores: Dict[str, float] = weather_scores
        self.weather_description: Dict[str, str] = weather_description
        self.temp_score_fn: Callable[[float], float] = temp_score_fn

    def _empty_wmi_dto(self) -> WMICalculationDTO:
        return WMICalculationDTO(
            value=0.0,
            weather_code="",
            weather_description="",
            temperature_celsius=0.0,
            by=By.NONE
        )
    
    def _get_max_score_condition(self, weather_codes: List[str]) -> Tuple[float, str, str]:
        if not weather_codes:
            logger.warning("No weather codes provided, returning default values.")
            return 0.0, "", ""
        
        weather_scores = self.weather_scores
        max_score: float = -1.0
        max_score_code: str = ""
        max_score_description: str = ""
        
        for code in weather_codes:
            score: Optional[float] = weather_scores.get(code)
            if score is None:
                logger.warning(f"Weather code {code} not found in weather scores dictionary.")
                continue

            if score > max_score:
                max_score: float = score
                max_score_code: str = code
                max_score_description: str = self.weather_description.get(code, "")

        if max_score < 0:
            logger.warning("No valid weather codes found, returning default values.")
            return 0.0, "", ""

        return max_score, max_score_code, max_score_description
    
    def _get_max_temp_score(self, temperatures: List[float]) -> tuple[float, float]:
        if not temperatures:
            logger.warning("No temperatures provided, returning default values.")
            return 0.0, 0.0
        
        max_score: float = -1.0
        max_score_temp: float = 0.0

        for temp in temperatures:
            score: float = self.temp_score_fn(temp)
            if score > max_score:
                max_score = score
                max_score_temp = temp

        if max_score < 0:
            logger.warning("No valid temperatures found, returning default values.")
            return 0.0, 0.0

        return max_score, max_score_temp

    def calculate(self, wmi_input: 'WMICalculationInputDTO') -> WMICalculationDTO:
        weather_conditions_result: Tuple[float, str, str] = self._get_max_score_condition(wmi_input.weather_codes)
        weather_score: float = weather_conditions_result[0]
        weather_code: str = weather_conditions_result[1]
        weather_description: str = weather_conditions_result[2]
        logger.debug(f"Max weather score: {weather_score}, code: {weather_code}, description: {weather_description}")

        temp_result: Tuple[float, float] = self._get_max_temp_score(wmi_input.temperature_celsius)
        temp_score: float = temp_result[0]
        temperature_celsius: float = temp_result[1]
        logger.debug(f"Max temperature score: {temp_score}, temperature: {temperature_celsius}")

        by: By = By.WEATHER_CONDITION if weather_score > temp_score else By.TEMPERATURE 
        return WMICalculationDTO(
            value=max(weather_score, temp_score),
            weather_code=weather_code,
            weather_description=weather_description,
            temperature_celsius=temperature_celsius,
            by=by
        )