import re

from django.core.exceptions import ValidationError

def UsernameValidator(username):
    if not bool(re.match(r'^[\w.@+-]+$', username)):
        raise ValidationError(
            'Поле username содержит недопустимые символы'
        )
    return username