from service.db_utils import build_connection_url 

def test_build_connection_url():
    config = {
        "username": "myuser",
        "password": "mypassword",
        "host": "mydb.example.com",
        "port": 5432,
        "dbname": "mydatabase"
    }

    expected = "postgresql+psycopg2://myuser:mypassword@mydb.example.com:5432/mydatabase"
    result = build_connection_url(config)

    assert result == expected