import pytest


def test_ocr_fallback_extracts_text_from_scanned_pdf(tmp_path):
    pytesseract = pytest.importorskip("pytesseract")
    pytest.importorskip("pdf2image")
    PIL_Image = pytest.importorskip("PIL.Image")
    from PIL import ImageDraw

    from hermes_legal.ingest.readers import read_document

    img = PIL_Image.new("RGB", (800, 200), color="white")
    draw = ImageDraw.Draw(img)
    draw.text((20, 20), "FREELANCE SERVICE AGREEMENT", fill="black")

    pdf_path = tmp_path / "scanned.pdf"
    img.save(pdf_path, "PDF")

    text = read_document(pdf_path)
    assert "AGREEMENT" in text.upper()


def test_no_ocr_flag_raises_on_scanned_pdf(tmp_path):
    PIL_Image = pytest.importorskip("PIL.Image")
    from PIL import ImageDraw

    from hermes_legal.ingest.readers import read_document

    img = PIL_Image.new("RGB", (800, 200), color="white")
    draw = ImageDraw.Draw(img)
    draw.text((20, 20), "SOME CONTRACT TEXT", fill="black")

    pdf_path = tmp_path / "scanned.pdf"
    img.save(pdf_path, "PDF")

    with pytest.raises(ValueError):
        read_document(pdf_path, allow_ocr=False)
