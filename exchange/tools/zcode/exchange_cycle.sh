#!/usr/bin/env bash
# ============================================================================
# exchange_cycle.sh v3.5 — exchange 信箱巡檢＋精準 push（ZCODE 收信代表 lane）
#   ★ 此腳本正本住喺 repo：exchange/tools/zcode/exchange_cycle.sh（v3 起）
#     scripts/ 下嗰份只係安裝副本；運行時自動 exec repo 正本，永遠用最新版
#
# v3.5 重點（回應 OpenClaw 1315 回執：⑦點頭開工，照 ⑥ 慣例）：
#   ⑦ 蓋章判定三重收窄（治「引述舊章／他方自章」兩種假陰性）：
#      a. 章只認 by ZCODE*——OpenClaw 信頭自章係佢側回執標記，唔代表我方已處理
#         （1315 信實測：自章令掃描器跳過未處理信）
#      b. 章須喺頭部窗口（frontmatter 後 STAMP_WIN=10 行內；0825 兩方約定檔頂蓋章，
#         實測全信箱 27 封歷史章均喺 ≤10 行）
#      c. 章內日期 ≥ 信件 frontmatter 日期——內文引述舊章（1119 實測）日期必早於信日期，
#         唔再命中；信日期唔可解析時照舊認章（防舊信翻案）
#
# v3.4 重點（回應 OpenClaw 1119 回執：第⑥項點頭開工，照 ⑤ 同款模式）：
#   ⑥ fileMode 根治：恆設 core.fileMode false（新 clone 兩落地位即設）——
#      防「repo 存活跨回滾／外部 chmod」造成嘅全檔假 M mode 噪音
#      （2026-10-27 10:31 實際發生一次，171 檔假 M 阻 ff 合併；gcfg 值唔同先寫，穩態零寫入）
#
# v3.3 重點（回應 OpenClaw 2340 派工＋0015 增補五項加固，老闆 10-27 指示即刻處理）：
#   ① 診斷可見：步驟失敗→diag_dump 落 stderr（df -h／失敗指令 stderr 原文節錄，
#      頭尾截斷防爆炸）；巡查報告加磁碟使用率一行
#   ② 稀疏重建：repo 蒸發後改 sparse clone（--depth 1 --filter=blob:none＋cone
#      淨拉 exchange/），SSH→HTTPS 兩路，帶耗時計時；稀疏唔過先 fallback 完整
#   ③ inspect 真・唯讀：config 改「值唔同先寫」（穩態零寫入）；巡查前後 git
#      status 自檢，inspect 路徑零工作區 side-effect
#   ④ push origin 自修復：origin=https 而 key 在位→自動 set-url SSH 先推；
#      key 唔在位→如實報「無 key」留本地，唔再誤報「憑證/遠端分叉」
#   ⑤ quotePath 根治：恆設 core.quotePath false（新 clone 即設）＋掃描改
#      git ls-files -z 零轉義——中文目錄名信件唔再漏掃
#
# v3.2 重點（回應 OpenClaw 0825 信＋08:56 push 撞板實測）：
#   1. STAMP_RE 收窄：要求 by＋(OpenClaw|ZCODE)，防信件內文行首引用協議原文假陽性
#   2. push 前自動 fetch＋rebase：遠端有新 commit（watcher :19／CCY :00）時自動
#      合併，唔再因非 ff 被拒（2026-10-26 08:56 實際發生，警報一次）
#
# v3 重點（回應 OpenClaw 0725 信修正）：
#   1. 信件判定修正：只掃「信件入口」（from_openclaw/*/manifest.md ＋頂層 loose .md），
#      唔再將附件 .md 當信（修正1：掃出附件 taskA_enumeration.md 假新信）
#   2. 蓋章匹配改全檔＋行首錠點（^>??✅ 已處理 / ⏳ 進行中）
#      （修正1：2330_reply 個章喺第 34 行，12 行窗口掃唔到）
#   3. 自裝機制：repo 版運行時自動安裝副本到 scripts/；重建後 clone 即用
#   4. 警報分層（回應修正2）：stdout 警報（排程 job 原文轉達老闆＝唔靠 git
#      嘅通道）→ worklog（第三層記錄）。判定準則：push 全壞都送得出去先算警報
#   冪等 bootstrap 不變：ssh 缺→提取 deb；key 缺但 upload zip 在位→自動恢復；
#   repo 缺→稀疏 clone（SSH 優先，HTTPS 唯讀 fallback；都唔過→完整 clone）
#
# 用法:
#   bash .../exchange_cycle.sh          巡檢（退出碼: 0=無新信/已報警, 10=有新信, 1=錯誤）
#   bash .../exchange_cycle.sh push "<訊息>" <path>...   精準 add→commit→push
# 鐵律: 唔 force push、唔刪分支、精準 add、禁 commit tsa_pw.txt／martin_v4/
#   credentials／任何私鑰（含 zcode_exchange_key）
# ============================================================================

