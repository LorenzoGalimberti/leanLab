# metrics/forms.py

from django import forms
from .models import Indicator, Result

class IndicatorForm(forms.ModelForm):
    """Form per creare/modificare un indicatore"""
    
    class Meta:
        model = Indicator
        # ✅ AGGIUNTO: 'test_type' nella lista campi
        fields = ['name', 'description', 'indicator_type', 'role', 'test_type', 'target_uplift']
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
            # ✅ NUOVO: Widget per test_type
            'test_type': forms.Select(attrs={
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
            'test_type': 'Tipo di Test',  # ✅ NUOVO
            'target_uplift': 'Target Miglioramento (%)'
        }
        help_texts = {
            'target_uplift': 'Percentuale di miglioramento attesa (es. 10 per +10%)',
            'role': 'Primario: obiettivo principale | Guardrail: metrica di sicurezza | Secondario: metrica di supporto',
            # ✅ NUOVO: Help text per test_type
            'test_type': 'A/B Test: varianti parallele | Pre/Post: prima/dopo rilascio | Single: misurazione baseline senza confronto'
        }


class ResultForm(forms.ModelForm):
    """
    Form per inserire un risultato manuale.
    ✅ DINAMICO: si adatta al test_type dell'indicatore
    """
    
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
    
    # ✅ NUOVO: __init__ per rendere il form dinamico
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Se stiamo modificando un Result esistente, prendi l'indicatore
        if self.instance and self.instance.pk:
            indicator = self.instance.indicator
        # Se stiamo creando un nuovo Result, l'indicatore viene passato dalla view
        # (lo gestiamo nella view stessa, qui prepariamo solo la logica)
        elif hasattr(self, 'indicator'):
            indicator = self.indicator
        else:
            # Fallback: non possiamo determinare il tipo, usa default A/B
            return
        
        # ✅ Adatta label e placeholder in base a test_type
        test_type = indicator.test_type
        
        if test_type == 'ab_test':
            # A/B Test: Control vs Variant (default, già impostato)
            self.fields['value_control'].label = 'Valore Control'
            self.fields['value_variant'].label = 'Valore Variant'
            self.fields['value_control'].widget.attrs['placeholder'] = 'Valore gruppo Control'
            self.fields['value_variant'].widget.attrs['placeholder'] = 'Valore gruppo Variant'
            self.fields['value_control'].help_text = 'Valore misurato nel gruppo di controllo'
            self.fields['value_variant'].help_text = 'Valore misurato nel gruppo variant'
        
        elif test_type == 'pre_post':
            # Pre/Post Test: Before vs After
            self.fields['value_control'].label = 'Valore PRIMA (Before)'
            self.fields['value_variant'].label = 'Valore DOPO (After)'
            self.fields['value_control'].widget.attrs['placeholder'] = 'Valore prima del rilascio'
            self.fields['value_variant'].widget.attrs['placeholder'] = 'Valore dopo il rilascio'
            self.fields['value_control'].help_text = 'Valore misurato prima del cambiamento'
            self.fields['value_variant'].help_text = 'Valore misurato dopo il cambiamento'
        
        elif test_type == 'single':
            # Single Baseline: un solo valore
            self.fields['value_control'].label = 'Valore Misurato'
            self.fields['value_control'].widget.attrs['placeholder'] = 'Valore baseline'
            self.fields['value_control'].help_text = 'Valore di riferimento (baseline)'
            
            # ✅ Nascondi il campo value_variant (lo popoleremo automaticamente nel save)
            # Invece di rimuoverlo, lo rendiamo non richiesto e nascosto via CSS
            self.fields['value_variant'].required = False
            self.fields['value_variant'].widget = forms.HiddenInput()
            
            