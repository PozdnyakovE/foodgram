def get_is_subscribed_value(self, obj):
    '''Вспомогательный метод для поля is_subscribed.'''
    request = self.context.get('request')
    if request and request.user.is_authenticated:
        return obj.subscribers.filter(user=request.user).exists()
    return False


def get_recipe_params(self, obj, model):
    '''Вспомогательный метод для поля модели рецептов.'''
    request = self.context.get('request')
    if request is None or request.user.is_anonymous:
        return False
    return model.objects.filter(user=request.user, recipe=obj).exists()