set -u
ORIG_ARGS=("$@")   # 捕獲原始 argv：self_install exec 時要完整重現（push 子命令路徑唔可以丟失）

REPO="/home/z/my-project/exchange-repo"
SSH_KEY="/home/z/my-project/.keys/zcode_exchange_key_20261028"   # 2026-10-28 rotate#2：私鑰存 .keys/（project volume 捱得過平台對 ~/.ssh 嘅 rollback；~/.ssh 已兩次被還原食key）
KEY_ZIP="/home/z/my-project/upload/zcode_test_key.zip"
SSHBIN_DIR="/home/z/my-project/.sshbin"
SSH_BIN="$SSHBIN_DIR/extract/usr/bin/ssh"
REMOTE_SSH="git@github.com:alvin-forex/trade-strategy-analyzer.git"
REMOTE_HTTPS="https://github.com/alvin-forex/trade-strategy-analyzer.git"
BRANCH="main"
SCAN_DIR="exchange/from_openclaw"
STAMP_RE='^>?[[:space:]]*(✅[[:space:]]*已處理|⏳[[:space:]]*進行中).*by[[:space:]]+ZCODE'   # v3.5 收窄：只認 by ZCODE*（我方回執）——OpenClaw 自章唔代表我方已處理；行首錨點防協議原文假陽性
STAMP_WIN=10   # ⑦ 頭部窗口：frontmatter 後 N 行內嘅章先算（0825 兩方約定檔頂蓋章）
WORKLOG="/home/z/my-project/worklog.md"
REPO_SELF="${REPO}/exchange/tools/zcode/exchange_cycle.sh"
SCRIPTS_COPY="/home/z/my-project/scripts/exchange_cycle.sh"

FORBIDDEN_RE='(^|/)(tsa_pw\.txt|\.env([^/]*)?|.*\.pem|id_rsa[^/]*|.*credentials.*|.*password.*|zcode_exchange_key|zcode_test_key(\.zip)?)(/|$)|(^|/)martin_v4(/|$)'

hkt_now()   { TZ=Asia/Hong_Kong date '+%H:%M'; }
hkt_stamp() { TZ=Asia/Hong_Kong date '+%Y-%m-%d %H:%M'; }
log()       { echo "[$(hkt_stamp) HKT] $*"; }

# ---- ① 診斷段：一律落 stderr（stdout 保留畀巡查報告解析）----
dline() { echo "[diag] $*" >&2; }
# df -h（根目錄＋repo 掛載點）＋失敗指令 stderr 原文節錄（>12 行→頭6＋尾3，截斷防爆炸）
diag_dump() {
  dline "---- df -h（/ 及 repo 掛載點） ----"
  df -h / "$REPO" 2>&1 | sed 's/^/[diag] /' >&2
  if [ -n "${1:-}" ]; then
    dline "---- 失敗指令 stderr 原文節錄 ----"
    local n; n="$(printf '%s\n' "$1" | wc -l)"
    if [ "$n" -gt 12 ]; then
      printf '%s\n' "$1" | head -6 | sed 's/^/[diag] /' >&2
      dline "...（中間省略 $((n-9)) 行）..."
      printf '%s\n' "$1" | tail -3 | sed 's/^/[diag] /' >&2
    else
      printf '%s\n' "$1" | sed 's/^/[diag] /' >&2
    fi
  fi
}
# 磁碟使用率一行（巡查報告用，stdout）
disk_line() { df -h / "$REPO" 2>/dev/null | awk 'NR>1{printf "%s %s  ", $6, $5}'; }

