# metrics/management/commands/seed_mock_data.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal
from projects.models import Project, Experiment
from metrics.models import Indicator, MockBigQueryData

class Command(BaseCommand):
    help = 'Popola il database con dati mock realistici per testare il flusso BigQuery'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🌱 Inizio seeding database...\n'))
        
        # Pulisci dati esistenti (opzionale)
        self.stdout.write('🧹 Pulizia dati esistenti...')
        MockBigQueryData.objects.all().delete()
        Indicator.objects.all().delete()
        Experiment.objects.all().delete()
        Project.objects.all().delete()
        
        # =======================
        # 1. CREA PROGETTO
        # =======================
        project = Project.objects.create(
            name="App Fitness Mobile",
            description="App mobile per tracking workout e nutrizione con funzionalità social",
            is_active=True
        )
        self.stdout.write(f'✅ Progetto creato: {project.name}')
        
        # =======================
        # 2. ESPERIMENTO 1: Onboarding Tutorial
        # =======================
        exp1 = Experiment.objects.create(
            project=project,
            title="Nuovo Tutorial Interattivo",
            hypothesis="Se rendiamo il tutorial più interattivo con gamification (badge, progress bar), "
                       "allora il completion rate aumenterà del 15% e la retention D7 del 10%",
            status='running',
            start_date=date.today() - timedelta(days=7),
            notes="Test su 50% utenti. Variant A: tutorial con badge e progress bar animata."
        )
        self.stdout.write(f'✅ Esperimento 1: {exp1.title}')
        
        # Indicatori Esperimento 1
        ind1_1 = Indicator.objects.create(
            experiment=exp1,
            name="Tutorial Completion Rate",
            description="Percentuale utenti che completano tutti i 5 step del tutorial",
            indicator_type='percentage',
            role='primary',
            target_uplift=Decimal('15.00'),
            bigquery_metric_key='completion_rate'
        )
        
        ind1_2 = Indicator.objects.create(
            experiment=exp1,
            name="Retention Day 7",
            description="Percentuale utenti che tornano dopo 7 giorni dalla registrazione",
            indicator_type='percentage',
            role='primary',
            target_uplift=Decimal('10.00'),
            bigquery_metric_key='retention_d7'
        )
        
        ind1_3 = Indicator.objects.create(
            experiment=exp1,
            name="Crash Rate",
            description="Percentuale sessioni con crash (guardrail: deve restare < 2%)",
            indicator_type='percentage',
            role='guardrail',
            target_uplift=Decimal('0.00'),
            bigquery_metric_key='crash_rate'
        )
        
        self.stdout.write(f'  → {exp1.indicators.count()} indicatori creati')
        
        # Mock BigQuery Data per Esperimento 1 (7 giorni di dati)
        for day_offset in range(7):
            day = date.today() - timedelta(days=6-day_offset)  # Da 6 giorni fa a oggi
            
            # Completion Rate: trend positivo
            MockBigQueryData.objects.create(
                experiment=exp1,
                metric_key='completion_rate',
                date=day,
                value_control=Decimal('62.5') + Decimal(day_offset * 0.5),
                value_variant=Decimal('74.0') + Decimal(day_offset * 0.8),
                sample_size_control=500 + day_offset * 50,
                sample_size_variant=500 + day_offset * 50
            )
            
            # Retention D7: dati disponibili solo dopo 7 giorni
            if day_offset >= 3:
                MockBigQueryData.objects.create(
                    experiment=exp1,
                    metric_key='retention_d7',
                    date=day,
                    value_control=Decimal('42.0') + Decimal(day_offset * 0.3),
                    value_variant=Decimal('48.5') + Decimal(day_offset * 0.4),
                    sample_size_control=450 + day_offset * 40,
                    sample_size_variant=450 + day_offset * 40
                )
            
            # Crash Rate: stabile (guardrail OK)
            MockBigQueryData.objects.create(
                experiment=exp1,
                metric_key='crash_rate',
                date=day,
                value_control=Decimal('1.2'),
                value_variant=Decimal('1.4'),
                sample_size_control=1000,
                sample_size_variant=1000
            )
        
        self.stdout.write(f'  → {MockBigQueryData.objects.filter(experiment=exp1).count()} righe mock BigQuery')
        
        # =======================
        # 3. ESPERIMENTO 2: Paywall Trial
        # =======================
        exp2 = Experiment.objects.create(
            project=project,
            title="Paywall con Trial 7gg invece di 3gg",
            hypothesis="Se offriamo 7 giorni di trial gratuito invece di 3, "
                       "allora il conversion rate aumenterà del 20%",
            status='running',
            start_date=date.today() - timedelta(days=5),
            notes="Test su utenti che aprono il paywall. Variant: 7gg trial vs Control: 3gg trial."
        )
        self.stdout.write(f'✅ Esperimento 2: {exp2.title}')
        
        # Indicatori Esperimento 2
        ind2_1 = Indicator.objects.create(
            experiment=exp2,
            name="Trial to Paid Conversion",
            description="Percentuale utenti che convertono da trial a premium",
            indicator_type='percentage',
            role='primary',
            target_uplift=Decimal('20.00'),
            bigquery_metric_key='conversion_rate'
        )
        
        ind2_2 = Indicator.objects.create(
            experiment=exp2,
            name="ARPU (Average Revenue Per User)",
            description="Revenue medio per utente nel periodo",
            indicator_type='revenue',
            role='secondary',
            target_uplift=Decimal('5.00'),
            bigquery_metric_key='arpu'
        )
        
        self.stdout.write(f'  → {exp2.indicators.count()} indicatori creati')
        
        # Mock BigQuery Data per Esperimento 2 (5 giorni)
        for day_offset in range(5):
            day = date.today() - timedelta(days=4-day_offset)
            
            # Conversion Rate: risultato positivo!
            MockBigQueryData.objects.create(
                experiment=exp2,
                metric_key='conversion_rate',
                date=day,
                value_control=Decimal('12.5'),
                value_variant=Decimal('16.2'),  # +29.6% 🎉
                sample_size_control=300,
                sample_size_variant=300
            )
            
            # ARPU: leggermente migliore
            MockBigQueryData.objects.create(
                experiment=exp2,
                metric_key='arpu',
                date=day,
                value_control=Decimal('1.85'),
                value_variant=Decimal('2.12'),  # +14.6%
                sample_size_control=300,
                sample_size_variant=300
            )
        
        self.stdout.write(f'  → {MockBigQueryData.objects.filter(experiment=exp2).count()} righe mock BigQuery')
        
        # =======================
        # 4. ESPERIMENTO 3: Home Redesign (FALLITO - PIVOT)
        # =======================
        exp3 = Experiment.objects.create(
            project=project,
            title="Home Screen Redesign con Cards",
            hypothesis="Se cambiamo il layout della home con card verticali invece di lista, "
                       "l'engagement aumenterà del 25%",
            status='completed',
            decision='pivot',
            start_date=date.today() - timedelta(days=14),
            end_date=date.today() - timedelta(days=1),
            notes="❌ PIVOT: L'esperimento ha peggiorato l'engagement del -12%. Rollback immediato effettuato."
        )
        self.stdout.write(f'✅ Esperimento 3: {exp3.title} (COMPLETATO - PIVOT)')
        
        # Indicatore Esperimento 3
        ind3_1 = Indicator.objects.create(
            experiment=exp3,
            name="Daily Active Users (DAU)",
            description="Percentuale utenti attivi giornalmente",
            indicator_type='percentage',
            role='primary',
            target_uplift=Decimal('25.00'),
            bigquery_metric_key='dau_rate'
        )
        
        # Mock BigQuery Data negativo
        MockBigQueryData.objects.create(
            experiment=exp3,
            metric_key='dau_rate',
            date=date.today() - timedelta(days=1),
            value_control=Decimal('58.3'),
            value_variant=Decimal('51.2'),  # PEGGIO! -12.2%
            sample_size_control=800,
            sample_size_variant=800
        )
        
        self.stdout.write(f'  → {exp3.indicators.count()} indicatori + mock data')
        
        # =======================
        # SUMMARY
        # =======================
        total_projects = Project.objects.count()
        total_experiments = Experiment.objects.count()
        total_indicators = Indicator.objects.count()
        total_mock_rows = MockBigQueryData.objects.count()
        
        self.stdout.write(self.style.SUCCESS(f'\n✅ SEEDING COMPLETATO!\n'))
        self.stdout.write(f'📊 Statistiche:')
        self.stdout.write(f'   - Progetti: {total_projects}')
        self.stdout.write(f'   - Esperimenti: {total_experiments}')
        self.stdout.write(f'   - Indicatori: {total_indicators}')
        self.stdout.write(f'   - Mock BigQuery Rows: {total_mock_rows}')
        self.stdout.write(self.style.SUCCESS(f'\n💡 Ora vai su http://localhost:8000/ e testa la web app!\n'))
        