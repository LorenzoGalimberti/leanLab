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
    
    # ✅ NUOVO: Scelta del tipo di test
    TEST_TYPE_CHOICES = [
        ('ab_test', 'A/B Test (Control vs Variant)'),
        ('pre_post', 'Pre/Post Test (Before vs After)'),
        ('single', 'Misurazione Singola (Baseline)'),
    ]
    
    experiment = models.ForeignKey(Experiment, on_delete=models.CASCADE, related_name='indicators')
    name = models.CharField(max_length=200, verbose_name="Nome Indicatore")
    description = models.TextField(blank=True, verbose_name="Descrizione")
    
    indicator_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='percentage')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='primary')
    
    # ✅ NUOVO: Campo test_type
    test_type = models.CharField(
        max_length=20,
        choices=TEST_TYPE_CHOICES,
        default='ab_test',
        verbose_name="Tipo di Test",
        help_text="A/B Test per varianti parallele, Pre/Post per before/after, Single per baseline"
    )
    
    target_uplift = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        help_text="Target % miglioramento (es. 10 per +10%)",
        verbose_name="Target Uplift %"
    )
    
    # Campo per mapping BigQuery (già esistente, ottimo!)
    bigquery_metric_key = models.CharField(
        max_length=100,
        blank=True,
        help_text="Chiave per recuperare dati da MockBigQueryData (es: completion_rate, retention_d7)",
        verbose_name="Metric Key BigQuery"
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
        """
        Calcola automaticamente delta % e decisione.
        ✅ Gestisce diversi tipi di test: A/B, Pre/Post, Single
        """
        
        # ✅ NUOVO: Gestione test_type = 'single' (Baseline)
        if self.indicator.test_type == 'single':
            # Per baseline: copia value_control in value_variant
            self.value_variant = self.value_control
            self.delta_percentage = 0
            self.decision_auto = 'baseline'
            super().save(*args, **kwargs)
            # Aggiorna decisione esperimento
            self.indicator.experiment.update_decision()
            return  # Esce subito, non serve altra logica
        
        # ✅ LOGICA ESISTENTE: A/B Test e Pre/Post Test
        if self.value_control and self.value_control != 0:
            self.delta_percentage = ((self.value_variant - self.value_control) / self.value_control) * 100
            
            # Decisione automatica
            if self.indicator.role == 'guardrail':
                # Guardrail: non deve peggiorare (soglia -5%)
                if self.delta_percentage < -5:
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
        
        # Aggiorna la decisione dell'esperimento
        self.indicator.experiment.update_decision()
    
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


# ========================================
# MODEL: MockBigQueryData
# ========================================

class MockBigQueryData(models.Model):
    """
    Simula i dati aggregati che tornerebbero da BigQuery.
    In produzione questo model non esiste, si interroga direttamente BigQuery.
    
    Esempio: se BigQuery restituisce "control: 64.5%, variant: 78.3%",
    qui salviamo quella riga già aggregata.
    
    Questo è utile per:
    1. Testing senza accesso a BigQuery reale
    2. Sviluppo locale con dati simulati
    3. Mockare risposte API durante la Fase 1
    """
    
    experiment = models.ForeignKey(
        'projects.Experiment',
        on_delete=models.CASCADE,
        related_name='mock_bigquery_data',
        help_text="Esperimento a cui si riferiscono questi dati"
    )
    
    metric_key = models.CharField(
        max_length=100,
        help_text="Identificatore metrica (es: completion_rate, retention_d7, arpu)"
    )
    
    date = models.DateField(
        help_text="Data a cui si riferiscono i dati aggregati"
    )
    
    # Valori aggregati (come tornano da BigQuery)
    value_control = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        help_text="Valore aggregato gruppo Control"
    )
    
    value_variant = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        null=True,  # ✅ AGGIUNTO: permette NULL per baseline
        blank=True,  # ✅ AGGIUNTO: permette form vuoto
        help_text="Valore aggregato gruppo Variant (NULL per baseline)"
    )
    
    # Metadata utili (opzionali ma utili per debugging)
    sample_size_control = models.IntegerField(
        default=0,
        help_text="Numero utenti nel gruppo Control"
    )
    
    sample_size_variant = models.IntegerField(
        default=0,
        help_text="Numero utenti nel gruppo Variant"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Mock BigQuery Data"
        verbose_name_plural = "Mock BigQuery Data"
        ordering = ['-date', 'experiment', 'metric_key']
        # Evita duplicati: stessa combinazione exp+metric+data
        unique_together = ['experiment', 'metric_key', 'date']
    
    def __str__(self):
        return f"{self.experiment.title} | {self.metric_key} | {self.date}"
    