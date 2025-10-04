# metrics/urls.py

from django.urls import path
from . import views

app_name = 'metrics'

urlpatterns = [
    # === Indicatori ===
    
    # Crea indicatore per un esperimento
    path('experiment/<int:experiment_pk>/indicator/create/', 
         views.indicator_create, name='indicator_create'),
    
    # Modifica indicatore
    path('indicator/<int:pk>/edit/', 
         views.indicator_edit, name='indicator_edit'),
    
    # Elimina indicatore
    path('indicator/<int:pk>/delete/', 
         views.indicator_delete, name='indicator_delete'),
    
    # === Risultati ===
    
    # Aggiungi risultato manuale a un indicatore
    path('indicator/<int:indicator_pk>/result/create/', 
         views.result_create, name='result_create'),
    
    # Modifica risultato
    path('result/<int:pk>/edit/', 
         views.result_edit, name='result_edit'),
    
    # Elimina risultato
    path('result/<int:pk>/delete/', 
         views.result_delete, name='result_delete'),
    
    # Lista risultati di un indicatore (opzionale)
    path('indicator/<int:indicator_pk>/results/', 
         views.result_list, name='result_list'),
]
