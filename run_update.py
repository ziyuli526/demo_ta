"""
run_update.py
30天視窗: 2026-09-21 ~ 2026-10-20
來源優先: obs(O-A0001-001) > forecast(F-C0032-001) > sim(線性内插)
禁止随機數；obs 可覆蓋 forecast/sim，反之不可
"""
import sys
sys.stdout.reconfigure(encoding="utf-8")

import os, requests, pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv
load_dotenv()

from config import STATIONS, CWA_API_KEY, CWA_API_URL, T_BASE, SLIDING_WINDOW_DAYS
from gdd_model import calculate_daily_gdd

WINDOW_END   = datetime(2026, 10, 20)
TODAY        = datetime(2026, 10, 18)
WINDOW_START = WINDOW_END - timedelta(days=SLIDING_WINDOW_DAYS - 1)  # 2026-09-21
TODAY_STR    = TODAY.strftime("%Y-%m-%d")

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CSV_PATH = os.path.join(DATA_DIR, "station_history.csv")

# 9月下旬各站季節基準溫(前後内插起點，不含亂數)
SEASONAL_BASE = {
    "C0G660": (31.0, 23.0),
    "C0K420": (31.0, 23.0),
    "C0H890": (29.0, 20.0),
    "C0M680": (31.5, 23.5),
    "C0X250": (32.0, 24.0),
    "C0R470": (33.0, 25.0),
    "C0U940": (30.0, 23.0),
    "C0F9M0": (31.0, 23.0),
    "C0V610": (32.5, 25.0),
    "C0A770": (30.0, 23.5),
}
COUNTY_MAP = {
    "C0G660": "彰化縣", "C0K420": "雲林縣", "C0H890": "南投縣",
    "C0M680": "嘉義縣", "C0X250": "臺南市", "C0R470": "屏東縣",
    "C0U940": "宜蘭縣", "C0F9M0": "臺中市", "C0V610": "高雄市",
    "C0A770": "臺北市",
}

def safe_float(val):
    if val is None:
        return None
    try:
        f = float(val)
        return None if f <= -98 else round(f, 1)
    except (ValueError, TypeError):
        return None

def lerp(v0, v1, n, i):
    """線性内插: i 從 0(v0) 到 n-1(v1)"""
    if n <= 1:
        return v0
    return round(v0 + (v1 - v0) * i / (n - 1), 1)

def get_obs():
    """O-A0001-001 取今日各站實測極溫"""
    obs = {}
    for st in STATIONS:
        sid = st["station_id"]
        try:
            r = requests.get(CWA_API_URL,
                params={"Authorization": CWA_API_KEY, "StationId": sid, "format": "JSON"},
                timeout=8)
            if r.status_code != 200:
                continue
            raw = r.json().get("records", {}).get("Station", [])
            if not raw:
                continue
            we = raw[0].get("WeatherElement", {})
            de = we.get("DailyExtreme", {})
            tmax = safe_float(de.get("DailyHigh", {}).get("TemperatureInfo", {}).get("AirTemperature"))
            tmin = safe_float(de.get("DailyLow",  {}).get("TemperatureInfo", {}).get("AirTemperature"))
            if tmax is not None and tmin is not None and tmax >= tmin:
                obs[sid] = {"t_max": tmax, "t_min": tmin}
        except Exception:
            pass
    return obs

def get_forecast():
    """F-C0032-001 取縣市36小時預報"""
    fc_data = {}
    try:
        r = requests.get(
            "https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-C0032-001",
            params={"Authorization": CWA_API_KEY, "format": "JSON", "elementName": "MaxT,MinT"},
            timeout=10)
        if r.status_code != 200:
            return fc_data
        locations = r.json().get("records", {}).get("location", [])
        loc_lkp = {loc["locationName"]: loc for loc in locations}

        for st in STATIONS:
            sid = st["station_id"]
            loc = loc_lkp.get(COUNTY_MAP.get(sid, ""))
            if not loc:
                continue
            elements = {el["elementName"]: el["time"] for el in loc.get("weatherElement", [])}
            day_vals = {}
            for t_entry in elements.get("MaxT", []):
                d = t_entry.get("startTime", "")[:10]
                v = safe_float(t_entry.get("parameter", {}).get("parameterName"))
                if d and v is not None:
                    day_vals.setdefault(d, {"maxs": [], "mins": []})["maxs"].append(v)
            for t_entry in elements.get("MinT", []):
                d = t_entry.get("startTime", "")[:10]
                v = safe_float(t_entry.get("parameter", {}).get("parameterName"))
                if d and v is not None:
                    day_vals.setdefault(d, {"maxs": [], "mins": []})["mins"].append(v)
            sid_fc = {}
            for d, vv in day_vals.items():
                if vv["maxs"] and vv["mins"]:
                    mx = max(vv["maxs"]); mn = min(vv["mins"])
                    if mx >= mn:
                        sid_fc[d] = {"t_max": mx, "t_min": mn}
            if sid_fc:
                fc_data[sid] = sid_fc
    except Exception as e:
        print(f"  [forecast API error] {e}")
    return fc_data

