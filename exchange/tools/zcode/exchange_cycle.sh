#!/usr/bin/env bash
# ============================================================================
# exchange_cycle.sh v3 — exchange 信箱巡檢＋精準 push（ZCODE_w 機房 lane）
#   ★ 此腳本正本住喺 repo：exchange/tools/zcode/exchange_cycle.sh（v3 起）
#     scripts/ 下嗰份只係安裝副本；運行時自動 exec repo 正本，永遠用最新版
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
#   repo 缺→clone（SSH 優先，HTTPS 唯讀 fallback）
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
SSH_KEY="$HOME/.ssh/zcode_exchange_key"
KEY_ZIP="/home/z/my-project/upload/zcode_test_key.zip"
SSHBIN_DIR="/home/z/my-project/.sshbin"
SSH_BIN="$SSHBIN_DIR/extract/usr/bin/ssh"
REMOTE_SSH="git@github.com:alvin-forex/trade-strategy-analyzer.git"
REMOTE_HTTPS="https://github.com/alvin-forex/trade-strategy-analyzer.git"
BRANCH="main"
SCAN_DIR="exchange/from_openclaw"
STAMP_RE='^>?[[:space:]]*(✅[[:space:]]*已處理|⏳[[:space:]]*進行中)'   # 全檔掃描＋行首錠點：附件引用唔會誤中，深位章（如 2330_reply 第 34 行）都掃到
WORKLOG="/home/z/my-project/worklog.md"
REPO_SELF="${REPO}/exchange/tools/zcode/exchange_cycle.sh"
SCRIPTS_COPY="/home/z/my-project/scripts/exchange_cycle.sh"

FORBIDDEN_RE='(^|/)(tsa_pw\.txt|\.env([^/]*)?|.*\.pem|id_rsa[^/]*|.*credentials.*|.*password.*|zcode_exchange_key|zcode_test_key(\.zip)?)(/|$)|(^|/)martin_v4(/|$)'

hkt_now()   { TZ=Asia/Hong_Kong date '+%H:%M'; }
hkt_stamp() { TZ=Asia/Hong_Kong date '+%Y-%m-%d %H:%M'; }
log()       { echo "[$(hkt_stamp) HKT] $*"; }

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

setup_git() {
  git -C "$REPO" config user.name  "ZCODE"                    >/dev/null 2>&1
  git -C "$REPO" config user.email "zcode@tsa-exchange.local" >/dev/null 2>&1
  git -C "$REPO" config core.autocrlf false                   >/dev/null 2>&1
  local sshbin; sshbin="$(ensure_ssh)" || return 1
  if ensure_key; then
    export GIT_SSH_COMMAND="$sshbin -i $SSH_KEY -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new -o ConnectTimeout=10"
    return 0
  fi
  return 2   # ssh 有、key 無
}

ensure_repo() {
  [ -d "$REPO/.git" ] && return 0
  log "[boot] repo 唔存在，clone 中..."
  if setup_git && git clone "$REMOTE_SSH" "$REPO" >/dev/null 2>&1; then
    log "[boot] SSH clone 完成"
    return 0
  fi
  if git clone "$REMOTE_HTTPS" "$REPO" >/dev/null 2>&1; then
    log "[boot] HTTPS clone 完成（唯讀 bootstrap）"
    return 0
  fi
  return 1
}

dirty_files() { git -C "$REPO" status --porcelain | head -20; }

fetch_latest() {
  local ok=0 via=""
  if git -C "$REPO" fetch origin "$BRANCH" >/dev/null 2>&1; then
    ok=1; via="SSH(origin)"
  elif git -C "$REPO" fetch "$REMOTE_HTTPS" "$BRANCH" >/dev/null 2>&1; then
    ok=1; via="HTTPS(唯讀fallback)"
  fi
  [ "$ok" -eq 0 ] && { log "[pull][ERROR] fetch 失敗（SSH 同 HTTPS 都唔通）"; return 1; }
  if git -C "$REPO" merge --ff-only FETCH_HEAD >/dev/null 2>&1; then
    log "[pull] 已更新（via $via）: $(git -C "$REPO" log -1 --format='%h %s')"
  else
    log "[pull][ERROR] ff-only merge 失敗——本地有分叉。按協議唔會 force，請人手處理。"
    return 1
  fi
  return 0
}

scan_unprocessed() {
  # 只掃信件入口：頂層 loose .md ＋ 一級資料夾內 manifest.md；附件唔係信
  # 注意：bash case 嘅 * 會跨越 /，所以要用斜線計數精確判層級
  local f rel slashes
  git -C "$REPO" ls-files "$SCAN_DIR" | while read -r f; do
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
    if ! grep -qE "$STAMP_RE" "$REPO/$f" 2>/dev/null; then
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
    alarm "⚠️⚠️ 部署金鑰缺失（~/.ssh/zcode_exchange_key）且 upload zip 唔在位——push 冇憑證。〔排程 agent 請將此行原文轉達老闆，請老闆重傳 key zip〕"
  fi

  local dirty; dirty="$(dirty_files)"
  [ -n "$dirty" ] && { log "[warn] 工作區唔乾淨:"; echo "$dirty" | sed 's/^/    /'; }

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

  echo "=================================================="
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
  setup_git || alarm "⚠️⚠️ 金鑰缺失——commit 留喺本地，push 將失敗。〔排程 agent 請原文轉達老闆〕"

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

  if git -C "$REPO" push origin "HEAD:$BRANCH" >/dev/null 2>&1; then
    log "[push] push origin $BRANCH 成功 ✅"
  else
    alarm "⚠️⚠️ push 失敗（憑證/遠端分叉）——commit 已留喺本地 main，唔會 force。〔排程 agent 請原文轉達老闆〕"
    exit 1
  fi
}

usage() { sed -n '2,32p' "$0" | sed 's/^# \{0,1\}//'; exit 2; }

case "${1:-}" in
  ""|inspect) inspect ;;
  push) shift; [ $# -ge 1 ] || usage; msg="$1"; shift; push_changes "$msg" "$@" ;;
  -h|--help|help) usage ;;
  *) log "[ERROR] 未知子命令: $1"; usage ;;
esac
