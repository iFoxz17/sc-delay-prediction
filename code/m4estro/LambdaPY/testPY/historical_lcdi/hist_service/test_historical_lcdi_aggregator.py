import pytest
from hist_service.historical_lcdi_aggregator import HistoricalLCDIAggregator

import pytest
from hist_service.historical_lcdi_aggregator import HistoricalLCDIAggregator

def test_extract_supplier_by_site_basic(caplog):
    aggregator = HistoricalLCDIAggregator()
    data = [
        {"site": {"id": 1, "location": "loc1"}, "supplier": {"id": 100, "name": "s1"}},
        {"site": {"id": 2, "location": "loc2"}, "supplier": {"id": 200, "name": "s2"}},
    ]
    mapping = aggregator._extract_supplier_by_site(data)
    assert mapping == {1: 100, 2: 200}

def test_extract_supplier_by_site_missing_fields(caplog):
    aggregator = HistoricalLCDIAggregator()
    data = [
        {"supplier": {"id": 100, "name": "s1"}},  # missing site
        {"site": {"id": 2, "location": "loc2"}},  # missing supplier
        {"site": {"id": 3, "location": "loc3"}, "supplier": {"id": 300, "name": "s3"}}
    ]
    with caplog.at_level("WARNING"):
        mapping = aggregator._extract_supplier_by_site(data)

    assert mapping == {3: 300}
    assert any("Missing" in msg for msg in caplog.messages)
    assert any("Missing" in msg for msg in caplog.messages)

def test_build_nested_indicators_basic(caplog):
    aggregator = HistoricalLCDIAggregator()
    indicators = [
        {"site": {"id": 1, "location": "loc1"}, "indicators": {"metric1": 10}},
        {"site": {"id": 1, "location": "loc1"}, "indicators": {"metric2": 20}},
        {"site": {"id": 1, "location": "loc1"}, "indicators": {"metric3": 30}},
        {"site": {"id": 2, "location": "loc2"}, "indicators": {"metric1": 5}},
    ]
    grouped = aggregator._build_nested_indicators(indicators, ("site",), ("id",))
    expected = {
        (1,): {"metric1": 10, "metric2": 20, "metric3": 30},
        (2,): {"metric1": 5}
    }
    assert grouped == expected

def test_build_nested_indicators_missing_fields(caplog):
    aggregator = HistoricalLCDIAggregator()
    indicators = [
        {"indicators": {"metric1": 10}},  # missing 'site'
        {"site": {"id": 1, "location": "loc1"}},  # missing 'indicators'
        {"site": {"id": 2, "location": "loc2"}, "indicators": {"metric2": 20}},
    ]
    with caplog.at_level("WARNING"):
        grouped = aggregator._build_nested_indicators(indicators, ("site",), ("id",))

    expected = {
        (2,): {"metric2": 20}
    }
    assert grouped == expected
    assert any("Missing" in msg for msg in caplog.messages)
    assert any("Missing 'indicators'" in msg for msg in caplog.messages)

def test_build_supplier_features_basic():
    aggregator = HistoricalLCDIAggregator()
    indicators = [
        {"site": {"id": 1, "location": "location1"}, "supplier": {"id": 1, "name": "Supplier A"}},
        {"site": {"id": 2, "location": "location2"}, "supplier": {"id": 2, "name": "Supplier B", "test": "test"}},
        {"site": {"id": 3, "test": "test"}, "supplier": {"id": 1, "rating": "A+"}},  
    ]
    result = aggregator._build_supplier_features(indicators)

    expected = {
        1: {"name": "Supplier A", "rating": "A+"},
        2: {"name": "Supplier B", "test": "test"},
    }
    assert dict(result) == expected

def test_build_site_features_basic():
    aggregator = HistoricalLCDIAggregator()
    indicators = [
        {"site": {"id": 1, "location": "location1"}, "supplier": {"id": 1, "name": "Supplier A"}},
        {"site": {"id": 2, "location": "location2"}, "supplier": {"id": 2, "name": "Supplier B", "test": "test"}},
        {"site": {"id": 3, "test": "test"}, "supplier": {"id": 1, "rating": "A+"}},  
    ]
    result = aggregator._build_site_features(indicators)

    expected = {
        1: {"location": "location1"},
        2: {"location": "location2"},
        3: {"test": "test"},
    }
    assert dict(result) == expected


