# metrics/management/commands/aggiorna_risultati.py

from django.core.management.base import BaseCommand
from google.cloud import bigquery
from datetime import datetime
from metrics.models import Indicator, Result
from decimal import Decimal

class Command(BaseCommand):
    help = 'Aggiorna automaticamente i risultati degli esperimenti da BigQuery'

    def add_arguments(self, parser):
        parser.add_argument(
            '--indicator',
            type=str,
            help='Nome indicatore specifico (opzionale). Se omesso, aggiorna tutti.'
        )
        parser.add_argument(
            '--experiment',
            type=str,
            help='Titolo esperimento specifico (opzionale)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Esegue solo una simulazione senza salvare'
        )

    def handle(self, *args, **options):
        indicator_name = options.get('indicator')
        experiment_title = options.get('experiment')
        dry_run = options.get('dry_run', False)
        
        self.stdout.write("=" * 70)
        self.stdout.write(self.style.SUCCESS("🚀 AGGIORNAMENTO RISULTATI DA BIGQUERY"))
        if dry_run:
            self.stdout.write(self.style.WARNING("⚠️  MODALITÀ DRY-RUN (nessun salvataggio)"))
        self.stdout.write("=" * 70)
        
        # Seleziona quali indicatori aggiornare
        indicators = Indicator.objects.exclude(
            bigquery_query__isnull=True
        ).exclude(
            bigquery_query=''
        )
        
        if indicator_name:
            indicators = indicators.filter(name=indicator_name)
            if not indicators.exists():
                self.stdout.write(self.style.ERROR(f"❌ Indicatore '{indicator_name}' non trovato"))
                return
        
        if experiment_title:
            indicators = indicators.filter(experiment__title=experiment_title)
        
        if not indicators.exists():
            self.stdout.write(self.style.WARNING("⚠️  Nessun indicatore trovato con query BigQuery configurata"))
            self.stdout.write("\n💡 Suggerimento: configura il campo 'Query BigQuery SQL' per gli indicatori nell'admin")
            return
        
        self.stdout.write(f"\n📊 Trovati {indicators.count()} indicatore/i da aggiornare:\n")
        for ind in indicators:
            self.stdout.write(f"   • {ind.name} ({ind.experiment.title})")
        self.stdout.write("")
        
        # Connetti a BigQuery
        try:
            client = bigquery.Client(project="knowhow-e6565")
            self.stdout.write("✅ Connesso a BigQuery\n")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Errore connessione BigQuery: {str(e)}"))
            self.stdout.write("\n💡 Verifica che GOOGLE_APPLICATION_CREDENTIALS sia configurato")
            return
        
        successi = 0
        errori = 0
        
        # Itera su ogni indicatore
        for indicator in indicators:
            self.stdout.write("-" * 70)
            self.stdout.write(f"📈 Aggiornamento: {self.style.SUCCESS(indicator.name)}")
            
            try:
                # Esegui la query specifica dell'indicatore
                query = indicator.bigquery_query
                
                self.stdout.write("🔍 Esecuzione query BigQuery...")
                risultato = client.query(query).result()
                rows = list(risultato)
                
                if not rows:
                    self.stdout.write(self.style.WARNING("   ⚠️  Query non ha restituito risultati"))
                    errori += 1
                    continue
                
                row = rows[0]
                
                # Estrai i valori (gestisci sia 'valore_control' che 'value_control')
                valore_control = float(row.get('valore_control') or row.get('value_control', 0))
                valore_variant = float(row.get('valore_variant') or row.get('value_variant', valore_control))
                
                self.stdout.write(f"   📊 Risultati:")
                self.stdout.write(f"      Valore Control: {self.style.SUCCESS(valore_control)}")
                self.stdout.write(f"      Valore Variant: {self.style.SUCCESS(valore_variant)}")
                
                # Calcola uplift se disponibile
                if valore_control > 0:
                    uplift = ((valore_variant - valore_control) / valore_control) * 100
                    self.stdout.write(f"      Uplift: {self.style.SUCCESS(f'{uplift:.2f}%')}")
                
                if dry_run:
                    self.stdout.write(f"   🔄 [DRY-RUN] Avrei salvato il risultato per {indicator.experiment.title}")
                else:
                    # Salva nel database
                    result, created = Result.objects.update_or_create(
                        indicator=indicator,
                        measured_at=datetime.now().date(),
                        defaults={
                            'value_control': Decimal(str(valore_control)),
                            'value_variant': Decimal(str(valore_variant)),
                            'notes': 'Aggiornamento automatico da BigQuery'
                        }
                    )
                    
                    status = "✅ Creato" if created else "✅ Aggiornato"
                    self.stdout.write(f"   {status} risultato per: {indicator.experiment.title}")
                
                successi += 1
                
            except KeyError as e:
                self.stdout.write(self.style.ERROR(f"   ❌ Errore: colonna mancante nella query: {str(e)}"))
                self.stdout.write(self.style.WARNING(f"   💡 Assicurati che la query restituisca: valore_control, valore_variant"))
                errori += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"   ❌ Errore: {str(e)}"))
                errori += 1
        
        # Riepilogo finale
        self.stdout.write("\n" + "=" * 70)
        self.stdout.write(self.style.SUCCESS(f"🎉 AGGIORNAMENTO COMPLETATO"))
        self.stdout.write(f"   ✅ Successi: {successi}")
        if errori > 0:
            self.stdout.write(self.style.WARNING(f"   ⚠️  Errori: {errori}"))
        self.stdout.write("=" * 70)
