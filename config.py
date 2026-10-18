"""
config.py - 小菜蛾 GDD 病蟲害預警系統設定檔
包含科學參數、四級風險定義與 10 大重點農藝觀測站列表
"""

import os
from dotenv import load_dotenv

# 載入 .env
load_dotenv()

# CWA API 設定
CWA_API_KEY = os.getenv("CWA_API_KEY", "")
CWA_API_URL = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/O-A0001-001"

# 小菜蛾科學參數 (依文獻: 巴西亞熱帶族群/台灣氣候)
T_BASE = 6.3          # 發育門檻溫度 (°C)
GENERATION_GDD = 300.0 # 完成一世代累積積溫 (GDD)
SLIDING_WINDOW_DAYS = 30 # 積溫累積時間視窗 (天)

# 四級風險燈號定義
RISK_LEVELS = [
    {
        "level": 1,
        "name": "低風險/發育初期",
        "min_gdd": 0.0,
        "max_gdd": 100.0,
        "color_name": "green",
        "hex": "#28a745",
        "badge_bg": "#d4edda",
        "badge_fg": "#155724",
        "icon": "🟢",
        "advice": "目前累積積溫較低，病蟲害密度極低，維持正常氣象監測與定期田間巡視即可。"
    },
    {
        "level": 2,
        "name": "觀察期",
        "min_gdd": 100.0,
        "max_gdd": 200.0,
        "color_name": "yellow",
        "hex": "#ffc107",
        "badge_bg": "#fff3cd",
        "badge_fg": "#856404",
        "icon": "🟡",
        "advice": "小菜蛾蟲卵開始孵化，建議提高田間巡查頻率，檢視葉背是否有幼蟲食痕與初齡幼蟲。"
    },
    {
        "level": 3,
        "name": "建議防治期",
        "min_gdd": 200.0,
        "max_gdd": 280.0,
        "color_name": "orange",
        "hex": "#fd7e14",
        "badge_bg": "#ffe8cc",
        "badge_fg": "#d9480f",
        "icon": "🟠",
        "advice": "積溫已達羽化高峰前夕！請立即準備輪用推薦藥劑（如蘇力菌 Bacillus thuringiensis）或佈設小菜蛾性費洛蒙誘捕器進行物理防除。"
    },
    {
        "level": 4,
        "name": "高峰爆發期",
        "min_gdd": 280.0,
        "max_gdd": float("inf"),
        "color_name": "red",
        "hex": "#dc3545",
        "badge_bg": "#f8d7da",
        "badge_fg": "#721c24",
        "icon": "🔴",
        "advice": "警告：累積積溫已接近/超過單世代 300 GDD，野外成蟲羽化與產卵達最高峰！請立即實施全面防治，並通知周邊農戶同步共同防除。"
    }
]

# 8-10 個十字花科蔬菜主要產區觀測站設定
STATIONS = [
    {
        "station_id": "C0G660",
        "name": "彰化溪湖",
        "county": "彰化縣",
        "town": "溪湖鎮",
        "lat": 23.9575,
        "lon": 120.4851,
        "crop_info": "全台十字花科包心白菜、甘藍核心產區"
    },
    {
        "station_id": "C0K420",
        "name": "雲林西螺",
        "county": "雲林縣",
        "town": "西螺鎮",
        "lat": 23.7972,
        "lon": 120.4658,
        "crop_info": "全台最大蔬菜集散與甘藍、青花菜批發基地"
    },
    {
        "station_id": "C0H890",
        "name": "南投埔里",
        "county": "南投縣",
        "town": "埔里鎮",
        "lat": 23.9664,
        "lon": 120.9675,
        "crop_info": "夏季高冷地甘藍與十字花科專業栽培區"
    },
    {
        "station_id": "C0M680",
        "name": "嘉義太保",
        "county": "嘉義縣",
        "town": "太保市",
        "lat": 23.4601,
        "lon": 120.3235,
        "crop_info": "嘉南平原露地甘藍與花菜類主要專區"
    },
    {
        "station_id": "C0X250",
        "name": "台南新營",
        "county": "台南市",
        "town": "新營區",
        "lat": 23.3106,
        "lon": 120.3168,
        "crop_info": "溪北地區十字花科小白菜、蘿蔔重點產區"
    },
    {
        "station_id": "C0R470",
        "name": "屏東高樹",
        "county": "屏東縣",
        "town": "高樹鄉",
        "lat": 22.8189,
        "lon": 120.6012,
        "crop_info": "屏東熱帶地區冬季裡作甘藍與芥菜產區"
    },
    {
        "station_id": "C0U940",
        "name": "宜蘭羅東",
        "county": "宜蘭縣",
        "town": "羅東鎮",
        "lat": 24.6770,
        "lon": 121.7667,
        "crop_info": "蘭陽平原雨季高濕度十字花科菜園區"
    },
    {
        "station_id": "C0F9M0",
        "name": "台中豐原",
        "county": "台中市",
        "town": "豐原區",
        "lat": 24.2568,
        "lon": 120.7239,
        "crop_info": "台中平地短期葉菜類與青花菜產區"
    },
    {
        "station_id": "C0V610",
        "name": "高雄梓官",
        "county": "高雄市",
        "town": "梓官區",
        "lat": 22.7597,
        "lon": 120.2642,
        "crop_info": "南台灣重要專業蔬菜專區與產銷班"
    },
    {
        "station_id": "C0A770",
        "name": "台北士林",
        "county": "台北市",
        "town": "士林區",
        "lat": 25.0933,
        "lon": 121.5284,
        "crop_info": "大台北近郊有機十字花科蔬菜農園區"
    }
]
