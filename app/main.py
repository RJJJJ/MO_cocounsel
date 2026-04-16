from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.api.research import router as research_router

app = FastAPI(title="MO_cocounsel Research API")

# 註冊 Day 54 建立的 router
app.include_router(research_router)

# === 以下為 Day 56 新增：掛載前端靜態檔案以供本地 Demo 使用 ===

# 掛載整個 frontend 資料夾，讓 FastAPI 可以讀取裡面的靜態檔案
app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")

# 設定當使用者訪問根目錄 (http://127.0.0.1:8000/) 時，直接回傳 Demo 的 HTML
@app.get("/")
async def root():
    return FileResponse("frontend/demo_research_integration.html")