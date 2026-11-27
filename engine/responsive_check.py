"""375px 響應式量測工具（卡 #39 (c)：響應式無橫向滾動）

全站 719 頁從來冇量過「375px 有無橫向滾動」。本模組把量測固定成可重跑工具：
產生 probe 頁（把目標頁塞入 375px iframe，用 `documentElement.scrollWidth` 量），
再解析 Chrome `--dump-dom` 的輸出。

為何唔直接 `--window-size=375`：實測無效——`--dump-dom` 下 window-size 只影響
外層，iframe 內 `clientWidth` 仍然是 360（有 scrollbar 預留）。用 iframe 反而
可一次量多頁（每 chunk 一批），719 頁分 60 批跑約 5 分鐘。

⚠️ 三條實測教訓（寫進測試）：
  1. 探針可能整份 render 唔出 marker（`--virtual-time-budget` 內未 load 完）。
     **冇 marker 必須當「冇量到」，唔可以當「零問題」**——我第一次就係咁把
     707/719 當成全站通過。
  2. 溢出要分兩種：元素寬過視窗但**祖先有 `overflow-x:auto/scroll/hidden`**
     （表格可橫掃，視覺正常）vs 元素真跑出容器外（真溢出）。
     只睇 `scrollWidth` 分唔開——`ccy/EURUSD.html` 兩者同時存在。
  3. 頁族要按檔名歸一化（`xxx_10344.html` / `xxx_10437.html` 同一模板），
     否則 63 頁 `detailed_comparison_all_levels_*` 只會變 63 行噪音。
"""
import json
import os
import re
from typing import Dict, Iterable, List, Optional, Sequence

DEFAULT_WIDTH = 375
_MARKER = "RESULT "
_BLOCK = re.compile(r"RESULT (\[.*?\])</div>", re.S)

_PROBE_TMPL = """<!DOCTYPE html><html><head><meta charset="utf-8">
<title>responsive probe</title></head><body><div id="o">pending</div><script>
const P=%(pages)s; const W=%(width)d; const PRE=%(prefix)s; const res=[]; let i=0;
function inScroller(e){
  let n=e.parentElement;
  while(n){ const ox=getComputedStyle(n).overflowX;
    if(ox==='auto'||ox==='scroll'||ox==='hidden') return true;
    n=n.parentElement; }
  return false;
}
function nx(){
  if(i>=P.length){document.getElementById('o').textContent='RESULT '+JSON.stringify(res);return;}
  const p=P[i++]; const f=document.createElement('iframe');
  f.style.cssText='width:'+W+'px;height:600px;border:0'; f.src=PRE+p;
  f.onload=()=>{ setTimeout(()=>{ try{
    const d=f.contentDocument, de=d.documentElement, cw=de.clientWidth;
    const wide=[...d.querySelectorAll('*')].filter(e=>{
      const r=e.getBoundingClientRect();
      return r.right>cw+1 && r.width>0 && !inScroller(e);
    });
    res.push({p:p, sw:de.scrollWidth, cw:cw, outsideScroller:wide.length,
      txt:(d.body?d.body.textContent.length:0), title:(d.title||'').slice(0,60),
      kinds:[...new Set(wide.map(e=>e.tagName.toLowerCase()))].slice(0,6)});
  }catch(e){res.push({p:p,err:String(e)});} f.remove(); nx(); }, 500); };
  f.onerror=()=>{res.push({p:p,err:'load-fail'}); f.remove(); nx();};
  document.body.appendChild(f);
} nx();
</script></body></html>"""


def build_probe_html(pages: Sequence[str], width: int = DEFAULT_WIDTH,
                     prefix: str = "./") -> str:
    """產生一個 HTML probe 頁，逐頁塞入 width 寬的 iframe 並量溢出。

    `prefix` 係頁面 URL 前綴：`--dir docs` 時用 `/`（rel path 已經由 docs 根算），
    `--dir docs/ccy` 時要傳 `/ccy/`。**唔傳會 404 而量到細頁 ⇒ 假綠**：
    實測 `--dir docs/ccy` 忘了傳前綴，35 頁全部報「零溢出」，其實全部載入
    404 頁（`txt` 只有幾十字）。所以探針會回報 `txt`／`title` 供驗。
    """
    return _PROBE_TMPL % {"pages": json.dumps(list(pages)), "width": width,
                          "prefix": json.dumps(prefix)}


def parse_result(dom: str) -> Optional[List[Dict]]:
    """由 `--dump-dom` 輸出抽 RESULT。

    返回 `None` = **冇量到**（冇 marker／JSON 壞）。呢個區分係必要的：
    返回 `[]` 會令「冇測到」扮成「零問題」（實測踩過）。
    """
    m = _BLOCK.search(dom)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except ValueError:
        return None


