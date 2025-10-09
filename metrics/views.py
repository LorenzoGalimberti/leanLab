# metrics/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from projects.models import Experiment
from .models import Indicator, Result
from .forms import IndicatorForm, ResultForm

# ========================================
# VIEWS INDICATORI
# ========================================

def indicator_create(request, experiment_pk):
    """Crea nuovo indicatore per un esperimento"""
    experiment = get_object_or_404(Experiment, pk=experiment_pk)
    project = experiment.project
    
    if request.method == 'POST':
        form = IndicatorForm(request.POST)
        if form.is_valid():
            indicator = form.save(commit=False)
            indicator.experiment = experiment
            indicator.save()
            messages.success(request, f'Indicatore "{indicator.name}" creato con successo!')
            return redirect('projects:experiment_detail', project_pk=project.pk, pk=experiment.pk)
    else:
        form = IndicatorForm()
    
    context = {
        'form': form,
        'experiment': experiment,
        'project': project,
        'title': f'Nuovo Indicatore per {experiment.title}',
        'button_text': 'Crea Indicatore'
    }
    
    return render(request, 'indicator_form.html', context)


def indicator_edit(request, pk):
    """Modifica indicatore esistente"""
    indicator = get_object_or_404(Indicator, pk=pk)
    experiment = indicator.experiment
    project = experiment.project
    
    if request.method == 'POST':
        form = IndicatorForm(request.POST, instance=indicator)
        if form.is_valid():
            form.save()
            messages.success(request, f'Indicatore "{indicator.name}" aggiornato!')
            return redirect('projects:experiment_detail', project_pk=project.pk, pk=experiment.pk)
    else:
        form = IndicatorForm(instance=indicator)
    
    context = {
        'form': form,
        'indicator': indicator,
        'experiment': experiment,
        'project': project,
        'title': f'Modifica Indicatore: {indicator.name}',
        'button_text': 'Salva Modifiche'
    }
    
    return render(request, 'indicator_form.html', context)


def indicator_delete(request, pk):
    """Elimina indicatore"""
    indicator = get_object_or_404(Indicator, pk=pk)
    experiment = indicator.experiment
    project = experiment.project
    
    if request.method == 'POST':
        indicator_name = indicator.name
        indicator.delete()
        messages.warning(request, f'Indicatore "{indicator_name}" eliminato.')
        return redirect('projects:experiment_detail', project_pk=project.pk, pk=experiment.pk)
    
    context = {
        'indicator': indicator,
        'experiment': experiment,
        'project': project,
    }
    
    return render(request, 'indicator_confirm_delete.html', context)


# ========================================
# VIEWS RISULTATI
# ========================================

def result_create(request, indicator_pk):
    """Aggiungi risultato manuale a un indicatore"""
    indicator = get_object_or_404(Indicator, pk=indicator_pk)
    experiment = indicator.experiment
    project = experiment.project
    
    if request.method == 'POST':
        form = ResultForm(request.POST)
        # ✅ NUOVO: Passa l'indicatore al form per renderlo dinamico
        form.indicator = indicator
        
        if form.is_valid():
            result = form.save(commit=False)
            result.indicator = indicator
            
            # ✅ NUOVO: Per test_type='single', copia automaticamente il valore
            if indicator.test_type == 'single':
                result.value_variant = result.value_control
            
            result.save()  # Il save() automatico calcola delta % e decisione
            
            # ✅ NUOVO: Messaggio adattato per baseline
            if indicator.test_type == 'single':
                messages.success(
                    request, 
                    f'Baseline salvata! Valore: {result.value_control:.2f}'
                )
            else:
                messages.success(
                    request, 
                    f'Risultato salvato! Delta: {result.delta_percentage:.2f}% → {result.decision_auto.upper()}'
                )
            
            return redirect('projects:experiment_detail', project_pk=project.pk, pk=experiment.pk)
    else:
        form = ResultForm()
        # ✅ NUOVO: Passa l'indicatore anche per GET (form vuoto)
        form.indicator = indicator
    
    context = {
        'form': form,
        'indicator': indicator,
        'experiment': experiment,
        'project': project,
        'title': f'Nuovo Risultato per {indicator.name}',
        'button_text': 'Salva Risultato'
    }
    
    return render(request, 'result_form.html', context)


def result_edit(request, pk):
    """Modifica risultato esistente"""
    result = get_object_or_404(Result, pk=pk)
    indicator = result.indicator
    experiment = indicator.experiment
    project = experiment.project
    
    if request.method == 'POST':
        form = ResultForm(request.POST, instance=result)
        # ✅ NUOVO: Il form prende l'indicatore dall'istanza result
        # (già gestito nel __init__ del form, ma esplicitiamo per chiarezza)
        
        if form.is_valid():
            result = form.save(commit=False)
            
            # ✅ NUOVO: Per test_type='single', copia automaticamente il valore
            if indicator.test_type == 'single':
                result.value_variant = result.value_control
            
            result.save()
            
            # ✅ NUOVO: Messaggio adattato
            if indicator.test_type == 'single':
                messages.success(request, f'Baseline aggiornata! Valore: {result.value_control:.2f}')
            else:
                messages.success(request, f'Risultato aggiornato! Delta: {result.delta_percentage:.2f}%')
            
            return redirect('projects:experiment_detail', project_pk=project.pk, pk=experiment.pk)
    else:
        form = ResultForm(instance=result)
        # Il form prende automaticamente l'indicatore da result.indicator
    
    context = {
        'form': form,
        'result': result,
        'indicator': indicator,
        'experiment': experiment,
        'project': project,
        'title': f'Modifica Risultato del {result.measured_at.strftime("%d/%m/%Y")}',
        'button_text': 'Salva Modifiche'
    }
    
    return render(request, 'result_form.html', context)


def result_delete(request, pk):
    """Elimina risultato"""
    result = get_object_or_404(Result, pk=pk)
    indicator = result.indicator
    experiment = indicator.experiment
    project = experiment.project
    
    if request.method == 'POST':
        result_date = result.measured_at.strftime("%d/%m/%Y")
        result.delete()
        messages.warning(request, f'Risultato del {result_date} eliminato.')
        return redirect('projects:experiment_detail', project_pk=project.pk, pk=experiment.pk)
    
    context = {
        'result': result,
        'indicator': indicator,
        'experiment': experiment,
        'project': project,
    }
    
    return render(request, 'result_confirm_delete.html', context)


def result_list(request, indicator_pk):
    """Lista tutti i risultati di un indicatore (opzionale)"""
    indicator = get_object_or_404(Indicator, pk=indicator_pk)
    experiment = indicator.experiment
    project = experiment.project
    results = indicator.results.all().order_by('-measured_at')
    
    context = {
        'indicator': indicator,
        'experiment': experiment,
        'project': project,
        'results': results,
    }
    
    return render(request, 'result_list.html', context)
