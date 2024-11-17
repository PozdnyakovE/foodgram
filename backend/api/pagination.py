from rest_framework.pagination import LimitOffsetPagination, PageNumberPagination


class PagePagination(PageNumberPagination):
    page_size_query_param = 'limit'