def split_chunks(items: Sequence[str], size: int) -> List[List[str]]:
    """切成每批 size 個，覆蓋每項一次。"""
    if size <= 0:
        raise ValueError("chunk size 必須 > 0")
    return [list(items[i:i + size]) for i in range(0, len(items), size)]


def _family(page: str) -> str:
    """檔名歸一化：去目錄尾數字、去 `_<digits>.html` 尾綴。"""
    norm = page.replace("\\", "/")
    directory, _, base = norm.rpartition("/")
    stem = re.sub(r"\.html?$", "", base)
    stem = re.sub(r"[_-]\d+$", "", stem)
    return (directory + "/" + stem) if directory else stem


def looks_like_ghost(row: Dict) -> bool:
    """判斷係唔係「載入 404／空殼」而唔係真頁面。

    實測三種情形（唔可以一刀切用字元數）：
      · 真 404 空殼：`txt` 幾十字、`title` 係 `404 Not Found`／空
        （`--page-prefix` 被 MSYS 改壞時 36 頁全部如此）
      · Python `http.server` 的 404：`title="Error response"`、
        正文含 `Error code: 404` —— **title 冇「404」二字**，只查 title 會漏
        （實測 `--dir docs/ccy` 忘了傳 `--page-prefix` 就係咁假報「36 頁零溢出」）
      · 真薄頁：`reports/index_5117.html` `txt=96` 但 `title` 正常
        (`Signal 5117 — Trade Strategy Analysis Report`)，呢個係真頁，要計入
    """
    if row.get("err"):
        return True
    title = (row.get("title") or "").strip()
    low = title.lower()
    if "404" in low or "not found" in low or "error response" in low:
        return True
    if title:
        return False
    # title 空 ⇒ 靠長度。注意「舊格式 rows 冇 txt」要當真頁，唔可以當空殼
    # （否則所有舊 JSON 重算都變 suspicious，實測踩過）。
    if "txt" not in row:
        return False
    return row["txt"] < 200


def summarise(rows: Iterable[Dict]) -> Dict:
    """統計：幾頁溢出、幾頁係容器內（視覺正常）、幾頁真溢出、按族分佈。

    另計 `suspicious`：疑似載入 404／空殼的頁。**唔可以當「零溢出」算落 measured**
    ——實測 `--dir docs/ccy` 忘了傳 URL 前綴，35 頁全部載入 404 而報零溢出。
    """
    rows = [r for r in rows if "sw" in r or r.get("err")]
    families: Dict[str, Dict[str, int]] = {}
    over = contained = real = 0
    measured = 0
    real_pages: List[str] = []
    suspicious: List[str] = []
    for r in rows:
        if looks_like_ghost(r):
            suspicious.append(r["p"])
            continue
        measured += 1
        fam = _family(r["p"])
        f = families.setdefault(fam, {"measured": 0, "overflow": 0})
        f["measured"] += 1
        if r["sw"] > r["cw"] + 1:
            over += 1
            f["overflow"] += 1
            if r.get("outsideScroller", 0) > 0:
                real += 1
                real_pages.append(r["p"])
            else:
                contained += 1
    return {
        "measured": measured,
        "overflow": over,
        "contained": contained,
        "real": real,
        "real_pages": real_pages,
        "suspicious": suspicious,
        "overflow_ratio": (over / measured) if measured else 0.0,
        "families": families,
    }


def is_plausible_page_prefix(prefix: str) -> bool:
    """檢查 page-prefix 係唔係合理的 URL 前綴。

    ⚠️ 實測陷阱（Windows Git Bash）：`--page-prefix /ccy/` 會被 MSYS 的路徑
    自動轉換改寫成 `C:/Program Files/Git/ccy/`——**連 `--page-prefix=/ccy/`
    等號形式都一樣中招**（實測四種寫法只有 `./ccy/`、`ccy/`、
    `MSYS2_ARG_CONV_EXCL='*'` 或 `MSYS_NO_PATHCONV=1` 逃得過）。後果係 iframe
    全部 404、量到 `title="Error response"` 的空殼、總結報「0 頁溢出」——**假綠**。

    對策：默認用 `./`（相對 probe 頁，`--outdir` 與 `--dir` 相同時剛好等價，
    而且冇前導斜線 ⇒ MSYS 唔會改寫）。呢個 guard 就係攔 `C:/...` 呢類。
    """
    if not prefix:
        return False
    if ":" in prefix:
        return False
    if prefix.startswith("//"):
        return True
    return prefix.startswith("/") or prefix.startswith("./") or not prefix.startswith("-")


