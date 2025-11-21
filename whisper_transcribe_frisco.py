#!/usr/bin/env python3
"""
Whisper Transcribe RTX 5080 - Python Edition
Usa Faster-Whisper nativo Python (GRATIS, più veloce dell'eseguibile)
"""

import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime
import argparse
import re

# Colori per terminale
class Colors:
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    RESET = '\033[0m'
    BOLD = '\033[1m'
    WHITE = '\033[97m'
    BRIGHT_GREEN = '\033[92m\033[1m'  # Matrix style!

# Modello corrente (globale)
CURRENT_MODEL = 'large-v3'

# Modelli disponibili
AVAILABLE_MODELS = [
    {'name': 'small', 'desc': 'Veloce, meno accurato (~460 MB)'},
    {'name': 'medium', 'desc': 'Bilanciato (~1.5 GB)'},
    {'name': 'large-v3', 'desc': 'Massima qualità (~3 GB) [CONSIGLIATO]'}
]

def print_colored(message, color=Colors.RESET):
    print(f"{color}{message}{Colors.RESET}")

def check_dependencies():
    """Verifica e installa dipendenze necessarie"""
    print_colored("\n[INFO] Verifico dipendenze...", Colors.CYAN)
    
    dependencies = {
        'faster-whisper': 'faster-whisper',
        'torch': 'torch',
        'ffmpeg-python': 'ffmpeg-python',
        'tqdm': 'tqdm'
    }
    
    missing = []
    
    for package, pip_name in dependencies.items():
        try:
            __import__(package.replace('-', '_'))
            print_colored(f"[OK] {package} installato", Colors.GREEN)
        except ImportError:
            missing.append(pip_name)
            print_colored(f"[WARN] {package} non trovato", Colors.YELLOW)
    
    if missing:
        print_colored(f"\n[INFO] Installo pacchetti mancanti: {', '.join(missing)}", Colors.CYAN)
        
        # Installa PyTorch con CUDA
        if 'torch' in missing:
            print_colored("[INFO] Installo PyTorch con supporto CUDA...", Colors.CYAN)
            subprocess.check_call([
                sys.executable, '-m', 'pip', 'install', 
                'torch', 'torchvision', 'torchaudio',
                '--index-url', 'https://download.pytorch.org/whl/cu121'
            ])
            missing.remove('torch')
        
        # Installa altri pacchetti
        if missing:
            subprocess.check_call([
                sys.executable, '-m', 'pip', 'install'
            ] + missing)
        
        print_colored("[OK] Dipendenze installate!", Colors.GREEN)
    
    # Verifica ffmpeg
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        print_colored("[OK] ffmpeg trovato", Colors.GREEN)
    except:
        print_colored("[ERROR] ffmpeg non trovato! Scarica da: https://ffmpeg.org/download.html", Colors.RED)
        return False
    
    return True

