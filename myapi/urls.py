from django.urls import path
from .views import *

urlpatterns = [
    path('get_response/',get_response),
    path('upload_file/', upload_file),
    path('get_file/', get_file),
    path('list_files/', list_files),
    path('delete_file/', delete_file),
    path('list_models/', list_models),
    path('current_model/', current_model),
    path('select_model/', select_model),
    path('add_model/', add_model),
    path('delete_model/', delete_model),
]
