from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('files/', views.FlowFileListView.as_view(), name='file_list'),
    path('files/<int:pk>/', views.FlowFileDetailView.as_view(), name='file_detail'),
    path('files/<int:pk>/delete/', views.FlowFileDeleteView.as_view(), name='file_delete'),
    path('meters/', views.MeterListView.as_view(), name='meter_list'),
    path('readings/', views.ReadingListView.as_view(), name='reading_list'),
    path('search/', views.search_readings, name='search_readings'),
]