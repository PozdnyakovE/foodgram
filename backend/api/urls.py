from django.urls import include, path
from rest_framework.routers import DefaultRouter

from api.views import (AvatarUpdateDeleteView, IngredientViewSet,
                       RecipeViewSet, SubscriptionsUserViewSet, TagViewSet)


router = DefaultRouter()
router.register('tags', TagViewSet, basename='tags')
router.register('ingredients', IngredientViewSet, basename='ingredients')
router.register('users', SubscriptionsUserViewSet, basename='subscriptions')
router.register('recipes', RecipeViewSet, basename='recipes')

urlpatterns = [
    path('', include(router.urls)),
    path('', include('djoser.urls')),
    path('auth/', include('djoser.urls.authtoken')),
    path('users/me/avatar/', AvatarUpdateDeleteView.as_view(), name='avatar'),
]