def chrome_path() -> Optional[str]:
    """Windows／Linux 的 Chrome 路徑。"""
    for p in (r"C:\Program Files\Google\Chrome\Application\chrome.exe",
              r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
              "/usr/bin/google-chrome", "/usr/bin/chromium"):
        if os.path.exists(p):
            return p
    return None


def main(argv=None) -> int:                       # pragma: no cover — 需真 Chrome
    """量測全站 375px 溢出。

        python -m engine.responsive_check --dir docs --width 375 [--outdir DIR]
        python -m engine.responsive_check --dir docs --json out.json

    `--outdir` 會把 probe 頁寫到該目錄（要喺 docs 內、經 http server 服務），
    用完自行刪除；唔給就只印統計。
    """
    import argparse
    import glob
    import subprocess

    ap = argparse.ArgumentParser(description="375px 橫向溢出量測（卡 #39(c)）")
    ap.add_argument("--dir", default="docs")
    ap.add_argument("--width", type=int, default=DEFAULT_WIDTH)
    ap.add_argument("--chunk", type=int, default=12)
    ap.add_argument("--url-prefix", default="http://127.0.0.1:8794",
                    help="probe 頁本身的 URL 前綴，要對應 --outdir 喺 http server "
                         "根下的位置（--dir docs 時 http://127.0.0.1:8794；"
                         "--dir docs/ccy 時 .../ccy）")
    ap.add_argument("--page-prefix", default="./",
                    help="iframe 內頁面的 URL 前綴（相對於 probe 頁）。"
                         "默認 ./ ⇒ 與 --outdir 同層時剛好指到同目錄的頁。"
                         "Windows Git Bash 唔好用前導 /（會被 MSYS 改成 C:/...）")
    ap.add_argument("--outdir", help="probe 頁落點（要喺 --dir 內並經 http 服務）")
    ap.add_argument("--budget", type=int, default=40000,
                    help="Chrome --virtual-time-budget（毫秒）。大頁（66 萬字元）"
                         "要 40s；細頁 15s 夠。")
    ap.add_argument("--json", help="把原始 rows 寫成 JSON")
    args = ap.parse_args(argv)

    if not is_plausible_page_prefix(args.page_prefix):
        print("❌ --page-prefix 唔似 URL 前綴：%r\n"
              "   實測 Windows Git Bash 會把 `/ccy/` 轉成 "
              "`C:/Program Files/Git/ccy/`（iframe 全部 404 ⇒ 假報零溢出）。\n"
              "   用 `MSYS_NO_PATHCONV=1` 或 `--page-prefix=/ccy/`（等號形式）。"
              % args.page_prefix)
        return 2

    exe = chrome_path()
    if not exe:
        print("❌ 搵唔到 Chrome")
        return 2

    pages = []
    for p in glob.glob(os.path.join(args.dir, "**", "*.html"), recursive=True):
        rel = os.path.relpath(p, args.dir).replace(os.sep, "/")
        pages.append(rel)
    pages.sort()

    rows: List[Dict] = []
    missing: List[str] = []

    def run_chunk(chunk: List[str], tag: str) -> Optional[List[Dict]]:
        probe = build_probe_html(chunk, args.width, args.page_prefix)
        name = "_rc_%s.html" % tag
        path = os.path.join(args.outdir, name)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(probe)
        target = args.url_prefix.rstrip("/") + "/" + name
        try:
            out = subprocess.run(
                [exe, "--headless=new", "--disable-gpu", "--no-sandbox",
                 "--window-size=1200,900", "--virtual-time-budget=%d" % args.budget,
                 "--dump-dom", target], capture_output=True).stdout.decode("utf-8", "replace")
        finally:
            os.remove(path)
        return parse_result(out)

    chunks = split_chunks(pages, args.chunk)
    for idx, chunk in enumerate(chunks):
        parsed = run_chunk(chunk, "%03d" % idx)
        if parsed is None:
            # 整批冇 marker（virtual-time-budget 內未 load 完）⇒ 拆細重試，
            # 再唔得就逐頁試；仍然冇 marker 才列入 unmeasured（唔可以當 OK）。
            parsed = []
            for sub in split_chunks(chunk, max(1, len(chunk) // 3)):
                p2 = run_chunk(sub, "%03d_r" % idx)
                if p2 is None:
                    parsed = None
                    break
                parsed.extend(p2)
        if parsed is None:
            missing.extend(chunk)
        else:
            rows.extend(parsed)

    s = summarise(rows)
    s["unmeasured"] = missing
    print(json.dumps(s, ensure_ascii=False, indent=1))
    if args.json:
        with open(args.json, "w", encoding="utf-8", newline="\n") as fh:
            json.dump({"summary": s, "rows": rows}, fh, ensure_ascii=False, indent=1)
    return 0 if not missing else 1


if __name__ == "__main__":                        # pragma: no cover
    raise SystemExit(main())
