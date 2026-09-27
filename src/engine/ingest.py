from __future__ import annotations

import ast
import hashlib
import json
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from src.base.models import MinimalSource, LogEvent
from src.engine.manifest import Manifest, ManifestEntry
from src.interface.colors import Colors as colors

if TYPE_CHECKING:
    from src.interface.interface import Interface

ChunkResult = tuple[MinimalSource, str, list[str]]


class IngestionResult(BaseModel):
    """
    Store the corpus and statistics produced by incremental ingestion.
    """

    texts: list[str] = Field(default_factory=list)
    sources: list[MinimalSource] = Field(default_factory=list)
    symbols: list[list[str]] = Field(default_factory=list)

    files_reused: int = 0
    files_reindexed: int = 0
    chunks_reused: int = 0
    chunks_generated: int = 0


class Ingest:
    """ Discover, chunk, enrich, and incrementally ingest repository files. """
    def __init__(self, max_chunk_size: int = 800, overlap: int = 100,
                 basic_print: bool = True, tui_display: bool = False,
                 return_results: bool = False, ui: Interface | None = None):
        """ Initialize the ingestion pipeline and its specialized chunkers. """
        self.max_chunk_size = max_chunk_size
        self.overlap = overlap
        self.py_chunk = PyChunk(max_chunk_size, overlap)
        self.md_chunk = MdChunk(max_chunk_size, overlap)
        self.text_chunk = TextChunk(max_chunk_size, overlap)
        self.exclude_dirs = {".git",
                             "__pycache__",
                             "build",
                             "dist",
                             "venv",
                             ".venv"}
        self.basic_print: bool = basic_print
        self.tui_display: bool = tui_display
        self.return_results: bool = return_results
        self.ui = ui

    def is_ignored(self, path: Path) -> bool:
        """ Return whether a path belongs to an excluded directory. """
        return any(part in self.exclude_dirs for part in path.parts)

    def _is_supported_file(self, file_path: Path) -> bool:
        """
        Return whether a file type is supported by the ingestion pipeline.
        """
        return (file_path.suffix in {".py", ".md", ".txt", ".rst"}
                or file_path.name in {"Dockerfile", "Makefile"})

    def _discover_files(self, root: Path) -> list[Path]:
        """
        Return all supported and non-ignored files in deterministic order.
        """
        files = [file_path for file_path in root.rglob("*")
                 if ((file_path.is_file() and not self.is_ignored(file_path)
                     and self._is_supported_file(file_path)))]
        return sorted(files, key=lambda path: path.as_posix())

    def _manifest_entry(self, file_path: Path) -> ManifestEntry:
        """
        Compute the persistent state of one source file.
        """
        digest = hashlib.sha256()
        try:
            with file_path.open("rb") as file:
                while block := file.read(1024 * 1024):
                    digest.update(block)
            file_stat = file_path.stat()
        except OSError as error:
            raise OSError(f"Unable to inspect {file_path}: {error}") from error
        return ManifestEntry(sha256=digest.hexdigest(), size=file_stat.st_size,
                             mtime_ns=file_stat.st_mtime_ns)

    def scan_repository(self, root_dir: str) -> tuple[list[Path], Manifest]:
        """ Discover supported files and build their current manifest. """
        root = Path(root_dir)
        if not root.exists():
            raise FileNotFoundError(f"Directory {root_dir} does not exist.")
        if not root.is_dir():
            raise NotADirectoryError(f"{root_dir} is not a directory.")
        files = self._discover_files(root)
        manifest_entries: dict[str, ManifestEntry] = {}
        for file_path in files:
            display_path = file_path.as_posix()
            try:
                manifest_entries[display_path] = (
                    self._manifest_entry(file_path))
            except OSError as error:
                if self.basic_print:
                    print(f"{colors.BASE_RED}ERROR{colors.RESET} "
                          f"while hashing {file_path}: {error}")
                elif self.tui_display:
                    self._emit(
                        LogEvent(source="index", type="error",
                                 message=f"{file_path} unreadable: {error}"))
        manifest = Manifest(max_chunk_size=self.max_chunk_size,
                            overlap=self.overlap, files=manifest_entries)
        usable_files = [file_path for file_path in files
                        if file_path.as_posix() in manifest_entries]
        return usable_files, manifest

    def _ingest_file(self, file_path: Path) -> list[ChunkResult]:
        """ Read, chunk, and enrich one supported source file. """
        display_path = file_path.as_posix()
        chunks: list[ChunkResult] = []
        try:
            content = file_path.read_text(encoding="utf-8")
            if file_path.suffix == ".py":
                chunks = self.py_chunk.chunk(display_path, content)
            elif file_path.suffix == ".md":
                chunks = self.md_chunk.chunk(display_path, content)
            elif file_path.suffix in {".txt", ".rst"}:
                chunks = self.text_chunk.chunk(display_path, content)
            elif file_path.name in {"Dockerfile", "Makefile"}:
                chunks = self.text_chunk.chunk(display_path, content)
        except Exception as error:
            if self.basic_print:
                print(f"{colors.BASE_RED}ERROR{colors.RESET} "
                      f"while reading {file_path}: {error}")
            elif self.tui_display:
                self._emit(
                    LogEvent(source="index", type="error",
                             message=f"{file_path} unreadable: {error}"))
            return []
        path_metadata = self._path_metadata(file_path)
        enriched_chunks: list[ChunkResult] = []
        for source, text, symbols in chunks:
            if not text.strip():
                continue
            enriched_text = (f"File path: {display_path}\nFile keywords: "
                             f"{path_metadata}\n\n{text}")
            enriched_chunks.append((source, enriched_text, symbols))
        return enriched_chunks

    def load_cached_chunks(
        self,
        chunks_file: str | Path,
    ) -> dict[str, list[ChunkResult]]:
        """
        Load previously generated chunks and group them by source file.
        """
        cache_path = Path(chunks_file)
        if not cache_path.exists():
            return {}
        chunks_by_file: dict[str, list[ChunkResult]] = {}
        try:
            with cache_path.open("r", encoding="utf-8") as file:
                for line_number, line in enumerate(file, start=1):
                    if not line.strip():
                        continue
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError as error:
                        raise ValueError(f"Invalid JSON in {cache_path}, "
                                         f"line {line_number}: {error}"
                                         ) from error
                    try:
                        file_path = str(record["file_path"])
                        first_index = int(record["first_character_index"])
                        last_index = int(record["last_character_index"])
                        text = str(record["text"])
                        raw_symbols = record.get("symbols", [])
                        if not isinstance(raw_symbols, list):
                            raise TypeError("'symbols' must be a list")
                        symbols = [str(symbol) for symbol in raw_symbols]
                    except (KeyError, TypeError, ValueError) as error:
                        raise ValueError("Invalid chunk record in "
                                         f"{cache_path}, line {line_number}: "
                                         f"{error}") from error
                    source = MinimalSource(file_path=file_path,
                                           first_character_index=first_index,
                                           last_character_index=last_index)
                    chunks_by_file.setdefault(file_path, []).append((source,
                                                                     text,
                                                                     symbols))
        except OSError as error:
            raise OSError(
                f"Unable to load chunk cache {cache_path}: {error}"
            ) from error
        return chunks_by_file

    def run(
        self,
        root_dir: str,
        files: list[Path] | None = None,
    ) -> tuple[list[str], list[MinimalSource], list[list[str]]]:
        """ Perform a complete ingestion of the selected repository files. """
        all_texts: list[str] = []
        all_sources: list[MinimalSource] = []
        all_symbols: list[list[str]] = []
        root = Path(root_dir)
        if not root.exists():
            if self.basic_print:
                print(f"{colors.BASE_RED}ERROR{colors.RESET}: Directory "
                      f"{root_dir} does not exist!")
            elif self.tui_display:
                self._emit(
                    LogEvent(source="index", type="error",
                             message=f"Directory {root_dir} does not exist!"))
            return [], [], []
        files_to_ingest = (files if files is not None
                           else self._discover_files(root))
        for file_path in files_to_ingest:
            chunks = self._ingest_file(file_path)
            for source, text, symbols in chunks:
                all_texts.append(text)
                all_sources.append(source)
                all_symbols.append(symbols)
        return all_texts, all_sources, all_symbols

    def run_incremental(
        self,
        root_dir: str,
        files: list[Path],
        reusable_paths: set[str],
        cached_chunks: dict[str, list[ChunkResult]],
    ) -> IngestionResult:
        """ Build a complete corpus while rechunking only changed files. """
        root = Path(root_dir)
        if not root.exists():
            raise FileNotFoundError(f"Directory {root_dir} does not exist.")
        if not root.is_dir():
            raise NotADirectoryError(f"{root_dir} is not a directory.")
        result = IngestionResult()
        for file_path in files:
            display_path = file_path.as_posix()
            if display_path in reusable_paths:
                chunks = cached_chunks.get(display_path, [])
                result.files_reused += 1
                result.chunks_reused += len(chunks)
            else:
                chunks = self._ingest_file(file_path)
                result.files_reindexed += 1
                result.chunks_generated += len(chunks)
            for source, text, symbols in chunks:
                result.texts.append(text)
                result.sources.append(source)
                result.symbols.append(symbols)
        return result

    def _emit(self, event: LogEvent) -> None:
        """ Forward a log event to the attached terminal interface. """
        if self.ui is not None:
            self.ui.receive_event(event)

    def _path_metadata(self, file_path: Path) -> str:
        """
        Convert the useful part of a file path into searchable keywords.
        """
        normalized = file_path.as_posix()
        parts = normalized.split("/")
        for root_name in ("docs", "vllm", "examples", "tests"):
            if root_name in parts:
                parts = parts[parts.index(root_name):]
                break
        else:
            parts = parts[-4:]
        useful_path = " ".join(parts)
        useful_path = re.sub(r"\.[^.\s/]+$", "", useful_path)
        useful_path = re.sub(r"[/_.-]+", " ", useful_path)
        useful_path = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", useful_path)
        return " ".join(useful_path.lower().split())


