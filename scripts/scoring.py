#!/usr/bin/env python3
"""
BTC Dashboard Scoring System v9 — Continuous Scoring + Trend Factors + Validation-Driven Weights

核心改进（基于验证结果）：
1. 连续评分：S型曲线替代二元判断，每个指标输出 [-1, 1] 连续分
2. 趋势因子：每个指标增加动量/斜率评分
3. 权重重构：基于验证结果的信息增益权重
4. 置信度：数据覆盖率 × 新鲜度 × 一致性
4. 背离检测：价格 vs 资金流/衍生品/链上
"""

import time, math, json
from pathlib import Path
from typing import Dict, Any, Callable, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum


class Signal(Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class Tier(Enum):
    CRITICAL = "critical"      # 核心流动性 - 权重 3.0
    MAJOR = "major"            # 货币政策/资金流 - 权重 2.0
    MINOR = "minor"            # 风险/情绪/供应 - 权重 1.0


@dataclass
class IndicatorScore:
    """单个指标的评分结果"""
    name: str
    value: Any
    signal: Signal
    weight: float
    tier: str
    continuous_score: float      # [-1, 1] 连续评分
    trend_score: float           # [-1, 1] 趋势/动量评分
    combined_score: float        # 综合评分 = 0.7*continuous + 0.3*trend
    interpretation: str
    source: str
    timestamp: int
    confidence: float            # 0-1 置信度


@dataclass
class ScoringResult:
    """评分总结果"""
    total_weight: float
    weighted_score: float        # 加权总分 [-100, 100]
    bullish_ratio: float         # 看多权重占比 0-100
    verdict: str
    verdict_icon: str
    verdict_color: str
    confidence: float            # 系统置信度 0-1
    tier_breakdown: Dict[str, Dict[str, float]]
    indicators: List[IndicatorScore]
    divergence_alerts: List[str]  # 背离预警


# ─── S型连续评分函数 ───
def sigmoid_score(value: float, bull_threshold: float, bear_threshold: float, steepness: float = 1.0) -> float:
    """
    S型连续评分 [-1, 1]
    - value > bull_threshold: 接近 +1
    - value < bear_threshold: 接近 -1
    - 中间平滑过渡
    """
    if value is None:
        return 0.0
    mid = (bull_threshold + bear_threshold) / 2
    # 归一化到 [-1, 1] 范围
    normalized = (value - mid) / max(1e-6, (bull_threshold - bear_threshold) / 2)
    return max(-1.0, min(1.0, math.tanh(steepness * normalized)))


def linear_score(value: float, bull_threshold: float, bear_threshold: float) -> float:
    """线性评分 [-1, 1]"""
    if value is None:
        return 0.0
    if value >= bull_threshold:
        return 1.0
    if value <= bear_threshold:
        return -1.0
    # 线性插值
    span = bull_threshold - bear_threshold
    if span == 0:
        return 0.0
    return (value - bear_threshold) / span * 2 - 1


def inverse_score(value: float, bull_threshold: float, bear_threshold: float) -> float:
    """反向评分：数值越小越看多"""
    return -linear_score(value, bull_threshold, bear_threshold)


# ─── 趋势/动量评分 ───
def calc_trend_score(current: float, previous: Optional[float], lookback_days: int = 30) -> float:
    """
    计算趋势评分 [-1, 1]
    使用线性回归斜率标准化
    """
    if current is None or previous is None:
        return 0.0
    if previous == 0:
        return 0.0
    change_pct = (current - previous) / abs(previous) * 100
    # 标准化：月变化 ±20% 映射到 ±1
    return max(-1.0, min(1.0, change_pct / 20.0))


def calc_momentum_score(values: List[float], window: int = 5) -> float:
    """动量评分：最近窗口的斜率"""
    if len(values) < window:
        return 0.0
    recent = values[-window:]
    if len(recent) < 2:
        return 0.0
    # 简单线性回归斜率
    n = len(recent)
    x = list(range(n))
    x_mean = sum(x) / n
    y_mean = sum(recent) / n
    num = sum((x[i] - x_mean) * (recent[i] - y_mean) for i in range(n))
    den = sum((x[i] - x_mean) ** 2 for i in range(n))
    if den == 0:
        return 0.0
    slope = num / den
    # 标准化：日斜率 1% 映射到 1.0
    return max(-1.0, min(1.0, slope / 0.01))


# ─── 辅助函数 ───
def _calc_etf_avg_change(etf_data: Dict) -> Optional[float]:
    """计算ETF平均涨跌幅"""
    if not etf_data:
        return None
    changes = []
    for v in etf_data.values():
        if isinstance(v, dict) and v.get("change_pct") is not None:
            changes.append(v["change_pct"])
    return sum(changes) / len(changes) if changes else None


def _calc_oi_change(deriv: Dict) -> Optional[float]:
    """计算OI 24h变化百分比（简化版，需历史数据支持）"""
    return None


def _calc_realized_price_ratio(price_usd: float, realized_price: float) -> Optional[float]:
    if price_usd and realized_price and realized_price > 0:
        return price_usd / realized_price
    return None


def _get_nested_history(history: List[Dict], path: str, days: int = 1) -> Optional[float]:
    """从历史记录获取前值"""
    if not history or len(history) < days + 1:
        return None
    try:
        keys = path.split(".")
        prev = history[-days - 1]  # 倒数第 days+1 条
        val = prev
        for k in keys:
            if isinstance(val, dict):
                val = val.get(k)
            else:
                return None
            if val is None:
                return None
        return float(val) if val is not None else None
    except Exception:
        return None


# ─── 指标评分配置：连续评分 + 趋势 + 权重 ───
# 格式：
# {
#   "tier": Tier,
#   "base_weight": float,           # 基础权重
#   "info_gain_weight": float,      # 信息增益调整权重 (验证后校准)
#   "score_fn": Callable,           # 连续评分函数
#   "trend_fn": Callable,           # 趋势评分函数
#   "bull_threshold": float,        # 看多阈值
#   "bear_threshold": float,        # 看空阈值
#   "interpretation_bull": str,
#   "interpretation_bear": str,
#   "interpretation_neutral": str,
#   "source": str,
#   "data_path": str,               # 数据路径
#   "trend_path": str,              # 趋势数据路径
# }

SCORING_CONFIG = {
    # ===== Tier 1: CRITICAL (3.0) - 核心流动性 =====
    "fed_assets_trillions": {
        "tier": Tier.CRITICAL,
        "base_weight": 3.0,
        "info_gain_weight": 2.56,     # IC=-0.0061 (噪声, 降权)
        "score_fn": lambda v: linear_score(v, 7.5, 6.5),
        "trend_fn": lambda c, p: calc_trend_score(c, p),
        "bull_threshold": 7.5,
        "bear_threshold": 6.5,
        "interpretation_bull": "Fed扩表加速 → 美元流动性充裕",
        "interpretation_bear": "Fed缩表加速 → 美元流动性收缩",
        "interpretation_neutral": "Fed资产平稳",
        "source": "FRED WALCL",
        "data_path": "macro.fed_assets_trillions",
        "trend_path": "macro.fed_assets_trillions",
    },
    "m2_yoy_pct": {
        "tier": Tier.CRITICAL,
        "base_weight": 3.0,
        "info_gain_weight": 3.1,     # M2同比预测力次之
        "score_fn": lambda v: sigmoid_score(v, 5.0, 0.0, steepness=1.2),
        "trend_fn": lambda c, p: calc_trend_score(c, p),
        "bull_threshold": 5.0,
        "bear_threshold": 0.0,
        "interpretation_bull": "M2显著扩张 → 广义货币强劲增长",
        "interpretation_bear": "M2收缩 → 信用紧缩风险",
        "interpretation_neutral": "M2温和增长",
        "source": "FRED M2SL",
        "data_path": "macro.m2_yoy_pct",
        "trend_path": "macro.m2_yoy_pct",
    },
    "rrp_billions": {
        "tier": Tier.CRITICAL,
        "base_weight": 3.0,
        "info_gain_weight": 4.20,     # IC=-0.1000 (强, 升权)
        "score_fn": lambda v: inverse_score(v, 50, 500),
        "trend_fn": lambda c, p: calc_trend_score(c, p),
        "bull_threshold": 50,
        "bear_threshold": 500,
        "interpretation_bull": "RRP快速耗尽 → 资金流入风险资产",
        "interpretation_bear": "RRP高位积累 → 资金沉淀隔夜逆回购",
        "interpretation_neutral": "RRP正常区间",
        "source": "FRED RRPONTSYD",
        "data_path": "macro.rrp_billions",
        "trend_path": "macro.rrp_billions",
    },

    # ===== Tier 2: MAJOR (2.0) - 货币政策/资金流 =====
    "dxy": {
        "tier": Tier.MAJOR,
        "base_weight": 2.0,
        "info_gain_weight": 1.76,     # IC=+0.0094 (噪声, 降权)
        "score_fn": lambda v: inverse_score(v, 98, 105),
        "trend_fn": lambda c, p: calc_trend_score(c, p),
        "bull_threshold": 98,
        "bear_threshold": 105,
        "interpretation_bull": "美元指数走弱 → 利好风险资产",
        "interpretation_bear": "美元指数走强 → 金融条件紧缩",
        "interpretation_neutral": "美元指数中性区间",
        "source": "Frankfurter.dev (ICE加权)",
        "data_path": "macro.dxy",
        "trend_path": "macro.dxy",
    },
    "real_yield_10y": {
        "tier": Tier.MAJOR,
        "base_weight": 2.0,
        "info_gain_weight": 2.0,
        "score_fn": lambda v: inverse_score(v, 1.5, 3.0),
        "trend_fn": lambda c, p: calc_trend_score(c, p),
        "bull_threshold": 1.5,
        "bear_threshold": 3.0,
        "interpretation_bull": "实际利率下行 → 金融条件宽松",
        "interpretation_bear": "实际利率上行 → 金融条件紧缩",
        "interpretation_neutral": "实际利率中性",
        "source": "FRED DFII10",
        "data_path": "macro.real_yield_10y",
        "trend_path": "macro.real_yield_10y",
    },
    "cpi_yoy_pct": {
        "tier": Tier.MAJOR,
        "base_weight": 2.0,
        "info_gain_weight": 2.70,     # IC=-0.2888 (强, 最高 IC, 升权)
        "score_fn": lambda v: inverse_score(v, 2.5, 5.0),
        "trend_fn": lambda c, p: calc_trend_score(c, p),
        "bull_threshold": 2.5,
        "bear_threshold": 5.0,
        "interpretation_bull": "通胀回落 → 降息预期升温",
        "interpretation_bear": "通胀粘性 → 维持高利率",
        "interpretation_neutral": "通胀温和可控",
        "source": "FRED CPIAUCSL",
        "data_path": "macro.cpi_yoy_pct",
        "trend_path": "macro.cpi_yoy_pct",
    },
    "fear_greed": {
        "tier": Tier.MAJOR,
        "base_weight": 2.0,
        "info_gain_weight": 3.15,     # IC=+0.0774 (强, 升权)
        # 低F&G=恐惧→逆向买入=看多, 高F&G=贪婪→看空
        # lambda: -linear_score(v, 0, 100) → F&G=0得+1, F&G=100得-1
        "score_fn": lambda v: -linear_score(v, 100, 0),   # F&G越低越看多
        "trend_fn": lambda c, p: calc_trend_score(c, p),
        "bull_threshold": 25,         # 极度恐惧看多
        "bear_threshold": 75,         # 极度贪婪看空
        "interpretation_bull": "极度恐惧 → 逆向买入机会",
        "interpretation_bear": "极度贪婪 → 回调风险上升",
        "interpretation_neutral": "情绪中性",
        "source": "Alternative.me",
        "data_path": "sentiment.current.value",
        "trend_path": "sentiment.current.value",
    },
    "etf_net_flow_pct": {
        "tier": Tier.MAJOR,
        "base_weight": 2.0,
        "info_gain_weight": 2.3,     # ETF流向直接反映机构意图
        "score_fn": lambda v: linear_score(_calc_etf_avg_change(v) if isinstance(v, dict) else v, 0.5, -0.5),
        "trend_fn": lambda c, p: calc_trend_score(_calc_etf_avg_change(c) if isinstance(c, dict) else c, _calc_etf_avg_change(p) if isinstance(p, dict) else p),
        "bull_threshold": 0.5,
        "bear_threshold": -0.5,
        "interpretation_bull": "ETF资金净流入 → 机构持续买入",
        "interpretation_bear": "ETF资金净流出 → 机构减仓",
        "interpretation_neutral": "ETF资金平稳",
        "source": "Finnhub (IBIT/FBTC/GBTC/ARKB/BITB等)",
        "data_path": "macro.etf",
        "trend_path": "macro.etf",
    },

    # ===== Tier 3: MINOR (1.0) - 风险/情绪/供应 =====
    "vix": {
        "tier": Tier.MINOR,
        "base_weight": 1.0,
        "info_gain_weight": 1.50,     # IC=+0.1237 (强, 升权)
        "score_fn": lambda v: inverse_score(v, 18, 25),
        "trend_fn": lambda c, p: calc_trend_score(c, p),
        "bull_threshold": 18,
        "bear_threshold": 25,
        "interpretation_bull": "VIX低位 → 市场自满/平静",
        "interpretation_bear": "VIX高位 → 恐慌/不确定性",
        "interpretation_neutral": "VIX正常波动",
        "source": "Yahoo Finance ^VIX",
        "data_path": "macro.vix.price",
        "trend_path": "macro.vix.price",
    },
    "oil_usd": {
        "tier": Tier.MINOR,
        "base_weight": 1.0,
        "info_gain_weight": 1.20,     # IC=-0.1413 (强, 升权)
        "score_fn": lambda v: inverse_score(v, 80, 100),
        "trend_fn": lambda c, p: calc_trend_score(c, p),
        "bull_threshold": 80,
        "bear_threshold": 100,
        "interpretation_bull": "油价低 → 通胀压力小",
        "interpretation_bear": "油价高 → 成本推动通胀",
        "interpretation_neutral": "油价中性",
        "source": "Yahoo Finance CL=F",
        "data_path": "macro.oil.price",
        "trend_path": "macro.oil.price",
    },
    "hashrate_eh_s": {
        "tier": Tier.MINOR,
        "base_weight": 1.0,
        "info_gain_weight": 1.80,     # IC=-0.0896 (强, 升权)
        "score_fn": lambda v: linear_score(v, 600, 400),
        "trend_fn": lambda c, p: calc_trend_score(c, p),
        "bull_threshold": 600,
        "bear_threshold": 400,
        "interpretation_bull": "算力创新高 → 矿工信心强/网络安全",
        "interpretation_bear": "算力下降 → 矿工抛售/信心动摇",
        "interpretation_neutral": "算力稳定增长",
        "source": "Blockchain.com",
        "data_path": "onchain.hashrate_1w_avg_eh_s",
        "trend_path": "onchain.hashrate_1w_avg_eh_s",
    },
    "btc_dominance_pct": {
        "tier": Tier.MINOR,
        "base_weight": 1.0,
        "info_gain_weight": 1.1,
        "score_fn": lambda v: linear_score(v, 55, 45),
        "trend_fn": lambda c, p: calc_trend_score(c, p),
        "bull_threshold": 55,
        "bear_threshold": 45,
        "interpretation_bull": "BTC主导率升 → 资金避险流入比特币",
        "interpretation_bear": "山寨季 → 资金流出BTC",
        "interpretation_neutral": "主导率稳定",
        "source": "CoinGecko Global",
        "data_path": "market.btc_dominance_pct",
        "trend_path": "market.btc_dominance_pct",
    },
    "roi_30d": {
        "tier": Tier.MINOR,
        "base_weight": 1.0,
        "info_gain_weight": 1.50,     # IC=+0.0943 (强, 升权)
        "score_fn": lambda v: linear_score(v, 0, -15),
        "trend_fn": lambda c, p: calc_trend_score(c, p),
        "bull_threshold": 0,
        "bear_threshold": -15,
        "interpretation_bull": "30天正收益 → 动量向上",
        "interpretation_bear": "30天大幅回撤 → 趋势转弱",
        "interpretation_neutral": "30天横盘整理",
        "source": "CoinMetrics",
        "data_path": "onchain.cm_roi_30d",
        "trend_path": "onchain.cm_roi_30d",
    },
    "usdt_mcap": {
        "tier": Tier.MINOR,
        "base_weight": 1.0,
        "info_gain_weight": 1.1,
        "score_fn": lambda v: linear_score(v, 150e9, 120e9),
        "trend_fn": lambda c, p: calc_trend_score(c, p),
        "bull_threshold": 150e9,
        "bear_threshold": 120e9,
        "interpretation_bull": "USDT扩张 → 链上流动性充裕",
        "interpretation_bear": "USDT收缩 → 稳定币资金外流",
        "interpretation_neutral": "USDT稳定",
        "source": "DeFiLlama/CoinGecko",
        "data_path": "macro.usdt_mcap",
        "trend_path": "macro.usdt_mcap",
    },
    "funding_rate_avg": {
        "tier": Tier.MINOR,
        "base_weight": 1.0,
        "info_gain_weight": 1.0,
        "score_fn": lambda v: linear_score(v, 0.01, -0.01),
        "trend_fn": lambda c, p: calc_trend_score(c, p),
        "bull_threshold": 0.01,
        "bear_threshold": -0.01,
        "interpretation_bull": "资金费率为正 → 多头支付空头，看多情绪",
        "interpretation_bear": "资金费率深度为负 → 空头强势/杠杆过热",
        "interpretation_neutral": "资金费率中性",
        "source": "Binance/Bybit/OKX",
        "data_path": "macro.avg_funding_rate_pct",
        "trend_path": "macro.avg_funding_rate_pct",
    },
    "basis_annualized": {
        "tier": Tier.MINOR,
        "base_weight": 1.0,
        "info_gain_weight": 1.0,
        "score_fn": lambda v: inverse_score(v, 5, 20),
        "trend_fn": lambda c, p: calc_trend_score(c, p),
        "bull_threshold": 5,
        "bear_threshold": 20,
        "interpretation_bull": "基差年化低 → 现货溢价/无杠杆泡沫",
        "interpretation_bear": "基差年化高 → 期货溢价/杠杆过热",
        "interpretation_neutral": "基差正常",
        "source": "Binance/Bybit",
        "data_path": "macro.binance_basis_pct_annual",
        "trend_path": "macro.binance_basis_pct_annual",
    },
    "oi_change_24h": {
        "tier": Tier.MINOR,
        "base_weight": 1.0,
        "info_gain_weight": 0.9,
        "score_fn": lambda v: linear_score(v, 5, -5),
        "trend_fn": lambda c, p: calc_trend_score(c, p),
        "bull_threshold": 5,
        "bear_threshold": -5,
        "interpretation_bull": "OI增加 → 新增仓位/趋势延续",
        "interpretation_bear": "OI大幅减少 → 平仓/趋势结束",
        "interpretation_neutral": "OI稳定",
        "source": "Binance/Bybit/OKX",
        "data_path": "macro.total_oi_usd_bn",
        "trend_path": "macro.total_oi_usd_bn",
    },
    "mvrv": {
        "tier": Tier.MINOR,
        "base_weight": 1.0,
        "info_gain_weight": 1.3,     # MVRV极值预测力强
        "score_fn": lambda v: inverse_score(v, 1.0, 3.5),
        "trend_fn": lambda c, p: calc_trend_score(c, p),
        "bull_threshold": 1.0,
        "bear_threshold": 3.5,
        "interpretation_bull": "MVRV<1 → 未实现亏损/底部区域",
        "interpretation_bear": "MVRV>3.5 → 未实现盈利丰厚/顶部区域",
        "interpretation_neutral": "MVRV正常区间",
        "source": "Glassnode/CoinMetrics",
        "data_path": "onchain.mvrv",
        "trend_path": "onchain.mvrv",
    },
    "nupl": {
        "tier": Tier.MINOR,
        "base_weight": 1.0,
        "info_gain_weight": 1.2,
        "score_fn": lambda v: inverse_score(v, 0.25, 0.75),
        "trend_fn": lambda c, p: calc_trend_score(c, p),
        "bull_threshold": 0.25,
        "bear_threshold": 0.75,
        "interpretation_bull": "NUPL低位 → 持仓者未实现盈亏平衡",
        "interpretation_bear": "NUPL高位 → 获利盘丰厚抛压大",
        "interpretation_neutral": "NUPL中性区间",
        "source": "Glassnode",
        "data_path": "onchain.nupl",
        "trend_path": "onchain.nupl",
    },
    "realized_price_ratio": {
        "tier": Tier.MINOR,
        "base_weight": 1.0,
        "info_gain_weight": 1.32,     # IC=-0.0492 (有效, 升权)
        "score_fn": lambda v: inverse_score(v, 1.0, 2.0),
        "trend_fn": lambda c, p: calc_trend_score(c, p),
        "bull_threshold": 1.0,
        "bear_threshold": 2.0,
        "interpretation_bull": "价格/实现价<1 → 长期持有者亏损/支撑",
        "interpretation_bear": "价格/实现价>2 → 获利回吐压力大",
        "interpretation_neutral": "价格/实现价正常",
        "source": "Glassnode/CoinMetrics",
        "data_path": "onchain.cm_roi_1yr",
        "trend_path": "onchain.cm_roi_1yr",
    },
}


# ─── 辅助函数 ───
def _calc_etf_avg_change(etf_data: Dict) -> Optional[float]:
    """计算ETF平均涨跌幅"""
    if not etf_data:
        return None
    changes = []
    for v in etf_data.values():
        if isinstance(v, dict) and v.get("change_pct") is not None:
            changes.append(v["change_pct"])
    return sum(changes) / len(changes) if changes else None


def _calc_oi_change(deriv: Dict) -> Optional[float]:
    """计算OI 24h变化百分比（简化版，需历史数据支持）"""
    return None


def _calc_realized_price_ratio(price_usd: float, realized_price: float) -> Optional[float]:
    if price_usd and realized_price and realized_price > 0:
        return price_usd / realized_price
    return None


def _get_nested_history(history: List[Dict], path: str, days: int = 1) -> Optional[float]:
    """从历史记录获取前值"""
    if not history or len(history) < days + 1:
        return None
    try:
        keys = path.split(".")
        prev = history[-days - 1]  # 倒数第 days+1 条
        val = prev
        for k in keys:
            if isinstance(val, dict):
                val = val.get(k)
            else:
                return None
            if val is None:
                return None
        return float(val) if val is not None else None
    except Exception:
        return None


def _get_nested(data: Dict, path: str) -> Any:
    """按点号路径获取嵌套值，并尝试转换为 float"""
    keys = path.split(".")
    val = data
    for k in keys:
        if isinstance(val, dict):
            val = val.get(k)
        else:
            return None
        if val is None:
            return None
    # 尝试转换为 float
    if isinstance(val, str):
        try:
            return float(val)
        except ValueError:
            return val
    return val


# ─── 核心评分函数 ───
def evaluate_indicator(name: str, current_value: Any, previous_value: Any, config: Dict) -> IndicatorScore:
    """评估单个指标：连续分 + 趋势分 + 置信度"""
    score_fn = config["score_fn"]
    trend_fn = config.get("trend_fn", lambda c, p: 0.0)

    # 连续评分 [-1, 1]
    continuous = score_fn(current_value) if current_value is not None else 0.0

    # 趋势评分 [-1, 1]
    trend = trend_fn(current_value, previous_value) if previous_value is not None else 0.0

    # 综合评分：70% 当前值 + 30% 趋势
    combined = 0.7 * continuous + 0.3 * trend

    # 信号判定
    if combined > 0.2:
        signal = Signal.BULLISH
        interpretation = config["interpretation_bull"]
    elif combined < -0.2:
        signal = Signal.BEARISH
        interpretation = config["interpretation_bear"]
    else:
        signal = Signal.NEUTRAL
        interpretation = config.get("interpretation_neutral", "中性区间")

    # 置信度：基于数据可用性
    confidence = 1.0
    if current_value is None:
        confidence *= 0.0
    elif previous_value is None:
        confidence *= 0.7  # 无趋势数据

    return IndicatorScore(
        name=name,
        value=current_value,
        signal=Signal.BULLISH if combined > 0.2 else Signal.BEARISH if combined < -0.2 else Signal.NEUTRAL,
        weight=config.get("info_gain_weight", config["base_weight"]),
        tier=config["tier"].value,
        continuous_score=round(continuous, 3),
        trend_score=round(trend, 3),
        combined_score=round(combined, 3),
        interpretation=interpretation,
        source=config["source"],
        timestamp=0,  # 由主程序填充
        confidence=round(confidence, 2),
    )


def detect_divergences(data: Dict, indicators: List[IndicatorScore]) -> List[str]:
    """检测背离：价格 vs 资金流/衍生品/链上"""
    alerts = []
    price = data.get("price", {}).get("usd")
    if not price:
        return alerts

    # 价格创新高但资金流流出
    etf = data.get("macro", {}).get("etf", {})
    etf_avg = _calc_etf_avg_change(etf)
    if etf_avg is not None and etf_avg < -1:
        alerts.append("⚠️ 价格上涨但ETF资金净流出 (Bullish Divergence)")

    # 价格上涨但资金费率深度为负
    deriv = data.get("macro", {}).get("derivatives", {})
    funding = deriv.get("avg_funding_rate_pct")
    if funding is not None and funding < -0.02:
        alerts.append("⚠️ 价格上涨但资金费率深度为负 (Short偏多)")

    # OI减少但价格上涨
    oi_change = deriv.get("oi_change_24h")
    if oi_change is not None and oi_change < -5:
        alerts.append("⚠️ 价格上涨但OI大幅减少 (平仓而非开仓)")

    # MVRV高位但价格创新高
    mvrv = data.get("onchain", {}).get("mvrv")
    if mvrv is not None and mvrv > 3.0:
        alerts.append("⚠️ MVRV>3但价格创新高 (获利盘极重)")

    # NUPL高位
    nupl = data.get("onchain", {}).get("nupl")
    if nupl is not None and nupl > 0.7:
        alerts.append("⚠️ NUPL>0.7 但价格创新高 (长期持有者获利盘极重)")

    return alerts


def calculate_score(data: Dict[str, Any], timestamp: int) -> ScoringResult:
    """
    计算总评分 v9
    输入: 完整的 latest.json 数据字典
    """
    # ─── 读取历史数据用于趋势计算 ───
    history_file = Path(__file__).parent.parent / "data" / "history.json"
    history = []
    if history_file.exists():
        try:
            with open(history_file) as f:
                history = json.load(f)
        except Exception:
            pass

    # ─── 提取当前值和前值映射 ───
    macro = data.get("macro", {})
    liquidity = macro.get("liquidity", {})
    price = data.get("price", {})
    market = data.get("market", {})
    sentiment = data.get("sentiment", {})
    onchain = data.get("onchain", {})
    supply = data.get("supply", {})
    deriv = macro.get("derivatives", {})

    value_map = {}
    for name, config in SCORING_CONFIG.items():
        value_map[name] = _get_nested(data, config["data_path"])

    prev_value_map = {}
    for name, config in SCORING_CONFIG.items():
        if "trend_path" in config:
            prev_value_map[name] = _get_nested_history(history, config["trend_path"])

    # ─── 评估每个指标 ───
    indicators = []
    for name, config in SCORING_CONFIG.items():
        current_val = value_map.get(name)
        prev_val = prev_value_map.get(name)
        indicator = evaluate_indicator(name, current_val, prev_val, config)
        indicator.timestamp = timestamp
        indicators.append(indicator)

    # ─── 背离检测 ───
    divergence_alerts = detect_divergences(data, indicators)

    # ─── 汇总计算 ───
    total_weight = sum(i.weight for i in indicators)
    weighted_sum = sum(i.combined_score * i.weight for i in indicators)
    weighted_score = round(weighted_sum / total_weight * 100, 1) if total_weight else 0  # [-100, 100]

    bullish_weight = sum(i.weight for i in indicators if i.signal == Signal.BULLISH)
    bearish_weight = sum(i.weight for i in indicators if i.signal == Signal.BEARISH)
    neutral_weight = sum(i.weight for i in indicators if i.signal == Signal.NEUTRAL)
    bullish_ratio = round(bullish_weight / total_weight * 100, 1) if total_weight else 0

    # 系统置信度：加权平均
    confidence = sum(i.confidence * i.weight for i in indicators) / total_weight if total_weight else 0
    confidence = round(confidence, 2)

    # 判词 — 3 档: 做空(0-45) / 中性空仓(45-55) / 做多(55-100)
    if bullish_ratio >= 55:
        verdict, icon, color = "做多", "🟢", "#00c853"
    elif bullish_ratio >= 45:
        verdict, icon, color = "中性 — 空仓等待", "🟡", "#ffc107"
    else:
        verdict, icon, color = "做空", "🔴", "#ff3d3d"

    # 分层分解
    tier_breakdown = {}
    for tier in Tier:
        tier_indicators = [i for i in indicators if i.tier == tier.value]
        tier_breakdown[tier.value] = {
            "total": round(sum(i.weight for i in tier_indicators), 1),
            "bullish": round(sum(i.weight for i in tier_indicators if i.signal == Signal.BULLISH), 1),
            "bearish": round(sum(i.weight for i in tier_indicators if i.signal == Signal.BEARISH), 1),
            "neutral": round(sum(i.weight for i in tier_indicators if i.signal == Signal.NEUTRAL), 1),
            "avg_score": round(sum(i.combined_score * i.weight for i in tier_indicators) /
                               sum(i.weight for i in tier_indicators), 3) if tier_indicators else 0,
        }

    return ScoringResult(
        total_weight=round(total_weight, 1),
        weighted_score=weighted_score,
        bullish_ratio=bullish_ratio,
        verdict=verdict,
        verdict_icon=icon,
        verdict_color=color,
        confidence=confidence,
        tier_breakdown=tier_breakdown,
        indicators=indicators,
        divergence_alerts=divergence_alerts,
    )


# ─── 导出用于前端显示的简化格式 ───
def format_for_frontend(result: ScoringResult) -> Dict[str, Any]:
    """转换为前端友好的格式"""
    return {
        "score": {
            "bullish_ratio": result.bullish_ratio,
            "weighted_score": result.weighted_score,
            "verdict": result.verdict,
            "verdict_icon": result.verdict_icon,
            "verdict_color": result.verdict_color,
            "confidence": result.confidence,
        },
        "tiers": result.tier_breakdown,
        "divergence_alerts": result.divergence_alerts,
        "indicators": [
            {
                "name": i.name,
                "value": i.value,
                "signal": i.signal.value,
                "weight": i.weight,
                "tier": i.tier,
                "continuous_score": i.continuous_score,
                "trend_score": i.trend_score,
                "combined_score": i.combined_score,
                "interpretation": i.interpretation,
                "source": i.source,
                "confidence": i.confidence,
            }
            for i in result.indicators
        ],
    }


if __name__ == "__main__":
    # 自测
    test_data = {
        "macro": {
            "liquidity": {"fed_assets_trillions": 7.8, "m2_yoy_pct": 6.2, "rrp_billions": 30, "real_yield_10y": 1.2},
            "dxy": 96.5,
            "inflation": {"cpi_yoy_pct": 2.8},
            "risk": {"vix": {"price": 15}, "oil": {"price": 75}},
            "etf": {"ibit": {"change_pct": 1.2}, "fbtc": {"change_pct": 0.8}},
            "stablecoins": {"usdt_mcap": 160e9},
            "derivatives": {"avg_funding_rate_pct": 0.002, "binance_basis_pct_annual": 3.5, "oi_change_24h": 2.1},
        },
        "price": {"usd": 65000},
        "market": {"btc_dominance_pct": 58},
        "sentiment": {"current": {"value": 20}},
        "onchain": {"hashrate_1w_avg_eh_s": 580, "cm_roi_30d": 0.05, "mvrv": 1.2, "nupl": 0.3, "realized_price_usd": 45000},
        "supply": {},
    }
    result = calculate_score(test_data, int(time.time()))
    print(f"Verdict: {result.verdict_icon} {result.verdict}")
    print(f"Weighted Score: {result.weighted_score}")
    print(f"Bullish Ratio: {result.bullish_ratio}%")
    print(f"Confidence: {result.confidence}")
    print(f"Tiers: {result.tier_breakdown}")
    print(f"Divergence Alerts: {result.divergence_alerts}")
    import json
    print(json.dumps(format_for_frontend(result), indent=2, ensure_ascii=False))