import hashlib
import json
import pathlib
import sys

import pytest

# Make "import load" work no matter where pytest is run from
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "pipeline"))
import load  # noqa: E402

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

ENGLISH = "Veridane helped a bank rebuild its payments platform on the cloud so customers can send money instantly."
JAPANESE = "ヴェリデーンはメーカーの工場にAIを導入し、品質管理を自動化しました。結果として不良品が大幅に減りました。"
ARABIC = "قامت فيريدان بمساعدة شركة المدفوعات على بناء منصة مدفوعات فورية جديدة تتيح للعملاء تحويل الأموال في ثوانٍ."


@pytest.fixture
def env(tmp_path, monkeypatch):
    """A fake corpus, fake live folder and fake output file, so real data is never touched."""
    corpus = tmp_path / "corpus"
    live = tmp_path / "corpus_live"
    corpus.mkdir()
    live.mkdir()
    out = tmp_path / "data" / "records.json"
    monkeypatch.setattr(load, "SOURCES", {"main": corpus, "live": live})
    monkeypatch.setattr(load, "OUT", out)
    return corpus, live, out


def run_load(out):
    load.load()
    return json.loads(out.read_text(encoding="utf-8"))


# ---------- clear_old_output ----------

def test_clear_old_output_deletes_old_file(env):
    _, _, out = env
    out.parent.mkdir(parents=True)
    out.write_text("old stale data")
    load.clear_old_output()
    assert not out.exists()


def test_clear_old_output_creates_missing_folder(env):
    _, _, out = env
    assert not out.parent.exists()
    load.clear_old_output()
    assert out.parent.exists()


# ---------- find_files ----------

def test_find_files_accepts_txt_in_any_capitalisation(tmp_path):
    (tmp_path / "a.txt").write_text("x")
    (tmp_path / "B.TXT").write_text("x")
    (tmp_path / "c.Txt").write_text("x")
    skipped = []
    names = [f.name for f in load.find_files(tmp_path, skipped)]
    assert sorted(names) == ["B.TXT", "a.txt", "c.Txt"]
    assert skipped == []


def test_find_files_looks_in_sub_folders(tmp_path):
    (tmp_path / "sub" / "deeper").mkdir(parents=True)
    (tmp_path / "sub" / "deeper" / "case-1.txt").write_text("x")
    assert len(load.find_files(tmp_path, [])) == 1


def test_find_files_ignores_mac_junk(tmp_path):
    (tmp_path / "case-1.txt").write_text("x")
    (tmp_path / "._case-1.txt").write_bytes(b"\x00\x05junk")
    (tmp_path / ".DS_Store").write_bytes(b"junk")
    (tmp_path / "__MACOSX").mkdir()
    (tmp_path / "__MACOSX" / "._case-1.txt").write_bytes(b"junk")
    skipped = []
    names = [f.name for f in load.find_files(tmp_path, skipped)]
    assert names == ["case-1.txt"]
    assert skipped == []  # junk is ignored quietly, it is not a real skipped file


def test_find_files_ignores_files_inside_hidden_folders(tmp_path):
    (tmp_path / ".hidden").mkdir()
    (tmp_path / ".hidden" / "case-1.txt").write_text("x")
    assert load.find_files(tmp_path, []) == []


def test_find_files_still_works_if_the_folder_itself_is_hidden(tmp_path):
    # e.g. the repo lives somewhere like /Users/me/.work/corpus
    folder = tmp_path / ".work" / "corpus"
    folder.mkdir(parents=True)
    (folder / "case-1.txt").write_text("x")
    assert len(load.find_files(folder, [])) == 1


def test_find_files_reports_other_file_types_as_skipped(tmp_path):
    (tmp_path / "case-1.txt").write_text("x")
    (tmp_path / "notes.docx").write_bytes(b"PK")
    (tmp_path / "case-2.md").write_text("x")
    skipped = []
    files = load.find_files(tmp_path, skipped)
    assert len(files) == 1
    assert len(skipped) == 2


def test_find_files_returns_sorted_order(tmp_path):
    for n in ["case-3.txt", "case-1.txt", "case-2.txt"]:
        (tmp_path / n).write_text("x")
    names = [f.name for f in load.find_files(tmp_path, [])]
    assert names == sorted(names)