class BaseChunk(ABC):
    """ Define shared behavior for format-specific text chunkers. """
    def __init__(self, max_chunk_size: int = 800, overlap: int = 100):
        """ Initialize the chunk size and overlap configuration. """
        self.max_chunk_size = max_chunk_size
        self.overlap = overlap

    @abstractmethod
    def chunk(self, file_path: str, content: str) -> list[ChunkResult]:
        """ Split file content into indexed chunks. """
        pass

    def _find_split_position(self, text: str, start: int,
                             target_end: int) -> int:
        """ Find a natural chunk boundary near the requested end position. """
        if target_end >= len(text):
            return len(text)
        search_start = max(start + 1, target_end - self.max_chunk_size // 3)
        for separator in ("\n\n", "\n", " "):
            position = text.rfind(separator, search_start, target_end)
            if position != -1:
                return position + len(separator)
        return target_end

    def _split_large_text(self, text: str, start_offset: int, file_path: str,
                          symbols: list[str] | None = None
                          ) -> list[ChunkResult]:
        """
        Split text into overlapping chunks with stable source positions.
        """
        chunks: list[ChunkResult] = []
        chunk_symbols = symbols or []
        current_pos = 0
        if self.max_chunk_size <= 0:
            raise ValueError("max_chunk_size must be greater than zero")
        if self.overlap < 0:
            raise ValueError("overlap cannot be negative")
        if self.overlap >= self.max_chunk_size:
            raise ValueError("overlap must be smaller than max_chunk_size")
        while current_pos < len(text):
            target_end = min(current_pos + self.max_chunk_size, len(text))
            end_pos = self._find_split_position(text, current_pos, target_end)
            if end_pos <= current_pos:
                end_pos = target_end
            sub_text = text[current_pos:end_pos]
            source = MinimalSource(
                file_path=file_path,
                first_character_index=start_offset + current_pos,
                last_character_index=start_offset + end_pos,
            )
            chunks.append((source, sub_text, chunk_symbols.copy()))
            if end_pos >= len(text):
                break
            current_pos = max(0, end_pos - self.overlap)
        return chunks


class PyChunk(BaseChunk):
    """ Split Python source code around top-level definitions. """
    def _build_line_map(self, content: str) -> list[int]:
        """ Map Python source line numbers to character offsets. """
        line_starts = [0]
        for index, char in enumerate(content):
            if char == "\n":
                line_starts.append(index + 1)
        return line_starts

    def _line_to_char(self, line_map: list[int], line: int | None,
                      col: int | None) -> int:
        """ Convert a source line and column into a character offset. """
        if line is None or col is None:
            return 0
        return line_map[line - 1] + col

    def _node_bounds(self, node: ast.AST,
                     line_map: list[int]) -> tuple[int, int] | None:
        """ Return the character bounds of an AST node when available. """
        lineno = getattr(node, "lineno", None)
        col_offset = getattr(node, "col_offset", None)
        end_lineno = getattr(node, "end_lineno", None)
        end_col_offset = getattr(node, "end_col_offset", None)
        if (lineno is None or col_offset is None or end_lineno is None
           or end_col_offset is None):
            return None
        start = self._line_to_char(line_map, lineno, col_offset)
        end = self._line_to_char(line_map, end_lineno, end_col_offset)
        return start, end

    def _make_chunks(self, text: str, start: int, file_path: str,
                     symbols: list[str]) -> list[ChunkResult]:
        """ Create one or more chunks from a Python source region. """
        if not text.strip():
            return []
        if len(text) <= self.max_chunk_size:
            source = MinimalSource(file_path=file_path,
                                   first_character_index=start,
                                   last_character_index=start + len(text))
            return [(source, text, symbols)]
        return self._split_large_text(text=text, start_offset=start,
                                      file_path=file_path, symbols=symbols)

    def chunk(self, file_path: str, content: str) -> list[ChunkResult]:
        """
        Split Python source around top-level classes and functions.
        Fall back to regular text splitting when the source cannot be parsed.
        """
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return self._split_large_text(content, 0, file_path, symbols=[])
        line_map = self._build_line_map(content)
        chunks: list[ChunkResult] = []
        cursor = 0
        definitions = [node for node in tree.body if isinstance(
                node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
        for node in definitions:
            bounds = self._node_bounds(node, line_map)
            if bounds is None:
                continue
            start, end = bounds
            prefix = content[cursor:start]
            chunks.extend(self._make_chunks(text=prefix, start=cursor,
                                            file_path=file_path, symbols=[]))
            node_text = content[start:end]
            chunks.extend(self._make_chunks(text=node_text, start=start,
                                            file_path=file_path,
                                            symbols=[node.name]))
            cursor = max(cursor, end)
        chunks.extend(self._make_chunks(text=content[cursor:], start=cursor,
                                        file_path=file_path, symbols=[]))
        if not chunks and content.strip():
            return self._split_large_text(content, 0, file_path, symbols=[])
        return chunks


class MdChunk(BaseChunk):
    """ Split Markdown content while preserving its heading hierarchy. """
    def _header_level(self, header: str) -> int:
        """ Return the nesting level of a Markdown heading. """
        return len(header) - len(header.lstrip("#"))

    def _header_title(self, header: str) -> str:
        """ Extract the title of a Markdown heading. """
        return header.lstrip("#").strip()

    def _add_hierarchy(
            self,
            chunks: list[ChunkResult],
            hierarchy: str
            ) -> list[ChunkResult]:
        """ Add the Markdown heading hierarchy to the indexed text. """
        enriched_chunks: list[ChunkResult] = []
        for source, text, symbols in chunks:
            enriched_text = (f"Markdown hierarchy: {hierarchy}\n\n{text}")
            enriched_chunks.append((source, enriched_text, symbols))
        return enriched_chunks

    def chunk(self, file_path: str, content: str) -> list[ChunkResult]:
        """ Split Markdown content into sections based on its headings. """
        chunks: list[ChunkResult] = []
        headers = list(re.finditer(r"^(#{1,6}\s+.+)$", content, re.MULTILINE))
        if not headers:
            return self._split_large_text(content, 0, file_path)
        if headers[0].start() > 0:
            intro_text = content[:headers[0].start()]
            if intro_text.strip():
                chunks.extend(self._split_large_text(intro_text, 0, file_path))
        header_stack: list[str] = []
        for index, header_match in enumerate(headers):
            header_text = header_match.group(1)
            header_level = self._header_level(header_text)
            header_title = self._header_title(header_text)
            header_stack = header_stack[:header_level - 1]
            header_stack.append(header_title)
            hierarchy = " > ".join(header_stack)
            start_pos = header_match.start()
            if index + 1 < len(headers):
                end_pos = headers[index + 1].start()
            else:
                end_pos = len(content)
            section_text = content[start_pos:end_pos]
            if len(section_text) > self.max_chunk_size:
                section_chunks = self._split_large_text(section_text,
                                                        start_pos, file_path)
                chunks.extend(self._add_hierarchy(section_chunks, hierarchy))
            else:
                source = MinimalSource(file_path=file_path,
                                       first_character_index=start_pos,
                                       last_character_index=end_pos)
                enriched_text = (f"Markdown hierarchy: {hierarchy}\n\n"
                                 f"{section_text}")
                chunks.append((source, enriched_text, []))
        return chunks


class TextChunk(BaseChunk):
    """ Split plain text into overlapping chunks. """
    def chunk(
        self,
        file_path: str,
        content: str,
    ) -> list[ChunkResult]:
        """ Split plain-text content into indexed chunks. """
        return self._split_large_text(text=content, start_offset=0,
                                      file_path=file_path, symbols=[])
