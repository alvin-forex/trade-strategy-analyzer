#!/usr/bin/env node
/**
 * encrypt_pages_deterministic.mjs — StatiCrypt deterministic wrapper（任務G，路線C）
 *
 * 目標：同明文 + 同密碼 + 同 salt → 輸出 byte-identical。
 * StatiCrypt CLI 用 crypto.getRandomValues 生成 IV（lib/cryptoEngine.js L70，無入口注入），
 * 令同一頁面每次重加密密文都唔同 → git diff 洗版。本 wrapper 繞過佢：
 *   iv = SHA-256(明文)[0:16]，其餘管線（hashPassword / AES-CBC / HMAC / template）
 *   與 staticrypt 3.5.4 完全同構 → 前端零改動。
 *
 * 輸出結構（與 codec.encodeWithHashedPassword 相同）：
 *   hex(HMAC-SHA256(hashedPassword, encrypted)[64 chars]) + hex(iv)[32] + hex(cipher)
 *
 * 相容性：輸出可被 lib/codec.js decode() 及前端 staticryptJs（password_template.html）
 * 直接解密 —— decode 驗簽（HMAC）→ cryptoEngine.decrypt（AES-CBC，讀頭 32 hex chars 做 iv）。
 *
 * 用法（接口模擬 CLI）：
 *   node encrypt_pages_deterministic.mjs <input.html> -p <password> -d <outdir>
 *        -s <salt-32hex> [--template <password_template.html>] [--remember <days>]
 *        [--no-verify] [--quiet]
 *   password 亦可由環境變數 TSA_ST_PW 提供；salt 亦可由 TSA_ST_SALT 提供。
 *
 * Salt 規則（比 CLI 嚴格）：必須明確提供（-s 或 TSA_ST_SALT）。
 * CLI 冇 salt 會隨機生成——deterministic wrapper 咁做會自毀，所以直接報錯。
 * salt 唔係秘密（會嵌入輸出頁面 config），固定佢只為 remember-me 穩定＋跨機器一致。
 *
 * 依賴：Node >= 18；零 npm install（只用 node:crypto＋staticrypt 3.5.4 原裝 lib/）。
 */

"use strict";

import { createRequire } from "node:module";
import { createHash, webcrypto } from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const __dirname = path.dirname(fileURLToPath(import.meta.url));

// staticrypt 3.5.4 原裝套件位置（同本 wrapper 同目錄安裝：scripts/staticrypt/）
const ST_ROOT = path.resolve(__dirname);
const cryptoEngine = require(path.join(ST_ROOT, "lib", "cryptoEngine.js"));
const { renderTemplate } = require(path.join(ST_ROOT, "lib", "formater.js"));

const { subtle } = webcrypto;

// ---------------------------------------------------------------------------
// CLI 解析
// ---------------------------------------------------------------------------

function usage(exitCode) {
    console.error(
        "Usage: node encrypt_pages_deterministic.mjs <input.html> -p <password> -d <outdir>\n" +
        "       -s <salt-32hex> [--template <password_template.html>] [--remember <days>]\n" +
        "       [--no-verify] [--quiet]\n" +
        "Env:   TSA_ST_PW (password), TSA_ST_SALT (salt-32hex)"
    );
    process.exit(exitCode);
}

function parseArgs(argv) {
    const args = { _: [], remember: 0, verify: true, quiet: false, template: path.join(ST_ROOT, "lib", "password_template.html") };
    for (let i = 0; i < argv.length; i++) {
        const a = argv[i];
        switch (a) {
            case "-p": case "--password":       args.password = argv[++i]; break;
            case "-d": case "--directory":      args.outDir = argv[++i]; break;
            case "-s": case "--salt":           args.salt = argv[++i]; break;
            case "--template":                  args.template = argv[++i]; break;
            case "--remember": {
                const d = parseInt(argv[++i], 10);
                args.remember = isNaN(d) ? 0 : d;
                break;
            }
            case "--no-verify":                 args.verify = false; break;
            case "-q": case "--quiet":          args.quiet = true; break;
            case "-h": case "--help":           usage(0); break;
            default:
                if (a.startsWith("-")) usage(1);
                args._.push(a);
        }
    }
    return args;
}

function die(msg) {
    console.error("ERROR: " + msg);
    process.exit(1);
}

const args = parseArgs(process.argv.slice(2));
if (args._.length !== 1) usage(1);
const inputPath = args._[0];

