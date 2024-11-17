from django.core.validators import MinValueValidator
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

NAME_MAX_LENGTH = 250

class Ingredient(models.Model):
    name = models.CharField(
        'Название ингредиента',
        max_length=NAME_MAX_LENGTH,
    )
    measurement_unit = models.CharField(
        'Единица измерения',
        max_length=NAME_MAX_LENGTH,
    )

    class Meta:
        ordering = ('name',)
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'

    def __str__(self):
        return self.name

class Tag(models.Model):
    name = models.CharField(
        'Название тэга',
        max_length=NAME_MAX_LENGTH,
        db_index=True,
        unique=True
    )
    # color = models.CharField(
    #     'Цвет',
    #     max_length=7,
    #     unique=True
    # )
    slug = models.SlugField(
        'Слаг тэга',
        max_length=NAME_MAX_LENGTH,
        unique=True
    )

    class Meta:
        ordering = ('name',)
        verbose_name = "Тэг"
        verbose_name_plural = "Тэги"

    def __str__(self):
        return self.name
    

class Recipe(models.Model):
    name = models.CharField(
        'Название блюда',
        max_length=NAME_MAX_LENGTH,
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='recipes',
        verbose_name='Автор рецепта',
    )
    text = models.TextField(
        'Описание рецепта',
        max_length=4000
    )
    cooking_time = models.PositiveSmallIntegerField(
        'Время приготовления',
        default=1,
        validators=(
            MinValueValidator(
                1, 'Не менее 1 минуты на приготовление'
            ),
        )
    )
    image = models.ImageField(
        'Изображение',
        upload_to='recipes_images/',
        blank=True,
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        verbose_name='Ингредиенты',
        through='RecipeIngredient',
        related_name="recipes"
    )
    tags = models.ManyToManyField(
        Tag,
        verbose_name='Теги',
        related_name="recipes"
    )
    pub_date = models.DateTimeField(
        verbose_name='Дата публикации',
        auto_now_add=True,
        editable=False,
    )

    class Meta:
        ordering = ('-pub_date', )
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'

    def __str__(self):
        return self.name


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='recipesingredients',
        verbose_name='Рецепт'

    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        related_name='recipesingredients',
        verbose_name='Ингредиент'
    )
    amount = models.PositiveSmallIntegerField(
        'Количество ингредиентов',
        default=0,
        validators=(
            MinValueValidator(
                1, 'Не менее одного ингредиента'
            ),
        )
    )

    class Meta:
        ordering = ('recipe', )
        verbose_name = 'Ингредиент для рецепта'
        verbose_name_plural = 'Ингредиенты для рецепта'
        constraints = (
            models.UniqueConstraint(
                fields=('recipe', 'ingredient', ),
                name='unique_ingredient_for_recipe',
            ),
        )


class Favorites(models.Model):
    user = models.ForeignKey(
        User,
        related_name='favorites',
        verbose_name='Пользователь',
        on_delete=models.CASCADE,
    )
    recipe = models.ForeignKey(
        Recipe,
        related_name='favorites',
        verbose_name='Рецепт',
        on_delete=models.CASCADE,
    )

    class Meta:
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранное'
        constraints = (
            models.UniqueConstraint(
                fields=('recipe', 'user', ),
                name='unique_favorite_recipe_for_user'
            ),
        )

    def __str__(self):
        return f'{self.recipe.name} в избранном у {self.user.username}'
    

class ShoppingCart(models.Model):
    user = models.ForeignKey(
        User,
        related_name='carts',
        verbose_name='Пользователь',
        on_delete=models.CASCADE,
    )
    recipe = models.ForeignKey(
        Recipe,
        related_name='carts',
        verbose_name='Рецепт',
        on_delete=models.CASCADE,
    )

    class Meta:
        verbose_name = 'Список покупок'
        verbose_name_plural = 'Списки покупок'
        constraints = (
            models.UniqueConstraint(
                fields=('user', 'recipe', ),
                name='unique_recipe_user_in_cart'
            ),
        )

    def __str__(self):
        return f'{self.user.username} добавил {self.recipe.name} в список'