# ---- 自裝機制（最頂執行，case 解析之前）----
# repo 正本為準：從其他路徑調用就立即 exec 正本（用完整原始 argv）；
# 正本運行時同步副本到 scripts/。喺頂部執行＝任何版本副本都喺 shift 參數之前轉跳，唔會丟失子命令
self_install() {
  local self; self="$(readlink -f "$0")"
  if [ "$self" != "$REPO_SELF" ] && [ -f "$REPO_SELF" ]; then
    exec bash "$REPO_SELF" "${ORIG_ARGS[@]}"
  fi
  if [ "$self" = "$REPO_SELF" ] && [ -d "$(dirname "$SCRIPTS_COPY")" ]; then
    if ! cmp -s "$REPO_SELF" "$SCRIPTS_COPY" 2>/dev/null; then
      cp -f "$REPO_SELF" "$SCRIPTS_COPY" 2>/dev/null &&
        log "[install] 已同步正本 → scripts/exchange_cycle.sh" >&2
    fi
  fi
}
self_install

# 警報：寫 worklog（冇就建）＋ stdout——修復①嘅核心：失敗一定有人知
alarm() {
  local msg="$1"
  log "⚠️ 警報: $msg"
  {
    echo ""
    echo "> ⚠️ **警報 $(hkt_stamp) HKT** — $msg"
  } >> "$WORKLOG" 2>/dev/null || {
    echo "# Worklog — TSA exchange（ZCODE 端）" > "$WORKLOG"
    echo "> ⚠️ **警報 $(hkt_stamp) HKT** — $msg" >> "$WORKLOG"
  }
}

# --- 自癒 1：ssh 客戶端（OS 級冇裝、無 sudo → 無 root 提取 deb）---
ensure_ssh() {
  command -v ssh >/dev/null 2>&1 && { echo "ssh"; return 0; }
  [ -x "$SSH_BIN" ] && { echo "$SSH_BIN"; return 0; }
  log "[boot] ssh 客戶端缺失，無 root 提取 openssh-client..." >&2   # stderr：函數 stdout 只準輸出二進制路徑（防 $() 捕獲污染）
  mkdir -p "$SSHBIN_DIR"
  ( cd "$SSHBIN_DIR" \
      && timeout 120 apt-get download openssh-client >/dev/null 2>&1 \
      && dpkg -x openssh-client_*.deb extract/ >/dev/null 2>&1 ) || {
    ( cd "$SSHBIN_DIR" && timeout 150 apt-get update -qq >/dev/null 2>&1 \
        && timeout 120 apt-get download openssh-client >/dev/null 2>&1 \
        && dpkg -x openssh-client_*.deb extract/ >/dev/null 2>&1 )
  }
  [ -x "$SSH_BIN" ] && { echo "$SSH_BIN"; return 0; }
  log "[boot][ERROR] ssh 提取失敗" >&2
  return 1
}

# --- 自癒 2：部署金鑰（upload zip 在位就自動恢復）---
ensure_key() {
  [ -f "$SSH_KEY" ] && return 0
  if [ -f "$KEY_ZIP" ]; then
    log "[boot] 金鑰缺失，從 upload zip 自動恢復..."
    mkdir -p "$HOME/.ssh" && chmod 700 "$HOME/.ssh"
    ( cd "$HOME/.ssh" && unzip -o "$KEY_ZIP" >/dev/null 2>&1 ) || return 1
    # zip 內檔名可能係 zcode_test_key，統一歸位
    [ -f "$SSH_KEY" ] || mv -f "$HOME/.ssh/zcode_test_key" "$SSH_KEY" 2>/dev/null
    chmod 600 "$SSH_KEY" 2>/dev/null
  fi
  [ -f "$SSH_KEY" ]
}

