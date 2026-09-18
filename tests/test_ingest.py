import pytest

from hermes_legal.ingest.readers import read_document, UnsupportedFileError


def test_read_txt(tmp_path):
    p = tmp_path / "contract.txt"
    p.write_text("Hello contract", encoding="utf-8")
    assert read_document(p) == "Hello contract"


def test_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        read_document(tmp_path / "missing.txt")


def test_unsupported_extension_raises(tmp_path):
    p = tmp_path / "contract.xyz"
    p.write_text("data", encoding="utf-8")
    with pytest.raises(UnsupportedFileError):
        read_document(p)


def test_read_docx_roundtrip(tmp_path):
    docx = pytest.importorskip("docx")
    p = tmp_path / "contract.docx"
    document = docx.Document()
    document.add_paragraph("This is a test clause.")
    document.save(str(p))

    text = read_document(p)
    assert "test clause" in text
