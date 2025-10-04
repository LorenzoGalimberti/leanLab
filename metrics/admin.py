# metrics/admin.py

from django.contrib import admin
from .models import Indicator, Result, DefinedEvent, MockBigQueryData

@admin.register(Indicator)
class IndicatorAdmin(admin.ModelAdmin):
    list_display = [
        'name', 
        'experiment', 
        'indicator_type', 
        'role', 
        'target_uplift',
        'bigquery_metric_key'  # ✅ Mostra il nuovo campo
    ]
    list_filter = ['indicator_type', 'role', 'experiment__project']
    search_fields = ['name', 'description', 'bigquery_metric_key']
    list_select_related = ['experiment', 'experiment__project']

@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):
    list_display = [
        'indicator', 
        'measured_at', 
        'value_control', 
        'value_variant', 
        'delta_percentage', 
        'decision_auto'
    ]
    list_filter = ['decision_auto', 'measured_at']
    readonly_fields = ['delta_percentage', 'decision_auto', 'created_at']
    list_select_related = ['indicator', 'indicator__experiment']

@admin.register(DefinedEvent)
class DefinedEventAdmin(admin.ModelAdmin):
    list_display = ['name', 'alias']
    search_fields = ['name', 'alias']

# ✅ AGGIUNGI QUESTO
@admin.register(MockBigQueryData)
class MockBigQueryDataAdmin(admin.ModelAdmin):
    list_display = [
        'experiment',
        'metric_key',
        'date',
        'value_control',
        'value_variant',
        'sample_size_control',
        'sample_size_variant',
        'created_at'
    ]
    list_filter = ['metric_key', 'date', 'experiment']
    search_fields = ['experiment__title', 'metric_key']
    list_select_related = ['experiment', 'experiment__project']
    date_hierarchy = 'date'
    
    # Campi readonly per evitare modifiche accidentali dei timestamp
    readonly_fields = ['created_at']

    