# ③⑤ config 只喺「現值≠目標值」先寫——穩態 inspect 連 .git/config 都零寫入
gcfg() {
  local cur; cur="$(git -C "$REPO" config --get "$1" 2>/dev/null || true)"
  [ "$cur" = "$2" ] || git -C "$REPO" config "$1" "$2" >/dev/null 2>&1
}
setup_git() {
  gcfg user.name  "ZCODE"
  gcfg user.email "zcode@tsa-exchange.local"
  gcfg core.autocrlf false
  gcfg core.quotePath false   # ⑤ 中文路徑掃描根治（ls-files -z 之外嘅雙保險）
  gcfg core.fileMode false    # ⑥ mode 噪音根治（值唔同先寫，穩態零寫入）
  local sshbin; sshbin="$(ensure_ssh)" || return 1
  if ensure_key; then
    export GIT_SSH_COMMAND="$sshbin -i $SSH_KEY -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new -o ConnectTimeout=10"
    return 0
  fi
  return 2   # ssh 有、key 無
}

ensure_repo() {
  [ -d "$REPO/.git" ] && return 0
  log "[boot] repo 唔存在，②稀疏重建中（淨拉 exchange/ 子樹）..."
  local t0 t1 err url mode
  t0="$(date +%s)"
  # ---- ② 稀疏 clone：部分 clone＋cone 模式淨 checkout exchange/（快、滿帶寬）----
  for mode in SSH HTTPS; do
    if [ "$mode" = "SSH" ]; then
      setup_git >/dev/null 2>&1 || { dline "SSH 憑證唔齊，跳過 SSH 稀疏路"; continue; }
      url="$REMOTE_SSH"
    else
      url="$REMOTE_HTTPS"
    fi
    err="$(git clone --depth 1 --filter=blob:none --no-checkout "$url" "$REPO" 2>&1)" || {
      dline "稀疏 clone 失敗（$mode）: $(printf '%s\n' "$err" | head -2)"
      rm -rf "$REPO" 2>/dev/null
      continue
    }
    if git -C "$REPO" sparse-checkout init --cone >/dev/null 2>&1 \
       && git -C "$REPO" sparse-checkout set exchange >/dev/null 2>&1 \
       && git -C "$REPO" checkout "$BRANCH" >/dev/null 2>&1; then
      t1=$(( $(date +%s) - t0 ))
      log "[boot] ②稀疏 clone 完成（$mode，淨 exchange/ 子樹，耗時 ${t1}s）: $(git -C "$REPO" log -1 --format='%h %s' 2>/dev/null)"
      git -C "$REPO" config core.quotePath false >/dev/null 2>&1   # ⑤ 新 clone 即設
      git -C "$REPO" config core.fileMode false >/dev/null 2>&1    # ⑥ 新 clone 即設
      return 0
    fi
    dline "sparse-checkout 設定失敗（$mode），轉 fallback"
    rm -rf "$REPO" 2>/dev/null
  done
  # ---- fallback：完整 clone（稀疏路全唔過先行；舊 git 無 partial-clone 能力時用）----
  log "[boot] 稀疏路唔過，fallback 完整 clone..."
  for mode in SSH HTTPS; do
    if [ "$mode" = "SSH" ]; then
      setup_git >/dev/null 2>&1 || continue
      url="$REMOTE_SSH"
    else
      url="$REMOTE_HTTPS"
    fi
    err="$(git clone --depth 1 "$url" "$REPO" 2>&1)" && {
      log "[boot] 完整 clone 完成（$mode，耗時 $(( $(date +%s) - t0 ))s）"
      git -C "$REPO" config core.quotePath false >/dev/null 2>&1
      git -C "$REPO" config core.fileMode false >/dev/null 2>&1    # ⑥ 新 clone 即設
      return 0
    }
    dline "完整 clone 失敗（$mode）: $(printf '%s\n' "$err" | head -2)"
    rm -rf "$REPO" 2>/dev/null
  done
  diag_dump ""   # ① 全路失敗：df -h 落 stderr
  return 1
}

dirty_files() { git -C "$REPO" status --porcelain | head -20; }

