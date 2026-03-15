"""
Arrel AI — Backend v4.5
========================
- Memoria de conversa
- File Watcher integrat
- RAG amb threshold
- Fonts RAG visibles
- Sandbox persistent
- Execution Feedback Loop (Research Mode)
- Config centralitzat
- ✨ Error handling millorat per open source
"""

from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
import ollama
import shutil
import os
import pypdf
import pypdf.errors
import docx
import docx.opc.exceptions
import re

from .core.model_loader import ModelLoader
from .core.sandbox import ScientificSandbox
from .core.file_watcher import start_file_watcher
from .core.self_reflection import (
    build_reflection_prompt, 
    detect_quality_issues
)
from .rag.chroma_store import ChromaStore
from .config import (
    PROMPTS, WATCH_FOLDER, MAX_RETRIES,
    MAX_RESEARCH_STEPS, MIN_RESEARCH_STEPS,
    RESEARCH_CONTINUE_PROMPT, RESEARCH_SYSTEM_PROMPT,
    ENABLE_SELF_REFLECTION, REFLECTION_FREQUENCY
)

# ---------------------------------------------------------------------------
# App & Middleware
# ---------------------------------------------------------------------------

app = FastAPI(title="Arrel AI", version="4.5")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Components globals
# ---------------------------------------------------------------------------

loader = ModelLoader()
sandbox = ScientificSandbox()
rag_engine = ChromaStore()
_file_watcher_observer = None

# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------

@app.on_event("startup")
async def _startup():
    global _file_watcher_observer
    _file_watcher_observer = start_file_watcher(rag_engine, WATCH_FOLDER)


@app.on_event("shutdown")
def _shutdown():
    loader.unload_current()
    if _file_watcher_observer:
        _file_watcher_observer.stop()
        _file_watcher_observer.join()

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class HistoryMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    prompt: str
    mode: str
    images: Optional[list] = []
    history: Optional[List[HistoryMessage]] = []
    research_mode: Optional[bool] = False


class LabRequest(BaseModel):
    code: str

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_messages(system_prompt: str, user_content: str, history: List[HistoryMessage]) -> list:
    msgs = [{"role": "system", "content": system_prompt}]
    for msg in history:
        msgs.append({"role": msg.role, "content": msg.content})
    msgs.append({"role": "user", "content": user_content})
    return msgs

# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------

