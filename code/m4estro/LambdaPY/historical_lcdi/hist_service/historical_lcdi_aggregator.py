from typing import Any, Dict, List, Tuple, Optional
from collections import defaultdict

from logger import get_logger
logger = get_logger(__name__)

class HistoricalLCDIAggregator:
    def __init__(
        self,
        dispatch_time_indicators: Optional[List[Dict[str, Any]]] = None,
        shipment_time_indicators: Optional[List[Dict[str, Any]]] = None,
        dri_indicators: Optional[List[Dict[str, Any]]] = None,
        cli_indicators: Optional[List[Dict[str, Any]]] = None,
    ):
        self.dispatch_time_indicators = dispatch_time_indicators or []
        self.shipment_time_indicators = shipment_time_indicators or []
        self.dri_indicators = dri_indicators or []
        self.cli_indicators = cli_indicators or []

    def _extract_supplier_by_site(
        self, *lists_of_indicators: List[Dict[str, Any]]
    ) -> Dict[int, int]:
        mapping: Dict[int, int] = {}
        for indicators in lists_of_indicators:
            for item in indicators:
                site_id = item.get("site", {}).get("id")
                supplier_id = item.get("supplier", {}).get("id")
                if site_id is None:
                    logger.error(f"Missing 'site.id' in item: {item}")
                    continue
                if supplier_id is None:
                    logger.error(f"Missing 'supplier.id' for site {site_id}: {item}")
                    continue
                mapping[site_id] = supplier_id
        return mapping

    def _build_nested_indicators(
        self,
        indicators: List[Dict[str, Any]],
        fields: Tuple[str, ...],
        field_keys: Tuple[str, ...],
    ) -> Dict[Tuple[Any, ...], Dict[str, Any]]:
        """
        Group a flat list of items into a dict keyed by the tuple of
        each item's nested field values, returning merged metric dicts.
        """
        grouped: Dict[Tuple[Any, ...], Dict[str, Any]] = defaultdict(dict)
        if len(fields) != len(field_keys):
            logger.error(f"fields and field_keys must match lengths: {fields}, {field_keys}")
            return grouped

        for item in indicators:
            key_parts: List[Any] = []
            for fld, key in zip(fields, field_keys):
                val = item.get(fld) if fld == key else item.get(fld, {}).get(key)
                key_parts.append(val)

            if any(part is None for part in key_parts):
                idx = key_parts.index(None)
                logger.error(
                    f"Missing field/key ({fields[idx]}.{field_keys[idx]}) in item: {item}"
                )
                continue

            if "indicators" not in item:
                logger.error(f"Missing 'indicators' in item: {item}")
                continue

            grouped[tuple(key_parts)].update(item["indicators"])

        return grouped

    def _build_supplier_features(self, indicators: List[Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
        features: Dict[int, Dict[str, Any]] = defaultdict(dict)
        for item in indicators:
            supplier = item.get("supplier", {})
            supplier_id = supplier.get("id")
            if supplier_id is None:
                logger.error(f"Missing 'supplier.id' in item: {item}")
                continue
            data = {k: v for k, v in supplier.items() if k != "id"}
            features[supplier_id].update(data)
        return features

    def _build_site_features(self, indicators: List[Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
        features: Dict[int, Dict[str, Any]] = defaultdict(dict)
        for item in indicators:
            site = item.get("site", {})
            site_id = site.get("id")
            if site_id is None:
                logger.error(f"Missing 'site.id' in item: {item}")
                continue
            data = {k: v for k, v in site.items() if k != "id"}
            features[site_id].update(data)
        return features

    def _build_carrier_features(self, indicators: List[Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
        features: Dict[int, Dict[str, Any]] = defaultdict(dict)
        for item in indicators:
            carrier = item.get("carrier", {})
            carrier_id = carrier.get("id")
            if carrier_id is None:
                logger.error(f"Missing 'carrier.id' in item: {item}")
                continue
            data = {k: v for k, v in carrier.items() if k != "id"}
            features[carrier_id].update(data)
        return features

    def aggregate(self) -> List[Dict[str, Any]]:
        # 1) Extract features
        site_features: Dict[int, Dict[str, Any]] = self._build_site_features(self.dri_indicators)
        supplier_features: Dict[int, Dict[str, Any]] = self._build_supplier_features(self.dri_indicators)
        carrier_features: Dict[int, Dict[str, Any]] = self._build_carrier_features(self.cli_indicators)

        # 2) Match supplier to site
        supplier_by_site = self._extract_supplier_by_site(
            self.dispatch_time_indicators,
            self.shipment_time_indicators,
            self.dri_indicators,
        )

        # 3) Group indicators
        by_site = self._build_nested_indicators(
            self.dispatch_time_indicators + self.dri_indicators,
            fields=("site",),
            field_keys=("id",),
        )
        by_carrier = self._build_nested_indicators(
            self.cli_indicators,
            fields=("carrier",),
            field_keys=("id",),
        )
        by_site_carrier = self._build_nested_indicators(
            self.shipment_time_indicators,
            fields=("site", "carrier"),
            field_keys=("id", "id"),
        )

        # 4) Build final aggregation
        aggregated: List[Dict[str, Any]] = []
        for (site_id, carrier_id), site_carrier_inds in by_site_carrier.items():
            maybe_supplier_id: Optional[int] = supplier_by_site.get(site_id)
            if maybe_supplier_id is None:
                logger.error(f"No supplier found for site {site_id}")
                continue
            supplier_id: int = maybe_supplier_id

            indicators: Dict[str, Any] = {}
            entry = {
                "site": {
                    "id": site_id,
                    **site_features.get(site_id, {}),
                },
                "supplier": {
                    "id": supplier_id,
                    **supplier_features.get(supplier_id, {}),
                },
                "carrier": {
                    "id": carrier_id,
                    **carrier_features.get(carrier_id, {}),
                },
                "indicators": indicators,
            }

            indicators.update(by_site.get((site_id,), {}))
            indicators.update(by_carrier.get((carrier_id,), {}))
            indicators.update(site_carrier_inds)
            if 'ADT' in indicators and 'AST' in indicators:
                indicators['AODT'] = indicators['ADT'] + indicators['AST']
            if 'DDI' in indicators and 'CTDI' in indicators:
                indicators['ODI'] = {
                    "lower": indicators['DDI']['lower'] + indicators['CTDI']['lower'],
                    "upper": indicators['DDI']['upper'] + indicators['CTDI']['upper'],
                }

            aggregated.append(entry)

        return aggregated
