"""
app.py - 小菜蛾 (Diamondback moth) GDD 積溫病蟲害預警地圖系統
介面完全採納「中央氣象署 (CWA) 官方縣市預報網站」之藍白經典視覺風格與排版設計
"""

import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

from config import STATIONS, RISK_LEVELS, T_BASE, GENERATION_GDD, CWA_API_KEY
from gdd_model import classify_risk_level, estimate_generations
from data_manager import GDDDataManager

# 1. 頁面配置
st.set_page_config(
    page_title="小菜蛾有效積溫全台監測與地圖預報系統",
    page_icon="🐛",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. 注入 CWA 官方網站等級之 CSS 樣式 (經典藍白、俐落卡片、紅框特報)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@300;400;500;700;900&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Noto Sans TC', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    
    .stApp {
        background-color: #f4f7fa;
    }
    
    .main .block-container {
        padding-top: 0rem;
        padding-bottom: 2rem;
        max-width: 1360px;
    }
    
    /* CWA 官方雙層導覽列 */
    .cwa-top-utility-bar {
        background-color: #003366;
        color: #d1e3f8;
        padding: 6px 24px;
        font-size: 0.82rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    .cwa-primary-header {
        background: linear-gradient(90deg, #004488 0%, #0f5b9e 100%);
        color: white;
        padding: 16px 28px;
        box-shadow: 0 4px 12px rgba(0, 51, 102, 0.2);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    .cwa-logo-title {
        font-size: 1.65rem;
        font-weight: 800;
        letter-spacing: 0.8px;
        display: flex;
        align-items: center;
        gap: 12px;
    }
    
    .cwa-sub-header {
        font-size: 0.95rem;
        color: #e2eeff;
        font-weight: 400;
        margin-top: 2px;
    }
    
    /* 氣象特報 Bar (仿 CWA 豪雨/強風特報風格) */
    .cwa-alert-strip {
        background-color: #fff4f4;
        border-bottom: 1px solid #ffcccc;
        padding: 10px 24px;
        display: flex;
        align-items: center;
        gap: 14px;
        font-size: 0.9rem;
    }
    
    .cwa-alert-badge {
        background-color: #d9534f;
        color: white;
        padding: 3px 10px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.82rem;
        display: inline-flex;
        align-items: center;
        gap: 4px;
    }

    .cwa-breadcrumb {
        background-color: #e9f2fb;
        padding: 8px 24px;
        font-size: 0.85rem;
        color: #004488;
        border-bottom: 1px solid #d4e4f5;
        margin-bottom: 20px;
    }
    
    /* 仿 CWA 縣市網格卡片 */
    .cwa-card-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
        gap: 14px;
    }
    
    .cwa-county-card {
        background-color: #ffffff;
        border: 1px solid #d9e6f2;
        border-radius: 8px;
        padding: 14px 16px;
        box-shadow: 0 2px 6px rgba(0, 68, 136, 0.05);
        transition: all 0.2s ease;
    }
    
    .cwa-county-card:hover {
        border-color: #0f5b9e;
        box-shadow: 0 4px 12px rgba(0, 68, 136, 0.12);
        transform: translateY(-1px);
    }
    
    .cwa-card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding-bottom: 8px;
        border-bottom: 1px solid #edf3f8;
        margin-bottom: 10px;
    }
    
    .cwa-card-title {
        font-size: 1.1rem;
        font-weight: 700;
        color: #003366;
    }
    
    .cwa-temp-tag {
        font-size: 1.05rem;
        font-weight: 700;
        color: #2c3e50;
    }
    
    .cwa-gdd-badge {
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 0.8rem;
        font-weight: 700;
    }

    /* Tab 分頁與頁籤風格 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background-color: #e3edf7;
        padding: 4px 6px;
        border-radius: 8px;
    }

    .stTabs [data-baseweb="tab"] {
        border-radius: 6px;
        padding: 8px 16px;
        font-weight: 700;
        color: #004488;
    }

    .stTabs [aria-selected="true"] {
        background-color: #ffffff !important;
        color: #003366 !important;
        box-shadow: 0 2px 6px rgba(0,0,0,0.08);
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def get_data_manager():
    return GDDDataManager()


dm = get_data_manager()

# 自動於後端維持 API 串接與數據載入
@st.cache_data(ttl=3600)  # 3600 秒 = 1 小時
def update_today(api_key):
    dm.update_with_today_api_data(api_key=api_key)
    
if CWA_API_KEY:
    dm.update_with_today_api_data(api_key=CWA_API_KEY)

# 3. 側邊欄 (區域與風險篩選)
with st.sidebar:
    st.markdown("### 🐛 病蟲害預警導覽")
    st.markdown("---")
    
    st.subheader("📍 區域與風險篩選")
    
    selected_risk_filter = st.selectbox(
        "發育風險等級",
        ["全部等級", "🟢 低風險/發育初期", "🟡 觀察期", "🟠 建議防治期", "🔴 高峰爆發期"]
    )
    
    counties = ["全部縣市"] + sorted(list(set(s["county"] for s in STATIONS)))
    selected_county_filter = st.selectbox("縣市選單", counties)

    st.markdown("---")
    st.markdown("""
    <div style="font-size: 0.82rem; color: #555; background: #eaf3fc; padding: 12px; border-radius: 8px; border: 1px solid #cce0f5;">
        <b>💡 小菜蛾 (GDD) 發育模型說明：</b><br>
        • 發育門檻 ($T_{base}$): <b>6.3°C</b><br>
        • 單世代完成積溫: <b>300 GDD</b><br>
        • 時間視窗: <b>過去 30 天</b>
    </div>
    """, unsafe_allow_html=True)

# 4. 頂部 Header (更新標題)
current_time_str = datetime.now().strftime("%Y/%m/%d %H:%M")

st.markdown(f"""
<div class="cwa-top-utility-bar">
    <div>農業氣象病蟲害監測預警資訊網</div>
    <div>資料更新時間：{current_time_str} ｜ 單位：攝氏 (°C) / GDD</div>
</div>
<div class="cwa-primary-header">
    <div>
        <div class="cwa-logo-title">
            <span>🐛 小菜蛾有效積溫全台監測與地圖預報系統</span>
        </div>
        <div class="cwa-sub-header">Diamondback Moth (Plutella xylostella) Growing Degree Days Warning System</div>
    </div>
    <div style="text-align: right; background: rgba(255,255,255,0.15); padding: 8px 16px; border-radius: 6px;">
        <div style="font-size: 0.8rem;">單世代發育門檻</div>
        <div style="font-weight: 800; font-size: 1.1rem;">300 GDD (T<sub>base</sub>=6.3°C)</div>
    </div>
</div>
""", unsafe_allow_html=True)

# 5. 載入數據與計算
all_summaries = dm.get_all_summary()

# 篩選資料
filtered_summaries = all_summaries.copy()
if selected_risk_filter != "全部等級":
    risk_target = selected_risk_filter.split(" ", 1)[1]
    filtered_summaries = [s for s in filtered_summaries if s["risk_name"] == risk_target]

if selected_county_filter != "全部縣市":
    filtered_summaries = [s for s in filtered_summaries if s["county"] == selected_county_filter]

red_alert_stations = [s for s in all_summaries if s["risk_level"] == 4]
orange_alert_stations = [s for s in all_summaries if s["risk_level"] == 3]

# 6. 仿 CWA 警特報紅框 Bar
if red_alert_stations or orange_alert_stations:
    alert_items_html = ""
    if red_alert_stations:
        names = "、".join([f"{s['name']} ({s['cumulative_gdd']} GDD)" for s in red_alert_stations])
        alert_items_html += f"<span><span class='cwa-alert-badge'>❗ 爆發特報</span> <b>高峰爆發期測站：</b>{names} — 累積積溫突破 300 GDD，野外成蟲產卵達高峰！</span> "
    if orange_alert_stations:
        names = "、".join([f"{s['name']} ({s['cumulative_gdd']} GDD)" for s in orange_alert_stations])
        alert_items_html += f"<span><span class='cwa-alert-badge' style='background-color: #f0ad4e;'>⚠️ 建議防治</span> <b>防治預警測站：</b>{names} — 請部署性費洛蒙誘捕器或輪用蘇力菌。</span>"

    st.markdown(f"""
    <div class="cwa-alert-strip">
        {alert_items_html}
    </div>
    """, unsafe_allow_html=True)

# 7. CWA 面包屑導覽
st.markdown("""
<div class="cwa-breadcrumb">
    🏠 首頁 > 農業氣象 > 病蟲害有效積溫 (GDD) 預警 > <b>全台縣市主要十字花科產區觀測站</b>
</div>
""", unsafe_allow_html=True)

# 8. 主要內容區域：左側互動地圖 + 右側 CWA 風格縣市預報網格卡片
map_col, grid_col = st.columns([1.1, 1.25])

with map_col:
    st.markdown("### 🗺️ 全台氣象觀測站預警地圖")
    st.caption("點擊地圖測站圖標可查看該農業產區之極溫、累積 GDD 及防除建議。")
    
    # 建立 CWA 風格地圖 ( centered on Taiwan 23.8, 120.95 )
    m = folium.Map(
        location=[23.8, 120.95],
        zoom_start=8,
        tiles="OpenStreetMap"
    )

    for st_data in filtered_summaries:
        color_hex = st_data["risk_hex"]
        
        # CWA 網頁風格之 Popup HTML
        popup_html = f"""
        <div style="font-family: 'Noto Sans TC', sans-serif; width: 250px; padding: 4px;">
            <div style="background-color: #004488; color: white; padding: 6px 10px; border-radius: 4px; font-weight: bold; font-size: 13px;">
                📍 {st_data['name']} ({st_data['county']})
            </div>
            <div style="padding: 8px 2px; font-size: 12px; line-height: 1.6; color: #2c3e50;">
                <b>當日極溫：</b><span style="color:#d9534f; font-weight:bold;">{st_data['latest_tmax']}°C</span> ~ <span style="color:#0275d8; font-weight:bold;">{st_data['latest_tmin']}°C</span><br>
                <b>30天累積積溫：</b><b style="font-size:14px; color:{color_hex};">{st_data['cumulative_gdd']} GDD</b><br>
                <b>風險燈號：</b><span style="background:{st_data['risk_hex']}; color:white; padding:1px 6px; border-radius:3px;">{st_data['risk_icon']} {st_data['risk_name']}</span><br>
                <b>世代進度：</b>完成 {st_data['generations_completed']} 世代 ({st_data['progress_pct']}%)
                <hr style="margin:6px 0; border-top:1px solid #e0e0e0;">
                <div style="background:#f0f6fd; padding:6px; border-radius:4px; font-size:11px; border-left:3px solid #0f5b9e;">
                    <b>💡 防治指引：</b>{st_data['advice']}
                </div>
            </div>
        </div>
        """

        folium.CircleMarker(
            location=[st_data["lat"], st_data["lon"]],
            radius=11,
            popup=folium.Popup(popup_html, max_width=280),
            tooltip=f"{st_data['risk_icon']} {st_data['name']} ({st_data['cumulative_gdd']} GDD | {st_data['latest_tmin']}~{st_data['latest_tmax']}°C)",
            color="#003366",
            fill=True,
            fill_color=color_hex,
            fill_opacity=0.9,
            weight=2
        ).add_to(m)

    st_folium(m, height=540, width=None, key="cwa_taiwan_map")

with grid_col:
    st.markdown("### 🏛️ 觀測站預報與積溫現況")
    
    # CWA 網格視圖卡片
    cards_list = ["<div class='cwa-card-grid'>"]
    for st_data in filtered_summaries:
        bg_badge = st_data["risk_hex"]
        card = (
            f'<div class="cwa-county-card">'
            f'<div class="cwa-card-header">'
            f'<div class="cwa-card-title">{st_data["risk_icon"]} {st_data["name"]}</div>'
            f'<div class="cwa-temp-tag"><span style="color:#d9534f;">{st_data["latest_tmax"]}°</span> / <span style="color:#0275d8;">{st_data["latest_tmin"]}°C</span></div>'
            f'</div>'
            f'<div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.85rem; color: #495057; margin-bottom: 8px;">'
            f'<span>縣市：<b>{st_data["county"]} {st_data["town"]}</b></span>'
            f'<span class="cwa-gdd-badge" style="background-color: {bg_badge}; color: white;">{st_data["cumulative_gdd"]} GDD</span>'
            f'</div>'
            f'<div style="font-size: 0.82rem; color: #6c757d; line-height: 1.4; background-color: #f8fafc; padding: 8px; border-radius: 6px;">'
            f'<b>{st_data["risk_name"]}</b>：{st_data["advice"][:36]}...'
            f'</div>'
            f'</div>'
        )
        cards_list.append(card)
    cards_list.append("</div>")
    
    st.markdown("".join(cards_list), unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# 9. 觀測站詳細分析與 Plotly 趨勢儀表板 (CWA 官方頁籤樣式)
st.markdown("### 📊 觀測站 30 天氣象與 GDD 累積趨勢深研")

col_select, col_space = st.columns([1, 2])
with col_select:
    station_options = [s["name"] for s in all_summaries]
    selected_st_name = st.selectbox("選擇分析觀測站：", station_options, index=1) # 預設選西螺

selected_st = next(s for s in all_summaries if s["name"] == selected_st_name)
trend_df = dm.get_station_trend(selected_st["station_id"])

# 測站重點 Card
st.markdown(f"""
<div style="background: white; border: 1px solid #d9e6f2; border-left: 6px solid {selected_st['risk_hex']}; padding: 14px 20px; border-radius: 8px; margin-bottom: 16px;">
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <span style="font-size: 1.25rem; font-weight: 800; color: #003366;">
            {selected_st['name']}觀測站 ({selected_st['county']} {selected_st['town']})
        </span>
        <span style="background: {selected_st['risk_hex']}; color: white; padding: 4px 14px; border-radius: 20px; font-weight: 700; font-size: 0.9rem;">
            {selected_st['risk_icon']} {selected_st['risk_name']} ({selected_st['cumulative_gdd']} GDD)
        </span>
    </div>
    <div style="font-size: 0.9rem; color: #495057; margin-top: 8px;">
        <b>世代進度：</b>完成 {selected_st['generations_completed']} 世代 ｜ <b>距離下一爆發期剩餘：</b>{selected_st['gdd_to_next_peak']} GDD
    </div>
</div>
""", unsafe_allow_html=True)

# Tabs
tab_gdd, tab_temp, tab_table = st.tabs(["📈 30天積溫累積趨勢", "🌡️ 每日極溫變化起伏", "📋 歷史氣象與 GDD 數據表"])

with tab_gdd:
    fig_gdd = make_subplots(specs=[[{"secondary_y": True}]])
    
    # 累積 GDD 曲線
    fig_gdd.add_trace(
        go.Scatter(
            x=trend_df["date"],
            y=trend_df["cumulative_gdd_trend"],
            name="30天累積 GDD",
            mode="lines+markers",
            line=dict(color="#004488", width=3),
            marker=dict(size=6, color="#0f5b9e")
        ),
        secondary_y=False
    )
    
    # 單日 GDD 柱狀圖
    fig_gdd.add_trace(
        go.Bar(
            x=trend_df["date"],
            y=trend_df["daily_gdd"],
            name="單日 GDD",
            marker_color="rgba(15, 91, 158, 0.25)"
        ),
        secondary_y=True
    )

    # 300 GDD 門檻線
    fig_gdd.add_hline(
        y=GENERATION_GDD,
        line_dash="dash",
        line_color="#d9534f",
        annotation_text="單世代門檻 (300 GDD)",
        annotation_position="top left",
        secondary_y=False
    )

    fig_gdd.update_layout(
        height=360,
        margin=dict(l=20, r=20, t=30, b=20),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)"
    )
    fig_gdd.update_xaxes(title="日期", showgrid=True, gridcolor="#edf3f8")
    fig_gdd.update_yaxes(title_text="累積 GDD", secondary_y=False, showgrid=True, gridcolor="#edf3f8")
    fig_gdd.update_yaxes(title_text="單日 GDD", secondary_y=True, showgrid=False)
    
    st.plotly_chart(fig_gdd, use_container_width=True)

with tab_temp:
    fig_temp = go.Figure()
    fig_temp.add_trace(
        go.Scatter(
            x=trend_df["date"],
            y=trend_df["t_max"],
            name="當日最高溫 Tmax (°C)",
            line=dict(color="#d9534f", width=2.5)
        )
    )
    fig_temp.add_trace(
        go.Scatter(
            x=trend_df["date"],
            y=trend_df["t_min"],
            name="當日最低溫 Tmin (°C)",
            line=dict(color="#0275d8", width=2.5),
            fill="tonexty",
            fillcolor="rgba(2, 117, 216, 0.12)"
        )
    )
    fig_temp.add_hline(
        y=T_BASE,
        line_dash="dot",
        line_color="#6c757d",
        annotation_text=f"發育門檻溫 Tbase ({T_BASE}°C)"
    )
    fig_temp.update_layout(
        height=360,
        margin=dict(l=20, r=20, t=30, b=20),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)"
    )
    fig_temp.update_xaxes(title="日期", showgrid=True, gridcolor="#edf3f8")
    fig_temp.update_yaxes(title="氣溫 (°C)", showgrid=True, gridcolor="#edf3f8")
    
    st.plotly_chart(fig_temp, use_container_width=True)

with tab_table:
    show_df = trend_df[["date", "t_max", "t_min", "daily_gdd", "cumulative_gdd_trend", "is_simulated"]].copy()
    show_df.columns = ["日期", "最高溫(°C)", "最低溫(°C)", "單日GDD", "30天累積GDD", "歷史模擬標記"]
    
    st.dataframe(show_df, use_container_width=True, height=260)
    
    csv_bytes = show_df.to_csv(index=False, encoding="utf-8-sig")
    st.download_button(
        label=f"📥 下載 {selected_st['name']} 30 天數據 CSV",
        data=csv_bytes,
        file_name=f"{selected_st['station_id']}_{selected_st['name']}_cwa_gdd.csv",
        mime="text/csv"
    )

# 10. CWA 官方風格頁尾
st.markdown("---")
st.markdown("""
<div style="background-color: #003366; color: #b0c4de; padding: 24px; text-align: center; border-radius: 8px; font-size: 0.85rem; line-height: 1.8;">
    <b>小菜蛾有效積溫全台監測與地圖預報系統</b><br>
    本系統採用小菜蛾 (Diamondback moth) 發育門檻 6.3°C 與 30 天滑動視窗累積積溫演算法 ｜ 氣象觀測資料源自 CWA Open Data API<br>
    © 2026 Diamondback Moth GDD Early Warning Map System. All Rights Reserved.
</div>
""", unsafe_allow_html=True)
