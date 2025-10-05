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
    
    # ========================================
    # ✅ METODI NUOVI PER CALCOLO DECISIONE
    # ========================================
    
    def calculate_decision(self):
        """
        Calcola la decisione finale dell'esperimento basandosi su tutti gli indicatori.
        
        Logica:
        1. Se ci sono guardrail che falliscono → PIVOT
        2. Se tutti i primari raggiungono target → PERSEVERE
        3. Altrimenti → PIVOT
        
        Returns:
            str: 'persevere', 'pivot', o 'pending' se non ci sono risultati
        """
        indicators = self.indicators.all()
        
        if not indicators.exists():
            return 'pending'
        
        # Verifica se tutti gli indicatori hanno almeno un risultato
        indicators_with_results = [ind for ind in indicators if ind.results.exists()]
        if not indicators_with_results:
            return 'pending'
        
        # Controlla guardrail
        guardrails = [ind for ind in indicators_with_results if ind.role == 'guardrail']
        for guardrail in guardrails:
            latest_result = guardrail.results.first()  # Ordinato per -measured_at
            if latest_result and latest_result.decision_auto == 'pivot':
                return 'pivot'  # Guardrail fallito → PIVOT immediato
        
        # Controlla indicatori primari
        primaries = [ind for ind in indicators_with_results if ind.role == 'primary']
        if not primaries:
            return 'pending'  # Nessun indicatore primario
        
        # Tutti i primari devono essere "persevere"
        all_primaries_ok = True
        for primary in primaries:
            latest_result = primary.results.first()
            if not latest_result or latest_result.decision_auto != 'persevere':
                all_primaries_ok = False
                break
        
        return 'persevere' if all_primaries_ok else 'pivot'
    
    def update_decision(self):
        """Aggiorna il campo decision chiamando calculate_decision() e salva"""
        new_decision = self.calculate_decision()
        if self.decision != new_decision:
            self.decision = new_decision
            self.save(update_fields=['decision', 'updated_at'])
        return new_decision
    
    def get_decision_summary(self):
        """
        Ritorna un dizionario con il riepilogo della decisione
        
        Returns:
            dict: {
                'decision': str,
                'primary_count': int,
                'primary_ok': int,
                'guardrail_count': int,
                'guardrail_failed': int,
                'message': str
            }
        """
        indicators = self.indicators.all()
        
        primaries = [ind for ind in indicators if ind.role == 'primary' and ind.results.exists()]
        guardrails = [ind for ind in indicators if ind.role == 'guardrail' and ind.results.exists()]
        
        primary_ok = sum(1 for ind in primaries 
                        if ind.results.first() and ind.results.first().decision_auto == 'persevere')
        
        guardrail_failed = sum(1 for ind in guardrails 
                              if ind.results.first() and ind.results.first().decision_auto == 'pivot')
        
        decision = self.calculate_decision()
        
        # Genera messaggio descrittivo
        if decision == 'pending':
            message = "In attesa di risultati"
        elif guardrail_failed > 0:
            message = f"❌ {guardrail_failed} guardrail falliti"
        elif decision == 'persevere':
            message = f"✅ Tutti i {len(primaries)} indicatori primari OK"
        else:
            message = f"⚠️ Solo {primary_ok}/{len(primaries)} indicatori primari OK"
        
        return {
            'decision': decision,
            'primary_count': len(primaries),
            'primary_ok': primary_ok,
            'guardrail_count': len(guardrails),
            'guardrail_failed': guardrail_failed,
            'message': message
        }
    
    