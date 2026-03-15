# 🌳 Arrel AI

> **Estació de Treball d'IA Local** per investigació científica amb RAG automàtic, sandbox persistent i loops d'execució iteratius.

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)
![React](https://img.shields.io/badge/React-18-61dafb?logo=react)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)
![License](https://img.shields.io/badge/License-MIT-green)

---

## ✨ Característiques

- **🔒 100% Local** - Cap dada surt del teu ordinador, zero dependències cloud
- **📚 RAG Automàtic** - File watcher que indexa documents (PDF, DOCX, CSV) automàticament
- **🧪 Sandbox Persistent** - Kernel de Python que manté variables entre execucions (estil Jupyter)
- **🔬 Research Mode** - Loops iteratius amb auto-correcció i verificació obligatòria
- **🤖 Multi-Model** - Swapping intel·ligent entre models especialitzats (ciència, programació, visió)
- **💭 Self-Reflection** - El model analitza críticament els seus propis resultats
- **⚡ Reranking** - Pipeline de dos estadis (retrieval + reranking) per màxima precisió RAG

---

## 🎯 Casos d'Ús

- **Investigació científica** amb anàlisi de dades
- **Exploració de datasets** amb visualitzacions interactives
- **Programació assistida** amb execució de codi en temps real
- **Anàlisi de documents** (articles, papers, reports) amb context automàtic
- **Processament d'imatges** amb models de visió locals

---

## 🔧 Requisits del Sistema

- **Python** 3.11 o superior
- **Node.js** 18+ i npm
- **[Ollama](https://ollama.ai)** instal·lat i executant-se
- **GPU amb 6GB+ VRAM** (RTX 3060 o superior recomanat)
- **~15GB d'espai lliure** per models

---

## 📦 Instal·lació

### 1️⃣ Clona el repositori

```bash
git clone https://github.com/biesro/ArrelAI.git
cd ArrelAI
```

### 2️⃣ Configura el Backend

```bash
cd backend

# Crea un entorn virtual (recomanat)
python -m venv venv

# Activa l'entorn virtual
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Instal·la dependencies
pip install -r requirements.txt

# Configura variables d'entorn
cp .env.example .env
# Edita .env i ajusta WATCH_FOLDER amb el teu path
```

### 3️⃣ Baixa els Models d'Ollama

```bash
ollama pull qwen3:8b
ollama pull qwen2.5-coder:7b
ollama pull qwen3-vl:4b
ollama pull qwen3-embedding:0.6b
```

**Nota**: La primera vegada trigarà ~10-15 minuts (són ~15GB totals).

### 4️⃣ Configura el Frontend

```bash
cd ../frontend
npm install
```

---

## 🚀 Ús

### Arrenca els serveis (3 terminals)

**Terminal 1 - Ollama:**
```bash
ollama serve
```

**Terminal 2 - Backend:**
```bash
cd backend
# Activa venv si no ho està
uvicorn main:app --reload
```

**Terminal 3 - Frontend:**
```bash
cd frontend
npm start
```

Obre el navegador a **http://localhost:3000** 🎉

---

## 📚 Com Funciona

### 1. **Indexació Automàtica de Documents**

Crea la carpeta configurada a `.env` (per defecte `~/Arrel_AI`):

```bash
# Linux/Mac
mkdir ~/Arrel_AI

# Windows
mkdir C:\Users\TeuNom\Arrel_AI
```

Posa-hi qualsevol document suportat:
- 📄 PDF
- 📝 DOCX
- 📊 CSV, TXT, MD

El **File Watcher** els detecta i indexa automàticament amb embeddings.

### 2. **Modes de Conversació**

- **General** - Assistent genèric multi-propòsit
- **Ciència** - Raonament matemàtic amb LaTeX, anàlisi de dades
- **Programació** - Escriptura i verificació de codi Python
- **Investigació** - Mode avançat amb loops iteratius i auto-correcció

### 3. **Execució de Codi**

Quan el model genera un bloc Python:
```python
import numpy as np
x = np.linspace(0, 10, 100)
y = np.sin(x)
print(f"Max: {np.max(y)}")
```

Pots executar-lo directament amb el botó **▶ Executar al Laboratori**.

### 4. **Research Mode**

El sistema:
1. Planifica l'estratègia (qwen3:8b)
2. Escriu el codi (qwen2.5-coder:7b)
3. Executa al sandbox i captura resultats
4. Auto-analitza amb **Self-Reflection**
5. Detecta problemes (NaN, Inf, arrays buits)
6. Itera fins trobar la solució correcta
7. **Verifica** amb test de contrast obligatori abans d'acabar

---

## 🏗️ Arquitectura

```
arrel-ai/
├── backend/
│   ├── main.py              # FastAPI server amb streaming
│   ├── config.py            # Configuració centralitzada
│   ├── core/
│   │   ├── sandbox.py       # Entorn d'execució persistent
│   │   ├── model_loader.py  # Gestió de VRAM i swapping
│   │   ├── file_watcher.py  # Indexació automàtica
│   │   └── self_reflection.py # Sistema d'auto-crítica
│   └── rag/
│       └── chroma_store.py  # ChromaDB + FlashRank reranking
└── frontend/
    ├── src/
    │   ├── App.js           # UI amb converses independents
    │   └── App.css          # Tema fosc amb accents per mode
    └── public/
```

### Components Clau

- **ScientificSandbox**: Execució de Python amb timeout, captura de stdout/plots, entorn persistent
- **ChromaStore**: RAG amb pipeline retrieval (15 candidats) → reranking (top 5)
- **ModelLoader**: Gestió de 6GB VRAM amb swap automàtic
- **FileWatcher**: Polling segur amb error handling específic per tipus de fitxer
- **Self-Reflection**: Raonament dimensional, detecció de problemes generals (NaN/Inf)

---

## 🧪 Tests

### Executar la suite de tests

```bash
# Instal·la dependencies de testing
pip install -r requirements_test.txt

# Executa tots els tests
pytest tests/ -v

# Amb cobertura de codi
pytest tests/ --cov=backend --cov-report=html
```

### Tests opcionals (requereixen Ollama actiu)

```bash
SKIP_MODEL_TESTS=false pytest tests/ -v
```

**Cobertura dels tests:**
- ✅ Sandbox timeout i execució correcta
- ✅ Persistència d'entorn (kernel Jupyter-like)
- ✅ Generació de gràfics amb Matplotlib
- ✅ RAG threshold filtering
- ✅ Model swapping (opcional, requereix Ollama)

---

## ⚙️ Configuració Avançada

### Variables d'Entorn (`.env`)

```bash
# Models Ollama
MODEL_GENERAL=qwen3:8b
MODEL_SCIENCE=qwen3:8b
MODEL_PROGRAMMING=qwen2.5-coder:7b
MODEL_VISION=qwen3-vl:4b
EMBED_MODEL=qwen3-embedding:0.6b

# RAG
RAG_THRESHOLD=0.25              # Mínim de similaritat (0-1)
RAG_N_RETRIEVAL=15              # Candidats inicials de ChromaDB
RAG_N_FINAL=5                   # Top N després de reranking

# Sandbox
SANDBOX_TIMEOUT=30              # Timeout en segons

# Research Mode
MAX_RESEARCH_STEPS=6            # Màxim d'iteracions
MIN_RESEARCH_STEPS=3            # Mínim abans de permetre acabar
ENABLE_SELF_REFLECTION=true    # Activar auto-crítica
```

### Canviar Models

Si vols usar altres models d'Ollama:

```bash
# Exemple: usar Llama 3.1 en lloc de Qwen
ollama pull llama3.1:8b

# Edita .env
MODEL_GENERAL=llama3.1:8b
```

**Nota**: Models més grans (70B) requereixen més VRAM.

---

## 🐛 Troubleshooting

### Error: "Cannot connect to Ollama"

```bash
# Comprova que Ollama està executant-se
ollama list

# Si no funciona, reinicia
ollama serve
```

### Error: "Model not found"

```bash
# Baixa el model que falta
ollama pull qwen3:8b
```

### Frontend no es connecta al backend

Comprova que el backend està a `http://127.0.0.1:8000`:

```bash
# Terminal del backend hauria de mostrar:
# INFO:     Uvicorn running on http://127.0.0.1:8000
```

Si uses un port diferent, edita `frontend/src/App.js`:

```javascript
const API_URL = 'http://127.0.0.1:8000';  // Canvia el port aquí
```

### Out of Memory (OOM) a la GPU

Redueix el nombre de models en memòria:
- El `ModelLoader` ja gestiona això automàticament
- Si persisteix, tanca altres aplicacions que usin GPU (Chrome, games, etc.)

---

## 🤝 Contribucions

Contribucions són benvingudes! Si trobes bugs o tens idees:

1. Obre un **Issue** descrivint el problema/proposta
2. Fes un **Fork** del repositori
3. Crea una **branch** (`git checkout -b feature/nova-funcionalitat`)
4. Commit dels canvis (`git commit -m 'Add: nova funcionalitat'`)
5. Push a la branch (`git push origin feature/nova-funcionalitat`)
6. Obre un **Pull Request**

---

## 📄 Llicència

Aquest projecte està llicenciat sota **MIT License** - veure [LICENSE](LICENSE) per detalls.

---

## 🙏 Crèdits

Construït amb:
- [**Ollama**](https://ollama.ai) - Runtime local de LLMs
- [**ChromaDB**](https://www.trychroma.com/) - Base de dades vectorial
- [**FlashRank**](https://github.com/PrithivirajDamodaran/FlashRank) - Reranking lleuger
- [**FastAPI**](https://fastapi.tiangolo.com/) - Framework web modern
- [**React**](https://react.dev/) - Interfície d'usuari
- **Qwen Models** (Alibaba Cloud) - Models base

---

## 📧 Contacte

Per preguntes o suggeriments, obre un issue al repositori.

---

**Arrel AI** - Investigació científica amb IA, 100% en local. 🌳