fetch_latest() {
  local ok=0 via="" err
  err="$(git -C "$REPO" fetch origin "$BRANCH" 2>&1)" && { ok=1; via="SSH(origin)"; }
  if [ "$ok" -eq 0 ]; then
    err="$(git -C "$REPO" fetch "$REMOTE_HTTPS" "$BRANCH" 2>&1)" && { ok=1; via="HTTPS(唯讀fallback)"; }
  fi
  if [ "$ok" -eq 0 ]; then
    log "[pull][ERROR] fetch 失敗（SSH 同 HTTPS 都唔通）"
    diag_dump "$err"   # ① df -h＋stderr 原文節錄
    return 1
  fi
  if git -C "$REPO" merge --ff-only FETCH_HEAD >/dev/null 2>&1; then
    log "[pull] 已更新（via $via）: $(git -C "$REPO" log -1 --format='%h %s')"
  else
    # 分叉自癒：本地有未 push 嘅自己 commit（如待 key 回信）＋遠端定時數據 commit——
    # 只 rebase 本地未 push commit（FETCH_HEAD..HEAD），唔掂遠端歷史，push 仍係 fast-forward，符合「唔 force push」
    if git -C "$REPO" rebase FETCH_HEAD >/dev/null 2>&1; then
      log "[pull] 分叉自癒：本地 commit 已 rebase 跟上遠端（via $via）: $(git -C "$REPO" log -1 --format='%h %s')"
    else
      git -C "$REPO" rebase --abort >/dev/null 2>&1
      log "[pull][ERROR] ff-only merge 失敗＋rebase 自癒失敗——本地有衝突分叉。按協議唔會 force，請人手處理。"
      return 1
    fi
  fi
  return 0
}

# ⑦ 判定信件是否已處理：頭部窗口內認 by ZCODE* 章，且章日期 ≥ 信件日期
#   三重條件缺一不可——引述舊章（日期早於信）／他方自章（非 ZCODE）／深位章（窗外）都唔算
is_processed() {
  local f="$1" line sdate ldate fm_end win_end
  # frontmatter 結束行（第二個 ---；無 frontmatter 則 0）
  fm_end=$(awk 'NR==1{ if($0!="---"){print 0; exit} next } $0=="---"{print NR; exit} NR>20{print 0; exit}' "$f" 2>/dev/null)
  [ -z "$fm_end" ] && fm_end=0
  if [ "$fm_end" -gt 0 ]; then win_end=$((fm_end + STAMP_WIN)); else win_end=$STAMP_WIN; fi
  # 信件日期（frontmatter 內 日期: 欄，去 HKT 尾）
  ldate=$(awk -v e="$fm_end" 'NR<=e && /^日期:/{sub(/^日期:[[:space:]]*/,""); sub(/[[:space:]]*HKT.*$/,""); print; exit}' "$f" 2>/dev/null)
  while IFS= read -r line; do
    printf '%s\n' "$line" | grep -qE "$STAMP_RE" || continue
    sdate=$(printf '%s\n' "$line" | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}[[:space:]]+[0-9]{2}:[0-9]{2}' | head -n1)
    # 章無日期（如協議原文引述）→ 唔算章
    [ -z "$sdate" ] && continue
    # 信日期唔可解析（缺／格式損）→ 照舊認章（防歷史信翻案）；無章新信唔受影響
    case "$ldate" in
      [0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]\ [0-9][0-9]:[0-9][0-9]) ;;
      *) return 0 ;;
    esac
    # ISO 格式零補齊，字典序即時間序
    [ "$sdate" = "$ldate" ] && return 0
    [ "$sdate" \> "$ldate" ] && return 0
  done < <(head -n "$win_end" "$f" 2>/dev/null)
  return 1
}

scan_unprocessed() {
  # 只掃信件入口：頂層 loose .md ＋ 一級資料夾內 manifest.md；附件唔係信
  # 注意：bash case 嘅 * 會跨越 /，所以要用斜線計數精確判層級
  local f rel slashes
  # ⑤ ls-files -z：路徑以 NUL 分隔零轉義——中文／特殊字元目錄名唔會被 quotePath
  #   轉成八進制引號串，case 匹配唔再靜默漏掃（config false 之外嘅根治）
  git -C "$REPO" ls-files -z "$SCAN_DIR" | while IFS= read -r -d '' f; do
    case "$f" in
      *.md) ;;
      *) continue ;;
    esac
    rel="${f#"$SCAN_DIR"/}"
    slashes="${rel//[^\/]/}"
    case "${#slashes}" in
      0) ;;                 # from_openclaw/xxx.md → loose mail
      1) case "$rel" in
           */manifest.md) ;;        # from_openclaw/郵件夾/manifest.md → folder mail
           *) continue ;;           # 一級資料夾內其他 .md → 附件
         esac ;;
      *) continue ;;        # 更深層 → 嵌套附件
    esac
    if ! is_processed "$REPO/$f"; then      # ⑦ 三重判定取代全檔 grep
      echo "$f"
    fi
  done
}

