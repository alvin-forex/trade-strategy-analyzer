#!/usr/bin/env python3
"""
CSV Parser - 讀取並解析交易數據 CSV 檔案
"""

import pandas as pd
from typing import Dict, Any
from datetime import datetime


def parse_csv(csv_path: str) -> pd.DataFrame:
    """
    讀取交易 CSV 檔案，自動識別欄位並處理日期格式

    Args:
        csv_path: CSV 檔案路徑

    Returns:
        pd.DataFrame: 解析後的交易數據
    """
    # 讀取 CSV
    df = pd.read_csv(csv_path)

    # 處理日期格式（DD/MM/YYYY HH:MM:SS）
    date_columns = ['Open Time', 'Close Time']
    for col in date_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], format='%d/%m/%Y %H:%M:%S', errors='coerce')

    # 確保數值欄位是正確類型
    numeric_columns = [
        'Lots', 'Open Price', 'Close Price', 'Commission', 'Swap',
        'Net Pips', 'Net Profit', 'Max Profit', 'Max Pips',
        'Max Loss', 'Max Loss Pips', 'Magic Number', 'Holding Time (Hours)'
    ]
    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # 標準化欄位名稱（移除空格，統一大小寫）
    df.columns = df.columns.str.strip()

    # 過濾非交易記錄（balance transfer、deposit 等）
    if 'Comment' in df.columns:
        non_trade = df['Comment'].str.contains('Transfer|Deposit|Withdraw|Balance', case=False, na=False)
        removed = non_trade.sum()
        if removed > 0:
            print(f'   ⚠️ 過濾 {removed} 筆非交易記錄（Transfer/Deposit 等）')
            df = df[~non_trade].copy()

    # 過濾零手數
    if 'Lots' in df.columns:
        zero_lots = df['Lots'] <= 0
        removed_zero = zero_lots.sum()
        if removed_zero > 0:
            print(f'   ⚠️ 過濾 {removed_zero} 筆零手數記錄')
            df = df[~zero_lots].copy()

    # 過濾無 Symbol 嘅記錄
    if 'Symbol' in df.columns:
        no_symbol = df['Symbol'].isna() | (df['Symbol'] == '')
        removed_sym = no_symbol.sum()
        if removed_sym > 0:
            print(f'   ⚠️ 過濾 {removed_sym} 筆無 Symbol 記錄')
            df = df[~no_symbol].copy()

    df = df.reset_index(drop=True)

    return df


def validate_csv(df: pd.DataFrame) -> Dict[str, Any]:
    """
    驗證 CSV 數據完整性

    Args:
        df: 解析後的 DataFrame

    Returns:
        Dict: 驗證結果，包含是否有錯誤及相關信息
    """
    result = {
        'valid': True,
        'errors': [],
        'warnings': [],
        'info': {}
    }

    # 檢查必要欄位
    required_columns = [
        'Open Time', 'Type', 'Lots', 'Symbol', 'Open Price',
        'Close Time', 'Close Price', 'Net Profit', 'Max Pips', 'Max Loss Pips'
    ]
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        result['valid'] = False
        result['errors'].append(f"缺少必要欄位: {', '.join(missing_columns)}")

    # 檢查日期格式
    if 'Open Time' in df.columns:
        null_dates = df['Open Time'].isna().sum()
        if null_dates > 0:
            result['warnings'].append(f"有 {null_dates} 筆記錄的日期格式無法解析")

    # 檢查負手數
    if 'Lots' in df.columns:
        negative_lots = (df['Lots'] < 0).sum()
        if negative_lots > 0:
            result['warnings'].append(f"有 {negative_lots} 筆記錄的手數為負數")

    # 統計信息
    result['info']['total_trades'] = len(df)
    result['info']['symbols'] = df['Symbol'].unique().tolist() if 'Symbol' in df.columns else []
    result['info']['date_range'] = {
        'from': df['Open Time'].min().strftime('%Y-%m-%d %H:%M:%S') if 'Open Time' in df.columns else None,
        'to': df['Open Time'].max().strftime('%Y-%m-%d %H:%M:%S') if 'Open Time' in df.columns else None
    }

    return result