def main():
    obs = get_obs()
    fc  = get_forecast()

    all_dates = [(WINDOW_START + timedelta(days=i)).strftime("%Y-%m-%d")
                 for i in range(SLIDING_WINDOW_DAYS)]
    # 歷史内插：09-21(idx=0) → 10-18(idx=27)，共 28 步
    N_HIST = 28

    records = []
    summary = {}

    for st in STATIONS:
        sid = st["station_id"]
        cnt = {"obs": 0, "forecast": 0, "sim": 0}

        obs_today = obs.get(sid)
        base_mx, base_mn = SEASONAL_BASE.get(sid, (30.0, 22.0))

        # 内插終點
        if obs_today:
            end_mx, end_mn = obs_today["t_max"], obs_today["t_min"]
        else:
            fc_today = fc.get(sid, {}).get(TODAY_STR)
            end_mx = fc_today["t_max"] if fc_today else base_mx - 2.0
            end_mn = fc_today["t_min"] if fc_today else base_mn - 2.0

        for i, date_str in enumerate(all_dates):
            row_dt = datetime.strptime(date_str, "%Y-%m-%d")

            if date_str == TODAY_STR and obs_today:
                t_max, t_min, src = obs_today["t_max"], obs_today["t_min"], "obs"

            elif row_dt > TODAY and date_str in fc.get(sid, {}):
                f = fc[sid][date_str]
                t_max, t_min, src = f["t_max"], f["t_min"], "forecast"

            elif row_dt < TODAY:
                # 歷史: 線性内插 (09-21 基準 → 10-18 實測)
                t_max = lerp(base_mx, end_mx, N_HIST, i)
                t_min = lerp(base_mn, end_mn, N_HIST, i)
                src = "sim"

            else:
                # 未來無預報: 用實測溫度延平，不用亂數
                t_max, t_min, src = end_mx, end_mn, "sim"

            # 驗證
            if t_max is None or t_min is None:
                continue
            if t_max < t_min:
                t_max, t_min = t_min, t_max

            daily_gdd = calculate_daily_gdd(t_max, t_min, T_BASE)
            records.append({
                "station_id": sid,
                "date":       date_str,
                "t_max":      t_max,
                "t_min":      t_min,
                "daily_gdd":  daily_gdd,
                "is_simulated": (src != "obs"),
                "data_source": src
            })
            cnt[src] += 1

        summary[sid] = cnt

    pd.DataFrame(records).to_csv(CSV_PATH, index=False, encoding="utf-8-sig")

    # ── 輸出摘要 ────────────────────────────────────────────────────────
    print(f"視窗: {WINDOW_START.strftime('%Y-%m-%d')} ~ {WINDOW_END.strftime('%Y-%m-%d')} (30天)")
    print()
    print(f"{'測站':<10} {'obs':>5} {'forecast':>10} {'sim':>5}  今日資料 (data_source)")
    print("-" * 62)
    for st in STATIONS:
        sid = st["station_id"]
        s = summary[sid]
        td = next((r for r in records if r["station_id"] == sid and r["date"] == TODAY_STR), None)
        td_info = f"Tmax={td['t_max']} Tmin={td['t_min']} [{td['data_source']}]" if td else "無"
        print(f"{st['name']:<10} {s['obs']:>5} {s['forecast']:>10} {s['sim']:>5}  {td_info}")

    print()
    no_obs_cnt = SLIDING_WINDOW_DAYS - 1  # 除今天外皆無實測
    fc_dates = sorted(set(
        d for sid_fc in fc.values() for d in sid_fc if d > TODAY_STR))
    print(f"無實測資料的日期: {no_obs_cnt} 天")
    print(f"  原因: O-A0001-001 為即時站，不提供歷史日期查詢")
    if fc_dates:
        print(f"預報覆蓋日期: {fc_dates}")
    else:
        print(f"預報日期: 無 (F-C0032-001 未回傳未來日期)")

if __name__ == "__main__":
    main()
