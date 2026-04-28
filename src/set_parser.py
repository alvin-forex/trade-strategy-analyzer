#!/usr/bin/env python3
"""
SET Parser - 讀取並解析策略設定 .set 檔案
"""

from typing import Dict, Any
import os


def parse_set(set_path: str) -> Dict[str, Any]:
    """
    讀取 .set 檔案並解析參數

    Args:
        set_path: .set 檔案路徑

    Returns:
        Dict: 解析後的參數，包含分類
    """
    # 讀取檔案
    with open(set_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # 解析 key=value
    params = {}
    for line in lines:
        line = line.strip()
        # 跳過空行和註釋
        if not line or line.startswith(';') or line.startswith('#'):
            continue
        # 解析 key=value
        if '=' in line:
            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip()
            params[key] = value

    # 分類參數
    categorized = categorize_parameters(params)

    # 加入原始路徑和檔名信息
    categorized['_meta'] = {
        'path': set_path,
        'filename': os.path.basename(set_path),
        'symbol': params.get('EA_SYMBOL', 'Unknown'),
        'period': params.get('EA_PERIOD', 'Unknown')
    }

    return categorized


def categorize_parameters(params: Dict[str, str]) -> Dict[str, Any]:
    """
    將參數按類別分類

    Args:
        params: 原始參數字典

    Returns:
        Dict: 分類後的參數
    """
    categorized = {
        'basic': {},
        'ma': {},
        'filters': {},
        'martingale': {},
        'tp_sl': {},
        'news': {},
        'cooldown': {},
        'other': {}
    }

    # 基本設定
    basic_keywords = ['EA_NAME', 'EA_VERSION', 'EA_SYMBOL', 'EA_PERIOD',
                      'OpenType', 'TradeType', 'Trading_Mode', 'MagicNumberB', 'MagicNumberS',
                      'commentB', 'commentS', 'MaxSpread', 'MaxSlippage']

    # MA / STC / 入市系統
    ma_keywords = ['BasicMaTimeframes', 'BasicMaLine1_Period', 'BasicMaLine2_Period',
                   'BasicMaLine345_Period', 'BasicMaLine6_Period', 'BasicMaMethod', 'BasicMaPrice', 'BasicMaShift',
                   'FollowMADirection', 'CloseByMADirection',
                   'EnterMaTimeframes', 'EnterMaLine_Period', 'EnterMaMethod', 'EnterMaPrice', 'EnterMaShift',
                   'MA_TopReturnTF', 'MA_TopReturnPeriod1', 'MA_TopReturnPeriod2',
                   'MA_TopReturnShift', 'MA_TopReturnStart', 'MA_TopReturnDist',
                   # MKD STC 系統
                   'effStcK', 'effStcD', 'effStcS', 'effStcShift',
                   'effStcH', 'effStcL', 'effStcRetDist',
                   'UseExitStc', 'exiStcK', 'exiStcD', 'exiStcS',
                   'exiStcShift', 'exiStcL', 'exiStcH', 'exiStcRetDist', 'ExiStc_TrailDist',
                   # MKD Power 系統
                   'effPow_holdingMins', 'effPow_TF', 'effPow_period',
                   'effPow_BuyOver', 'effPow_SellOver', 'effPow_High', 'effPow_Low',
                   'dirCtrl_apply', 'AIsrc']

    # 濾鏡系統
    filter_keywords = ['UseAISignal', 'AIsrc',
                       'UseVlt', 'VolatilityApplied', 'VltTf', 'VltPeriod', 'VltFrom', 'VltUntil',
                       'UseRSI', 'effRsi_TF', 'effRsi_period', 'effRsi_price', 'effRsi_shift',
                       'effRsi_high', 'effRsi_low',
                       'UseBB', 'effBB_TF', 'effBB_period', 'effBB_deviation',
                       'effBB_shift', 'effBB_price',
                       'UseCorrelation', 'CorrTf', 'CorrPeriod', 'MaxCorr', 'MinCorr',
                       # MKD MACD
                       'UseMACD', 'effMacd_TF', 'effMacd_Fast', 'effMacd_Slow',
                       'effMacd_Signal', 'effMacd_Dist',
                       # MKD 其他
                       'EnterFreqMode', 'EnterFreqBarMode', 'HftMode',
                       'UseCCY', 'ValStr']

    # 馬丁 / 層數系統
    martin_keywords = ['EntryLot', 'lotExp', 'effPipstep', 'PipstepMode', 'LotsizeMode',
                      'preOrderCount', 'preOrderLot', 'slInLevel', 'TeleportOrder',
                      'teleStart', 'teleDist', 'teleLifetime',
                      'pipstep2', 'pipstep3', 'pipstep4',
                      'pipstep5', 'pipstep6', 'pipstep7', 'pipstep8',
                      'pipstep9', 'pipstep10', 'pipstep11', 'pipstep12',
                      'pipstep13', 'pipstep14', 'pipstep15', 'pipstep16',
                      'lotsize2', 'lotsize3', 'lotsize4', 'lotsize5',
                      'lotsize6', 'lotsize7', 'lotsize8', 'lotsize9',
                      'lotsize10', 'lotsize11', 'lotsize12', 'lotsize13',
                      'lotsize14', 'lotsize15', 'lotsize16',
                      # MKD 層數系統
                      'PipStep1', 'lot1', 'beDist1', 'tpDist1', 'slDist1', 'trailStart1', 'trailDist1',
                      'PipStep2', 'lot2', 'beDist2', 'tpDist2', 'slDist2', 'trailStart2', 'trailDist2',
                      'PipStep3', 'lot3', 'beDist3', 'tpDist3', 'slDist3', 'trailStart3', 'trailDist3',
                      'PipStep4', 'lot4', 'beDist4', 'tpDist4', 'slDist4', 'trailStart4', 'trailDist4',
                      'PipStep5', 'lot5', 'beDist5', 'tpDist5', 'slDist5', 'trailStart5', 'trailDist5',
                      'PipStep', 'lot', 'beDist', 'tp', 'slDist', 'trailStart', 'trailDist',
                      'coreTFS1', 'lotS1', 'beDistS1', 'tpDistS1', 'slDistS1', 'trailStartS1', 'trailDistS1',
                      'coreTFS2', 'lotS2', 'PipStepS2', 'beDistS2', 'tpDistS2', 'slDistS2', 'trailStartS2', 'trailDistS2',
                      'coreTF1', 'coreTF2', 'coreTF3', 'coreTF4', 'coreTF5', 'coreTF']

    # TP/SL / 出場系統
    tp_sl_keywords = ['DollarMode0', 'DollarAmount0', 'DollarStart0', 'DollarTrail0',
                      'DollarBreakStart0', 'DollarBreakEven0', 'DollarLoss0',
                      'DollarMode', 'DollarAmount', 'DollarStart', 'DollarTrail',
                      'DollarBreakStart', 'DollarBreakEven', 'DollarLoss',
                      'DynamicTP', 'DynTP_DollarTrail',
                      # MKD 出場
                      'TradeCloseOnlyOnDD', 'TradeModeResetOnDD',
                      'ExiMACD', 'ExiMacdDiff',
                      'effMacd_trStart', 'effMacd_trDist']

    # 新聞過濾
    news_keywords = ['HighNews', 'HighIndentBefore', 'HighIndentAfter',
                     'NFPNews', 'NFPIndentBefore', 'NFPIndentAfter',
                     'SpeaksNews', 'SpeaksIndentBefore', 'SpeaksIndentAfter',
                     'DrawNewsLines']

    # 冷卻系統
    cooldown_keywords = ['CooldownAfterClose', 'CooldownMA_TF', 'CooldownMA_Period',
                         'CooldownMA_Shift', 'UseCooldownAfterClose', 'CooldownMinute']

    # 分類
    for key, value in params.items():
        if key in basic_keywords:
            categorized['basic'][key] = value
        elif key in ma_keywords:
            categorized['ma'][key] = value
        elif key in filter_keywords:
            categorized['filters'][key] = value
        elif key in martin_keywords:
            categorized['martingale'][key] = value
        elif key in tp_sl_keywords:
            categorized['tp_sl'][key] = value
        elif key in news_keywords:
            categorized['news'][key] = value
        elif key in cooldown_keywords:
            categorized['cooldown'][key] = value
        else:
            categorized['other'][key] = value

    return categorized


def parse_multiple_sets(set_paths: list) -> Dict[str, Dict[str, Any]]:
    """
    解析多個 .set 檔案

    Args:
        set_paths: .set 檔案路徑列表

    Returns:
        Dict: 以貨幣對為鍵的設定字典
    """
    result = {}

    for set_path in set_paths:
        try:
            params = parse_set(set_path)
            symbol = params['_meta']['symbol']
            result[symbol] = params
        except Exception as e:
            print(f"警告: 無法解析 {set_path}: {e}")

    return result