@pytest.mark.parametrize(
    "dispatch, delivery, dri, cli, expected_count, expected_combinations, expected_suppliers, expected_indicator_keys",
    [
        # Test case 0: Normal case with multiple sites, suppliers, and carriers
        (
            [
                {"site": {"id": 1, "location": "location1"}, "supplier": {"id": 1, "name": "supplier1"}, "indicators": {"ADT": 56.8, "DDI": {"lower": 1.2, "upper": 3.55}}},
                {"site": {"id": 2, "location": "location2"}, "supplier": {"id": 1, "name": "supplier1"}, "indicators": {"ADT": 45.0, "DDI": {"lower": 1.0, "upper": 2.5}}},
                {"site": {"id": 3, "location": "location3"}, "supplier": {"id": 2, "name": "supplier2"}, "indicators": {"ADT": 60.0, "DDI": {"lower": 1.5, "upper": 4.0}}}
            ],
            [
                {"site": {"id": 1, "location": "location1"}, "supplier": {"id": 1, "name": "supplier1"}, "carrier": {"id": 1, "name": "ups"}, "indicators": {"AST": 56.8, "CTDI": {"lower": 1.2, "upper": 3.55}}},
                {"site": {"id": 1, "location": "location1"}, "supplier": {"id": 1, "name": "supplier1"}, "carrier": {"id": 3, "name": "fedex"}, "indicators": {"AST": 16.8, "CTDI": {"lower": 0.2, "upper": 5.55}}},
                {"site": {"id": 2, "location": "location2"}, "supplier": {"id": 1, "name": "supplier1"}, "carrier": {"id": 3, "name": "fedex"}, "indicators": {"AST": 45.0, "CTDI": {"lower": 1.0, "upper": 2.5}}},
                {"site": {"id": 2, "location": "location2"}, "supplier": {"id": 1, "name": "supplier1"}, "carrier": {"id": 1, "name": "ups"}, "indicators": {"AST": 50.0, "CTDI": {"lower": 1.0, "upper": 3.0}}},
                {"site": {"id": 3, "location": "location3"}, "supplier": {"id": 2, "name": "supplier2"}, "carrier": {"id": 2, "name": "dhl"}, "indicators": {"AST": 55.0, "CTDI": {"lower": 1.5, "upper": 4.5}}}
            ],
            [
                {"site": {"id": 1, "location": "location1"}, "supplier": {"id": 1, "name": "supplier1"}, "indicators": {"DRI": 0.09}},
                {"site": {"id": 2, "location": "location2"}, "supplier": {"id": 1, "name": "supplier1"}, "indicators": {"DRI": 0.03}},
                {"site": {"id": 3, "location": "location3"}, "supplier": {"id": 2, "name": "supplier2"}, "indicators": {"DRI": 0.1}}
            ],
            [
                {"carrier": {"id": 1, "name": "ups"}, "indicators": {"CLI": 0.1}},
                {"carrier": {"id": 3, "name": "fedex"}, "indicators": {"CLI": 0.05}},
                {"carrier": {"id": 2, "name": "dhl"}, "indicators": {"CLI": 0.08}}
            ],
            5,
            [(1, "ups"), (1, "fedex"), (2, "fedex"), (2, "ups"), (3, "dhl")],
            {1: 1, 2: 1, 3: 2},
            {"ADT", "DDI", "AST", "CTDI", "DRI", "CLI", "AODT", "ODI"}
        ),

        # Test case 1: Single site with one supplier and one carrier, with all indicators present
        (
            [{"site": {"id": 1, "location": "location1"}, "supplier": {"id": 1, "name": "supplier1"}, "indicators": {"ADT": 10.0, "DDI": {"lower": 1.0, "upper": 2.0}}}],
            [{"site": {"id": 1, "location": "location1"}, "supplier": {"id": 1, "name": "supplier1"}, "carrier": {"id": 3, "name": "fedex"}, "indicators": {"AST": 20.0, "CTDI": {"lower": 0.5, "upper": 1.5}}}],
            [{"site": {"id": 1, "location": "location1"}, "supplier": {"id": 1, "name": "supplier1"}, "indicators": {"DRI": 0.1}}],
            [{"carrier": {"id": 3, "name": "fedex"}, "indicators": {"CLI": 0.05}}],
            1,
            [(1, "fedex")],
            {1: 1},
            {"ADT", "DDI", "AST", "CTDI", "DRI", "CLI", "AODT", "ODI"}
        ),

        # Test case 2: Multiple sites with different suppliers and carriers, with some optional indicators
        (
            [{"site": {"id": 2, "location": "location2"}, "supplier": {"id": 2, "name": "supplier2"}, "indicators": {"ADT": 30.0, "DDI": {"lower": 1.1, "upper": 3.3}}}],
            [
                {"site": {"id": 2, "location": "location2"}, "supplier": {"id": 2, "name": "supplier2"}, "carrier": {"id": 1, "name": "ups"}, "indicators": {"AST": 35.0, "CTDI": {"lower": 0.8, "upper": 2.5}}},
                {"site": {"id": 2, "location": "location2"}, "supplier": {"id": 2, "name": "supplier2"}, "carrier": {"id": 2, "name": "dhl"}, "indicators": {"AST": 36.0, "CTDI": {"lower": 0.7, "upper": 2.2}}}
            ],
            [{"site": {"id": 2, "location": "location2"}, "supplier": {"id": 2, "name": "supplier2"}, "indicators": {"DRI": 0.05}}],
            [
                {"carrier": {"id": 1, "name": "ups"}, "indicators": {"CLI": 0.02}},
                {"carrier": {"id": 2, "name": "dhl"}, "indicators": {"CLI": 0.03}}
            ],
            2,
            [(2, "ups"), (2, "dhl")],
            {2: 2},
            {"ADT", "DDI", "AST", "CTDI", "DRI", "CLI", "AODT", "ODI"}
        ),
                # Test case 3: Single site with one carrier
        (
            # dispatch
            [{"site": {"id": 4, "location": "location4"}, "supplier": {"id": 4, "name": "supplier4"}, "indicators": {"ADT": 70.0, "DDI": {"lower": 1.5, "upper": 5.0}}}],
            # delivery
            [{"site": {"id": 4, "location": "location4"}, "supplier": {"id": 4, "name": "supplier4"}, "carrier": {"id": 1, "name": "dhl"}, "indicators": {"AST": 65.0, "CTDI": {"lower": 1.0, "upper": 4.5}}}],
            # dri
            [{"site": {"id": 4, "location": "location4"}, "supplier": {"id": 4, "name": "supplier4"}, "indicators": {"DRI": 0.2}}],
            # cli
            [{"carrier": {"id": 1, "name": "dhl"}, "indicators": {"CLI": 0.04}}],
            # expected_count
            1,
            # expected_combinations
            [(4, "dhl")],
            # expected_suppliers
            {4: 4},
            # expected_indicator_keys
            {"ADT", "DDI", "AST", "CTDI", "DRI", "CLI", "AODT", "ODI"}
        ),

        # Test case 4: Single site with multiple carriers
        (
            # dispatch
            [{"site": {"id": 5, "location": "location5"}, "supplier": {"id": 5, "name": "supplier5"}, "indicators": {"ADT": 90.0, "DDI": {"lower": 2.0, "upper": 6.0}}}],
            # delivery
            [
                {"site": {"id": 5, "location": "location5"}, "supplier": {"id": 5, "name": "supplier5"}, "carrier": {"id": 3, "name": "fedex"}, "indicators": {"AST": 80.0, "CTDI": {"lower": 2.0, "upper": 5.0}}}, 
                {"site": {"id": 5, "location": "location5"}, "supplier": {"id": 5, "name": "supplier5"}, "carrier": {"id": 1, "name": "ups"},   "indicators": {"AST": 85.0, "CTDI": {"lower": 2.5, "upper": 5.5}}}, 
                {"site": {"id": 5, "location": "location5"}, "supplier": {"id": 5, "name": "supplier5"}, "carrier": {"id": 2, "name": "dhl"},   "indicators": {"AST": 88.0, "CTDI": {"lower": 2.8, "upper": 5.8}}}
            ],
            # dri
            [{"site": {"id": 5, "location": "location5"}, "supplier": {"id": 5, "name": "supplier5"}, "indicators": {"DRI": 0.15}}],
            # cli
            [
                {"carrier": {"id": 2, "name": "dhl"}, "indicators": {"CLI": 0.05}},
                {"carrier": {"id": 1, "name": "ups"}, "indicators": {"CLI": 0.06}},
                {"carrier": {"id": 3, "name": "fedex"}, "indicators": {"CLI": 0.07}}
            ],
            # expected_count
            3,
            # expected_combinations
            [(5, "fedex"), (5, "ups"), (5, "dhl")],
            # expected_suppliers
            {5: 5},
            # expected_indicator_keys
            {"ADT", "DDI", "AST", "CTDI", "DRI", "CLI", "AODT", "ODI"}
        ),
    ]
)
def test_aggregate_historical_indicators(
    dispatch,
    delivery,
    dri,
    cli,
    expected_count,
    expected_combinations,
    expected_suppliers,
    expected_indicator_keys,
):
    aggregator = HistoricalLCDIAggregator(
        dispatch_time_indicators=dispatch,
        shipment_time_indicators=delivery,
        dri_indicators=dri,
        cli_indicators=cli
    )
    result = aggregator.aggregate()

    assert len(result) == expected_count

    for site, carrier in expected_combinations:
        entry = next((e for e in result if e["site"]['id'] == site and e["carrier"]['name'] == carrier), None)
        assert entry is not None, f"Missing entry for site={site}, carrier={carrier}"

        assert "supplier" in entry
        assert "indicators" in entry
        assert isinstance(entry["indicators"], dict) 
        assert entry["supplier"]['id'] == expected_suppliers[entry["site"]['id']]
        assert entry["carrier"]['name'] == carrier

        keys = set(entry["indicators"].keys())
        assert keys == expected_indicator_keys, f"Unexpected indicator keys in entry for site={site}, carrier={carrier}: {keys}"



