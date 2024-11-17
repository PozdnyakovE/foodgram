from django.db import transaction
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from djoser.serializers import UserCreateSerializer, UserSerializer
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers, status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.validators import UniqueTogetherValidator

from users.models import Subscription
from recipes.models import Favorites, Ingredient, Recipe, RecipeIngredient, ShoppingCart, Tag
from .utils import set_tags_ingredients


USERS_ME_PATH = '/api/users/me/'

User = get_user_model()

class UserInfoSerializer(UserSerializer):
    """."""
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id',
            'email',
            'username',
            'first_name', 
            'last_name',
            'is_subscribed',
            'avatar'
        )

    def get_is_subscribed(self, obj):
        # request_user = self.context.get('request').user
        # return (
        #     request_user.is_authenticated
        #     and Subscription.objects.filter(
        #     user=request_user,
        #     author=obj).exists()
        # )

        request = self.context.get('request')
        # return (request and request.user.is_authenticated
        #         and obj.subscribers.filter(user=request.user).exists())
        if request and request.user.is_authenticated:
            return obj.subscribers.filter(user=request.user).exists()
        return False

    def to_representation(self, instance):
        request = self.context.get('request')
        if request.path == USERS_ME_PATH and not request.user.is_authenticated:
            raise AuthenticationFailed
        return super().to_representation(instance)
    

class UserRegistrationSerializer(UserCreateSerializer):
    """."""
    class Meta:
        model = User
        fields = (
            'id',
            'email',
            'username',
            'first_name', 
            'last_name',
            'password'
        )
        # extra_kwargs = {
        #     'first_name': {'required': True, 'allow_blank': False},
        #     'last_name': {'required': True, 'allow_blank': False}
        # }
        # fields = ('email', 'id', 'username', 'first_name',
        #           'last_name', 'password')
        #fields = '__all__'


class AvatarUpdateSerializer(serializers.ModelSerializer):
    # avatar = Base64ImageField(required=True)
    avatar = Base64ImageField()

    class Meta:
        model = User
        fields = ('avatar', )

    def update(self, instance, validated_data):
        avatar = validated_data.get('avatar', None)
        if avatar:
            instance.avatar = avatar
        instance.save()
        return instance
    

class RecipeShortSerializer(serializers.ModelSerializer):
    """."""
    class Meta:
        model = Recipe
        fields = (
            'id',
            'name',
            'image',
            'cooking_time'
        )



class UserSubscriptionsSerializer(UserInfoSerializer):
    """"Сериализатор для предоставления информации
    о подписках пользователя.
    """
    # is_subscribed = serializers.SerializerMethodField(
    #     method_name='get_is_subscribed')
    # recipes = serializers.SerializerMethodField(method_name='get_recipes')
    # recipes_count = serializers.SerializerMethodField(
    #     method_name='get_recipes_count')
    is_subscribed = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('email', 'id', 'username', 'first_name',
                  'last_name', 'is_subscribed', 'recipes', 'recipes_count', 'avatar')

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if request is None or request.user.is_anonymous:
            return False
        return Subscription.objects.filter(user=request.user, author=obj).exists()

    def get_recipes(self, obj):
        request = self.context.get('request')
        recipes_limit = request.POST.get('recipes_limit')
        queryset = obj.recipes.all()
        if recipes_limit:
            queryset = queryset[:(recipes_limit)]
        return RecipeShortSerializer(queryset, many=True).data

    def get_recipes_count(self, obj):
        return obj.recipes.all().count()

class UserMakeSubscribeSerializer(serializers.ModelSerializer):
    """Сериализатор для подписки/отписки от пользователей."""

    author = UserInfoSerializer
    user = UserInfoSerializer

    class Meta:
        model = Subscription
        fields = ('author', 'user')
        validators = (
            UniqueTogetherValidator(
                queryset=Subscription.objects.all(),
                fields=('author', 'user'),
                message='Вы уже подписаны на этого пользователя'
            ),
        )

    def validate(self, data):
        author = data.get('author')
        user = data.get('user')
        if user == author:
            raise serializers.ValidationError(
                {'errors': 'Нельзя подписаться на самого себя'}
            )
        return data

    def create(self, validated_data):
        author = validated_data.get('author')
        user = validated_data.get('user')
        return Subscription.objects.create(user=user, author=author)


class TagSerialiser(serializers.ModelSerializer):
    """."""
    class Meta:
        model = Tag
        fields = '__all__'


class IngredientSerializer(serializers.ModelSerializer):
    """."""
    class Meta:
        model = Ingredient
        fields = '__all__'


class IngredientAddSerializer(serializers.ModelSerializer):
    """."""
    id = serializers.IntegerField(write_only=True)
    amount = serializers.IntegerField(write_only=True)

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'amount')


class IngredientGetSerializer(serializers.ModelSerializer):
    """."""
    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(source='ingredient.measurement_unit')

    class Meta:
        model = RecipeIngredient
        fields = (
            'id',
            'name',
            'measurement_unit',
            'amount'
        )


