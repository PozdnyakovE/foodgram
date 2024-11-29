from django.core.management.base import BaseCommand
import pandas as pd

from recipes.models import Ingredient


class Command(BaseCommand):
    '''Добавление ингредентов в базу данных.'''

    help = 'Adding ingredients'

    def handle(self, *args, **options):
        for index, row in pd.read_csv('data/ingredients.csv').iterrows():
            ingredient = Ingredient(
                name=row['name'],
                measurement_unit=row['measurement_unit']
            )
            ingredient.save()
        self.stdout.write("[!] The ingredients has been loaded successfully.")
