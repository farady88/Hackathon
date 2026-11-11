"""Where the agent gets case text from. This is the seam for the embedded corpus.

A store needs two methods:
    search(query, k) -> list[Hit]      candidate passages for a query
    get_case(case_id) -> list[str]     the untouched source lines of one case

CorpusStore works today on the raw .txt files. EmbeddedStore is the stub to fill in
when the embedded corpus is delivered; nothing outside this file has to change.

Only case .txt files are read here. Never read the answer-key CSV or the examples docx.
"""
from dataclasses import dataclass
import os
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
EMBEDDED_PATH = Path(os.environ.get("LYNCEUS_STORE_PATH", Path(__file__).resolve().parent / "store"))


@dataclass
class Hit:
    case_id: str
    text: str
    line_start: int
    line_end: int
    score: float | None = None


def corpus_dirs():
    """LYNCEUS_CORPUS (os.pathsep separated) or lynceus/corpus plus every lynceus_*/ folder,
    so a new live-round folder is picked up with no code change."""
    override = os.environ.get("LYNCEUS_CORPUS")
    if override:
        return [Path(p) for p in override.split(os.pathsep) if p]
    return [REPO / "lynceus" / "corpus", *sorted(p for p in REPO.glob("lynceus_*") if p.is_dir())]


class CorpusStore:
    """Fallback with no index: search() returns every case and the model does the ranking.
    Fine while the corpus is a few dozen one-paragraph files."""
    exhaustive = True  # search() ignores the query, so calling it twice adds nothing

    def __init__(self, dirs=None):
        self.dirs = [Path(d) for d in dirs] if dirs is not None else corpus_dirs()

    def paths(self):
        found = {}
        for d in self.dirs:
            for p in sorted(d.glob("*.txt")):
                # "._*" files are macOS sidecars, not cases
                if p.is_file() and not p.name.startswith("."):
                    found.setdefault(p.stem, p)
        return found

    def get_case(self, case_id):
        path = self.paths().get(case_id)
        if path is None:
            raise KeyError(f"Case not found: {case_id}")
        return path.read_text(encoding="utf-8-sig").splitlines()

    def search(self, query, k=8):
        hits = []
        for case_id in self.paths():
            lines = self.get_case(case_id)
            if lines:
                hits.append(Hit(case_id, "\n".join(lines), 1, len(lines)))
        return hits


class EmbeddedStore(CorpusStore):
    """Stub for the embedded corpus. get_case() stays on the raw files so citations
    always point at the untouched source."""
    exhaustive = False

    def __init__(self, path=EMBEDDED_PATH, dirs=None):
        super().__init__(dirs)
        self.path = Path(path)

    def search(self, query, k=8):
        # Embed the query, take the top k chunks from the collection at self.path and
        # return Hit(case_id, chunk_text, line_start, line_end, score) for each.
        raise NotImplementedError("Embedded corpus not wired in yet: implement EmbeddedStore.search")


def get_store():
    return EmbeddedStore() if EMBEDDED_PATH.exists() else CorpusStore()
