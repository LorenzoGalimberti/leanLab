# metrics/utils.py

from datetime import date, timedelta
import random
from decimal import Decimal
from .models import Result

# ============================================
# CONFIGURAZIONE METRICHE MOCK
# ============================================

METRIC_CONFIGS = {
    'actions_per_session': {
        'control_base': 12.3,
        'variant_base': 13.1,
        'variance': 0.15,  # ±15% variabilità
    },
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
    }
}

# ============================================
# FUNZIONI DI GENERAZIONE DATI MOCK
# ============================================

def generate_mock_data(metric_key, start_date, end_date):
    """
    Genera dati mock realistici con variabilità
    
    Args:
        metric_key: chiave metrica (es. 'actions_per_session')
        start_date: data inizio
        end_date: data fine
        
    Returns:
        list: [{'date': date, 'control': float, 'variant': float}, ...]
    """
    if metric_key not in METRIC_CONFIGS:
        return []
    
    config = METRIC_CONFIGS[metric_key]
    control_base = config['control_base']
    variant_base = config['variant_base']
    variance = config['variance']
    
    data = []
    current_date = start_date
    days_total = (end_date - start_date).days + 1
    
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
# AGGIORNAMENTO INDICATORI DA BIGQUERY MOCK
# ============================================

def update_indicator_from_bigquery(indicator, import_all=True):
    """
    Genera dati mock e crea/aggiorna Result
    
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
    
    # Genera dati mock
    mock_data_list = generate_mock_data(metric_key, start_date, end_date)
    
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
        
        if existing_result:
            # Aggiorna esistente (opzionale: potresti decidere di non aggiornare)
            existing_result.value_control = Decimal(str(mock_data['control']))
            existing_result.value_variant = Decimal(str(mock_data['variant']))
            existing_result.notes = f"Aggiornato da BigQuery Mock"
            existing_result.save()
            created_results.append(existing_result)
        else:
            # Crea nuovo
            result = Result.objects.create(
                indicator=indicator,
                measured_at=mock_data['date'],
                value_control=Decimal(str(mock_data['control'])),
                value_variant=Decimal(str(mock_data['variant'])),
                notes=f"Importato da BigQuery Mock"
            )
            created_results.append(result)
    
    return created_results


def update_experiment_from_bigquery(experiment, import_all=True):
    """
    Aggiorna TUTTI gli indicatori di un esperimento
    
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
                results['errors'].append(f"{indicator.name}: nessun dato generato")
        
        except Exception as e:
            results['skipped'] += 1
            results['errors'].append(f"{indicator.name}: errore - {str(e)}")
    
    return results
