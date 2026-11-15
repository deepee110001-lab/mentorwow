import json


def dumps(value) -> str:
    return json.dumps(value, default=str)


def loads(value, default=None):
    if value in (None, ""):
        return default if default is not None else []
    if isinstance(value, (list, dict)):
        return value
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default if default is not None else []
