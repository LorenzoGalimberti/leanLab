# metrics/utils.py

from datetime import date
from .models import MockBigQueryData, Result

def fetch_from_bigquery_mock(indicator):
    """
    Simula una query BigQuery leggendo da MockBigQueryData.
    In produzione: eseguirebbe query SQL su BigQuery reale.
    In test: legge dalla tabella mock.
    
    Args:
        indicator: Oggetto Indicator
    
    Returns:
        dict con 'value_control', 'value_variant', 'date', 'sample_size_control', 'sample_size_variant'
        oppure None se non trova dati
    """
    experiment = indicator.experiment
    metric_key = indicator.bigquery_metric_key
    
    # Se l'indicatore non ha metric_key configurata, non possiamo fare nulla
    if not metric_key:
        return None
    
    # Cerca l'ultimo dato disponibile per questo esperimento e metrica
    mock_data = MockBigQueryData.objects.filter(
        experiment=experiment,
        metric_key=metric_key
    ).order_by('-date').first()
    
    if not mock_data:
        return None
    
    return {
        'value_control': mock_data.value_control,
        'value_variant': mock_data.value_variant,
        'date': mock_data.date,
        'sample_size_control': mock_data.sample_size_control,
        'sample_size_variant': mock_data.sample_size_variant,
    }


def update_indicator_from_bigquery(indicator):
    """
    Recupera dati da BigQuery mock e crea/aggiorna un Result.
    
    Args:
        indicator: Oggetto Indicator
    
    Returns:
        Result object se successo, None altrimenti
    """
    # Fetch dati da mock
    data = fetch_from_bigquery_mock(indicator)
    
    if not data:
        return None
    
    # Controlla se esiste già un risultato per questa data
    existing_result = Result.objects.filter(
        indicator=indicator,
        measured_at=data['date']
    ).first()
    
    if existing_result:
        # Aggiorna esistente
        existing_result.value_control = data['value_control']
        existing_result.value_variant = data['value_variant']
        existing_result.notes = f"Aggiornato da BigQuery (sample: {data['sample_size_control']} vs {data['sample_size_variant']})"
        existing_result.save()  # save() ricalcola automaticamente delta e decisione
        return existing_result
    else:
        # Crea nuovo
        result = Result.objects.create(
            indicator=indicator,
            measured_at=data['date'],
            value_control=data['value_control'],
            value_variant=data['value_variant'],
            notes=f"Importato da BigQuery (sample: {data['sample_size_control']} vs {data['sample_size_variant']})"
        )
        return result


def update_experiment_from_bigquery(experiment):
    """
    Aggiorna TUTTI gli indicatori di un esperimento da BigQuery mock.
    
    Args:
        experiment: Oggetto Experiment
    
    Returns:
        dict con statistiche dell'operazione:
        {
            'total_indicators': int,
            'updated': int,
            'skipped': int,
            'errors': list
        }
    """
    results = {
        'total_indicators': 0,
        'updated': 0,
        'skipped': 0,
        'errors': []
    }
    
    for indicator in experiment.indicators.all():
        results['total_indicators'] += 1
        
        # Salta indicatori senza metric_key configurata
        if not indicator.bigquery_metric_key:
            results['skipped'] += 1
            results['errors'].append(f"{indicator.name}: nessuna metric_key configurata")
            continue
        
        try:
            result = update_indicator_from_bigquery(indicator)
            if result:
                results['updated'] += 1
            else:
                results['skipped'] += 1
                results['errors'].append(f"{indicator.name}: nessun dato mock disponibile in MockBigQueryData")
        except Exception as e:
            results['skipped'] += 1
            results['errors'].append(f"{indicator.name}: errore - {str(e)}")
    
    return results