def test_find_files_ignores_folders_named_like_text_files(tmp_path):
    (tmp_path / "weird.txt").mkdir()
    assert load.find_files(tmp_path, []) == []


# ---------- read_file ----------

def test_read_file_plain_utf8(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text(ENGLISH, encoding="utf-8")
    assert load.read_file(f) == ENGLISH


def test_read_file_keeps_non_english_text_exactly(tmp_path):
    for text in (JAPANESE, ARABIC, "Café déjà vu, Müller, Łódź, Ελληνικά, Русский"):
        f = tmp_path / "a.txt"
        f.write_text(text, encoding="utf-8")
        assert load.read_file(f) == text


def test_read_file_strips_surrounding_whitespace(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("\n\n  hello world  \n\n", encoding="utf-8")
    assert load.read_file(f) == "hello world"


def test_read_file_removes_byte_order_marker(tmp_path):
    f = tmp_path / "a.txt"
    f.write_bytes(b"\xef\xbb\xbf" + ENGLISH.encode("utf-8"))
    text = load.read_file(f)
    assert text == ENGLISH
    assert not text.startswith("\ufeff")


def test_read_file_whitespace_only_file_becomes_empty(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("   \n\t\n  ", encoding="utf-8")
    assert load.read_file(f) == ""


def test_read_file_empty_file(tmp_path):
    f = tmp_path / "a.txt"
    f.write_bytes(b"")
    assert load.read_file(f) == ""


def test_read_file_does_not_crash_on_non_utf8(tmp_path):
    f = tmp_path / "a.txt"
    f.write_bytes(JAPANESE.encode("shift_jis"))
    text = load.read_file(f)  # must not raise
    assert "\ufffd" in text  # bad characters are visible, not silently wrong


def test_read_file_does_not_crash_on_binary(tmp_path):
    f = tmp_path / "a.txt"
    f.write_bytes(bytes(range(256)) * 4)
    assert isinstance(load.read_file(f), str)


# ---------- check_text ----------

def test_check_text_clean_text_has_no_issues():
    issues = []
    load.check_text(ENGLISH, issues)
    assert issues == []


def test_check_text_flags_empty():
    issues = []
    load.check_text("", issues)
    assert any("empty" in i for i in issues)


def test_check_text_flags_broken_characters():
    issues = []
    load.check_text("some text with a \ufffd in it", issues)
    assert any("broken" in i for i in issues)


# ---------- make_unique_id ----------

def test_make_unique_id_first_use_is_unchanged():
    issues, used = [], set()
    assert load.make_unique_id("case-1", "main", used, issues) == "case-1"
    assert issues == []


def test_make_unique_id_duplicate_is_renamed_and_flagged():
    issues, used = [], {"case-1"}
    new_id = load.make_unique_id("case-1", "live", used, issues)
    assert new_id == "live-case-1"
    assert len(issues) == 1


def test_make_unique_id_never_returns_the_same_id_twice():
    # Three files all called case-1 must still end up with three different ids
    used, ids = set(), []
    for batch in ["main", "live", "live", "live"]:
        ids.append(load.make_unique_id("case-1", batch, used, []))
    assert len(set(ids)) == 4


# ---------- detect_language ----------

def test_detect_language_known_languages():
    assert load.detect_language(ENGLISH, []) == "en"
    assert load.detect_language(JAPANESE, []) == "ja"
    assert load.detect_language(ARABIC, []) == "ar"


def test_detect_language_empty_text_is_unknown_without_crashing():
    assert load.detect_language("", []) == "unknown"


def test_detect_language_text_with_no_letters_is_unknown_and_flagged():
    issues = []
    assert load.detect_language("12345 67890 !!!", issues) == "unknown"
    assert issues  # the failure is reported, not hidden


def test_detect_language_gives_same_answer_every_time():
    answers = {load.detect_language(ENGLISH, []) for _ in range(25)}
    assert len(answers) == 1


# ---------- save_json ----------

def test_save_json_keeps_non_english_readable(tmp_path):
    f = tmp_path / "x.json"
    load.save_json(f, {"text": JAPANESE})
    assert JAPANESE in f.read_text(encoding="utf-8")
    assert json.loads(f.read_text(encoding="utf-8")) == {"text": JAPANESE}


# ---------- print_report ----------

def test_print_report_shows_issues_next_to_case_id(capsys):
    records = [{"case_id": "case-1", "data_issues": ["empty file", "other problem"]},
               {"case_id": "case-2", "data_issues": []}]
    load.print_report(records, [])
    out = capsys.readouterr().out
    assert "case-1: empty file; other problem" in out
    assert "case-2:" not in out  # clean records are not listed
    assert "No issues found" not in out


def test_print_report_says_when_everything_is_fine(capsys):
    load.print_report([{"case_id": "case-1", "data_issues": []}], [])
    assert "No issues found" in capsys.readouterr().out


def test_print_report_lists_skipped_files(capsys):
    load.print_report([], ["folder/notes.docx"])
    out = capsys.readouterr().out
    assert "notes.docx" in out
    assert "No issues found" not in out


# ---------- load() end to end ----------

def test_load_writes_all_records_into_one_json_file(env):
    corpus, _, out = env
    (corpus / "case-1.txt").write_text(ENGLISH, encoding="utf-8")
    (corpus / "case-2.txt").write_text(JAPANESE, encoding="utf-8")
    records = run_load(out)
    assert isinstance(records, list)
    assert [r["case_id"] for r in records] == ["case-1", "case-2"]
    # only one output file was created
    assert [p.name for p in out.parent.iterdir()] == ["records.json"]


def test_load_records_have_every_expected_field(env):
    corpus, _, out = env
    (corpus / "case-1.txt").write_text(ENGLISH, encoding="utf-8")
    record = run_load(out)[0]
    assert set(record) == {"case_id", "source_path", "batch", "language",
                           "text_original", "text_english", "data_issues"}
    assert record["batch"] == "main"
    assert record["language"] == "en"
    assert record["text_original"] == ENGLISH
    assert record["text_english"] is None
    assert record["data_issues"] == []
    assert pathlib.Path(record["source_path"]).exists()


def test_load_keeps_non_english_readable_in_the_json_file(env):
    corpus, _, out = env
    (corpus / "case-1.txt").write_text(JAPANESE, encoding="utf-8")
    load.load()
    raw = out.read_text(encoding="utf-8")
    assert "ヴェリデーン" in raw  # not turned into \u escape codes


def test_load_labels_main_and_live_batches(env):
    corpus, live, out = env
    (corpus / "case-1.txt").write_text(ENGLISH, encoding="utf-8")
    (live / "case-2.txt").write_text(ARABIC, encoding="utf-8")
    records = {r["case_id"]: r for r in run_load(out)}
    assert records["case-1"]["batch"] == "main"
    assert records["case-2"]["batch"] == "live"


def test_load_works_when_live_folder_does_not_exist_yet(env):
    corpus, live, out = env
    live.rmdir()
    (corpus / "case-1.txt").write_text(ENGLISH, encoding="utf-8")
    assert len(run_load(out)) == 1


def test_load_with_no_files_writes_an_empty_list_and_does_not_crash(env, capsys):
    _, _, out = env
    assert run_load(out) == []
    assert "No issues found" in capsys.readouterr().out


def test_load_is_a_clean_start_and_replaces_stale_output(env):
    corpus, _, out = env
    out.parent.mkdir(parents=True)
    out.write_text(json.dumps([{"case_id": "ghost"}]))
    (corpus / "case-1.txt").write_text(ENGLISH, encoding="utf-8")
    ids = [r["case_id"] for r in run_load(out)]
    assert ids == ["case-1"]  # the ghost record is gone


def test_load_running_twice_gives_identical_output(env):
    corpus, live, out = env
    (corpus / "case-1.txt").write_text(ENGLISH, encoding="utf-8")
    (live / "case-2.txt").write_text(JAPANESE, encoding="utf-8")
    (live / "case-3.txt").write_text("", encoding="utf-8")  # gives an issue too
    load.load()
    first = out.read_bytes()
    load.load()
    assert out.read_bytes() == first


def test_load_new_live_files_are_picked_up_without_code_changes(env):
    corpus, live, out = env
    (corpus / "case-1.txt").write_text(ENGLISH, encoding="utf-8")
    assert len(run_load(out)) == 1
    (live / "case-9.txt").write_text(ARABIC, encoding="utf-8")  # the 12:30 drop
    assert len(run_load(out)) == 2


def test_load_flags_empty_and_broken_files_but_still_loads_the_rest(env, capsys):
    corpus, live, out = env
    (corpus / "case-1.txt").write_text(ENGLISH, encoding="utf-8")
    (live / "case-2.txt").write_text("", encoding="utf-8")
    (live / "case-3.txt").write_bytes(JAPANESE.encode("shift_jis"))
    records = {r["case_id"]: r for r in run_load(out)}
    assert len(records) == 3
    assert records["case-1"]["data_issues"] == []
    assert any("empty" in i for i in records["case-2"]["data_issues"])
    assert any("broken" in i for i in records["case-3"]["data_issues"])
    printed = capsys.readouterr().out
    assert "case-2:" in printed and "case-3:" in printed


def test_load_all_case_ids_are_unique_even_with_repeated_names(env):
    corpus, live, out = env
    (corpus / "case-1.txt").write_text(ENGLISH, encoding="utf-8")
    (live / "a").mkdir()
    (live / "b").mkdir()
    (live / "a" / "case-1.txt").write_text(ENGLISH + " one", encoding="utf-8")
    (live / "b" / "case-1.txt").write_text(ENGLISH + " two", encoding="utf-8")
    ids = [r["case_id"] for r in run_load(out)]
    assert len(ids) == 3
    assert len(set(ids)) == 3


def test_load_ignores_junk_and_reports_wrong_file_types(env, capsys):
    corpus, live, out = env
    (live / "case-1.txt").write_text(ENGLISH, encoding="utf-8")
    (live / "._case-1.txt").write_bytes(b"\x00junk")
    (live / ".DS_Store").write_bytes(b"junk")
    (live / "notes.docx").write_bytes(b"PK")
    records = run_load(out)
    assert [r["case_id"] for r in records] == ["case-1"]
    assert "notes.docx" in capsys.readouterr().out


def test_load_never_changes_the_original_files(env):
    corpus, live, out = env
    files = [corpus / "case-1.txt", live / "case-2.txt"]
    files[0].write_text(ENGLISH + "\n\n", encoding="utf-8")
    files[1].write_bytes(JAPANESE.encode("shift_jis"))
    before = {f: hashlib.sha256(f.read_bytes()).hexdigest() for f in files}
    load.load()
    after = {f: hashlib.sha256(f.read_bytes()).hexdigest() for f in files}
    assert before == after


def test_load_puts_issues_inside_the_record_and_clean_records_get_an_empty_list(env):
    corpus, _, out = env
    (corpus / "case-1.txt").write_text(ENGLISH, encoding="utf-8")
    (corpus / "case-2.txt").write_text("", encoding="utf-8")  # has a problem
    records = {r["case_id"]: r for r in run_load(out)}
    assert records["case-1"]["data_issues"] == []
    assert "empty file" in records["case-2"]["data_issues"]


def test_load_issues_are_recorded_on_the_renamed_case_id(env):
    corpus, live, out = env
    (corpus / "case-1.txt").write_text(ENGLISH, encoding="utf-8")
    (live / "case-1.txt").write_text(ENGLISH + " again", encoding="utf-8")
    records = {r["case_id"]: r for r in run_load(out)}
    assert records["case-1"]["data_issues"] == []
    assert records["live-case-1"]["data_issues"]  # the rename is noted


# ---------- the real corpus (skipped if it isn't in the repo) ----------

REAL_CORPUS = REPO_ROOT / "corpus"


@pytest.mark.skipif(not REAL_CORPUS.exists(), reason="real corpus folder not found")
def test_real_corpus_loads_every_case_file(tmp_path, monkeypatch):
    out = tmp_path / "records.json"
    monkeypatch.setattr(load, "SOURCES", {"main": REAL_CORPUS})
    monkeypatch.setattr(load, "OUT", out)
    load.load()
    records = json.loads(out.read_text(encoding="utf-8"))
    expected = [p for p in REAL_CORPUS.glob("case-*.txt") if not p.name.startswith(".")]
    assert len(records) == len(expected)
    ids = [r["case_id"] for r in records]
    assert len(set(ids)) == len(ids)
    assert all(not i.startswith(".") for i in ids)
    assert all(r["text_original"] for r in records)  # nothing empty
    assert all("\ufffd" not in r["text_original"] for r in records)  # nothing garbled

