from __future__ import annotations

import hashlib
import json
import pickle
import re
from pathlib import Path
from typing import Any, TYPE_CHECKING

import bm25s
import faiss
import numpy as np
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer

from src.base.models import MinimalSource, LogEvent
from src.interface.colors import Colors as colors

if TYPE_CHECKING:
    from src.interface.interface import Interface


DEFAULT_EMBEDDING_MODEL = (
    "sentence-transformers/all-MiniLM-L6-v2"
)


class SearchEngine:
    """
    Provide BM25-based retrieval with optional query expansion, caching, and
    result reranking.
    """
    def __init__(self, basic_print: bool = True, tui_display: bool = False,
                 return_results: bool = False,
                 ui: Interface | None = None) -> None:
        """
        Initialize an empty search engine and configure its output mode.
        """
        self.retriever: bm25s.BM25 | None = None
        self.sources: list[MinimalSource] = []
        self.symbols: list[list[str]] = []
        self.basic_print: bool = basic_print
        self.tui_display: bool = tui_display
        self.return_results: bool = return_results
        self.ui = ui

    def _tokenize(self, texts: list[str]) -> Any:
        """ Tokenize a collection of texts for BM25 indexing or retrieval. """
        return bm25s.tokenize(texts, lower=True,
                              show_progress=self.basic_print)

    def _expand_query(self, query: str) -> str:
        """ Expand a query with predefined domain-specific search terms. """
        expansions = {
            "openai": ["openai compatible server"],
            "lora": ["lora adapter"],
            "multimodal": ["mm modality"],
            "kv cache": ["key value cache"],
            "scheduler": ["request scheduler"],
            "tokenizer": ["tokenization"],
            "embedding": ["embeddings"],
        }
        lowered = query.lower()
        added: list[str] = []
        for key, values in expansions.items():
            if re.search(rf"\b{re.escape(key)}\b", lowered):
                added.extend(values)
        if not added:
            return query
        return query + " " + " ".join(added)

    def _cache_key(self, query: str, top_k: int, expand_query: bool) -> str:
        """ Generate a stable cache key for a search request. """
        raw = f"{query}|k={top_k}|expand={expand_query}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _cache_path(self, cache_dir: str, cache_key: str) -> Path:
        """ Return the cache file path associated with a cache key. """
        return Path(cache_dir) / f"{cache_key}.json"

    def _load_cache(self, cache_dir: str, query: str, top_k: int,
                    expand_query: bool
                    ) -> list[tuple[MinimalSource, str, float]] | None:
        """ Load cached search results for a matching query if available. """
        path = self._cache_path(cache_dir,
                                self._cache_key(query, top_k, expand_query))
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        cached_results = []
        for item in data:
            source = MinimalSource(**item["source"])
            cached_results.append((source, item["text"], float(item["score"])))
        return cached_results

    def _save_cache(self, cache_dir: str, query: str, top_k: int,
                    expand_query: bool,
                    results: list[tuple[MinimalSource, str, float]]) -> None:
        """ Save search results to the query cache. """
        Path(cache_dir).mkdir(parents=True, exist_ok=True)
        path = self._cache_path(cache_dir,
                                self._cache_key(query, top_k, expand_query))
        data = []
        for source, text, score in results:
            data.append({
                "source": source.model_dump(),
                "text": text,
                "score": score,
            })
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)

    def _symbol_bonus(self, query: str, idx: int) -> float:
        """
        Compute a relevance bonus based on matching extracted code symbols.
        """
        if idx >= len(self.symbols):
            return 0.0
        query_words = {
            word.lower()
            for word in re.findall(r"\w+", query)
        }
        bonus = 0.0
        for symbol in self.symbols[idx]:
            symbol_words = set(self._split_symbol(symbol))
            common_words = query_words & symbol_words
            bonus += len(common_words)
        return bonus

    def _split_symbol(self, symbol: str) -> list[str]:
        """ Split a symbol name into lowercase searchable words. """
        parts = re.findall(
            r"[A-Z]+(?=[A-Z][a-z]|$)|[A-Z]?[a-z]+",
            symbol
        )
        return [part.lower() for part in parts]

    def build_index(self, texts: list[str], sources: list[MinimalSource],
                    symbols: list[list[str]] | None = None) -> None:
        """ Build the BM25 index and store the associated source metadata. """
        self.sources = sources
        self.symbols = symbols if symbols is not None else [[] for _ in texts]
        corpus_tokens = self._tokenize(texts)
        self.retriever = bm25s.BM25(corpus=texts)
        if self.retriever:
            self.retriever.index(corpus_tokens, show_progress=self.basic_print)
        if self.basic_print:
            print(f"Index done : {colors.BASE_GREEN}{len(texts)}{colors.RESET}"
                  " indexed chunks.")
        elif self.tui_display:
            self._emit(
                LogEvent(
                    source="index",
                    type="info",
                    message="Index done : ",
                    text_var=f"{len(texts)}",
                    message_end=" indexed chunks."))

    def save(self, path: str) -> None:
        """ Save the retrieval index and its associated metadata to disk. """
        save_dir = Path(path)
        save_dir.mkdir(parents=True, exist_ok=True)
        if self.retriever:
            self.retriever.save(save_dir, show_progress=self.basic_print)
        with open(save_dir / "sources.pkl", "wb") as f:
            pickle.dump(self.sources, f)
        with open(save_dir / "symbols.pkl", "wb") as f:
            pickle.dump(self.symbols, f)
        if self.basic_print:
            print(f"Index and sources saved in {colors.BASE_BR_CYAN}{path}"
                  f"{colors.RESET}")
        elif self.tui_display:
            self._emit(
                LogEvent(
                    source="index",
                    type="info",
                    message="Index and sources saved in ",
                    text_var=f"{path}",
                    message_end="."))

    def load(self, path: str, requester: str = "") -> None:
        """ Load a retrieval index and its associated metadata from disk. """
        load_dir = Path(path)
        if not load_dir.exists():
            raise FileNotFoundError(f"{colors.BASE_RED}ERROR{colors.RESET}: "
                                    f"Index folder {path} does not exist!")
        self.retriever = bm25s.BM25.load(load_dir, load_corpus=True)
        with open(load_dir / "sources.pkl", "rb") as f:
            self.sources = pickle.load(f)
        symbols_file = load_dir / "symbols.pkl"
        if symbols_file.exists():
            with open(symbols_file, "rb") as f:
                self.symbols = pickle.load(f)
        else:
            self.symbols = [[] for _ in self.sources]
        if self.basic_print:
            print(f"Loaded index: {colors.BASE_GREEN}{len(self.sources)}"
                  f"{colors.RESET} chunks ready.")
        elif self.tui_display:
            self._emit(
                LogEvent(
                    source=requester,
                    type="info",
                    message="Loaded index: ",
                    text_var=f"{len(self.sources)}",
                    message_end=" chunks ready."))

    def _raw_query(self, search_query: str, top_k: int,
                   use_ast_bonus: bool = True
                   ) -> list[tuple[int, MinimalSource, str, float]]:
        """ Retrieve raw BM25 search results before optional reranking. """
        if not self.retriever or not self.sources:
            raise ValueError(f"{colors.BASE_RED}ERROR{colors.RESET}:"
                             "Index not initiated nor loaded.")
        query_tokens = self._tokenize([search_query])
        candidate_k = min(max(top_k * 2, top_k), len(self.sources))
        results = self.retriever.retrieve(query_tokens, k=candidate_k)
        if isinstance(results, tuple):
            indices_matrice, scores_matrice = results
        else:
            indices_matrice = getattr(results,
                                      "indices",
                                      results.get("indices"))
            scores_matrice = getattr(results,
                                     "scores",
                                     results.get("scores"))
        indices_top = indices_matrice[0]
        scores_top = scores_matrice[0]
        final_results: list[tuple[int, MinimalSource, str, float]] = []
        for i in range(len(indices_top)):
            val = indices_top[i]
            idx_val: Any = (
                val.get("id", val.get("index", 0))
                if isinstance(val, dict) else val
            )
            idx = int(idx_val)
            score = float(scores_top[i])
            if use_ast_bonus:
                score += 0.25 * self._symbol_bonus(search_query, idx)
            source = self.sources[idx]
            raw_content = self.retriever.corpus[idx]
            if isinstance(raw_content, dict):
                text = str(raw_content.get("text", ""))
            elif isinstance(raw_content, list):
                text = " ".join(raw_content)
            else:
                text = str(raw_content)
            final_results.append((idx, source, text, score))
        final_results.sort(key=lambda item: item[3], reverse=True)
        return final_results[:top_k]

    def _merge_results(
            self,
            base_results: list[tuple[int, MinimalSource, str, float]],
            expanded_results: list[tuple[int, MinimalSource, str, float]],
            top_k: int,
            expanded_weight: float = 0.25
            ) -> list[tuple[MinimalSource, str, float]]:
        """ Merge and rerank results from the original and expanded queries """
        merged: dict[int, tuple[MinimalSource, str, float]] = {}
        for idx, source, text, score in base_results:
            merged[idx] = (source, text, score)
        for idx, source, text, score in expanded_results:
            if idx in merged:
                old_source, old_text, old_score = merged[idx]
                merged[idx] = (old_source, old_text,
                               old_score + score * expanded_weight)
            else:
                merged[idx] = (source, text, score * expanded_weight)
        sorted_results = sorted(
            merged.values(),
            key=lambda item: item[2],
            reverse=True
        )
        return sorted_results[:top_k]

    def _is_documentation_source(
            self,
            source: MinimalSource,
            ) -> bool:
        """
        Return True when a source belongs to the documentation tree.
        """
        normalized_path = (
            source.file_path
            .replace("\\", "/")
            .lower()
        )
        return "/docs/" in f"/{normalized_path}"

    def _apply_docs_bonus(
            self,
            results: list[tuple[MinimalSource, str, float]],
            docs_bonus: float,
            top_k: int,
            ) -> list[tuple[MinimalSource, str, float]]:
        """
        Apply a multiplicative score bonus to documentation sources.
        A docs_bonus value of 0.05 represents a five-percent bonus.
        """
        if docs_bonus <= 0.0:
            return results[:top_k]
        reranked_results: list[
            tuple[MinimalSource, str, float]
        ] = []
        for source, text, score in results:
            adjusted_score = score

            if self._is_documentation_source(source):
                adjusted_score *= 1.0 + docs_bonus

            reranked_results.append((
                source,
                text,
                adjusted_score,
            ))
        reranked_results.sort(
            key=lambda item: item[2],
            reverse=True,
        )
        return reranked_results[:top_k]

    def query(
            self,
            user_query: str,
            top_k: int = 5,
            expand_query: bool = False,
            use_cache: bool = False,
            use_ast_bonus: bool = True,
            cache_dir: str = "data/processed/query_cache",
            docs_bonus: float = 0.0,
            ) -> list[tuple[MinimalSource, str, float]]:
        """
        Retrieve search results with optional caching, query expansion, and
        documentation reranking.
        """
        if not self.retriever or not self.sources:
            raise ValueError(f"{colors.BASE_RED}ERROR{colors.RESET}:"
                             "Index not initiated nor loaded.")
        if top_k <= 0:
            raise ValueError("top_k must be greater than zero.")
        if docs_bonus < 0.0:
            raise ValueError("docs_bonus cannot be negative.")
        candidate_k = min(max(top_k * 4, 20), len(self.sources))
        if use_cache:
            cached = self._load_cache(cache_dir, user_query, candidate_k,
                                      expand_query)
            if cached is not None:
                return self._apply_docs_bonus(results=cached,
                                              docs_bonus=docs_bonus,
                                              top_k=top_k)
        if not expand_query:
            raw_results = self._raw_query(user_query, candidate_k,
                                          use_ast_bonus)
            results = [
                (source, text, score)
                for _, source, text, score in raw_results
            ]
        else:
            expanded_query = self._expand_query(user_query)
            if expanded_query == user_query:
                raw_results = self._raw_query(user_query, candidate_k,
                                              use_ast_bonus)
                results = [
                    (source, text, score)
                    for _, source, text, score in raw_results
                ]
            else:
                base_results = self._raw_query(user_query, candidate_k,
                                               use_ast_bonus)
                expanded_results = self._raw_query(expanded_query, candidate_k,
                                                   use_ast_bonus)
                results = self._merge_results(
                    base_results=base_results,
                    expanded_results=expanded_results,
                    top_k=candidate_k, expanded_weight=0.25)
        if use_cache:
            self._save_cache(cache_dir, user_query, candidate_k, expand_query,
                             results)
        return self._apply_docs_bonus(results=results, docs_bonus=docs_bonus,
                                      top_k=top_k)

    def _emit(self, event: LogEvent) -> None:
        """ Forward a log event to the attached terminal interface. """
        if self.ui is not None:
            self.ui.receive_event(event)


