from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.shortcuts import HttpResponse, get_object_or_404
from djoser.views import UserViewSet
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.views import APIView

# from api.pagination import SubscribePagination
from api.filters import IngredientFilter, RecipeFilter
from api.permissions import IsAuthorOrReadOnly
#from api.utils import add_recipe_to_cart_or_favorite
from recipes.models import Ingredient, Recipe, RecipeIngredient, ShoppingCart, Tag, Favorites
from users.models import Subscription
from .serializers import (AvatarUpdateSerializer, IngredientSerializer, TagSerialiser, 
                          UserMakeSubscribeSerializer, UserSubscriptionsSerializer,
                          RecipeAddSerializer, RecipeGetSerializer, ShoppingCartSerializer, FavoritesSerializer)

User = get_user_model()

BASE_URL = 'http://127.0.0.1:8000/'

class SubscriptionsUserViewSet(UserViewSet):

    @action(
        detail=True,
        methods=('POST', 'DELETE'),
        url_path='subscribe',
        url_name='subscribe',
        permission_classes=(IsAuthenticated,),
    )
    def subscribe(self, request, id):
        # user = request.user
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
                {'errors': 'Вы не подписаны на этого пользователя'},
                status=status.HTTP_400_BAD_REQUEST
            )
        subscription.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=('GET',),
        url_path='subscriptions',
        url_name='subscriptions',
        permission_classes=(IsAuthenticated,),
    )
    def subscriptions(self, request):
        # user = request.user
        queryset = User.objects.filter(subscribers__user=request.user)
        pages = self.paginate_queryset(queryset)
        serializer = UserSubscriptionsSerializer(
            pages,
            many=True,
            context={'request': request}
        )
        return self.get_paginated_response(serializer.data)
    

class AvatarUpdateDelete(generics.UpdateAPIView, generics.DestroyAPIView):
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
    """."""
    queryset = Tag.objects.all()
    serializer_class = TagSerialiser
    #permission_classes = (AllowAny, )
    pagination_class = None


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    """."""
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    #permission_classes = (AllowAny, )
    filter_backends = (DjangoFilterBackend, )
    filterset_class = IngredientFilter
    pagination_class = None


class RecipeViewSet(viewsets.ModelViewSet):
    """Работа с рецептами. Создание/изменение/удаление рецепта.
    Получение информации о рецептах.
    Добавление рецептов в избранное и список покупок.
    Отправка файла со списком рецептов.
    """
    # permission_classes = [IsAuthenticatedOrReadOnly]
    queryset = Recipe.objects.all()
    # pagination_class = RecipePagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = RecipeFilter

    def partial_update(self, request, *args, **kwargs):
        recipe_id = self.kwargs['pk']
        recipe = get_object_or_404(Recipe, id=recipe_id)
        if recipe.author != request.user:
            return Response(
                {'detail': 'У вас нет прав на обновление этого рецепта.'},
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
                {'detail': 'У вас нет прав на удаление этого рецепта.'},
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
        # frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:3000')
        # url_to_recipes = os.getenv('URL_TO_RECIPES', 'recipes')
        short_link = f'{BASE_URL}recipes/{recipe_id}/'
        return Response({'short-link': short_link})
    

    @action(
        detail=True,
        methods=('POST', 'DELETE'),
        url_path='shopping_cart',
        # url_name='shopping_cart',
        permission_classes=(IsAuthenticated,)
    )
    def shopping_cart(self, request, pk):
        recipe = get_object_or_404(Recipe, id=pk)
        if request.method == 'POST':
            return self.add_recipe_to_cart_or_favorite(request, recipe, ShoppingCartSerializer)
            # serializer = ShoppingCartSerializer(
            #     data={'user': request.user.id, 'recipe': recipe.id, },
            #     context={'request': request}
            # )
            # serializer.is_valid(raise_exception=True)
            # serializer.save()
            # return Response(serializer.data, status=status.HTTP_201_CREATED)

        if request.method == 'DELETE':
            error_message = 'У вас нет этого рецепта в списке покупок'
            return self.delete_recipe_from_cart_or_favorite(request, ShoppingCart, recipe, error_message)
        
    @action(
        detail=False,
        methods=('get',),
        url_path='download_shopping_cart',
        # permission_classes=[IsAuthenticated, ]
    )
    def download_shopping_cart(self, request):
        """."""
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
        methods=['post', 'delete'],
        # permission_classes=[IsAuthenticated, ]
    )
    def favorite(self, request, pk):
        """Работа с избранными рецептами.
        Удаление/добавление в избранное.
        """
        recipe = get_object_or_404(Recipe, id=pk)
        if request.method == 'POST':
            return self.add_recipe_to_cart_or_favorite(request, recipe, FavoritesSerializer)

        if request.method == 'DELETE':
            error_message = 'У вас нет этого рецепта в избранном'
            return self.delete_recipe_from_cart_or_favorite(request, Favorites,
                                         recipe, error_message)