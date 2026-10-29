#!/usr/bin/env node
"use strict";

/**
 * decrypt_page.mjs — StatiCrypt 3.5.4 加密頁解密（remember-me 重加密流程用）。
 *
 * 與 encrypt_pages_deterministic.mjs 同構反向：抽 staticryptConfig 內嵌密文＋salt，
 * 三輪 PBKDF2 派 key，原裝 codec.decode() 解回 plaintext。
 * 密碼只由 -p / TSA_ST_PW 傳入，NEVER 寫入任何檔案。
 *
 * Usage:
 *   node scripts/staticrypt/decrypt_page.mjs <encrypted.html> -p <password> -o <out.html>
 *   node scripts/staticrypt/decrypt_page.mjs <encrypted.html> -p <password> --print   # stdout 前幾行驗證
 */
import { createRequire } from "node:module";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ST_ROOT = path.resolve(__dirname);
const cryptoEngine = require(path.join(ST_ROOT, "lib", "cryptoEngine.js"));
const codec = require(path.join(ST_ROOT, "lib", "codec.js"));

function usage(exitCode) {
    console.error("Usage: node decrypt_page.mjs <encrypted.html> -p <password> [-o out.html | --print]");
    process.exit(exitCode);
}

const args = { _: [], out: null, print: false, pw: process.env.TSA_ST_PW ?? null };
const a = process.argv.slice(2);
for (let i = 0; i < a.length; i++) {
    if (a[i] === "-p") args.pw = a[++i];
    else if (a[i] === "-o") args.out = a[++i];
    else if (a[i] === "--print") args.print = true;
    else args._.push(a[i]);
}
if (args._.length !== 1 || !args.pw) usage(1);

const html = fs.readFileSync(args._[0], "utf8");

// 1. 抽 staticryptConfig JSON（鏈式宣告可能冇 const 前綴；hex 串內無 }，lazy 到第一個 } 即 JSON 結尾）
const m = html.match(/staticryptConfig\s*=\s*(\{.*?\})\s*;/);
if (!m) { console.error("ERR: staticryptConfig not found"); process.exit(1); }
let cfg;
try { cfg = JSON.parse(m[1]); } catch (e) { console.error("ERR: config JSON parse: " + e.message); process.exit(1); }
const msg = cfg.staticryptEncryptedMsgUniqueVariableName;
const salt = cfg.staticryptSaltUniqueVariableName;
if (!msg || !salt) { console.error("ERR: msg/salt missing in config"); process.exit(1); }

// 2. 三輪 PBKDF2 派 key（與 wrapper/CLI 同）
const hashedPassword = await cryptoEngine.hashPassword(args.pw, salt);

// 3. 原裝 codec.decode
const { success, decoded, message } = await codec.init(cryptoEngine).decode(msg, hashedPassword, salt);
if (!success) {
    console.error("DECRYPT_FAIL: " + (message ?? "decode unsuccessful"));
    process.exit(2);
}

// 4. 輸出
if (args.out) {
    fs.writeFileSync(args.out, decoded, "utf8");
    console.log("DECRYPT_OK -> " + args.out + " (" + Buffer.byteLength(decoded) + " bytes)");
} else if (args.print) {
    console.log(decoded.split("\n").slice(0, 6).join("\n"));
    console.log("DECRYPT_OK (print, total " + Buffer.byteLength(decoded) + " bytes)");
} else {
    console.log("DECRYPT_OK (" + Buffer.byteLength(decoded) + " bytes) — 用 -o 或 --print 睇內容");
}
