# projects/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Count, Q
from .models import Project, Experiment
from .forms import ProjectForm, ExperimentForm
from metrics.utils import update_experiment_from_bigquery  # ✅ RIGA AGGIUNTA

# ========================================
# VIEWS PROGETTI
# ========================================

def project_list(request):
    """Lista tutti i progetti - HOME dell'applicazione"""
    projects = Project.objects.filter(is_active=True).prefetch_related('experiments').order_by('-created_at')
    
    # Statistiche
    total_experiments = Experiment.objects.filter(project__is_active=True).count()
    completed_experiments = Experiment.objects.filter(
        project__is_active=True, 
        status='completed'
    ).count()
    
    context = {
        'projects': projects,
        'total_projects': projects.count(),
        'total_experiments': total_experiments,
        'completed_experiments': completed_experiments,
    }
    
    return render(request, 'project_list.html', context)


def project_detail(request, pk):
    """Dettaglio di un singolo progetto"""
    project = get_object_or_404(Project, pk=pk)
    experiments = project.experiments.all().order_by('-created_at')
    
    stats = {
        'total': experiments.count(),
        'running': experiments.filter(status='running').count(),
        'completed': experiments.filter(status='completed').count(),
        'draft': experiments.filter(status='draft').count(),
        'persevere': experiments.filter(decision='persevere').count(),
        'pivot': experiments.filter(decision='pivot').count(),
    }
    
    context = {
        'project': project,
        'experiments': experiments,
        'stats': stats,
    }
    
    return render(request, 'project_detail.html', context)


def project_create(request):
    """Crea un nuovo progetto"""
    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save()
            messages.success(request, f'Progetto "{project.name}" creato con successo!')
            return redirect('projects:detail', pk=project.pk)
    else:
        form = ProjectForm()
    
    context = {
        'form': form,
        'title': 'Nuovo Progetto',
        'button_text': 'Crea Progetto'
    }
    
    return render(request, 'project_form.html', context)


def project_edit(request, pk):
    """Modifica un progetto esistente"""
    project = get_object_or_404(Project, pk=pk)
    
    if request.method == 'POST':
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            form.save()
            messages.success(request, f'Progetto "{project.name}" aggiornato con successo!')
            return redirect('projects:detail', pk=project.pk)
    else:
        form = ProjectForm(instance=project)
    
    context = {
        'form': form,
        'project': project,
        'title': f'Modifica Progetto: {project.name}',
        'button_text': 'Salva Modifiche'
    }
    
    return render(request, 'project_form.html', context)


def project_delete(request, pk):
    """Elimina (soft delete) un progetto"""
    project = get_object_or_404(Project, pk=pk)
    
    if request.method == 'POST':
        project_name = project.name
        project.is_active = False
        project.save()
        messages.warning(request, f'Progetto "{project_name}" eliminato.')
        return redirect('projects:list')
    
    context = {
        'project': project,
    }
    
    return render(request, 'project_confirm_delete.html', context)


# ========================================
# VIEWS ESPERIMENTI
# ========================================

def experiment_list(request, project_pk):
    """Lista esperimenti di un progetto"""
    project = get_object_or_404(Project, pk=project_pk)
    experiments = project.experiments.all().order_by('-created_at')
    
    context = {
        'project': project,
        'experiments': experiments,
    }
    
    return render(request, 'experiment_list.html', context)


def experiment_detail(request, project_pk, pk):
    """Dettaglio esperimento"""
    project = get_object_or_404(Project, pk=project_pk)
    experiment = get_object_or_404(Experiment, pk=pk, project=project)
    indicators = experiment.indicators.all().prefetch_related('results')
    
    context = {
        'project': project,
        'experiment': experiment,
        'indicators': indicators,
    }
    
    return render(request, 'experiment_detail.html', context)


def experiment_create(request, project_pk):
    """Crea nuovo esperimento in un progetto"""
    project = get_object_or_404(Project, pk=project_pk)
    
    if request.method == 'POST':
        form = ExperimentForm(request.POST)
        if form.is_valid():
            experiment = form.save(commit=False)
            experiment.project = project
            experiment.save()
            messages.success(request, f'Esperimento "{experiment.title}" creato con successo!')
            return redirect('projects:experiment_detail', project_pk=project.pk, pk=experiment.pk)
    else:
        form = ExperimentForm()
    
    context = {
        'form': form,
        'project': project,
        'title': f'Nuovo Esperimento in {project.name}',
        'button_text': 'Crea Esperimento'
    }
    
    return render(request, 'experiment_form.html', context)


def experiment_edit(request, project_pk, pk):
    """Modifica esperimento esistente"""
    project = get_object_or_404(Project, pk=project_pk)
    experiment = get_object_or_404(Experiment, pk=pk, project=project)
    
    if request.method == 'POST':
        form = ExperimentForm(request.POST, instance=experiment)
        if form.is_valid():
            form.save()
            messages.success(request, f'Esperimento "{experiment.title}" aggiornato!')
            return redirect('projects:experiment_detail', project_pk=project.pk, pk=experiment.pk)
    else:
        form = ExperimentForm(instance=experiment)
    
    context = {
        'form': form,
        'project': project,
        'experiment': experiment,
        'title': f'Modifica: {experiment.title}',
        'button_text': 'Salva Modifiche'
    }
    
    return render(request, 'experiment_form.html', context)


