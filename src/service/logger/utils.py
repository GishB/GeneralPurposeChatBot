path_fields = {
    "common": {
        "request": [],
        "response": [],
        "common": [],
    },
    "/api/v1/predict": {
        "request": [],
        "response": [],
        "common": [],
    },
    "gc.chat": {
        "request": [],
        "response": [],
        "common": [],
    },
    "gc.embeddings": {
        "request": [],
        "response": [],
        "common": [],
    },
}


def mask_sensitive_data(data, path="common", message_type="common"):
    path = path_fields.get(path, path_fields["common"])
    mask_fields = path.get(message_type, [])
    return _masker(data, mask_fields)


def _masker(data, mask_fields):
    """Маскирует поля с чувствительными данными в словаре"""
    if isinstance(data, dict):
        return {
            k: ("***" if not mask_fields or k.lower() in mask_fields else _masker(v, mask_fields))
            for k, v in data.items()
        }
    if isinstance(data, list):
        return [_masker(item, mask_fields) for item in data]
    return data
