import shutil
from pathlib import Path

from policydrift.ingest.manifest import load_manifest, sha256_file, verify_sources


def test_every_captured_source_matches_its_hash(root: Path) -> None:
    raw_dir = root / "data" / "raw"
    sources = load_manifest(raw_dir / "manifest.jsonl")
    assert len(sources) >= 46
    assert verify_sources(sources, raw_dir) == []


def test_manifest_paths_encode_scheme_version_language_and_release_id(root: Path) -> None:
    for s in load_manifest(root / "data" / "raw" / "manifest.jsonl"):
        assert s.path == f"{s.scheme}/{s.version}/pib-{s.release_tag}-{s.language}.txt"
        if s.release_id_kind == "prid":
            assert s.url == f"https://www.pib.gov.in/PressReleasePage.aspx?PRID={s.release_id}"
        else:
            assert s.url == f"https://www.pib.gov.in/newsite/erelcontent.aspx?relid={s.release_id}"


def test_tampered_or_missing_file_is_reported(root: Path, tmp_path: Path) -> None:
    raw_dir = root / "data" / "raw"
    source = load_manifest(raw_dir / "manifest.jsonl")[0]
    copy_dir = tmp_path / "raw"
    target = copy_dir / source.path
    target.parent.mkdir(parents=True)
    shutil.copy(raw_dir / source.path, target)
    assert verify_sources([source], copy_dir) == []

    target.write_text(target.read_text(encoding="utf-8") + "edited", encoding="utf-8")
    assert sha256_file(target) != source.sha256
    assert verify_sources([source], copy_dir) == [f"sha256 mismatch: {source.path}"]

    target.unlink()
    assert verify_sources([source], copy_dir) == [f"missing file: {source.path}"]


def test_duplicate_entries_are_reported(root: Path) -> None:
    raw_dir = root / "data" / "raw"
    source = load_manifest(raw_dir / "manifest.jsonl")[0]
    assert verify_sources([source, source], raw_dir) == [f"duplicate manifest entry: {source.path}"]
