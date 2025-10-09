# metrics/management/commands/seed_mock_data.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal
from projects.models import Project, Experiment
from metrics.models import Indicator, MockBigQueryData, Result

class Command(BaseCommand):
    help = 'Popola il database con dati mock realistici per testare tutti i test_type'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Inizio seeding database...\n'))
        
        # Pulisci dati esistenti
        self.stdout.write('Pulizia dati esistenti...')
        Result.objects.all().delete()
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
        # 2. ESPERIMENTO 1: A/B TEST - Onboarding Tutorial (21 GIORNI)
        # =======================
        exp1 = Experiment.objects.create(
            project=project,
            title="Nuovo Tutorial Interattivo (A/B Test)",
            hypothesis="Se rendiamo il tutorial più interattivo con gamification (badge, progress bar), "
                       "allora il completion rate aumenterà del 15% e la retention D7 del 10%",
            status='running',
            start_date=date.today() - timedelta(days=21),
            notes="Test A/B su 50% utenti. Control: tutorial classico | Variant: tutorial con badge e progress bar animata."
        )
        self.stdout.write(f'\n📊 Esperimento 1 (A/B TEST): {exp1.title}')
        
        # Indicatori Esperimento 1 (A/B Test)
        ind1_1 = Indicator.objects.create(
            experiment=exp1,
            name="Tutorial Completion Rate",
            description="Percentuale utenti che completano tutti i 5 step del tutorial",
            indicator_type='percentage',
            role='primary',
            test_type='ab_test',  # ✅ A/B TEST
            target_uplift=Decimal('15.00'),
            bigquery_metric_key='completion_rate'
        )
        
        ind1_2 = Indicator.objects.create(
            experiment=exp1,
            name="Retention Day 7",
            description="Percentuale utenti che tornano dopo 7 giorni dalla registrazione",
            indicator_type='percentage',
            role='primary',
            test_type='ab_test',  # ✅ A/B TEST
            target_uplift=Decimal('10.00'),
            bigquery_metric_key='retention_d7'
        )
        
        ind1_3 = Indicator.objects.create(
            experiment=exp1,
            name="Crash Rate",
            description="Percentuale sessioni con crash (guardrail: deve restare < 2%)",
            indicator_type='percentage',
            role='guardrail',
            test_type='ab_test',  # ✅ A/B TEST
            target_uplift=Decimal('0.00'),
            bigquery_metric_key='crash_rate'
        )
        
        self.stdout.write(f'  ✅ {exp1.indicators.count()} indicatori A/B TEST creati')
        
        # Mock BigQuery Data + Results per Esperimento 1 (21 giorni)
        for day_offset in range(21):
            day = date.today() - timedelta(days=20-day_offset)
            
            # Completion Rate: trend positivo crescente
            base_control = Decimal('62.5')
            base_variant = Decimal('74.0')
            noise_control = Decimal(day_offset % 3) * Decimal('0.3')
            noise_variant = Decimal(day_offset % 3) * Decimal('0.5')
            
            control_val = base_control + Decimal(day_offset * 0.2) + noise_control
            variant_val = base_variant + Decimal(day_offset * 0.35) + noise_variant
            
            MockBigQueryData.objects.create(
                experiment=exp1,
                metric_key='completion_rate',
                date=day,
                value_control=control_val,
                value_variant=variant_val,
                sample_size_control=500 + day_offset * 30,
                sample_size_variant=500 + day_offset * 30
            )
            
            # Crea Result ogni 3 giorni
            if day_offset % 3 == 0:
                Result.objects.create(
                    indicator=ind1_1,
                    measured_at=day,
                    value_control=control_val,
                    value_variant=variant_val,
                    notes=f"Dati A/B Test giorno {day_offset+1}"
                )
            
            # Retention D7: dati disponibili solo dopo 7 giorni
            if day_offset >= 7:
                ret_control = Decimal('42.0') + Decimal((day_offset-7) * 0.15)
                ret_variant = Decimal('48.5') + Decimal((day_offset-7) * 0.22)
                
                MockBigQueryData.objects.create(
                    experiment=exp1,
                    metric_key='retention_d7',
                    date=day,
                    value_control=ret_control,
                    value_variant=ret_variant,
                    sample_size_control=450 + (day_offset-7) * 25,
                    sample_size_variant=450 + (day_offset-7) * 25
                )
                
                if day_offset % 7 == 0:
                    Result.objects.create(
                        indicator=ind1_2,
                        measured_at=day,
                        value_control=ret_control,
                        value_variant=ret_variant,
                        notes=f"Retention D7 settimana {(day_offset-7)//7 + 1}"
                    )
            
            # Crash Rate: stabile (guardrail OK)
            crash_noise = Decimal((day_offset % 5) * 0.05)
            crash_control = Decimal('1.2') + crash_noise
            crash_variant = Decimal('1.4') + crash_noise
            
            MockBigQueryData.objects.create(
                experiment=exp1,
                metric_key='crash_rate',
                date=day,
                value_control=crash_control,
                value_variant=crash_variant,
                sample_size_control=1000 + day_offset * 20,
                sample_size_variant=1000 + day_offset * 20
            )
            
            if day_offset % 5 == 0:
                Result.objects.create(
                    indicator=ind1_3,
                    measured_at=day,
                    value_control=crash_control,
                    value_variant=crash_variant,
                    notes="Guardrail check"
                )
        
        self.stdout.write(f'  ✅ {MockBigQueryData.objects.filter(experiment=exp1).count()} mock rows BigQuery')
        self.stdout.write(f'  ✅ {Result.objects.filter(indicator__experiment=exp1).count()} Result rows')
        
        # =======================
        # 3. ESPERIMENTO 2: PRE/POST TEST - Login Social (14 GIORNI)
        # =======================
        exp2 = Experiment.objects.create(
            project=project,
            title="Aggiunta Login Social (Pre/Post Test)",
            hypothesis="Se aggiungiamo il login con Google/Apple oltre a email/password, "
                       "la conversion rate di signup aumenterà del 30%",
            status='completed',
            decision='persevere',
            start_date=date.today() - timedelta(days=21),
            end_date=date.today() - timedelta(days=7),
            notes="Pre/Post Test. BEFORE: 7 giorni solo email/password | Rilascio: giorno 8 | AFTER: 7 giorni con social login"
        )
        self.stdout.write(f'\n📊 Esperimento 2 (PRE/POST TEST): {exp2.title}')
        
        # Indicatori Esperimento 2 (Pre/Post)
        ind2_1 = Indicator.objects.create(
            experiment=exp2,
            name="Signup Conversion Rate",
            description="Percentuale visitatori che completano registrazione",
            indicator_type='percentage',
            role='primary',
            test_type='pre_post',  # ✅ PRE/POST TEST
            target_uplift=Decimal('30.00'),
            bigquery_metric_key='signup_conversion'
        )
        
        ind2_2 = Indicator.objects.create(
            experiment=exp2,
            name="Time to Complete Signup",
            description="Tempo medio per completare signup (secondi)",
            indicator_type='average',
            role='secondary',
            test_type='pre_post',  # ✅ PRE/POST TEST
            target_uplift=Decimal('20.00'),
            bigquery_metric_key='signup_time'
        )
        
        ind2_3 = Indicator.objects.create(
            experiment=exp2,
            name="Signup Abandonment Rate",
            description="Percentuale utenti che abbandonano il form (guardrail)",
            indicator_type='percentage',
            role='guardrail',
            test_type='pre_post',  # ✅ PRE/POST TEST
            target_uplift=Decimal('0.00'),
            bigquery_metric_key='signup_abandonment'
        )
        
        self.stdout.write(f'  ✅ {exp2.indicators.count()} indicatori PRE/POST creati')
        
        # Mock BigQuery Data PRE/POST
        # BEFORE (7 giorni): value_control
        # AFTER (7 giorni): value_variant
        
        # BEFORE period
        for day_offset in range(7):
            day = date.today() - timedelta(days=20-day_offset)
            
            MockBigQueryData.objects.create(
                experiment=exp2,
                metric_key='signup_conversion',
                date=day,
                value_control=Decimal('8.2') + Decimal(day_offset * 0.05),  # Before
                value_variant=Decimal('0.0'),  # Non ancora rilasciato
                sample_size_control=350 + day_offset * 20
            )
        
        # AFTER period
        for day_offset in range(7, 14):
            day = date.today() - timedelta(days=20-day_offset)
            
            after_val = Decimal('14.7') + Decimal((day_offset-7) * 0.3)
            
            MockBigQueryData.objects.create(
                experiment=exp2,
                metric_key='signup_conversion',
                date=day,
                value_control=Decimal('0.0'),  # Before finito
                value_variant=after_val,  # After
                sample_size_variant=350 + (day_offset-7) * 20
            )
        
        # Crea 1 Result finale Pre/Post
        Result.objects.create(
            indicator=ind2_1,
            measured_at=date.today() - timedelta(days=7),
            value_control=Decimal('8.45'),   # Media BEFORE
            value_variant=Decimal('15.80'),  # Media AFTER
            notes="Pre/Post Test: Before (7gg) vs After (7gg) - PERSEVERE: +87% conversion"
        )
        
        # Time to signup
        Result.objects.create(
            indicator=ind2_2,
            measured_at=date.today() - timedelta(days=7),
            value_control=Decimal('124.5'),  # Before: 124s
            value_variant=Decimal('68.2'),   # After: 68s (-45%)
            notes="Tempo signup drasticamente ridotto con social login"
        )
        
        # Abandonment (guardrail)
        Result.objects.create(
            indicator=ind2_3,
            measured_at=date.today() - timedelta(days=7),
            value_control=Decimal('42.3'),   # Before: 42.3%
            value_variant=Decimal('28.7'),   # After: 28.7% (miglioramento)
            notes="Guardrail OK: abbandono ridotto con social login"
        )
        
        self.stdout.write(f'  ✅ {MockBigQueryData.objects.filter(experiment=exp2).count()} mock rows BigQuery')
        self.stdout.write(f'  ✅ {Result.objects.filter(indicator__experiment=exp2).count()} Result rows')
        
        # =======================
        # 4. ESPERIMENTO 3: SINGLE BASELINE - Prima Settimana Lancio (7 GIORNI)
        # =======================
        exp3 = Experiment.objects.create(
            project=project,
            title="Baseline Metrics - Prima Settimana Lancio",
            hypothesis="Misurazione baseline per stabilire metriche di riferimento del primo lancio app",
            status='completed',
            decision='pending',
            start_date=date.today() - timedelta(days=60),
            end_date=date.today() - timedelta(days=53),
            notes="Single baseline: prima settimana lancio app, no confronto, solo reference values"
        )
        self.stdout.write(f'\n📊 Esperimento 3 (SINGLE BASELINE): {exp3.title}')
        
        # Indicatori Esperimento 3 (Single Baseline)
        ind3_1 = Indicator.objects.create(
            experiment=exp3,
            name="Tutorial Completion Rate (Baseline)",
            description="Baseline: % utenti che completano tutorial nella prima settimana",
            indicator_type='percentage',
            role='primary',
            test_type='single',  # ✅ SINGLE BASELINE
            target_uplift=Decimal('0.00'),  # N/A per baseline
            bigquery_metric_key='tutorial_completion_baseline'
        )
        
        ind3_2 = Indicator.objects.create(
            experiment=exp3,
            name="DAU Rate (Baseline)",
            description="Baseline: Daily Active Users % nella prima settimana",
            indicator_type='percentage',
            role='primary',
            test_type='single',  # ✅ SINGLE BASELINE
            target_uplift=Decimal('0.00'),
            bigquery_metric_key='dau_baseline'
        )
        
        ind3_3 = Indicator.objects.create(
            experiment=exp3,
            name="Avg Session Duration (Baseline)",
            description="Baseline: durata media sessione primi utenti",
            indicator_type='average',
            role='secondary',
            test_type='single',  # ✅ SINGLE BASELINE
            target_uplift=Decimal('0.00'),
            bigquery_metric_key='session_duration_baseline'
        )
        
        self.stdout.write(f'  ✅ {exp3.indicators.count()} indicatori SINGLE BASELINE creati')
        
        # ✅ CORRETTO: Mock BigQuery Data per Baseline (7 giorni)
        # Un solo bacino di utenti, nessuna divisione Control/Variant
        for day_offset in range(7):
            day = date.today() - timedelta(days=59-day_offset)
            
            # Tutorial completion baseline
            baseline_completion = Decimal('68.5') + Decimal(day_offset * 0.4)
            MockBigQueryData.objects.create(
                experiment=exp3,
                metric_key='tutorial_completion_baseline',
                date=day,
                value_control=baseline_completion,  # ← Valore unico (tutti gli utenti)
                value_variant=None,  # ← NULL (non esiste variant per baseline)
                sample_size_control=240 + day_offset * 30,  # ← Tutti gli utenti insieme
                sample_size_variant=0  # ← Non applicabile
            )
            
            # DAU baseline
            baseline_dau = Decimal('45.2') + Decimal(day_offset * 0.8)
            MockBigQueryData.objects.create(
                experiment=exp3,
                metric_key='dau_baseline',
                date=day,
                value_control=baseline_dau,
                value_variant=None,
                sample_size_control=240 + day_offset * 30,
                sample_size_variant=0
            )
            
            # Session duration baseline
            baseline_session = Decimal('6.8') + Decimal(day_offset * 0.2)
            MockBigQueryData.objects.create(
                experiment=exp3,
                metric_key='session_duration_baseline',
                date=day,
                value_control=baseline_session,
                value_variant=None,
                sample_size_control=240 + day_offset * 30,
                sample_size_variant=0
            )
        
        # ✅ CORRETTO: Crea Result finali baseline
        # Solo value_control, value_variant sarà auto-popolato dal save()
        Result.objects.create(
            indicator=ind3_1,
            measured_at=date.today() - timedelta(days=53),
            value_control=Decimal('70.1'),  # ← Valore misurato
            # value_variant verrà copiato automaticamente dal save()
            notes="Baseline prima settimana: 70.1% completano tutorial"
        )
        
        Result.objects.create(
            indicator=ind3_2,
            measured_at=date.today() - timedelta(days=53),
            value_control=Decimal('48.4'),
            # value_variant auto-popolato
            notes="Baseline DAU: 48.4% utenti attivi giornalmente"
        )
        
        Result.objects.create(
            indicator=ind3_3,
            measured_at=date.today() - timedelta(days=53),
            value_control=Decimal('7.5'),
            # value_variant auto-popolato
            notes="Baseline sessione media: 7.5 minuti"
        )
        
        self.stdout.write(f'  ✅ {MockBigQueryData.objects.filter(experiment=exp3).count()} mock rows BigQuery')
        self.stdout.write(f'  ✅ {Result.objects.filter(indicator__experiment=exp3).count()} Result rows')
        
        # =======================
        # SUMMARY
        # =======================
        total_projects = Project.objects.count()
        total_experiments = Experiment.objects.count()
        total_indicators = Indicator.objects.count()
        total_mock_rows = MockBigQueryData.objects.count()
        total_results = Result.objects.count()
        
        # Count by test_type
        ab_indicators = Indicator.objects.filter(test_type='ab_test').count()
        prepost_indicators = Indicator.objects.filter(test_type='pre_post').count()
        single_indicators = Indicator.objects.filter(test_type='single').count()
        
        self.stdout.write(self.style.SUCCESS(f'\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('SEEDING COMPLETATO!'))
        self.stdout.write(self.style.SUCCESS('='*60))
        
        self.stdout.write(f'\n📊 Statistiche:')
        self.stdout.write(f'   • Progetti: {total_projects}')
        self.stdout.write(f'   • Esperimenti: {total_experiments}')
        self.stdout.write(f'   • Indicatori: {total_indicators}')
        self.stdout.write(f'     - A/B Test: {ab_indicators}')
        self.stdout.write(f'     - Pre/Post Test: {prepost_indicators}')
        self.stdout.write(f'     - Single Baseline: {single_indicators}')
        self.stdout.write(f'   • Mock BigQuery Rows: {total_mock_rows}')
        self.stdout.write(f'   • Result Rows: {total_results}')
        
        self.stdout.write(self.style.SUCCESS(f'\n🚀 Ora testa la web app su http://localhost:8000/\n'))
        self.stdout.write(self.style.WARNING('⚠️  Ricorda di fare le migrations prima di eseguire questo comando:'))
        self.stdout.write('   python manage.py makemigrations')
        self.stdout.write('   python manage.py migrate')