from django.db import transaction
from django.contrib.auth import get_user_model
from djoser.serializers import UserCreateSerializer, UserSerializer
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from users.models import Subscription
from recipes.models import (Favorites, Ingredient, Recipe,
                            RecipeIngredient, ShoppingCart, Tag)
from .utils import get_is_subscribed_value, get_recipe_params


User = get_user_model()


class UserInfoSerializer(UserSerializer):
    """Сериализатор для работы с объектами модели пользователя."""

    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'first_name', 'last_name',
                  'is_subscribed', 'avatar')

    def get_is_subscribed(self, obj):
        return get_is_subscribed_value(self, obj)


class UserRegistrationSerializer(UserCreateSerializer):
    """Сериализатор для создания объектов модели пользователя."""

    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'first_name', 'last_name',
                  'password')


class AvatarUpdateSerializer(serializers.ModelSerializer):
    """Сериализатор работы с полем аватара модели пользователя."""

    avatar = Base64ImageField()

    class Meta:
        model = User
        fields = ('avatar', )

    def update(self, instance, validated_data):
        avatar = validated_data.get('avatar')
        if avatar:
            instance.avatar = avatar
        instance.save()
        return instance


class RecipeShortSerializer(serializers.ModelSerializer):
    """Сериализатор для краткого отображения рецептов."""
    image = Base64ImageField()
    name = serializers.ReadOnlyField()
    cooking_time = serializers.ReadOnlyField()

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class UserSubscriptionsSerializer(UserInfoSerializer):
    """"Сериализатор для отображения подлписок пользователя."""

    is_subscribed = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('email', 'id', 'username', 'first_name', 'last_name',
                  'is_subscribed', 'recipes', 'recipes_count', 'avatar')

    def get_is_subscribed(self, obj):
        return get_is_subscribed_value(self, obj)

    def get_recipes(self, obj):
        request = self.context.get('request')
        recipes_limit = request.query_params.get('recipes_limit', None)
        queryset = obj.recipes.all()
        if recipes_limit:
            queryset = queryset[:(int(recipes_limit))]
        return RecipeShortSerializer(queryset, many=True).data

    def get_recipes_count(self, obj):
        return obj.recipes.all().count()


class UserMakeSubscribeSerializer(serializers.ModelSerializer):
    """Сериализатор для работы с подпиской/отпиской."""

    class Meta:
        model = Subscription
        fields = ('author', 'user')
        validators = (
            UniqueTogetherValidator(
                queryset=Subscription.objects.all(),
                fields=('author', 'user'),
                message='Подписка на этого пользователя уже оформлена'
            ),
        )

    def validate(self, data):
        author = data.get('author')
        user = data.get('user')
        if user == author:
            raise serializers.ValidationError(
                {'errors': 'Невозможно оформить подписку на самого себя'}
            )
        return data

    def create(self, validated_data):
        author = validated_data.get('author')
        user = validated_data.get('user')
        return Subscription.objects.create(user=user, author=author)


