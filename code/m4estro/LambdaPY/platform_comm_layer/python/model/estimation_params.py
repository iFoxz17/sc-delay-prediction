from sqlalchemy.orm import Mapped, mapped_column

from model.base import Base

ESTIMATION_PARAMS_TABLE_NAME = 'estimation_params'

class EstimationParams(Base):
    __tablename__ = ESTIMATION_PARAMS_TABLE_NAME

    id: Mapped[int] = mapped_column(primary_key=True)
    
    # DT parameters
    dt_confidence: Mapped[float] = mapped_column(nullable=False)
    # Holidays parameters
    consider_closure_holidays: Mapped[bool] = mapped_column(nullable=False)
    consider_working_holidays: Mapped[bool] = mapped_column(nullable=False)
    consider_weekends_holidays: Mapped[bool] = mapped_column(nullable=False)

    # Route time estimator parameters
    rte_mape: Mapped[float] = mapped_column(nullable=False)
    use_rte_model: Mapped[bool] = mapped_column(nullable=False)

    # TMI parameters
    use_traffic_service: Mapped[bool] = mapped_column(nullable=False)
    tmi_max_timediff_hours: Mapped[float] = mapped_column(nullable=False)

    # WMI parameters
    use_weather_service: Mapped[bool] = mapped_column(nullable=False)
    wmi_max_timediff_hours: Mapped[float] = mapped_column(nullable=False)
    wmi_step_distance_km: Mapped[float] = mapped_column(nullable=False)
    wmi_max_points: Mapped[int] = mapped_column(nullable=False)

    # PT parameters
    pt_path_min_prob: Mapped[float] = mapped_column(nullable=False)
    pt_max_paths: Mapped[int] = mapped_column(nullable=False)
    pt_ext_data_min_prob: Mapped[float] = mapped_column(nullable=False)
    pt_confidence: Mapped[float] = mapped_column(nullable=False)

    # TT parameters
    tt_confidence: Mapped[float] = mapped_column(nullable=False)

    # TFST parameters
    tfst_tolerance: Mapped[float] = mapped_column(nullable=False)

    def __str__(self) -> str:
        return (f"EstimationParams(id={self.id}, "
                f"dt_confidence={self.dt_confidence}, "
                f"consider_closure_holidays={self.consider_closure_holidays}, "
                f"consider_working_holidays={self.consider_working_holidays}, "
                f"consider_weekends_holidays={self.consider_weekends_holidays}, "
                f"rte_mape={self.rte_mape}, "
                f"use_traffic_service={self.use_traffic_service}, "
                f"tmi_max_timediff_hours={self.tmi_max_timediff_hours}, "
                f"use_weather_service={self.use_weather_service}, "
                f"weather_max_timediff_hours={self.wmi_max_timediff_hours}, "
                f"wmi_step_distance_km={self.wmi_step_distance_km}, "
                f"wmi_max_points={self.wmi_max_points}, "
                f"pt_path_min_prob={self.pt_path_min_prob}, "
                f"pt_max_paths={self.pt_max_paths}, "
                f"pt_ext_data_min_prob={self.pt_ext_data_min_prob}, "
                f"pt_confidence={self.pt_confidence}, "
                f"tt_confidence={self.tt_confidence}, "
                f"tfst_tollerance={self.tfst_tollerance})")
