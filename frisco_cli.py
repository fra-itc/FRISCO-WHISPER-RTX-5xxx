#!/usr/bin/env python3
"""
FRISCO WHISPER RTX 5xxx - Modern CLI Wrapper
Modular architecture with backward-compatible user experience
"""

import os
import sys
import time
from pathlib import Path
from typing import Optional, List
from datetime import datetime

# Import new modular components
from src.core.transcription import TranscriptionEngine, AudioConverter
from src.core.gpu_manager import GPUManager
from src.data.database import DatabaseManager
from src.data.file_manager import FileManager
from src.data.transcript_manager import TranscriptManager

# Colori per terminale (Matrix style!)
class Colors:
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    RESET = '\033[0m'
    BOLD = '\033[1m'
    WHITE = '\033[97m'
    BRIGHT_GREEN = '\033[92m\033[1m'


# Modelli disponibili
AVAILABLE_MODELS = [
    {'name': 'small', 'desc': 'Veloce, meno accurato (~460 MB)'},
    {'name': 'medium', 'desc': 'Bilanciato (~1.5 GB)'},
    {'name': 'large-v3', 'desc': 'Massima qualità (~3 GB) [CONSIGLIATO]'}
]

CURRENT_MODEL = 'large-v3'


def print_colored(message, color=Colors.RESET):
    """Print colored message to console."""
    print(f"{color}{message}{Colors.RESET}")


