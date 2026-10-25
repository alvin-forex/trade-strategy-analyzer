#!/bin/bash
# 任務G wrapper 驗證套組 — determinism／雪崩／跨目錄／前端路徑模擬
set -u
W=/home/z/my-project/scripts/staticrypt_3.5.4/encrypt_pages_deterministic.mjs
SRC=/home/z/my-project/scripts/_st_test.html
SALT=2f5a7c9e1b3d4f6a8c0e2b4d6f8a1c3e
PW="TestPass123"
OUT=/home/z/my-project/scripts/_st_test_workspace
rm -rf "$OUT"; mkdir -p "$OUT/a" "$OUT/b"

echo "=== T1 determinism：同輸入兩次加密必須 byte-identical ==="
node "$W" "$SRC" -p "$PW" -d "$OUT/a" -s $SALT -q
node "$W" "$SRC" -p "$PW" -d "$OUT/b" -s $SALT -q
if cmp -s "$OUT/a/_st_test.html" "$OUT/b/_st_test.html"; then
    echo "T1 PASS — byte-identical ($(wc -c < "$OUT/a/_st_test.html") bytes)"
else
    echo "T1 FAIL — outputs differ!"; diff <(xxd "$OUT/a/_st_test.html") <(xxd "$OUT/b/_st_test.html") | head -5
fi

echo ""
echo "=== T2 雪崩：內容改 1 byte → 密文必須全變 ==="
sed 's/hello deterministic world/hello deterministic worle/' "$SRC" > "$OUT/input_b.html"
node "$W" "$OUT/input_b.html" -p "$PW" -d "$OUT/a2" -s $SALT -q >/dev/null
A=$(sed -n 's/.*"staticryptEncryptedMsgUniqueVariableName":"\([a-f0-9]*\)".*/\1/p' "$OUT/a/_st_test.html")
B=$(sed -n 's/.*"staticryptEncryptedMsgUniqueVariableName":"\([a-f0-9]*\)".*/\1/p' "$OUT/a2/input_b.html")
same=$(python3 -c "
a,b='$A','$B'
print(sum(1 for x,y in zip(a,b) if x==y), '/', len(a))
")
echo "hex 對位相同率：$same（應該 ~25%，即 IV+CBC 雪崩）"

echo ""
echo "=== T3 跨目錄/跨工作目錄 determinism：唔同 cwd 跑同一檔 ==="
mkdir -p "$OUT/cwd1" "$OUT/cwd2"
(cd "$OUT/cwd1" && node "$W" "$SRC" -p "$PW" -d . -s $SALT -q)
(cd "$OUT/cwd2" && node "$W" "$SRC" -p "$PW" -d . -s $SALT -q)
if cmp -s "$OUT/cwd1/_st_test.html" "$OUT/cwd2/_st_test.html" && cmp -s "$OUT/cwd1/_st_test.html" "$OUT/a/_st_test.html"; then
    echo "T3 PASS — cwd 無關，三處 byte-identical"
else
    echo "T3 FAIL"
fi

echo ""
echo "=== T4 前端路徑模擬：從輸出頁面 extract config，原裝 codec.decode 解密 ==="
node --input-type=module -e "
import { createRequire } from 'node:module';
const require = createRequire('/home/z/my-project/scripts/staticrypt_3.5.4/');
const fs = require('fs');
const ce = require('/home/z/my-project/scripts/staticrypt_3.5.4/lib/cryptoEngine.js');
const codec = require('/home/z/my-project/scripts/staticrypt_3.5.4/lib/codec.js');
const html = fs.readFileSync('$OUT/a/_st_test.html', 'utf8');
const cfgMatch = html.match(/staticryptConfig = (\{.*?\});\n/s);
if (!cfgMatch) { console.log('T4 FAIL — config not found in page'); process.exit(1); }
const cfg = JSON.parse(cfgMatch[1]);
const msg = cfg.staticryptEncryptedMsgUniqueVariableName;
const salt = cfg.staticryptSaltUniqueVariableName;
const hashed = await ce.hashPassword('TestPass123', salt);
const r = await codec.init(ce).decode(msg, hashed, salt);
if (r.success && r.decoded === fs.readFileSync('$SRC', 'utf8')) {
    console.log('T4 PASS — 前端同路徑 decode 成功，內容 byte-identical');
} else {
    console.log('T4 FAIL —', r.success ? 'content mismatch' : r.message);
    process.exit(1);
}
"

echo ""
echo "=== T5 錯密碼：decode 必須拒絕（唔會誤解） ==="
node --input-type=module -e "
import { createRequire } from 'node:module';
const require = createRequire('/home/z/my-project/scripts/staticrypt_3.5.4/');
const fs = require('fs');
const ce = require('/home/z/my-project/scripts/staticrypt_3.5.4/lib/cryptoEngine.js');
const codec = require('/home/z/my-project/scripts/staticrypt_3.5.4/lib/codec.js');
const html = fs.readFileSync('$OUT/a/_st_test.html', 'utf8');
const cfg = JSON.parse(html.match(/staticryptConfig = (\{.*?\});\n/s)[1]);
const hashed = await ce.hashPassword('WrongPass', cfg.staticryptSaltUniqueVariableName);
const r = await codec.init(ce).decode(cfg.staticryptEncryptedMsgUniqueVariableName, hashed, cfg.staticryptSaltUniqueVariableName);
console.log(r.success ? 'T5 FAIL — 錯密碼竟然解到?!' : 'T5 PASS — 錯密碼被 HMAC 拒絕:', r.success ? '' : r.message);
"

echo ""
echo "=== T6 鹽變化：同內容唔同 salt → 密文必須唔同（唔可以有隱藏常數） ==="
node "$W" "$SRC" -p "$PW" -d "$OUT/d" -s aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa1 -q
S=$(sed -n 's/.*"staticryptEncryptedMsgUniqueVariableName":"\([a-f0-9]*\)".*/\1/p' "$OUT/d/_st_test.html")
if [ "$A" != "$S" ]; then echo "T6 PASS — salt 參與管線，輸出不同"; else echo "T6 FAIL — salt 冇生效?!"; fi
