def chunk_text(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    """
    Splits text into chunks of a specified size with overlap.
    (This is a basic example; consider using libraries for robustness)
    """
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - chunk_overlap
        if end >= len(text):
             break # Exit loop if end goes beyond text length
    return chunks

# --- Inside create_database.py loop ---
# after: full_text += page.get_text()
# chunk_size = 1000  # Example size (adjust based on model/needs)
# chunk_overlap = 100 # Example overlap
# text_chunks = chunk_text(full_text, chunk_size, chunk_overlap)
# --- Now process text_chunks instead of full_text ---