documents = []


def add_document(name):
    documents.append(name)


def get_documents():
    return documents


def remove_document(name):
    """
    Removes a filename from the in-memory document list.
    Returns True if it was found and removed, False otherwise.

    Note: this only affects the tracked filename list — it does not
    delete the file from disk or remove its chunks from the FAISS/BM25
    vector store. See app/brain/vector_service.py if full deletion
    (including indexed chunks) is needed later.
    """
    if name in documents:
        documents.remove(name)
        return True
    return False