def test_gpu():
    """Test GPU e compute types supportati"""
    print_colored("\n" + "="*50, Colors.CYAN)
    print_colored("  TEST GPU E DIAGNOSTICA", Colors.CYAN)
    print_colored("="*50, Colors.CYAN)
    
    try:
        import torch
        
        if torch.cuda.is_available():
            print_colored(f"\n[OK] CUDA disponibile!", Colors.GREEN)
            print_colored(f"GPU: {torch.cuda.get_device_name(0)}", Colors.GREEN)
            print_colored(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB", Colors.GREEN)
            print_colored(f"CUDA Version: {torch.version.cuda}", Colors.GREEN)
        else:
            print_colored("[WARN] CUDA non disponibile, uso CPU", Colors.YELLOW)
            return False
        
        from faster_whisper import WhisperModel
        
        print_colored("\n[INFO] Testo compute types...", Colors.CYAN)
        
        results = {}
        
        # Test float32
        try:
            print_colored("Test FLOAT32...", Colors.CYAN)
            model = WhisperModel("tiny", device="cuda", compute_type="float32")
            results['float32'] = True
            print_colored("[OK] FLOAT32 supportato", Colors.GREEN)
            del model
        except Exception as e:
            results['float32'] = False
            print_colored(f"[WARN] FLOAT32 fallito: {e}", Colors.YELLOW)
        
        # Test float16
        try:
            print_colored("Test FLOAT16...", Colors.CYAN)
            model = WhisperModel("tiny", device="cuda", compute_type="float16")
            results['float16'] = True
            print_colored("[OK] FLOAT16 supportato (OTTIMALE RTX 5080!)", Colors.GREEN)
            del model
        except Exception as e:
            results['float16'] = False
            print_colored(f"[WARN] FLOAT16 fallito: {e}", Colors.YELLOW)
        
        # Test int8
        try:
            print_colored("Test INT8...", Colors.CYAN)
            model = WhisperModel("tiny", device="cuda", compute_type="int8")
            results['int8'] = True
            print_colored("[OK] INT8 supportato (velocità massima!)", Colors.GREEN)
            del model
        except Exception as e:
            results['int8'] = False
            print_colored(f"[WARN] INT8 fallito: {e}", Colors.YELLOW)
        
        # Raccomandazioni
        print_colored("\n" + "="*50, Colors.CYAN)
        print_colored("RACCOMANDAZIONI:", Colors.CYAN)
        print_colored("="*50, Colors.CYAN)
        
        if results.get('float16'):
            print_colored("[OK] Usa FLOAT16 per prestazioni ottimali RTX 5080", Colors.GREEN)
            return 'float16'
        elif results.get('int8'):
            print_colored("[OK] Usa INT8 per velocita massima", Colors.GREEN)
            return 'int8'
        elif results.get('float32'):
            print_colored("[OK] Usa FLOAT32 (compatibilita universale)", Colors.GREEN)
            return 'float32'
        else:
            print_colored("! Nessun compute type GPU funzionante, uso CPU", Colors.YELLOW)
            return None
            
    except Exception as e:
        print_colored(f"[ERROR] Test GPU fallito: {e}", Colors.RED)
        return None

def convert_to_wav(input_file, output_dir):
    """Converte audio in WAV 16kHz mono"""
    from tqdm import tqdm

    print_colored("\n[1/3] Conversione in WAV...", Colors.CYAN)

    input_path = Path(input_file)
    output_path = Path(output_dir) / f"{input_path.stem}.wav"

    # Prima otteniamo la durata del file audio
    duration_cmd = [
        'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1', str(input_path)
    ]

    try:
        duration_result = subprocess.run(duration_cmd, capture_output=True, text=True)
        duration = float(duration_result.stdout.strip())
    except:
        duration = None

    cmd = [
        'ffmpeg', '-i', str(input_path),
        '-ar', '16000', '-ac', '1',
        '-c:a', 'pcm_s16le',
        '-progress', 'pipe:1',
        str(output_path), '-y'
    ]

    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               universal_newlines=True, bufsize=1)

    pbar = None
    if duration:
        pbar = tqdm(total=int(duration * 1000000), unit='us', desc='Conversione',
                   bar_format='{desc}: {percentage:3.0f}%|{bar}| {elapsed}<{remaining}')

    for line in process.stdout:
        if pbar and line.startswith('out_time_us='):
            time_us = int(line.split('=')[1].strip())
            pbar.n = min(time_us, pbar.total)
            pbar.refresh()

    process.wait()

    if pbar:
        pbar.close()

    if process.returncode != 0:
        stderr = process.stderr.read()
        print_colored(f"[ERROR] Conversione fallita: {stderr}", Colors.RED)
        return None

    print_colored(f"[OK] WAV creato: {output_path}", Colors.GREEN)
    return output_path

def get_audio_duration(audio_file):
    """Ottiene la durata dell'audio in secondi"""
    try:
        cmd = [
            'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1', str(audio_file)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())
    except:
        return None

