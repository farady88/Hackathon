import json, pathlib
from langdetect import detect, DetectorFactory

# Without this, langdetect can give different answers on different runs
DetectorFactory.seed = 0

# Where the raw files live: the main corpus, and a folder for the live round files
SOURCES = {"main": pathlib.Path("corpus"), "live": pathlib.Path("corpus_live")}

# One file holding every record
OUT = pathlib.Path("data/records.json")


def clear_old_output():
    """Clean start: delete the old results so nothing stale is left over."""
    if OUT.exists():
        OUT.unlink()
    OUT.parent.mkdir(parents=True, exist_ok=True)


def find_files(folder, skipped):
    """Return the real text files in a folder and note anything we ignore."""
    files = []
    for f in sorted(folder.rglob("*")):  # rglob also looks inside sub folders
        if not f.is_file():
            continue
        # Skip hidden Mac junk such as ._case-1.txt, .DS_Store and the __MACOSX folder
        # (only look at the path inside the corpus folder, not where the repo lives)
        inside = f.relative_to(folder).parts
        if any(part.startswith(".") or part == "__MACOSX" for part in inside):
            continue
        # Accept .txt in any capitalisation (.txt, .TXT), list everything else as skipped
        if f.suffix.lower() == ".txt":
            files.append(f)
        else:
            skipped.append(str(f))
    return files


def read_file(f):
    """Read a file as UTF-8 so every language loads properly."""
    try:
        # utf-8-sig also removes the invisible marker some editors put at the start
        return f.read_text(encoding="utf-8-sig").strip()
    except UnicodeDecodeError:
        # File isn't UTF-8: still load it, bad characters become a "broken character" symbol
        return f.read_text(encoding="utf-8", errors="replace").strip()


def check_text(text, issues):
    """Flag files that are empty or contain broken characters."""
    if not text:
        issues.append("empty file")
    if "\ufffd" in text:  # \ufffd is the "broken character" symbol
        issues.append("contains broken characters (file may not be UTF-8)")


def make_unique_id(case_id, batch, used_ids, issues):
    """If this case number was already used, rename it so nothing is lost."""
    if case_id in used_ids:
        issues.append(f"case id '{case_id}' already used, renamed")
        new_id, n = f"{batch}-{case_id}", 2
        while new_id in used_ids:  # still taken? add a number until it is free
            new_id = f"{batch}-{case_id}-{n}"
            n += 1
        case_id = new_id
    used_ids.add(case_id)
    return case_id


def detect_language(text, issues):
    """Work out the language from the text itself."""
    try:
        return detect(text) if text else "unknown"
    except Exception:
        # If detection fails, don't crash, just mark it and note the problem
        issues.append("language not detected")
        return "unknown"


def save_json(path, data):
    """Write data to a JSON file, keeping non English characters readable."""
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def print_report(records, skipped):
    """Print every issue next to its case id."""
    print("\n--- ISSUES ---")
    found = False
    for r in records:
        if r["data_issues"]:
            found = True
            print(f"{r['case_id']}: {'; '.join(r['data_issues'])}")
    if skipped:
        found = True
        print(f"Skipped files (not .txt): {skipped}")
    if not found:
        print("No issues found")
    print(f"\nLoaded {len(records)} entries into {OUT}")


def load():
    clear_old_output()
    records = []   # one record per file
    skipped = []   # files we ignored because they weren't .txt
    used_ids = set()

    # Go through each source folder (main first, then live)
    for batch, folder in SOURCES.items():
        # Skip a folder if it isn't there, e.g. the live folder before 12:30
        if not folder.exists():
            continue

        for f in find_files(folder, skipped):
            issues = []  # problems found with this file
            text = read_file(f)
            check_text(text, issues)
            case_id = make_unique_id(f.stem, batch, used_ids, issues)
            lang = detect_language(text, issues)

            # Build one record for this file
            records.append({
                "case_id": case_id,             # e.g. "case-322"
                "source_path": str(f),          # where the original file is, for tracing back
                "batch": batch,                 # "main" or "live"
                "language": lang,               # detected language code, e.g. "en", "ja"
                "text_original": text,          # the text exactly as it was in the file
                "text_english": None,           # empty for now, a translation can go here later
                "data_issues": issues,          # any problems found, for the evidence pack
            })

    # Save all records together in one JSON file
    save_json(OUT, records)
    print_report(records, skipped)


# Only run load() when this file is run directly, not when it's imported
if __name__ == "__main__":
    load()