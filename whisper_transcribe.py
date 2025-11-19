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

# Colori per terminale
class Colors:
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_colored(message, color=Colors.RESET):
    print(f"{color}{message}{Colors.RESET}")

def check_dependencies():
    """Verifica e installa dipendenze necessarie"""
    print_colored("\n[INFO] Verifico dipendenze...", Colors.CYAN)
    
    dependencies = {
        'faster-whisper': 'faster-whisper',
        'torch': 'torch',
        'ffmpeg-python': 'ffmpeg-python'
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
            print_colored("✓ Usa FLOAT16 per prestazioni ottimali RTX 5080", Colors.GREEN)
            return 'float16'
        elif results.get('int8'):
            print_colored("✓ Usa INT8 per velocità massima", Colors.GREEN)
            return 'int8'
        elif results.get('float32'):
            print_colored("✓ Usa FLOAT32 (compatibilità universale)", Colors.GREEN)
            return 'float32'
        else:
            print_colored("! Nessun compute type GPU funzionante, uso CPU", Colors.YELLOW)
            return None
            
    except Exception as e:
        print_colored(f"[ERROR] Test GPU fallito: {e}", Colors.RED)
        return None

def convert_to_wav(input_file, output_dir):
    """Converte audio in WAV 16kHz mono"""
    print_colored("\n[1/3] Conversione in WAV...", Colors.CYAN)
    
    input_path = Path(input_file)
    output_path = Path(output_dir) / f"{input_path.stem}.wav"
    
    cmd = [
        'ffmpeg', '-i', str(input_path),
        '-ar', '16000', '-ac', '1',
        '-c:a', 'pcm_s16le',
        str(output_path), '-y'
    ]
    
    result = subprocess.run(cmd, capture_output=True)
    
    if result.returncode != 0:
        print_colored(f"[ERROR] Conversione fallita: {result.stderr.decode()}", Colors.RED)
        return None
    
    print_colored(f"[OK] WAV creato: {output_path}", Colors.GREEN)
    return output_path

def transcribe_audio(wav_path, output_dir, task='transcribe', language='it', 
                     model_size='medium', compute_type='float16', beam_size=2, batch_size=24):
    """Trascrizione con Faster-Whisper"""
    print_colored("\n[2/3] Trascrizione...", Colors.CYAN)
    print_colored(f"Modello: {model_size} | Compute: {compute_type} | Lingua: {language}", Colors.CYAN)
    print_colored(f"Beam: {beam_size} | Batch: {batch_size}", Colors.CYAN)
    
    from faster_whisper import WhisperModel
    
    device = "cuda" if compute_type else "cpu"
    if not compute_type:
        compute_type = "float32"
        batch_size = 4
        print_colored("[WARN] Uso CPU (lento)", Colors.YELLOW)
    
    # Configurazioni di fallback
    configs = [
        {'compute': compute_type, 'device': device, 'batch': batch_size},
        {'compute': 'float32', 'device': 'cuda', 'batch': int(batch_size * 0.75)},
        {'compute': 'float32', 'device': 'cuda', 'batch': int(batch_size * 0.5)},
        {'compute': 'float32', 'device': 'cpu', 'batch': 4}
    ]
    
    for i, config in enumerate(configs, 1):
        try:
            if i > 1:
                print_colored(f"\n[RETRY {i}/{len(configs)}] Compute={config['compute']} Device={config['device']} Batch={config['batch']}", Colors.YELLOW)
            
            # Carica modello
            print_colored(f"[INFO] Carico modello {model_size}...", Colors.CYAN)
            model = WhisperModel(
                model_size,
                device=config['device'],
                compute_type=config['compute']
            )
            
            # Trascrizione
            print_colored("[INFO] Trascrizione in corso (può richiedere alcuni minuti)...", Colors.CYAN)
            
            segments, info = model.transcribe(
                str(wav_path),
                task=task,
                language=language,
                beam_size=beam_size,
                batch_size=config['batch'],
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=500)
            )
            
            print_colored(f"[OK] Lingua rilevata: {info.language} (probabilità: {info.language_probability:.2%})", Colors.GREEN)
            
            # Salva SRT
            output_path = Path(output_dir) / f"{Path(wav_path).stem}.srt"
            
            with open(output_path, 'w', encoding='utf-8') as f:
                for i, segment in enumerate(segments, 1):
                    f.write(f"{i}\n")
                    f.write(f"{format_timestamp(segment.start)} --> {format_timestamp(segment.end)}\n")
                    f.write(f"{segment.text.strip()}\n\n")
            
            print_colored(f"[OK] Trascrizione completata!", Colors.GREEN)
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
        
        print_colored("="*50, Colors.CYAN)
        print_colored("  WHISPER RTX 5080 - PYTHON EDITION", Colors.CYAN)
        print_colored("="*50, Colors.CYAN)
        print()
        print_colored("GPU: NVIDIA RTX 5080 16GB", Colors.GREEN)
        print_colored(f"Compute consigliato: {best_compute or 'CPU'}", Colors.YELLOW)
        print()
        print_colored("="*50, Colors.CYAN)
        print("[1] Trascrivi audio (mantiene lingua)")
        print("[2] Traduci in italiano")
        print("[3] Batch processing")
        print("[4] Test GPU")
        print("[0] Esci")
        print()
        
        choice = input("Scelta [0-4]: ")
        
        if choice == '0':
            print_colored("\nArrivederci!", Colors.CYAN)
            break
            
        elif choice == '1':
            language = input("\nLingua [it/en/es/fr/de/auto]: ") or "auto"
            process_files(input_dir, output_dir, 'transcribe', language, best_compute)
            
        elif choice == '2':
            print_colored("\nTraduzione verso italiano", Colors.CYAN)
            process_files(input_dir, output_dir, 'translate', 'en', best_compute)
            
        elif choice == '3':
            language = input("\nLingua [it/en/es/auto]: ") or "auto"
            batch_process(input_dir, output_dir, 'transcribe', language, best_compute)
            
        elif choice == '4':
            best_compute = test_gpu()
            input("\nPremi INVIO per continuare...")

