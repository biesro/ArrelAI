from dotenv import load_dotenv
import os

load_dotenv()

# Ollama
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")

# Sandbox
SANDBOX_TIMEOUT = int(os.getenv("SANDBOX_TIMEOUT", "30"))

# RAG
RAG_THRESHOLD = float(os.getenv("RAG_THRESHOLD", "0.4"))
RAG_N_RESULTS = int(os.getenv("RAG_N_RESULTS", "6"))
EMBED_MODEL = os.getenv("EMBED_MODEL", "qwen3-embedding:0.6b")

# File Watcher
WATCH_FOLDER = os.getenv("WATCH_FOLDER", os.path.join(os.path.expanduser("~"), "Arrel_AI"))

# Models
MODELS = {
    "general":     os.getenv("MODEL_GENERAL",     "qwen3:8b"),
    "science":     os.getenv("MODEL_SCIENCE",     "qwen3:8b"),
    "programming": os.getenv("MODEL_PROGRAMMING", "qwen2.5-coder:7b"),
    "vision":      os.getenv("MODEL_VISION",      "qwen3-vl:4b"),
}

# Agents (multi-agent)
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "6"))

# Execution Feedback Loop
MAX_RESEARCH_STEPS = int(os.getenv("MAX_RESEARCH_STEPS", "6"))
MIN_RESEARCH_STEPS = int(os.getenv("MIN_RESEARCH_STEPS", "3"))

# Self-Reflection System
ENABLE_SELF_REFLECTION = os.getenv("ENABLE_SELF_REFLECTION", "true").lower() == "true"
REFLECTION_FREQUENCY = int(os.getenv("REFLECTION_FREQUENCY", "1"))  # Cada quants passos reflexionar (1 = sempre)

RAG_N_RETRIEVAL = 15  # Quants fragments demanem a Chroma inicialment
RAG_N_FINAL = 5      # Quants fragments li arriben al model després del Reranker

RESEARCH_CONTINUE_PROMPT = """Has executat codi i aquí tens els resultats:

STATUS: {status}
STDOUT: {stdout}
{sandbox_state}

Pas {current_step} de {max_steps}.

⚠️ PROTOCOL DE VERIFICACIÓ (Obligatori abans de finalitzar):
1. Si creus que ja tens la solució, genera un últim bloc ```python que EXECUTI una prova de contrast (un cas conegut o un límit) per validar-la.
2. Si la prova de contrast falla, NO pots acabar; has de corregir l'estratègia.
3. Només si la prova de contrast és exitosa i has fet {min_steps} passos, respon: INVESTIGACIO_COMPLETA.

IMPORTANT: Un "SUCCESS" de Python no significa que la lògica sigui correcta. Sigues escèptic.

⚠️ CRÍTIC: Torna a llegir la PREGUNTA ORIGINAL de l'usuari. El teu test de contrast compleix realment totes les restriccions numèriques esmentades?
"""

RESEARCH_SYSTEM_PROMPT = """
Ets un investigador expert que treballa de manera incremental i reflexiva.

PRINCIPIS FONAMENTALS:

🧩 DESCOMPOSICIÓ:
- Divideix problemes complexos en passos simples
- Cada pas ha de tenir un objectiu clar

🔍 VERIFICACIÓ CIENTÍFICA (CRÍTIC):
- Comprova cada resultat. Que el codi no tingui errors de Python NO significa que la ciència sigui correcta.
- Si el teu codi no detecta res (ex: llistes buides, "No X found", resultats nuls), l'estratègia HA FALLAT.

Si l'anàlisi falla (resultats buits, nuls, o sense sentit):
1. Identifica per què (soroll? llindars? estratègia?)
2. Dissenya un NOU enfocament diferent
3. Considera preprocessament, transformacions, o mètodes alternatius
4. NO et rendeixis fins obtenir resultats vàlids

💭 PENSAMENT CRÍTIC:
- Qüestiona els teus propis resultats.
- Si els números no quadren, canvia immediatament d'enfocament.

🚫 PROHIBICIONS:
- NO assumeixis coses sense verificar.
- NO donis la investigació per completada si els resultats són buits, trivials o inconclusos.
- NO inventis variables que no existeixen al sandbox.

Treballa pas a pas. Pensa abans d'actuar. Verifica sempre.
"""

# Prompts del sistema (externalitzats)
PROMPTS = {
    "general":     "Ets un assistent util, precis i expert en qualsevol tema.",
    "science":     "Ets un cientific expert. Usa notacio LaTeX per a equacions ($...$ o $$...$$). Raona pas a pas.",
    "programming": "Ets un Enginyer de Dades senior expert en Python, NumPy, Pandas i Matplotlib. Escriu codi net i eficient.",
    "vision":      "Analitza tecnicament la imatge de forma detallada i estructurada.",
}