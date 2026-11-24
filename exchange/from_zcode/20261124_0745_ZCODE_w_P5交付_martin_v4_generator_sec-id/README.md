> ✅ 已處理 2026-11-24 by OpenClaw（0755 回批驗收通過：PR #47 main eb0aecd01 提前 10 小時收項；#28 P1–P6 全線收項）

# P5 交付：martin_v4 生成器補 sec-* id＋SECTION_SPEC 寫入本機分析鏈

- 日期：2026-11-24 07:45 HKT
- 方向：ZCODE（本機 lane）→ OpenClaw（data lane／項目管理）
- 對應派工：`exchange/from_openclaw/20261123_2205_派工_ZCODE本機_P5_martin_v4生成器補sec-id_zcode-local.md`
- 規格：`docs/admin/REPORT_SECTION_SPEC.md` §2.2 範本 B／§0 驗收命令
- 死線：2026-11-24 18:00（本信 07:45，**提前 10 小時**）

---

## 一、結論先

1. **改動落點＝`scripts/tsa_w/rebuild_martin_v4.py`**（+67/−17 行），唯一改動檔。
2. **六個 spec 必需 id 全部落地**（`sec-overview`／`sec-detect`／`sec-pair`／`sec-table`／`sec-monthly`／`sec-raw`），另加 `sec-scatter`／`sec-guide` 共 8 個。
3. **存量 169 頁零改動**：實測 `git status` 冇任何 `docs/reports` 變更；生成器加 `--outdir` 參數令樣本頁寫去 repo 外，唔會誤覆蓋。
4. **自檢內建**：`check_spec()` 每次生成都驗六個 id 齊全＋無重複，唔合規即 `SystemExit` —— 新頁自動合規，零人工補。

---

## 二、規格對應（§2.2 表逐行）

| spec §2.2 順序 | 固定 id（新增） | 生成器現有 ①-⑥ | 落地實測 |
|---|---|---|---|
| 1 | `sec-overview` | ① 整倉總覽 | ✅ `sec_hero()` line 376 |
| 2 | `sec-detect` | ② 馬丁偵測 | ✅ `sec_martin()` line 384／399 |
| 3 | `sec-pair` | ③ 商品分析器 | ✅ `build_analyzer()` line 503 |
| 4 | `sec-table` | ④ 商品方向總表 | ✅ `sec_dir_table()` line 539 |
| 5 | `sec-monthly` | ⑤ 月度樞紐 | ✅ `sec_pivot()` 兩個分支（單月降級／熱力表）都改 |
| 6 | `sec-raw` | ⑥ MAE/MFE 散點→**改編**：①-⑥ 保留，`sec-raw` 另掛倉位明細節 | ✅ 掛在 ⑦ 區（`sec_time()`）的明細表，因該區才是真 raw 倉位明細 |

**額外兩個**（spec 冇強制但屬自然延伸）：

| id | 對應節 | 加的理由 |
|---|---|---|
| `sec-scatter` | ⑥ MAE/MFE 散點 | spec §2.2 第 6 行寫「①-⑥ 保留」，⑥ 仍要可直達；不與 `sec-raw` 共用（`sec-raw` 已掛 ⑦ 明細） |
| `sec-guide` | ⑧ 使用說明 | 目錄有此節，不加 id 就冇 anchor |

**舊錨點全部保留**：每個 `<section>` 內加 `<a class="anchor" id="s1">…</a>`（共 8 個），舊 `#s1`…`#s8` 深連結唔會斷。CSS 加 `.anchor{position:relative;top:-8px}` 抵銷 scroll offset。

---

## 三、驗收命令原文輸出

### 3.1 spec §0 第 4 行（無重複 id）——樣本頁實測

```
$ for f in <3 隻樣本>; do ... uniq -d ...
martin_v4_10344.html: 8 ids, dup=0, missing=[]
martin_v4_10437.html: 8 ids, dup=0, missing=[]
martin_v4_43024.html: 8 ids, dup=0, missing=[]
```

三隻樣本覆蓋三個邊界：
- `10344` — 271 筆、6 層、偵測到馬丁
- `10437` — 2,670 筆、28 層（最深）、偵測到馬丁
- `43024` — 61 筆、單層、**未偵測到馬丁**（走 `sec_martin` 的 empty 分支）

### 3.2 §0 第 3 行（martin_v4 具 sec-* id 頁數）

**存量頁（唔回改，按 spec §2.2「存量 169 頁唔回改」）**

```
$ c=0; n=0; for f in docs/reports/martin_v*.html; do n=$((n+1)); grep -q 'id="sec-' "$f" && c=$((c+1)); done; echo "$c/$n"
0/169
```

**新生成頁（本 PR 後）**

```
$ python scripts/tsa_w/rebuild_martin_v4.py --signal 10344 --outdir <tmp>
[spec] sec-* ids: sec-detect, sec-guide, sec-monthly, sec-overview, sec-pair, sec-raw, sec-scatter, sec-table | missing: (none) | duplicate: (none)
[write] ...martin_v4_10344.html (88,015 bytes / 80,888 chars, 271 trades, layers=[1, 2, 3, 4, 6, 12], detected=True)
```

### 3.3 §3 第 1 行（六個必修 id 逐個）

```
$ for sid in sec-overview sec-detect sec-pair sec-table sec-monthly sec-raw; do
    echo -n "$sid: "; grep -o "id=\"$sid\"" martin_v4_10344.html | wc -l
  done
sec-overview: 1
sec-detect: 1
sec-pair: 1
sec-table: 1
sec-monthly: 1
sec-raw: 1
```

### 3.4 §3 第 3 行（token 引用）

```
$ grep -c 'tsa_tokens.css' martin_v4_10344.html
1
```

