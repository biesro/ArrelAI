"""
ChromaStore — Arrel AI RAG Engine v4.5
=======================================
Gestiona la memòria vectorial del sistema usant ChromaDB i Ollama embeddings.

✨ Característiques v4.5:
- Pipeline de dos estadis: Retrieval (ChromaDB) + Reranking (FlashRank)
- Threshold de similaritat configurable
- Retorna les fonts usades per mostrar-les a la UI
- Embedding model configurable via .env
- Error handling complet
"""

import chromadb
import uuid
import os
import ollama
from flashrank import Ranker, RerankRequest

from ..config import RAG_THRESHOLD, RAG_N_RESULTS, EMBED_MODEL

# Constants per al pipeline de reranking
RAG_N_RETRIEVAL = 15  # Quants fragments demanem a Chroma inicialment
RAG_N_FINAL = 5       # Quants fragments li arriben al model després del Reranker


class ChromaStore:
    def __init__(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(current_dir, "../../"))
        db_path = os.path.join(project_root, "chroma_db")

        os.makedirs(db_path, exist_ok=True)
        print(f"📦 Inicialitzant ChromaDB a: {db_path}")

        self.embed_model = EMBED_MODEL

        # Verificar que el model d'embeddings existeix
        try:
            ollama.embed(model=self.embed_model, input="test")
            print(f"🧠 Model d'embeddings '{self.embed_model}' OK.")
        except Exception:
            fallback = "qwen2.5-coder:7b"
            print(f"⚠️ '{self.embed_model}' no disponible. Usant '{fallback}'.")
            self.embed_model = fallback

        self.client = chromadb.PersistentClient(path=db_path)
        
        # Usem distància cosinus per tenir similaritats normalitzades entre 0 i 1
        self.collection = self.client.get_or_create_collection(
            name="arrel_knowledge",
            metadata={"hnsw:space": "cosine"}
        )
        
        # Inicialitzem el Reranker (baixarà el model de ~150MB el primer cop)
        # Corre en CPU, no gasta VRAM de la GPU
        print("💡 Carregant Reranker lleuger (FlashRank)...")
        try:
            self.ranker = Ranker(model_name="ms-marco-MiniLM-L-12-v2")
            print("✅ Reranker carregat correctament.")
        except Exception as e:
            print(f"⚠️ Error carregant Reranker: {e}")
            print("   El sistema funcionarà sense reranking.")
            self.ranker = None

    # ------------------------------------------------------------------
    # Indexació
    # ------------------------------------------------------------------

    def add_document(self, text: str, filename: str):
        """
        Trosseja el document i genera embeddings per lots.
        
        Args:
            text: Text complet del document
            filename: Nom del fitxer original (per tracking)
        """
        if not text.strip():
            print(f"⚠️ '{filename}' està buit, no s'indexarà.")
            return

        # Chunking amb overlap per no perdre context
        chunk_size = 2500
        overlap = 200
        chunks = []
        
        for i in range(0, len(text), chunk_size - overlap):
            chunk = text[i:i + chunk_size]
            if chunk.strip():  # Només afegim chunks no buits
                chunks.append(chunk)

        if not chunks:
            print(f"⚠️ No s'han pogut generar chunks per '{filename}'.")
            return

        print(f"🔄 Processant {len(chunks)} fragments de '{filename}'...")

        # Generació d'embeddings per lots (més eficient)
        all_embeddings = []
        batch_size = 50

        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            try:
                response = ollama.embed(model=self.embed_model, input=batch)
                all_embeddings.extend(response['embeddings'])
                print(f"  ⏳ {min(i + batch_size, len(chunks))}/{len(chunks)} fragments processats...")
            except Exception as e:
                print(f"❌ Error generant embeddings per lot {i//batch_size + 1}: {e}")
                # Continuem amb els següents lots

        if not all_embeddings:
            print(f"⚠️ No s'han pogut generar embeddings per '{filename}'.")
            return

        if len(all_embeddings) != len(chunks):
            print(f"⚠️ Mismatch: {len(chunks)} chunks però {len(all_embeddings)} embeddings.")
            # Ajustem per evitar crash
            min_len = min(len(chunks), len(all_embeddings))
            chunks = chunks[:min_len]
            all_embeddings = all_embeddings[:min_len]

        # Generem IDs únics i metadades
        ids = [str(uuid.uuid4()) for _ in chunks]
        metadatas = [{"source": filename} for _ in chunks]

        # Inserció a ChromaDB
        try:
            self.collection.add(
                documents=chunks,
                embeddings=all_embeddings,
                ids=ids,
                metadatas=metadatas
            )
            print(f"✅ '{filename}' indexat correctament ({len(chunks)} fragments).")
        except Exception as e:
            print(f"❌ Error afegint '{filename}' a ChromaDB: {e}")

    # ------------------------------------------------------------------
    # Consulta amb Reranking
    # ------------------------------------------------------------------

    def query(self, question: str, n_results: int = RAG_N_RESULTS) -> tuple[str, list[str]]:
        """
        RAG amb Pipeline de dos estadis:
        1. Retrieval (ChromaDB) - Busca 15 candidats per similitud vectorial
        2. Reranking (FlashRank) - Re-puntua i tria els 5 millors segons rellevància real
        
        Args:
            question: Pregunta de l'usuari
            n_results: Nombre de resultats finals (per defecte usa config)
        
        Returns:
            tuple (context formatat, llista de fonts usades)
        """
        if self.collection.count() == 0:
            return "", []

        try:
            # 1. Generem embedding de la pregunta
            response = ollama.embed(model=self.embed_model, input=question)
            query_embedding = response['embeddings'][0]

            # 2. Retrieval inicial: Demanem més candidats per tenir marge
            n_retrieval = RAG_N_RETRIEVAL if self.ranker else n_results
            
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=min(n_retrieval, self.collection.count()),
                include=["documents", "metadatas", "distances"]
            )

            if not results['documents'] or not results['documents'][0]:
                return "", []

            # 3. Si tenim Reranker, l'usem
            if self.ranker:
                return self._query_with_reranking(question, results)
            else:
                return self._query_without_reranking(results, n_results)

        except Exception as e:
            print(f"❌ Error en la consulta RAG: {e}")
            return "", []

    def _query_with_reranking(self, question: str, results: dict) -> tuple[str, list[str]]:
        """Processa resultats amb reranking."""
        # Preparar fragments per al Reranker
        passages = []
        for i in range(len(results['documents'][0])):
            passages.append({
                "id": i,
                "text": results['documents'][0][i],
                "metadata": results['metadatas'][0][i]
            })

        # Executar Reranking
        try:
            rerank_request = RerankRequest(query=question, passages=passages)
            reranked = self.ranker.rerank(rerank_request)
        except Exception as e:
            print(f"⚠️ Error en reranking: {e}. Usant resultats sense reranking.")
            return self._query_without_reranking(results, RAG_N_FINAL)

        # Filtrat per Threshold i formatat final
        formatted_results = []
        sources_used = []
        
        # Només agafem els top N un cop re-puntuats
        for item in reranked[:RAG_N_FINAL]:
            # El score de FlashRank sol ser [0, 1]
            if item['score'] >= RAG_THRESHOLD:
                filename = item['metadata'].get('source', 'Desconegut')
                formatted_results.append(f"[Font: {filename}]\n{item['text']}")
                if filename not in sources_used:
                    sources_used.append(filename)

        context = "\n...\n".join(formatted_results)
        return context, sources_used

    def _query_without_reranking(self, results: dict, n_results: int) -> tuple[str, list[str]]:
        """Processa resultats sense reranking (fallback)."""
        formatted_results = []
        sources_used = []

        for text, metadata, distance in zip(
            results['documents'][0][:n_results],
            results['metadatas'][0][:n_results],
            results['distances'][0][:n_results]
        ):
            # ChromaDB cosinus retorna distància (0=idèntic, 2=oposat)
            # Convertim a similaritat: 1 - dist/2 → [0, 1]
            similarity = 1.0 - (distance / 2.0)

            if similarity >= RAG_THRESHOLD:
                filename = metadata.get('source', 'Desconegut')
                formatted_results.append(f"[Font: {filename}]\n{text}")
                if filename not in sources_used:
                    sources_used.append(filename)

        context = "\n...\n".join(formatted_results)
        return context, sources_used

    # ------------------------------------------------------------------
    # Gestió de documents
    # ------------------------------------------------------------------

    def get_loaded_files(self) -> list[str]:
        """Retorna la llista de fitxers indexats."""
        if self.collection.count() == 0:
            return []
        
        try:
            results = self.collection.get(include=["metadatas"])
            unique_files = {meta['source'] for meta in results.get('metadatas', []) if meta}
            return sorted(list(unique_files))
        except Exception as e:
            print(f"❌ Error obtenint llista de fitxers: {e}")
            return []

    def delete_document(self, filename: str) -> bool:
        """Elimina tots els chunks d'un document."""
        if self.collection.count() == 0:
            return False
        
        try:
            self.collection.delete(where={"source": filename})
            print(f"🗑️ '{filename}' eliminat del RAG.")
            return True
        except Exception as e:
            print(f"❌ Error esborrant '{filename}': {e}")
            return False
