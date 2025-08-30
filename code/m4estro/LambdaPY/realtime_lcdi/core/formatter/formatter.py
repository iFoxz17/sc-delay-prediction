from typing import TYPE_CHECKING, Dict, Any, List, Optional
from datetime import datetime

import igraph as ig

from dataclasses import dataclass

from graph_config import V_ID_ATTR, TYPE_ATTR

from model.alpha import Alpha, AlphaType
from model.order import OrderStatus
from model.holiday import Holiday, HolidayCategory

from core.executor.executor import ExecutorResult
from core.calculator.tfst.alpha.alpha_dto import AlphaDTO
from core.calculator.dt.holiday.holiday_dto import HolidayDTO

@dataclass(frozen=True)
class EstimatedTimeSharedDTO:
    order_id: int
    manufacturer_order_id: int
    tracking_number: str
    carrier_id: int
    carrier_name: str
    site_id: int
    site_location: str
    supplier_id: int
    manufacturer_supplier_id: int
    supplier_name: str
    manufacturer_id: int
    manufacturer_name: str
    manufacturer_location: str
    SLS: bool
    SRS: bool
    EODT: float
    EDD: datetime  
    dispatch_td_lower: float
    dispatch_td_upper: float
    shipment_td_lower: float
    shipment_td_upper: float
    status: str

if TYPE_CHECKING:
    from model.estimated_time import EstimatedTime
    from model.site import Site
    from model.supplier import Supplier
    from model.carrier import Carrier
    from model.manufacturer import Manufacturer

