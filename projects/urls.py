# projects/urls.py

from django.urls import path
from . import views

app_name = 'projects'

urlpatterns = [
    # Lista progetti
    path('', views.project_list, name='list'),
    
    # CRUD Progetti
    path('create/', views.project_create, name='create'),
    path('<int:pk>/', views.project_detail, name='detail'),
    path('<int:pk>/edit/', views.project_edit, name='edit'),
    path('<int:pk>/delete/', views.project_delete, name='delete'),
    
    # Esperimenti
    path('<int:project_pk>/experiments/', views.experiment_list, name='experiment_list'),
    path('<int:project_pk>/experiments/create/', views.experiment_create, name='experiment_create'),
    path('<int:project_pk>/experiments/<int:pk>/', views.experiment_detail, name='experiment_detail'),
    path('<int:project_pk>/experiments/<int:pk>/edit/', views.experiment_edit, name='experiment_edit'),
    path('<int:project_pk>/experiments/<int:pk>/delete/', views.experiment_delete, name='experiment_delete'),
    path('<int:project_pk>/experiments/<int:pk>/dashboard/', views.experiment_dashboard, name='experiment_dashboard'),
    
    # ✅ AGGIUNGI QUESTA RIGA
    path('<int:project_pk>/experiments/<int:pk>/update-bigquery/', 
         views.experiment_update_from_bigquery, 
         name='experiment_update_bigquery'),
]
