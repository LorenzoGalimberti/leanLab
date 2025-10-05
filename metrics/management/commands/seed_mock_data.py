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
        self.stdout.write(self.style.SUCCESS('Inizio seeding database...\n'))
        
        # Pulisci dati esistenti
        self.stdout.write('Pulizia dati esistenti...')
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
        self.stdout.write(f'Progetto creato: {project.name}')
        
        # =======================
        # 2. ESPERIMENTO 1: Onboarding Tutorial (21 GIORNI)
        # =======================
        exp1 = Experiment.objects.create(
            project=project,
            title="Nuovo Tutorial Interattivo",
            hypothesis="Se rendiamo il tutorial più interattivo con gamification (badge, progress bar), "
                       "allora il completion rate aumenterà del 15% e la retention D7 del 10%",
            status='running',
            start_date=date.today() - timedelta(days=21),
            notes="Test su 50% utenti. Variant A: tutorial con badge e progress bar animata."
        )
        self.stdout.write(f'Esperimento 1: {exp1.title}')
        
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
        
        self.stdout.write(f'  {exp1.indicators.count()} indicatori creati')
        
        # Mock BigQuery Data per Esperimento 1 (21 giorni)
        for day_offset in range(21):
            day = date.today() - timedelta(days=20-day_offset)
            
            # Completion Rate: trend positivo crescente
            base_control = Decimal('62.5')
            base_variant = Decimal('74.0')
            noise_control = Decimal(day_offset % 3) * Decimal('0.3')  # Variabilità realistica
            noise_variant = Decimal(day_offset % 3) * Decimal('0.5')
            
            MockBigQueryData.objects.create(
                experiment=exp1,
                metric_key='completion_rate',
                date=day,
                value_control=base_control + Decimal(day_offset * 0.2) + noise_control,
                value_variant=base_variant + Decimal(day_offset * 0.35) + noise_variant,
                sample_size_control=500 + day_offset * 30,
                sample_size_variant=500 + day_offset * 30
            )
            
            # Retention D7: dati disponibili solo dopo 7 giorni
            if day_offset >= 7:
                MockBigQueryData.objects.create(
                    experiment=exp1,
                    metric_key='retention_d7',
                    date=day,
                    value_control=Decimal('42.0') + Decimal((day_offset-7) * 0.15),
                    value_variant=Decimal('48.5') + Decimal((day_offset-7) * 0.22),
                    sample_size_control=450 + (day_offset-7) * 25,
                    sample_size_variant=450 + (day_offset-7) * 25
                )
            
            # Crash Rate: stabile con piccole fluttuazioni (guardrail OK)
            crash_noise = Decimal((day_offset % 5) * 0.05)
            MockBigQueryData.objects.create(
                experiment=exp1,
                metric_key='crash_rate',
                date=day,
                value_control=Decimal('1.2') + crash_noise,
                value_variant=Decimal('1.4') + crash_noise,
                sample_size_control=1000 + day_offset * 20,
                sample_size_variant=1000 + day_offset * 20
            )
        
        self.stdout.write(f'  {MockBigQueryData.objects.filter(experiment=exp1).count()} righe mock BigQuery')
        
        # =======================
        # 3. ESPERIMENTO 2: Paywall Trial (14 GIORNI)
        # =======================
        exp2 = Experiment.objects.create(
            project=project,
            title="Paywall con Trial 7gg invece di 3gg",
            hypothesis="Se offriamo 7 giorni di trial gratuito invece di 3, "
                       "allora il conversion rate aumenterà del 20%",
            status='running',
            start_date=date.today() - timedelta(days=14),
            notes="Test su utenti che aprono il paywall. Variant: 7gg trial vs Control: 3gg trial."
        )
        self.stdout.write(f'Esperimento 2: {exp2.title}')
        
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
        
        ind2_3 = Indicator.objects.create(
            experiment=exp2,
            name="Churn Rate dopo 30gg",
            description="Percentuale utenti che cancellano abbonamento (guardrail)",
            indicator_type='percentage',
            role='guardrail',
            target_uplift=Decimal('0.00'),
            bigquery_metric_key='churn_rate'
        )
        
        self.stdout.write(f'  {exp2.indicators.count()} indicatori creati')
        
        # Mock BigQuery Data per Esperimento 2 (14 giorni)
        for day_offset in range(14):
            day = date.today() - timedelta(days=13-day_offset)
            
            # Conversion Rate: risultato molto positivo con trend stabile
            conv_noise = Decimal((day_offset % 4) * 0.2)
            MockBigQueryData.objects.create(
                experiment=exp2,
                metric_key='conversion_rate',
                date=day,
                value_control=Decimal('12.5') + conv_noise,
                value_variant=Decimal('16.8') + conv_noise,  # +34% circa
                sample_size_control=280 + day_offset * 15,
                sample_size_variant=280 + day_offset * 15
            )
            
            # ARPU: migliora gradualmente
            MockBigQueryData.objects.create(
                experiment=exp2,
                metric_key='arpu',
                date=day,
                value_control=Decimal('1.85') + Decimal(day_offset * 0.01),
                value_variant=Decimal('2.18') + Decimal(day_offset * 0.015),
                sample_size_control=280 + day_offset * 15,
                sample_size_variant=280 + day_offset * 15
            )
            
            # Churn Rate: leggermente peggiore ma entro guardrail
            if day_offset >= 5:  # Dati disponibili dopo 5 giorni
                MockBigQueryData.objects.create(
                    experiment=exp2,
                    metric_key='churn_rate',
                    date=day,
                    value_control=Decimal('8.5'),
                    value_variant=Decimal('9.2'),  # +8% ma sotto soglia critica
                    sample_size_control=200,
                    sample_size_variant=200
                )
        
        self.stdout.write(f'  {MockBigQueryData.objects.filter(experiment=exp2).count()} righe mock BigQuery')
        
        # =======================
        # 4. ESPERIMENTO 3: Home Redesign (30 GIORNI - COMPLETATO)
        # =======================
        exp3 = Experiment.objects.create(
            project=project,
            title="Home Screen Redesign con Cards",
            hypothesis="Se cambiamo il layout della home con card verticali invece di lista, "
                       "l'engagement aumenterà del 25%",
            status='completed',
            decision='pivot',
            start_date=date.today() - timedelta(days=45),
            end_date=date.today() - timedelta(days=15),
            notes="PIVOT: Esperimento fallito. Engagement -12%, tempo sessione -8%. Rollback effettuato."
        )
        self.stdout.write(f'Esperimento 3: {exp3.title} (COMPLETATO - PIVOT)')
        
        # Indicatori Esperimento 3
        ind3_1 = Indicator.objects.create(
            experiment=exp3,
            name="Daily Active Users (DAU)",
            description="Percentuale utenti attivi giornalmente",
            indicator_type='percentage',
            role='primary',
            target_uplift=Decimal('25.00'),
            bigquery_metric_key='dau_rate'
        )
        
        ind3_2 = Indicator.objects.create(
            experiment=exp3,
            name="Avg Session Duration",
            description="Durata media sessione in minuti",
            indicator_type='average',
            role='primary',
            target_uplift=Decimal('15.00'),
            bigquery_metric_key='session_duration'
        )
        
        ind3_3 = Indicator.objects.create(
            experiment=exp3,
            name="Actions per Session",
            description="Numero medio azioni per sessione",
            indicator_type='count',
            role='secondary',
            target_uplift=Decimal('20.00'),
            bigquery_metric_key='actions_per_session'
        )
        
        self.stdout.write(f'  {exp3.indicators.count()} indicatori creati')
        
        # Mock BigQuery Data NEGATIVO per 30 giorni
        for day_offset in range(30):
            day = date.today() - timedelta(days=44-day_offset)
            
            # DAU: peggioramento graduale
            dau_decline = Decimal(day_offset * 0.08)
            MockBigQueryData.objects.create(
                experiment=exp3,
                metric_key='dau_rate',
                date=day,
                value_control=Decimal('58.3') - dau_decline * Decimal('0.3'),
                value_variant=Decimal('51.2') - dau_decline * Decimal('0.5'),  # PEGGIO
                sample_size_control=800 + day_offset * 10,
                sample_size_variant=800 + day_offset * 10
            )
            
            # Session Duration: anche questo peggiora
            MockBigQueryData.objects.create(
                experiment=exp3,
                metric_key='session_duration',
                date=day,
                value_control=Decimal('8.5'),
                value_variant=Decimal('7.8'),  # -8%
                sample_size_control=800 + day_offset * 10,
                sample_size_variant=800 + day_offset * 10
            )
            
            # Actions: leggermente meglio ma non basta
            MockBigQueryData.objects.create(
                experiment=exp3,
                metric_key='actions_per_session',
                date=day,
                value_control=Decimal('12.3'),
                value_variant=Decimal('13.1'),  # +6.5% (non raggiunge +20%)
                sample_size_control=800 + day_offset * 10,
                sample_size_variant=800 + day_offset * 10
            )
        
        self.stdout.write(f'  {MockBigQueryData.objects.filter(experiment=exp3).count()} righe mock BigQuery')
        
        # =======================
        # SUMMARY
        # =======================
        total_projects = Project.objects.count()
        total_experiments = Experiment.objects.count()
        total_indicators = Indicator.objects.count()
        total_mock_rows = MockBigQueryData.objects.count()
        
        self.stdout.write(self.style.SUCCESS(f'\nSEEDING COMPLETATO!\n'))
        self.stdout.write(f'Statistiche:')
        self.stdout.write(f'   - Progetti: {total_projects}')
        self.stdout.write(f'   - Esperimenti: {total_experiments}')
        self.stdout.write(f'   - Indicatori: {total_indicators}')
        self.stdout.write(f'   - Mock BigQuery Rows: {total_mock_rows}')
        self.stdout.write(self.style.SUCCESS(f'\nOra testa la web app su http://localhost:8000/\n'))
        