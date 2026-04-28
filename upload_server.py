#!/usr/bin/env python3
"""Simple file upload server — no Gradio dependency."""
import os, sys, shutil, glob
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

UPLOAD_HTML = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>🦀 上傳 .set 檔案</title>
<style>
body{font-family:system-ui;max-width:500px;margin:40px auto;padding:0 20px;background:#1a1a2e;color:#eee}
h1{color:#e94560}form{display:flex;flex-direction:column;gap:12px}
input[type=file]{padding:12px;background:#16213e;border:2px dashed #e94560;border-radius:8px;color:#eee;font-size:16px}
button{padding:14px;background:#e94560;color:#fff;border:none;border-radius:8px;font-size:16px;cursor:pointer;font-weight:bold}
button:hover{background:#c81e45}#result{margin-top:20px;padding:16px;background:#16213e;border-radius:8px;white-space:pre-wrap;display:none}
.files{margin-top:20px}li{margin:6px 0}
</style></head><body>
<h1>🦀 Trade Strategy — 上傳 .set</h1>
<form id="form" enctype="multipart/form-data">
  <input type="file" name="files" multiple accept=".set,.csv,.txt" required>
  <button type="submit">上傳</button>
</form>
<div id="result"></div>
<div class="files"><h3>已上傳檔案：</h3><ul id="list"></ul></div>
<script>
document.getElementById('form').onsubmit=async e=>{
  e.preventDefault();
  const fd=new FormData(e.target);
  const r=await fetch('/upload',{method:'POST',body:fd});
  const j=await r.json();
  const el=document.getElementById('result');
  el.style.display='block';
  el.textContent=j.ok?'✅ '+j.msg:'❌ '+j.error;
  if(j.ok)loadFiles();
};
async function loadFiles(){
  const r=await fetch('/files');
  const j=await r.json();
  document.getElementById('list').innerHTML=j.files.map(f=>'<li>📄 '+f+'</li>').join('');
}
loadFiles();
</script></body></html>"""

@app.get("/")
async def index():
    return HTMLResponse(UPLOAD_HTML)

@app.post("/upload")
async def upload(files: list[UploadFile] = File(...)):
    saved = []
    for f in files:
        dest = os.path.join(UPLOAD_DIR, f.filename)
        with open(dest, "wb") as out:
            shutil.copyfileobj(f.file, out)
        saved.append(f.filename)
    return {"ok": True, "msg": f"已上傳 {len(saved)} 個檔案: {', '.join(saved)}"}

@app.get("/files")
async def list_files():
    files = sorted(os.path.basename(p) for p in glob.glob(os.path.join(UPLOAD_DIR, '*')))
    return {"files": files}

if __name__ == "__main__":
    print("🚀 Upload server on http://0.0.0.0:7860")
    uvicorn.run(app, host="0.0.0.0", port=7860)
