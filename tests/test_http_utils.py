import json
import requests
from streamlit_app.utils.http_utils import parse_error_message


def _resp(obj, status=400, content_type="application/json"):
    r = requests.Response()
    r.status_code = status
    r._content = obj if isinstance(obj, (bytes, bytearray)) else json.dumps(obj).encode()
    r.headers["Content-Type"] = content_type
    return r


def test_parse_dict_detail_str():
    r = _resp({"detail": "simple"})
    assert parse_error_message(r) == "simple"


def test_parse_dict_detail_object():
    r = _resp({"detail": {"code": "X", "message": "hola"}})
    assert parse_error_message(r) == "hola"


def test_parse_list_items():
    r = _resp([{"msg": "uno"}, {"msg": "dos"}])
    assert parse_error_message(r) == "uno; dos"


def test_parse_non_json():
    r = _resp(b"Plain text", content_type="text/plain")
    assert parse_error_message(r) == "Plain text"