class VectorIndexMetadata(BaseModel):
    """
    Describe a persistent semantic vector index.
    """
    version: int = 1
    model_name: str
    dimension: int
    chunk_count: int
    normalized: bool = True


class VectorSearchEngine:
    """
    Build and query a CPU semantic vector index.
    """
    def __init__(
        self,
        model_name: str = DEFAULT_EMBEDDING_MODEL,
        basic_print: bool = True,
        tui_display: bool = False,
        return_results: bool = False,
        ui: Interface | None = None,
    ) -> None:
        """
        Initialize an empty semantic search engine.
        """
        self.model_name = model_name
        self.basic_print = basic_print
        self.tui_display = tui_display
        self.return_results = return_results
        self.ui = ui
        self.model: SentenceTransformer | None = None
        self.index: Any | None = None
        self.sources: list[MinimalSource] = []
        self.texts: list[str] = []
        self.chunk_ids: list[str] = []
        self.embeddings: np.ndarray | None = None
        self.embeddings_reused: int = 0
        self.embeddings_generated: int = 0

    @staticmethod
    def _chunk_id(source: MinimalSource, text: str) -> str:
        """ Returns a stable identifier for one chunk. """
        raw = (f"{source.file_path}\0"
               f"{source.first_character_index}\0"
               f"{source.last_character_index}\0"
               f"{text}")
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _load_model(self) -> SentenceTransformer:
        """
        Load the embedding model only when it is first needed.
        """
        if self.model is None:
            self.model = SentenceTransformer(self.model_name, device="cpu")
        return self.model

    def _encode(self, texts: list[str],
                show_progress: bool = True) -> np.ndarray:
        """
        Encode and normalize texts as float32 vectors.
        """
        if not texts:
            raise ValueError("Cannot encode an empty text collection.")
        model = self._load_model()
        raw_embeddings = model.encode(texts, batch_size=32,
                                      show_progress_bar=show_progress,
                                      convert_to_numpy=True,
                                      normalize_embeddings=True)
        embeddings = np.asarray(raw_embeddings, dtype=np.float32)
        if embeddings.ndim != 2:
            raise ValueError("The embedding model returned an invalid "
                             "vector matrix.")
        if embeddings.shape[0] != len(texts):
            raise ValueError("Embedding count does not match text count.")
        return np.ascontiguousarray(embeddings, dtype=np.float32)

    def _cached_embeddings(self) -> dict[str, np.ndarray]:
        """
        Return cached embeddings indexed by stable chunk identifier.
        """
        if self.embeddings is None:
            return {}
        if not self.chunk_ids:
            return {}
        if len(self.chunk_ids) != len(self.embeddings):
            return {}
        return {
            chunk_id: embedding
            for chunk_id, embedding in zip(self.chunk_ids, self.embeddings,
                                           strict=True)}

    def build_index(
        self,
        texts: list[str],
        sources: list[MinimalSource],
    ) -> None:
        """
        Build or incrementally update the semantic vector index.
        """
        if len(texts) != len(sources):
            raise ValueError("Cannot build vector index: texts and sources "
                             "have different lengths.")
        if not texts:
            raise ValueError("Cannot build vector index from an empty corpus.")
        cached_embeddings = self._cached_embeddings()
        current_chunk_ids = [
            self._chunk_id(source, text)
            for source, text in zip(sources, texts, strict=True)
        ]
        missing_positions: list[int] = []
        missing_texts: list[str] = []
        for position, chunk_id in enumerate(current_chunk_ids):
            if chunk_id not in cached_embeddings:
                missing_positions.append(position)
                missing_texts.append(texts[position])
        self.embeddings_reused = (
            len(current_chunk_ids) - len(missing_positions))
        self.embeddings_generated = len(missing_positions)
        generated_embeddings: np.ndarray | None = None
        if missing_texts:
            generated_embeddings = self._encode(missing_texts)
        dimension: int
        if cached_embeddings:
            first_cached_embedding = next(iter(cached_embeddings.values()))
            dimension = int(first_cached_embedding.shape[0])
        elif generated_embeddings is not None:
            dimension = int(generated_embeddings.shape[1])
        else:
            raise RuntimeError("Cannot determine semantic embedding "
                               "dimension.")
        current_embeddings = np.empty(
            (len(current_chunk_ids), dimension), dtype=np.float32)
        generated_position = 0
        for position, chunk_id in enumerate(current_chunk_ids):
            cached_embedding = cached_embeddings.get(chunk_id)
            if cached_embedding is not None:
                if cached_embedding.shape != (dimension,):
                    raise RuntimeError("Cached embedding dimension is "
                                       "inconsistent with the current vector "
                                       "index.")
                current_embeddings[position] = cached_embedding
                continue
            if generated_embeddings is None:
                raise RuntimeError("A missing chunk has no generated "
                                   "embedding.")
            current_embeddings[position] = generated_embeddings[
                generated_position
            ]
            generated_position += 1
        current_embeddings = np.ascontiguousarray(current_embeddings,
                                                  dtype=np.float32)
        self.index = faiss.IndexFlatIP(dimension)
        self.index.add(current_embeddings)
        self.texts = list(texts)
        self.sources = list(sources)
        self.chunk_ids = current_chunk_ids
        self.embeddings = current_embeddings

    def save(self, path: str | Path) -> None:
        """
        Persist the FAISS index, corpus metadata and texts.
        """
        if self.index is None:
            raise ValueError("No semantic index has been built.")
        if not self.sources or not self.texts:
            raise ValueError("Semantic index metadata is empty.")
        save_dir = Path(path)
        save_dir.mkdir(parents=True, exist_ok=True)
        index_file = save_dir / "index.faiss"
        sources_file = save_dir / "sources.pkl"
        chunk_ids_file = save_dir / "chunk_ids.pkl"
        embeddings_file = save_dir / "embeddings.npy"
        texts_file = save_dir / "texts.pkl"
        metadata_file = save_dir / "metadata.json"
        dimension = int(self.index.d)
        chunk_count = int(self.index.ntotal)
        metadata = VectorIndexMetadata(model_name=self.model_name,
                                       dimension=dimension,
                                       chunk_count=chunk_count)
        temporary_index = save_dir / "index.faiss.tmp"
        temporary_sources = save_dir / "sources.pkl.tmp"
        temporary_chunk_ids = save_dir / "chunk_ids.pkl.tmp"
        temporary_embeddings = save_dir / "embeddings.npy.tmp"
        temporary_texts = save_dir / "texts.pkl.tmp"
        temporary_metadata = save_dir / "metadata.json.tmp"
        if self.embeddings is None:
            raise RuntimeError("Cannot save vector index: embeddings are not "
                               "available.")
        try:
            faiss.write_index(self.index, str(temporary_index))
            with temporary_sources.open("wb") as file:
                pickle.dump(self.sources, file)
            with temporary_texts.open("wb") as file:
                pickle.dump(self.texts, file)
            with temporary_chunk_ids.open("wb") as file:
                pickle.dump(self.chunk_ids, file)
            with temporary_embeddings.open("wb") as file:
                np.save(file, self.embeddings)
            temporary_metadata.write_text(metadata.model_dump_json(indent=2),
                                          encoding="utf-8")
            temporary_index.replace(index_file)
            temporary_sources.replace(sources_file)
            temporary_texts.replace(texts_file)
            temporary_metadata.replace(metadata_file)
            temporary_chunk_ids.replace(chunk_ids_file)
            temporary_embeddings.replace(embeddings_file)
        except Exception:
            for temporary_file in (temporary_index, temporary_sources,
                                   temporary_texts, temporary_metadata,
                                   temporary_chunk_ids, temporary_embeddings):
                if temporary_file.exists():
                    temporary_file.unlink()
            raise
        if self.basic_print:
            print(f"Semantic index saved in {colors.BASE_BR_CYAN}{save_dir}"
                  f"{colors.RESET}.")
        elif self.tui_display:
            self._emit(
                LogEvent(source="index", type="info",
                         message="Semantic index saved in ",
                         text_var=str(save_dir), message_end="."))

    def load(self, path: str | Path, requester: str = "") -> None:
        """
        Load a persistent semantic vector index.
        """
        load_dir = Path(path)
        index_file = load_dir / "index.faiss"
        sources_file = load_dir / "sources.pkl"
        texts_file = load_dir / "texts.pkl"
        metadata_file = load_dir / "metadata.json"
        chunk_ids_file = load_dir / "chunk_ids.pkl"
        embeddings_file = load_dir / "embeddings.npy"
        required_files = (index_file, sources_file, texts_file, metadata_file)
        missing_files = [
            file_path.name for file_path in required_files
            if not file_path.exists()]
        if missing_files:
            raise FileNotFoundError("Semantic index is incomplete. Missing: "
                                    + ", ".join(missing_files))
        metadata_content = metadata_file.read_text(encoding="utf-8")
        metadata = VectorIndexMetadata.model_validate_json(metadata_content)
        loaded_index = faiss.read_index(str(index_file))
        with sources_file.open("rb") as file:
            loaded_sources = pickle.load(file)
        with texts_file.open("rb") as file:
            loaded_texts = pickle.load(file)
        with chunk_ids_file.open("rb") as file:
            loaded_chunk_ids = pickle.load(file)
        loaded_embeddings = np.load(embeddings_file)
        if not isinstance(loaded_sources, list):
            raise ValueError("Invalid semantic sources file.")
        if not isinstance(loaded_texts, list):
            raise ValueError("Invalid semantic texts file.")
        if int(loaded_index.d) != metadata.dimension:
            raise ValueError("Semantic index dimension does not match its "
                             "metadata.")
        if int(loaded_index.ntotal) != metadata.chunk_count:
            raise ValueError("Semantic index size does not match its "
                             "metadata.")
        if len(loaded_sources) != metadata.chunk_count:
            raise ValueError("Semantic source count does not match the vector "
                             "index.")
        if len(loaded_texts) != metadata.chunk_count:
            raise ValueError("Semantic text count does not match the vector "
                             "index.")
        self.model_name = metadata.model_name
        self.index = loaded_index
        self.sources = loaded_sources
        self.texts = loaded_texts
        self.chunk_ids = loaded_chunk_ids
        self.embeddings = loaded_embeddings
        if self.basic_print:
            print(f"Loaded semantic index: {colors.BASE_GREEN}"
                  f"{metadata.chunk_count}{colors.RESET} chunks ready.")
        elif self.tui_display:
            self._emit(
                LogEvent(source=requester, type="info",
                         message="Loaded semantic index: ",
                         text_var=str(metadata.chunk_count),
                         message_end=" chunks ready."))

    def query(
        self,
        user_query: str,
        top_k: int = 5,
    ) -> list[tuple[MinimalSource, str, float]]:
        """
        Retrieve the chunks closest to the query embedding.
        """
        if self.index is None:
            raise ValueError("Semantic index not initiated nor loaded.")
        if not self.sources or not self.texts:
            raise ValueError("Semantic corpus metadata is empty.")
        if not user_query.strip():
            raise ValueError("Query cannot be empty.")
        if top_k <= 0:
            raise ValueError("top_k must be greater than zero.")
        query_embedding = self._encode([user_query], show_progress=False)
        result_count = min(top_k, len(self.sources))
        scores_matrix, indices_matrix = self.index.search(query_embedding,
                                                          result_count)
        results: list[tuple[MinimalSource, str, float]] = []
        for index_value, score_value in zip(indices_matrix[0],
                                            scores_matrix[0]):
            index_position = int(index_value)
            if index_position < 0:
                continue
            results.append((self.sources[index_position],
                            self.texts[index_position], float(score_value)))
        return results

    def _emit(self, event: LogEvent) -> None:
        """ Forward a log event to the attached terminal interface. """
        if self.ui is not None:
            self.ui.receive_event(event)


