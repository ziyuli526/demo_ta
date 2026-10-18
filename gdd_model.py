"""
gdd_model.py - 小菜蛾 GDD 積溫發育科學模型與風險判定模組
包含單日 GDD 計算、累積 GDD 計算、四級風險判定與世代發育進度估算
"""

from typing import List, Dict, Any, Union
from config import T_BASE, GENERATION_GDD, RISK_LEVELS


def calculate_daily_gdd(t_max: Union[float, int, str], t_min: Union[float, int, str], t_base: float = T_BASE) -> float:
    """
    計算單日有效積溫 (GDD, Growing Degree Days)
    
    公式: 每日GDD = ((當日最高溫 T_max + 當日最低溫 T_min) / 2) - T_base
    規則: 若計算結果 < 0，則該日 GDD 記為 0.0
    
    :param t_max: 當日最高溫 (°C)
    :param t_min: 當日最低溫 (°C)
    :param t_base: 發育門檻溫度 (°C)，小菜蛾預設為 6.3°C
    :return: 單日 GDD 數值 (float)
    """
    try:
        t_max_val = float(t_max)
        t_min_val = float(t_min)
    except (ValueError, TypeError):
        # 若傳入非數值或 None，安全傳回 0.0
        return 0.0

    # 防呆邏輯：若最高溫小於最低溫，進行校正
    if t_max_val < t_min_val:
        t_max_val, t_min_val = t_min_val, t_max_val

    t_mean = (t_max_val + t_min_val) / 2.0
    gdd = t_mean - t_base

    return round(max(0.0, gdd), 2)


def calculate_cumulative_gdd(daily_gdd_list: List[float]) -> float:
    """
    計算累積積溫 (Cumulative GDD)
    
    :param daily_gdd_list: 每日 GDD 列表 (過去 N 天)
    :return: 累積 GDD 加總 (float)
    """
    valid_gdds = []
    for val in daily_gdd_list:
        try:
            valid_gdds.append(float(val))
        except (ValueError, TypeError):
            continue

    return round(sum(valid_gdds), 2)


def classify_risk_level(cumulative_gdd: float) -> Dict[str, Any]:
    """
    依據累積 GDD 判定病蟲害四級風險等級
    
    0–100: 低風險/發育初期 (🟢 綠)
    100–200: 觀察期 (🟡 黃)
    200–280: 建議防治期 (🟠 橙)
    >280: 高峰爆發期 (🔴 紅)
    
    :param cumulative_gdd: 30天累積 GDD
    :return: Risk level dictionary
    """
    gdd_val = max(0.0, float(cumulative_gdd))

    for risk in RISK_LEVELS:
        if risk["min_gdd"] <= gdd_val < risk["max_gdd"]:
            res = risk.copy()
            res["cumulative_gdd"] = gdd_val
            return res

    # 預設最後一級 (爆發期)
    res = RISK_LEVELS[-1].copy()
    res["cumulative_gdd"] = gdd_val
    return res


def estimate_generations(cumulative_gdd: float) -> Dict[str, Any]:
    """
    估算目前積溫相當於完成多少世代小菜蛾發育
    
    :param cumulative_gdd: 累積積溫
    :return: 世代分析數據字典
    """
    gdd_val = max(0.0, float(cumulative_gdd))
    generations_completed = gdd_val / GENERATION_GDD
    current_gen_gdd = gdd_val % GENERATION_GDD
    progress_pct = round((current_gen_gdd / GENERATION_GDD) * 100, 1)
    gdd_to_next_peak = round(max(0.0, GENERATION_GDD - current_gen_gdd), 1)

    return {
        "generations_completed": round(generations_completed, 2),
        "current_gen_gdd": round(current_gen_gdd, 1),
        "progress_pct": min(100.0, progress_pct),
        "gdd_to_next_peak": gdd_to_next_peak,
        "generation_threshold": GENERATION_GDD
    }


# 單元測試範例驗證
if __name__ == "__main__":
    print("--- GDD Model Unit Test ---")
    print("Day GDD (Tmax=28, Tmin=18, Tbase=6.3):", calculate_daily_gdd(28, 18)) # (23 - 6.3) = 16.7
    print("Day GDD (Tmax=5, Tmin=2, Tbase=6.3):", calculate_daily_gdd(5, 2))     # 3.5 - 6.3 = -2.8 -> 0.0
    print("Risk for 85 GDD:", classify_risk_level(85)["name"])
    print("Risk for 150 GDD:", classify_risk_level(150)["name"])
    print("Risk for 230 GDD:", classify_risk_level(230)["name"])
    print("Risk for 310 GDD:", classify_risk_level(310)["name"])
    print("Gen progress for 350 GDD:", estimate_generations(350))