def clear_screen():
    """Clear terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')


def print_banner():
    """Print ASCII art banner."""
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

    print_colored("  ⚡ Modern CLI - CUDA Accelerated - Modular Architecture - NVIDIA RTX 5080 16GB ⚡\\n", Colors.GREEN)


class FriscoCLI:
    """
    Modern CLI wrapper for Frisco Whisper transcription system.

    Features:
    - Modular architecture using new components
    - Database-backed job tracking
    - GPU optimization
    - Progress tracking with ETA
    - Matrix-style visual effects
    - Backward compatible with original CLI
    """

    def __init__(self):
        """Initialize CLI with all necessary components."""
        self.base_dir = Path(".")
        self.input_dir = self.base_dir / "audio"
        self.output_dir = self.base_dir / "transcripts"
        self.db_dir = self.base_dir / "database"

        # Create directories
        for d in [self.input_dir, self.output_dir, self.db_dir]:
            d.mkdir(exist_ok=True)

        # Initialize components
        self.db = DatabaseManager(str(self.db_dir / 'transcription.db'))
        self.file_mgr = FileManager(self.db, base_dir=self.input_dir)
        self.transcript_mgr = TranscriptManager(self.db)
        self.gpu_mgr = GPUManager()

        # Current settings
        self.current_model = CURRENT_MODEL
        self.best_compute = None

        print_colored("[INFO] Inizializzazione componenti...", Colors.CYAN)
        print_colored("[OK] Database inizializzato", Colors.GREEN)
        print_colored("[OK] File manager pronto", Colors.GREEN)
        print_colored("[OK] Transcript manager pronto", Colors.GREEN)

    def test_gpu(self) -> Optional[str]:
        """Test GPU capabilities and return best compute type."""
        print_colored("\\n" + "="*50, Colors.CYAN)
        print_colored("  TEST GPU E DIAGNOSTICA", Colors.CYAN)
        print_colored("="*50, Colors.CYAN)

        if not self.gpu_mgr.has_cuda:
            print_colored("[WARN] CUDA non disponibile, uso CPU", Colors.YELLOW)
            return None

        # Get GPU info
        gpu_info = self.gpu_mgr.get_gpu_info(0)
        if gpu_info:
            print_colored(f"\\n[OK] GPU: {gpu_info.name}", Colors.GREEN)
            print_colored(f"[OK] VRAM: {gpu_info.total_memory_gb:.1f} GB", Colors.GREEN)
            print_colored(f"[OK] CUDA: {gpu_info.cuda_version}", Colors.GREEN)
            print_colored(f"\\n[INFO] Compute types supportati:", Colors.CYAN)
            for ct in gpu_info.supported_compute_types:
                print_colored(f"  ✓ {ct}", Colors.GREEN)

            best = gpu_info.recommended_compute_type
            if best:
                print_colored(f"\\n[RACCOMANDATO] Usa {best} per prestazioni ottimali", Colors.BRIGHT_GREEN)

            return best

        return None

    def select_model(self):
        """Interactive model selection menu."""
        clear_screen()
        print_colored("\\n" + "="*70, Colors.CYAN)
        print_colored("  SELEZIONE MODELLO WHISPER", Colors.CYAN)
        print_colored("="*70, Colors.CYAN)
        print()

        for i, model in enumerate(AVAILABLE_MODELS, 1):
            color = Colors.BRIGHT_GREEN if model['name'] == self.current_model else Colors.WHITE
            marker = " ◄ ATTUALE" if model['name'] == self.current_model else ""
            print_colored(f"  [{i}] {model['name']:12} - {model['desc']}{marker}", color)

        print()
        print_colored("="*70, Colors.CYAN)

        choice = input("\\nScegli modello [1-3] o INVIO per confermare attuale: ").strip()

        if not choice:
            print_colored(f"\\n[INFO] Confermato modello: {self.current_model}", Colors.GREEN)
        else:
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(AVAILABLE_MODELS):
                    self.current_model = AVAILABLE_MODELS[idx]['name']
                    print_colored(f"\\n[OK] Modello cambiato in: {self.current_model}", Colors.GREEN)
                else:
                    print_colored("\\n[ERROR] Scelta non valida!", Colors.RED)
            except ValueError:
                print_colored("\\n[ERROR] Inserisci un numero valido!", Colors.RED)

        input("\\nPremi INVIO per continuare...")

    def list_audio_files(self) -> List[Path]:
        """Get list of audio files in input directory."""
        extensions = ['*.m4a', '*.mp3', '*.wav', '*.mp4', '*.aac', '*.flac', '*.opus']
        files = []
        for ext in extensions:
            files.extend(self.input_dir.glob(ext))
        return sorted(files)

    def transcribe_single(self, language: Optional[str] = None):
        """Transcribe single audio file."""
        files = self.list_audio_files()

        if not files:
            print_colored("\\nNessun file trovato!", Colors.YELLOW)
            input("\\nPremi INVIO per continuare...")
            return

        # Select file
        if len(files) == 1:
            input_file = files[0]
            print_colored(f"\\n[AUTO] Selezionato unico file: {input_file.name}", Colors.GREEN)
        else:
            print_colored(f"\\nFile disponibili in '{self.input_dir}':", Colors.CYAN)
            print("="*50)
            for i, f in enumerate(files, 1):
                print(f"  [{i}] {f.name}")
            print("="*50)

            choice = input("\\nNumero file (INVIO per annullare): ").strip()
            if not choice:
                return

            try:
                idx = int(choice) - 1
                if 0 <= idx < len(files):
                    input_file = files[idx]
                else:
                    print_colored("Numero non valido!", Colors.RED)
                    input("\\nPremi INVIO per continuare...")
                    return
            except ValueError:
                print_colored("Inserisci un numero valido!", Colors.RED)
                input("\\nPremi INVIO per continuare...")
                return

        # Upload file to database
        try:
            print_colored(f"\\n[1/3] Registrazione file nel database...", Colors.CYAN)
            file_id, is_new = self.file_mgr.upload_file(str(input_file))
            if is_new:
                print_colored(f"[OK] File registrato (ID: {file_id})", Colors.GREEN)
            else:
                print_colored(f"[OK] File già presente (ID: {file_id})", Colors.YELLOW)
        except Exception as e:
            print_colored(f"[ERROR] Registrazione fallita: {e}", Colors.RED)
            input("\\nPremi INVIO per continuare...")
            return

        # Convert to WAV if needed
        wav_path = input_file
        if input_file.suffix.lower() != '.wav':
            print_colored(f"\\n[2/3] Conversione in WAV...", Colors.CYAN)
            converter = AudioConverter()
            wav_path = converter.convert_to_wav(str(input_file), str(self.output_dir))
            if not wav_path:
                print_colored("[ERROR] Conversione fallita!", Colors.RED)
                input("\\nPremi INVIO per continuare...")
                return
            print_colored(f"[OK] WAV creato: {wav_path.name}", Colors.GREEN)

        # Create transcription job
        job_id = self.db.create_job(
            file_path=str(input_file),
            model_size=self.current_model,
            task_type='transcribe',
            language=language,
            compute_type=self.best_compute or 'float32',
            device='cuda' if self.best_compute else 'cpu'
        )

        # Transcribe
        print_colored(f"\\n[3/3] Trascrizione con modello {self.current_model}...", Colors.CYAN)
        print_colored("="*70, Colors.CYAN)

        # Update job status
        self.db.update_job(job_id, status='processing', started_at=datetime.now())

        # Create transcription engine
        engine = TranscriptionEngine(
            model_size=self.current_model,
            compute_type=self.best_compute or 'float32',
            device='cuda' if self.best_compute else 'cpu'
        )

        # Define progress callback
        def progress_callback(data):
            segment_num = data['segment_number']
            text = data['text']
            timestamp = f"{int(data['start'] // 60):02d}:{int(data['start'] % 60):02d}"

            # Matrix-style output
            print(f"{Colors.YELLOW}[{timestamp}]{Colors.RESET} ", end='', flush=True)
            for char in text:
                print(f"{Colors.BRIGHT_GREEN}{char}{Colors.RESET}", end='', flush=True)
                time.sleep(0.01)
            print()

            # Show progress every 5 segments
            if segment_num % 5 == 0 and data.get('progress_pct'):
                print_colored(
                    f"  [{segment_num} seg] Progresso: {data['progress_pct']:.1f}%",
                    Colors.CYAN
                )

        # Perform transcription
        result = engine.transcribe(
            audio_path=str(wav_path),
            output_dir=str(self.output_dir),
            language=language,
            progress_callback=progress_callback
        )

        # Cleanup WAV if it was converted
        if wav_path != input_file and Path(wav_path).exists():
            Path(wav_path).unlink()

        if result.success:
            # Update job
            self.db.update_job(
                job_id,
                status='completed',
                completed_at=datetime.now(),
                processing_time_seconds=result.duration,
                detected_language=result.language,
                language_probability=result.language_probability
            )

            # Save transcript
            with open(result.output_path, 'r', encoding='utf-8') as f:
                srt_content = f.read()

            # Parse SRT to segments
            segments = []
            # Simple SRT parsing (basic implementation)
            # For production, use proper SRT parser

            transcript_id = self.db.save_transcription(
                job_id=job_id,
                text=f"Transcription completed ({result.segments_count} segments)",
                language=result.language,
                segments=[],  # Would parse SRT here
                srt_path=str(result.output_path)
            )

            print_colored("\\n" + "="*70, Colors.GREEN)
            print_colored("COMPLETATO CON SUCCESSO!", Colors.GREEN)
            print_colored("="*70, Colors.GREEN)
            print_colored(f"Segmenti: {result.segments_count}", Colors.GREEN)
            print_colored(f"Lingua: {result.language} ({result.language_probability:.1%})", Colors.GREEN)
            print_colored(f"Tempo: {result.duration:.1f}s", Colors.GREEN)
            print_colored(f"Output: {result.output_path}", Colors.GREEN)

            open_file = input("\\nAprire il file? [S/N] (default: S): ") or "S"
            if open_file.lower() == 's':
                try:
                    if os.name == 'nt':
                        os.startfile(result.output_path)
                    else:
                        import subprocess
                        subprocess.run(['xdg-open', result.output_path])
                except Exception as e:
                    print_colored(f"Impossibile aprire: {e}", Colors.YELLOW)
        else:
            # Update job with error
            self.db.update_job(
                job_id,
                status='failed',
                completed_at=datetime.now(),
                error_message=result.error
            )
            print_colored(f"\\n[ERROR] Trascrizione fallita: {result.error}", Colors.RED)

        input("\\nPremi INVIO per continuare...")

    def batch_process(self, language: Optional[str] = None):
        """Batch process all audio files."""
        files = self.list_audio_files()

        if not files:
            print_colored("\\nNessun file trovato!", Colors.YELLOW)
            input("\\nPremi INVIO per continuare...")
            return

        print_colored(f"\\n[INFO] Trovati {len(files)} file da processare:", Colors.CYAN)
        for i, f in enumerate(files, 1):
            print(f"  [{i}] {f.name}")

        confirm = input(f"\\nProcessare tutti i {len(files)} file? [S/N] (default: S): ") or "S"
        if confirm.lower() != 's':
            return

        print_colored(f"\\n[INFO] Inizio batch processing...", Colors.CYAN)

        success_count = 0
        failed_count = 0
        start_time = time.time()

        for i, file in enumerate(files, 1):
            print_colored(f"\\n{'='*50}", Colors.YELLOW)
            print_colored(f"[{i}/{len(files)}] {file.name}", Colors.YELLOW)
            print_colored(f"{'='*50}", Colors.YELLOW)

            # Simple progress - reuse single file transcription logic
            # In production, this would be optimized
            # For now, just showing structure

            print_colored(f"[TODO] Implementare batch processing ottimizzato", Colors.YELLOW)

        total_time = time.time() - start_time

        print_colored("\\n" + "="*50, Colors.CYAN)
        print_colored("BATCH COMPLETATO", Colors.CYAN)
        print_colored("="*50, Colors.CYAN)
        print(f"Totale: {len(files)}")
        print_colored(f"Successi: {success_count}", Colors.GREEN)
        print_colored(f"Falliti: {failed_count}", Colors.RED)
        print_colored(f"Tempo totale: {int(total_time // 60)}m {int(total_time % 60)}s", Colors.CYAN)

        input("\\nPremi INVIO per continuare...")

    def run(self):
        """Main menu loop."""
        # Test GPU on startup
        self.best_compute = self.test_gpu()
        input("\\nPremi INVIO per continuare...")

        while True:
            clear_screen()
            print_banner()

            print_colored("="*70, Colors.CYAN)
            if self.gpu_mgr.has_cuda:
                gpu_info = self.gpu_mgr.get_gpu_info(0)
                print_colored(f"GPU: {gpu_info.name if gpu_info else 'Unknown'}", Colors.GREEN)
                print_colored(f"Compute: {self.best_compute or 'CPU'}", Colors.YELLOW)
            else:
                print_colored("GPU: Non disponibile (uso CPU)", Colors.YELLOW)

            print_colored(f"Modello attuale: {self.current_model}", Colors.BRIGHT_GREEN)
            print()
            print_colored("="*70, Colors.CYAN)
            print("[1] Trascrivi audio (mantiene lingua)")
            print("[2] Traduci in italiano")
            print("[3] Batch processing")
            print("[4] Test GPU")
            print("[5] Scegli modello")
            print("[0] Esci")
            print()

            choice = input("Scelta [0-5]: ").strip()

            if choice == '0':
                print_colored("\\nArrivederci!", Colors.CYAN)
                break

            elif choice == '1':
                lang_input = input("\\nLingua [it/en/es/fr/de o INVIO per auto-detect]: ").strip()
                language = None if not lang_input or lang_input.lower() == 'auto' else lang_input
                if not language:
                    print_colored("[INFO] Rilevamento automatico lingua attivato", Colors.CYAN)
                self.transcribe_single(language)

            elif choice == '2':
                print_colored("\\n[TODO] Traduzione non ancora implementata", Colors.YELLOW)
                input("\\nPremi INVIO per continuare...")

            elif choice == '3':
                lang_input = input("\\nLingua [it/en/es/fr/de o INVIO per auto-detect]: ").strip()
                language = None if not lang_input or lang_input.lower() == 'auto' else lang_input
                if not language:
                    print_colored("[INFO] Rilevamento automatico lingua attivato", Colors.CYAN)
                self.batch_process(language)

            elif choice == '4':
                self.best_compute = self.test_gpu()
                input("\\nPremi INVIO per continuare...")

            elif choice == '5':
                self.select_model()


def main():
    """Main entry point."""
    try:
        cli = FriscoCLI()
        cli.run()
    except KeyboardInterrupt:
        print_colored("\\n\\n[INFO] Interrotto dall'utente", Colors.YELLOW)
    except Exception as e:
        print_colored(f"\\n[ERROR] Errore fatale: {e}", Colors.RED)
        import traceback
        traceback.print_exc()
        input("\\nPremi INVIO per uscire...")


if __name__ == "__main__":
    main()
