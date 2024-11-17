from django.contrib.auth import get_user_model
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Sum
from django.shortcuts import HttpResponse, get_object_or_404
from djoser.views import UserViewSet
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from api.filters import IngredientFilter, RecipeFilter
from recipes.models import Ingredient, Recipe, RecipeIngredient, ShoppingCart, Tag, Favorites
from users.models import Subscription
from .serializers import (AvatarUpdateSerializer, IngredientSerializer, FavoritesSerializer,
                          RecipeAddSerializer, RecipeGetSerializer, ShoppingCartSerializer, TagSerialiser, 
                          UserMakeSubscribeSerializer, UserSubscriptionsSerializer)


User = get_user_model()

BASE_URL = 'http://127.0.0.1:8000/'


class SubscriptionsUserViewSet(UserViewSet):
    """Вьюсет для работы с подписками."""

    @action(
        detail=True,
        methods=('POST', 'DELETE'),
        url_path='subscribe',
        permission_classes=(IsAuthenticated,),
    )
    def subscribe(self, request, id):
        author = get_object_or_404(User, id=id)
        serializer = UserMakeSubscribeSerializer(
            data={'user': request.user.id, 'author': author.id}
        )
        if request.method == 'POST':
            serializer.is_valid(raise_exception=True)
            serializer.save()
            serializer = UserSubscriptionsSerializer(
                author, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        subscription = Subscription.objects.filter(user=request.user, author=author)
        if not subscription.exists():
            return Response(
                {'errors': 'Подписка на этого пользователя не оформлена'},
                status=status.HTTP_400_BAD_REQUEST
            )
        subscription.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=('GET',),
        url_path='subscriptions',
        permission_classes=(IsAuthenticated,),
    )
    def subscriptions(self, request):
        queryset = User.objects.filter(subscribers__user=request.user)
        pages = self.paginate_queryset(queryset)
        serializer = UserSubscriptionsSerializer(
            pages,
            many=True,
            context={'request': request}
        )
        return self.get_paginated_response(serializer.data)
    

class AvatarUpdateDeleteView(generics.UpdateAPIView, generics.DestroyAPIView):
    """Класс для обновления/удаления аватара."""

    queryset = User.objects.all()
    serializer_class = AvatarUpdateSerializer
    permission_classes = (IsAuthenticatedOrReadOnly, )

    def get_object(self):
        return self.request.user

    def destroy(self, request, *args, **kwargs):
        user = self.get_object()
        user.avatar.delete(save=True)
        return Response(status=status.HTTP_204_NO_CONTENT)
    
class TagViewSet(viewsets.ReadOnlyModelViewSet):
    """Вьюсет для работы с тегами."""

    queryset = Tag.objects.all()
    serializer_class = TagSerialiser
    pagination_class = None


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    """Вьюсет для работы с ингредиентами."""

    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filter_backends = (DjangoFilterBackend, )
    filterset_class = IngredientFilter
    pagination_class = None


class RecipeViewSet(viewsets.ModelViewSet):
    """Вьюсет для работы с рецептами.
    Обеспечивает удаление/создание/обновление, получение информации об объекте.
    Формирование текстового файла со списком, добавление в избранное
    и список покупок. 
    """

    queryset = Recipe.objects.all()
    filter_backends = (DjangoFilterBackend, )
    filterset_class = RecipeFilter

    def partial_update(self, request, *args, **kwargs):
        recipe_id = self.kwargs['pk']
        recipe = get_object_or_404(Recipe, id=recipe_id)
        if recipe.author != request.user:
            return Response(
                {'errors': 'Недостаточно прав для обновление данного рецепта.'},
                status=status.HTTP_403_FORBIDDEN)
        serializer = self.get_serializer(recipe, data=request.data,
                                         partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_200_OK)

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return RecipeGetSerializer
        return RecipeAddSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def destroy(self, request, *args, **kwargs):
        recipe_id = self.kwargs['pk']
        recipe = get_object_or_404(Recipe, id=recipe_id)

        if recipe.author != request.user:
            return Response(
                {'errors': 'Недостаточно прав для удаления данного рецепта.'},
                status=status.HTTP_403_FORBIDDEN)
        recipe.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @staticmethod
    def add_recipe_to_cart_or_favorite(request, recipe, serializer):
        serializer = serializer(
            data={'user': request.user.id, 'recipe': recipe.id},
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @staticmethod
    def delete_recipe_from_cart_or_favorite(request, model, recipe, error):
        if not model.objects.filter(user=request.user,
                                     recipe=recipe).exists():
            return Response({'errors': error},
                        status=status.HTTP_400_BAD_REQUEST)
        model.objects.filter(user=request.user, recipe=recipe).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=True, url_path='get-link')
    def get_link(self, request, pk=None):
        recipe_id = self.kwargs[self.lookup_field]
        short_link = f'{BASE_URL}recipes/{recipe_id}/'
        return Response({'short-link': short_link})
    
    @action(
        detail=True,
        methods=('POST', 'DELETE'),
        url_path='shopping_cart',
        permission_classes=(IsAuthenticated,)
    )
    def shopping_cart(self, request, pk):
        recipe = get_object_or_404(Recipe, id=pk)
        if request.method == 'POST':
            return self.add_recipe_to_cart_or_favorite(request, recipe, ShoppingCartSerializer)

        if request.method == 'DELETE':
            return self.delete_recipe_from_cart_or_favorite(
                request, ShoppingCart, recipe,
                'Данный рецепт не содержится в списке покупок'
            )
        
    @action(
        detail=False,
        methods=('GET',),
        url_path='download_shopping_cart',
    )
    def download_shopping_cart(self, request):
        ingredients = RecipeIngredient.objects.filter(
            recipe__carts__user=request.user
        ).values(
            'ingredient__name', 'ingredient__measurement_unit'
        ).annotate(ingredient_amount=Sum('amount'))
        shopping_list = ['Список покупок:\n']
        for ingredient in ingredients:
            name = ingredient['ingredient__name']
            measurement_unit = ingredient['ingredient__measurement_unit']
            amount = ingredient['ingredient_amount']
            shopping_list.append(f'\n{name}, {amount}, {measurement_unit}')
        response = HttpResponse(shopping_list, content_type='text/plain')
        response['Content-Disposition'] = \
            'attachment; filename="shopping_cart.txt"'
        return response
    
    @action(
        detail=True,
        methods=('POST', 'DELETE',),
    )
    def favorite(self, request, pk):
        recipe = get_object_or_404(Recipe, id=pk)
        if request.method == 'POST':
            return self.add_recipe_to_cart_or_favorite(request, recipe, FavoritesSerializer)

        if request.method == 'DELETE':
            return self.delete_recipe_from_cart_or_favorite(
                request, Favorites, recipe,
                'Данный рецепт не содержится в избранном'
            )