const password = args.password ?? process.env.TSA_ST_PW;
const salt = args.salt ?? process.env.TSA_ST_SALT;

if (!password) die("password required (-p or TSA_ST_PW)");
if (!salt) die("salt required (-s or TSA_ST_SALT) — deterministic wrapper refuses to generate a random one");
if (salt.length !== 32 || /[^a-f0-9]/.test(salt))
    die("salt must be a 32-character hex string (same rule as StatiCrypt: [0-9a-f]{32})");
if (!fs.existsSync(inputPath)) die(`input not found: ${inputPath}`);
if (!fs.existsSync(args.template)) die(`template not found: ${args.template}`);

// ---------------------------------------------------------------------------
// 核心加密（deterministic）
// ---------------------------------------------------------------------------

function toHex(bytes) {
    return Buffer.from(bytes).toString("hex");
}

/**
 * 與 cryptoEngine.encrypt() 同構，唯一分別：iv 由明文 SHA-256 派生。
 * AES-CBC（subtle 默認 PKCS#7 padding，與原版一致）。
 */
async function encryptDeterministic(msg, hashedPassword) {
    const iv = createHash("sha256").update(msg, "utf8").digest().subarray(0, 16);

    const key = await subtle.importKey(
        "raw",
        Buffer.from(hashedPassword, "hex"),
        "AES-CBC",
        false,
        ["encrypt"]
    );

    const encrypted = await subtle.encrypt(
        { name: "AES-CBC", iv },
        key,
        new TextEncoder().encode(msg)
    );

    return toHex(iv) + toHex(new Uint8Array(encrypted));
}

// ---------------------------------------------------------------------------
// 主流程
// ---------------------------------------------------------------------------

const msg = fs.readFileSync(inputPath, "utf8");

// 1. 同 CLI 一致：三輪 PBKDF2（1k SHA-1 → 14k → 585k SHA-256，共 600k iterations）
const hashedPassword = await cryptoEngine.hashPassword(password, salt);

// 2. deterministic 加密 + HMAC 簽名（與 codec.encodeWithHashedPassword 同構）
const encrypted = await encryptDeterministic(msg, hashedPassword);
const hmac = await cryptoEngine.signMessage(hashedPassword, encrypted);
const signedMsg = hmac + encrypted;

// 3. 內建自驗：輸出必須被原裝 codec.decode() 解回原文（唔過就唔出貨）
if (args.verify) {
    const codec = require(path.join(ST_ROOT, "lib", "codec.js"));
    const { success, decoded, message } = await codec.init(cryptoEngine).decode(signedMsg, hashedPassword, salt);
    if (!success) die(`self-verify failed: ${message ?? "decode unsuccessful"}`);
    if (decoded !== msg) die("self-verify failed: decoded content differs from input");
}

// 4. template render —— 完全重現 CLI genFile 流程
//    convertCommonJSToBrowserJS：與 cli/helpers.js L206 同構（刪 require 行 + IIFE 包 exports）
function convertCommonJSToBrowserJS(libFile) {
    const moduleText = fs
        .readFileSync(path.join(ST_ROOT, "lib", libFile), "utf8")
        .replace(/^.*\brequire\(.*$\n/gm, "");
    return `
((function(){
  const exports = {};
  ${moduleText}
  return exports;
})())
  `.trim();
}

const templateData = {
    js_staticrypt: renderTemplate(convertCommonJSToBrowserJS("staticryptJs.js"), {
        js_codec: convertCommonJSToBrowserJS("codec.js"),
        js_crypto_engine: convertCommonJSToBrowserJS("cryptoEngine.js"),
    }),
    is_remember_enabled: args.remember > 0,
    staticrypt_config: {
        staticryptEncryptedMsgUniqueVariableName: signedMsg,
        isRememberEnabled: args.remember > 0,
        rememberDurationInDays: args.remember,
        staticryptSaltUniqueVariableName: salt,
    },
};

const rendered = renderTemplate(fs.readFileSync(args.template, "utf8"), templateData);

// 5. 寫出 outdir/<basename>（與 CLI -d 行為一致）
const outDir = path.resolve(args.outDir ?? "encrypted");
const outPath = path.join(outDir, path.basename(inputPath));
fs.mkdirSync(outDir, { recursive: true });
fs.writeFileSync(outPath, rendered);

if (!args.quiet) {
    console.log(`ENC ${inputPath} -> ${outPath}`);
    console.log(`    salt=${salt} iv=sha256(msg)[0:16] signedMsg=${signedMsg.length} hex chars`);
}
