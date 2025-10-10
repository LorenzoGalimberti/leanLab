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
            test_type='ab_test',
            target_uplift=Decimal('15.00'),
            bigquery_metric_key='completion_rate'
        )
        
        ind1_2 = Indicator.objects.create(
            experiment=exp1,
            name="Retention Day 7",
            description="Percentuale utenti che tornano dopo 7 giorni dalla registrazione",
            indicator_type='percentage',
            role='primary',
            test_type='ab_test',
            target_uplift=Decimal('10.00'),
            bigquery_metric_key='retention_d7'
        )
        
        ind1_3 = Indicator.objects.create(
            experiment=exp1,
            name="Crash Rate",
            description="Percentuale sessioni con crash (guardrail: deve restare < 2%)",
            indicator_type='percentage',
            role='guardrail',
            test_type='ab_test',
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
            test_type='pre_post',
            target_uplift=Decimal('30.00'),
            bigquery_metric_key='signup_conversion'
        )
        
        ind2_2 = Indicator.objects.create(
            experiment=exp2,
            name="Time to Complete Signup",
            description="Tempo medio per completare signup (secondi)",
            indicator_type='average',
            role='secondary',
            test_type='pre_post',
            target_uplift=Decimal('20.00'),
            bigquery_metric_key='signup_time'
        )
        
        ind2_3 = Indicator.objects.create(
            experiment=exp2,
            name="Signup Abandonment Rate",
            description="Percentuale utenti che abbandonano il form (guardrail)",
            indicator_type='percentage',
            role='guardrail',
            test_type='pre_post',
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
                value_control=Decimal('8.2') + Decimal(day_offset * 0.05),
                value_variant=Decimal('0.0'),
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
                value_control=Decimal('0.0'),
                value_variant=after_val,
                sample_size_variant=350 + (day_offset-7) * 20
            )
        
        # Crea 1 Result finale Pre/Post
        Result.objects.create(
            indicator=ind2_1,
            measured_at=date.today() - timedelta(days=7),
            value_control=Decimal('8.45'),
            value_variant=Decimal('15.80'),
            notes="Pre/Post Test: Before (7gg) vs After (7gg) - PERSEVERE: +87% conversion"
        )
        
        # Time to signup
        Result.objects.create(
            indicator=ind2_2,
            measured_at=date.today() - timedelta(days=7),
            value_control=Decimal('124.5'),
            value_variant=Decimal('68.2'),
            notes="Tempo signup drasticamente ridotto con social login"
        )
        
        # Abandonment (guardrail)
        Result.objects.create(
            indicator=ind2_3,
            measured_at=date.today() - timedelta(days=7),
            value_control=Decimal('42.3'),
            value_variant=Decimal('28.7'),
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
            test_type='single',
            target_uplift=Decimal('72.00'),
            bigquery_metric_key='tutorial_completion_baseline'
        )
        
        ind3_2 = Indicator.objects.create(
            experiment=exp3,
            name="DAU Rate (Baseline)",
            description="Baseline: Daily Active Users % nella prima settimana",
            indicator_type='percentage',
            role='primary',
            test_type='single',
            target_uplift=Decimal('50.00'),
            bigquery_metric_key='dau_baseline'
        )
        
        ind3_3 = Indicator.objects.create(
            experiment=exp3,
            name="Avg Session Duration (Baseline)",
            description="Baseline: durata media sessione primi utenti",
            indicator_type='average',
            role='secondary',
            test_type='single',
            target_uplift=Decimal('8.00'),
            bigquery_metric_key='session_duration_baseline'
        )
        
        self.stdout.write(f'  ✅ {exp3.indicators.count()} indicatori SINGLE BASELINE creati')
        
        # Mock BigQuery Data per Baseline (7 giorni)
        for day_offset in range(7):
            day = date.today() - timedelta(days=59-day_offset)
            
            # Tutorial completion baseline
            baseline_completion = Decimal('68.5') + Decimal(day_offset * 0.4)
            MockBigQueryData.objects.create(
                experiment=exp3,
                metric_key='tutorial_completion_baseline',
                date=day,
                value_control=baseline_completion,
                value_variant=None,
                sample_size_control=240 + day_offset * 30,
                sample_size_variant=0
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
        
        # Crea Result finali baseline
        Result.objects.create(
            indicator=ind3_1,
            measured_at=date.today() - timedelta(days=53),
            value_control=Decimal('70.1'),
            notes="Baseline prima settimana: 70.1% completano tutorial (target: 72%)"
        )
        
        Result.objects.create(
            indicator=ind3_2,
            measured_at=date.today() - timedelta(days=53),
            value_control=Decimal('48.4'),
            notes="Baseline DAU: 48.4% utenti attivi giornalmente (target: 50%)"
        )
        
        Result.objects.create(
            indicator=ind3_3,
            measured_at=date.today() - timedelta(days=53),
            value_control=Decimal('7.5'),
            notes="Baseline sessione media: 7.5 minuti (target: 8 min)"
        )
        
        self.stdout.write(f'  ✅ {MockBigQueryData.objects.filter(experiment=exp3).count()} mock rows BigQuery')
        self.stdout.write(f'  ✅ {Result.objects.filter(indicator__experiment=exp3).count()} Result rows')
        
        # =======================
        # 5. ESPERIMENTO 4: A/B TEST - E-commerce Checkout One-Click (14 GIORNI)
        # =======================
        exp4 = Experiment.objects.create(
            project=project,
            title="Checkout One-Click vs Multi-Step (A/B Test)",
            hypothesis="Se riduciamo gli step del checkout da 3 a 1, "
                       "la conversion rate aumenterà del 25% senza impattare l'Average Order Value",
            status='completed',
            decision='persevere',
            start_date=date.today() - timedelta(days=28),
            end_date=date.today() - timedelta(days=14),
            notes="Test A/B su checkout e-commerce. Control: 3 step (cart→shipping→payment) | "
                  "Variant: 1 step (tutto in una pagina)"
        )
        self.stdout.write(f'\n📊 Esperimento 4 (A/B TEST - E-commerce): {exp4.title}')
        
        # Indicatori Esperimento 4
        ind4_1 = Indicator.objects.create(
            experiment=exp4,
            name="Checkout Conversion Rate",
            description="% utenti che completano l'acquisto dopo aver aggiunto al carrello",
            indicator_type='percentage',
            role='primary',
            test_type='ab_test',
            target_uplift=Decimal('25.00'),
            bigquery_metric_key='checkout_conversion'
        )
        
        ind4_2 = Indicator.objects.create(
            experiment=exp4,
            name="Average Order Value (AOV)",
            description="Valore medio ordine in € - deve rimanere stabile",
            indicator_type='revenue',
            role='primary',
            test_type='ab_test',
            target_uplift=Decimal('0.00'),
            bigquery_metric_key='aov'
        )
        
        ind4_3 = Indicator.objects.create(
            experiment=exp4,
            name="Cart Abandonment Rate",
            description="% carrelli abbandonati (guardrail: non deve peggiorare)",
            indicator_type='percentage',
            role='guardrail',
            test_type='ab_test',
            target_uplift=Decimal('0.00'),
            bigquery_metric_key='cart_abandonment'
        )
        
        ind4_4 = Indicator.objects.create(
            experiment=exp4,
            name="Time to Complete Checkout",
            description="Tempo medio per completare checkout (secondi)",
            indicator_type='average',
            role='secondary',
            test_type='ab_test',
            target_uplift=Decimal('-40.00'),
            bigquery_metric_key='checkout_time'
        )
        
        self.stdout.write(f'  ✅ {exp4.indicators.count()} indicatori E-commerce creati')
        
        # Mock BigQuery Data per Esperimento 4 (14 giorni)
        for day_offset in range(14):
            day = date.today() - timedelta(days=27-day_offset)
            
            # Checkout Conversion: miglioramento significativo
            conv_control = Decimal('12.3') + Decimal(day_offset * 0.15)
            conv_variant = Decimal('16.8') + Decimal(day_offset * 0.25)
            
            MockBigQueryData.objects.create(
                experiment=exp4,
                metric_key='checkout_conversion',
                date=day,
                value_control=conv_control,
                value_variant=conv_variant,
                sample_size_control=300 + day_offset * 25,
                sample_size_variant=300 + day_offset * 25
            )
            
            if day_offset % 4 == 0:
                Result.objects.create(
                    indicator=ind4_1,
                    measured_at=day,
                    value_control=conv_control,
                    value_variant=conv_variant,
                    notes=f"Checkout conversion giorno {day_offset+1}"
                )
            
            # AOV: stabile (leggero calo accettabile)
            aov_control = Decimal('87.50') + Decimal((day_offset % 4) * 0.8)
            aov_variant = Decimal('85.20') + Decimal((day_offset % 4) * 0.9)
            
            MockBigQueryData.objects.create(
                experiment=exp4,
                metric_key='aov',
                date=day,
                value_control=aov_control,
                value_variant=aov_variant,
                sample_size_control=300 + day_offset * 25,
                sample_size_variant=300 + day_offset * 25
            )
            
            if day_offset % 5 == 0:
                Result.objects.create(
                    indicator=ind4_2,
                    measured_at=day,
                    value_control=aov_control,
                    value_variant=aov_variant,
                    notes="AOV stabile"
                )
            
            # Cart Abandonment: miglioramento (guardrail OK)
            aband_control = Decimal('68.5') - Decimal(day_offset * 0.2)
            aband_variant = Decimal('63.2') - Decimal(day_offset * 0.3)
            
            MockBigQueryData.objects.create(
                experiment=exp4,
                metric_key='cart_abandonment',
                date=day,
                value_control=aband_control,
                value_variant=aband_variant,
                sample_size_control=450 + day_offset * 20,
                sample_size_variant=450 + day_offset * 20
            )
            
            if day_offset % 6 == 0:
                Result.objects.create(
                    indicator=ind4_3,
                    measured_at=day,
                    value_control=aband_control,
                    value_variant=aband_variant,
                    notes="Guardrail cart abandonment"
                )
            
            # Checkout Time: riduzione drastica
            time_control = Decimal('145.0') - Decimal(day_offset * 0.5)
            time_variant = Decimal('62.0') + Decimal(day_offset * 0.3)
            
            MockBigQueryData.objects.create(
                experiment=exp4,
                metric_key='checkout_time',
                date=day,
                value_control=time_control,
                value_variant=time_variant,
                sample_size_control=300 + day_offset * 25,
                sample_size_variant=300 + day_offset * 25
            )
            
            if day_offset % 5 == 0:
                Result.objects.create(
                    indicator=ind4_4,
                    measured_at=day,
                    value_control=time_control,
                    value_variant=time_variant,
                    notes="Tempo checkout drasticamente ridotto"
                )
        
        self.stdout.write(f'  ✅ {MockBigQueryData.objects.filter(experiment=exp4).count()} mock rows BigQuery')
        self.stdout.write(f'  ✅ {Result.objects.filter(indicator__experiment=exp4).count()} Result rows')
        
        # =======================
        # 6. ESPERIMENTO 5: A/B TEST - Badge/Rewards System (21 GIORNI)
        # =======================
        exp5 = Experiment.objects.create(
            project=project,
            title="Sistema Badge e Rewards (A/B Test)",
            hypothesis="Se aggiungiamo un sistema di badge e rewards per workout completati, "
                       "la retention D7 aumenterà del 20% e le sessioni settimanali del 25%",
            status='running',
            start_date=date.today() - timedelta(days=21),
            notes="Test A/B gamification. Control: app standard | "
                  "Variant: badge (Bronze/Silver/Gold), rewards ogni 5 workout, leaderboard"
        )
        self.stdout.write(f'\n📊 Esperimento 5 (A/B TEST - Gamification): {exp5.title}')
        
        # Indicatori Esperimento 5
        ind5_1 = Indicator.objects.create(
            experiment=exp5,
            name="Day 7 Retention",
            description="% utenti che tornano dopo 7 giorni",
            indicator_type='percentage',
            role='primary',
            test_type='ab_test',
            target_uplift=Decimal('20.00'),
            bigquery_metric_key='retention_d7_gamif'
        )
        
        ind5_2 = Indicator.objects.create(
            experiment=exp5,
            name="Weekly Active Sessions",
            description="Numero medio sessioni per utente alla settimana",
            indicator_type='average',
            role='primary',
            test_type='ab_test',
            target_uplift=Decimal('25.00'),
            bigquery_metric_key='weekly_sessions'
        )
        
        ind5_3 = Indicator.objects.create(
            experiment=exp5,
            name="App Crash Rate",
            description="% sessioni con crash (guardrail: badge system non deve impattare stabilità)",
            indicator_type='percentage',
            role='guardrail',
            test_type='ab_test',
            target_uplift=Decimal('0.00'),
            bigquery_metric_key='crash_rate_gamif'
        )
        
        ind5_4 = Indicator.objects.create(
            experiment=exp5,
            name="Workout Completion Rate",
            description="% workout completati vs iniziati",
            indicator_type='percentage',
            role='secondary',
            test_type='ab_test',
            target_uplift=Decimal('15.00'),
            bigquery_metric_key='workout_completion'
        )
        
        self.stdout.write(f'  ✅ {exp5.indicators.count()} indicatori Gamification creati')
        
        # Mock BigQuery Data per Esperimento 5 (21 giorni)
        for day_offset in range(21):
            day = date.today() - timedelta(days=20-day_offset)
            
            # Retention D7: dati disponibili dopo 7 giorni
            if day_offset >= 7:
                ret_control = Decimal('38.5') + Decimal((day_offset-7) * 0.2)
                ret_variant = Decimal('48.2') + Decimal((day_offset-7) * 0.3)
                
                MockBigQueryData.objects.create(
                    experiment=exp5,
                    metric_key='retention_d7_gamif',
                    date=day,
                    value_control=ret_control,
                    value_variant=ret_variant,
                    sample_size_control=400 + (day_offset-7) * 20,
                    sample_size_variant=400 + (day_offset-7) * 20
                )
                
                if day_offset % 7 == 0:
                    Result.objects.create(
                        indicator=ind5_1,
                        measured_at=day,
                        value_control=ret_control,
                        value_variant=ret_variant,
                        notes=f"Retention D7 settimana {(day_offset-7)//7 + 1}"
                    )
            
            # Weekly Sessions: miglioramento costante
            sessions_control = Decimal('3.2') + Decimal(day_offset * 0.05)
            sessions_variant = Decimal('4.5') + Decimal(day_offset * 0.08)
            
            MockBigQueryData.objects.create(
                experiment=exp5,
                metric_key='weekly_sessions',
                date=day,
                value_control=sessions_control,
                value_variant=sessions_variant,
                sample_size_control=500 + day_offset * 30,
                sample_size_variant=500 + day_offset * 30
            )
            
            if day_offset % 5 == 0:
                Result.objects.create(
                    indicator=ind5_2,
                    measured_at=day,
                    value_control=sessions_control,
                    value_variant=sessions_variant,
                    notes="Weekly sessions in crescita"
                )
            
            # Crash Rate: stabile (guardrail OK)
            crash_control = Decimal('0.8') + Decimal((day_offset % 4) * 0.05)
            crash_variant = Decimal('0.9') + Decimal((day_offset % 4) * 0.06)
            
            MockBigQueryData.objects.create(
                experiment=exp5,
                metric_key='crash_rate_gamif',
                date=day,
                value_control=crash_control,
                value_variant=crash_variant,
                sample_size_control=800 + day_offset * 20,
                sample_size_variant=800 + day_offset * 20
            )
            
            if day_offset % 6 == 0:
                Result.objects.create(
                    indicator=ind5_3,
                    measured_at=day,
                    value_control=crash_control,
                    value_variant=crash_variant,
                    notes="Guardrail crash rate OK"
                )
            
            # Workout Completion: miglioramento con badge
            compl_control = Decimal('72.5') + Decimal(day_offset * 0.15)
            compl_variant = Decimal('85.0') + Decimal(day_offset * 0.2)
            
            MockBigQueryData.objects.create(
                experiment=exp5,
                metric_key='workout_completion',
                date=day,
                value_control=compl_control,
                value_variant=compl_variant,
                sample_size_control=600 + day_offset * 25,
                sample_size_variant=600 + day_offset * 25
            )
            
            if day_offset % 4 == 0:
                Result.objects.create(
                    indicator=ind5_4,
                    measured_at=day,
                    value_control=compl_control,
                    value_variant=compl_variant,
                    notes="Completion rate workout migliorato"
                )
        
        self.stdout.write(f'  ✅ {MockBigQueryData.objects.filter(experiment=exp5).count()} mock rows BigQuery')
        self.stdout.write(f'  ✅ {Result.objects.filter(indicator__experiment=exp5).count()} Result rows')
        
        # =======================
        # SUMMARY FINALE
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
        
        # Count by role
        primary_indicators = Indicator.objects.filter(role='primary').count()
        guardrail_indicators = Indicator.objects.filter(role='guardrail').count()
        secondary_indicators = Indicator.objects.filter(role='secondary').count()
        
        # Experiments by status
        running_exp = Experiment.objects.filter(status='running').count()
        completed_exp = Experiment.objects.filter(status='completed').count()
        
        # Experiments by decision
        persevere_exp = Experiment.objects.filter(decision='persevere').count()
        pivot_exp = Experiment.objects.filter(decision='pivot').count()
        pending_exp = Experiment.objects.filter(decision='pending').count()
        
        self.stdout.write(self.style.SUCCESS(f'\n' + '='*70))
        self.stdout.write(self.style.SUCCESS('🎉 SEEDING COMPLETATO CON SUCCESSO!'))
        self.stdout.write(self.style.SUCCESS('='*70))
        
        self.stdout.write(self.style.SUCCESS(f'\n📊 STATISTICHE DATABASE:'))
        self.stdout.write(f'\n┌─────────────────────────────────────────────────────────┐')
        self.stdout.write(f'│  PROGETTI                                               │')
        self.stdout.write(f'├─────────────────────────────────────────────────────────┤')
        self.stdout.write(f'│  • Totale progetti: {total_projects:>2}                                    │')
        self.stdout.write(f'└─────────────────────────────────────────────────────────┘')
        
        self.stdout.write(f'\n┌─────────────────────────────────────────────────────────┐')
        self.stdout.write(f'│  ESPERIMENTI                                            │')
        self.stdout.write(f'├─────────────────────────────────────────────────────────┤')
        self.stdout.write(f'│  • Totale esperimenti: {total_experiments:>2}                              │')
        self.stdout.write(f'│  • Running: {running_exp:>2}                                          │')
        self.stdout.write(f'│  • Completed: {completed_exp:>2}                                        │')
        self.stdout.write(f'│                                                         │')
        self.stdout.write(f'│  Decisioni:                                             │')
        self.stdout.write(f'│  • Persevere: {persevere_exp:>2}  ✅                                     │')
        self.stdout.write(f'│  • Pivot: {pivot_exp:>2}      ⚠️                                      │')
        self.stdout.write(f'│  • Pending: {pending_exp:>2}    ⏳                                     │')
        self.stdout.write(f'└─────────────────────────────────────────────────────────┘')
        
        self.stdout.write(f'\n┌─────────────────────────────────────────────────────────┐')
        self.stdout.write(f'│  INDICATORI                                             │')
        self.stdout.write(f'├─────────────────────────────────────────────────────────┤')
        self.stdout.write(f'│  • Totale indicatori: {total_indicators:>2}                               │')
        self.stdout.write(f'│                                                         │')
        self.stdout.write(f'│  Per tipo di test:                                      │')
        self.stdout.write(f'│  • A/B Test: {ab_indicators:>2}                                        │')
        self.stdout.write(f'│  • Pre/Post Test: {prepost_indicators:>2}                                  │')
        self.stdout.write(f'│  • Single Baseline: {single_indicators:>2}                                │')
        self.stdout.write(f'│                                                         │')
        self.stdout.write(f'│  Per ruolo:                                             │')
        self.stdout.write(f'│  • Primari: {primary_indicators:>2}      (obiettivi principali)           │')
        self.stdout.write(f'│  • Guardrail: {guardrail_indicators:>2}    (metriche di sicurezza)          │')
        self.stdout.write(f'│  • Secondari: {secondary_indicators:>2}    (analisi supporto)               │')
        self.stdout.write(f'└─────────────────────────────────────────────────────────┘')
        
        self.stdout.write(f'\n┌─────────────────────────────────────────────────────────┐')
        self.stdout.write(f'│  DATI GENERATI                                          │')
        self.stdout.write(f'├─────────────────────────────────────────────────────────┤')
        self.stdout.write(f'│  • Mock BigQuery Rows: {total_mock_rows:>4}                            │')
        self.stdout.write(f'│  • Result Rows: {total_results:>4}                                    │')
        self.stdout.write(f'└─────────────────────────────────────────────────────────┘')
        
        self.stdout.write(self.style.SUCCESS(f'\n🚀 WEB APP PRONTA!'))
        self.stdout.write(f'\n   Avvia il server con:')
        self.stdout.write(self.style.HTTP_INFO('   python manage.py runserver'))
        self.stdout.write(f'\n   Apri il browser su:')
        self.stdout.write(self.style.HTTP_INFO('   http://localhost:8000/'))
        
        self.stdout.write(self.style.WARNING(f'\n⚠️  NOTA: Se non hai ancora fatto le migrations:'))
        self.stdout.write('   1. python manage.py makemigrations')
        self.stdout.write('   2. python manage.py migrate')
        self.stdout.write('   3. python manage.py seed_mock_data')
        
        self.stdout.write(self.style.SUCCESS(f'\n✨ Buon testing! ✨\n'))