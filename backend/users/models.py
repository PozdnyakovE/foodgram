from django.contrib.auth.models import AbstractUser
from django.db import models

from .validators import UsernameValidator


MAX_EMAIL_LENGTH = 250
MAX_NAME_LENGTH = 150
HELP_TEXT = 'Обязательное поле для заполнения'


class User(AbstractUser):
    email = models.EmailField(
        'Адрес электронной почты',
        max_length=MAX_EMAIL_LENGTH,
        unique=True,
        blank=False,
        null=False,
        db_index=True,
        help_text = HELP_TEXT
    )
    username = models.CharField(
        'Уникальное имя пользователя (никнейм)',
        max_length=MAX_NAME_LENGTH,
        unique=True,
        blank=False,
        null=False,
        help_text = HELP_TEXT,
        validators=(UsernameValidator, )
    )
    first_name = models.CharField(
        'Имя',
        max_length=MAX_NAME_LENGTH,
        blank=False,
        null=False,
        help_text = HELP_TEXT
    )
    last_name = models.CharField(
        'Фамилия',
        max_length=MAX_NAME_LENGTH,
        blank=False,
        null=False,
        help_text = HELP_TEXT
    )
    password = models.CharField(
        'Пароль',
        max_length=MAX_NAME_LENGTH,
        blank=False,
        null=False,
    )
    avatar = models.ImageField(
        'Аватар',
        upload_to='user_images/',
        blank=True,
    )

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ('username',)

    def __str__(self):
        return f'Ник:{self.username}, Почта:{self.email}'


class Subscription(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='subscriptions',
        verbose_name='Пользователь',
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='subscribers',
        verbose_name='Автор',
    )

    class Meta:
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'
        constraints = [
            models.UniqueConstraint(
                fields=('user', 'author'),
                name='unique_subscription'
            )
        ]

    def __str__(self):
        return f'{self.user.username} подписан на {self.author.username}'
