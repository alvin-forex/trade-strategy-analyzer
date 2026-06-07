/**
 * TSA Database Frontend Integration
 * 使用 sql.js-httpvfs 在浏览器中查询 SQLite 数据库
 * 
 * 功能：
 * - 按需加载数据块，不下载整个数据库
 * - GitHub Pages 完美兼容
 * - 支持信号查询、排名查询等
 */

// TSA Database 配置
const TSA_DB_CONFIG = {
    // 数据库 URL（相对于 docs/ 目录）
    dbUrl: './data/tsa.db',
    // Worker URL
    workerUrl: './js/sqlite.worker.js',
    // WASM URL
    wasmUrl: './js/sql-wasm.wasm',
    // 最大读取字节数 (10MB)
    maxBytesToRead: 10 * 1024 * 1024
};

// 全局 worker 实例
let tsaWorker = null;
let tsaDb = null;

/**
 * 初始化 TSA 数据库连接
 * @returns {Promise<Object>} worker 实例
 */
async function initTsaDb() {
    if (tsaWorker) {
        return tsaWorker;
    }

    try {
        // 动态加载 sql.js-httpvfs
        const { createDbWorker } = await loadSqlJsHttpvfs();
        
        const config = {
            from: "inline",
            config: {
                serverMode: "full",
                requestChunkSize: 4096,
                url: TSA_DB_CONFIG.dbUrl
            }
        };

        tsaWorker = await createDbWorker(
            [config],
            TSA_DB_CONFIG.workerUrl,
            TSA_DB_CONFIG.wasmUrl,
            TSA_DB_CONFIG.maxBytesToRead
        );
        
        tsaDb = tsaWorker.db;
        console.log('[TSA-DB] 数据库初始化成功');
        
        return tsaWorker;
    } catch (error) {
        console.error('[TSA-DB] 初始化失败:', error);
        throw error;
    }
}

/**
 * 动态加载 sql.js-httpvfs 库
 */
async function loadSqlJsHttpvfs() {
    // 尝试从 CDN 加载
    const cdnUrls = [
        'https://cdn.jsdelivr.net/npm/sql.js-httpvfs@0.8.12/dist/sql.js-httpvfs.esm.js',
        'https://unpkg.com/sql.js-httpvfs@0.8.12/dist/sql.js-httpvfs.esm.js'
    ];
    
    for (const url of cdnUrls) {
        try {
            const module = await import(url);
            console.log(`[TSA-DB] 从 CDN 加载成功: ${url}`);
            return module;
        } catch (e) {
            console.warn(`[TSA-DB] CDN 加载失败: ${url}`, e);
        }
    }
    
    throw new Error('无法加载 sql.js-httpvfs 库');
}

/**
 * 执行 SQL 查询
 * @param {string} sql SQL 查询语句
 * @param {Array} params 查询参数
 * @returns {Promise<Array>} 查询结果
 */
async function tsaQuery(sql, params = []) {
    if (!tsaDb) {
        await initTsaDb();
    }
    
    try {
        const result = await tsaDb.exec(sql, params);
        return result;
    } catch (error) {
        console.error('[TSA-DB] 查询失败:', error);
        throw error;
    }
}

/**
 * 获取信号排名列表
 * @param {string} symbol 货币对（可选）
 * @param {number} limit 返回数量
 * @param {string} version 策略版本 (v4/v5)
 * @returns {Promise<Array>} 排名列表
 */
async function getSignalRanking(symbol = null, limit = 20, version = 'v5') {
    let sql = `
        SELECT 
            signal_id,
            symbol,
            dde_score,
            win_rate,
            profit_factor,
            trades,
            total_net_pips,
            max_dd_pips,
            martin_pct,
            red_card,
            ea,
            lv
        FROM dde_scores
        WHERE strategy_version = ?
    `;
    
    const params = [version];
    
    if (symbol) {
        sql += ' AND symbol = ?';
        params.push(symbol);
    }
    
    sql += ' ORDER BY dde_score DESC LIMIT ?';
    params.push(limit);
    
    const result = await tsaQuery(sql, params);
    
    if (result.length === 0) {
        return [];
    }
    
    // 转换为对象数组
    const columns = result[0].columns;
    const rows = result[0].values;
    
    return rows.map(row => {
        const obj = {};
        columns.forEach((col, i) => {
            obj[col] = row[i];
        });
        return obj;
    });
}

/**
 * 获取特定信号的详细信息
 * @param {string} signalId 信号 ID
 * @returns {Promise<Object|null>} 信号详情
 */
async function getSignalDetail(signalId) {
    const sql = `
        SELECT * FROM dde_scores
        WHERE signal_id = ?
        ORDER BY analysis_date DESC
    `;
    
    const result = await tsaQuery(sql, [signalId]);
    
    if (result.length === 0) {
        return null;
    }
    
    const columns = result[0].columns;
    const rows = result[0].values;
    
    return rows.map(row => {
        const obj = {};
        columns.forEach((col, i) => {
            obj[col] = row[i];
        });
        return obj;
    });
}

