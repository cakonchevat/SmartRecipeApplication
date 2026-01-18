# Test the detection function
from smart_recipe_app.ml_scan import detect_ingredients_with_claude

results = detect_ingredients_with_claude('/path/to/test/image.jpg')
print(results)