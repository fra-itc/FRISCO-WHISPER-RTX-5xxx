# FRISCO WHISPER RTX 5xxx

![Version](https://img.shields.io/badge/version-1.2-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-green.svg)
![CUDA](https://img.shields.io/badge/CUDA-12.1+-orange.svg)
![License](https://img.shields.io/badge/license-MIT-brightgreen.svg)

**Trascrizione e traduzione audio AI ottimizzata per GPU NVIDIA RTX 5xxx**

Strumento professionale di trascrizione audio basato su OpenAI Whisper con accelerazione CUDA, specificamente ottimizzato per le GPU NVIDIA RTX serie 5000 (RTX 5080, RTX 5090).

## Caratteristiche

### Funzionalità Core
- **Trascrizione audio** in formato SRT (sottotitoli)
- **Traduzione automatica** verso italiano
- **Rilevamento automatico** della lingua sorgente
- **Batch processing** per elaborare più file contemporaneamente
- **Supporto multi-formato**: M4A, MP3, WAV, MP4, AAC, FLAC

### Ottimizzazioni RTX 5xxx
- **CUDA float16** per prestazioni ottimali su architettura Ada Lovelace
- **Fallback automatici**: int8, float32, CPU se necessario
- **Faster-Whisper** nativo Python (più veloce dell'eseguibile originale)
- **VAD (Voice Activity Detection)** per migliore accuratezza

### Esperienza Utente (v1.2)
- **Progress bar in tempo reale** durante conversione audio
- **Progress bar per trascrizione** con conteggio segmenti
- **Stima tempo rimanente** durante elaborazione batch
- **Menu interattivo** con ASCII art personalizzato
- **Auto-detection** dipendenze con installazione automatica

## Requisiti di Sistema

### Hardware
- **GPU**: NVIDIA RTX 5080/5090 (16-24GB VRAM) - raccomandato
- **CPU**: Qualsiasi processore moderno (fallback se GPU non disponibile)
- **RAM**: 8GB minimo, 16GB raccomandato
- **Spazio**: ~5GB per modelli AI

### Software
- **Python**: 3.8 o superiore
- **CUDA Toolkit**: 12.1 o superiore
- **ffmpeg**: Per conversione audio
- **Sistema operativo**: Windows 10/11, Linux (Ubuntu 20.04+)

## Installazione

### 1. Clona il repository
```bash
git clone https://github.com/fra-itc/FRISCO-WHISPER-RTX-5xxx.git
cd FRISCO-WHISPER-RTX-5xxx
```

### 2. Installa ffmpeg

**Windows:**
- Scarica da [ffmpeg.org](https://ffmpeg.org/download.html)
- Aggiungi al PATH di sistema

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

### 3. Esegui il programma
Il programma installerà automaticamente le dipendenze Python al primo avvio:
```bash
python3 whisper_transcribe_frisco.py
```

Le seguenti librerie verranno installate automaticamente:
- `torch` (con supporto CUDA 12.1)
- `faster-whisper`
- `ffmpeg-python`
- `tqdm`

## Utilizzo

### Avvio
```bash
python3 whisper_transcribe_frisco.py
```

### Menu Principale
```
═══════════════════════════════════════════════════
  FRISCO WHISPER RTX 5080 [RULEZ] - Python Edition
═══════════════════════════════════════════════════

[1] Trascrivi audio (mantiene lingua)
[2] Traduci in italiano
[3] Batch processing
[4] Test GPU
[0] Esci
```

### Modalità d'uso

#### 1. Trascrizione Singola
- Seleziona opzione `[1]`
- Scegli la lingua (o INVIO per auto-detect)
- Posiziona i file audio nella cartella `audio/`
- Seleziona il file da trascrivere
- Output: file `.srt` in `transcripts/`

**Esempio:**
```
Lingua [it/en/es/fr/de o INVIO per auto-detect]: en
[1/3] Conversione in WAV...
Conversione: 100%|████████████████| 00:12<00:00
[2/3] Trascrizione...
Trascrizione: 100%|████████████████| 142seg [02:15, 1.05seg/s]
[OK] Trascrizione completata! (142 segmenti)
```

#### 2. Traduzione in Italiano
- Seleziona opzione `[2]`
- Trascrizione + traduzione automatica verso italiano
- Utile per contenuti in lingua straniera

#### 3. Batch Processing
- Seleziona opzione `[3]`
- Elabora automaticamente tutti i file nella cartella `audio/`
- Mostra progresso complessivo e tempo stimato
- Ideale per grandi quantità di audio

**Output batch:**
```
[INFO] Trovati 5 file da processare
[1/5] conferenza.mp3
Tempo stimato rimanente: 15m 30s
...
BATCH COMPLETATO
Successi: 5
Tempo totale: 12m 45s
```

#### 4. Test GPU
- Seleziona opzione `[4]`
- Verifica CUDA e compute types supportati
- Raccomanda la configurazione ottimale

## Struttura Cartelle

```
FRISCO-WHISPER-RTX-5xxx/
├── audio/              # Input: file audio da trascrivere
├── transcripts/        # Output: file SRT generati
├── logs/               # Log di elaborazione
├── whisper_transcribe_frisco.py  # Script principale
├── README.md           # Questa documentazione
└── .gitignore          # File ignorati da git
```

## Formati Supportati

### Input Audio
- `.m4a` - Audio AAC (iPhone, registratori)
- `.mp3` - MP3 (universale)
- `.wav` - WAV non compresso
- `.mp4` - Video MP4 (estrae audio)
- `.aac` - Audio AAC grezzo
- `.flac` - Audio lossless

### Output
- `.srt` - Sottotitoli (formato SubRip)
- Encoding UTF-8
- Timestamp formato: `HH:MM:SS,mmm`

## Parametri Avanzati

### Modelli Whisper Disponibili
- `tiny` - Veloce, meno accurato (~1GB VRAM)
- `base` - Bilanciato (~1GB VRAM)
- `small` - Buona qualità (~2GB VRAM)
- `medium` - Alta qualità (~5GB VRAM) - **default**
- `large` - Massima qualità (~10GB VRAM)

### Compute Types
1. **float16** - Ottimale per RTX 5xxx (velocità + accuratezza)
2. **int8** - Massima velocità, accuratezza leggermente ridotta
3. **float32** - Compatibilità universale, più lento

### Parametri Trascrizione
```python
beam_size=5              # Qualità beam search
vad_filter=True          # Filtro Voice Activity Detection
temperature=0.0          # Determinismo (0.0 = massimo)
condition_on_previous_text=True  # Contesto frasi precedenti
```

## Changelog

### v1.2 (2025-11-19)
- **Aggiunta progress bar per conversione WAV** con percentuale e tempo rimanente
- **Aggiunta progress bar per trascrizione** con conteggio segmenti
- Integrazione libreria `tqdm` per feedback visivo
- Uso di `ffprobe` per calcolo durata preciso
- Migliorata esperienza utente durante elaborazione
- Aggiunto `.gitignore` per file Python

### v1.1 (2025-11-18)
- Supporto auto-detection lingua (None = auto)
- Selezione automatica file se solo uno disponibile
- Migliorati messaggi di log colorati
- ASCII art branding "RULEZ"

### v1.0 (2025-11-17)
- Release iniziale
- Supporto RTX 5080 con float16
- Menu interattivo
- Batch processing
- Test GPU automatico

## Troubleshooting

### GPU non rilevata
```bash
# Verifica CUDA
python3 -c "import torch; print(torch.cuda.is_available())"

# Reinstalla PyTorch con CUDA
pip install torch --index-url https://download.pytorch.org/whl/cu121
```

### ffmpeg non trovato
```bash
# Linux
sudo apt install ffmpeg

# Windows: aggiungi ffmpeg.exe al PATH
# macOS
brew install ffmpeg
```

### Out of Memory (VRAM)
- Usa modello più piccolo: `small` invece di `medium`
- Chiudi altre applicazioni che usano la GPU
- Prova compute type `int8` invece di `float16`

### Trascrizione lenta
- Verifica che CUDA sia attivo (opzione `[4]` Test GPU)
- Usa `int8` per velocità massima
- Riduci `beam_size` da 5 a 3

## Performance

### Benchmark RTX 5080 (16GB VRAM)
| Durata Audio | Modello  | Compute | Tempo Trascrizione |
|--------------|----------|---------|-------------------|
| 1 minuto     | medium   | float16 | ~8 secondi        |
| 10 minuti    | medium   | float16 | ~1.5 minuti       |
| 1 ora        | medium   | float16 | ~9 minuti         |

*Note: i tempi variano in base alla qualità audio e lingua*

## Lingue Supportate

Auto-detection supporta **99 lingue**, incluse:
- Italiano, Inglese, Spagnolo, Francese, Tedesco
- Cinese, Giapponese, Coreano, Russo, Arabo
- Portoghese, Olandese, Polacco, Turco, Svedese
- E molte altre...

## Contributi

Contributi benvenuti! Per favore:
1. Fai fork del repository
2. Crea un branch per la feature (`git checkout -b feature/nuova-funzione`)
3. Commit le modifiche (`git commit -am 'Aggiungi nuova funzione'`)
4. Push al branch (`git push origin feature/nuova-funzione`)
5. Apri una Pull Request

## Licenza

MIT License - vedi file LICENSE per dettagli

## Credits

- **OpenAI Whisper** - Modello AI di trascrizione
- **Faster-Whisper** - Implementazione ottimizzata CTranslate2
- **NVIDIA CUDA** - Accelerazione GPU
- **FFmpeg** - Conversione audio

## Supporto

Per bug, feature request o domande:
- Apri una [Issue](https://github.com/fra-itc/FRISCO-WHISPER-RTX-5xxx/issues)
- Contatta: fra-itc

---

**Made with ❤️ for RTX 5xxx series**

*FRISCO WHISPER - RULEZ!!!*
