# FFmpeg Setup Guide - Local Installation

**FRISCO WHISPER RTX 5xxx** - Automatic FFmpeg Download & Configuration

---

## 🎯 Quick Start

Il progetto ora include un sistema automatico per scaricare e configurare ffmpeg localmente nella cartella del progetto. **Non serve più installazione di sistema!**

### Installazione Automatica (Raccomandato)

```bash
# Scarica e installa ffmpeg localmente
python setup_ffmpeg.py

# Verifica installazione
python setup_ffmpeg.py --verify
```

### Cosa Fa lo Script

1. **Rileva la piattaforma** (Linux x64/arm64, Windows, macOS)
2. **Scarica ffmpeg** dalla fonte ufficiale più recente
3. **Estrae i binari** nella cartella `bin/`
4. **Verifica funzionamento** con test automatico
5. **Configura AudioProcessor** per usare i binari locali

---

## 📋 Comandi Disponibili

### Download e Installazione
```bash
# Installazione normale
python setup_ffmpeg.py

# Forza re-download (anche se già presente)
python setup_ffmpeg.py --force

# Solo verifica (non scarica)
python setup_ffmpeg.py --verify

# Pulisci file temporanei
python setup_ffmpeg.py --cleanup
```

---

## 🔍 Come Funziona

### 1. Rilevamento Automatico

Lo script rileva automaticamente:
- Sistema operativo (Linux, Windows, macOS)
- Architettura (x64, arm64)
- Versione ffmpeg appropriata

### 2. Download Intelligente

