from utils.parsing import parse_id_list, parse_str_list, get_query_params

def test_parse_id_list_valid_input():
    assert parse_id_list("1, 2,3 , 4") == {1, 2, 3, 4}

def test_parse_id_list_with_invalid_and_empty_tokens(caplog):
    result = parse_id_list("10, , 20, abc, 30")
    assert result == {10, 20, 30}
    assert "Invalid ID encountered: abc" in caplog.text

def test_parse_id_list_empty_string():
    assert parse_id_list("") == set()

def test_parse_id_list_spaces_only():
    assert parse_id_list(" , , ") == set()



def test_parse_str_list_lowercase_default():
    assert parse_str_list("Alpha, beta ,Gamma, delta") == {"alpha", "beta", "gamma", "delta"}

def test_parse_str_list_uppercase():
    assert parse_str_list("Alpha, beta ,Gamma, delta", case="upper") == {"ALPHA", "BETA", "GAMMA", "DELTA"}

def test_parse_str_list_no_case_transform():
    assert parse_str_list("Alpha, beta ,Gamma, delta", case=None) == {"Alpha", "beta", "Gamma", "delta"}

def test_parse_str_list_with_empty_and_spaces():
    assert parse_str_list(" , , Test , , value ") == {"test", "value"}

def test_parse_str_list_empty_string():
    assert parse_str_list("") == set()

def test_parse_str_list_case_unknown_defaults_to_no_transform():
    # Optional test — current behavior falls back to no case transform
    assert parse_str_list("A, B", case="invalid") == {"A", "B"}


def test_get_query_params_with_allowed_keys():
    event = {
        "status": "shipped",
        "state": "delivered",
        "irrelevant": "ignore",
        "empty": ""
    }
    allowed_keys = set(["status", "state"])
    
    result = get_query_params(event, allowed_keys)

    expected = {
        "status": "shipped",
        "state": "delivered"
    }
    assert result == expected

def test_get_query_params_without_allowed_keys():
    event = {
        "foo": "bar",
        "baz": "qux"
    }
    result = get_query_params(event)

    assert result == {
        "foo": "bar",
        "baz": "qux"
    }

def test_get_query_params_with_none_values_and_filter():
    event = {
        "status": "",
        "state": None,
        "valid": "yes"
    }
    allowed_keys = {"status", "state", "valid"}
    
    result = get_query_params(event, allowed_keys)

    assert result == {"valid": "yes"}

def test_get_query_params_with_no_query_params():
    event = {"status": None,
    }
    result = get_query_params(event, {"status"})
    assert result == {}

def test_get_query_params_missing_query_params_key():
    event = {}
    result = get_query_params(event)
    assert result == {}