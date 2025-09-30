# projects/forms.py

from django import forms
from .models import Project, Experiment

class ProjectForm(forms.ModelForm):
    """Form per creare/modificare un progetto"""
    
    class Meta:
        model = Project
        fields = ['name', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Es: App Mobile Fitness'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Descrizione del progetto...'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
        labels = {
            'name': 'Nome Progetto',
            'description': 'Descrizione',
            'is_active': 'Progetto Attivo'
        }


class ExperimentForm(forms.ModelForm):
    """Form per creare/modificare un esperimento"""
    
    class Meta:
        model = Experiment
        fields = ['title', 'hypothesis', 'status', 'start_date', 'end_date', 'notes']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Es: Test nuovo onboarding'
            }),
            'hypothesis': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Se [azione], allora [risultato atteso]...'
            }),
            'status': forms.Select(attrs={
                'class': 'form-select'
            }),
            'start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'end_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Note aggiuntive...'
            }),
        }
        labels = {
            'title': 'Titolo Esperimento',
            'hypothesis': 'Ipotesi da Testare',
            'status': 'Stato',
            'start_date': 'Data Inizio',
            'end_date': 'Data Fine',
            'notes': 'Note'
        }