class HybridSearchEngine:
    """
    Combine lexical and semantic retrieval with Reciprocal Rank Fusion.
    """
    def __init__(
        self,
        bm25_engine: SearchEngine,
        vector_engine: VectorSearchEngine,
        rrf_constant: int = 60,
        candidate_multiplier: int = 4,
        minimum_candidates: int = 20,
    ) -> None:
        """
        Initialize the hybrid retriever and validate its retrieval indices.
        """
        if rrf_constant <= 0:
            raise ValueError("rrf_constant must be greater than zero.")
        if candidate_multiplier <= 0:
            raise ValueError("candidate_multiplier must be greater than zero.")
        if minimum_candidates <= 0:
            raise ValueError("minimum_candidates must be greater than zero.")
        self.bm25_engine = bm25_engine
        self.vector_engine = vector_engine
        self.rrf_constant = rrf_constant
        self.candidate_multiplier = candidate_multiplier
        self.minimum_candidates = minimum_candidates
        self._validate_indices()

    @staticmethod
    def _source_key(
        source: MinimalSource,
    ) -> tuple[str, int, int]:
        """ Return the stable location key identifying one retrieved chunk. """
        return (source.file_path, int(source.first_character_index),
                int(source.last_character_index))

    def _validate_indices(self) -> None:
        """ Ensure lexical and semantic indices describe the same corpus. """
        if self.bm25_engine.retriever is None:
            raise ValueError("BM25 index not initiated nor loaded.")
        if not self.bm25_engine.sources:
            raise ValueError("BM25 source metadata is empty.")
        if self.vector_engine.index is None:
            raise ValueError("Semantic index not initiated nor loaded.")
        if not self.vector_engine.sources:
            raise ValueError("Semantic source metadata is empty.")
        if not self.vector_engine.texts:
            raise ValueError("Semantic text metadata is empty.")
        bm25_sources = self.bm25_engine.sources
        vector_sources = self.vector_engine.sources
        if len(bm25_sources) != len(vector_sources):
            raise ValueError("BM25 and semantic indices contain different "
                             "numbers of chunks. Rebuild both indices "
                             "together.")
        bm25_keys = [self._source_key(source) for source in bm25_sources]
        vector_keys = [self._source_key(source) for source in vector_sources]
        if bm25_keys != vector_keys:
            raise ValueError("BM25 and semantic indices were built from "
                             "different corpora. Rebuild both indices "
                             "together.")

    def query(
        self,
        user_query: str,
        top_k: int = 5,
        expand_query: bool = False,
        use_cache: bool = False,
        use_ast_bonus: bool = True,
        cache_dir: str = "data/processed/query_cache",
        docs_bonus: float = 0.0,
    ) -> list[tuple[MinimalSource, str, float]]:
        """
        Retrieve and fuse BM25 and semantic results using
        Reciprocal Rank Fusion.
        """
        if not user_query.strip():
            raise ValueError("Query cannot be empty.")
        if top_k <= 0:
            raise ValueError("top_k must be greater than zero.")
        if docs_bonus < 0.0:
            raise ValueError("docs_bonus cannot be negative.")
        corpus_size = len(self.bm25_engine.sources)
        candidate_k = min(
            max(top_k * self.candidate_multiplier, self.minimum_candidates),
            corpus_size)

        bm25_results = self.bm25_engine.query(user_query=user_query,
                                              top_k=candidate_k,
                                              expand_query=expand_query,
                                              use_cache=use_cache,
                                              use_ast_bonus=use_ast_bonus,
                                              cache_dir=cache_dir,
                                              docs_bonus=docs_bonus)
        semantic_results = self.vector_engine.query(user_query=user_query,
                                                    top_k=candidate_k)
        fused_scores: dict[tuple[str, int, int], float] = {}
        fused_results: dict[tuple[str, int, int],
                            tuple[MinimalSource, str]] = {}
        best_ranks: dict[tuple[str, int, int], int] = {}
        self._add_ranked_results(results=bm25_results,
                                 fused_scores=fused_scores,
                                 fused_results=fused_results,
                                 best_ranks=best_ranks)
        self._add_ranked_results(results=semantic_results,
                                 fused_scores=fused_scores,
                                 fused_results=fused_results,
                                 best_ranks=best_ranks)
        ordered_keys = sorted(fused_scores,
                              key=lambda key: (-fused_scores[key],
                                               best_ranks[key], key))
        return [(fused_results[key][0], fused_results[key][1],
                 fused_scores[key]) for key in ordered_keys[:top_k]]

    def _add_ranked_results(
        self,
        results: list[tuple[MinimalSource, str, float]],
        fused_scores: dict[tuple[str, int, int], float],
        fused_results: dict[
            tuple[str, int, int],
            tuple[MinimalSource, str],
        ],
        best_ranks: dict[tuple[str, int, int], int],
    ) -> None:
        """
        Add one ranked result list to the current RRF aggregation.
        """
        for rank, (source, text, _) in enumerate(results, start=1):
            key = self._source_key(source)
            reciprocal_rank = 1.0 / (self.rrf_constant + rank)
            fused_scores[key] = (fused_scores.get(key, 0.0) + reciprocal_rank)
            if key not in fused_results:
                fused_results[key] = (source, text)
            previous_best_rank = best_ranks.get(key)
            if (previous_best_rank is None or rank < previous_best_rank):
                best_ranks[key] = rank