def experiment_delete(request, project_pk, pk):
    """Elimina esperimento"""
    project = get_object_or_404(Project, pk=project_pk)
    experiment = get_object_or_404(Experiment, pk=pk, project=project)
    
    if request.method == 'POST':
        experiment_title = experiment.title
        experiment.delete()
        messages.warning(request, f'Esperimento "{experiment_title}" eliminato.')
        return redirect('projects:experiment_list', project_pk=project.pk)
    
    context = {
        'project': project,
        'experiment': experiment,
    }
    
    return render(request, 'experiment_confirm_delete.html', context)


# projects/views.py - FUNZIONE experiment_dashboard COMPLETA
# Sostituisci SOLO questa funzione nel tuo views.py esistente

import json
from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import Project, Experiment

def experiment_dashboard(request, project_pk, pk):
    """
    Dashboard esperimento con grafici e tabelle adattivi al test_type.
    ✅ FIX: Calcolo corretto gap per baseline (valore assoluto)
    """
    project = get_object_or_404(Project, pk=project_pk)
    experiment = get_object_or_404(Experiment, pk=pk, project=project)
    indicators = experiment.indicators.all().prefetch_related('results')
    
    chart_data = []
    
    for indicator in indicators:
        results = indicator.results.order_by('measured_at')
        
        if not results.exists():
            continue
        
        # Prepara dati in base a test_type
        test_type = indicator.test_type
        
        # Converti in lista Python sicura
        results_list = []
        
        if test_type == 'single':
            # ========================================
            # SINGLE BASELINE: valore + gap assoluto
            # ========================================
            for result in results:
                # ✅ CORRETTO: per baseline, target_uplift è valore assoluto
                target_value = float(indicator.target_uplift or 0)
                baseline_value = float(result.value_control or 0)
                
                # Se target_uplift è 0, non c'è target aspirazionale
                if target_value == 0:
                    gap = 0
                    gap_percentage = 0
                    target_display = baseline_value  # Usa baseline come riferimento
                else:
                    # Gap = baseline - target (valori assoluti)
                    gap = baseline_value - target_value
                    # Gap % = quanto manca/eccede rispetto al target
                    gap_percentage = round((gap / target_value * 100) if target_value != 0 else 0, 2)
                    target_display = target_value
                
                results_list.append({
                    'date': result.measured_at.strftime('%d/%m/%Y'),
                    'baseline': baseline_value,
                    'target': target_display,
                    'gap': gap,
                    'gap_percentage': gap_percentage
                })
        
        elif test_type == 'pre_post':
            # ========================================
            # PRE/POST TEST: before vs after
            # ========================================
            for result in results:
                results_list.append({
                    'date': result.measured_at.strftime('%d/%m/%Y'),
                    'before': float(result.value_control or 0),
                    'after': float(result.value_variant or 0),
                    'delta': float(result.delta_percentage or 0)
                })
        
        else:  # 'ab_test'
            # ========================================
            # A/B TEST: control vs variant (standard)
            # ========================================
            for result in results:
                results_list.append({
                    'date': result.measured_at.strftime('%d/%m/%Y'),
                    'control': float(result.value_control or 0),
                    'variant': float(result.value_variant or 0),
                    'delta': float(result.delta_percentage or 0)
                })
        
        chart_data.append({
            'indicator': indicator,
            'results': results,
            'results_json': results_list,
            'test_type': test_type
        })
    
    # Converti in JSON sicuro per Chart.js
    chart_data_json = json.dumps([{
        'indicatorId': item['indicator'].id,
        'indicatorName': item['indicator'].name,
        'testType': item['test_type'],
        'targetUplift': float(item['indicator'].target_uplift or 0),
        'results': item['results_json']
    } for item in chart_data])
    
    context = {
        'project': project,
        'experiment': experiment,
        'indicators': indicators,
        'chart_data': chart_data,
        'chart_data_json': chart_data_json
    }
    
    return render(request, 'experiment_dashboard.html', context)
# ========================================
# VIEW AGGIORNAMENTO BIGQUERY
# ========================================

def experiment_update_from_bigquery(request, project_pk, pk):
    """
    Aggiorna tutti gli indicatori dell'esperimento interrogando BigQuery (mock).
    Questa view viene chiamata quando l'utente clicca "Aggiorna da BigQuery".
    """
    project = get_object_or_404(Project, pk=project_pk)
    experiment = get_object_or_404(Experiment, pk=pk, project=project)
    
    # Esegue l'aggiornamento IMPORTANDO TUTTI I DATI STORICI
    results = update_experiment_from_bigquery(experiment, import_all=True)
    
    # Messaggi di feedback per l'utente
    if results['updated'] > 0:
        messages.success(
            request, 
            f"✅ Aggiornati {results['updated']}/{results['total_indicators']} indicatori! "
            f"Importati {results['total_results_created']} punti dati storici da BigQuery."
        )
    
    if results['skipped'] > 0:
        # Mostra solo i primi 3 errori per non sovraccaricare il messaggio
        error_summary = ', '.join(results['errors'][:3])
        if len(results['errors']) > 3:
            error_summary += f" (e altri {len(results['errors']) - 3}...)"
        
        messages.warning(
            request,
            f"⚠️ {results['skipped']} indicatori saltati. Dettagli: {error_summary}"
        )
    
    if results['updated'] == 0 and results['total_indicators'] > 0:
        messages.error(
            request,
            "❌ Nessun indicatore aggiornato. Verifica che abbiano metric_key configurata e che esistano dati in MockBigQueryData."
        )
    
    # Redirect alla dashboard per vedere i risultati
    return redirect('projects:experiment_dashboard', project_pk=project.pk, pk=experiment.pk)

