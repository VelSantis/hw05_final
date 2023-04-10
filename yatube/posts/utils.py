from django.core.paginator import Paginator
from django.conf import settings


def get_page_obj(request, objects):
    paginator = Paginator(objects, settings.PAGE_SIZE)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return page_obj
