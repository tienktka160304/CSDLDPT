from __future__ import annotations

from pathlib import Path
import tempfile

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .database import connect, get_images_dir, get_db_path
from .feature_extractor import extract_features_from_image
from .search import ImageSearchEngine


class SearchByFilenameRequest(BaseModel):
    filename: str
    top_k: int = 5
    exclude_self: bool = True


app = FastAPI(
    title="PTIT Multimedia Database - Object Image Search API",
    description="Backend phần 2: lưu trữ vector đặc trưng và tìm kiếm top-k ảnh đồ vật tương đồng.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

conn = connect(get_db_path())
engine = ImageSearchEngine(conn)

images_dir = get_images_dir()
if images_dir.exists():
    app.mount("/images", StaticFiles(directory=str(images_dir)), name="images")


@app.get("/")
def root():
    return {
        "message": "Image search backend is running",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "database": str(get_db_path()),
        "images_dir": str(images_dir),
        "total_images": engine.count,
        "vector_dim": engine.dim,
    }


@app.get("/images-list")
def list_images(limit: int = 20, offset: int = 0):
    limit = max(1, min(limit, 100))
    offset = max(0, offset)
    rows = conn.execute(
        """
        SELECT id, filename, stored_path, original_width, original_height, status
        FROM images
        ORDER BY id
        LIMIT ? OFFSET ?
        """,
        (limit, offset),
    ).fetchall()
    return {
        "limit": limit,
        "offset": offset,
        "items": [
            {
                "id": int(r["id"]),
                "filename": r["filename"],
                "stored_path": r["stored_path"],
                "image_url": f"/images/{r['filename']}",
                "original_width": r["original_width"],
                "original_height": r["original_height"],
                "status": r["status"],
            }
            for r in rows
        ],
    }


@app.post("/search-by-filename")
def search_by_filename(req: SearchByFilenameRequest):
    try:
        query_vector = engine.vector_from_filename(req.filename)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy ảnh: {req.filename}")

    results = engine.search_vector(
        query_vector,
        top_k=req.top_k,
        exclude_filename=req.filename if req.exclude_self else None,
    )
    return {
        "query": req.filename,
        "top_k": req.top_k,
        "results": results,
    }


@app.post("/search-image")
async def search_image(file: UploadFile = File(...), top_k: int = Form(5)):
    suffix = Path(file.filename or "query.jpg").suffix or ".jpg"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        features = extract_features_from_image(tmp_path)
        query_vector = engine.vector_from_features(features)
        results = engine.search_vector(query_vector, top_k=top_k)
        return {
            "query_filename": file.filename,
            "top_k": top_k,
            "results": results,
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Lỗi xử lý ảnh đầu vào: {exc}")
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass
