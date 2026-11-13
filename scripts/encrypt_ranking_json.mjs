#!/usr/bin/env node
/**
 * encrypt_ranking_json.mjs — 排名雙頁 JSON 加密（開工令任務 ③，方案 A）
 *
 * 目標：data/*.json 明文唔准上 public Pages（repo public + JSON 獨立可 fetch＝密碼被繞過）。
 * 做法：與 encrypt_pages_deterministic.mjs 完全同構——hashPassword 三輪 PBKDF2
 *   （1k SHA-1 → 14k → 585k SHA-256）→ AES-CBC（iv = SHA-256(明文)[0:16]）→
 *   HMAC 簽名，輸出 .json.enc ＝ hex(hmac)[64] + hex(iv)[32] + hex(cipher)。
 *   前端 common.js 讀 localStorage「staticrypt_passphrase_general」（同 staticrypt
 *   remember-me 同源）派 key 解密——頁面解鎖後零二次輸入。
 *
 * deterministic：同明文＋同密碼＋同 salt → byte-identical（05:30 鏈日跑零 git diff 噪音）。
 *
 * 用法（VPS 05:30 鏈 / 手動，repo root 行）：
 *   node scripts/encrypt_ranking_json.mjs
 *     環境：TSA_PW_FILE（一般層密碼檔；同 encrypt_admin_pages.sh 同一制）
 *           TSA_ST_SALT（可選，預設與全站同 salt）
 *   輸入：docs/data/signal_ranking.json + docs/data/ccy_ranking.json（prep_ranking_data.py 產出）
 *   輸出：docs/data/*.json.enc（.enc 入 git；明文 .json 由 .gitignore 排除）
 *
 * 自驗：每個 .enc 用原裝 lib/codec.js decode() 解回原文比對，唔過即 exit 1 唔出貨。
 * 依賴：Node >= 18；零 npm install。
 */
"use strict";

import { createRequire } from "node:module";
import path from "node:path";
import { fileURLToPath } from "node:url";
import fs from "node:fs";

const require = createRequire(import.meta.url);
const __dirname = path.dirname(fileURLToPath(import.meta.url));

const ST_ROOT = path.resolve(__dirname, "staticrypt");
const cryptoEngine = require(path.join(ST_ROOT, "lib", "cryptoEngine.js"));
const codec = require(path.join(ST_ROOT, "lib", "codec.js"));

const REPO = path.resolve(__dirname, "..");
const DATA_DIR = path.join(REPO, "docs", "data");
const FILES = ["signal_ranking.json", "ccy_ranking.json"];

const PW_FILE = process.env.TSA_PW_FILE || "/home/alvin/tsa_pw.txt";
const SALT = process.env.TSA_ST_SALT || "2f5a7c9e1b3d4f6a8c0e2b4d6f8a1c3e"; // 與全站同（非秘密）

function die(msg) { console.error("❌ " + msg); process.exit(1); }

async function encryptDeterministic(msg, hashedPassword) {
    const { createHash, webcrypto } = await import("node:crypto");
    const subtle = webcrypto.subtle;
    const iv = createHash("sha256").update(msg, "utf8").digest().subarray(0, 16);
    const key = await subtle.importKey("raw", Buffer.from(hashedPassword, "hex"), "AES-CBC", false, ["encrypt"]);
    const encrypted = await subtle.encrypt({ name: "AES-CBC", iv }, key, new TextEncoder().encode(msg));
    const toHex = (b) => Buffer.from(b).toString("hex");
    return toHex(iv) + toHex(new Uint8Array(encrypted));
}

async function main() {
    if (!fs.existsSync(PW_FILE)) die(`password file not found: ${PW_FILE}（TSA_PW_FILE）`);
    const password = fs.readFileSync(PW_FILE, "utf8").trim();
    const hashedPassword = await cryptoEngine.hashPassword(password, SALT);
    const dec = await codec.init(cryptoEngine);

    for (const name of FILES) {
        const src = path.join(DATA_DIR, name);
        if (!fs.existsSync(src)) die(`input not found: ${src}（先跑 prep_ranking_data.py）`);
        const msg = fs.readFileSync(src, "utf8");
        const encrypted = await encryptDeterministic(msg, hashedPassword);
        const hmac = await cryptoEngine.signMessage(hashedPassword, encrypted);
        const signed = hmac + encrypted;
        // 自驗：原裝 codec.decode 必須解回原文（唔過唔出貨）
        const { success, decoded, message } = await dec.decode(signed, hashedPassword, SALT);
        if (!success || decoded !== msg) die(`self-verify failed for ${name}: ${message ?? "decode mismatch"}`);
        const out = src + ".enc";
        fs.writeFileSync(out, signed, "utf8");
        console.log(`✅ ${path.relative(REPO, out)}  ${(signed.length / 1024).toFixed(1)}KB（hmac64+iv32+cipher，自驗 PASS）`);
    }
    console.log("明文 .json 已由 .gitignore 排除——只准 commit .enc");
}

main().catch((e) => die(e.stack || String(e)));
