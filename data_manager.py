"""
data_manager.py - 30 天歷史滑動視窗 (Sliding Window) 資料管理器
負責儲存歷史氣溫與 GDD 數據、自動追加最新 API/模擬氣象資料、維護 30 天視窗
"""

import os
import pandas as pd
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any

from config import STATIONS, SLIDING_WINDOW_DAYS, T_BASE
from gdd_model import calculate_daily_gdd, calculate_cumulative_gdd, classify_risk_level, estimate_generations
from cwa_api import fetch_station_weather

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CSV_PATH = os.path.join(DATA_DIR, "station_history.csv")


class GDDDataManager:
    """30天滑動視窗資料庫與計算管理器"""

    def __init__(self, csv_path: str = CSV_PATH):
        self.csv_path = csv_path
        os.makedirs(os.path.dirname(self.csv_path), exist_ok=True)
        self._ensure_data_initialized()

    def _ensure_data_initialized(self):
        """若歷史 CSV 不存在，建立每個測站過去 29 天的初始化模擬歷史氣象資料"""
        if not os.path.exists(self.csv_path):
            self.generate_initial_simulation_data()

    def generate_initial_simulation_data(self):
        """生成初始化 29 天過去歷史氣溫 + 1 天當日預設氣溫"""
        records = []
        today = datetime.now()

        for st in STATIONS:
            st_id = st["station_id"]
            
            # 設定不同測站的微氣候基溫趨勢
            base_tmax = 28.5
            base_tmin = 20.5
            if st_id == "C0I080": # 埔里 (涼爽)
                base_tmax, base_tmin = 26.5, 17.5
            elif st_id in ["467490", "C0V710"]: # 屏東/高雄 (炎熱)
                base_tmax, base_tmin = 31.0, 23.0

            # 產生過去 29 天模擬歷史
            for i in range(SLIDING_WINDOW_DAYS - 1, 0, -1):
                date_str = (today - timedelta(days=i)).strftime("%Y-%m-%d")
                
                # 類隨機氣溫波浪 (呈現自然天氣變化)
                t_max = round(base_tmax + random.uniform(-2.5, 3.0), 1)
                t_min = round(base_tmin + random.uniform(-2.0, 2.5), 1)
                if t_max < t_min:
                    t_max, t_min = t_min, t_max
                
                daily_gdd = calculate_daily_gdd(t_max, t_min, T_BASE)

                records.append({
                    "station_id": st_id,
                    "date": date_str,
                    "t_max": t_max,
                    "t_min": t_min,
                    "daily_gdd": daily_gdd,
                    "is_simulated": True
                })

            # 當日數據 (作為第 30 筆)
            date_today = today.strftime("%Y-%m-%d")
            t_max_today = round(base_tmax + random.uniform(-1.0, 2.0), 1)
            t_min_today = round(base_tmin + random.uniform(-1.0, 1.5), 1)
            if t_max_today < t_min_today:
                t_max_today, t_min_today = t_min_today, t_max_today
            
            gdd_today = calculate_daily_gdd(t_max_today, t_min_today, T_BASE)
            
            records.append({
                "station_id": st_id,
                "date": date_today,
                "t_max": t_max_today,
                "t_min": t_min_today,
                "daily_gdd": gdd_today,
                "is_simulated": True
            })

        df = pd.DataFrame(records)
        df.to_csv(self.csv_path, index=False, encoding="utf-8-sig")

    def load_data(self) -> pd.DataFrame:
        """載入歷史氣象資料庫"""
        if not os.path.exists(self.csv_path):
            self.generate_initial_simulation_data()
        
        df = pd.read_csv(self.csv_path, encoding="utf-8-sig")
        return df

    def update_with_today_api_data(self, api_key: str = "") -> Dict[str, Any]:
        """
        呼叫 CWA API (或模擬) 抓取各測站當日真實最高溫/最低溫，
        將其 append 入資料庫，並維持固定 30 天滑動視窗 (Sliding Window)。
        """
        df = self.load_data()
        today_str = datetime.now().strftime("%Y-%m-%d")
        api_results = []

        new_records = []

        for st in STATIONS:
            st_id = st["station_id"]
            # 呼叫 API 抓取
            weather_res = fetch_station_weather(st_id, api_key=api_key)
            api_results.append(weather_res)

            t_max = weather_res["t_max"]
            t_min = weather_res["t_min"]
            is_sim = weather_res["is_simulated"]
            daily_gdd = calculate_daily_gdd(t_max, t_min, T_BASE)

            # 取出該測站原有資料
            st_df = df[df["station_id"] == st_id].sort_values("date")
            
            # 若今日資料已存在，覆蓋最新筆；否則 append 並丟棄最舊一筆
            if not st_df.empty and st_df.iloc[-1]["date"] == today_str:
                st_df.iloc[-1, st_df.columns.get_loc("t_max")] = t_max
                st_df.iloc[-1, st_df.columns.get_loc("t_min")] = t_min
                st_df.iloc[-1, st_df.columns.get_loc("daily_gdd")] = daily_gdd
                st_df.iloc[-1, st_df.columns.get_loc("is_simulated")] = is_sim
                updated_st_df = st_df.tail(SLIDING_WINDOW_DAYS)
            else:
                new_row = pd.DataFrame([{
                    "station_id": st_id,
                    "date": today_str,
                    "t_max": t_max,
                    "t_min": t_min,
                    "daily_gdd": daily_gdd,
                    "is_simulated": is_sim
                }])
                combined = pd.concat([st_df, new_row], ignore_index=True)
                updated_st_df = combined.tail(SLIDING_WINDOW_DAYS)

            new_records.append(updated_st_df)

        final_df = pd.concat(new_records, ignore_index=True)
        final_df.to_csv(self.csv_path, index=False, encoding="utf-8-sig")

        # 計算 API 成功/模擬統計
        sim_count = sum(1 for r in api_results if r.get("is_simulated", True))
        real_count = len(api_results) - sim_count

        return {
            "total_stations": len(STATIONS),
            "real_api_count": real_count,
            "simulated_count": sim_count,
            "api_results": api_results
        }



    def get_all_summary(self) -> List[Dict[str, Any]]:
        df = self.load_data()
        summary_list = []

        for st in STATIONS:
            st_id = st["station_id"]
            st_df = df[df["station_id"] == st_id].sort_values("date").tail(SLIDING_WINDOW_DAYS)
            
            daily_gdds = st_df["daily_gdd"].tolist()
            cumulative_gdd = calculate_cumulative_gdd(daily_gdds)
            risk_info = classify_risk_level(cumulative_gdd)
            gen_info = estimate_generations(cumulative_gdd)

            # 最新一日數據
            latest_row = st_df.iloc[-1] if not st_df.empty else {}
            latest_tmax = latest_row.get("t_max", 0.0)
            latest_tmin = latest_row.get("t_min", 0.0)
            is_sim = bool(latest_row.get("is_simulated", True))

            summary_item = {
                "station_id": st_id,
                "name": st["name"],
                "county": st["county"],
                "town": st["town"],
                "lat": st["lat"],
                "lon": st["lon"],
                "crop_info": st["crop_info"],
                "latest_tmax": latest_tmax,
                "latest_tmin": latest_tmin,
                "cumulative_gdd": cumulative_gdd,
                "risk_level": risk_info["level"],
                "risk_name": risk_info["name"],
                "risk_color": risk_info["color_name"],
                "risk_hex": risk_info["hex"],
                "risk_icon": risk_info["icon"],
                "advice": risk_info["advice"],
                "is_simulated": is_sim,
                "generations_completed": gen_info["generations_completed"],
                "progress_pct": gen_info["progress_pct"],
                "gdd_to_next_peak": gen_info["gdd_to_next_peak"]
            }
            summary_list.append(summary_item)

        return summary_list

    def get_station_trend(self, station_id: str) -> pd.DataFrame:
        """
        傳回指定測站過去 30 天的每日 GDD 與累積 GDD 趨勢 DataFrame
        """
        df = self.load_data()
        st_df = df[df["station_id"] == station_id].sort_values("date").tail(SLIDING_WINDOW_DAYS).copy()
        
        # 計算邊走邊加總的 30 天累積 GDD 趨勢
        st_df["cumulative_gdd_trend"] = st_df["daily_gdd"].cumsum().round(2)
        return st_df


if __name__ == "__main__":
    print("--- Data Manager Test ---")
    dm = GDDDataManager()
    summary = dm.get_all_summary()
    print(f"Loaded {len(summary)} station summaries.")
    for s in summary[:3]:
        print(f"Station {s['name']} -> Cum GDD: {s['cumulative_gdd']} ({s['risk_icon']} {s['risk_name']})")
