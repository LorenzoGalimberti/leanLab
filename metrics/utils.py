# metrics/utils.py

from datetime import date, timedelta
import random
from decimal import Decimal
from .models import Result, MockBigQueryData

# ============================================
# ✅ CONFIGURAZIONE METRICHE MOCK COMPLETA
# ============================================

METRIC_CONFIGS = {
    # === ESPERIMENTO 1: A/B TEST ===
    'completion_rate': {
        'control_base': 65.0,
        'variant_base': 72.0,
        'variance': 0.08,
    },
    'retention_d7': {
        'control_base': 28.5,
        'variant_base': 33.2,
        'variance': 0.12,
    },
    'crash_rate': {
        'control_base': 2.3,
        'variant_base': 2.1,
        'variance': 0.20,
    },
    
    # === ESPERIMENTO 2: PRE/POST TEST ===
    'signup_conversion': {
        'control_base': 8.2,   # BEFORE
        'variant_base': 14.7,  # AFTER
        'variance': 0.10,
    },
    'signup_time': {
        'control_base': 124.5,  # BEFORE (secondi)
        'variant_base': 68.2,   # AFTER (secondi)
        'variance': 0.15,
    },
    'signup_abandonment': {
        'control_base': 42.3,  # BEFORE
        'variant_base': 28.7,  # AFTER
        'variance': 0.12,
    },
    
    # === ESPERIMENTO 3: SINGLE BASELINE ===
    'tutorial_completion_baseline': {
        'baseline': 68.5,
        'variance': 0.05,
    },
    'dau_baseline': {
        'baseline': 45.2,
        'variance': 0.08,
    },
    'session_duration_baseline': {
        'baseline': 6.8,  # minuti
        'variance': 0.10,
    },
    
    # === ALTRE METRICHE COMUNI ===
    'actions_per_session': {
        'control_base': 12.3,
        'variant_base': 13.1,
        'variance': 0.15,
    },
}

# ============================================
# ✅ FUNZIONI DI GENERAZIONE DATI MOCK ADATTIVE
# ============================================

