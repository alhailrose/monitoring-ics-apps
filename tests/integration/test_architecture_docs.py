from pathlib import Path


def test_architecture_doc_exists():
    assert Path("docs/architecture/folder-structure.md").exists()