inspect() {
  # ---- 冪等 bootstrap：環境自檢，缺嘢先自癒，救唔到就報警 exit 0 ----
  if ! ensure_repo; then
    alarm "⚠️⚠️ exchange-repo clone 失敗（key/clone 缺失，需重交附件）——本鐘巡檢跳過。〔排程 agent 請將此行原文轉達老闆〕"
    echo "$(hkt_now) 巡查失敗已報警（clone 缺失），HEAD=未知"
    exit 0
  fi
  if ! setup_git; then
    alarm "⚠️⚠️ 部署金鑰缺失（$SSH_KEY）——push 冇憑證。〔排程 agent 請將此行原文轉達老闆：舊 zip 內 key 已作廢，重傳無用；請 OpenClaw 照 rotate #2 信（from_zcode/20261028_0136）加新 deploy key〕"
  fi

  local dirty; dirty="$(dirty_files)"
  [ -n "$dirty" ] && { log "[warn] 工作區唔乾淨:"; echo "$dirty" | sed 's/^/    /'; }

  # ③ 真・唯讀自檢：巡查唔准有工作區 side-effect（前後 git status 對比）
  local st_before st_after
  st_before="$(git -C "$REPO" status --porcelain 2>/dev/null)"

  if ! fetch_latest; then
    alarm "⚠️⚠️ git fetch/merge 失敗——〔排程 agent 請將此行原文轉達老闆〕；下鐘自動重試"
    echo "$(hkt_now) 巡查失敗已報警（fetch），HEAD=$(git -C "$REPO" rev-parse --short HEAD 2>/dev/null || echo 未知)"
    exit 0
  fi

  # ---- 掃描匯報 ----
  local head_short head_sub unprocessed n=0
  head_short="$(git -C "$REPO" rev-parse --short HEAD)"
  head_sub="$(git -C "$REPO" log -1 --format='%s')"
  unprocessed="$(scan_unprocessed)"
  [ -n "$unprocessed" ] && n="$(printf '%s\n' "$unprocessed" | wc -l | tr -d ' ')"

  st_after="$(git -C "$REPO" status --porcelain 2>/dev/null)"
  [ "$st_before" != "$st_after" ] && dline "③⚠ inspect 期間工作區出現變化（應零寫入）: ${st_after:0:200}"

  echo "=================================================="
  echo "磁碟: $(disk_line)"   # ① df -h 節錄（/ 及 repo 掛載點）
  if [ "$n" -eq 0 ]; then
    echo "$(hkt_now) 巡查完成，無新信，HEAD=$head_short"
    echo "=================================================="
    exit 0
  fi
  echo "有新信 $n 封，HEAD=$head_short（$(hkt_now) HKT）:"
  printf '%s\n' "$unprocessed" | nl -w2 -s' '
  echo "--------------------------------------------------"
  echo "目前 HEAD 訊息: $head_sub"
  echo "=================================================="
  exit 10
}