'''
# Test case 3: Single site with multiple carriers
        (
            [{"site": 4, "supplier": 4, "indicators": {"ADT": 70.0, "DDI": {"lower": 1.5, "upper": 5.0}}}],
            [{"site": 4, "supplier": 4, "carrier": "dhl", "indicators": {"AST": 65.0, "CTDI": {"lower": 1.0, "upper": 4.5}}}],
            [{"site": 4, "supplier": 4, "indicators": {"DRI": 0.2}}],
            [{"carrier": "dhl", "indicators": {"CLI": 0.04}}],
            1,
            [(4, "dhl")],
            {4: 4},
            {"ADT", "DDI", "AST", "CTDI", "DRI", "CLI"},
        ),

        # Test case 4: Single site with multiple carriers
        (
            [{"site": 5, "supplier": 5, "indicators": {"ADT": 90.0, "DDI": {"lower": 2.0, "upper": 6.0}}}],
            [
                {"site": 5, "supplier": 5, "carrier": "fedex", "indicators": {"AST": 80.0, "CTDI": {"lower": 2.0, "upper": 5.0}}},
                {"site": 5, "supplier": 5, "carrier": "ups", "indicators": {"AST": 85.0, "CTDI": {"lower": 2.5, "upper": 5.5}}},
                {"site": 5, "supplier": 5, "carrier": "dhl", "indicators": {"AST": 88.0, "CTDI": {"lower": 2.8, "upper": 5.8}}}
            ],
            [{"site": 5, "supplier": 5, "indicators": {"DRI": 0.15}}],
            [
                {"carrier": "fedex", "indicators": {"CLI": 0.05}},
                {"carrier": "ups", "indicators": {"CLI": 0.06}},
                {"carrier": "dhl", "indicators": {"CLI": 0.07}}
            ],
            3,
            [(5, "fedex"), (5, "ups"), (5, "dhl")],
            {5: 5},
            {"ADT", "DDI", "AST", "CTDI", "DRI", "CLI"},
        ),

        # Test case 5: Complete grid with 3 suppliers, 5 sites, 3 carriers (dhl, fedex, ups)
        (
            # Dispatch: one entry per site
            [
                {"site": 1, "supplier": 1, "indicators": {"ADT": 10.0, "DDI": {"lower": 1.0, "upper": 2.0}}},
                {"site": 2, "supplier": 1, "indicators": {"ADT": 20.0, "DDI": {"lower": 1.1, "upper": 2.1}}},
                {"site": 3, "supplier": 2, "indicators": {"ADT": 30.0, "DDI": {"lower": 1.2, "upper": 2.2}}},
                {"site": 4, "supplier": 2, "indicators": {"ADT": 40.0, "DDI": {"lower": 1.3, "upper": 2.3}}},
                {"site": 5, "supplier": 3, "indicators": {"ADT": 50.0, "DDI": {"lower": 1.4, "upper": 2.4}}}
            ],
            # Delivery: a delivery entry for each site and each carrier ("dhl", "fedex", "ups")
            [
                # Site 1
                {"site": 1, "supplier": 1, "carrier": "dhl", "indicators": {"AST": 11.0, "CTDI": {"lower": 0.9, "upper": 1.9}}},
                {"site": 1, "supplier": 1, "carrier": "fedex", "indicators": {"AST": 12.0, "CTDI": {"lower": 1.0, "upper": 2.0}}},
                {"site": 1, "supplier": 1, "carrier": "ups", "indicators": {"AST": 13.0, "CTDI": {"lower": 1.1, "upper": 2.1}}},
                # Site 2
                {"site": 2, "supplier": 1, "carrier": "dhl", "indicators": {"AST": 21.0, "CTDI": {"lower": 1.9, "upper": 2.9}}},
                {"site": 2, "supplier": 1, "carrier": "fedex", "indicators": {"AST": 22.0, "CTDI": {"lower": 2.0, "upper": 3.0}}},
                {"site": 2, "supplier": 1, "carrier": "ups", "indicators": {"AST": 23.0, "CTDI": {"lower": 2.1, "upper": 3.1}}},
                # Site 3
                {"site": 3, "supplier": 2, "carrier": "dhl", "indicators": {"AST": 31.0, "CTDI": {"lower": 2.9, "upper": 3.9}}},
                {"site": 3, "supplier": 2, "carrier": "fedex", "indicators": {"AST": 32.0, "CTDI": {"lower": 3.0, "upper": 4.0}}},
                {"site": 3, "supplier": 2, "carrier": "ups", "indicators": {"AST": 33.0, "CTDI": {"lower": 3.1, "upper": 4.1}}},
                # Site 4
                {"site": 4, "supplier": 2, "carrier": "dhl", "indicators": {"AST": 41.0, "CTDI": {"lower": 3.9, "upper": 4.9}}},
                {"site": 4, "supplier": 2, "carrier": "fedex", "indicators": {"AST": 42.0, "CTDI": {"lower": 4.0, "upper": 5.0}}},
                {"site": 4, "supplier": 2, "carrier": "ups", "indicators": {"AST": 43.0, "CTDI": {"lower": 4.1, "upper": 5.1}}},
                # Site 5
                {"site": 5, "supplier": 3, "carrier": "dhl", "indicators": {"AST": 51.0, "CTDI": {"lower": 4.9, "upper": 5.9}}},
                {"site": 5, "supplier": 3, "carrier": "fedex", "indicators": {"AST": 52.0, "CTDI": {"lower": 5.0, "upper": 6.0}}},
                {"site": 5, "supplier": 3, "carrier": "ups", "indicators": {"AST": 53.0, "CTDI": {"lower": 5.1, "upper": 6.1}}}
            ],
            # DRI: one per site
            [
                {"site": 1, "supplier": 1, "indicators": {"DRI": 0.11}},
                {"site": 2, "supplier": 1, "indicators": {"DRI": 0.22}},
                {"site": 3, "supplier": 2, "indicators": {"DRI": 0.33}},
                {"site": 4, "supplier": 2, "indicators": {"DRI": 0.44}},
                {"site": 5, "supplier": 3, "indicators": {"DRI": 0.55}}
            ],
            # CLI: one per carrier
            [
                {"carrier": "dhl", "indicators": {"CLI": 0.101}},
                {"carrier": "fedex", "indicators": {"CLI": 0.102}},
                {"carrier": "ups", "indicators": {"CLI": 0.103}}
            ],
            15,
            [(site, carrier) for site in [1, 2, 3, 4, 5] for carrier in ("dhl", "fedex", "ups")],
            {1: 1, 2: 1, 3: 2, 4: 2, 5: 3},
            {"ADT", "DDI", "AST", "CTDI", "DRI", "CLI"},
        ),
 # Test case 6: Only delivery data available (no dispatch, no dri, no cli)
        (
            [],
            [{"site": 1, "supplier": 1, "carrier": "dhl", "indicators": {"AST": 10.0, "CTDI": {"lower": 0.5, "upper": 1.5}}}],
            [],
            [],
            1,
            [(1, "dhl")],
            {1: 1},
            {"AST", "CTDI"}
        ),

        # Test case 7: Delivery and CLI available, but no dispatch or dri
        (
            [],
            [{"site": 1, "supplier": 1, "carrier": "fedex", "indicators": {"AST": 20.0, "CTDI": {"lower": 1.0, "upper": 2.0}}}],
            [],
            [{"carrier": "fedex", "indicators": {"CLI": 0.05}}],
            1,
            [(1, "fedex")],
            {1: 1},
            {"AST", "CTDI", "CLI"}
        ),

        # Test case 8: Dispatch and DRI available, but no delivery or CLI
        (
            [{"site": 2, "supplier": 2, "indicators": {"ADT": 35.0, "DDI": {"lower": 1.5, "upper": 2.5}}}],
            [],
            [{"site": 2, "supplier": 2, "indicators": {"DRI": 0.12}}],
            [],
            0,
            [],
            {2: 2},
            {"ADT", "DDI", "DRI"}
        ),

        # Test case 9: Dispatch and delivery with partial indicators (missing CTDI in delivery)
        (
            [{"site": 3, "supplier": 3, "indicators": {"ADT": 40.0, "DDI": {"lower": 1.1, "upper": 3.2}}}],
            [{"site": 3, "supplier": 3, "carrier": "ups", "indicators": {"AST": 38.0}}],
            [{"site": 3, "supplier": 3, "indicators": {"DRI": 0.09}}],
            [{"carrier": "ups", "indicators": {"CLI": 0.08}}],
            1,
            [(3, "ups")],
            {3: 3},
            {"ADT", "DDI", "AST", "DRI", "CLI"}
        ),

        # Test case 10: Delivery without indicators (should be ignored)
        (
            [{"site": 4, "supplier": 4, "indicators": {"ADT": 50.0, "DDI": {"lower": 2.0, "upper": 3.0}}}],
            [],
            [{"site": 4, "supplier": 4, "indicators": {"DRI": 0.05}}],
            [{"carrier": "dhl", "indicators": {"CLI": 0.07}}],
            0,
            [],
            {},
            {}
        ),

        # Test case 11: CLI only (no dispatch, no delivery, no dri)
        (
            [],
            [],
            [],
            [{"carrier": "fedex", "indicators": {"CLI": 0.03}}],
            0,
            [],
            {},
            {}
        ),

        # Test case 12: Entries with empty indicators dictionary
        (
            [
                {"site": 1, "supplier": 1, "indicators": {}}
            ],
            [
                {"site": 1, "supplier": 1, "carrier": "fedex", "indicators": {}}
            ],
            [
                {"site": 1, "supplier": 1, "indicators": {}}
            ],
            [
                {"carrier": "fedex", "indicators": {}}
            ],
            0,  # No usable entries
            [],
            {},
            set()  # No indicator keys
        ),
        # Test case 13: no dispatch and delivery
        (
            [],
            [],
            [{"site": 1, "supplier": 1, "indicators": {'DRI': 0.0}}],
            [
                {"carrier": "fedex", "indicators": {'CLI': 0.0}},
                {"carrier": "dhl", "indicators": {'CLI': 0.0}},
                {"carrier": "ups", "indicators": {'CLI': 0.0}}
            ],
            0,  # No usable entries
            [],
            {},
            set()  # No indicator keys
        ),
'''       