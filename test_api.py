import sys
sys.stdout.reconfigure(encoding='utf-8')

from data_manager import GDDDataManager
dm = GDDDataManager()
summary = dm.get_all_summary()
for s in summary:
    tag = 'API真實' if not s['is_simulated'] else '模擬'
    print(f"{s['name']}: Tmax={s['latest_tmax']} Tmin={s['latest_tmin']} 30dGDD={s['cumulative_gdd']} [{tag}] {s['risk_name']}")
