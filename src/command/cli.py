from __future__ import annotations

import json
import pickle
import sys
import time
from pathlib import Path
from typing import cast, TYPE_CHECKING

from llama_cpp import Llama, CreateCompletionResponse
from tqdm import tqdm

from src.base.models import RagDataset, MinimalSearchResults, MinimalAnswer
from src.base.models import StudentSearchResults, StudentSearchResultsAndAnswer
from src.base.models import EvaluateResult, LogEvent
from src.base.utils import RagUtils as utils
from src.engine.engine import SearchEngine, VectorSearchEngine
from src.engine.engine import HybridSearchEngine
from src.engine.ingest import Ingest, ChunkResult
from src.engine.manifest import Manifest
from src.interface.colors import Colors as colors

if TYPE_CHECKING:
    from src.interface.interface import Interface

DATA_PATH = "data/raw/vllm-0.10.1"
INDEX_PATH = "data/processed/bm25_index"
CHUNKS_PATH = "data/processed/chunks"
MANIFEST_PATH = "data/processed/index_manifest.json"
DATASET_PATH = "data/datasets/UnansweredQuestions/dataset_docs_public.json"
DATASET_ANSWERED = "data/datasets/AnsweredQuestions/dataset_docs_public.json"
SAVE_DIRECTORY = "data/output/search_results"
SEARCH_RESULT_PATH = "data/output/search_results/dataset_docs_public.json"
SAVE_RESULTS_ANSWER_DIRECTORY = "data/output/search_results_and_answer"
VECTOR_INDEX_PATH = "data/vector/vector_index"


class CLIError(Exception):
    """Represent an error raised while executing a CLI command."""
    pass


