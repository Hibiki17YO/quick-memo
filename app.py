from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from pydantic import BaseModel
from pathlib import Path
import uuid

from paths import bundle_dir, app_dir
from db import (
    create_memo, get_memos, get_memo, update_memo, delete_memo,
    create_image, delete_image,
    get_categories, create_category, update_category, delete_category,
    get_settings, get_setting, set_setting,
)

app = FastAPI()

BUNDLE = bundle_dir()
APP = app_dir()

# Ensure uploads dir exists at runtime location
(APP / "uploads").mkdir(exist_ok=True)

app.mount("/static", StaticFiles(directory=str(BUNDLE / "static")), name="static")
app.mount("/uploads", StaticFiles(directory=str(APP / "uploads")), name="uploads")

templates = Jinja2Templates(directory=str(BUNDLE / "templates"))


class MemoCreate(BaseModel):
    title: str = ""
    content: str = ""
    is_pinned: int = 0
    category_id: int | None = None
    tags: str = ""


class MemoUpdate(BaseModel):
    title: str = ""
    content: str = ""
    is_pinned: int = 0
    category_id: int | None = None
    tags: str = ""


class CategoryCreate(BaseModel):
    name: str


class CategoryUpdate(BaseModel):
    name: str


class SettingsUpdate(BaseModel):
    settings: dict[str, str]


# --- Pages ---

@app.get("/", response_class=HTMLResponse)
async def management_page(request: Request):
    return templates.TemplateResponse("management.html", {"request": request})


@app.get("/api/editor-html", response_class=HTMLResponse)
async def editor_page(request: Request):
    return templates.TemplateResponse("editor.html", {"request": request})


# --- Memo API ---

@app.get("/api/memos")
async def list_memos(q: str = "", sort: str = "newest", limit: int = 20, offset: int = 0,
                     category_id: int | None = None, tag: str = ""):
    return get_memos(q=q, sort=sort, limit=limit, offset=offset,
                     category_id=category_id, tag=tag)


@app.get("/api/memos/{memo_id}")
async def read_memo(memo_id: int):
    memo = get_memo(memo_id)
    if not memo:
        raise HTTPException(status_code=404, detail="Memo not found")
    return memo


@app.post("/api/memos")
async def create_memo_api(data: MemoCreate):
    return create_memo(title=data.title, content=data.content, is_pinned=data.is_pinned,
                       category_id=data.category_id, tags=data.tags)


@app.put("/api/memos/{memo_id}")
async def update_memo_api(memo_id: int, data: MemoUpdate):
    memo = update_memo(memo_id, title=data.title, content=data.content,
                       is_pinned=data.is_pinned, category_id=data.category_id, tags=data.tags)
    if not memo:
        raise HTTPException(status_code=404, detail="Memo not found")
    return memo


@app.delete("/api/memos/{memo_id}")
async def delete_memo_api(memo_id: int):
    delete_memo(memo_id)
    return {"ok": True}


# --- Category API ---

@app.get("/api/categories")
async def list_categories():
    return get_categories()


@app.post("/api/categories")
async def create_category_api(data: CategoryCreate):
    return create_category(data.name)


@app.put("/api/categories/{cat_id}")
async def update_category_api(cat_id: int, data: CategoryUpdate):
    cat = update_category(cat_id, data.name)
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    return cat


@app.delete("/api/categories/{cat_id}")
async def delete_category_api(cat_id: int):
    delete_category(cat_id)
    return {"ok": True}


# --- Settings API ---

@app.get("/api/settings")
async def read_settings():
    return get_settings()


@app.put("/api/settings")
async def write_settings(data: SettingsUpdate):
    for k, v in data.settings.items():
        set_setting(k, v)
    return {"ok": True}


# --- Image Upload ---

@app.post("/api/upload")
async def upload_image(file: UploadFile = File(...), memo_id: int = Form(0)):
    ext = Path(file.filename).suffix if file.filename else ".png"
    filename = f"{uuid.uuid4().hex}{ext}"
    dest = APP / "uploads" / filename
    content = await file.read()
    dest.write_bytes(content)
    image_id = create_image(memo_id, filename, file.filename or "image.png")
    return {"url": f"/uploads/{filename}", "id": image_id}


@app.delete("/api/images/{image_id}")
async def delete_image_api(image_id: int):
    ok = delete_image(image_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Image not found")
    return {"ok": True}