class RecipeGetSerializer(serializers.ModelSerializer):
    """."""
    tags = TagSerialiser(many=True, read_only=True)
    author = UserInfoSerializer(read_only=True)
    ingredients = IngredientGetSerializer(many=True, read_only=True,
                                          source='recipesingredients')
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = (
            'id',
            'tags',
            'author',
            'ingredients',
            'name',
            'image',
            'text',
            'cooking_time',
            'is_favorited',
            'is_in_shopping_cart',
        )

    def get_is_favorited(self, obj):
        request = self.context.get('request')
        # return (request and request.user.is_authenticated
        #         and Favorites.objects.filter(
        #             user=request.user, recipe=obj
        #         ).exists())
        if request is None or request.user.is_anonymous:
            return False
        return Favorites.objects.filter(user=request.user, recipe=obj).exists()

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get('request')
        # return (request and request.user.is_authenticated
        #         and ShoppingCart.objects.filter(
        #             user=request.user, recipe=obj
        #         ).exists())
        if request is None or request.user.is_anonymous:
            return False
        return ShoppingCart.objects.filter(user=request.user, recipe=obj).exists()
    

class RecipeAddSerializer(serializers.ModelSerializer):
    """."""
    ingredients = IngredientAddSerializer(many=True, required=True)
    tags = serializers.PrimaryKeyRelatedField(queryset=Tag.objects.all(),
                                              many=True,
                                              required=True,)
    image = Base64ImageField(required=True)

    class Meta:
        model = Recipe
        fields = (
            'id',
            'tags',
            'ingredients',
            'name',
            'image',
            'text',
            'cooking_time',
        )

    def validate(self, attrs):
        ingredients_data = attrs.get('ingredients')
        tags_data = attrs.get('tags')
        cooking_time_data = attrs.get('cooking_time')
        image_data = attrs.get('image')
        if not image_data:
            raise serializers.ValidationError(
                {'image': 'Это поле не может быть пустым.'})
        if not cooking_time_data:
            raise serializers.ValidationError(
                {'cooking_time_data': 'Это поле не может быть пустым.'})
        if not ingredients_data:
            raise serializers.ValidationError(
                {'ingredients': 'Это поле не может быть пустым.'})
        if not tags_data:
            raise serializers.ValidationError(
                {'tags': 'Это поле не может быть пустым.'})
        ingredient_ids = [ingredient['id'] for ingredient in ingredients_data]
        if len(ingredient_ids) != len(set(ingredient_ids)):
            raise serializers.ValidationError(
                {'ingredients': 'Ингредиенты не должны повторяться.'})
        tags_ids = [tag for tag in tags_data]
        if len(tags_ids) != len(set(tags_ids)):
            raise serializers.ValidationError(
                {'tags': 'Теги не должны повторяться.'})
        for ingredient_data in ingredients_data:
            ingredient_id = ingredient_data.get('id')
            amount = ingredient_data.get('amount')
            if not Ingredient.objects.filter(id=ingredient_id).exists():
                raise serializers.ValidationError(
                    {'ingredients': f'Ингредиент с ID {ingredient_id} не '
                                    f'существует.'})
            if amount <= 0:
                raise serializers.ValidationError(
                    {'ingredients': f'Количество для '
                                    f'ингредиента с ID {ingredient_id} '
                                    f'должно быть больше 0!!!'})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        tags_data = validated_data.pop('tags')
        ingredients_data = validated_data.pop('ingredients')
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags_data)
        self.create_ingredients(recipe, ingredients_data)
        return recipe

    @transaction.atomic
    def update(self, instance, validated_data):
        ingredients_data = validated_data.get('ingredients')
        tags_data = validated_data.get('tags')
        if tags_data:
            instance.tags.set(tags_data)

        if ingredients_data:
            # instance.recipe_with_ingredient.all().delete()
            instance.recipesingredients.all().delete()
            self.create_ingredients(instance, ingredients_data)

        if 'image' in validated_data:
            instance.image = validated_data.get('image', instance.image)
        instance.save()
        return instance

    def create_ingredients(self, recipe, ingredients_data):
        ingredient_objects = [
            RecipeIngredient(
                recipe=recipe,
                ingredient=get_object_or_404(Ingredient,
                                             id=ingredient_data['id']),
                amount=ingredient_data['amount']
            )
            for ingredient_data in ingredients_data
        ]
        RecipeIngredient.objects.bulk_create(ingredient_objects)

    def to_representation(self, instance):
        return RecipeGetSerializer(instance, context=self.context).data


class ShoppingCartSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShoppingCart
        fields = '__all__'
        validators = [
            UniqueTogetherValidator(
                queryset=ShoppingCart.objects.all(),
                fields=('user', 'recipe'),
                message='Рецепт уже добавлен в список покупок'
            )
        ]

    def to_representation(self, instance):
        request = self.context.get('request')
        return RecipeShortSerializer(
            instance.recipe,
            context={'request': request}
        ).data
    # user = UserInfoSerializer
    # recipe = RecipeGetSerializer

    # class Meta:
    #     model = ShoppingCart
    #     fields = ('user', 'recipe')
    #     validators = (
    #         UniqueTogetherValidator(
    #             queryset=ShoppingCart.objects.all(),
    #             fields=('user', 'recipe'),
    #             message='Рецепт уже добавлен в список покупок'
    #         ),
    #     )

    # def create(self, validated_data):
    #     user = validated_data.get('user')
    #     recipe = validated_data.get('recipe')
    #     return ShoppingCart.objects.create(user=user, recipe=recipe)


class FavoritesSerializer(serializers.ModelSerializer):
    """."""
    class Meta:
        model = Favorites
        fields = '__all__'
        validators = [
            UniqueTogetherValidator(
                queryset=Favorites.objects.all(),
                fields=('user', 'recipe'),
                message='Рецепт уже добавлен в избранное'
            )
        ]

    def to_representation(self, instance):
        request = self.context.get('request')
        return RecipeShortSerializer(
            instance.recipe,
            context={'request': request}
        ).data