# metrics/models.py

from django.db import models
from projects.models import Experiment

class Indicator(models.Model):
    """Indicatore/metrica da misurare"""
    
    TYPE_CHOICES = [
        ('percentage', 'Percentuale'),
        ('average', 'Media'),
        ('count', 'Conteggio'),
        ('revenue', 'Revenue'),
    ]
    
    ROLE_CHOICES = [
        ('primary', 'Primario'),
        ('guardrail', 'Guardrail'),
        ('secondary', 'Secondario'),
    ]
    
    experiment = models.ForeignKey(Experiment, on_delete=models.CASCADE, related_name='indicators')
    name = models.CharField(max_length=200, verbose_name="Nome Indicatore")
    description = models.TextField(blank=True, verbose_name="Descrizione")
    
    indicator_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='percentage')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='primary')
    
    target_uplift = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        help_text="Target % miglioramento (es. 10 per +10%)",
        verbose_name="Target Uplift %"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Indicatore"
        verbose_name_plural = "Indicatori"
        ordering = ['experiment', '-role', 'name']
    
    def __str__(self):
        return f"{self.experiment.title} - {self.name}"


class Result(models.Model):
    """Risultato di un indicatore in un momento specifico"""
    
    indicator = models.ForeignKey(Indicator, on_delete=models.CASCADE, related_name='results')
    measured_at = models.DateField(verbose_name="Data Misurazione")
    
    value_control = models.DecimalField(max_digits=12, decimal_places=4, verbose_name="Valore Control")
    value_variant = models.DecimalField(max_digits=12, decimal_places=4, verbose_name="Valore Variant")
    
    delta_percentage = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name="Delta %")
    decision_auto = models.CharField(max_length=20, blank=True, verbose_name="Decisione Auto")
    
    notes = models.TextField(blank=True, verbose_name="Note")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Risultato"
        verbose_name_plural = "Risultati"
        ordering = ['-measured_at']
    
    def save(self, *args, **kwargs):
        """Calcola automaticamente delta % e decisione"""
        if self.value_control and self.value_control != 0:
            self.delta_percentage = ((self.value_variant - self.value_control) / self.value_control) * 100
            
            # Decisione automatica
            if self.indicator.role == 'guardrail':
                # Guardrail: non deve peggiorare
                if self.delta_percentage < -5:  # Soglia -5%
                    self.decision_auto = 'pivot'
                else:
                    self.decision_auto = 'ok'
            else:
                # Indicatore primario/secondario
                if self.delta_percentage >= self.indicator.target_uplift:
                    self.decision_auto = 'persevere'
                else:
                    self.decision_auto = 'pivot'
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.indicator.name} - {self.measured_at}"


class DefinedEvent(models.Model):
    """Evento Firebase predefinito (opzionale per fase 1)"""
    name = models.CharField(max_length=100, unique=True)
    alias = models.CharField(max_length=100, verbose_name="Alias descrittivo")
    description = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Evento Definito"
        verbose_name_plural = "Eventi Definiti"
    
    def __str__(self):
        return self.alias
    