def process_files(input_dir, output_dir, task, language, compute_type):
    """Processa singolo file"""
    print_colored(f"\nFile disponibili in '{input_dir}':", Colors.CYAN)
    print("="*50)
    
    files = list(input_dir.glob('*.m4a')) + list(input_dir.glob('*.mp3')) + \
            list(input_dir.glob('*.wav')) + list(input_dir.glob('*.mp4'))
    
    if not files:
        print_colored("Nessun file trovato!", Colors.YELLOW)
        input("\nPremi INVIO per continuare...")
        return
    
    for f in files:
        print(f"  {f.name}")
    
    print("="*50)
    filename = input("\nNome file (o INVIO per annullare): ")
    
    if not filename:
        return
    
    input_file = input_dir / filename
    
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
        
        open_file = input("\nAprire il file? [S/N]: ")
        if open_file.lower() == 's':
            if os.name == 'nt':
                os.startfile(result)
            else:
                subprocess.run(['xdg-open', result])
    
    input("\nPremi INVIO per continuare...")

def batch_process(input_dir, output_dir, task, language, compute_type):
    """Batch processing"""
    files = list(input_dir.glob('*.m4a')) + list(input_dir.glob('*.mp3')) + \
            list(input_dir.glob('*.wav')) + list(input_dir.glob('*.mp4'))
    
    if not files:
        print_colored("Nessun file trovato!", Colors.YELLOW)
        input("\nPremi INVIO per continuare...")
        return
    
    print_colored(f"\n[INFO] Processando {len(files)} file...", Colors.CYAN)
    
    success = 0
    failed = 0
    
    for i, file in enumerate(files, 1):
        print_colored(f"\n[{i}/{len(files)}] {file.name}", Colors.YELLOW)
        
        wav_path = convert_to_wav(file, output_dir)
        if not wav_path:
            failed += 1
            continue
        
        result = transcribe_audio(
            wav_path, output_dir,
            task=task,
            language=language,
            compute_type=compute_type or 'float32'
        )
        
        if wav_path.exists():
            wav_path.unlink()
        
        if result:
            success += 1
        else:
            failed += 1
    
    print_colored("\n" + "="*50, Colors.CYAN)
    print_colored("BATCH COMPLETATO", Colors.CYAN)
    print_colored("="*50, Colors.CYAN)
    print(f"Totale: {len(files)}")
    print_colored(f"Successi: {success}", Colors.GREEN)
    print_colored(f"Falliti: {failed}", Colors.RED)
    
    input("\nPremi INVIO per continuare...")

def main():
    """Main entry point"""
    print_colored("""
 ╦ ╦╦ ╦╦╔═╗╔═╗╔═╗╦═╗  ╦═╗╔╦╗═╗ ╦  ╔═╗╔═╗╔╗ ╔═╗
 ║║║╠═╣║╚═╗╠═╝║╣ ╠╦╝  ╠╦╝ ║ ╔╩╦╝  ╚═╗║ ║╠╩╗║ ║
 ╚╩╝╩ ╩╩╚═╝╩  ╚═╝╩╚═  ╩╚═ ╩ ╩ ╚═  ╚═╝╚═╝╚═╝╚═╝
 
 Python Edition - FREE & FAST
 Ottimizzato per NVIDIA RTX 5080 16GB
    """, Colors.CYAN)
    
    if not check_dependencies():
        print_colored("\n[ERROR] Risolvi i problemi di dipendenze!", Colors.RED)
        input("\nPremi INVIO per uscire...")
        return
    
    print_colored("\n[OK] Sistema pronto!", Colors.GREEN)
    input("\nPremi INVIO per continuare...")
    
    interactive_menu()

if __name__ == "__main__":
    main()