class CLI:
    """Coordinate indexing, retrieval, generation, and evaluation commands."""
    def __init__(self) -> None:
        """Initialize the command interface without an attached terminal UI."""
        self._ui: Interface | None = None

    def index(
        self,
        max_chunk_size: int = 800,
        data_path: str = DATA_PATH,
        index_path: str = INDEX_PATH,
        chunks_path: str = CHUNKS_PATH,
        manifest_path: str = MANIFEST_PATH,
        hybrid_retrieval: bool = False,
        vector_index_path: str = VECTOR_INDEX_PATH,
        basic_print: bool = True,
        tui_display: bool = False,
        return_results: bool = False,
    ) -> None:
        """
        Build and persist the retrieval indices from a source repository.
        """

        if int(basic_print) + int(tui_display) + int(return_results) != 1:
            print("\n\n\n\33[1;31m  Exactly ONE display mode must be "
                  "enabled\33[0m\n\n")
            sys.exit(1)

        if basic_print:
            print(f"\33[2A {colors.BASE_BROWN}╚" + "═" * 30 + "╦" + "═" * 74
                  + "╦")
            print(" " * 32 + f"{colors.BASE_BROWN}║{colors.BASE_BR_CYAN}"
                  + " " * 22 + " ╻ ┏┓╻╺┳┓┏━╸╻ ╻   "
                  + f"{colors.BASE_CYAN}┏┳┓┏━┓╺┳┓┏━╸"
                  + " " * 22 + f"{colors.BASE_BROWN}║")
            print(" " * 32 + f"{colors.BASE_BROWN}║{colors.BASE_BR_CYAN}"
                  + " " * 22 + " ┃ ┃┗┫ ┃┃┣╸ ┏╋┛   "
                  + f"{colors.BASE_CYAN}┃┃┃┃ ┃ ┃┃┣╸ "
                  + " " * 22 + f"{colors.BASE_BROWN}║")
            print(" " * 32 + f"{colors.BASE_BROWN}║{colors.BASE_BR_CYAN}"
                  + " " * 22 + " ╹ ╹ ╹╺┻┛┗━╸╹ ╹   "
                  + f"{colors.BASE_CYAN}╹ ╹┗━┛╺┻┛┗━╸"
                  + " " * 22 + f"{colors.BASE_BROWN}║")
            print(" " * 32 + f"{colors.BASE_BROWN}╚" + "═" * 74 + "╝")
            print(f"{colors.RESET}")
        elif tui_display:
            self._emit(
                LogEvent(source="index", type="start",
                         message=" Index command launched "))

        if hybrid_retrieval:
            if basic_print:
                print(f"Semantic index    : {colors.BASE_GREEN}enabled"
                      f"{colors.RESET}")
            elif tui_display:
                self._emit(
                    LogEvent(source="index", type="info",
                             message="Semantic vector index: ",
                             text_var="enabled", message_end="."))

        if basic_print:
            print(f"{colors.BASE_PURPLE}──╼━━═══{colors.RESET} Ingestion of "
                  f"{colors.BASE_BR_CYAN}{data_path}{colors.RESET} "
                  f"{colors.BASE_PURPLE}═══━━╾──{colors.RESET}")
        elif tui_display:
            self._emit(
                LogEvent(source="index", type="info",
                         message="Ingestion of data from ",
                         text_var=f"{data_path}", message_end="..."))

        start_time = time.perf_counter()
        ingest = Ingest(max_chunk_size=max_chunk_size, overlap=150,
                        basic_print=basic_print, tui_display=tui_display,
                        return_results=return_results, ui=self._ui)
        engine = SearchEngine(basic_print=basic_print, tui_display=tui_display,
                              return_results=return_results, ui=self._ui)
        vector_engine: VectorSearchEngine | None = None

        if hybrid_retrieval:
            vector_engine = VectorSearchEngine(basic_print=basic_print,
                                               tui_display=tui_display,
                                               return_results=return_results,
                                               ui=self._ui)
            vector_index_directory = Path(vector_index_path)
            if vector_index_directory.is_dir():
                try:
                    vector_engine.load(vector_index_path)
                    if basic_print:
                        print("Loaded existing semantic cache: "
                              f"{len(vector_engine.chunk_ids)} embeddings.")
                except (
                    FileNotFoundError,
                    OSError,
                    RuntimeError,
                    ValueError,
                    pickle.PickleError,
                ) as error:
                    if basic_print:
                        print("Existing semantic cache could not be reused; "
                              f"a full rebuild will be performed: {error}")

        try:
            chunks_dir = Path(chunks_path)
            chunks_file = chunks_dir / "chunks.jsonl"
            previous_manifest = Manifest.load(manifest_path)
            files, current_manifest = ingest.scan_repository(data_path)
            manifest_compatible = (
                previous_manifest is not None
                and previous_manifest.is_compatible(
                    max_chunk_size=max_chunk_size,
                    overlap=ingest.overlap))
            cache_available = chunks_file.exists()
            cached_chunks: dict[str, list[ChunkResult]] = {}
            if manifest_compatible and cache_available:
                try:
                    cached_chunks = ingest.load_cached_chunks(
                        chunks_file
                    )
                except (OSError, ValueError) as error:
                    if basic_print:
                        print(f"{colors.BASE_BROWN}WARNING{colors.RESET}: "
                              f"chunk cache cannot be reused: {error}")
                        print("A complete ingestion will be performed.")
                    elif tui_display:
                        self._emit(
                            LogEvent(source="index", type="warning",
                                     message=("Chunk cache cannot be reused. "
                                              "A complete ingestion will be "
                                              "performed.")))
                    previous_manifest = None
                    cached_chunks = {}
            else:
                previous_manifest = None
            manifest_changes = current_manifest.compare(previous_manifest)
            reusable_paths = set(manifest_changes.unchanged)
            ingestion_result = ingest.run_incremental(
                root_dir=data_path, files=files,
                reusable_paths=reusable_paths, cached_chunks=cached_chunks)
            if basic_print:
                print(f"Files found       : {colors.BASE_BR_CYAN}"
                      f"{manifest_changes.files_found}{colors.RESET}")
                print(f"Files reused      : {colors.BASE_BR_CYAN}"
                      f"{ingestion_result.files_reused}{colors.RESET}")
                print(f"Files re-indexed  : {colors.BASE_GREEN}"
                      f"{ingestion_result.files_reindexed}{colors.RESET}")
                print(f"  Added           : {colors.BASE_GREEN}"
                      f"{len(manifest_changes.added)}{colors.RESET}")
                print(f"  Modified        : {colors.BASE_BROWN}"
                      f"{len(manifest_changes.modified)}{colors.RESET}")
                print(f"Files removed     : {colors.BASE_RED}"
                      f"{len(manifest_changes.removed)}{colors.RESET}")
                print(f"Chunks reused     : {colors.BASE_BR_CYAN}"
                      f"{ingestion_result.chunks_reused}{colors.RESET}")
                print(f"Chunks generated  : {colors.BASE_GREEN}"
                      f"{ingestion_result.chunks_generated}{colors.RESET}")
            elif tui_display:
                sheet = [
                    "Files found", str(manifest_changes.files_found),
                    "Files reused", str(ingestion_result.files_reused),
                    "Files re-indexed", str(ingestion_result.files_reindexed),
                    "      added", str(len(manifest_changes.added)),
                    "      modified", str(len(manifest_changes.modified)),
                    "Files removed", str(len(manifest_changes.removed)),
                    "Chunks reused", str(ingestion_result.chunks_reused),
                    "Chunks generated", str(ingestion_result.chunks_generated)
                ]
                self._emit(
                    LogEvent(source="index", type="files_analysis_sheet",
                             message="Files analysis", fields=sheet))
            if not ingestion_result.texts:
                if basic_print:
                    print("No chunks available. Check your data path.")
                elif tui_display:
                    self._emit(
                        LogEvent(source="index", type="error",
                                 message=("No chunks available. "
                                          "Check your data path.")))
                return
            if basic_print:
                print(f"Corpus contains {colors.BASE_BR_CYAN}"
                      f"{len(ingestion_result.texts)}{colors.RESET} chunks. "
                      f"Building BM25 index...")
            elif tui_display:
                self._emit(
                    LogEvent(source="index", type="info",
                             message="Corpus contains ",
                             text_var=str(len(ingestion_result.texts)),
                             message_end=(" chunks. Building BM25 index...")))
            engine.build_index(ingestion_result.texts,
                               ingestion_result.sources,
                               ingestion_result.symbols)
            if vector_engine is not None:
                if basic_print:
                    print("Building semantic vector index with "
                          f"{colors.BASE_BR_CYAN}{vector_engine.model_name}"
                          f"{colors.RESET}...")
                elif tui_display:
                    self._emit(
                        LogEvent(source="index", type="info",
                                 message=("Building semantic vector "
                                          "index with "),
                                 text_var=vector_engine.model_name,
                                 message_end="..."))
                vector_engine.build_index(ingestion_result.texts,
                                          ingestion_result.sources)
                if basic_print:
                    print("Semantic embeddings reused    : "
                          f"{colors.BASE_BR_CYAN}"
                          f"{vector_engine.embeddings_reused}"
                          f"{colors.RESET}")
                    print("Semantic embeddings generated : "
                          f"{colors.BASE_BR_CYAN}"
                          f"{vector_engine.embeddings_generated}"
                          f"{colors.RESET}")
            if basic_print:
                print(f"Saving index to {colors.BASE_BR_CYAN}"
                      f"{index_path}{colors.RESET}...")
            elif tui_display:
                self._emit(
                    LogEvent(source="index", type="info",
                             message="Saving index to ",
                             text_var=f"{index_path}",
                             message_end="..."))
            engine.save(index_path)
            if vector_engine is not None:
                vector_engine.save(vector_index_path)
            chunks_dir.mkdir(parents=True, exist_ok=True)
            temporary_chunks_file = chunks_file.with_suffix(
                chunks_file.suffix + ".tmp")
            try:
                with temporary_chunks_file.open("w", encoding="utf-8") as file:
                    for source, text, symbols in zip(
                        ingestion_result.sources,
                        ingestion_result.texts,
                        ingestion_result.symbols,
                    ):
                        record = {
                            "file_path": source.file_path,
                            "first_character_index": (
                                source.first_character_index
                            ),
                            "last_character_index": (
                                source.last_character_index
                            ),
                            "text": text,
                            "symbols": symbols,
                        }
                        file.write(
                            json.dumps(record, ensure_ascii=False,) + "\n")
                temporary_chunks_file.replace(chunks_file)
            except OSError:
                if temporary_chunks_file.exists():
                    temporary_chunks_file.unlink()
                raise
            current_manifest.save(manifest_path)
            elapsed = time.perf_counter() - start_time
            if basic_print:
                print("Ingestion complete! Indices saved under "
                      f"{colors.BASE_BR_CYAN}data/processed/{colors.RESET}")
                print(f"Time: {colors.BASE_BR_CYAN}{elapsed:.2f}"
                      f"{colors.RESET}s")
            elif tui_display:
                self._emit(
                    LogEvent(source="index", type="info",
                             message=("Ingestion complete! "
                                      "Indices saved under "),
                             text_var="data/processed/", message_end="."))
                self._emit(
                    LogEvent(source="index", type="finish",
                             message=" Index done ", duration=elapsed))

        except Exception as error:
            if basic_print:
                print(f"{colors.BASE_RED}ERROR{colors.RESET} "
                      f"during ingestion: {error}")
                sys.exit(1)
            elif tui_display:
                self._emit(
                    LogEvent(source="index", type="error",
                             message=f"during ingestion: {error}"))

    def search(self,
               query: str,
               k: int = 10,
               index_path: str = INDEX_PATH,
               vector_index_path: str = VECTOR_INDEX_PATH,
               basic_print: bool = True,
               tui_display: bool = False,
               return_results: bool = False,
               use_cache: bool = True,
               use_ast_bonus: bool = True,
               hybrid_retrieval: bool = False,
               docs_bonus: float = 0.05) -> None | str:
        """
        Search the indexed corpus and return the most relevant matching chunks.
        """

        if int(basic_print) + int(tui_display) + int(return_results) != 1:
            print("\n\n\n\33[1;31m  Exactly ONE display mode must be "
                  "enabled\33[0m\n\n")
            sys.exit()

        engine = SearchEngine(basic_print=basic_print, tui_display=tui_display,
                              return_results=return_results)

        if not Path(index_path).exists():
            if basic_print:
                print(f"{colors.BASE_RED}ERROR{colors.RESET}: Index not found "
                      f"at {index_path}. "
                      "Please run the 'index' command first.")
            elif tui_display:
                self._emit(
                    LogEvent(source="search", type="error",
                             message=f"Index not found at {index_path}. Please"
                                     + " run the 'index' command first"))
            return None

        if basic_print:
            print(f"\33[2A {colors.BASE_BROWN}╚" + "═" * 30 + "╦" +
                  "═" * 74 + "╦")
            print(" " * 32 + f"{colors.BASE_BROWN}║{colors.BASE_BR_CYAN}" +
                  " " * 21 +
                  f"┏━┓┏━╸┏━┓┏━┓┏━╸╻ ╻  {colors.BASE_CYAN}┏┳┓┏━┓╺┳┓┏━╸" +
                  " " * 21 + f"{colors.BASE_BROWN}║")
            print(" " * 32 + f"{colors.BASE_BROWN}║{colors.BASE_BR_CYAN}" +
                  " " * 21 +
                  f"┗━┓┣╸ ┣━┫┣┳┛┃  ┣━┫  {colors.BASE_CYAN}┃┃┃┃ ┃ ┃┃┣╸ " +
                  " " * 21 + f"{colors.BASE_BROWN}║")
            print(" " * 32 + f"{colors.BASE_BROWN}║{colors.BASE_BR_CYAN}" +
                  " " * 21 +
                  f"┗━┛┗━╸╹ ╹╹┗╸┗━╸╹ ╹  {colors.BASE_CYAN}╹ ╹┗━┛╺┻┛┗━╸" +
                  " " * 21 + f"{colors.BASE_BROWN}║")
            print(" " * 32 + f"{colors.BASE_BROWN}╚" + "═" * 74 + "╝")
            print(f"{colors.RESET}")
        elif tui_display:
            self._emit(
                LogEvent(source="search", type="start",
                         message=" Search command launched "))

        if basic_print:
            print(f"{colors.BASE_PURPLE}──╼━━═══{colors.RESET} Loading "
                  f"existing index from {colors.BASE_BR_CYAN}{index_path}"
                  f"{colors.RESET} {colors.BASE_PURPLE}═══━━╾──{colors.RESET}")
        elif tui_display:
            self._emit(
                LogEvent(source="search", type="info",
                         message="Loading existing index from ",
                         text_var=f"{index_path}", message_end="."))

        try:
            engine.load(index_path, requester="search")
        except FileNotFoundError as e:
            message = f"Index file not found: {e.filename}"
            if basic_print:
                print(f"{colors.BASE_RED}ERROR{colors.RESET}: {message}")
            elif tui_display:
                self._emit(
                    LogEvent(source="search", type="error", message=message))
            return None
        except Exception as e:
            if basic_print:
                print(f"{colors.BASE_RED}ERROR{colors.RESET}: {e}")
            elif tui_display:
                self._emit(
                    LogEvent(source="search", type="error", message=f"{e}"))
            return None

        retrieval_engine: SearchEngine | HybridSearchEngine = engine

        if hybrid_retrieval:
            vector_index_directory = Path(vector_index_path)
            if not vector_index_directory.exists():
                message = (f"Semantic index not found at {vector_index_path}. "
                           "Falling back to BM25 retrieval. ")
                if basic_print:
                    print(f"{colors.BASE_BROWN}WARNING{colors.RESET}: "
                          f"{message}")
                elif tui_display:
                    self._emit(
                        LogEvent(source="search", type="warning",
                                 message=message))
            else:
                vector_engine = VectorSearchEngine(
                    basic_print=basic_print,
                    tui_display=tui_display,
                    return_results=return_results,
                    ui=self._ui)
                try:
                    vector_engine.load(vector_index_path, requester="search")
                    retrieval_engine = HybridSearchEngine(
                        bm25_engine=engine,
                        vector_engine=vector_engine)
                except FileNotFoundError as e:
                    missing_file = (e.filename if e.filename is not None
                                    else str(e))
                    message = ("Semantic index is incomplete. Missing file: "
                               f"{missing_file}. Falling back to BM25 "
                               "retrieval.")
                    if basic_print:
                        print(f"{colors.BASE_BROWN}WARNING{colors.RESET}: "
                              f"{message}")
                    elif tui_display:
                        self._emit(
                            LogEvent(source="search", type="warning",
                                     message=message))
                except Exception as e:
                    message = ("Cannot initialize hybrid retrieval: "
                               f"{e}. Falling back to BM25 retrieval.")
                    if basic_print:
                        print(f"{colors.BASE_BROWN}WARNING{colors.RESET}: "
                              f"{message}")
                    elif tui_display:
                        self._emit(
                            LogEvent(source="search", type="warning",
                                     message=message))

        if basic_print:
            print(f"SEARCHING FOR: '{colors.BASE_BR_CYAN}{query}"
                  f"{colors.RESET}'")
        elif tui_display:
            self._emit(
                LogEvent(source="search", type="info",
                         message="Searching for: ", text_var=f"{query}",
                         message_end=""))

        try:
            t_total = time.perf_counter()
            results = retrieval_engine.query(user_query=query, top_k=k,
                                             use_cache=use_cache,
                                             use_ast_bonus=use_ast_bonus,
                                             docs_bonus=docs_bonus)
            results_txt: str = ""
            for i, (source, text, score) in enumerate(results, 1):
                if basic_print:
                    print(f"\n{colors.BASE_PURPLE}─━═{colors.RESET} "
                          f"Result {colors.BASE_BR_CYAN}#{i:02}{colors.RESET} "
                          f"- Score {colors.BASE_BR_CYAN}{score:.2f}"
                          f"{colors.RESET} {colors.BASE_PURPLE}═━─"
                          f"{colors.RESET}")
                    print(f"File: {colors.BASE_BR_CYAN}{source.file_path}"
                          f"{colors.RESET}")
                    print(f"Indices: {colors.BASE_BR_CYAN}"
                          f"{source.first_character_index}{colors.RESET} "
                          f"to {colors.BASE_BR_CYAN}"
                          f"{source.last_character_index}"
                          f"{colors.RESET}")
                    text_len = 42
                    while (score > 0 and
                           query.lower() not in text.lower()[:text_len]
                           and text_len < len(text)):
                        text_len += 42
                    text_len += 42
                    text_len = min(text_len, len(text))
                    lines = (text[:text_len].strip() + "...").splitlines()
                    max_line_len = 0
                    for line in lines:
                        if len(line) > max_line_len:
                            max_line_len = len(line)
                    max_line_len += 4
                    print(f"{colors.BASE_BR_CYAN}╭" +
                          "─" * (max_line_len // 3 - 1) +
                          "━" * (max_line_len - (max_line_len // 3) * 2) +
                          "─" * (max_line_len // 3 - 1) + f"╮{colors.RESET}")
                    for line in lines:
                        line_len = len(line)
                        line = line.replace(f"{query}",
                                            f"{colors.REVERSE}{query}"
                                            f"{colors.RESET}")
                        line = line.replace(f"{query.upper()}",
                                            f"{colors.REVERSE}{query.upper()}"
                                            f"{colors.RESET}")
                        line = line.replace(f"{query.lower()}",
                                            f"{colors.REVERSE}{query.lower()}"
                                            f"{colors.RESET}")
                        line = line.replace(f"{query.capitalize()}",
                                            f"{colors.REVERSE}"
                                            f"{query.capitalize()}"
                                            f"{colors.RESET}")
                        print(f"{colors.BASE_BR_CYAN}│{colors.RESET} " +
                              line + " " * (max_line_len - line_len - 4) +
                              f" {colors.BASE_BR_CYAN}│{colors.RESET}")
                    print(f"{colors.BASE_BR_CYAN}╰" +
                          "─" * (max_line_len // 3 - 1) +
                          "━" * (max_line_len - (max_line_len // 3) * 2) +
                          "─" * (max_line_len // 3 - 1) + f"╯{colors.RESET}")
                elif tui_display:
                    text_len = 42
                    while (score > 0 and
                           query.lower() not in text.lower()[:text_len]
                           and text_len < len(text)):
                        text_len += 42
                    text_len += 42
                    text_len = min(text_len, len(text))
                    text_part = text[:text_len].strip() + "..."
                    text_part = "\n".join(text_part.splitlines()[2:])
                    self._emit(
                        LogEvent(source="search", type="extract",
                                 message=source.file_path, text_var=query,
                                 message_end=text_part, value=score,
                                 int_a=i, int_b=source.first_character_index,
                                 int_c=source.last_character_index))
                elif return_results:
                    text_len = 42
                    while (score > 0 and
                           query.lower() not in text.lower()[:text_len]
                           and text_len < len(text)):
                        text_len += 42
                    text_len += 42
                    text_len = min(text_len, len(text))
                    text_part = text[:text_len].strip() + "..."
                    text_part = "\n".join(text_part.splitlines()[2:])
                    results_txt += (f"FOUND IN {source.file_path} ("
                                    + f"{int(source.first_character_index)}"
                                    + " to "
                                    + f"{int(source.last_character_index)}"
                                    + "):\n"
                                    + f"{text_part}\n"
                                    + "-" * 42 + " "
                                    + f"Score: {score:.2f}"
                                    + " " + "-" * 42 + "\n\n")
            elapsed = time.perf_counter() - t_total
            if not basic_print and tui_display:
                self._emit(
                    LogEvent(source="search", type="finish",
                             message=" Search done ", duration=elapsed))
            if return_results:
                return results_txt

        except Exception as e:
            if basic_print:
                print(f"{colors.BASE_RED}ERROR{colors.RESET}"
                      f" during query: {e}")
            elif tui_display:
                self._emit(
                    LogEvent(source="search", type="error",
                             message=f"during query: {e}"))

        return None

    def search_dataset(self,
                       dataset_path: str = DATASET_PATH,
                       k: int = 10,
                       save_directory: str = SAVE_DIRECTORY,
                       index_path: str = INDEX_PATH,
                       vector_index_path: str = VECTOR_INDEX_PATH,
                       basic_print: bool = True,
                       tui_display: bool = False,
                       return_results: bool = False,
                       expand_query: bool = False,
                       use_cache: bool = True,
                       use_ast_bonus: bool = True,
                       hybrid_retrieval: bool = False,
                       docs_bonus: float = 0.05) -> None:
        """
        Search every question in a dataset and save the retrieved sources.
        """

        if int(basic_print) + int(tui_display) + int(return_results) != 1:
            print("\n\n\n\33[1;31m  Exactly ONE display mode must be "
                  "enabled\33[0m\n\n")
            sys.exit()

        dataset_file = Path(dataset_path)
        if not dataset_file.exists():
            if basic_print:
                print(f"{colors.BASE_RED}ERROR{colors.RESET}: Dataset not "
                      f"found at {colors.BASE_BR_CYAN}{dataset_path}"
                      f"{colors.RESET}")
            elif tui_display:
                self._emit(
                    LogEvent(
                        source="search_dataset",
                        type="error",
                        message=f"Dataset not found at {dataset_path}."))
            return

        engine = SearchEngine(basic_print=basic_print, tui_display=tui_display,
                              return_results=return_results)

        if not Path(index_path).exists():
            if basic_print:
                print(f"{colors.BASE_RED}ERROR{colors.RESET}: Index not found "
                      f"at {index_path}. "
                      "Please run the 'index' command first.")
            elif tui_display:
                self._emit(
                    LogEvent(source="search_dataset", type="start",
                             message=" Search_Dataset command launched "))
                self._emit(
                    LogEvent(source="search_dataset", type="error",
                             message=f"Index not found at {index_path}. Please"
                                     " run the 'index' command first."))
            return

        if basic_print:
            print(f"\33[2A {colors.BASE_BROWN}╚" + "═" * 30 + "╦" +
                  "═" * 74 + "╦")
            print(" " * 32 + f"{colors.BASE_BROWN}║{colors.BASE_BR_CYAN}" +
                  " " * 9 +
                  "┏━┓┏━╸┏━┓┏━┓┏━╸╻ ╻  ╺┳┓┏━┓╺┳╸┏━┓┏━┓┏━╸╺┳╸   "
                  f"{colors.BASE_CYAN}┏┳┓┏━┓╺┳┓┏━╸" +
                  " " * 9 + f"{colors.BASE_BROWN}║")
            print(" " * 32 + f"{colors.BASE_BROWN}║{colors.BASE_BR_CYAN}" +
                  " " * 9 +
                  "┗━┓┣╸ ┣━┫┣┳┛┃  ┣━┫   ┃┃┣━┫ ┃ ┣━┫┗━┓┣╸  ┃    "
                  f"{colors.BASE_CYAN}┃┃┃┃ ┃ ┃┃┣╸ " +
                  " " * 9 + f"{colors.BASE_BROWN}║")
            print(" " * 32 + f"{colors.BASE_BROWN}║{colors.BASE_BR_CYAN}" +
                  " " * 9 +
                  "┗━┛┗━╸╹ ╹╹┗╸┗━╸╹ ╹  ╺┻┛╹ ╹ ╹ ╹ ╹┗━┛┗━╸ ╹    "
                  f"{colors.BASE_CYAN}╹ ╹┗━┛╺┻┛┗━╸" +
                  " " * 9 + f"{colors.BASE_BROWN}║")
            print(" " * 32 + f"{colors.BASE_BROWN}╚" + "═" * 74 + "╝")
            print(f"{colors.RESET}")
        elif tui_display:
            self._emit(
                LogEvent(source="search_dataset", type="start",
                         message=" Search_Dataset command launched "))

        if basic_print:
            print(f"{colors.BASE_PURPLE}──╼━━═══{colors.RESET} Loading "
                  f"existing index from {colors.BASE_BR_CYAN}{index_path}"
                  f"{colors.RESET} {colors.BASE_PURPLE}═══━━╾──{colors.RESET}")
        elif tui_display:
            self._emit(
                LogEvent(source="search_dataset", type="info",
                         message="Loading existing index from ",
                         text_var=f"{index_path}", message_end="."))

        try:
            engine.load(index_path, requester="search_dataset")
        except FileNotFoundError as e:
            message = f"Index file not found: {e.filename}"
            if basic_print:
                print(f"{colors.BASE_RED}ERROR{colors.RESET}: {message}")
            elif tui_display:
                self._emit(
                    LogEvent(source="search_dataset", type="error",
                             message=message))
            return
        except Exception as e:
            if basic_print:
                print(f"{colors.BASE_RED}ERROR{colors.RESET}: {e}")
            elif tui_display:
                self._emit(
                    LogEvent(source="search_dataset", type="error",
                             message=f"{e}"))
            return

        retrieval_engine: SearchEngine | HybridSearchEngine = engine

        if hybrid_retrieval:
            vector_index_directory = Path(vector_index_path)
            if not vector_index_directory.exists():
                message = (f"Semantic index not found at {vector_index_path}. "
                           "Falling back to BM25 retrieval. ")
                if basic_print:
                    print(f"{colors.BASE_BROWN}WARNING{colors.RESET}: "
                          f"{message}")
                elif tui_display:
                    self._emit(
                        LogEvent(source="search_dataset", type="warning",
                                 message=message))
            else:
                vector_engine = VectorSearchEngine(
                    basic_print=basic_print,
                    tui_display=tui_display,
                    return_results=return_results,
                    ui=self._ui)
                try:
                    vector_engine.load(vector_index_path,
                                       requester="search_dataset")
                    retrieval_engine = HybridSearchEngine(
                        bm25_engine=engine,
                        vector_engine=vector_engine)
                except FileNotFoundError as e:
                    missing_file = (e.filename if e.filename is not None
                                    else str(e))
                    message = ("Semantic index is incomplete. Missing file: "
                               f"{missing_file}. Falling back to BM25 "
                               "retrieval.")
                    if basic_print:
                        print(f"{colors.BASE_BROWN}WARNING{colors.RESET}: "
                              f"{message}")
                    elif tui_display:
                        self._emit(
                            LogEvent(source="search_dataset", type="warning",
                                     message=message))
                except Exception as e:
                    message = ("Cannot initialize hybrid retrieval: "
                               f"{e}. Falling back to BM25 retrieval.")
                    if basic_print:
                        print(f"{colors.BASE_BROWN}WARNING{colors.RESET}: "
                              f"{message}")
                    elif tui_display:
                        self._emit(
                            LogEvent(source="search_dataset", type="warning",
                                     message=message))

        if basic_print:
            print(f"\n{colors.BASE_PURPLE}──╼━━═══{colors.RESET} Loading "
                  f"dataset from {colors.BASE_BR_CYAN}{dataset_path}"
                  f"{colors.RESET} {colors.BASE_PURPLE}═══━━╾──{colors.RESET}")
        elif tui_display:
            self._emit(
                LogEvent(source="search_dataset", type="info",
                         message="Loading dataset from ",
                         text_var=f"{dataset_path}", message_end="."))

        try:
            dataset_content = dataset_file.read_text(encoding="utf-8")
            dataset = RagDataset.model_validate_json(dataset_content)
        except Exception as e:
            if basic_print:
                print(f"{colors.BASE_RED}ERROR{colors.RESET}: Failed to parse "
                      f"dataset JSON: {e}")
            elif tui_display:
                self._emit(
                    LogEvent(source="search_dataset", type="error",
                             message=f"Failed to parse dataset JSON: {e}"))
            return

        all_results: list[MinimalSearchResults] = []
        t_total = time.perf_counter()

        def search_dataset_loop() -> None:
            """
            Search the current dataset question and
            append its retrieval result.
            """
            try:
                results = retrieval_engine.query(user_query=q.question,
                                                 top_k=k,
                                                 expand_query=expand_query,
                                                 use_cache=use_cache,
                                                 use_ast_bonus=use_ast_bonus,
                                                 docs_bonus=docs_bonus)
                retrieved_sources = [res[0] for res in results]
                minimal_res = MinimalSearchResults(
                    question_id=q.question_id,
                    question=q.question,
                    retrieved_sources=retrieved_sources)
                all_results.append(minimal_res)
            except Exception as e:
                if basic_print:
                    print(f"\n{colors.BASE_RED}ERROR{colors.RESET} during "
                          f"query '{q.question_id}': {e}")
                elif tui_display:
                    self._emit(
                        LogEvent(source="search_dataset", type="error",
                                 message=(f"during query '{q.question_id}': "
                                          f"{e}")))
                all_results.append(MinimalSearchResults(
                    question_id=q.question_id,
                    question=q.question,
                    retrieved_sources=[]))

        if basic_print:
            for q in tqdm(dataset.rag_questions, desc="Searching queries",
                          colour="cyan"):
                search_dataset_loop()
        elif tui_display:
            self._emit(
                LogEvent(source="search_dataset", type="progbar",
                         message="Searching queries", value=-1000.0))
            for i, q in enumerate(dataset.rag_questions):
                search_dataset_loop()
                self._emit(
                    LogEvent(source="search_dataset", type="progbar",
                             message="Searching queries",
                             value=((i + 1) / len(dataset.rag_questions) * 100)
                             ))
            self._emit(
                LogEvent(source="search_dataset", type="progbar",
                         message="Searching queries", value=1000.0))

        final_output = StudentSearchResults(search_results=all_results, k=k)
        elapsed = time.perf_counter() - t_total

        if basic_print:
            print(f"\nSearch completed in {colors.BASE_BR_CYAN}"
                  f"{elapsed:.2f}{colors.RESET}s for "
                  f"{colors.BASE_BR_CYAN}{len(all_results)}{colors.RESET}"
                  " queries")
        elif tui_display:
            self._emit(
                LogEvent(source="search_dataset", type="info",
                         message="Search completed for ",
                         text_var=f"{len(all_results)}",
                         message_end=" queries."))

        save_dir = Path(save_directory)
        save_dir.mkdir(parents=True, exist_ok=True)
        out_file = save_dir / dataset_file.name

        try:
            out_file.write_text(final_output.model_dump_json(indent=4),
                                encoding="utf-8")
            if basic_print:
                print(f"\nSaved student_search_results to "
                      f"{colors.BASE_BR_CYAN}{out_file}{colors.RESET}")
            elif tui_display:
                self._emit(
                    LogEvent(source="search_dataset", type="info",
                             message="Saved student_search_result to ",
                             text_var=f"{out_file}", message_end="."))
                self._emit(
                    LogEvent(source="search_dataset", type="finish",
                             message=" Search_Dataset done ",
                             duration=elapsed))
        except Exception as e:
            if basic_print:
                print(f"{colors.BASE_RED}ERROR{colors.RESET}: Failed to save "
                      f"results: {e}")
            elif tui_display:
                self._emit(
                    LogEvent(source="search_dataset", type="error",
                             message=f"Failed to save results: {e}"))

    def answer(self,
               query: str,
               k: int = 10,
               index_path: str = INDEX_PATH,
               vector_index_path: str = VECTOR_INDEX_PATH,
               basic_print: bool = True,
               tui_display: bool = False,
               return_results: bool = False,
               expand_query: bool = False,
               use_cache: bool = True,
               use_ast_bonus: bool = True,
               hybrid_retrieval: bool = False,
               docs_bonus: float = 0.05) -> str | None:
        """
        Retrieve relevant context and generate an answer to a single question.
        """

        if int(basic_print) + int(tui_display) + int(return_results) != 1:
            print("\n\n\n\33[1;31m  Exactly ONE display mode must be "
                  "enabled\33[0m\n\n")
            sys.exit()

        if basic_print:
            print(f"\33[2A {colors.BASE_BROWN}╚" + "═" * 30 + "╦" +
                  "═" * 74 + "╦")
            print(" " * 32 + f"{colors.BASE_BROWN}║{colors.BASE_BR_CYAN}" +
                  " " * 21 +
                  f"┏━┓┏┓╻┏━┓╻ ╻┏━╸┏━┓  {colors.BASE_CYAN}┏┳┓┏━┓╺┳┓┏━╸" +
                  " " * 21 + f"{colors.BASE_BROWN}║")
            print(" " * 32 + f"{colors.BASE_BROWN}║{colors.BASE_BR_CYAN}" +
                  " " * 21 +
                  f"┣━┫┃┗┫┗━┓┃╻┃┣╸ ┣┳┛  {colors.BASE_CYAN}┃┃┃┃ ┃ ┃┃┣╸ " +
                  " " * 21 + f"{colors.BASE_BROWN}║")
            print(" " * 32 + f"{colors.BASE_BROWN}║{colors.BASE_BR_CYAN}" +
                  " " * 21 +
                  f"╹ ╹╹ ╹┗━┛┗┻┛┗━╸╹┗╸  {colors.BASE_CYAN}╹ ╹┗━┛╺┻┛┗━╸" +
                  " " * 21 + f"{colors.BASE_BROWN}║")
            print(" " * 32 + f"{colors.BASE_BROWN}╚" + "═" * 74 + "╝")
            print(f"{colors.RESET}")
        elif tui_display:
            self._emit(
                LogEvent(source="answer", type="start",
                         message=" Answer command launched "))

        try:
            llm = Llama.from_pretrained(repo_id="Qwen/Qwen3-0.6B-GGUF",
                                        filename="*.gguf", n_ctx=4096,
                                        n_threads=None, verbose=False)
            engine = SearchEngine(basic_print=basic_print,
                                  tui_display=tui_display,
                                  return_results=return_results)
        except Exception as e:
            if basic_print:
                print(f"{colors.BASE_RED}ERROR{colors.RESET}: Failed to "
                      f"initialize models: {e}")
            elif tui_display:
                self._emit(
                    LogEvent(source="answer", type="error",
                             message=f"Failed to initialize models: {e}"))
            return None

        if not Path(index_path).exists():
            if basic_print:
                print(f"{colors.BASE_RED}ERROR{colors.RESET}: "
                      f"Index not found at {index_path}. "
                      f"Please run the 'index' command first.")
            elif tui_display:
                self._emit(
                    LogEvent(source="answer", type="error",
                             message=f"Index not found at {index_path}. Please"
                                     + " run the 'index' command first"))
            return None

        if basic_print:
            print(f"\n{colors.BASE_PURPLE}──╼━━═══{colors.RESET} Loading "
                  f"existing index from {colors.BASE_BR_CYAN}{index_path}"
                  f"{colors.RESET} {colors.BASE_PURPLE}═══━━╾──{colors.RESET}")
        elif tui_display:
            self._emit(
                LogEvent(source="answer", type="info",
                         message="Loading existing index from ",
                         text_var=f"{index_path}", message_end="."))

        try:
            engine.load(index_path, requester="answer")
        except FileNotFoundError as e:
            message = f"Index file not found: {e.filename}"
            if basic_print:
                print(f"{colors.BASE_RED}ERROR{colors.RESET}: {message}")
            elif tui_display:
                self._emit(
                    LogEvent(source="answer", type="error", message=message))
            return None
        except Exception as e:
            if basic_print:
                print(f"{colors.BASE_RED}ERROR{colors.RESET}: {e}")
            elif tui_display:
                self._emit(
                    LogEvent(source="answer", type="error", message=f"{e}"))
            return None

        retrieval_engine: SearchEngine | HybridSearchEngine = engine
        hybrid_active = False

        if hybrid_retrieval:
            vector_index_directory = Path(vector_index_path)
            if not vector_index_directory.exists():
                message = (f"Semantic index not found at {vector_index_path}. "
                           "Falling back to BM25 retrieval.")
                if basic_print:
                    print(f"{colors.BASE_BROWN}WARNING{colors.RESET}: "
                          f"{message}")
                elif tui_display:
                    self._emit(
                        LogEvent(source="answer", type="warning",
                                 message=message))
            else:
                vector_engine = VectorSearchEngine(
                    basic_print=basic_print,
                    tui_display=tui_display,
                    return_results=return_results,
                    ui=self._ui,
                )
                try:
                    vector_engine.load(vector_index_path, requester="answer")
                    retrieval_engine = HybridSearchEngine(
                        bm25_engine=engine,
                        vector_engine=vector_engine)
                    hybrid_active = True
                except FileNotFoundError as e:
                    missing_file = (e.filename if e.filename is not None
                                    else str(e))
                    message = ("Semantic index is incomplete. Missing file: "
                               f"{missing_file}. Falling back to BM25 "
                               "retrieval.")
                    if basic_print:
                        print(f"{colors.BASE_BROWN}WARNING{colors.RESET}: "
                              f"{message}")
                    elif tui_display:
                        self._emit(
                            LogEvent(source="answer", type="warning",
                                     message=message))
                except Exception as e:
                    message = ("Cannot initialize hybrid retrieval: "
                               f"{e}. Falling back to BM25 retrieval.")
                    if basic_print:
                        print(f"{colors.BASE_BROWN}WARNING{colors.RESET}: "
                              f"{message}")
                    elif tui_display:
                        self._emit(
                            LogEvent(source="answer", type="warning",
                                     message=message))

        if basic_print:
            print(f"SEARCHING FOR: '{colors.BASE_BR_CYAN}{query}"
                  f"{colors.RESET}'")
        elif tui_display:
            self._emit(
                LogEvent(source="answer", type="info",
                         message="Question asked: ", text_var=f"{query}",
                         message_end=""))

        t = time.perf_counter()

        try:
            results = retrieval_engine.query(user_query=query, top_k=k,
                                             expand_query=expand_query,
                                             use_cache=use_cache,
                                             use_ast_bonus=use_ast_bonus,
                                             docs_bonus=docs_bonus)
            if not results:
                raise ValueError("The retrieval engine returned no results.")
            retrieved_sources = [result[0] for result in results]
            context_text = "\n\n".join(text for _, text, _ in results)
        except Exception as e:
            if basic_print:
                print(f"{colors.BASE_RED}ERROR{colors.RESET} "
                      f"during query: {e}")
            elif tui_display:
                self._emit(
                    LogEvent(source="answer", type="error",
                             message=f"during query: {e}"))
            return None

        all_scores = [score for _, _, score in results]
        top_score = all_scores[0]
        avg_score = sum(all_scores) / len(all_scores)
        dominance_ratio = top_score / avg_score if avg_score > 0 else 0
        insufficient_relevance = (not hybrid_active
                                  and (avg_score < 3 or dominance_ratio > 1.5))

        if insufficient_relevance:
            if basic_print:
                print(f"\n{colors.BASE_BROWN}╭" + "─" * 44 +
                      f"╮{colors.RESET}")
                print(f"{colors.BASE_BROWN}│{colors.RESET}       {colors.BOLD}"
                      f"No relevant{colors.RESET} information found,      "
                      f"{colors.BASE_BROWN}│{colors.RESET}")
                print(f"{colors.BASE_BROWN}│{colors.RESET} cannot answer "
                      f"{colors.BOLD}efficiently{colors.RESET} on this "
                      f"question. {colors.BASE_BROWN}│{colors.RESET}")
                print(f"{colors.BASE_BROWN}│{colors.RESET}              "
                      f"                              {colors.BASE_BROWN}│"
                      f"{colors.RESET}")
                print(f"{colors.BASE_BROWN}│{colors.RESET}              "
                      f"Top score: {colors.ITALIC}{top_score:.2f}"
                      f"{colors.RESET}               {colors.BASE_BROWN}│"
                      f"{colors.RESET}")
                print(f"{colors.BASE_BROWN}│{colors.RESET}              "
                      f"Avg score: {colors.ITALIC}{avg_score:.2f}"
                      f"{colors.RESET}               {colors.BASE_BROWN}│"
                      f"{colors.RESET}")
                print(f"{colors.BASE_BROWN}│{colors.RESET}           Dominance"
                      f" ratio: {colors.ITALIC}{dominance_ratio:.2f}"
                      f"{colors.RESET}            {colors.BASE_BROWN}│"
                      f"{colors.RESET}")
                print(f"{colors.BASE_BROWN}╰" + "─" * 44 +
                      f"╯{colors.RESET}")
            elif tui_display:
                self._emit(
                    LogEvent(source="answer", type="noanswer",
                             float_a=top_score, float_b=avg_score,
                             float_c=dominance_ratio))
                f = time.perf_counter() - t
                self._emit(
                    LogEvent(source="answer", type="finish",
                             message=" Answer done ", duration=f))
            return None

        max_context_chars = 700

        if len(context_text) > max_context_chars:
            context_text = context_text[:max_context_chars]

        prompt = (
            f"<|im_start|>system\n"
            f"You are a strict retrieval-based assistant. "
            f"Answer the question concisely in 1-3 sentences based ONLY "
            f"on the following context.\n\n"
            f"CONTEXT:\n{context_text}\n\n"
            f"Do not use your knowledge. All answers must rely strictly on "
            f"the provided context.\n"
            f"<|im_end|>\n"
            f"<|im_start|>user\n{query}<|im_end|>\n"
            f"<|im_start|>assistant\n<think>\n\n</think>\n"
        )

        try:
            raw_response = llm.create_completion(
                prompt=prompt, max_tokens=48, temperature=0.0,
                stop=["<|im_end|>", "<|endoftext|>"])
            response = cast(CreateCompletionResponse, raw_response)
            generated_text = response["choices"][0]["text"].strip()
        except Exception as e:
            if basic_print:
                print(f"{colors.BASE_RED}ERROR{colors.RESET} during answer "
                      f"generation: {e}")
                f = time.perf_counter() - t
                print(f"time: {colors.BASE_BR_CYAN}{f:.2f}{colors.RESET}s")
            elif tui_display:
                self._emit(
                    LogEvent(source="answer", type="error",
                             message=f"during answer generation: {e}"))
                f = time.perf_counter() - t
                self._emit(
                    LogEvent(source="answer", type="finish",
                             message=" Answer done ", duration=f))
            return None

        answer_obj = MinimalAnswer(question_id="single_query", question=query,
                                   retrieved_sources=retrieved_sources,
                                   answer=generated_text)
        final_output = StudentSearchResultsAndAnswer(
            search_results=[answer_obj], k=k)

        if basic_print:
            print(final_output.model_dump_json(indent=2))
            f = time.perf_counter() - t
            print(f"time: {colors.BASE_BR_CYAN}{f:.2f}{colors.RESET}s\n")
            question_box = f"{colors.BASE_BROWN}╭" + "─" * 88 + "╮\n"
            question_lines = utils.split_words(query, 86)
            for question_line in question_lines:
                question_box += (f"{colors.BASE_BROWN}│ " +
                                 f"{colors.BASE_WHITE}{question_line:^86}"
                                 + f" {colors.BASE_BROWN}│\n")
            question_box += (f"{colors.BASE_BROWN}│ ⸝"
                             + "─" * 86 + "╯\n"
                             + f"{colors.BASE_BROWN}│╱")
            answer_box = (" " * 47 + f"{colors.BASE_BR_CYAN}╭"
                          + "─" * 88 + "╮\n")
            answer_lines = utils.split_words(generated_text, 86)
            for answer_line in answer_lines:
                answer_box += (" " * 49 + f"{colors.BASE_BR_CYAN}│ "
                               + f"{colors.BASE_WHITE}{answer_line:^86}"
                               + f" {colors.BASE_BR_CYAN}│\n")
            answer_box += (" " * 49 + f"{colors.BASE_BR_CYAN}╰" + "─" * 86
                           + "⸜ │\n" + " " * (122 - len(f"{f:.2f}"))
                           + f"{colors.BASE_IT_BR_BLACK}generated in "
                           + f"{colors.BASE_CYAN}{f:.2f}"
                           + f"{colors.BASE_IT_BR_BLACK}s{colors.RESET}"
                           + f"{colors.BASE_BR_CYAN}" + " ╲│\n")
            print(f"{question_box}{colors.RESET}{answer_box}{colors.RESET}")
        elif tui_display:
            self._emit(
                LogEvent(source="answer", type="json",
                         message=final_output.model_dump_json(indent=2)))
            f = time.perf_counter() - t
            self._emit(
                LogEvent(source="answer", type="bubbles",
                         message="unique question", left_box=query,
                         right_box=generated_text, duration=f,
                         int_a=0, int_b=0))
            self._emit(
                LogEvent(source="answer", type="finish",
                         message=" Answer done ", duration=f))
        if return_results:
            return generated_text
        return None

    def answer_dataset(self,
                       student_search_results_path: str = SEARCH_RESULT_PATH,
                       save_directory: str = SAVE_RESULTS_ANSWER_DIRECTORY,
                       max_context_chars: int = 700,
                       basic_print: bool = True,
                       tui_display: bool = False,
                       return_results: bool = False) -> None:
        """
        Generate grounded answers from previously retrieved dataset results.
        """

        if int(basic_print) + int(tui_display) + int(return_results) != 1:
            print("\n\n\n\33[1;31m  Exactly ONE display mode must be "
                  "enabled\33[0m\n\n")
            sys.exit()

        if basic_print:
            print(f"\33[2A {colors.BASE_BROWN}╚" + "═" * 30 + "╦" +
                  "═" * 74 + "╦")
            print(" " * 32 + f"{colors.BASE_BROWN}║{colors.BASE_BR_CYAN}" +
                  " " * 9 + "┏━┓┏┓╻┏━┓╻ ╻┏━╸┏━┓  ╺┳┓┏━┓╺┳╸┏━┓┏━┓┏━╸╺┳╸   "
                  f"{colors.BASE_CYAN}┏┳┓┏━┓╺┳┓┏━╸" + " " * 9 +
                  f"{colors.BASE_BROWN}║")
            print(" " * 32 + f"{colors.BASE_BROWN}║{colors.BASE_BR_CYAN}" +
                  " " * 9 + "┣━┫┃┗┫┗━┓┃╻┃┣╸ ┣┳┛   ┃┃┣━┫ ┃ ┣━┫┗━┓┣╸  ┃    "
                  f"{colors.BASE_CYAN}┃┃┃┃ ┃ ┃┃┣╸ " + " " * 9 +
                  f"{colors.BASE_BROWN}║")
            print(" " * 32 + f"{colors.BASE_BROWN}║{colors.BASE_BR_CYAN}" +
                  " " * 9 + "╹ ╹╹ ╹┗━┛┗┻┛┗━╸╹┗╸  ╺┻┛╹ ╹ ╹ ╹ ╹┗━┛┗━╸ ╹    "
                  f"{colors.BASE_CYAN}╹ ╹┗━┛╺┻┛┗━╸" + " " * 9 +
                  f"{colors.BASE_BROWN}║")
            print(" " * 32 + f"{colors.BASE_BROWN}╚" + "═" * 74 + "╝")
            print(f"{colors.RESET}")
        elif tui_display:
            self._emit(
                LogEvent(source="answer_dataset", type="start",
                         message=" Answer_Dataset command launched "))

        results_file = Path(student_search_results_path)

        if not results_file.exists():
            if basic_print:
                print(f"{colors.BASE_RED}ERROR{colors.RESET}: File not found "
                      f"at {colors.BASE_BR_CYAN}{student_search_results_path}"
                      f"{colors.RESET}")
            elif tui_display:
                self._emit(
                    LogEvent(source="answer_dataset", type="error",
                             message="File not found at "
                                     f"{student_search_results_path}."))
            return

        try:
            student_results = StudentSearchResults.model_validate_json(
                results_file.read_text(encoding="utf-8"))
        except Exception as e:
            if basic_print:
                print(f"{colors.BASE_RED}ERROR{colors.RESET}: Failed to parse "
                      f"student search results JSON: {e}")
            elif tui_display:
                self._emit(
                    LogEvent(source="answer_dataset", type="error",
                             message="Failed to parse student search results "
                                     f"JSON: {e}"))
            return

        try:
            llm = Llama.from_pretrained(repo_id="Qwen/Qwen3-0.6B-GGUF",
                                        filename="*.gguf", n_ctx=4096,
                                        n_threads=None, verbose=False)
        except Exception as e:
            if basic_print:
                print(f"{colors.BASE_RED}ERROR{colors.RESET}: Failed to load "
                      f"model: {e}")
            elif tui_display:
                self._emit(
                    LogEvent(source="answer_dataset", type="error",
                             message=f"Failed to load model: {e}"))
            return

        if basic_print:
            print(f"\n{colors.BASE_PURPLE}──╼━━═══{colors.RESET} Loaded "
                  f"{colors.BASE_BR_CYAN}{len(student_results.search_results)}"
                  f"{colors.RESET} questions from {colors.BASE_BR_CYAN}"
                  f"{student_search_results_path}{colors.RESET} "
                  f"{colors.BASE_PURPLE}═══━━╾──{colors.RESET}\n")
        elif tui_display:
            self._emit(
                LogEvent(source="answer_dataset", type="info",
                         message="Loaded ",
                         text_var=f"{len(student_results.search_results)}",
                         message_end=" questions from "
                                     f"{student_search_results_path}."))

        all_answers: list[MinimalAnswer] = []
        t_total = time.perf_counter()

        def answer_dataset_loop() -> None:
            """
            Generate and store an answer for the current dataset item.
            """
            t_q = time.perf_counter()
            context_parts: list[str] = []
            for src in item.retrieved_sources:
                src_file = Path(src.file_path)
                try:
                    file_text = src_file.read_text(encoding="utf-8",
                                                   errors="ignore")
                    chunk = file_text[src.first_character_index:
                                      src.last_character_index]
                    context_parts.append(chunk)
                except Exception:
                    continue
            context_text = "\n\n".join(context_parts)
            if len(context_text) > max_context_chars:
                context_text = context_text[:max_context_chars]
            prompt = (
                "<|im_start|>system\n"
                "You are a strict retrieval-based assistant. "
                "Answer the question concisely in 1-3 sentences based ONLY "
                "on the following context.\n\n"
                f"CONTEXT:\n{context_text}\n\n"
                "Do not use your knowledge. All answers must rely strictly on"
                " the provided context.\n"
                "<|im_end|>\n"
                f"<|im_start|>user\n{item.question}<|im_end|>\n"
                "<|im_start|>assistant\n<think>\n\n</think>\n"
            )
            try:
                raw_response = llm.create_completion(
                    prompt=prompt,
                    max_tokens=48,
                    temperature=0.0,
                    stop=["<|im_end|>", "<|endoftext|>"])
                response = cast(CreateCompletionResponse, raw_response)
                answer_text = response["choices"][0]["text"].strip()
            except Exception as e:
                if basic_print:
                    print(f"\n{colors.BASE_RED}ERROR{colors.RESET} "
                          "generating answer for '"
                          f"{colors.BASE_BR_CYAN}{item.question_id}"
                          f"{colors.RESET}': {e}")
                elif tui_display:
                    self._emit(
                        LogEvent(source="answer_dataset", type="error",
                                 message="generating answer for '"
                                         f"{item.question_id}': {e}"))
                answer_text = ""

            if basic_print:
                question_box = f"{colors.BASE_BROWN}╭" + "─" * 88 + "╮\n"
                question_lines = utils.split_words(item.question, 86)
                for question_line in question_lines:
                    question_box += (f"{colors.BASE_BROWN}│ " +
                                     f"{colors.BASE_WHITE}{question_line:^86}"
                                     + f" {colors.BASE_BROWN}│\n")
                question_box += (f"{colors.BASE_BROWN}│ ⸝"
                                 + "─" * 86 + "╯\n"
                                 + f"{colors.BASE_BROWN}│╱")
                answer_box = (" " * 47 + f"{colors.BASE_BR_CYAN}╭"
                              + "─" * 88 + "╮\n")
                answer_lines = utils.split_words(answer_text, 86)
                for answer_line in answer_lines:
                    answer_box += (" " * 49 + f"{colors.BASE_BR_CYAN}│ "
                                   + f"{colors.BASE_WHITE}{answer_line:^86}"
                                   + f" {colors.BASE_BR_CYAN}│\n")
                elapsed = time.perf_counter() - t_q
                answer_box += (" " * 49 + f"{colors.BASE_BR_CYAN}╰" + "─" * 86
                               + "⸜ │\n" + " " * (112 - len(f"{elapsed:.2f}"))
                               + f"{colors.BASE_IT_BR_BLACK}generated in "
                               + f"{colors.BASE_CYAN}"
                               + f"{elapsed:.2f}"
                               + f"{colors.BASE_IT_BR_BLACK}s "
                               + f"({count_items:03}/{nb_items:03})"
                               + f"{colors.RESET}"
                               + f"{colors.BASE_BR_CYAN}" + " ╲│\n")
                tqdm.write(" " * 29 + f"{colors.BASE_IT_BR_BLACK}" + "─" * 21 +
                           f" {item.question_id} " + "─" * 21 +
                           f"{colors.RESET}\n"
                           f"{question_box}{colors.RESET}"
                           f"{answer_box}{colors.RESET}")
            elif tui_display:
                self._emit(
                    LogEvent(source="answer_dataset", type="bubbles",
                             message=item.question_id,
                             left_box=item.question,
                             right_box=answer_text,
                             duration=time.perf_counter() - t_q,
                             int_a=nb_items, int_b=count_items))
            all_answers.append(MinimalAnswer(
                question_id=item.question_id,
                question=item.question,
                retrieved_sources=item.retrieved_sources,
                answer=answer_text))

        nb_items = len(student_results.search_results)
        count_items = 1
        if basic_print:
            for item in tqdm(student_results.search_results, desc="Answering",
                             colour="cyan"):
                answer_dataset_loop()
                count_items += 1
        elif tui_display:
            self._emit(
                LogEvent(source="answer_dataset", type="progbar",
                         message="Answering", value=-1000.0))
            for i, item in enumerate(student_results.search_results):
                answer_dataset_loop()
                count_items += 1
                self._emit(
                    LogEvent(source="answer_dataset", type="progbar",
                             message="Answering",
                             value=((i + 1)
                                    / len(student_results.search_results)
                                    * 100)))
            self._emit(
                LogEvent(source="answer_dataset", type="progbar",
                         message="Answering", value=1000.0))

        elapsed = time.perf_counter() - t_total

        if basic_print:
            print(f"\nTotal time: {colors.BASE_BR_CYAN}"
                  f"{elapsed:.2f}{colors.RESET}s "
                  f"({colors.ITALIC}{len(all_answers)} questions"
                  f"{colors.RESET})")
        elif tui_display:
            self._emit(
                LogEvent(source="answer_dataset", type="info",
                         message="Answered ",
                         text_var=f"{len(all_answers)}",
                         message_end=" questions."))

        final_output = StudentSearchResultsAndAnswer(
            search_results=all_answers,
            k=student_results.k)
        save_dir = Path(save_directory)
        save_dir.mkdir(parents=True, exist_ok=True)
        out_file = save_dir / Path(student_search_results_path).name

        try:
            out_file.write_text(final_output.model_dump_json(indent=4),
                                encoding="utf-8")
            if basic_print:
                print("\nSaved student_search_results_and_answer to "
                      f"{colors.BASE_BR_CYAN}{out_file}{colors.RESET}")
            elif tui_display:
                self._emit(
                    LogEvent(source="answer_dataset", type="info",
                             message="Saved student_search_results_and_answer "
                                     + "to ",
                             text_var=f"{out_file}", message_end="."))
                self._emit(
                    LogEvent(source="answer_dataset", type="finish",
                             message=" Answer_Dataset done ",
                             duration=elapsed))
        except Exception as e:
            if basic_print:
                print(f"{colors.BASE_RED}ERROR{colors.RESET}: Failed to "
                      f"save results: {e}")
            elif tui_display:
                self._emit(
                    LogEvent(source="answer_dataset", type="error",
                             message=f"Failed to save results: {e}"))

    def evaluate(self,
                 student_search_results_path: str = SEARCH_RESULT_PATH,
                 dataset_path: str = DATASET_ANSWERED,
                 k: int = 10,
                 basic_print: bool = True,
                 tui_display: bool = False,
                 return_results: bool = False) -> EvaluateResult | None:
        """
        Evaluate retrieval results against the answered reference dataset.
        """

        if int(basic_print) + int(tui_display) + int(return_results) != 1:
            print("\n\n\n\33[1;31m  Exactly ONE display mode must be "
                  "enabled\33[0m\n\n")
            sys.exit()

        results_file = Path(student_search_results_path)
        if not results_file.exists():
            if basic_print:
                print(f"{colors.BASE_RED}ERROR{colors.RESET}: File not found "
                      f"at {colors.BASE_BR_CYAN}{student_search_results_path}"
                      f"{colors.RESET}")
            return None

        valid_file = Path(dataset_path)
        if not valid_file.exists():
            if basic_print:
                print(f"{colors.BASE_RED}ERROR{colors.RESET}: File not found "
                      f"at {colors.BASE_BR_CYAN}{dataset_path}{colors.RESET}")
            return None

        student_valid = False

        try:
            student_results = StudentSearchResults.model_validate_json(
                results_file.read_text(encoding="utf-8")
            )
            student_valid = True
        except Exception as e:
            if basic_print:
                print(f"{colors.BASE_RED}ERROR{colors.RESET}: Failed to parse "
                      f"student search results JSON: {e}")
            return None

        if basic_print:
            print(f"\33[2A {colors.BASE_BROWN}╚" + "═" * 30 + "╦" +
                  "═" * 74 + "╦")
            print(" " * 32 + f"{colors.BASE_BROWN}║{colors.BASE_BR_CYAN}" +
                  " " * 18 + f"┏━╸╻ ╻┏━┓╻  ╻ ╻┏━┓╺┳╸┏━╸  {colors.BASE_CYAN}"
                  "┏┳┓┏━┓╺┳┓┏━╸" + " " * 18 + f"{colors.BASE_BROWN}║")
            print(" " * 32 + f"{colors.BASE_BROWN}║{colors.BASE_BR_CYAN}" +
                  " " * 18 + f"┣╸ ┃┏┛┣━┫┃  ┃ ┃┣━┫ ┃ ┣╸   {colors.BASE_CYAN}"
                  "┃┃┃┃ ┃ ┃┃┣╸ " + " " * 18 + f"{colors.BASE_BROWN}║")
            print(" " * 32 + f"{colors.BASE_BROWN}║{colors.BASE_BR_CYAN}" +
                  " " * 18 + f"┗━╸┗┛ ╹ ╹┗━╸┗━┛╹ ╹ ╹ ┗━╸  {colors.BASE_CYAN}"
                  "╹ ╹┗━┛╺┻┛┗━╸" + " " * 18 + f"{colors.BASE_BROWN}║")
            print(" " * 32 + f"{colors.BASE_BROWN}╚" + "═" * 74 + "╝")
            print(f"{colors.RESET}")

        if basic_print:
            if student_valid:
                msg = f"{colors.BASE_GREEN}is valid{colors.RESET}"
            else:
                msg = f"{colors.BASE_RED}is NOT valid{colors.RESET}"
            print(f"\n{colors.BASE_PURPLE}──╼━━━═══{colors.RESET} Student "
                  f"data {msg} {colors.BASE_PURPLE}═══━━━╾──{colors.RESET}\n")

        try:
            valid_results = RagDataset.model_validate_json(
                valid_file.read_text(encoding="utf-8"))
        except Exception as e:
            if basic_print:
                print(f"{colors.BASE_RED}ERROR{colors.RESET}: Failed to parse "
                      f"answered questions search results JSON: {e}")
            return None

        total_questions = len(valid_results.rag_questions)
        questions_with_sources = sum(1 for q in valid_results.rag_questions
                                     if getattr(q, "sources", []))
        questions_with_student_sources = sum(
            1 for r in student_results.search_results if r.retrieved_sources)

        if basic_print:
            print("Total questions:                      "
                  f"{colors.BASE_BR_CYAN}{total_questions}{colors.RESET}")
            print("Total questions with sources:         "
                  f"{colors.BASE_BR_CYAN}{questions_with_sources}"
                  f"{colors.RESET}")
            print("Total questions with student sources: "
                  f"{colors.BASE_BR_CYAN}{questions_with_student_sources}"
                  f"{colors.RESET}")

        student_results_dict = {res.question_id: res for
                                res in student_results.search_results}
        thresholds = sorted(set([1, 3, 5, k]))

        if basic_print:
            print(f"\n{colors.BASE_PURPLE}──╼━━━════{colors.RESET} Evaluation "
                  f"results {colors.BASE_PURPLE}═════━━━╾──{colors.RESET}\n")
            print(f"Questions evaluated: {questions_with_sources}")

        recall1: float | None = None
        recall3: float | None = None
        recall5: float | None = None
        recallk: float | None = None

        for threshold in thresholds:
            total_found: float = 0.0
            total_expected = 0
            for question in valid_results.rag_questions:
                correct = getattr(question, "sources", [])
                if not correct:
                    continue
                student_answer = student_results_dict.get(
                    question.question_id
                )
                search = (student_answer.retrieved_sources[:threshold]
                          if student_answer else [])
                found_questions = 0
                for g in correct:
                    for r in search:
                        if utils.calculate_overlap(r, g) >= 0.05:
                            found_questions += 1
                            break
                recall_question = found_questions / len(correct)
                total_found += recall_question
                total_expected += 1
            if total_expected > 0:
                recall = total_found / total_expected
                if threshold == k:
                    recallk = recall
                if threshold == 1:
                    recall1 = recall
                elif threshold == 3:
                    recall3 = recall
                elif threshold == 5:
                    recall5 = recall
                if basic_print and threshold < 10:
                    print(f"Recall@{threshold}:  {colors.BASE_BR_CYAN}"
                          f"{recall:.3f}{colors.RESET}")
                elif basic_print:
                    print(f"Recall@{threshold}: {colors.BASE_BR_CYAN}"
                          f"{recall:.3f}{colors.RESET}")
            else:
                if basic_print and threshold < 10:
                    print(f"Recall@{threshold}:  {colors.BASE_RED}N/A"
                          f"{colors.RESET}")
                elif basic_print:
                    print(f"Recall@{threshold}: {colors.BASE_RED}N/A"
                          f"{colors.RESET}")

        if tui_display:
            result = EvaluateResult(
                student_valid=student_valid,
                total_questions=total_questions,
                questions_with_sources=questions_with_sources,
                questions_with_student_sources=questions_with_student_sources,
                k=k,
                recall1=recall1,
                recall3=recall3,
                recall5=recall5,
                recallk=recallk,
                )
            return result
        return None

    def interface(self,
                  data_path: str = DATA_PATH,
                  index_path: str = INDEX_PATH,
                  chunks_path: str = CHUNKS_PATH,
                  dataset_path: str = DATASET_PATH,
                  dataset_answered: str = DATASET_ANSWERED,
                  save_directory: str = SAVE_DIRECTORY,
                  search_result_path: str = SEARCH_RESULT_PATH,
                  save_results_answer_dir: str = SAVE_RESULTS_ANSWER_DIRECTORY,
                  ) -> None:
        """
        Launch the terminal user interface with the configured data paths.
        """

        from src.interface.interface import Interface
        ui = Interface(self,
                       data_path,
                       index_path,
                       chunks_path,
                       dataset_path,
                       dataset_answered,
                       save_directory,
                       search_result_path,
                       save_results_answer_dir)
        self._ui = ui
        try:
            ui.run()
        finally:
            self._ui = None

    def _emit(self, event: LogEvent) -> None:
        """Forward a log event to the attached terminal interface."""
        if self._ui is not None:
            self._ui.receive_event(event)
