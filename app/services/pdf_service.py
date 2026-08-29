from PyPDF2 import PdfReader


def extract_pdf(file_path: str) -> str:
    """
    Extract text from a PDF file
    """

    text = ""

    reader = PdfReader(file_path)

    for page in reader.pages:
        text += page.extract_text() or ""

    return text