class Formatter:
    def __init__(self) -> None:
        pass

    def _format_holiday_dto_list(self, holidays: List[HolidayDTO]) -> List[Dict[str, Any]]:
        return [h.to_dict() for h in holidays]
    
    def _format_holiday_list(self, holidays: List[Holiday]) -> List[Dict[str, Any]]:
        return [{
            "id": h.id,
            "name": h.name,
            "country_code": h.country_code,
            "category": h.category.value,
            "description": h.description,
            "type": h.type,
            "date": h.date.isoformat(),
            }
            for h in holidays]
    
    def _format_alpha_params(self, alpha: Alpha | AlphaDTO) -> Optional[Dict[str, Any]]:
        if isinstance(alpha, Alpha):
            match alpha.type:
                case AlphaType.CONST:
                    return {"type": alpha.type.value, "const_value": alpha.value}
                case AlphaType.EXP:
                    return {"type": alpha.type.value, "tt_weight": alpha.tt_weight}
                case AlphaType.MARKOV:
                    return {"type": alpha.type.value}
                
            raise ValueError(f"Unsupported alpha type: {alpha.type}. This should never happen.")
        
        match alpha.type_:
            case AlphaType.CONST:
                return {"type": alpha.type_.value, "const_value": alpha.value}
            case AlphaType.EXP:
                return {"type": alpha.type_.value, "tt_weight": alpha.maybe_tt_weight}
            case AlphaType.MARKOV:
                return {"type": alpha.type_.value}
            
        raise ValueError(f"Unsupported alpha type: {alpha.type_}. This should never happen.")

        
    def _format_alpha(self, alpha: Alpha | AlphaDTO) -> Dict[str, Any]:
        if isinstance(alpha, Alpha):
            alpha_values: Dict[str, Any] = {
                "input": alpha.input,
                "value": alpha.value,
            }
            match alpha.type:
                case AlphaType.CONST:
                    pass
                case AlphaType.EXP:
                    alpha_values["tau"] = alpha.tau
                case AlphaType.MARKOV:
                    alpha_values["tau"] = alpha.tau
                    alpha_values["gamma"] = alpha.gamma
                case _:
                    raise ValueError(f"Unsupported alpha type: {alpha.type}. This should never happen.")

            return alpha_values

        alpha_values: Dict[str, Any] = {
            "input": alpha.input,
            "value": alpha.value,
        }
        match alpha.type_:
            case AlphaType.CONST:
                pass
            case AlphaType.EXP:
                alpha_values["tau"] = alpha.maybe_tau
            case AlphaType.MARKOV:
                alpha_values["tau"] = alpha.maybe_tau
                alpha_values["gamma"] = alpha.maybe_gamma
            case _:
                raise ValueError(f"Unsupported alpha type: {alpha.type_}. This should never happen.")
        return alpha_values
        

    def _format_basic_info(self, et: 'EstimatedTime') -> Dict[str, Any]:
        closure_holidays: List[Holiday] = []
        working_holidays: List[Holiday] = []
        for holiday in et.holidays:
            match holiday.category:
                case HolidayCategory.CLOSURE:
                    closure_holidays.append(holiday)
                case HolidayCategory.WORKING:
                    working_holidays.append(holiday)
        
        return {
                "id": et.id,
                "vertex": {
                    "id": et.vertex_id,
                    "name": et.vertex.name,
                    "type": et.vertex.type.value,
                },

                "order_time": et.order.manufacturer_creation_timestamp.isoformat(),
                "shipment_time": et.shipment_time.isoformat(),
                "event_time": et.event_time.isoformat(),
                "estimation_time": et.estimation_time.isoformat(),

                "status": et.status,

                "indicators": {
                    "parameters": {
                        "DT": {
                            "holidays": {
                                "consider_closure_holidays": et.estimation_params.consider_closure_holidays,
                                "consider_working_holidays": et.estimation_params.consider_working_holidays,
                                "consider_weekends_holidays": et.estimation_params.consider_weekends_holidays,
                            },
                            "confidence": et.estimation_params.dt_confidence,
                        },
                        "alpha": self._format_alpha_params(et.alpha),
                        "PT": {
                            "RTEstimator": {
                                "model_mape": et.estimation_params.rte_mape,
                                "use_model": et.estimation_params.use_rte_model
                            },
                            "TMI": {
                                "use_traffic_service": et.estimation_params.use_traffic_service,
                                "max_timediff_hours": et.estimation_params.tmi_max_timediff_hours,
                            },
                            "WMI": {
                                "use_weather_service": et.estimation_params.use_weather_service,
                                "max_timediff_hours": et.estimation_params.wmi_max_timediff_hours,
                                "step_distance_km": et.estimation_params.wmi_step_distance_km,
                                "max_points": et.estimation_params.wmi_max_points,
                            },
                            "path_min_prob": et.estimation_params.pt_path_min_prob,
                            "max_paths": et.estimation_params.pt_max_paths,
                            "ext_data_min_prob": et.estimation_params.pt_ext_data_min_prob,
                            "confidence": et.estimation_params.pt_confidence,
                        },
                        "TT": {
                            "confidence": et.estimation_params.tt_confidence,
                        },
                        "TFST": {
                            "tolerance": et.estimation_params.tfst_tolerance,
                        },
                        "delay": {
                            "dispatch_confidence": et.time_deviation.dt_confidence,
                            "shipment_confidence": et.time_deviation.st_confidence,
                        },
                    },

                    "TMI": et.PT_avg_tmi,
                    "WMI": et.PT_avg_wmi,

                    "DT": {
                        "lower": et.DT_lower,
                        "mean": et.DT,
                        "upper": et.DT_upper,
                        "holidays": {
                            "closure": {
                                "n": len(closure_holidays),
                                "days": self._format_holiday_list(closure_holidays)
                            },
                            "working": {
                                "n": len(working_holidays),
                                "days": self._format_holiday_list(working_holidays)
                            },
                            "weekends": {
                                "n": et.DT_weekend_days,
                                "days": None,               # Weekend days are not stored in the database
                            },   
                        }
                    },
                    "alpha": self._format_alpha(et.alpha),
                    "TT": {
                        "lower": et.TT_lower,
                        "upper": et.TT_upper,
                    },
                    "PT": {
                        "n_paths": et.PT_n_paths,
                        "lower": et.PT_lower,
                        "upper": et.PT_upper,
                    },
                    "TFST": {
                        "lower": et.TFST_lower,
                        "upper": et.TFST_upper,
                    },
                    "EST": et.EST,
                    "CFDI": {
                        "lower": et.CFDI_lower,
                        "upper": et.CFDI_upper,
                    },
                    "EODT": et.EODT,
                    "EDD": et.EDD.isoformat(),
                    "delay": {
                        "dispatch": {
                            "lower": et.time_deviation.dt_hours_lower,
                            "upper": et.time_deviation.dt_hours_upper
                        },
                        "shipment": {
                            "lower": et.time_deviation.st_hours_lower,
                            "upper": et.time_deviation.st_hours_upper
                        },
                        "total": {
                            "lower": et.time_deviation.dt_hours_lower + et.time_deviation.st_hours_lower,
                            "upper": et.time_deviation.dt_hours_upper + et.time_deviation.st_hours_upper
                        }
                    }
                }
            } 

    def format_et(self, et: 'EstimatedTime') -> Dict[str, Any]:
        basic_info = self._format_basic_info(et)
        return {
            **basic_info,
            "order": {
                "id": et.order.id,
                "manufacturer_order_id": et.order.manufacturer_order_id,
                "tracking_number": et.order.tracking_number,
                "SLS": et.order.SLS,
                "SRS": et.order.SRS,
            },
            "site": {
                "id": et.order.site.id,
                "location": et.order.site.location.name
            },
            "supplier": {
                "id": et.order.site.supplier.id,
                "manufacturer_id": et.order.site.supplier.manufacturer_supplier_id,
                "name": et.order.site.supplier.name
            },
            "carrier": {
                "id": et.order.carrier_id,
                "name": et.order.carrier.name
            },
            "manufacturer": {
                "id": et.order.manufacturer.id,
                "name": et.order.manufacturer.name,
                "location": et.order.manufacturer.location_name
            }
        }
    
    def format_et_by_order(self, shared: EstimatedTimeSharedDTO, ets: List['EstimatedTime']) -> Dict[str, Any]:
        return {
            "order_id": shared.order_id,
            "manufacturer_order_id": shared.manufacturer_order_id,
            "tracking_number": shared.tracking_number,

            "site": {
                "id": shared.site_id,
                "location": shared.site_location
            },
            "supplier": {
                "id": shared.supplier_id,
                "manufacturer_id": shared.manufacturer_order_id,
                "name": shared.supplier_name
            },
            "carrier": {
                "id": shared.carrier_id,
                "name": shared.carrier_name
            },
            "manufacturer": {
                "id": shared.manufacturer_id,
                "name": shared.manufacturer_name,
                "location": shared.manufacturer_location
            },

            "SLS": shared.SLS,
            "SRS": shared.SRS,
            
            "EODT": shared.EODT,            
            "EDD": shared.EDD.isoformat(),
            "delay": {
                "dispatch": {
                    "lower": shared.dispatch_td_lower,
                    "upper": shared.dispatch_td_upper
                },
                "shipment": {
                    "lower": shared.shipment_td_lower,
                    "upper": shared.shipment_td_upper
                },
                "total": {
                    "lower": shared.dispatch_td_lower + shared.shipment_td_lower,
                    "upper": shared.dispatch_td_upper + shared.shipment_td_upper
                }
            },

            "status": shared.status,

            "data": [
                self._format_basic_info(et)
                for et in ets
            ]
        }
    
    def format_volatile_result(self, 
                               vertex: ig.Vertex, 
                               site: 'Site',
                               supplier: 'Supplier',
                               carrier: 'Carrier',
                               manufacturer: 'Manufacturer',
                               executor_result: 'ExecutorResult',
                               status: OrderStatus
                               ) -> Dict[str, Any]:
                    
        return {
            "site": {
                "id": site.id,
                "location": site.location_name
            },
            "supplier": {
                "id": supplier.id,
                "manufacturer_id": supplier.manufacturer_supplier_id,
                "name": supplier.name
            },
            "carrier": {
                "id": carrier.id,
                "name": carrier.name
            },
            "manufacturer": {
                "id": manufacturer.id,
                "name": manufacturer.name,
                "location": manufacturer.location_name
            },
            "vertex": {
                "id": vertex[V_ID_ATTR],
                "name": vertex["name"],
                "type": vertex[TYPE_ATTR]
            },

            "order_time": executor_result.time_sequence.order_time.isoformat(),
            "shipment_time": executor_result.time_sequence.shipment_time.isoformat(),
            "event_time": executor_result.time_sequence.event_time.isoformat(),
            "estimation_time": executor_result.time_sequence.estimation_time.isoformat(),

            "status": status.value,

            "indicators": {
                "parameters": {
                    "DT": {
                        "holidays": {
                            "consider_closure_holidays": executor_result.dt.elapsed_holidays.consider_closure_holidays,
                            "consider_working_holidays": executor_result.dt.elapsed_holidays.consider_working_holidays,
                            "consider_weekends_holidays": executor_result.dt.elapsed_holidays.consider_weekends_holidays,
                        },
                        "confidence": executor_result.dt.confidence,
                    },
                    "alpha": self._format_alpha_params(executor_result.tfst_executor_result.alpha),
                    "PT": executor_result.tfst_executor_result.pt.params.to_dict(),
                    "TT": {
                        "tt_confidence": executor_result.tfst_executor_result.tt.confidence,
                    },
                    "TFST": {
                        "tolerance": executor_result.tfst_executor_result.tfst.tolerance,
                    },
                    "delay": {
                        "dispatch_confidence": executor_result.time_deviation.dt_confidence,
                        "shipment_confidence": executor_result.time_deviation.st_confidence,
                    },
                },

                "TMI": executor_result.tfst_executor_result.pt.avg_tmi,
                "WMI": executor_result.tfst_executor_result.pt.avg_wmi,

                "DT": {
                    "elapsed": {
                        "value": {
                            "working": executor_result.dt.elapsed_working_time,
                            "total": executor_result.dt.elapsed_time
                        },
                        "holidays": {
                            "closure": {
                                "n": len(executor_result.dt.elapsed_holidays.closure_holidays),
                                "days": self._format_holiday_dto_list(executor_result.dt.elapsed_holidays.closure_holidays)
                            },
                            "working": {
                                "n": len(executor_result.dt.elapsed_holidays.working_holidays),
                                "days": self._format_holiday_dto_list(executor_result.dt.elapsed_holidays.working_holidays)
                            },
                            "weekends": {
                                "n": len(executor_result.dt.elapsed_holidays.weekend_holidays),
                                "days": self._format_holiday_dto_list(executor_result.dt.elapsed_holidays.weekend_holidays)
                            },
                        }

                    },
                    "remaining": {
                        "value": {
                            "working": {
                                "lower": executor_result.dt.remaining_working_time_lower,
                                "mean": executor_result.dt.remaining_working_time,
                                "upper": executor_result.dt.remaining_working_time_upper
                            },
                            "total": {
                                "lower": executor_result.dt.remaining_time_lower,
                                "mean": executor_result.dt.remaining_time,
                                "upper": executor_result.dt.remaining_time_upper
                            }
                        },
                        "holidays": {
                            "closure": {
                                "n": len(executor_result.dt.remaining_holidays.closure_holidays),
                                "days": self._format_holiday_dto_list(executor_result.dt.remaining_holidays.closure_holidays)
                            },
                            "working": {
                                "n": len(executor_result.dt.remaining_holidays.working_holidays),
                                "days": self._format_holiday_dto_list(executor_result.dt.remaining_holidays.working_holidays)
                            },
                            "weekends": {
                                "n": len(executor_result.dt.remaining_holidays.weekend_holidays),
                                "days": self._format_holiday_dto_list(executor_result.dt.remaining_holidays.weekend_holidays)
                            },
                        }
                    },
                    "total": {
                        "value": {
                            "working": {
                                'lower': executor_result.dt.total_working_time_lower,
                                'mean': executor_result.dt.total_working_time,
                                'upper': executor_result.dt.total_working_time_upper
                            },
                            "total": {
                                'lower': executor_result.dt.total_time_lower,
                                'mean': executor_result.dt.total_time,
                                'upper': executor_result.dt.total_time_upper
                            }
                        },
                        "holidays": {
                            "closure": {
                                "n": len(executor_result.dt.total_holidays.closure_holidays),
                                "days": self._format_holiday_dto_list(executor_result.dt.total_holidays.closure_holidays)
                            },
                            "working": {
                                "n": len(executor_result.dt.total_holidays.working_holidays),
                                "days": self._format_holiday_dto_list(executor_result.dt.total_holidays.working_holidays)
                            },
                            "weekends": {
                                "n": len(executor_result.dt.total_holidays.weekend_holidays),
                                "days": self._format_holiday_dto_list(executor_result.dt.total_holidays.weekend_holidays)
                            },
                        }
                    },
                },
                "alpha": self._format_alpha(executor_result.tfst_executor_result.alpha),    
                "TT": {
                    "lower": executor_result.tfst_executor_result.tt.lower,
                    "upper": executor_result.tfst_executor_result.tt.upper,
                },
                "PT": {
                    "n_paths": executor_result.tfst_executor_result.pt.n_paths,
                    "lower": executor_result.tfst_executor_result.pt.lower,
                    "upper": executor_result.tfst_executor_result.pt.upper,
                    "tmi_data": [
                        tmi.to_dict() for tmi in executor_result.tfst_executor_result.pt.tmi_data
                    ],
                    "wmi_data": [
                        wmi.to_dict() for wmi in executor_result.tfst_executor_result.pt.wmi_data
                    ],
                },
                "TFST": {
                    "computed": executor_result.tfst_executor_result.tfst.computed.value,
                    "lower": executor_result.tfst_executor_result.tfst.lower,
                    "upper": executor_result.tfst_executor_result.tfst.upper,
                },
                "EST": executor_result.est.value,
                "CFDI": {
                    "lower": executor_result.cfdi.lower,
                    "upper": executor_result.cfdi.upper,
                },
                "EODT": executor_result.eodt.value,
                "EDD": executor_result.edd.value.isoformat(),
                "delay": {
                    "dispatch": {
                        "lower": executor_result.time_deviation.dt_td_lower,
                        "upper": executor_result.time_deviation.dt_td_upper
                    },
                    "shipment": {
                        "lower": executor_result.time_deviation.st_td_lower,
                        "upper": executor_result.time_deviation.st_td_upper
                    },
                    "total": {
                        "lower": executor_result.time_deviation.dt_td_lower + executor_result.time_deviation.st_td_lower,
                        "upper": executor_result.time_deviation.dt_td_upper + executor_result.time_deviation.st_td_upper
                    }
                }
            }
        } 