def generate_mock_data(metric_key, test_type, start_date, end_date):
    """
    Genera dati mock realistici ADATTIVI al tipo di test
    
    Args:
        metric_key: chiave metrica (es. 'completion_rate')
        test_type: 'ab_test', 'pre_post', o 'single'
        start_date: data inizio
        end_date: data fine
        
    Returns:
        list: [{'date': date, 'control': float, 'variant': float|None}, ...]
    """
    if metric_key not in METRIC_CONFIGS:
        return []
    
    config = METRIC_CONFIGS[metric_key]
    variance = config['variance']
    
    data = []
    current_date = start_date
    days_total = (end_date - start_date).days + 1
    
    # ========================================
    # ✅ CASO 1: SINGLE BASELINE
    # ========================================
    if test_type == 'single':
        baseline_value = config.get('baseline', 50.0)
        
        while current_date <= end_date:
            # Variazione casuale giornaliera
            noise = random.uniform(-variance, variance)
            value = baseline_value * (1 + noise)
            
            data.append({
                'date': current_date,
                'control': round(value, 2),
                'variant': None  # ✅ NULL per baseline
            })
            
            current_date += timedelta(days=1)
    
    # ========================================
    # ✅ CASO 2: PRE/POST TEST
    # ========================================
    elif test_type == 'pre_post':
        control_base = config['control_base']  # BEFORE
        variant_base = config['variant_base']  # AFTER
        
        # Dividi periodo in due metà: BEFORE e AFTER
        mid_point = start_date + timedelta(days=days_total // 2)
        
        while current_date <= end_date:
            if current_date < mid_point:
                # PERIODO BEFORE: solo control
                noise = random.uniform(-variance, variance)
                control_value = control_base * (1 + noise)
                
                data.append({
                    'date': current_date,
                    'control': round(control_value, 2),
                    'variant': None  # ✅ Non ancora rilasciato
                })
            else:
                # PERIODO AFTER: solo variant
                day_after = (current_date - mid_point).days
                noise = random.uniform(-variance, variance)
                variant_value = variant_base * (1 + noise)
                
                data.append({
                    'date': current_date,
                    'control': None,  # ✅ Before finito
                    'variant': round(variant_value, 2)
                })
            
            current_date += timedelta(days=1)
    
    # ========================================
    # ✅ CASO 3: A/B TEST (default)
    # ========================================
    else:  # 'ab_test'
        control_base = config['control_base']
        variant_base = config['variant_base']
        
        while current_date <= end_date:
            # Trend progressivo: variant migliora nel tempo
            day_index = (current_date - start_date).days
            trend_factor = 1 + (day_index / days_total * 0.05)  # +5% alla fine
            
            # Variazione casuale giornaliera
            control_noise = random.uniform(-variance, variance)
            variant_noise = random.uniform(-variance, variance)
            
            # Calcola valori finali
            control_value = control_base * (1 + control_noise)
            variant_value = variant_base * (1 + variant_noise) * trend_factor
            
            data.append({
                'date': current_date,
                'control': round(control_value, 2),
                'variant': round(variant_value, 2)
            })
            
            current_date += timedelta(days=1)
    
    return data


# ============================================
# ✅ AGGIORNAMENTO INDICATORI DA BIGQUERY MOCK
# ============================================

def update_indicator_from_bigquery(indicator, import_all=True):
    """
    Genera dati mock e crea/aggiorna Result.
    ✅ ADATTIVO: gestisce A/B, Pre/Post, Single Baseline.
    
    Args:
        indicator: Oggetto Indicator
        import_all: Se True, importa tutti i dati storici. Se False, solo l'ultimo.
    
    Returns:
        Lista di Result objects creati/aggiornati
    """
    metric_key = indicator.bigquery_metric_key
    
    if not metric_key:
        return []
    
    # Determina date di inizio/fine
    experiment = indicator.experiment
    
    if experiment.start_date and experiment.end_date:
        start_date = experiment.start_date
        end_date = experiment.end_date
    else:
        # Default: ultimi 30 giorni
        end_date = date.today()
        start_date = end_date - timedelta(days=30)
    
    # ✅ NUOVO: Passa test_type a generate_mock_data
    test_type = indicator.test_type
    mock_data_list = generate_mock_data(metric_key, test_type, start_date, end_date)
    
    if not mock_data_list:
        return []
    
    # Se import_all=False, prendi solo l'ultimo
    if not import_all:
        mock_data_list = [mock_data_list[-1]]
    
    created_results = []
    
    for mock_data in mock_data_list:
        # Controlla se esiste già un risultato per questa data
        existing_result = Result.objects.filter(
            indicator=indicator,
            measured_at=mock_data['date']
        ).first()
        
        # ========================================
        # ✅ GESTIONE SPECIALE PER SINGLE BASELINE
        # ========================================
        if test_type == 'single':
            value_control = Decimal(str(mock_data['control']))
            
            if existing_result:
                existing_result.value_control = value_control
                existing_result.value_variant = value_control  # ✅ Copia automatica
                existing_result.notes = f"Baseline aggiornata da BigQuery Mock"
                existing_result.save()
                created_results.append(existing_result)
            else:
                result = Result.objects.create(
                    indicator=indicator,
                    measured_at=mock_data['date'],
                    value_control=value_control,
                    # value_variant verrà copiato automaticamente dal save()
                    notes=f"Baseline importata da BigQuery Mock"
                )
                created_results.append(result)
        
        # ========================================
        # ✅ GESTIONE PRE/POST TEST
        # ========================================
        elif test_type == 'pre_post':
            # Pre/Post ha o control o variant, mai entrambi nello stesso giorno
            
            # Se siamo nel periodo BEFORE (solo control)
            if mock_data['control'] is not None and mock_data['variant'] is None:
                # Salta: vogliamo creare un Result solo alla fine con media
                continue
            
            # Se siamo nel periodo AFTER (solo variant)
            elif mock_data['variant'] is not None and mock_data['control'] is None:
                # Alla fine del periodo AFTER, crea UN solo Result con medie
                # Saltiamo i giorni intermedi, creiamo solo alla fine
                if mock_data == mock_data_list[-1]:  # Ultimo giorno
                    # Calcola media BEFORE
                    before_data = [d for d in mock_data_list if d['control'] is not None]
                    after_data = [d for d in mock_data_list if d['variant'] is not None]
                    
                    avg_before = sum(d['control'] for d in before_data) / len(before_data)
                    avg_after = sum(d['variant'] for d in after_data) / len(after_data)
                    
                    if existing_result:
                        existing_result.value_control = Decimal(str(avg_before))
                        existing_result.value_variant = Decimal(str(avg_after))
                        existing_result.notes = f"Pre/Post Test: BEFORE (media {len(before_data)}gg) vs AFTER (media {len(after_data)}gg)"
                        existing_result.save()
                        created_results.append(existing_result)
                    else:
                        result = Result.objects.create(
                            indicator=indicator,
                            measured_at=mock_data['date'],
                            value_control=Decimal(str(avg_before)),
                            value_variant=Decimal(str(avg_after)),
                            notes=f"Pre/Post Test: BEFORE (media {len(before_data)}gg) vs AFTER (media {len(after_data)}gg)"
                        )
                        created_results.append(result)
        
        # ========================================
        # ✅ GESTIONE A/B TEST (standard)
        # ========================================
        else:  # 'ab_test'
            value_control = Decimal(str(mock_data['control']))
            value_variant = Decimal(str(mock_data['variant']))
            
            if existing_result:
                existing_result.value_control = value_control
                existing_result.value_variant = value_variant
                existing_result.notes = f"A/B Test aggiornato da BigQuery Mock"
                existing_result.save()
                created_results.append(existing_result)
            else:
                result = Result.objects.create(
                    indicator=indicator,
                    measured_at=mock_data['date'],
                    value_control=value_control,
                    value_variant=value_variant,
                    notes=f"A/B Test importato da BigQuery Mock"
                )
                created_results.append(result)
    
    return created_results


def update_experiment_from_bigquery(experiment, import_all=True):
    """
    Aggiorna TUTTI gli indicatori di un esperimento.
    ✅ ADATTIVO: gestisce tutti i test_type.
    
    Args:
        experiment: Oggetto Experiment
        import_all: Se True, importa tutti i dati storici
    
    Returns:
        dict con statistiche dell'operazione
    """
    results = {
        'total_indicators': 0,
        'updated': 0,
        'skipped': 0,
        'total_results_created': 0,
        'errors': []
    }
    
    for indicator in experiment.indicators.all():
        results['total_indicators'] += 1
        
        # Salta indicatori senza metric_key
        if not indicator.bigquery_metric_key:
            results['skipped'] += 1
            results['errors'].append(f"{indicator.name}: nessuna metric_key configurata")
            continue
        
        try:
            created_results = update_indicator_from_bigquery(indicator, import_all=import_all)
            
            if created_results:
                results['updated'] += 1
                results['total_results_created'] += len(created_results)
            else:
                results['skipped'] += 1
                results['errors'].append(f"{indicator.name}: nessun dato generato (verifica METRIC_CONFIGS)")
        
        except Exception as e:
            results['skipped'] += 1
            results['errors'].append(f"{indicator.name}: errore - {str(e)}")
    
    return results


# ============================================
# ✅ FUNZIONE HELPER: Importa da MockBigQueryData
# ============================================

def import_from_mock_bigquery_data(indicator):
    """
    Importa dati REALI da MockBigQueryData (se esistono).
    Questa funzione SOSTITUISCE la generazione casuale se ci sono dati nel DB.
    
    Args:
        indicator: Oggetto Indicator
    
    Returns:
        Lista di Result objects creati
    """
    metric_key = indicator.bigquery_metric_key
    experiment = indicator.experiment
    
    if not metric_key:
        return []
    
    # Query MockBigQueryData
    mock_data_records = MockBigQueryData.objects.filter(
        experiment=experiment,
        metric_key=metric_key
    ).order_by('date')
    
    if not mock_data_records.exists():
        return []
    
    created_results = []
    
    for mock_record in mock_data_records:
        # Controlla se esiste già un Result per questa data
        existing_result = Result.objects.filter(
            indicator=indicator,
            measured_at=mock_record.date
        ).first()
        
        # ✅ Gestione per SINGLE BASELINE
        if indicator.test_type == 'single':
            if existing_result:
                existing_result.value_control = mock_record.value_control
                existing_result.value_variant = mock_record.value_control  # Copia
                existing_result.notes = f"Baseline da MockBigQueryData"
                existing_result.save()
                created_results.append(existing_result)
            else:
                result = Result.objects.create(
                    indicator=indicator,
                    measured_at=mock_record.date,
                    value_control=mock_record.value_control,
                    notes=f"Baseline da MockBigQueryData"
                )
                created_results.append(result)
        
        # ✅ Gestione per A/B TEST e PRE/POST
        else:
            value_control = mock_record.value_control or Decimal('0')
            value_variant = mock_record.value_variant or Decimal('0')
            
            if existing_result:
                existing_result.value_control = value_control
                existing_result.value_variant = value_variant
                existing_result.notes = f"Da MockBigQueryData"
                existing_result.save()
                created_results.append(existing_result)
            else:
                result = Result.objects.create(
                    indicator=indicator,
                    measured_at=mock_record.date,
                    value_control=value_control,
                    value_variant=value_variant,
                    notes=f"Da MockBigQueryData"
                )
                created_results.append(result)
    
    return created_results
