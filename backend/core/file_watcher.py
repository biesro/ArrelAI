"""
File Watcher — Arrel AI v4.5
=============================
Vigila una carpeta del sistema de fitxers i indexa automàticament
qualsevol fitxer suportat que s'hi afegeixi o elimini.

✨ Millora v4.5: Error handling específic per tipus de fitxer i 
   polling de lectura per a fitxers grans (Open Source Ready).

Ús:
  - Posa un PDF/DOCX/CSV/TXT a ~/Arrel_AI → s'indexa sol
  - Elimina'l → s'esborra del RAG sol
  - No cal tocar la UI
"""

import os
import time
import pypdf
import pypdf.errors
import docx
import docx.opc.exceptions
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

SUPPORTED_EXTENSIONS = {'.pdf', '.docx', '.csv', '.txt', '.md'}


def _wait_for_file_ready(filepath: str, timeout: int = 30) -> bool:
    """
    Espera fins que el fitxer estigui completament copiat i el SO l'alliberi.
    Evita que el programa faci crash si s'arrossega un fitxer molt pesat.
    """
    previous_size = -1
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            current_size = os.path.getsize(filepath)
            
            # Si el pes és > 0 i no ha canviat respecte a la iteració anterior
            if current_size == previous_size and current_size > 0:
                # Intentem obrir-lo per confirmar que el SO ja no el bloqueja
                with open(filepath, 'rb'):
                    pass
                return True
                
            previous_size = current_size
        except (OSError, IOError):
            # El fitxer encara està bloquejat pel procés de còpia, l'ignorem de moment
            pass
            
        time.sleep(0.5)  # Comprovem cada mig segon
        
    return False  # Ha superat el timeout i no s'ha pogut llegir


def _extract_text(filepath: str) -> tuple[str, str | None]:
    """
    Extreu text d'un fitxer segons la seva extensió.
    
    Returns:
        tuple(text, error_message)
        - Si tot va bé: (text, None)
        - Si hi ha error: ("", error_message)
    """
    ext = os.path.splitext(filepath)[1].lower()
    text = ""

    try:
        if ext == '.pdf':
            try:
                with open(filepath, "rb") as f:
                    reader = pypdf.PdfReader(f)
                    for page in reader.pages:
                        text += (page.extract_text() or "") + "\n"
            except pypdf.errors.PdfReadError as e:
                return "", f"PDF corrupte: {str(e)[:100]}"
            except pypdf.errors.FileNotDecryptedError:
                return "", "PDF encriptat. Desencripta'l abans d'indexar."

        elif ext == '.docx':
            try:
                doc = docx.Document(filepath)
                text = "\n".join([p.text for p in doc.paragraphs])
            except docx.opc.exceptions.PackageNotFoundError:
                return "", "Fitxer .docx danyat o no vàlid."
            except KeyError as e:
                return "", f"Format .docx no suportat: {str(e)[:100]}"

        elif ext in {'.csv', '.txt', '.md'}:
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    text = f.read()
            except UnicodeDecodeError:
                # Intent amb Latin-1
                try:
                    with open(filepath, "r", encoding="latin-1") as f:
                        text = f.read()
                except Exception as e:
                    return "", f"Encoding no suportat: {str(e)[:100]}"
        
        # Validació: fitxer buit
        if not text.strip():
            return "", "Fitxer buit o sense text extraïble."
        
        return text, None
        
    except PermissionError:
        return "", "Error de permisos. No es pot llegir el fitxer."
    except OSError as e:
        return "", f"Error d'E/S: {str(e)[:100]}"
    except Exception as e:
        return "", f"Error inesperat: {str(e)[:200]}"


class _ArrelFileHandler(FileSystemEventHandler):
    def __init__(self, rag_engine, watch_folder: str):
        super().__init__()
        self.rag_engine = rag_engine
        self.watch_folder = watch_folder
        self._index_existing_files()

    def _index_existing_files(self):
        """Indexa els fitxers que ja existien a la carpeta quan arrenca el servidor."""
        print(f"🔍 Escanejant carpeta existent: {self.watch_folder}")
        already_indexed = set(self.rag_engine.get_loaded_files())

        for filename in os.listdir(self.watch_folder):
            filepath = os.path.join(self.watch_folder, filename)
            ext = os.path.splitext(filename)[1].lower()

            if os.path.isfile(filepath) and ext in SUPPORTED_EXTENSIONS:
                if filename not in already_indexed:
                    print(f"  📄 Indexant: {filename}")
                    self._process_and_index(filepath)
                else:
                    print(f"  ✅ Ja indexat: {filename}")

    def on_created(self, event):
        if event.is_directory:
            return
        ext = os.path.splitext(event.src_path)[1].lower()
        if ext in SUPPORTED_EXTENSIONS:
            filename = os.path.basename(event.src_path)
            print(f"🆕 Nou fitxer detectat, esperant que finalitzi la còpia: {filename}...")
            
            # Substituïm el sleep rígid pel polling segur
            if _wait_for_file_ready(event.src_path):
                self._process_and_index(event.src_path)
            else:
                print(f"❌ Error: Temps d'espera esgotat intentant llegir '{filename}'. L'arxiu triga massa en copiar-se o està bloquejat.")

    def on_deleted(self, event):
        if event.is_directory:
            return
        ext = os.path.splitext(event.src_path)[1].lower()
        if ext in SUPPORTED_EXTENSIONS:
            filename = os.path.basename(event.src_path)
            print(f"🗑️ Fitxer eliminat, esborrant del RAG: {filename}")
            self.rag_engine.delete_document(filename)

    def on_moved(self, event):
        """Gestiona el cas de reanomenar o moure un fitxer a la carpeta."""
        if event.is_directory:
            return
        old_name = os.path.basename(event.src_path)
        new_ext = os.path.splitext(event.dest_path)[1].lower()
        
        if new_ext in SUPPORTED_EXTENSIONS:
            self.rag_engine.delete_document(old_name)
            filename = os.path.basename(event.dest_path)
            print(f"🔄 Fitxer reanomenat/mogut, processant: {filename}...")
            
            # Polling per curar-nos en salut si el procés de moure és lent
            if _wait_for_file_ready(event.dest_path):
                self._process_and_index(event.dest_path)
            else:
                print(f"❌ Error: Temps d'espera esgotat intentant llegir '{filename}'.")

    def _process_and_index(self, filepath: str):
        """Processa i indexa un fitxer amb error handling millorat."""
        filename = os.path.basename(filepath)
        
        # Extracció amb error handling
        text, error = _extract_text(filepath)
        
        if error:
            print(f"❌ Error processant '{filename}': {error}")
            return
        
        if not text.strip():
            print(f"⚠️ '{filename}' buit després d'extreure'l.")
            return
        
        # Indexació al RAG
        try:
            self.rag_engine.add_document(text, filename)
            print(f"✅ '{filename}' indexat automàticament via File Watcher.")
        except Exception as e:
            print(f"❌ Error indexant '{filename}' al RAG: {str(e)[:200]}")


def start_file_watcher(rag_engine, watch_folder: str):
    """
    Arrenca el File Watcher en background.
    Retorna l'observer per poder aturar-lo al shutdown.
    """
    os.makedirs(watch_folder, exist_ok=True)
    handler = _ArrelFileHandler(rag_engine, watch_folder)
    observer = Observer()
    observer.schedule(handler, path=watch_folder, recursive=False)
    observer.start()
    print(f"👁️  File Watcher actiu — vigilant: {watch_folder}")
    return observer