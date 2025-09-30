# leanlab/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    # Admin Django
    path('admin/', admin.site.urls),
    
    # Homepage → redirect a lista progetti
    path('', RedirectView.as_view(url='/projects/', permanent=False), name='home'),
    
    # App URLs
    path('projects/', include('projects.urls')),
    path('metrics/', include('metrics.urls')),
    path('reports/', include('reports.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Personalizzazione titoli Admin
admin.site.site_header = "LeanLab Admin"
admin.site.site_title = "LeanLab"
admin.site.index_title = "Gestione Esperimenti"