def transcribe_audio(wav_path, output_dir, task='transcribe', language=None,
                     model_size='medium', compute_type='float16', beam_size=5):
    """Trascrizione con Faster-Whisper"""
    print_colored("\n[2/3] Trascrizione...", Colors.CYAN)
    lang_display = language if language else "auto-detect"
    print_colored(f"Modello: {model_size} | Compute: {compute_type} | Lingua: {lang_display}", Colors.CYAN)
    print_colored(f"Beam: {beam_size}", Colors.CYAN)

    # Ottieni durata audio per calcolare ETA
    audio_duration = get_audio_duration(wav_path)
    if audio_duration:
        minutes = int(audio_duration // 60)
        seconds = int(audio_duration % 60)
        print_colored(f"Durata audio: {minutes}m {seconds}s", Colors.CYAN)
    
    from faster_whisper import WhisperModel
    
    device = "cuda" if compute_type else "cpu"
    if not compute_type:
        compute_type = "float32"
        print_colored("[WARN] Uso CPU (lento)", Colors.YELLOW)
    
    # Configurazioni di fallback
    configs = [
        {'compute': compute_type, 'device': device},
        {'compute': 'float32', 'device': 'cuda'},
        {'compute': 'int8_float32', 'device': 'cuda'},
        {'compute': 'float32', 'device': 'cpu'}
    ]
    
    for i, config in enumerate(configs, 1):
        try:
            if i > 1:
                print_colored(f"\n[RETRY {i}/{len(configs)}] Compute={config['compute']} Device={config['device']}", Colors.YELLOW)
            
            # Carica modello
            print_colored(f"[INFO] Carico modello {model_size}...", Colors.CYAN)
            model = WhisperModel(
                model_size,
                device=config['device'],
                compute_type=config['compute']
            )
            
            # Trascrizione
            print_colored("[INFO] Trascrizione in corso (può richiedere alcuni minuti)...", Colors.CYAN)
            
            # Prepara parametri - language può essere None per auto-detection
            transcribe_params = {
                'audio': str(wav_path),
                'task': task,
                'beam_size': beam_size,
                'vad_filter': True,
                'vad_parameters': dict(min_silence_duration_ms=500),
                'condition_on_previous_text': True,
                'temperature': 0.0,
                'compression_ratio_threshold': 2.4,
                'log_prob_threshold': -1.0,
                'no_speech_threshold': 0.6
            }
            
            # Aggiungi language solo se specificato (None = auto-detect)
            if language is not None:
                transcribe_params['language'] = language
            
            segments, info = model.transcribe(**transcribe_params)

            print_colored(f"[OK] Lingua rilevata: {info.language} (probabilità: {info.language_probability:.2%})", Colors.GREEN)

            # Salva SRT con visualizzazione in tempo reale stile Matrix
            import time
            output_path = Path(output_dir) / f"{Path(wav_path).stem}.srt"

            print_colored("\n" + "="*70, Colors.CYAN)
            print_colored("  TRASCRIZIONE IN TEMPO REALE - MATRIX MODE", Colors.BRIGHT_GREEN)
            print_colored("="*70, Colors.CYAN)
            print()

            segments_list = []
            start_time = time.time()

            with open(output_path, 'w', encoding='utf-8') as f:
                segment_count = 0

                for segment in segments:
                    segment_count += 1
                    segments_list.append(segment)

                    # Scrivi nel file SRT
                    f.write(f"{segment_count}\n")
                    f.write(f"{format_timestamp(segment.start)} --> {format_timestamp(segment.end)}\n")
                    f.write(f"{segment.text.strip()}\n\n")
                    f.flush()  # Forza scrittura immediata

                    # Visualizzazione Matrix-style in tempo reale
                    timestamp_str = f"[{format_timestamp(segment.start).split(',')[0]}]"
                    print(f"{Colors.YELLOW}{timestamp_str}{Colors.RESET} ", end='', flush=True)

                    # Stampa il testo carattere per carattere (effetto Matrix)
                    text = segment.text.strip()
                    for char in text:
                        print(f"{Colors.BRIGHT_GREEN}{char}{Colors.RESET}", end='', flush=True)
                        time.sleep(0.01)  # Piccolo delay per effetto "digitazione"

                    print()  # Newline dopo ogni segmento

                    # Calcola e mostra ETA ogni 5 segmenti
                    if segment_count % 5 == 0:
                        elapsed_time = time.time() - start_time
                        audio_processed = segment.end  # Tempo audio processato in secondi

                        if audio_duration and audio_processed > 0:
                            # Calcola velocità di processamento
                            processing_speed = audio_processed / elapsed_time  # audio_sec / real_sec
                            remaining_audio = audio_duration - audio_processed
                            eta_seconds = remaining_audio / processing_speed if processing_speed > 0 else 0

                            # Formatta ETA
                            eta_min = int(eta_seconds // 60)
                            eta_sec = int(eta_seconds % 60)
                            progress_pct = (audio_processed / audio_duration) * 100

                            print_colored(
                                f"  [{segment_count} seg] "
                                f"Progresso: {progress_pct:.1f}% | "
                                f"Velocità: {processing_speed:.1f}x | "
                                f"ETA: {eta_min}m {eta_sec}s",
                                Colors.CYAN
                            )
                        else:
                            print_colored(f"  [{segment_count} segmenti processati...]", Colors.CYAN)

            print()
            print_colored("="*70, Colors.CYAN)
            print_colored(f"[OK] Trascrizione completata! ({len(segments_list)} segmenti)", Colors.GREEN)
            print_colored(f"[OK] File salvato: {output_path}", Colors.GREEN)
            
            return output_path
            
        except Exception as e:
            print_colored(f"[ERROR] Tentativo {i} fallito: {e}", Colors.RED)
            if i < len(configs):
                continue
            else:
                return None
    
    return None

def format_timestamp(seconds):
    """Formatta timestamp per SRT"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

def select_model():
    """Menu selezione modello Whisper"""
    global CURRENT_MODEL

    print_colored("\n" + "="*70, Colors.CYAN)
    print_colored("  SELEZIONE MODELLO WHISPER", Colors.CYAN)
    print_colored("="*70, Colors.CYAN)
    print()

    for i, model in enumerate(AVAILABLE_MODELS, 1):
        color = Colors.BRIGHT_GREEN if model['name'] == CURRENT_MODEL else Colors.WHITE
        marker = " ◄ ATTUALE" if model['name'] == CURRENT_MODEL else ""
        print_colored(f"  [{i}] {model['name']:12} - {model['desc']}{marker}", color)

    print()
    print_colored("="*70, Colors.CYAN)

    choice = input("\nScegli modello [1-3] o INVIO per confermare attuale: ").strip()

    if not choice:
        print_colored(f"\n[INFO] Confermato modello: {CURRENT_MODEL}", Colors.GREEN)
        input("\nPremi INVIO per continuare...")
        return

    try:
        idx = int(choice) - 1
        if 0 <= idx < len(AVAILABLE_MODELS):
            CURRENT_MODEL = AVAILABLE_MODELS[idx]['name']
            print_colored(f"\n[OK] Modello cambiato in: {CURRENT_MODEL}", Colors.GREEN)
        else:
            print_colored("\n[ERROR] Scelta non valida!", Colors.RED)
    except ValueError:
        print_colored("\n[ERROR] Inserisci un numero valido!", Colors.RED)

    input("\nPremi INVIO per continuare...")

def interactive_menu():
    """Menu interattivo"""
    # Setup
    input_dir = Path("audio")
    output_dir = Path("transcripts")
    log_dir = Path("logs")
    
    for d in [input_dir, output_dir, log_dir]:
        d.mkdir(exist_ok=True)
    
    # Test GPU
    best_compute = test_gpu()
    input("\nPremi INVIO per continuare...")
    
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')

        print_colored("═" * 70, Colors.CYAN)
        print_colored("  FRISCO WHISPER RTX 5080 [RULEZ] - Python Edition", Colors.GREEN)
        print_colored("═" * 70, Colors.CYAN)
        print()
        print_colored("GPU: NVIDIA RTX 5080 16GB", Colors.GREEN)
        print_colored(f"Compute consigliato: {best_compute or 'CPU'}", Colors.YELLOW)
        print_colored(f"Modello attuale: {CURRENT_MODEL}", Colors.BRIGHT_GREEN)
        print()
        print_colored("="*70, Colors.CYAN)
        print("[1] Trascrivi audio (mantiene lingua)")
        print("[2] Traduci in italiano")
        print("[3] Batch processing")
        print("[4] Test GPU")
        print("[5] Scegli modello (default: large-v3)")
        print("[0] Esci")
        print()

        choice = input("Scelta [0-5]: ")
        
        if choice == '0':
            print_colored("\nArrivederci!", Colors.CYAN)
            break
            
        elif choice == '1':
            language = input("\nLingua [it/en/es/fr/de o INVIO per auto-detect] (default: auto): ").strip()
            if not language or language.lower() == 'auto':
                language = None  # None attiva auto-detection in faster-whisper
                print_colored("[INFO] Rilevamento automatico lingua attivato", Colors.CYAN)
            process_files(input_dir, output_dir, 'transcribe', language, best_compute)
            
        elif choice == '2':
            print_colored("\nTraduzione verso italiano", Colors.CYAN)
            process_files(input_dir, output_dir, 'translate', 'en', best_compute)
            
        elif choice == '3':
            language = input("\nLingua [it/en/es/fr/de o INVIO per auto-detect] (default: auto): ").strip()
            if not language or language.lower() == 'auto':
                language = None  # None attiva auto-detection
                print_colored("[INFO] Rilevamento automatico lingua attivato", Colors.CYAN)
            batch_process(input_dir, output_dir, 'transcribe', language, best_compute)
            
        elif choice == '4':
            best_compute = test_gpu()
            input("\nPremi INVIO per continuare...")

        elif choice == '5':
            select_model()

def process_files(input_dir, output_dir, task, language, compute_type):
    """Processa singolo file"""
    files = list(input_dir.glob('*.m4a')) + list(input_dir.glob('*.mp3')) + \
            list(input_dir.glob('*.wav')) + list(input_dir.glob('*.mp4')) + \
            list(input_dir.glob('*.aac')) + list(input_dir.glob('*.flac'))
    
    if not files:
        print_colored("\nNessun file trovato!", Colors.YELLOW)
        input("\nPremi INVIO per continuare...")
        return
    
    # Se c'è un solo file, selezionalo automaticamente
    if len(files) == 1:
        input_file = files[0]
        print_colored(f"\n[AUTO] Selezionato unico file disponibile: {input_file.name}", Colors.GREEN)
    else:
        # Mostra lista file disponibili
        print_colored(f"\nFile disponibili in '{input_dir}':", Colors.CYAN)
        print("="*50)
        
        for i, f in enumerate(files, 1):
            print(f"  [{i}] {f.name}")
        
        print("="*50)
        
        choice = input("\nNumero file o nome completo (INVIO per annullare): ")
        
        if not choice:
            return
        
        # Supporta sia numero che nome
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(files):
                input_file = files[idx]
            else:
                print_colored("Numero non valido!", Colors.RED)
                input("\nPremi INVIO per continuare...")
                return
        except ValueError:
            # È un nome file
            input_file = input_dir / choice
            if not input_file.exists():
                print_colored(f"File non trovato: {input_file}", Colors.RED)
                input("\nPremi INVIO per continuare...")
                return
    
    # Converti e trascrivi
    wav_path = convert_to_wav(input_file, output_dir)
    if not wav_path:
        input("\nPremi INVIO per continuare...")
        return
    
    result = transcribe_audio(
        wav_path, output_dir,
        task=task,
        language=language,
        model_size=CURRENT_MODEL,
        compute_type=compute_type or 'float32'
    )
    
    # Pulizia
    if wav_path.exists():
        wav_path.unlink()
    
    if result:
        print_colored("\n" + "="*50, Colors.GREEN)
        print_colored("COMPLETATO CON SUCCESSO!", Colors.GREEN)
        print_colored("="*50, Colors.GREEN)
        print(f"Output: {result}")
        
        open_file = input("\nAprire il file? [S/N] (default: S): ") or "S"
        if open_file.lower() == 's':
            try:
                if os.name == 'nt':
                    os.startfile(result)
                else:
                    subprocess.run(['xdg-open', result])
            except Exception as e:
                print_colored(f"Impossibile aprire automaticamente: {e}", Colors.YELLOW)
    
    input("\nPremi INVIO per continuare...")

def batch_process(input_dir, output_dir, task, language, compute_type):
    """Batch processing"""
    files = list(input_dir.glob('*.m4a')) + list(input_dir.glob('*.mp3')) + \
            list(input_dir.glob('*.wav')) + list(input_dir.glob('*.mp4')) + \
            list(input_dir.glob('*.aac')) + list(input_dir.glob('*.flac'))
    
    if not files:
        print_colored("\nNessun file trovato!", Colors.YELLOW)
        input("\nPremi INVIO per continuare...")
        return
    
    print_colored(f"\n[INFO] Trovati {len(files)} file da processare:", Colors.CYAN)
    for i, f in enumerate(files, 1):
        print(f"  [{i}] {f.name}")
    
    confirm = input(f"\nProcessare tutti i {len(files)} file? [S/N] (default: S): ") or "S"
    if confirm.lower() != 's':
        return
    
    print_colored(f"\n[INFO] Inizio batch processing...", Colors.CYAN)
    
    success = 0
    failed = 0
    start_time = datetime.now()
    
    for i, file in enumerate(files, 1):
        print_colored(f"\n{'='*50}", Colors.YELLOW)
        print_colored(f"[{i}/{len(files)}] {file.name}", Colors.YELLOW)
        
        # Tempo stimato rimanente
        if i > 1:
            elapsed = (datetime.now() - start_time).total_seconds()
            avg_time = elapsed / (i - 1)
            remaining = avg_time * (len(files) - i + 1)
            print_colored(f"Tempo stimato rimanente: {int(remaining // 60)}m {int(remaining % 60)}s", Colors.CYAN)
        
        print_colored(f"{'='*50}", Colors.YELLOW)
        
        wav_path = convert_to_wav(file, output_dir)
        if not wav_path:
            failed += 1
            continue
        
        result = transcribe_audio(
            wav_path, output_dir,
            task=task,
            language=language,
            model_size=CURRENT_MODEL,
            compute_type=compute_type or 'float32'
        )
        
        if wav_path.exists():
            wav_path.unlink()
        
        if result:
            success += 1
        else:
            failed += 1
    
    total_time = (datetime.now() - start_time).total_seconds()
    
    print_colored("\n" + "="*50, Colors.CYAN)
    print_colored("BATCH COMPLETATO", Colors.CYAN)
    print_colored("="*50, Colors.CYAN)
    print(f"Totale: {len(files)}")
    print_colored(f"Successi: {success}", Colors.GREEN)
    print_colored(f"Falliti: {failed}", Colors.RED)
    print_colored(f"Tempo totale: {int(total_time // 60)}m {int(total_time % 60)}s", Colors.CYAN)
    
    input("\nPremi INVIO per continuare...")

def main():
    """Main entry point"""
    print_colored("""
 ________          __                                                                          __       __  __        __                                               
|        \\        |  \\                                                                        |  \\  _  |  \\|  \\      |  \\                                              
| $$$$$$$$______   \\$$  _______   _______   ______                                            | $$ / \\ | $$| $$____   \\$$  _______   ______    ______    ______        
| $$__   /      \\ |  \\ /       \\ /       \\ /      \\                                           | $$/  $\\| $$| $$    \\ |  \\ /       \\ /      \\  /      \\  /      \\       
| $$  \\ |  $$$$$$\\| $$|  $$$$$$$|  $$$$$$$|  $$$$$$\\                                          | $$  $$$\\ $$| $$$$$$$\\| $$|  $$$$$$$|  $$$$$$\\|  $$$$$$\\|  $$$$$$\\      
| $$$$$ | $$   \\$$| $$ \\$$    \\ | $$      | $$  | $$                                          | $$ $$\\$$\\$$| $$  | $$| $$ \\$$    \\ | $$  | $$| $$    $$| $$   \\$$      
| $$    | $$      | $$ _\\$$$$$$\\| $$_____ | $$__/ $$                                          | $$$$  \\$$$$| $$  | $$| $$ _\\$$$$$$\\| $$__/ $$| $$$$$$$$| $$            
| $$    | $$      | $$|       $$ \\$$     \\ \\$$    $$                                          | $$$    \\$$$| $$  | $$| $$|       $$| $$    $$ \\$$     \\| $$            
 \\$$     \\$$       \\$$ \\$$$$$$$   \\$$$$$$$  \\$$$$$$                                            \\$$      \\$$ \\$$   \\$$ \\$$ \\$$$$$$$ | $$$$$$$   \\$$$$$$$ \\$$            
                                                                                                                                   | $$                                
                                                                                                                                   | $$                                
                                                                                                                                    \\$$                                
 _______   __    __  __        ________  ________  __  __  __                          _______  ________  __    __        _______                                      
|       \\ |  \\  |  \\|  \\      |        \\|        \\|  \\|  \\|  \\                        |       \\|        \\|  \\  |  \\      |       \\                                     
| $$$$$$$\\| $$  | $$| $$      | $$$$$$$$ \\$$$$$$$$| $$| $$| $$                        | $$$$$$$\\\\$$$$$$$$| $$  | $$      | $$$$$$$  __    __  __    __  __    __       
| $$__| $$| $$  | $$| $$      | $$__        /  $$ | $$| $$| $$                        | $$__| $$  | $$    \\$$\\/  $$      | $$____  |  \\  /  \\|  \\  /  \\|  \\  /  \\      
| $$    $$| $$  | $$| $$      | $$  \\      /  $$  | $$| $$| $$                        | $$    $$  | $$     >$$  $$       | $$    \\  \\$$\\/  $$ \\$$\\/  $$ \\$$\\/  $$      
| $$$$$$$\\| $$  | $$| $$      | $$$$$     /  $$    \\$$ \\$$ \\$$                        | $$$$$$$\\  | $$    /  $$$$\\        \\$$$$$$$\\  >$$  $$   >$$  $$   >$$  $$       
| $$  | $$| $$__/ $$| $$_____ | $$_____  /  $$___  __  __  __                         | $$  | $$  | $$   |  $$ \\$$\\      |  \\__| $$ /  $$$$\\  /  $$$$\\  /  $$$$\\       
| $$  | $$ \\$$    $$| $$     \\| $$     \\|  $$    \\|  \\|  \\|  \\                        | $$  | $$  | $$   | $$  | $$       \\$$    $$|  $$ \\$$\\|  $$ \\$$\\|  $$ \\$$\\      
 \\$$   \\$$  \\$$$$$$  \\$$$$$$$$ \\$$$$$$$$ \\$$$$$$$$ \\$$ \\$$ \\$$                         \\$$   \\$$   \\$$    \\$$   \\$$        \\$$$$$$  \\$$   \\$$ \\$$   \\$$ \\$$   \\$$      
                                                                                                                                                                       
    """, Colors.CYAN)
    
    print_colored("  ⚡ Python Edition - CUDA Accelerated - float16 Optimized - NVIDIA RTX 5080 16GB ⚡\n", Colors.GREEN)
    
    if not check_dependencies():
        print_colored("\n[ERROR] Risolvi i problemi di dipendenze!", Colors.RED)
        input("\nPremi INVIO per uscire...")
        return
    
    print_colored("\n[OK] Sistema pronto!", Colors.GREEN)
    input("\nPremi INVIO per continuare...")
    
    interactive_menu()

if __name__ == "__main__":
    main()