push_changes() {
  local msg="$1"; shift
  if ! ensure_repo; then
    alarm "⚠️⚠️ push 前 bootstrap clone 失敗——commit 未執行。〔排程 agent 請原文轉達老闆〕"
    exit 1
  fi
  # ---- ④ origin URL 自修復：https 而 key 在位→自動 set-url SSH 先至推；
  #      無 key→唔好再誤報「憑證/遠端分叉」，如實報「無 key」留本地 ----
  local cur_url no_key=0
  cur_url="$(git -C "$REPO" remote get-url origin 2>/dev/null || echo "?")"
  if [ "$cur_url" != "$REMOTE_SSH" ]; then
    if ensure_key; then
      git -C "$REPO" remote set-url origin "$REMOTE_SSH" 2>/dev/null \
        && log "[push] ④origin URL 自修復: $cur_url → SSH（key 在位）"
    else
      no_key=1
    fi
  fi
  setup_git || no_key=1
  [ "$no_key" -eq 1 ] && alarm "⚠️⚠️ push：部署金鑰唔在位（無 key）——commit 照做留本地，唔會推；唔再誤報憑證/分叉。請恢復 ~/.ssh/zcode_exchange_key 或 upload zip 後下鐘自動續推。〔排程 agent 請原文轉達老闆〕"

  [ "$#" -eq 0 ] && { log "[push][ERROR] push 子命令要至少一個檔案路徑"; exit 1; }
  case "$msg" in *$'\n'*) log "[push][ERROR] commit 訊息唔可以有換行"; exit 1 ;; esac

  local p real
  for p in "$@"; do
    real="$REPO/$p"
    case "$real" in "$REPO"/*) ;; *) log "[push][ERROR] 路徑唔喺 repo 內: $p"; exit 1 ;; esac
    [ -e "$real" ] || { log "[push][ERROR] 檔案唔存在: $p"; exit 1; }
    echo "$p" | grep -qE "$FORBIDDEN_RE" && {
      log "[push][ERROR] 可疑/禁路徑，拒絕 add（協議規則 6）: $p"; exit 1; }
  done

  local dirty; dirty="$(dirty_files)"
  [ -n "$dirty" ] && { log "[push][warn] 工作區有其他未提交變更（只精準 add 指定檔）:"; echo "$dirty" | sed 's/^/    /'; }

  git -C "$REPO" add -- "$@" || { log "[push][ERROR] git add 失敗"; exit 1; }
  local staged; staged="$(git -C "$REPO" diff --cached --name-only)"
  [ -z "$staged" ] && { log "[push][ERROR] 冇嘢 staged（檔案冇變更？）"; exit 1; }
  log "[push] staged:"; echo "$staged" | sed 's/^/    /'

  case "$msg" in exchange:*) ;; *) msg="exchange: $msg" ;; esac
  git -C "$REPO" commit -m "$msg" >/dev/null || { log "[push][ERROR] commit 失敗"; exit 1; }
  log "[push] commit 完成: $(git -C "$REPO" log -1 --format='%h %s')"

  # v3.2 push 前同步：遠端可能有新 commit（OpenClaw watcher :19／CCY :00）時自動
  # 合併，唔再因非 ff 被拒。rebase 失敗→abort 還原→警報，commit 留本地，永不 force。
  if [ "$no_key" -eq 1 ]; then
    log "[push] 無 key——跳過 rebase/push，commit 已留喺本地 main（④如實報告）"
    exit 1
  fi
  if git -C "$REPO" fetch origin "$BRANCH" >/dev/null 2>&1; then
    if ! git -C "$REPO" rebase "origin/$BRANCH" >/dev/null 2>&1; then
      git -C "$REPO" rebase --abort >/dev/null 2>&1
      alarm "⚠️⚠️ push 前 rebase 失敗（遠端分叉自動合併唔過／工作區唔乾淨）——commit 已留喺本地，唔會 force。〔排程 agent 請原文轉達老闆〕"
      exit 1
    fi
  fi

  local perr
  perr="$(git -C "$REPO" push origin "HEAD:$BRANCH" 2>&1)" && {
    log "[push] push origin $BRANCH 成功 ✅"
  } || {
    log "[push][ERROR] push origin $BRANCH 失敗"
    diag_dump "$perr"   # ① df -h＋push stderr 原文節錄（憑證/分叉/網絡一眼可辨）
    alarm "⚠️⚠️ push 失敗（詳見 stderr 診斷段原文節錄）——commit 已留喺本地 main，唔會 force。〔排程 agent 請原文轉達老闆〕"
    exit 1
  }
}

usage() { sed -n '2,40p' "$0" | sed 's/^# \{0,1\}//'; exit 2; }

case "${1:-}" in
  ""|inspect) inspect ;;
  push) shift; [ $# -ge 1 ] || usage; msg="$1"; shift; push_changes "$msg" "$@" ;;
  -h|--help|help) usage ;;
  *) log "[ERROR] 未知子命令: $1"; usage ;;
esac