Scarica da fonti ufficiali:
- **Linux**: [johnvansickle.com](https://johnvansickle.com/ffmpeg/) (static builds)
- **Windows**: [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) (essentials)
- **macOS**: [evermeet.cx](https://evermeet.cx/ffmpeg/) (latest)

### 3. Installazione Locale

```
FRISCO-WHISPER-RTX-5xxx/
├── bin/                    # ← Binari ffmpeg locali
│   ├── ffmpeg              # ← Eseguibile ffmpeg
│   └── ffprobe             # ← Eseguibile ffprobe
├── downloads/              # ← Download temporanei (auto-cleanup)
├── setup_ffmpeg.py         # ← Script di setup
└── ...
```

### 4. Integrazione AudioProcessor

`AudioProcessor` cerca i binari in questo ordine:

1. **Prima**: `bin/ffmpeg` e `bin/ffprobe` (locale)
2. **Poi**: `ffmpeg` e `ffprobe` nel PATH (sistema)

```python
from src.core.audio_processor import AudioProcessor

# AudioProcessor cerca automaticamente ffmpeg locale
processor = AudioProcessor()

if processor._ffmpeg_available:
    print(f"✅ FFmpeg trovato: {processor.ffmpeg_path}")
else:
    print("❌ FFmpeg non disponibile")
```

---

## 🌐 Supporto Multi-Piattaforma

### Linux (x64 / arm64)
- **Download**: Static build da johnvansickle.com
- **Formato**: tar.xz
- **Dimensione**: ~70 MB
- **Versione**: Latest release

### Windows (x64)
- **Download**: Essentials build da gyan.dev
- **Formato**: ZIP
- **Dimensione**: ~90 MB
- **Versione**: Latest release

### macOS (x64 / arm64)
- **Download**: Static build da evermeet.cx
- **Formato**: ZIP
- **Dimensione**: ~60 MB
- **Versione**: 6.1+

---

## ✅ Verifica Installazione

### Test Rapido
```bash
python setup_ffmpeg.py --verify
```

**Output atteso**:
```
🔍 Verifying installation...
   ✅ ffmpeg: ffmpeg version 6.1 Copyright (c) 2000-2023 the FFmpeg developers
   ✅ ffprobe: ffprobe version 6.1 Copyright (c) 2000-2023 the FFmpeg developers
```

### Test Python
```python
from src.core.audio_processor import AudioProcessor

ap = AudioProcessor()
print(f"FFmpeg disponibile: {ap._ffmpeg_available}")
print(f"Percorso ffmpeg: {ap.ffmpeg_path}")
print(f"Percorso ffprobe: {ap.ffprobe_path}")

# Test conversione OPUS
if ap._ffmpeg_available:
    metadata = ap.detect_format('audio/file.opus')
    print(f"Formato: {metadata.format}")
    print(f"Durata: {metadata.duration}s")
```

---

## 🔧 Troubleshooting

### Problema: Download fallisce

**Soluzione 1 - Proxy/Firewall**:
```bash
# Controlla connessione
curl -I https://johnvansickle.com/ffmpeg/
```

**Soluzione 2 - Download manuale**:
1. Scarica da [johnvansickle.com/ffmpeg/releases/](https://johnvansickle.com/ffmpeg/releases/)
2. Estrai nella cartella `bin/`
3. Rendi eseguibili (Linux/macOS): `chmod +x bin/ffmpeg bin/ffprobe`

### Problema: "Permission denied" (Linux/macOS)

```bash
# Rendi eseguibili i binari
chmod +x bin/ffmpeg bin/ffprobe

# Verifica
./bin/ffmpeg -version
```

### Problema: Binari non funzionano

```bash
# Forza re-download
python setup_ffmpeg.py --force

# Verifica piattaforma
python -c "import platform; print(platform.system(), platform.machine())"
```

### Problema: Spazio insufficiente

I binari occupano ~70-90 MB. Se serve spazio:

```bash
# Rimuovi download temporanei
python setup_ffmpeg.py --cleanup

# Usa installazione di sistema invece
sudo apt install ffmpeg  # Linux
brew install ffmpeg      # macOS
```

---

## 🆚 Installazione Locale vs Sistema

### Locale (Raccomandato)

**Vantaggi**:
- ✅ No permessi root/admin
- ✅ Versione specifica garantita
- ✅ Isolamento da altre applicazioni
- ✅ Portabile con progetto
- ✅ Sempre aggiornato allo stesso modo

**Svantaggi**:
- ❌ ~70-90 MB per progetto
- ❌ Non condiviso con altri programmi

### Sistema

**Vantaggi**:
- ✅ Condiviso tra applicazioni
- ✅ Gestito dal package manager

**Svantaggi**:
- ❌ Richiede permessi admin
- ❌ Versione dipende dalla distro
- ❌ Potrebbe mancare su alcuni sistemi

---

## 📦 Aggiornamento FFmpeg

### Aggiorna Versione Locale
```bash
# Forza re-download versione più recente
python setup_ffmpeg.py --force
```

### Controlla Versione
```bash
./bin/ffmpeg -version | head -1
```

---

## 🔐 Sicurezza

### Download sicuri da fonti ufficiali:

- **Linux**: johnvansickle.com - Trusted static builds dal 2012
- **Windows**: gyan.dev - Official FFmpeg builds
- **macOS**: evermeet.cx - Official macOS builds

### Verifica manuale (opzionale):

```bash
# Controlla checksum
sha256sum bin/ffmpeg

# Confronta con hash ufficiale dalla fonte
```

---

## 🚀 Integrazione CI/CD

### GitHub Actions

```yaml
name: Setup

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup FFmpeg
        run: python setup_ffmpeg.py

      - name: Verify FFmpeg
        run: python setup_ffmpeg.py --verify

      - name: Run Tests
        run: pytest tests/
```

### Docker

```dockerfile
FROM python:3.10

WORKDIR /app
COPY . .

# Installa dipendenze Python
RUN pip install -r requirements.txt

# Setup FFmpeg locale
RUN python setup_ffmpeg.py

# Verifica
RUN python setup_ffmpeg.py --verify

CMD ["python", "src/ui/web_server.py"]
```

---

## 📊 Comparazione Metodi

| Metodo | Tempo Setup | Spazio | Permessi | Portabilità |
|--------|-------------|---------|----------|-------------|
| `setup_ffmpeg.py` | ~30s | 70-90 MB | No root | ✅ Alta |
| `apt install` | ~10s | ~50 MB | Root | ❌ Bassa |
| `brew install` | ~1m | ~60 MB | Admin | ❌ Bassa |
| Download manuale | ~5m | Variabile | No root | ⚠️ Media |

---

## 🎓 FAQ

**Q: Posso usare ffmpeg di sistema invece?**
A: Sì, AudioProcessor lo usa automaticamente se non trova i binari locali.

**Q: I binari vanno in git?**
A: No, `bin/` è in `.gitignore`. Ogni sviluppatore esegue `setup_ffmpeg.py`.

**Q: Funziona offline?**
A: No per il download iniziale. Poi sì, i binari sono locali.

**Q: Quanto spazio occupa?**
A: ~70-90 MB per i binari, ~100 MB durante download (poi rimosso).

**Q: È sicuro?**
A: Sì, scarica solo da fonti ufficiali FFmpeg.

**Q: Posso usare una versione specifica?**
A: Lo script scarica la latest. Per versioni specifiche, modifica `FFMPEG_URLS` in `setup_ffmpeg.py`.

---

## 📞 Supporto

### Problemi con setup_ffmpeg.py

1. Controlla log completo: `python setup_ffmpeg.py 2>&1 | tee setup.log`
2. Verifica piattaforma supportata
3. Testa download manuale dalla URL mostrata
4. Apri issue su GitHub con il log

### Problemi con AudioProcessor

```python
# Debug info
from src.core.audio_processor import AudioProcessor
import logging

logging.basicConfig(level=logging.DEBUG)
ap = AudioProcessor()
```

---

## 🎉 Conclusione

Con `setup_ffmpeg.py` non devi più:
- ❌ Installare ffmpeg manualmente sul sistema
- ❌ Configurare PATH
- ❌ Preoccuparti di versioni diverse
- ❌ Richiedere permessi admin

**Basta un comando**: `python setup_ffmpeg.py` 🚀

---

**Created**: 2025-11-21
**Version**: 1.0
**Maintainer**: FRISCO WHISPER RTX 5xxx Team
