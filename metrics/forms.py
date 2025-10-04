# metrics/forms.py

from django import forms
from .models import Indicator, Result

class IndicatorForm(forms.ModelForm):
    """Form per creare/modificare un indicatore"""
    
    class Meta:
        model = Indicator
        fields = ['name', 'description', 'indicator_type', 'role', 'target_uplift']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Es: Completion Rate Tutorial'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descrizione dettagliata dell\'indicatore...'
            }),
            'indicator_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'role': forms.Select(attrs={
                'class': 'form-select'
            }),
            'target_uplift': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Es: 10',
                'step': '0.01',
                'min': '0'
            }),
        }
        labels = {
            'name': 'Nome Indicatore',
            'description': 'Descrizione',
            'indicator_type': 'Tipo Indicatore',
            'role': 'Ruolo',
            'target_uplift': 'Target Miglioramento (%)'
        }
        help_texts = {
            'target_uplift': 'Percentuale di miglioramento attesa (es. 10 per +10%)',
            'role': 'Primario: obiettivo principale | Guardrail: metrica di sicurezza | Secondario: metrica di supporto'
        }


class ResultForm(forms.ModelForm):
    """Form per inserire un risultato manuale"""
    
    class Meta:
        model = Result
        fields = ['measured_at', 'value_control', 'value_variant', 'notes']
        widgets = {
            'measured_at': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'value_control': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Valore gruppo Control',
                'step': '0.0001'
            }),
            'value_variant': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Valore gruppo Variant',
                'step': '0.0001'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Note aggiuntive (opzionale)...'
            }),
        }
        labels = {
            'measured_at': 'Data Misurazione',
            'value_control': 'Valore Control',
            'value_variant': 'Valore Variant',
            'notes': 'Note'
        }
        help_texts = {
            'value_control': 'Valore misurato nel gruppo di controllo',
            'value_variant': 'Valore misurato nel gruppo variant (test)',
        }
        