from dataclasses import dataclass
from git import Repo, Commit
from locomote.parser import Segment
from pathlib import Path

from typing import Iterator


def generate_text_iter(from_text: str, to_text: str) -> Iterator[str]:
    yield from_text
    segments = Segment.from_sequences(from_text, to_text)
    text_modifiers = []
    for seg in segments:
        text_modifiers += seg.char_mods()
    for mod in text_modifiers:
        from_text = mod(from_text)
        yield from_text
    yield to_text

@dataclass
class FileHistory:
    path: Path
    commits: list[Commit]

    @classmethod
    def from_repo(cls, file_path: str, repo_dir: str | None = None, rev: str | None = None) -> "FileHistory":
        repo = Repo(repo_dir) if repo_dir else Repo(".")
        return cls(
            Path(file_path), 
            sorted([x for x in repo.iter_commits(rev=rev, paths=file_path)], key=lambda x: x.committed_datetime)
        )
    
    def content_for(self, commit: Commit) -> str:
        return commit.tree[str(self.path)].data_stream.read().decode()
    
    @property
    def sequence_iter(self) -> Iterator[tuple[Commit, Iterator[str]]]:
        for idx in range(1, len(self.commits)):
            yield self.commits[idx], generate_text_iter(
                self.content_for(self.commits[idx-1]),
                self.content_for(self.commits[idx])
            )