/**
 * 获取货币对统计
 * @returns {Promise<Array>} 货币对统计
 */
async function getSymbolStats() {
    const sql = `
        SELECT 
            symbol,
            COUNT(*) as signal_count,
            AVG(dde_score) as avg_score,
            MAX(dde_score) as max_score,
            AVG(win_rate) as avg_win_rate,
            AVG(profit_factor) as avg_pf
        FROM dde_scores
        WHERE strategy_version = 'v5'
        GROUP BY symbol
        ORDER BY avg_score DESC
    `;
    
    const result = await tsaQuery(sql);
    
    if (result.length === 0) {
        return [];
    }
    
    const columns = result[0].columns;
    const rows = result[0].values;
    
    return rows.map(row => {
        const obj = {};
        columns.forEach((col, i) => {
            obj[col] = row[i];
        });
        return obj;
    });
}

/**
 * 搜索信号
 * @param {string} keyword 搜索关键词
 * @param {number} limit 返回数量
 * @returns {Promise<Array>} 搜索结果
 */
async function searchSignals(keyword, limit = 20) {
    const sql = `
        SELECT 
            signal_id,
            symbol,
            dde_score,
            win_rate,
            profit_factor,
            trades,
            ea,
            lv
        FROM dde_scores
        WHERE strategy_version = 'v5'
        AND (signal_id LIKE ? OR symbol LIKE ? OR ea LIKE ?)
        ORDER BY dde_score DESC
        LIMIT ?
    `;
    
    const searchPattern = `%${keyword}%`;
    const result = await tsaQuery(sql, [searchPattern, searchPattern, searchPattern, limit]);
    
    if (result.length === 0) {
        return [];
    }
    
    const columns = result[0].columns;
    const rows = result[0].values;
    
    return rows.map(row => {
        const obj = {};
        columns.forEach((col, i) => {
            obj[col] = row[i];
        });
        return obj;
    });
}

/**
 * 获取 Red Card 信号列表
 * @param {number} limit 返回数量
 * @returns {Promise<Array>} Red Card 信号
 */
async function getRedCardSignals(limit = 50) {
    const sql = `
        SELECT 
            signal_id,
            symbol,
            dde_score,
            red_reasons,
            ea,
            lv
        FROM dde_scores
        WHERE red_card = 1
        ORDER BY dde_score DESC
        LIMIT ?
    `;
    
    const result = await tsaQuery(sql, [limit]);
    
    if (result.length === 0) {
        return [];
    }
    
    const columns = result[0].columns;
    const rows = result[0].values;
    
    return rows.map(row => {
        const obj = {};
        columns.forEach((col, i) => {
            obj[col] = row[i];
        });
        return obj;
    });
}

/**
 * 获取批次运行历史
 * @param {number} limit 返回数量
 * @returns {Promise<Array>} 批次历史
 */
async function getBatchHistory(limit = 10) {
    const sql = `
        SELECT * FROM batch_runs
        ORDER BY created_at DESC
        LIMIT ?
    `;
    
    const result = await tsaQuery(sql, [limit]);
    
    if (result.length === 0) {
        return [];
    }
    
    const columns = result[0].columns;
    const rows = result[0].values;
    
    return rows.map(row => {
        const obj = {};
        columns.forEach((col, i) => {
            obj[col] = row[i];
        });
        return obj;
    });
}

/**
 * 获取数据库统计信息
 * @returns {Promise<Object>} 统计信息
 */
async function getDbStats() {
    const sql = `
        SELECT 
            (SELECT COUNT(*) FROM dde_scores) as total_records,
            (SELECT COUNT(DISTINCT signal_id) FROM dde_scores) as unique_signals,
            (SELECT COUNT(DISTINCT symbol) FROM dde_scores) as unique_symbols,
            (SELECT COUNT(*) FROM batch_runs) as total_batches,
            (SELECT MAX(analysis_date) FROM dde_scores) as last_analysis
    `;
    
    const result = await tsaQuery(sql);
    
    if (result.length === 0) {
        return null;
    }
    
    const columns = result[0].columns;
    const row = result[0].values[0];
    
    const stats = {};
    columns.forEach((col, i) => {
        stats[col] = row[i];
    });
    
    return stats;
}

/**
 * 获取已读取的字节数
 * @returns {Promise<number>} 已读字节数
 */
async function getBytesRead() {
    if (!tsaWorker) {
        return 0;
    }
    return await tsaWorker.worker.bytesRead;
}

/**
 * 重置字节计数器
 */
function resetBytesRead() {
    if (tsaWorker) {
        tsaWorker.worker.bytesRead = 0;
    }
}

// 导出函数
window.TsaDb = {
    init: initTsaDb,
    query: tsaQuery,
    getSignalRanking,
    getSignalDetail,
    getSymbolStats,
    searchSignals,
    getRedCardSignals,
    getBatchHistory,
    getDbStats,
    getBytesRead,
    resetBytesRead
};

console.log('[TSA-DB] 模块加载完成，使用 TsaDb.init() 初始化数据库');