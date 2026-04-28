#!/usr/bin/env python3
"""
Position Builder - 倉位重構
將 CSV 中的獨立交易組合成倉位
"""

import pandas as pd
from typing import Dict, List, Any
from datetime import timedelta


def build_positions(df: pd.DataFrame, lot_exp: float = 1.8) -> List[Dict[str, Any]]:
    """
    將交易按 Symbol + Direction + Close Time 分組，重構為倉位

    Args:
        df: 解析後的交易 DataFrame
        lot_exp: 馬丁倍率，用於計算層數

    Returns:
        List[Dict]: 倉位列表
    """
    if df.empty:
        return []

    # 計算每筆交易的層數
    df = calculate_layers(df, lot_exp)

    # 按 Symbol + Direction + Close Time 分組（容差 ±60秒）
    df = add_position_key(df)

    # 分組並計算倉位級統計
    positions = []
    for position_key, group in df.groupby('position_key'):
        position = calculate_position_stats(group, position_key)
        positions.append(position)

    # 按平倉時間排序
    positions.sort(key=lambda x: x['close_time'])

    return positions


def calculate_layers(df: pd.DataFrame, lot_exp: float = 1.8) -> pd.DataFrame:
    """
    根據手數計算每筆交易的層數

    Args:
        df: 交易 DataFrame
        lot_exp: 馬丁倍率

    Returns:
        pd.DataFrame: 加入層數的 DataFrame
    """
    df = df.copy()

    # 動態偵測基礎手數（取最小 lots）
    base_lot = df['Lots'].min()
    
    # 動態生成層數映射
    # 按手數排序，每個唯一值對應一層
    unique_lots = sorted(df['Lots'].unique())
    layer_mapping = {round(lot, 4): i + 1 for i, lot in enumerate(unique_lots)}
    
    def get_layer(lots: float) -> int:
        return layer_mapping.get(round(lots, 4), 1)
        # 如果不在預定義範圍內，根據倍率推算
        if lots >= 0.01:
            layer = int(round(lots / 0.02, 0))
            return min(layer, 9)  # 最大到第 9 層
        return 1

    df['layer'] = df['Lots'].apply(get_layer)

    return df


def add_position_key(df: pd.DataFrame) -> pd.DataFrame:
    """
    添加倉位分組鍵（Symbol + Direction + Close Time 容差 ±60秒）

    Args:
        df: 交易 DataFrame

    Returns:
        pd.DataFrame: 加入倉位鍵的 DataFrame
    """
    df = df.copy()

    # 獲取方向（Type 欄位）
    df['direction'] = df['Type'].str.upper()

    # 將 Close Time 四捨五入到分鐘（處理 ±60秒容差）
    df['close_time_rounded'] = df['Close Time'].dt.floor('min')

    # 創建倉位鍵
    df['position_key'] = (
        df['Symbol'].astype(str) + '_' +
        df['direction'] + '_' +
        df['close_time_rounded'].astype(str)
    )

    # 標記部分平倉（同一 Symbol 但 Close Time 差距 > 5 分鐘）
    df['is_partial_close'] = False
    for symbol in df['Symbol'].unique():
        symbol_df = df[df['Symbol'] == symbol].sort_values('Close Time')
        if len(symbol_df) > 1:
            for i in range(len(symbol_df) - 1):
                time_diff = (symbol_df.iloc[i+1]['Close Time'] - symbol_df.iloc[i]['Close Time']).total_seconds()
                if time_diff > 300:  # 5 分鐘
                    df.loc[symbol_df.iloc[i].name, 'is_partial_close'] = True

    return df


def calculate_position_stats(group: pd.DataFrame, position_key: str) -> Dict[str, Any]:
    """
    計算倉位級別統計

    Args:
        group: 同一倉位的所有交易
        position_key: 倉位鍵

    Returns:
        Dict: 倉位統計
    """
    # 解析倉位鍵
    parts = position_key.split('_')
    symbol = parts[0]
    direction = parts[1]
    close_time_str = '_'.join(parts[2:])
    close_time = pd.to_datetime(close_time_str)

    # 基本信息
    total_lots = group['Lots'].sum()
    max_layer = group['layer'].max()
    min_layer = group['layer'].min()

    # 盈虧統計
    net_profit = group['Net Profit'].sum()
    max_profit = group['Max Profit'].sum()
    max_loss = group['Max Loss'].sum()
    max_pips = group['Max Pips'].max()  # 使用最大浮盈
    max_loss_pips = group['Max Loss Pips'].max()  # 使用最大浮虧

    # 手續費和隔夜利息
    total_commission = group['Commission'].sum()
    total_swap = group['Swap'].sum()

    # 時間
    open_time = group['Open Time'].min()
    holding_time_hours = (close_time - open_time).total_seconds() / 3600

    # L1 統計（用於入市質量評分）
    l1_trade = group[group['layer'] == 1].iloc[0] if len(group[group['layer'] == 1]) > 0 else None
    l1_max_pips = l1_trade['Max Pips'] if l1_trade is not None else max_pips
    l1_max_loss_pips = l1_trade['Max Loss Pips'] if l1_trade is not None else max_loss_pips

    # 高層數（L4+）統計
    l4_trades = group[group['layer'] >= 4]

    # 檢查是否部分平倉
    is_partial_close = group['is_partial_close'].any()

    return {
        'position_key': position_key,
        'symbol': symbol,
        'direction': direction,
        'open_time': open_time,
        'close_time': close_time,
        'holding_time_hours': holding_time_hours,
        'total_lots': total_lots,
        'max_layer': max_layer,
        'layer_count': len(group),
        'net_profit': net_profit,
        'max_profit': max_profit,
        'max_loss': max_loss,
        'max_pips': max_pips,
        'max_loss_pips': max_loss_pips,
        'total_commission': total_commission,
        'total_swap': total_swap,
        'l1_max_pips': l1_max_pips,
        'l1_max_loss_pips': l1_max_loss_pips,
        'l4_plus_trades_count': len(l4_trades),
        'is_partial_close': is_partial_close,
        'is_win': net_profit > 0,
        'trades': group.to_dict('records')
    }


def detect_partial_close_candidates(df: pd.DataFrame) -> List[str]:
    """
    檢測可能的部分平倉候選

    Args:
        df: 交易 DataFrame

    Returns:
        List[str]: 部分平倉候選的倉位鍵列表
    """
    candidates = []

    for symbol in df['Symbol'].unique():
        symbol_df = df[df['Symbol'] == symbol].sort_values('Close Time')

        for i in range(len(symbol_df) - 1):
            time_diff = (symbol_df.iloc[i+1]['Close Time'] - symbol_df.iloc[i]['Close Time']).total_seconds()
            if time_diff > 300:  # 5 分鐘
                candidates.append(f"{symbol_df.iloc[i]['Symbol']}_{symbol_df.iloc[i]['Type'].upper()}")

    return candidates
