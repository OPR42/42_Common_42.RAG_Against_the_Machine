from __future__ import annotations

import json
from pathlib import Path
from pydantic import BaseModel, Field, ValidationError


MANIFEST_VERSION = 1
INDEX_VERSION = 1


class ManifestEntry(BaseModel):
    """ Store the state of one indexed source file. """
    sha256: str
    size: int
    mtime_ns: int


class ManifestChanges(BaseModel):
    """ Describe the differences between two repository manifests. """
    unchanged: list[str] = Field(default_factory=list)
    modified: list[str] = Field(default_factory=list)
    added: list[str] = Field(default_factory=list)
    removed: list[str] = Field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        return bool(self.modified or self.added or self.removed)

    @property
    def files_found(self) -> int:
        return len(self.unchanged) + len(self.modified) + len(self.added)

    @property
    def files_reused(self) -> int:
        return len(self.unchanged)

    @property
    def files_reindexed(self) -> int:
        return len(self.modified) + len(self.added)


class Manifest(BaseModel):
    """ Store the state and chunking configuration of an indexed repository """
    manifest_version: int = MANIFEST_VERSION
    index_version: int = INDEX_VERSION
    max_chunk_size: int
    overlap: int
    files: dict[str, ManifestEntry] = Field(default_factory=dict)

    @classmethod
    def load(cls, path: str | Path) -> Manifest | None:
        """
        Load a manifest.
        """
        manifest_path = Path(path)
        if not manifest_path.exists():
            return None
        try:
            content = manifest_path.read_text(encoding="utf-8")
            return cls.model_validate_json(content)
        except (OSError, ValidationError, json.JSONDecodeError) as error:
            raise ValueError(
                f"Invalid manifest file {manifest_path}: {error}"
            ) from error

    def save(self, path: str | Path) -> None:
        """
        Save the manifest atomically.
        """
        manifest_path = Path(path)
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = manifest_path.with_suffix(
            manifest_path.suffix + ".tmp")
        try:
            temporary_path.write_text(self.model_dump_json(indent=2),
                                      encoding="utf-8")
            temporary_path.replace(manifest_path)
        except OSError as error:
            if temporary_path.exists():
                temporary_path.unlink()
            raise OSError(f"Unable to save manifest to {manifest_path}: "
                          f"{error}") from error

    def is_compatible(self, max_chunk_size: int, overlap: int) -> bool:
        """ Return whether this manifest can reuse the current chunk data. """
        return (self.manifest_version == MANIFEST_VERSION
                and self.index_version == INDEX_VERSION
                and self.max_chunk_size == max_chunk_size
                and self.overlap == overlap)

    def compare(self, previous: Manifest | None) -> ManifestChanges:
        """ Compare this manifest with a previous repository state. """
        current_paths = set(self.files)
        if previous is None:
            return ManifestChanges(added=sorted(current_paths))
        previous_paths = set(previous.files)
        added = current_paths - previous_paths
        removed = previous_paths - current_paths
        common = current_paths & previous_paths
        unchanged: list[str] = []
        modified: list[str] = []
        for file_path in common:
            current_entry = self.files[file_path]
            previous_entry = previous.files[file_path]
            if current_entry.sha256 == previous_entry.sha256:
                unchanged.append(file_path)
            else:
                modified.append(file_path)
        return ManifestChanges(unchanged=sorted(unchanged),
                               modified=sorted(modified),
                               added=sorted(added),
                               removed=sorted(removed))
