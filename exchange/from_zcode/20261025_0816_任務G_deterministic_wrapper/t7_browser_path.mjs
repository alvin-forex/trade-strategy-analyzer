/**
 * T7 — 真前端路徑模擬：輸出頁面嘅 <script>（含 IIFE 嵌入嘅 codec/cryptoEngine/staticryptJs）
 * 喺 Node vm 瀏覽器模擬入面實際執行，經 form submit → handleDecryptionOfPage →
 * hashPassword（browser crypto）→ decode（驗 HMAC）→ decrypt（AES-CBC）→ document.write。
 * 任何一環壞咗（require 刪除誤傷、IIFE break、crypto 全域缺失）都會喺呢度爆。
 */
import { webcrypto } from "node:crypto";
import fs from "node:fs";
import vm from "node:vm";

const HTML_PATH = process.argv[2];
const PASSWORD = process.argv[3] ?? "TestPass123";
const ORIG_PATH = process.argv[4];

const html = fs.readFileSync(HTML_PATH, "utf8");

// extract 最後一個 <script>（template 嘅主 JS）
const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)];
if (scripts.length === 0) {
    console.error("T7 FAIL — 冇 <script> 可提取");
    process.exit(1);
}
const mainScript = scripts[scripts.length - 1][1];

// --- 瀏覽器 mock ---
let written = "";
const listeners = {};
const elements = {
    "staticrypt_loading": { classList: { add() {}, remove() {} } },
    "staticrypt_content": { classList: { add() {}, remove() {} } },
    "staticrypt-remember-label": { classList: { add() {}, remove() {} } },
    "staticrypt-password": { value: PASSWORD, type: "password", focus() {}, classList: { add() {}, remove() {} } },
    "staticrypt-remember": { checked: false },
    "staticrypt-form": { addEventListener(ev, fn) { listeners[ev] = fn; } },
};
const sandbox = {
    crypto: webcrypto,              // browser 全域 crypto（IIFE 刪走 require 行之後靠呢個）
    document: {
        getElementById: (id) => elements[id] ?? null,
        querySelector: () => ({ addEventListener() {}, src: "", alt: "", title: "" }),
        write: (s) => { written += s; },
        close() {},
    },
    alert() {},
    console,
    setTimeout,
};
sandbox.window = {
    crypto: webcrypto,
    localStorage: { setItem() {}, getItem() {}, removeItem() {} },
    onload: null,
};
sandbox.window.window = sandbox.window;
sandbox.TextEncoder = TextEncoder;
sandbox.TextDecoder = TextDecoder;
vm.createContext(sandbox);

try {
    vm.runInContext(mainScript, sandbox, { timeout: 30000 });
} catch (e) {
    console.error("T7 FAIL — script 執行爆咗:", e.message);
    process.exit(1);
}

if (!listeners["submit"]) {
    console.error("T7 FAIL — form submit listener 冇註冊到");
    process.exit(1);
}

// 觸發 form submit（真前端密碼入口）
await listeners["submit"]({ preventDefault() {} });

const orig = fs.readFileSync(ORIG_PATH, "utf8");
if (written === orig) {
    console.log(`T7 PASS — 瀏覽器路徑全通：form submit → ${written.length} bytes 明文還原，與原輸入 byte-identical`);
} else {
    console.error(`T7 FAIL — 還原唔一致：written=${written.length} orig=${orig.length}`);
    process.exit(1);
}
