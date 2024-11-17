from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response

from recipes.models import Ingredient, RecipeIngredient

def set_tags_ingredients(ingredient_list, recipe):
    """."""
    RecipeIngredient.objects.bulk_create(
        [RecipeIngredient(
            recipe=recipe,
            #ingredient=Ingredient.objects.get(pk=ingredient['id']),
            ingredient = get_object_or_404(Ingredient, id=ingredient.get('id')),
            #amount=ingredient['amount']
            amount = ingredient.get('amount')
        ) for ingredient in ingredient_list]
    )
    # ingredient_list = []
    # for ingredient in ingredients:
    #     current_ingredient = get_object_or_404(Ingredient,
    #                                            id=ingredient.get('id'))
    #     amount = ingredient.get('amount')
    #     ingredient_list.append(
    #         RecipeIngredient(
    #             recipe=recipe,
    #             ingredient=current_ingredient,
    #             amount=amount
    #         )
    #     )
    # RecipeIngredient.objects.bulk_create(ingredient_list)

def add_recipe_to_cart_or_favorite(request, recipe, serializer):
    serializer = serializer(
        data={'user': request.user.id, 'recipe': recipe.id},
        context={'request': request}
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data, status=status.HTTP_201_CREATED)