# projects/models.py

from django.db import models
from django.utils import timezone

class Project(models.Model):
    """Progetto principale (es. un'app mobile)"""
    name = models.CharField(max_length=200, verbose_name="Nome Progetto")
    description = models.TextField(blank=True, verbose_name="Descrizione")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True, verbose_name="Attivo")
    
    class Meta:
        verbose_name = "Progetto"
        verbose_name_plural = "Progetti"
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name


class Experiment(models.Model):
    """Esperimento A/B collegato a un progetto"""
    
    STATUS_CHOICES = [
        ('draft', 'Bozza'),
        ('running', 'In corso'),
        ('completed', 'Completato'),
    ]
    
    DECISION_CHOICES = [
        ('pending', 'In attesa'),
        ('persevere', 'Persevere'),
        ('pivot', 'Pivot'),
    ]
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='experiments')
    title = models.CharField(max_length=200, verbose_name="Titolo Esperimento")
    hypothesis = models.TextField(verbose_name="Ipotesi da testare")
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    decision = models.CharField(max_length=20, choices=DECISION_CHOICES, default='pending')
    
    start_date = models.DateField(null=True, blank=True, verbose_name="Data Inizio")
    end_date = models.DateField(null=True, blank=True, verbose_name="Data Fine")
    
    notes = models.TextField(blank=True, verbose_name="Note")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Esperimento"
        verbose_name_plural = "Esperimenti"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.project.name} - {self.title}"