@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    Upload de documents amb error handling específic per tipus de fitxer.
    Millora per open source: Errors clars i accionables per l'usuari.
    """
    temp_path = f"/tmp/arrel_{file.filename}"
    text = ""
    
    try:
        # Guardar fitxer temporal
        with open(temp_path, "wb") as buf:
            shutil.copyfileobj(file.file, buf)

        # PDF - Errors específics
        if file.filename.endswith('.pdf'):
            try:
                with open(temp_path, "rb") as f:
                    reader = pypdf.PdfReader(f)
                    for page in reader.pages:
                        text += (page.extract_text() or "") + "\n"
            except pypdf.errors.PdfReadError as e:
                return {"status": "error", "message": f"PDF corrupte o no vàlid: {str(e)[:100]}"}
            except pypdf.errors.FileNotDecryptedError:
                return {"status": "error", "message": "El PDF està encriptat. Si us plau, desencripta'l primer."}
            
        # DOCX - Errors específics
        elif file.filename.endswith('.docx'):
            try:
                doc = docx.Document(temp_path)
                text = "\n".join([p.text for p in doc.paragraphs])
            except docx.opc.exceptions.PackageNotFoundError:
                return {"status": "error", "message": "El fitxer .docx està danyat o no és un document vàlid."}
            except KeyError as e:
                return {"status": "error", "message": f"Format .docx no suportat o corrupte: {str(e)[:100]}"}
            
        # Text files - Encoding handling
        elif file.filename.endswith(('.csv', '.txt', '.md')):
            try:
                with open(temp_path, "r", encoding="utf-8") as f:
                    text = f.read()
            except UnicodeDecodeError:
                # Intenta amb altres encodings comuns
                try:
                    with open(temp_path, "r", encoding="latin-1") as f:
                        text = f.read()
                except Exception:
                    return {"status": "error", "message": "Encoding no suportat. El fitxer ha de ser UTF-8 o Latin-1."}

        # Validació: fitxer buit
        if not text.strip():
            return {"status": "error", "message": f"'{file.filename}' està buit o no conté text extraïble."}

        # Indexar al RAG
        try:
            rag_engine.add_document(text, file.filename)
        except Exception as e:
            return {"status": "error", "message": f"Error indexant al RAG: {str(e)[:200]}"}
        
        return {"status": "success", "message": f"'{file.filename}' afegit a la memoria."}
        
    except PermissionError:
        return {"status": "error", "message": "Error de permisos. No es pot accedir al fitxer."}
    except OSError as e:
        return {"status": "error", "message": f"Error d'E/S: {str(e)[:100]}"}
    except Exception as e:
        return {"status": "error", "message": f"Error inesperat processant '{file.filename}': {str(e)[:200]}"}
    finally:
        # Neteja del fitxer temporal
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass  # No volem que fallar la neteja trenqui la resposta


@app.get("/api/documents")
async def list_documents():
    return {"documents": rag_engine.get_loaded_files()}


@app.delete("/api/documents/{filename}")
async def delete_document(filename: str):
    success = rag_engine.delete_document(filename)
    if success:
        return {"status": "success", "message": f"'{filename}' esborrat."}
    return {"status": "error", "message": "No s'ha pogut esborrar el document."}

# ---------------------------------------------------------------------------
# Laboratori
# ---------------------------------------------------------------------------

@app.post("/api/lab/execute")
async def run_experiment(request: LabRequest):
    return sandbox.execute_and_plot(request.code)


@app.post("/api/lab/reset")
async def reset_sandbox():
    sandbox.reset_env()
    return {"status": "success", "message": "Entorn del laboratori reiniciat."}

# ---------------------------------------------------------------------------
# Chat (streaming)
# ---------------------------------------------------------------------------

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    user_prompt = request.prompt
    mode = request.mode if not request.images else "vision"

    # Research: usem science com a model base + feedback loop actiu
    if mode == "research":
        mode = "science"
        research_active = True
    else:
        research_active = request.research_mode

    history = request.history or []

    context, sources_used = rag_engine.query(user_prompt)

    final_prompt = user_prompt
    if context:
        final_prompt = (
            f"Utilitza aquesta informacio com a context per respondre:\n"
            f"{context}\n\n"
            f"Pregunta: {user_prompt}"
        )

    def generate_stream():
        # Fonts RAG
        if sources_used:
            fonts_str = " . ".join([f"`{s}`" for s in sources_used])
            yield f"> RAG: {fonts_str}\n\n"

        # ---------------------------------------------------------------
        # RESEARCH LOOP
        # ---------------------------------------------------------------
        if mode in ["science", "programming"] and research_active:
            yield f"> Investigacio activa: maxim {MAX_RESEARCH_STEPS} passos, minim {MIN_RESEARCH_STEPS}...\n\n"

            # Noms dels models (sense swap innecessari al principi)
            science_model = loader.models["science"]
            coder_model   = loader.models["programming"]

            research_messages = [
                {"role": "system", "content": RESEARCH_SYSTEM_PROMPT},
                {"role": "user",   "content": final_prompt}
            ]

            steps_done = 0
            consecutive_failures = 0  # Comptador de fallades consecutives
            last_failure_output = ""  # Última sortida de fallada per detectar repeticions
            # Guardem el codi de cada pas exitós per donar context al model quan falla
            successful_code_history = []

            for step in range(MAX_RESEARCH_STEPS):
                yield f"> Pas {step + 1}/{MAX_RESEARCH_STEPS}: Planificant...\n\n"

                # qwen3:8b decideix que fer
                loader.load_expert("science")
                step_response = ollama.chat(
                    model=science_model,
                    messages=research_messages
                )['message']['content']

                # Condicio de parada — nomes si hem fet prou passos
                has_completion_token = "INVESTIGACIO_COMPLETA" in step_response or "INVESTIGACIÓ_COMPLETA" in step_response
                
                if has_completion_token and steps_done >= MIN_RESEARCH_STEPS:
                    yield f"> Investigacio completada en {step + 1} passos!\n\n---\n\n"
                    for line in step_response.split('\n'):
                        yield line + '\n'
                    return

                # Si el model vol acabar pero no hem fet prou passos o ha fallat analíticament, forcem continuació estricta
                if has_completion_token and steps_done < MIN_RESEARCH_STEPS:
                    yield f"> Pas {step + 1}: Investigació insuficient (només {steps_done}/{MIN_RESEARCH_STEPS} passos completats). Forçant nou enfocament...\n\n"
                    research_messages.append({"role": "assistant", "content": step_response})
                    research_messages.append({
                        "role": "user",
                        "content": (
                            f"⚠️ PROHIBIT ACABAR: Només has completat {steps_done} passos d'execució dels {MIN_RESEARCH_STEPS} requerits.\n\n"
                            f"Revisa l'última sortida (STDOUT). Si el resultat va ser:\n"
                            f"  • Buit (llistes buides, arrays sense dades)\n"
                            f"  • Negatiu (ex: 'No X found', 'Detection failed')\n"
                            f"  • Trivial (ex: tots zeros, valors constants)\n\n"
                            f"Això indica que la teva estratègia anterior NO ha funcionat.\n\n"
                            f"CAUSES POSSIBLES:\n"
                            f"  • Criteri de selecció massa estricte o massa lax\n"
                            f"  • Dades necessiten preprocessament previ\n"
                            f"  • Enfocament matemàtic inadequat per aquest problema\n\n"
                            f"TASCA: Genera un NOU bloc ```python amb una estratègia COMPLETAMENT DIFERENT:\n"
                            f"  • Prova preprocessar les dades (normalització, agregació, transformacions)\n"
                            f"  • Revisa i ajusta els criteris o llindars utilitzats\n"
                            f"  • Considera un enfocament matemàtic alternatiu\n\n"
                            f"NO repeteixis la mateixa lògica que ja ha fallat."
                        )
                    })
                    continue

                code_match = re.search(r'```python\n(.*?)\n```', step_response, re.DOTALL)

                if not code_match:
                    # Resposta teorica sense codi
                    yield f"> Pas {step + 1} - Analisi teorica:\n\n"
                    for line in step_response.split('\n'):
                        yield line + '\n'
                    research_messages.append({"role": "assistant", "content": step_response})
                    steps_done += 1
                    continue

                # qwen2.5-coder escriu el codi final
                yield f"> Agent Coder: Escrivint codi per al pas {step + 1}...\n\n"

                # Detectem si és el primer pas (sandbox buit)
                is_first_step = len(successful_code_history) == 0

                # 🔍 SANDBOX INTROSPECTION — El model veu l'estat actual
                sandbox_state_str = sandbox.get_state_summary()

                # Construim el context del sandbox segons la situació
                if is_first_step:
                    sandbox_context = (
                        f"\n⚡ PRIMER PAS — El sandbox està BUIT.\n"
                        f"Has de GENERAR totes les dades i variables necessàries des de zero.\n"
                        f"Utilitza NumPy (np), Pandas (pd), i Matplotlib (plt) que ja estan importats.\n"
                    )
                else:
                    sandbox_context = (
                        f"\n{sandbox_state_str}\n\n"
                        f"⚠️ Pots usar directament aquestes variables. NO les tornis a definir.\n"
                    )

                loader.load_expert("programming")
                coder_response = ollama.chat(
                    model=coder_model,
                    messages=[
                        {"role": "system", "content": "Ets un expert en Python científic. Implementes solucions basades en criteris de validació estrictes."},
                        {"role": "user", "content": (
                            f"PREGUNTA ORIGINAL DE L'USUARI:\n{final_prompt}\n\n"
                            f"INSTRUCCIONS DEL CIENTÍFIC PER AQUEST PAS:\n{step_response}\n\n"
                            f"{sandbox_context}\n\n"
                            f"TASCA: Escriu el codi Python per a aquest pas.\n\n"
                            f"⚠️ REGLA CRÍTICA DE VERIFICACIÓ:\n"
                            f"Has d'incloure al final del codi un bloc de 'UNIT TEST' o 'ASSERT' "
                            f"que comprovi exactament el CRITERI DE VALIDACIÓ que ha dictat el científic.\n"
                            f"Si el test no passa, el codi ha de llançar un error o fer un print clar de 'TEST FAILED'.\n\n"
                            f"Retorna ÚNICAMENT el bloc ```python."
                        )}
                    ]
                )['message']['content']

                code_match2 = re.search(r'```python\n(.*?)\n```', coder_response, re.DOTALL)
                python_code = code_match2.group(1) if code_match2 else code_match.group(1)

                yield f"```python\n{python_code}\n```\n\n"

                exec_result = sandbox.execute_and_plot(python_code)
                steps_done += 1

                if exec_result["status"] == "success":
                    stdout    = exec_result.get("output", "") or ""
                    has_plot  = "Si" if exec_result.get("plot") else "No"
                    has_table = "Si" if exec_result.get("table") else "No"

                    # 🔍 DETECCIÓ DE PROBLEMES GENERALS (NaN, Inf, arrays buits)
                    quality_issues = detect_quality_issues(sandbox.persistent_env)
                    quality_str = ""
                    if quality_issues:
                        quality_str = "\n⚠️ PROBLEMES DE QUALITAT DETECTATS:\n"
                        quality_str += "\n".join(quality_issues) + "\n"
                        yield quality_str

                    # 💭 SELF-REFLECTION (el model analitza els seus propis resultats)
                    reflection_str = ""
                    if ENABLE_SELF_REFLECTION and (steps_done % REFLECTION_FREQUENCY == 0):
                        reflection_str = build_reflection_prompt(
                            stdout, 
                            sandbox.persistent_env, 
                            step_num=step + 1
                        )

                    # Detectem si el resultat exitós és idèntic al anterior (bucle estúpid)
                    is_repeated_success = (stdout.strip() == last_failure_output and consecutive_failures > 0)

                    # Guardem el codi exitós per donar context als passos futurs
                    successful_code_history.append(python_code)
                    last_failure_output = stdout.strip()
                    consecutive_failures = 0

                    if stdout.strip():
                        yield f"> Sortida:\n```\n{stdout.strip()}\n```\n\n"
                    if exec_result.get("plot"):
                        yield "> Graf generat.\n\n"

                    # Si el resultat és idèntic al anterior, avisar al model
                    repeated_warning = (
                        f"\n⚠️ ATENCIÓ: Aquest resultat és idèntic al pas anterior. "
                        f"La teva estratègia no està funcionant. Canvia completament d'enfocament.\n"
                        if is_repeated_success else ""
                    )

                    # 🔍 SANDBOX STATE per al feedback
                    sandbox_state_feedback = f"\n{sandbox.get_state_summary()}\n"

                    feedback = RESEARCH_CONTINUE_PROMPT.format(
                        status="SUCCESS" + (" (RESULTAT REPETIT)" if is_repeated_success else ""),
                        stdout=stdout.strip() or "(cap sortida de text)",
                        has_plot=has_plot,
                        has_table=has_table,
                        sandbox_state=sandbox_state_feedback,
                        quality_issues=quality_str,
                        reflection_prompt=reflection_str,
                        current_step=step + 1,
                        max_steps=MAX_RESEARCH_STEPS,
                        min_steps=MIN_RESEARCH_STEPS
                    ) + repeated_warning
                else:
                    error = exec_result.get("message", "Error desconegut")[:500]
                    current_output = stdout if 'stdout' in dir() else ""

                    # Detectem si és la mateixa fallada repetida
                    is_repeated = (current_output == last_failure_output and consecutive_failures > 0)
                    consecutive_failures += 1
                    last_failure_output = current_output

                    yield f"> Error al pas {step + 1} (fallada #{consecutive_failures}): {error}\n\n"

                    # Si porta 2+ fallades consecutives, forcem canvi d'estrategia
                    if consecutive_failures >= 2:
                        strategy_warning = (
                            f"\n\n⚠️ ATENCIO CRITICA: Has provat la mateixa estrategia {consecutive_failures} vegades sense exit. "
                            f"El resultat continua sent incorrecte. "
                            f"Has de CANVIAR COMPLETAMENT D'ENFOCAMENT. "
                            f"NO tornis a usar el mateix metode. Prova una aproximacio totalment diferent."
                        )
                    else:
                        strategy_warning = ""

                    # 🔍 SANDBOX STATE per context d'error
                    sandbox_state_error = f"\n{sandbox.get_state_summary()}\n"

                    feedback = (
                        f"ERROR AL PAS {step + 1}:\n{error}\n\n"
                        f"{sandbox_state_error}\n"
                        f"Codi dels passos anteriors exitosos:\n"
                        + ("\n---\n".join([f"Pas {i+1}:\n```python\n{c}\n```"
                                          for i, c in enumerate(successful_code_history)])
                           if successful_code_history else "(cap pas exitós encara)")
                        + f"\n\nCorregeix l'error. Usa NOMES les variables que existeixen al sandbox."
                        + strategy_warning
                    )

                research_messages.append({"role": "assistant", "content": step_response})
                research_messages.append({"role": "user",      "content": feedback})

            yield f"> Limit de {MAX_RESEARCH_STEPS} passos assolit.\n\n"
            return

        # ---------------------------------------------------------------
        # MODE MULTI-AGENT normal (science / programming)
        # ---------------------------------------------------------------
        elif mode in ["science", "programming"]:
            yield "> Agent Principal: Analitzant el problema...\n\n"

            loader.load_expert(mode)
            creator_model = loader.models[mode]

            draft_messages = _build_messages(PROMPTS[mode], final_prompt, history)
            draft_response = ollama.chat(model=creator_model, messages=draft_messages)['message']['content']

            # Ciencia teorica sense codi
            if mode == "science" and "```python" not in draft_response.lower():
                yield "> Agent Cientific: (Mode Teoric)\n\n"
                for line in draft_response.split('\n'):
                    yield line + '\n'
                return

            yield "> Agent Verificador (QA): Iniciant auto-correccio...\n\n"

            loader.load_expert("programming")
            verifier_model = loader.models["programming"]

            verifier_prompt = (
                f"Ets un expert en QA i Revisor de Codi Senior.\n"
                f"Revisa i adapta el codi per a Matplotlib headless.\n\n"
                f"REGLES ESTRICTES:\n"
                f"1. Elimina plt.show(). Usa plt.savefig('output.png', bbox_inches='tight').\n"
                f"2. Usa print() per mostrar resultats numerics, NO escriguis a fitxers.\n"
                f"3. Comprova la logica matematica i les crides a llibreries.\n"
                f"4. Retorna SEMPRE el codi dins d'un unic bloc ```python.\n\n"
                f"CODI A REVISAR:\n{draft_response}"
            )

            verifier_messages = _build_messages(
                "Ets un revisor de codi estricte. Produeix el resultat final i validat.",
                verifier_prompt,
                []
            )

            final_valid_response = ""
            current_response = ""

            for attempt in range(MAX_RETRIES):
                yield f"> Iteracio {attempt + 1}/{MAX_RETRIES}: Validant al sandbox intern...\n\n"

                current_response = ollama.chat(
                    model=verifier_model,
                    messages=verifier_messages
                )['message']['content']

                code_match = re.search(r'```python\n(.*?)\n```', current_response, re.DOTALL)

                if not code_match:
                    yield "> Format incorrecte. Forcant correccio...\n\n"
                    verifier_messages.append({"role": "assistant", "content": current_response})
                    verifier_messages.append({
                        "role": "user",
                        "content": "Error de format: TOTA la resposta ha de ser un unic bloc ```python."
                    })
                    continue

                python_code = code_match.group(1)
                test_result = sandbox.execute_and_plot(python_code)

                if test_result["status"] == "success":
                    yield f"> Validacio superada a la iteracio {attempt + 1}!\n\n---\n\n"
                    final_valid_response = current_response
                    break
                else:
                    error_msg = test_result["message"]
                    yield f"> Error al sandbox: {error_msg[:300]}\n\n"
                    verifier_messages.append({"role": "assistant", "content": current_response})
                    verifier_messages.append({
                        "role": "user",
                        "content": (
                            f"EXECUCIO FALLIDA:\n{error_msg}\n\n"
                            f"INSTRUCCIONS:\n"
                            f"1. Identifica la linia exacta del Traceback i arregla-la.\n"
                            f"2. NO eliminis cap variable o parametre del codi original.\n"
                            f"3. Retorna UNICAMENT el codi Python corregit dins de ```python."
                        )
                    })

            if not final_valid_response:
                yield "> No s'ha pogut garantir un codi lliure d'errors. Mostrant l'ultim intent:\n\n---\n\n"
                final_valid_response = current_response

            for line in final_valid_response.split('\n'):
                yield line + '\n'

        # ---------------------------------------------------------------
        # MODE NORMAL (general / vision)
        # ---------------------------------------------------------------
        else:
            loader.load_expert(mode)
            model_name = loader.models[mode]

            messages = _build_messages(
                PROMPTS.get(mode, PROMPTS["general"]),
                final_prompt,
                history
            )

            if request.images:
                clean_images = [img.split(",")[1] if "," in img else img for img in request.images]
                messages[-1]["images"] = clean_images

            stream = ollama.chat(model=model_name, messages=messages, stream=True)
            for chunk in stream:
                if 'message' in chunk and 'content' in chunk['message']:
                    yield chunk['message']['content']

    return StreamingResponse(generate_stream(), media_type="text/plain")
