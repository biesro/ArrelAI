"""
ChromaStore — Arrel AI RAG Engine
===================================
Gestiona la memòria vectorial del sistema usant ChromaDB i Ollama embeddings.

Novetats v4:
- Threshold de similaritat configurable (filtra context irrellevant)
- Retorna les fonts usades per mostrar-les a la UI
- Distància cosinus normalitzada per tenir scores coherents
- Embedding model configurable via .env
"""

import chromadb
import uuid
import os
import ollama
from flashrank import Ranker, RerankRequest # Necessari: pip install flashrank

from ..config import RAG_THRESHOLD, RAG_N_RESULTS, EMBED_MODEL

class ChromaStore:
    def __init__(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(current_dir, "../../"))
        db_path = os.path.join(project_root, "chroma_db")

        os.makedirs(db_path, exist_ok=True)
        self.embed_model = EMBED_MODEL
        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = self.client.get_or_create_collection(
            name="arrel_knowledge",
            metadata={"hnsw:space": "cosine"}
        )
        
        # Inicialitzem el Reranker (baixarà el model de ~150MB el primer cop)
        # Corre en CPU, no gasta VRAM de la GPU
        print("💡 Carregant Reranker lleuger (FlashRank)...")
        self.ranker = Ranker(model_name="ms-marco-MiniLM-L-12-v2")

    def query(self, question: str, n_results: int = 15) -> tuple[str, list[str]]:
        """
        RAG amb Pipeline de dos estadis:
        1. Retrieval (ChromaDB) - Busca 15 candidats per similitud vectorial.
        2. Reranking (FlashRank) - Re-puntua i tria els 5 millors segons rellevància real.
        """
        if self.collection.count() == 0:
            return "", []

        try:
            # 1. Recuperació Vectorial inicial
            response = ollama.embed(model=self.embed_model, input=question)
            query_embedding = response['embeddings'][0]

            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=min(n_results, self.collection.count()),
                include=["documents", "metadatas", "distances"]
            )

            if not results['documents'] or not results['documents'][0]:
                return "", []

            # 2. Preparar fragments per al Reranker
            passages = []
            for i in range(len(results['documents'][0])):
                passages.append({
                    "id": i,
                    "text": results['documents'][0][i],
                    "metadata": results['metadatas'][0][i]
                })

            # 3. Executar Reranking
            rerank_request = RerankRequest(query=question, passages=passages)
            reranked = self.ranker.rerank(rerank_request)

            # 4. Filtrat per Threshold i formatat final
            formatted_results = []
            sources_used = []
            
            # Només agafem els top 5 un cop re-puntuats
            for item in reranked[:5]:
                # El score de FlashRank sol ser [0, 1]
                if item['score'] >= RAG_THRESHOLD:
                    filename = item['metadata'].get('source', 'Desconegut')
                    formatted_results.append(f"[Font: {filename}]\n{item['text']}")
                    if filename not in sources_used:
                        sources_used.append(filename)

            context = "\n...\n".join(formatted_results)
            return context, sources_used

        except Exception as e:
            print(f"❌ Error en la consulta RAG (Reranker): {e}")
            return "", []

    # ------------------------------------------------------------------
    # Gestió de documents
    # ------------------------------------------------------------------

    def get_loaded_files(self) -> list[str]:
        if self.collection.count() == 0:
            return []
        results = self.collection.get(include=["metadatas"])
        unique_files = {meta['source'] for meta in results.get('metadatas', []) if meta}
        return sorted(list(unique_files))

    def delete_document(self, filename: str) -> bool:
        if self.collection.count() == 0:
            return False
        try:
            self.collection.delete(where={"source": filename})
            print(f"🗑️ '{filename}' eliminat del RAG.")
            return True
        except Exception as e:
            print(f"❌ Error esborrant '{filename}': {e}")
            return False