class TagSerialiser(serializers.ModelSerializer):
    """Сериализатор для модели тегов."""

    class Meta:
        model = Tag
        fields = '__all__'


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для модели ингредиентов."""

    class Meta:
        model = Ingredient
        fields = '__all__'


class IngredientAddSerializer(serializers.ModelSerializer):
    """Сериализатор для создания объектов модели ингредиентов."""

    id = serializers.IntegerField(write_only=True)
    amount = serializers.IntegerField(write_only=True)

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'amount')


class IngredientGetSerializer(serializers.ModelSerializer):
    """Сериализатор для получения объектов модели ингредиентов."""

    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = RecipeIngredient
        fields = (
            'id',
            'name',
            'measurement_unit',
            'amount'
        )


class RecipeGetSerializer(serializers.ModelSerializer):
    """Сериализатор для получения объектов модели рецептов."""

    tags = TagSerialiser(many=True, read_only=True)
    author = UserInfoSerializer(read_only=True)
    ingredients = IngredientGetSerializer(many=True, read_only=True,
                                          source='recipe_ingredients')
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = ('id', 'tags', 'author', 'ingredients', 'name',
                  'image', 'text', 'cooking_time', 'is_favorited',
                  'is_in_shopping_cart')

    def get_is_favorited(self, obj):
        return get_recipe_params(self, obj, Favorites)

    def get_is_in_shopping_cart(self, obj):
        return get_recipe_params(self, obj, ShoppingCart)


class RecipeAddSerializer(serializers.ModelSerializer):
    """Сериализатор для добавления объектов модели рецептов."""

    ingredients = IngredientAddSerializer(required=True, many=True)
    tags = serializers.PrimaryKeyRelatedField(required=True,
                                              queryset=Tag.objects.all(),
                                              many=True,)
    image = Base64ImageField(required=True, use_url=True)

    class Meta:
        model = Recipe
        fields = ('id', 'tags', 'ingredients', 'name', 'image',
                  'text', 'cooking_time')

    def validate_image(self, img):
        if not img:
            raise serializers.ValidationError(
                'Загрузите изображение рецепта.'
            )
        return img

    def validate(self, attrs):
        ingredients_data = attrs.get('ingredients')
        tags_data = attrs.get('tags')
        ingredient_ids = [ingredient['id'] for ingredient in ingredients_data]
        tags_ids = [tag for tag in tags_data]
        for item in [ingredient_ids, tags_ids]:
            if len(item) != len(set(item)):
                raise serializers.ValidationError(
                    'Игредиенты и теги не должны повторяться.'
                )
        for ingredient_data in ingredients_data:
            ingredient_id = ingredient_data.get('id')
            amount = ingredient_data.get('amount')
            if not Ingredient.objects.filter(id=ingredient_id).exists():
                raise serializers.ValidationError(
                    {'ingredients': f'Ингредиент с id {ingredient_id} не '
                                    f'обнаружен.'})
            if amount <= 0:
                raise serializers.ValidationError(
                    {'ingredients': f'Для ингредиента с id {ingredient_id} '
                                    f'количество должно быть больше 0.'})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        tags_data = validated_data.pop('tags')
        ingredients_data = validated_data.pop('ingredients')
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags_data)
        self.add_ingredients(recipe, ingredients_data)
        return recipe

    @transaction.atomic
    def update(self, instance, validated_data):
        tags = validated_data.pop('tags', None)
        ingredients = validated_data.pop('ingredients', None)
        instance = super().update(instance, validated_data)
        instance.tags.set(tags)
        instance.ingredients.clear()
        self.add_ingredients(instance, ingredients)
        return instance

    def add_ingredients(self, recipe, ingredients_data):
        RecipeIngredient.objects.bulk_create(
            [
                RecipeIngredient(
                    recipe=recipe,
                    ingredient_id=ingredient.get('id'),
                    amount=ingredient.get('amount')
                )
                for ingredient in ingredients_data
            ]
        )

    def to_representation(self, instance):
        return RecipeGetSerializer(instance, context=self.context).data


class ShoppingCartSerializer(serializers.ModelSerializer):
    """Сериализатор для объектов модели списка покупок."""

    class Meta:
        model = ShoppingCart
        fields = '__all__'
        validators = (
            UniqueTogetherValidator(
                queryset=ShoppingCart.objects.all(),
                fields=('user', 'recipe'),
                message='Рецепт уже добавлен в список покупок'
            ),
        )

    def to_representation(self, instance):
        request = self.context.get('request')
        return RecipeShortSerializer(
            instance.recipe,
            context={'request': request}
        ).data


class FavoritesSerializer(serializers.ModelSerializer):
    """Сериализатор для объектов модели избранного."""

    class Meta:
        model = Favorites
        fields = '__all__'
        validators = (
            UniqueTogetherValidator(
                queryset=Favorites.objects.all(),
                fields=('user', 'recipe'),
                message='Рецепт уже добавлен в избранное'
            ),
        )

    def to_representation(self, instance):
        request = self.context.get('request')
        return RecipeShortSerializer(
            instance.recipe,
            context={'request': request}
        ).data
