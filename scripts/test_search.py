from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.database import connect
from app.search import ImageSearchEngine


conn = connect(PROJECT_ROOT / "data" / "image_search.db")
engine = ImageSearchEngine(conn)

query = "0000_image10025.jpg"
print("Total images:", engine.count)
print("Vector dim:", engine.dim)
print("Query:", query)
for item in engine.search_vector(engine.vector_from_filename(query), top_k=5, exclude_filename=query):
    print(item)
