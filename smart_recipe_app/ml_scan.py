import os
from django.conf import settings
from ultralytics import YOLO

_yolo_model = None

def _get_weights_path():
    # Put the YOLOE weight file here (download once and store in your weights folder)
    return os.path.join(settings.BASE_DIR, "smart_recipe_app", "weights", "yoloe-26s-seg.pt")

def detect_ingredients_local_yolo(image_path: str) -> list[dict]:
    global _yolo_model
    if _yolo_model is None:
        _yolo_model = YOLO(_get_weights_path())

    # Prompt the foods you want to detect
    wanted = [
        "tomato", "cucumber", "onion", "garlic", "potato", "carrot",
        "egg", "milk", "cheese", "yogurt", "butter",
        "chicken", "tuna", "sausage", "bacon",
        "bread", "flour", "pasta", "rice",
        "olive oil", "beans", "cabbage",
        "walnut", "almond", "peanut", "sesame", "soy", "eggs", "pepper", "orange", "banana", "olives"
    ]

    # Ultralytics supports prompting classes like this in CLI and via API patterns;
    # depending on your ultralytics version, you can use:
    # - model.set_classes(wanted) before predict
    # - or pass classes in predict / yolo predict ... classes="a,b,c"
    try:
        _yolo_model.set_classes(wanted)
    except Exception:
        pass

    results = _yolo_model(image_path, verbose=False)
    r = results[0]

    items = []
    names = r.names

    for box in r.boxes:
        cls_id = int(box.cls[0])
        conf = float(box.conf[0])
        label = str(names.get(cls_id, "unknown")).lower().strip()
        items.append({"label": label, "confidence": conf, "quantity_guess": None})

    # merge same labels -> quantity
    merged = {}
    for it in items:
        key = it["label"]
        if key not in merged:
            merged[key] = {"label": key, "confidence": it["confidence"], "quantity_guess": 1}
        else:
            merged[key]["quantity_guess"] += 1
            merged[key]["confidence"] = max(merged[key]["confidence"], it["confidence"])

    return list(merged.values())
