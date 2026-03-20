import requests
import pandas as pd
from datetime import datetime
from config import POLYGON_API_KEY, TZ_NY

def calculer_donnees_trade(ticker, date_trade):
    date_str = date_trade.strftime('%Y-%m-%d')
    
    # Fenêtres NY Time
    dt_start_pm = TZ_NY.localize(datetime.combine(date_trade, datetime.strptime("04:00", "%H:%M").time()))
    dt_end_pm = TZ_NY.localize(datetime.combine(date_trade, datetime.strptime("09:30", "%H:%M").time()))
    dt_start_hod = TZ_NY.localize(datetime.combine(date_trade, datetime.strptime("09:30", "%H:%M").time()))
    dt_end_hod = TZ_NY.localize(datetime.combine(date_trade, datetime.strptime("12:00", "%H:%M").time()))

    start_pm = int(dt_start_pm.timestamp() * 1000)
    end_pm = int(dt_end_pm.timestamp() * 1000)
    start_hod = int(dt_start_hod.timestamp() * 1000)
    end_hod = int(dt_end_hod.timestamp() * 1000)

    res = {
        "Prev_Close ($)": 0.0, "PM_High ($)": 0.0, "Open_9h30 ($)": 0.0, 
        "HOD ($)": 0.0, "LOD ($)": 0.0, "Gap to Open %": 0.0, 
        "HOD to LOD Drop %": 0.0, "HOD to PMH %": 0.0, "Heure HOD": ""
    }
    
    try:
        # 1. Daily Data
        url_day = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/day/{date_str}/{date_str}?adjusted=true&apiKey={POLYGON_API_KEY}"
        data_day = requests.get(url_day).json()
        if data_day.get("results"):
            d = data_day["results"][0]
            res["Open_9h30 ($)"] = d.get("o", 0)
            res["HOD ($)"] = d.get("h", 0)
            res["LOD ($)"] = d.get("l", 0)

        # 2. Previous Close
        url_prev = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/prev?adjusted=true&apiKey={POLYGON_API_KEY}"
        data_prev = requests.get(url_prev).json()
        if data_prev.get("results"):
            pc = data_prev["results"][0].get("c", 0)
            res["Prev_Close ($)"] = pc
            if pc > 0: res["Gap to Open %"] = round(((res["Open_9h30 ($)"] - pc) / pc) * 100, 2)

        # 3. Minute Data (PM & HOD)
        url_min = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/minute/{date_str}/{date_str}?adjusted=true&apiKey={POLYGON_API_KEY}"
        data_min = requests.get(url_min).json()
        if data_min.get("results"):
            bars = data_min["results"]
            pm_bars = [b for b in bars if start_pm <= b['t'] < end_pm]
            if pm_bars:
                res["PM_High ($)"] = max([b['h'] for b in pm_bars])
            
            session_bars = [b for b in bars if start_hod <= b['t'] <= end_hod]
            if session_bars:
                h_bar = max(session_bars, key=lambda b: b['h'])
                res["Heure HOD"] = datetime.fromtimestamp(h_bar['t'] / 1000, TZ_NY).strftime('%H:%M')

            if res["PM_High ($)"] > 0:
                res["HOD to PMH %"] = round(((res["HOD ($)"] - res["PM_High ($)"]) / res["PM_High ($)"]) * 100, 2)
            if res["HOD ($)"] > 0:
                res["HOD to LOD Drop %"] = round(((res["LOD ($)"] - res["HOD ($)"]) / res["HOD ($)"]) * 100, 2)
    except: pass
    return res
