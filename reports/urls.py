# reports/urls.py

from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    # Per ora tutto commentato - creeremo le views una alla volta
    
    # # Genera PDF singolo esperimento
    # path('experiment/<int:experiment_pk>/pdf/', 
    #      views.experiment_pdf, name='experiment_pdf'),
    
    # # Genera PDF completo progetto (tutti gli esperimenti)
    # path('project/<int:project_pk>/pdf/', 
    #      views.project_pdf, name='project_pdf'),
    
    # # Esporta risultati in CSV (opzionale)
    # path('experiment/<int:experiment_pk>/csv/', 
    #      views.experiment_csv, name='experiment_csv'),
    
    # # Dashboard sintesi globale (tutti i progetti)
    # path('dashboard/', views.global_dashboard, name='global_dashboard'),
]