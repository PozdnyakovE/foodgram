# python manage.py runscript load_from_csv
import pandas as pd

from recipes.models import Ingredient

for index, row in pd.read_csv('data/ingredients.csv').iterrows():
    ingredient = Ingredient(
        name=row['name'],
        measurement_unit=row['measurement_unit']
    )
    ingredient.save()