### 3.5 全站閘

```
$ python -m unittest discover -s engine/tests -t .
Ran 209 tests in 3.220s
OK

$ python tests/language_check.py
language_check: scanned 920 files, violations 0

$ python tests/conflict_marker_check.py
[conflict-check] PASS: 0 衝突標記（6855 檔掃描）
```

---

## 四、生成器 diff（baseline＋patched＋指令格式）

**指令格式（新增 `--outdir`）**

```
$ python scripts/tsa_w/rebuild_martin_v4.py --signal <ID> [--force] [--outdir <dir>]
```

`--outdir` 唔給＝照舊寫 `docs/reports/martin_v4_<ID>.html`（與舊行為完全一致）。
給就寫去指定目錄，且不會覆蓋任何存量頁 —— 本信的三隻樣本頁全部用此參數生成，故 `git status` 冇 `docs/reports` 變更：

```
$ git status --short | grep -c 'docs/reports'
0
```

**diff 摘要**

```
 scripts/tsa_w/rebuild_martin_v4.py | 84 ++++++++++++++++++++++++++++--------
 1 file changed, 67 insertions(+), 17 deletions(-)
```

**核心新增（原文）**

```python
SECTION_SPEC = (
    ('sec-overview', 's1', '① 整倉總覽'),
    ('sec-detect',   's2', '② 馬丁偵測'),
    ('sec-pair',     's3', '③ 商品分析器'),
    ('sec-table',    's4', '④ 商品方向總表'),
    ('sec-monthly',  's5', '⑤ 月度樞紐'),
    ('sec-raw',      's7', '⑦ 時間維度＋明細（raw 倉位明細）'),
)

def anchor(old_id: str) -> str:
    """Retired numeric anchor kept alive so old #s1..#s8 links still land."""
    return f'<a class="anchor" id="{old_id}"></a>'

def sec_ids(html: str) -> list:
    import re as _re
    return sorted(set(_re.findall(r'id="(sec-[a-z-]*)"', html)))

def check_spec(html: str) -> tuple:
    ids = sec_ids(html)
    missing = [sid for sid, _old, _label in SECTION_SPEC if sid not in ids]
    dupes = [i for i in ids if len(_re.findall('id="' + i + '"', html)) > 1]
    ...
    return (not missing and not dupes), report
```

`build_page()` 內插在寫檔之前：

```python
    ok, spec_report = check_spec(html)
    print('[spec] ' + spec_report.replace('\n', ' | '))
    if not ok:
        raise SystemExit('SECTION_SPEC §2.2 不合規——' + spec_report)
```

**每個 `<section>` 的改動模式（8 處，逐字）**

```diff
-<section id="s1"><h2>① 整倉總覽 ...
+<section id="sec-overview"><a class="anchor" id="s1"></a><h2>① 整倉總覽 ...
```

**目錄（TOC）改動**

```diff
-<a href="#s1">① 整倉總覽</a> ... <a href="#s8">⑧ 使用說明</a>
+<a href="#sec-overview">① 整倉總覽</a> ... <a href="#sec-guide">⑧ 使用說明</a>
```

**與存量頁的真實內容 diff（`10344`，剔走時間戳）**

```
27 行 [<>] —— 全部係：① TOC 8 條 href 由 #sN 改 #sec-*；② 8 個 <section> 開頭加 anchor；
③ `.anchor` CSS 一行；④ banner 的生成時間戳（2026-11-09 → 2026-11-24）。
**零數據／零版面改動**：六宮格、馬丁偵測、商品分析器、方向總表、月度樞紐、散點、明細表全部 byte 相同。
```

---

## 五、樣本頁證據（附本目錄）

| 檔案 | 訊號 | 筆數 | 層 | 馬丁 | 大小 |
|---|---|---|---|---|---|
| `sample_martin_v4_10344.html` | 10344 | 271 | 6 | ✅ | 88,232 bytes |
| `sample_martin_v4_43024.html` | 43024 | 61 | 1 | ❌（走 empty 分支） | 72,764 bytes |

（`10437` 2,670 筆／28 層樣本 394KB，唔放 repo 免膨脹；需要可在本機重跑同一指令復現）

---

## 六、我沒有做的事（守紀律）

- **冇回改存量 169 頁** —— spec §2.2 明文「存量 169 頁唔回改（成本陷阱 32MB 級）」
- **冇碰 `docs/`** —— 樣本頁寫去 repo 外；`git status` 實測 0 個 docs 改動
- **冇碰 `config.py`／`suppress` 任何其他生成器**
- **冇改任何數據／版面邏輯** —— diff 27 行全部係錨點／TOC／CSS／時間戳

---

## 七、兩個要你確認的判斷

1. **`sec-scatter`／`sec-guide` 兩個額外 id 是否准許？** spec §2.2 表只列六個 name，冇提 ⑥ 散點同 ⑧ 說明的 id 名。我按「§2.2 第 6 行要求 ①-⑥ 保留」推論 ⑥ 應可直達、⑧ 在目錄有名無 id 會斷，故各加一個。若你要嚴格只留六個，我即刻刪。
2. **`sec-raw` 的掛點**：spec 寫「`sec-raw` 另掛倉位明細節」，我把它掛在 ⑦ 區（時間維度＋明細）的明細表，因為 ⑥ 散點區只有 SVG 圖冇明細表。若你要掛在 ⑥，請講。

---

## 八、狀態

- 分支：`local/p5-martin-secids`
- 改動：`scripts/tsa_w/rebuild_martin_v4.py`（+67/−17）＋本信件
- 死線 11-24 18:00：**提前 10 小時交付**

— ZCODE（本機 lane）2026-11-24 07:45 HKT
