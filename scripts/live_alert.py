#!/usr/bin/env python3
"""
Cloud-ready Real-time Beijing (PEK / PKX) Aviation Spotter Alert Monitor.
Zero third-party dependencies (pure Python 3 stdlib).
"""

import argparse
import json
import math
import os
import smtplib
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from email.header import Header
from email.mime.text import MIMEText
from email.utils import formataddr

from zh_l10n import zh_aircraft, zh_airline, zh_livery, zh_origin

CST = timezone(timedelta(hours=8))
BEIJING_LAT = 39.9042
BEIJING_LON = 116.4074

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Origin": "https://www.flightradar24.com",
    "Referer": "https://www.flightradar24.com/",
}

ULTRA_VIP_CALLSIGN_PREFIXES = (
    "AF1", "AF2", "AIRFORCE1", "EXEC1", "SAM", "VENUS",
    "RSD", "GAF", "COTAM", "JPN001", "JPN002", "JF001", "JF002",
    "KAF001", "KAF002", "KRH", "RRR", "CFC01", "SUI", "AME", "IAM",
    "FAB01", "ASY", "CCA001", "CCA002", "CCA003", "CCA004", "CCA005",
    "CCA006", "CCA007", "CCA008", "CCA009", "B2479",
)

GOV_MIL_CALLSIGN_PREFIXES = ULTRA_VIP_CALLSIGN_PREFIXES + (
    "SPAR", "PAT", "RCH", "CNV", "LAGR", "PLF", "CEF", "HUAF", "ROF", "SVF",
    "FIN", "NOW", "DAF", "NAF", "BAF", "MMF", "BRK", "IAF", "KAF", "SGR",
    "RMAF", "RTAF", "RSAF", "QAF", "UAE00", "UAF", "SVA00", "HZHM", "KAC00",
    "EGY", "TUN", "MAR", "KZR00", "UZB00", "AZG", "BRU", "PKF", "BGD",
)

ULTRA_RARE_TYPES = {
    "A124": "安东诺夫 An-124 巨型战略运输机",
    "A225": "安东诺夫 An-225",
    "IL96": "伊留申 Il-96 俄制四发专机/宽体机",
    "IL62": "伊留申 Il-62 绝版俄制四发机",
    "MD11": "麦道 MD-11 罕见三发宽体机",
    "DC10": "麦道 DC-10 罕见三发宽体机",
    "B74S": "波音 747SP 绝版短体四发机",
    "B742": "波音 747-200 / VC-25 / E-4B 经典四发特种机",
    "B743": "波音 747-300 绝版四发机",
    "A345": "空客 A340-500 罕见四发远程宽体机",
    "A346": "空客 A340-600 罕见超长四发宽体机",
    "A3ST": "空客 Beluga 大白鲸特种运输机",
    "A337": "空客 BelugaXL 大白鲸XL特种运输机",
    "BLCF": "波音 747 Dreamlifter 巨型特种货机",
    "C5M": "洛克希德 C-5M 银河战略运输机",
    "C5": "洛克希德 C-5 银河战略运输机",
    "C17": "波音 C-17 环球霸王战略运输机",
    "VC25": "波音 VC-25 空军一号",
    "E4B": "波音 E-4B 末日飞机",
    "C32A": "波音 C-32A 空军二号",
    "E3CF": "波音 E-3 预警机",
    "B703": "波音 707 绝版经典四发机",
}

RARE_POPUP_TYPES = {
    "A388": "空客 A380-800 双层巨无霸",
    "B748": "波音 747-8 珍稀四发巨无霸",
    "B744": "波音 747-400 经典四发巨无霸",
    "A343": "空客 A340-300 罕见四发宽体机",
    "A342": "空客 A340-200 罕见四发宽体机",
    "IL76": "伊留申 Il-76 俄制重型运输机",
    "T204": "图波列夫 Tu-204 俄制客/货机",
    "T214": "图波列夫 Tu-214 俄制特种/客机",
    "A310": "空客 A310 罕见经典宽体机",
    "A306": "空客 A300-600 经典宽体机",
    "A338": "空客 A330-800neo 极罕见宽体机",
    "A339": "空客 A330-900neo 少见新一代宽体机",
    "A35K": "空客 A350-1000 旗舰大型宽体机",
    "B753": "波音 757-300 罕见加长757",
    "B764": "波音 767-400ER 罕见767子型号",
}

LARGE_VIP_BIZJET_TYPES = {
    "G650", "GLF6", "G700", "GL7T", "GLEX", "GL6T", "FA7X", "FA8X", "ACJ", "BBJ",
}

VIP_OWNER_KEYWORDS = (
    "government", "air force", "armed forces", "state aviation", "royal flight",
    "royal air force", "presidential", "ministry", "defense", "defence",
    "special flight", "republic of",
)

KNOWN_SPECIAL_LIVERIES = {
    "B-2006": "国航「爱China」彩绘 (B777-300ER)",
    "B-2032": "国航「微笑中国」彩绘 (B777-300ER)",
    "B-2047": "国航「星空联盟」涂装 (B777-300ER)",
    "B-308M": "国航「世园号」彩绘 (A350-900)",
    "B-1083": "国航「爱China」彩绘 (A350-900)",
    "B-919X": "国航首架五星红旗涂装 C919",
    "B-2002": "东航「进博号 CIIE」彩绘 (B777-300ER)",
    "B-919A": "东航全球首架交付 C919",
    "B-301D": "川航「熊猫之路」彩绘 (A350-900)",
    "B-304V": "川航「熊猫之路」彩绘 (A350-900)",
    "B-304U": "川航「熊猫之路」彩绘 (A350-900)",
    "B-306N": "川航「大运号」彩绘 (A350-900)",
    "B-1356": "厦航「联合梦想号」彩绘 (B787-9)",
    "B-209R": "吉祥航空「绚彩花瓣」彩绘 (B787-9)",
    "B-207N": "吉祥航空「梦旅生花」彩绘 (B787-9)",
    "B-208A": "吉祥航空「丝路飘带」彩绘 (B787-9)",
    "B-20D1": "吉祥航空「中国牡丹」彩绘 (B787-9)",
    "B-20EC": "吉祥航空「原神号」彩绘 (B787-9)",
    "B-1111": "上航「第100架飞机」彩绘 (B787-9)",
    "PH-BVA": "荷航「Orange Pride 橙色骄傲」彩绘 (B777-300ER)",
    "JA894A": "全日空 ANA「皮卡丘」彩绘 (B787-9)",
    "B-18101": "中华航空「皮卡丘」彩绘 (A321neo)",
}

ULTRA_VIP_REGS = {"B-2479", "82-8000", "92-9000", "73-1676", "73-1677", "74-0787", "75-0125"}


def beijing_sunrise_sunset(dt_cst: datetime) -> tuple[datetime, datetime]:
    day_of_year = dt_cst.timetuple().tm_yday
    lat_rad = math.radians(BEIJING_LAT)
    gamma = 2.0 * math.pi / 365.0 * (day_of_year - 1)
    eqtime = 229.18 * (
        0.000075
        + 0.001868 * math.cos(gamma)
        - 0.032077 * math.sin(gamma)
        - 0.014615 * math.cos(2 * gamma)
        - 0.040849 * math.sin(2 * gamma)
    )
    decl = (
        0.006918
        - 0.399912 * math.cos(gamma)
        + 0.070257 * math.sin(gamma)
        - 0.006758 * math.cos(2 * gamma)
        + 0.000907 * math.sin(2 * gamma)
        - 0.002697 * math.cos(3 * gamma)
        + 0.00148 * math.sin(3 * gamma)
    )
    cos_ha = (math.cos(math.radians(90.833)) / (math.cos(lat_rad) * math.cos(decl))) - (
        math.tan(lat_rad) * math.tan(decl)
    )
    cos_ha = max(-1.0, min(1.0, cos_ha))
    ha_deg = math.degrees(math.acos(cos_ha))
    sunrise_utc_min = 720.0 - 4.0 * (BEIJING_LON + ha_deg) - eqtime
    sunset_utc_min = 720.0 - 4.0 * (BEIJING_LON - ha_deg) - eqtime
    midnight_cst = dt_cst.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=CST)
    return (
        midnight_cst + timedelta(minutes=sunrise_utc_min + 480.0),
        midnight_cst + timedelta(minutes=sunset_utc_min + 480.0),
    )


def is_within_shootable_window(eta_cst: datetime) -> tuple[bool, datetime, datetime]:
    sunrise, sunset = beijing_sunrise_sunset(eta_cst)
    return ((sunrise - timedelta(hours=1)) < eta_cst < (sunset + timedelta(hours=1))), sunrise, sunset


def http_get_json(url: str, timeout: int = 15) -> dict:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def load_state(state_file: str) -> dict:
    if not os.path.exists(state_file):
        return {"notified": {}}
    try:
        with open(state_file, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) and "notified" in data else {"notified": {}}
    except Exception:
        return {"notified": {}}


def save_state(state_file: str, state: dict) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(state_file)), exist_ok=True)
    cutoff = time.time() - 18 * 3600
    state["notified"] = {
        k: v for k, v in state.get("notified", {}).items() if v.get("ts", 0) >= cutoff
    }
    with open(state_file, "w", encoding="utf-8") as fh:
        json.dump(state, fh, ensure_ascii=False, indent=2)


def load_daily_forecast_keys(forecast_file: str, today_str: str) -> set[str]:
    keys = set()
    if not os.path.exists(forecast_file):
        return keys
    try:
        with open(forecast_file, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if data.get("target_date") != today_str:
            return keys
        for ap_data in (data.get("airports") or {}).values():
            for cat in ("special_liveries", "special_aircraft", "vip_or_unusual"):
                for item in ap_data.get(cat) or []:
                    flt = (item.get("flight_number") or "").upper()
                    reg = (item.get("registration") or "").upper()
                    if flt:
                        keys.add(f"FLT:{flt}")
                    if flt and reg:
                        keys.add(f"FLTR:{flt}:{reg}")
    except Exception:
        pass
    return keys


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def matches_prefix(callsign: str, prefixes: tuple[str, ...]) -> bool:
    cs = (callsign or "").strip().upper()
    return bool(cs) and any(cs.startswith(p) for p in prefixes)


def is_comac_factory_aircraft(ac_code: str, reg: str, airline: str = "", owner: str = "", callsign: str = "", flt: str = "") -> bool:
    ac = (ac_code or "").upper()
    r = (reg or "").upper()
    cs = (callsign or "").upper()
    op = f"{airline or ''} {owner or ''}".lower()
    if r.startswith(("B-001", "B-002")) or cs.startswith(("COMAC", "B001", "B002")):
        return True
    if ac in {"C919", "C929"}:
        if "comac" in op or "commercial aircraft corporation" in op or "商飞" in op:
            return True
        if not flt and r.startswith(("B-658", "B-659", "B-919")) and not any(
            k in op for k in ("air china", "china eastern", "china southern")
        ):
            return True
    return False


def scan_fr24_live_arrivals(now_cst: datetime, forecast_keys: set[str]) -> list[dict]:
    alerts = []
    now_ts = int(now_cst.timestamp())
    for ap in ("PEK", "PKX"):
        for page in (1, 2):
            params = urllib.parse.urlencode({
                "code": ap.lower(),
                "plugin[]": "schedule",
                "plugin-setting[schedule][mode]": "arrivals",
                "plugin-setting[schedule][timestamp]": str(now_ts - 1800),
                "limit": "100",
                "page": str(page),
            })
            url = f"https://api.flightradar24.com/common/v1/airport.json?{params}"
            try:
                payload = http_get_json(url, timeout=15)
                rows = payload["result"]["response"]["airport"]["pluginData"]["schedule"]["arrivals"]["data"] or []
            except Exception:
                break

            for row in rows:
                f = row.get("flight") or {}
                status = f.get("status") or {}
                is_live = bool(status.get("live"))
                status_text = status.get("text") or ""
                generic_status = (status.get("generic") or {}).get("status") or {}
                diverted = bool(generic_status.get("diverted")) or ("divert" in status_text.lower())

                time_info = f.get("time") or {}
                eta_ts = (time_info.get("estimated") or {}).get("arrival") or (time_info.get("scheduled") or {}).get("arrival")
                if not eta_ts or generic_status.get("text") == "landed":
                    continue
                if not is_live and not diverted and (eta_ts < now_ts - 600 or eta_ts > now_ts + 4 * 3600):
                    continue

                eta_cst = datetime.fromtimestamp(eta_ts, tz=CST)
                ident = f.get("identification") or {}
                flt = ((ident.get("number") or {}).get("default") or "").upper()
                callsign = (ident.get("callsign") or "").upper()
                ac = f.get("aircraft") or {}
                ac_code = ((ac.get("model") or {}).get("code") or "").upper()
                ac_text = (ac.get("model") or {}).get("text") or ""
                reg = (ac.get("registration") or "").upper()
                hex_code = (ac.get("hex") or "").upper()
                restricted = bool(ac.get("restricted"))
                airline_obj = f.get("airline") or {}
                airline_name = airline_obj.get("name") or ""
                airline_iata = ((airline_obj.get("code") or {}).get("iata") or "").upper()
                owner_name = (f.get("owner") or {}).get("name") or ""
                origin = (f.get("airport") or {}).get("origin") or {}
                origin_iata = ((origin.get("code") or {}).get("iata") or "").upper()
                origin_pos = origin.get("position") or {}
                origin_city = (origin_pos.get("region") or {}).get("city") or ""
                origin_country = (origin_pos.get("country") or {}).get("name") or ""

                reasons, category, is_ultra = [], None, False
                if matches_prefix(callsign, ULTRA_VIP_CALLSIGN_PREFIXES) or reg in ULTRA_VIP_REGS:
                    reasons.append(f"🚨 顶级专机呼号/注册号 ({callsign or reg})")
                    category, is_ultra = "VIP_ULTRA", True
                if ac_code in ULTRA_RARE_TYPES:
                    reasons.append(f"🚨 殿堂级极稀有机型: {ULTRA_RARE_TYPES[ac_code]}")
                    category, is_ultra = category or "RARE_ULTRA", True
                if is_comac_factory_aircraft(ac_code, reg, airline_name, owner_name, callsign, flt):
                    reasons.append(f"🚨 中国商飞 COMAC 自持/试飞演示机 ({reg or callsign or ac_code})")
                    category, is_ultra = category or "RARE_ULTRA", True
                if diverted:
                    reasons.append(f"🔀 突发备降 {ap} ({status_text})")
                    category = category or "DIVERSION"

                combined_op = (airline_name + " " + owner_name).lower()
                if matches_prefix(callsign, GOV_MIL_CALLSIGN_PREFIXES) or any(k in combined_op for k in VIP_OWNER_KEYWORDS):
                    if not is_ultra:
                        reasons.append("🏛️ 政府/军政/外事专机特征")
                        category = category or "VIP_GOV"
                elif (restricted or (not flt and is_live)) and (ac_code in LARGE_VIP_BIZJET_TYPES or ac_code in RARE_POPUP_TYPES or ac_code in ULTRA_RARE_TYPES):
                    reasons.append("🛩️ 无商业航班号/受限大型专机或公务机")
                    category = category or "VIP_GOV"

                livery_desc = ""
                if "(" in airline_name:
                    s_i = airline_name.find("(") + 1
                    e_i = airline_name.rfind(")")
                    p_txt = (airline_name[s_i:e_i] if e_i > s_i else airline_name[s_i:]).strip()
                    if p_txt and p_txt.lower() not in {"cargo", "express", "regional"}:
                        livery_desc = p_txt
                elif reg in KNOWN_SPECIAL_LIVERIES:
                    livery_desc = KNOWN_SPECIAL_LIVERIES[reg]

                already_forecasted = (f"FLTR:{flt}:{reg}" in forecast_keys) if (flt and reg) else (f"FLT:{flt}" in forecast_keys)
                if livery_desc and is_live and not already_forecasted:
                    reasons.append(f"🎨 临期上线/新增彩绘: {zh_livery(livery_desc)}")
                    category = category or "LIVERY_POPUP"
                if ac_code in RARE_POPUP_TYPES and is_live and not already_forecasted:
                    reasons.append(f"✈️ 临期/新增稀有机型: {RARE_POPUP_TYPES[ac_code]}")
                    category = category or "RARE_POPUP"

                if reasons:
                    utc_date = now_cst.astimezone(timezone.utc).strftime("%Y-%m-%d")
                    fid = (ident.get("id") or "")
                    fr24_link = (
                        f"https://www.flightradar24.com/{callsign or flt}/{fid}"
                        if (callsign or flt) and fid
                        else (f"https://www.flightradar24.com/data/aircraft/{reg.lower()}" if reg else f"https://www.flightradar24.com/{callsign or flt}")
                    )
                    adsb_link = f"https://globe.adsb.lol/?icao={hex_code.lower()}&showTrace={utc_date}" if hex_code else ""
                    alerts.append({
                        "dedup_key": f"FR24ARR:{ap}:{flt or callsign}:{reg}:{eta_cst.strftime('%Y-%m-%d')}",
                        "source": "FR24 实时到港",
                        "airport": ap,
                        "category": category,
                        "is_ultra": is_ultra,
                        "eta_cst": eta_cst,
                        "eta_str": eta_cst.strftime("%H:%M"),
                        "flight": flt or callsign or "N/A",
                        "airline": zh_airline(airline_name, airline_iata, owner_name),
                        "origin": zh_origin(origin_iata, origin_city, origin_country),
                        "aircraft": zh_aircraft(ac_text, ac_code),
                        "registration": reg,
                        "status": status_text or ("飞行中" if is_live else "计划"),
                        "reasons": reasons,
                        "fr24_url": fr24_link,
                        "adsb_url": adsb_link,
                    })
    return alerts


def scan_fr24_live_radar(now_cst: datetime, forecast_keys: set[str]) -> list[dict]:
    alerts = []
    url = (
        "https://data-cloud.flightradar24.com/zones/fcgi/feed.js"
        "?bounds=52,22,85,135&faa=1&satellite=1&mlat=1&flarm=1&adsb=1"
        "&gnd=0&air=1&vehicles=0&estimated=1&maxage=14400&gliders=0&stats=0"
    )
    try:
        feed = http_get_json(url, timeout=15)
    except Exception:
        return alerts

    for fid, v in feed.items():
        if not isinstance(v, list) or len(v) < 17:
            continue
        hex_code = str(v[0] or "").upper()
        lat, lon = float(v[1] or 0), float(v[2] or 0)
        alt_ft, gs_kt = int(v[4] or 0), int(v[5] or 0)
        squawk = str(v[6] or "")
        ac_code, reg = str(v[8] or "").upper(), str(v[9] or "").upper()
        orig, dest = str(v[11] or "").upper(), str(v[12] or "").upper()
        flt, vspeed = str(v[13] or "").upper(), int(v[15] or 0)
        callsign = str(v[16] or "").strip().upper()

        dist_km = haversine_km(lat, lon, BEIJING_LAT, BEIJING_LON)
        heading_to_bjs = dest in {"PEK", "PKX"}
        approaching_unlisted = (not dest) and dist_km <= 180 and alt_ft <= 26000 and vspeed <= -200
        if not heading_to_bjs and not approaching_unlisted:
            continue

        eta_hours = (dist_km / max(gs_kt * 1.852, 350.0)) if dist_km > 25 else 0.1
        eta_cst = now_cst + timedelta(hours=min(eta_hours, 12.0))

        reasons, category, is_ultra = [], None, False
        if squawk == "7700" and dist_km <= 300:
            reasons.append("🆘 挂出 7700 紧急代码（可能在京津冀区域紧急备降）")
            category, is_ultra = "EMERGENCY", True
        if matches_prefix(callsign, ULTRA_VIP_CALLSIGN_PREFIXES) or reg in ULTRA_VIP_REGS:
            reasons.append(f"🚨 顶级专机实时在空 ({callsign or reg})")
            category, is_ultra = category or "VIP_ULTRA", True
        if ac_code in ULTRA_RARE_TYPES:
            reasons.append(f"🚨 殿堂级极稀有机型实时在空: {ULTRA_RARE_TYPES[ac_code]}")
            category, is_ultra = category or "RARE_ULTRA", True
        if is_comac_factory_aircraft(ac_code, reg, "", "", callsign, flt):
            reasons.append(f"🚨 中国商飞 COMAC 自持/试飞演示机实时在空 ({reg or callsign})")
            category, is_ultra = category or "RARE_ULTRA", True
        if not is_ultra and matches_prefix(callsign, GOV_MIL_CALLSIGN_PREFIXES):
            reasons.append(f"🏛️ 政府/军政呼号实时进京 ({callsign})")
            category = category or "VIP_GOV"
        if not is_ultra and approaching_unlisted and ac_code in LARGE_VIP_BIZJET_TYPES:
            reasons.append(f"🛩️ 未上时刻表大型公务/专机向北京下降 ({ac_code}, 距京 {int(dist_km)}km)")
            category = category or "VIP_GOV"

        already_forecasted = (f"FLTR:{flt}:{reg}" in forecast_keys) if (flt and reg) else (f"FLT:{flt}" in forecast_keys)
        if reg in KNOWN_SPECIAL_LIVERIES and not already_forecasted:
            reasons.append(f"🎨 临期彩绘实时在空: {KNOWN_SPECIAL_LIVERIES[reg]}")
            category = category or "LIVERY_POPUP"

        if reasons:
            utc_date = now_cst.astimezone(timezone.utc).strftime("%Y-%m-%d")
            fr24_link = (
                f"https://www.flightradar24.com/{callsign or flt}/{fid}"
                if (callsign or flt)
                else (f"https://www.flightradar24.com/data/aircraft/{reg.lower()}" if reg else "")
            )
            adsb_link = f"https://globe.adsb.lol/?icao={hex_code.lower()}&showTrace={utc_date}" if hex_code else ""
            alerts.append({
                "dedup_key": f"LIVE:{hex_code or callsign}:{reg}:{now_cst.strftime('%Y-%m-%d')}",
                "source": "FR24 实时雷达",
                "airport": dest if heading_to_bjs else "PEK/PKX(进近)",
                "category": category,
                "is_ultra": is_ultra,
                "eta_cst": eta_cst,
                "eta_str": f"约 {eta_cst.strftime('%H:%M')}",
                "flight": flt or callsign or hex_code,
                "airline": "实时雷达目标",
                "origin": orig or "未知",
                "aircraft": ac_code or "未知",
                "registration": reg or hex_code,
                "status": f"距京 {int(dist_km)}km · 高度 {alt_ft}ft · 速度 {gs_kt}kt",
                "reasons": reasons,
                "fr24_url": fr24_link,
                "adsb_url": adsb_link,
            })
    return alerts


def scan_adsb_lol(now_cst: datetime) -> list[dict]:
    alerts = []
    try:
        data = http_get_json(f"https://api.adsb.lol/v2/point/{BEIJING_LAT}/{BEIJING_LON}/150", timeout=15)
    except Exception:
        return alerts

    for ac in data.get("ac") or []:
        hex_code = str(ac.get("hex") or "").upper()
        callsign = str(ac.get("flight") or "").strip().upper()
        reg = str(ac.get("r") or "").upper()
        ac_type = str(ac.get("t") or "").upper()
        desc = str(ac.get("desc") or "")
        owner = str(ac.get("ownOp") or "")
        alt = ac.get("alt_baro")
        alt_ft = int(alt) if isinstance(alt, (int, float)) else 0
        gs = ac.get("gs") or 0
        baro_rate = ac.get("baro_rate") or 0
        dist_km = float(ac.get("dst") or 999) * 1.852
        is_mil = bool(int(ac.get("dbFlags") or 0) & 1)
        squawk = str(ac.get("squawk") or "")

        is_low = (alt_ft <= 26000) or (baro_rate <= -300)
        reasons, category, is_ultra = [], None, False

        if squawk == "7700":
            reasons.append("🆘 挂出 7700 紧急代码（adsb.lol 实时捕获）")
            category, is_ultra = "EMERGENCY", True
        if matches_prefix(callsign, ULTRA_VIP_CALLSIGN_PREFIXES) or reg in ULTRA_VIP_REGS:
            reasons.append(f"🚨 顶级元首/空军一号级专机现身北京空域 ({callsign or reg})")
            category, is_ultra = category or "VIP_ULTRA", True
        if ac_type in ULTRA_RARE_TYPES:
            reasons.append(f"🚨 殿堂级极稀有机型现身北京空域: {ULTRA_RARE_TYPES[ac_type]}")
            category, is_ultra = category or "RARE_ULTRA", True
        if is_comac_factory_aircraft(ac_type, reg, "", owner, callsign, ""):
            reasons.append(f"🚨 中国商飞 COMAC 自持/试飞演示机现身北京空域 ({reg or callsign})")
            category, is_ultra = category or "RARE_ULTRA", True
        if not is_ultra and is_low:
            if is_mil or matches_prefix(callsign, GOV_MIL_CALLSIGN_PREFIXES) or any(k in owner.lower() for k in VIP_OWNER_KEYWORDS):
                reasons.append(f"🏛️ 军政/外交/未屏蔽专机进入北京进近空域 (军政标志={is_mil})")
                category = category or "VIP_GOV"
            elif ac_type in RARE_POPUP_TYPES and dist_km <= 120:
                reasons.append(f"✈️ 稀有机型低空进近北京: {RARE_POPUP_TYPES[ac_type]}")
                category = category or "RARE_POPUP"

        if reasons:
            eta_hours = (dist_km / max(float(gs) * 1.852, 350.0)) if dist_km > 20 else 0.08
            eta_cst = now_cst + timedelta(hours=min(eta_hours, 4.0))
            utc_date = now_cst.astimezone(timezone.utc).strftime("%Y-%m-%d")
            adsb_link = f"https://globe.adsb.lol/?icao={hex_code.lower()}&showTrace={utc_date}" if hex_code else "https://globe.adsb.lol/"
            fr24_link = f"https://www.flightradar24.com/data/aircraft/{reg.lower()}" if reg else ""
            alerts.append({
                "dedup_key": f"LIVE:{hex_code or callsign}:{reg}:{now_cst.strftime('%Y-%m-%d')}",
                "source": "adsb.lol 未屏蔽雷达",
                "airport": "北京空域 (PEK/PKX)",
                "category": category,
                "is_ultra": is_ultra,
                "eta_cst": eta_cst,
                "eta_str": f"约 {eta_cst.strftime('%H:%M')}",
                "flight": callsign or reg or hex_code,
                "airline": owner or ("军政/特种航空器" if is_mil else "未公开运营商"),
                "origin": f"距京 {int(dist_km)} km",
                "aircraft": f"{ac_type} {desc}".strip() or "未知机型",
                "registration": reg or f"HEX:{hex_code}",
                "status": f"高度 {alt_ft}ft · 升降率 {baro_rate}fpm · 地速 {int(gs)}kt",
                "reasons": reasons,
                "fr24_url": fr24_link,
                "adsb_url": adsb_link,
            })
    return alerts


def build_alert_html(alerts: list[dict], now_cst: datetime, sunrise: datetime, sunset: datetime) -> str:
    rows_html = []
    for a in alerts:
        bg = "#fef2f2" if a["is_ultra"] else "#fffbeb"
        badge = "🚨 极特殊/全天候直通" if a["is_ultra"] else "⚡ 拍机时段突发提醒"
        links = []
        if a.get("adsb_url"):
            links.append(f'<a href="{a["adsb_url"]}" style="color:#2563eb;font-size:12px;">adsb.lol 当日航迹 →</a>')
        if a.get("fr24_url"):
            links.append(f'<a href="{a["fr24_url"]}" style="color:#2563eb;font-size:12px;">FR24 追踪/档案 →</a>')
        links_html = " &nbsp;|&nbsp; ".join(links)
        rows_html.append(f"""
        <tr style="background-color:{bg};">
          <td style="border:1px solid #e2e8f0;padding:8px;"><strong>{a['eta_str']}</strong><br><span style="font-size:11px;color:#64748b;">{a['airport']}</span></td>
          <td style="border:1px solid #e2e8f0;padding:8px;"><strong>{a['flight']}</strong><br><span style="font-size:11px;color:#64748b;">{a['airline']}</span></td>
          <td style="border:1px solid #e2e8f0;padding:8px;">{a['aircraft']}<br><span style="color:#2563eb;">{a['registration']}</span></td>
          <td style="border:1px solid #e2e8f0;padding:8px;">{a['origin']}<br><span style="font-size:11px;color:#64748b;">{a['status']}</span></td>
          <td style="border:1px solid #e2e8f0;padding:8px;">
            <span style="display:inline-block;font-size:11px;padding:2px 6px;border-radius:4px;background:#fee2e2;color:#991b1b;margin-bottom:4px;">{badge}</span><br>
            {'<br>'.join(a['reasons'])}<br>
            {links_html}
          </td>
        </tr>""")
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="utf-8"><title>北京机场实时突发预警</title></head>
<body style="font-family:'Microsoft YaHei','PingFang SC',Arial,sans-serif;color:#1f2937;max-width:860px;margin:0 auto;padding:18px;background:#f8fafc;">
  <div style="background:#ffffff;border-radius:10px;padding:22px;border:1px solid #fecaca;">
    <h2 style="margin:0 0 8px 0;color:#991b1b;border-bottom:2px solid #dc2626;padding-bottom:8px;">
      🚨 北京机场（PEK / PKX）实时突发拍机预警
    </h2>
    <p style="margin:6px 0 16px 0;font-size:13px;color:#475569;">
      <strong>检测时间：</strong>{now_cst.strftime('%Y-%m-%d %H:%M')}（北京时间） &nbsp;|&nbsp;
      <strong>今日北京日出/日落：</strong>{sunrise.strftime('%H:%M')} / {sunset.strftime('%H:%M')}（可拍窗口 {(sunrise - timedelta(hours=1)).strftime('%H:%M')}–{(sunset + timedelta(hours=1)).strftime('%H:%M')}）
    </p>
    <table style="width:100%;border-collapse:collapse;font-size:13px;">
      <thead>
        <tr style="background:#fef2f2;color:#7f1d1d;">
          <th style="border:1px solid #fecaca;padding:8px;text-align:left;width:82px;">预计到港</th>
          <th style="border:1px solid #fecaca;padding:8px;text-align:left;">航班 / 运营方</th>
          <th style="border:1px solid #fecaca;padding:8px;text-align:left;">机型 / 注册号</th>
          <th style="border:1px solid #fecaca;padding:8px;text-align:left;">来源 / 动态</th>
          <th style="border:1px solid #fecaca;padding:8px;text-align:left;">触发原因与追踪</th>
        </tr>
      </thead>
      <tbody>{''.join(rows_html)}</tbody>
    </table>
    <p style="font-size:12px;color:#64748b;margin-top:14px;margin-bottom:0;">
      提示：云端自动预警（同一航班 18 小时内不重复提醒），实时航路与备降机场可能临时调整，请以实时雷达为准。
    </p>
  </div>
</body>
</html>"""


def send_email(subject: str, html_body: str, config_path: str | None = None) -> None:
    cfg = {}
    if config_path and os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as fh:
            cfg = json.load(fh)
    user = (os.environ.get("SMTP_163_USER") or cfg.get("user") or "").strip()
    auth_code = (os.environ.get("SMTP_163_AUTH_CODE") or cfg.get("auth_code") or "").strip()
    raw_recipients = (os.environ.get("ALERT_TO_EMAIL") or cfg.get("default_to") or user).strip()
    recipients = [r.strip() for r in raw_recipients.replace(";", ",").split(",") if r.strip()]
    host = os.environ.get("SMTP_HOST") or cfg.get("host") or "smtp.163.com"
    port = int(os.environ.get("SMTP_PORT") or cfg.get("port") or 465)
    if not user or not auth_code or not recipients:
        raise RuntimeError("Missing SMTP_163_USER / SMTP_163_AUTH_CODE / ALERT_TO_EMAIL")

    ctx = ssl.create_default_context()
    with smtplib.SMTP_SSL(host, port, context=ctx, timeout=25) as server:
        server.login(user, auth_code)
        for rcpt in recipients:
            msg = MIMEText(html_body, "html", "utf-8")
            msg["From"] = formataddr((str(Header("北京机场实时预警", "utf-8")), user))
            msg["To"] = rcpt
            msg["Subject"] = Header(subject, "utf-8")
            server.sendmail(user, [rcpt], msg.as_string())


def main() -> int:
    parser = argparse.ArgumentParser(description="Cloud Beijing PEK/PKX Live Alert Monitor")
    parser.add_argument("--state-dir", default="state", help="Directory for notified_state.json and arrivals.json")
    parser.add_argument("--smtp-config", help="Optional local smtp_config.json fallback")
    parser.add_argument("--dry-run", action="store_true", help="Scan without emailing or saving state")
    args = parser.parse_args()

    sys.stdout.reconfigure(encoding="utf-8")
    now_cst = datetime.now(CST)
    today_str = now_cst.strftime("%Y-%m-%d")
    sunrise, sunset = beijing_sunrise_sunset(now_cst)

    state_file = os.path.join(args.state_dir, "notified_state.json")
    forecast_file = os.path.join(args.state_dir, "arrivals.json")
    state = load_state(state_file)
    notified = state.get("notified", {})
    forecast_keys = load_daily_forecast_keys(forecast_file, today_str)

    raw_alerts = []
    raw_alerts.extend(scan_fr24_live_arrivals(now_cst, forecast_keys))
    raw_alerts.extend(scan_fr24_live_radar(now_cst, forecast_keys))
    raw_alerts.extend(scan_adsb_lol(now_cst))

    is_quiet_hours = (now_cst.hour >= 20) or (now_cst.hour < 8)
    merged = {}
    suppressed_dark = 0
    suppressed_quiet = 0
    for a in raw_alerts:
        key = a["dedup_key"]
        if key in notified:
            continue
        if is_quiet_hours and not a["is_ultra"]:
            suppressed_quiet += 1
            continue
        shootable, _, _ = is_within_shootable_window(a["eta_cst"])
        if not shootable and not a["is_ultra"]:
            suppressed_dark += 1
            continue
        if key not in merged:
            merged[key] = a
        else:
            for r in a["reasons"]:
                if r not in merged[key]["reasons"]:
                    merged[key]["reasons"].append(r)
            if a["is_ultra"]:
                merged[key]["is_ultra"] = True

    final_alerts = sorted(merged.values(), key=lambda x: (not x["is_ultra"], x["eta_cst"]))
    print(
        f"[{now_cst.strftime('%Y-%m-%d %H:%M:%S CST')}] "
        f"Beijing sunrise={sunrise.strftime('%H:%M')} sunset={sunset.strftime('%H:%M')} quiet={is_quiet_hours} | "
        f"raw={len(raw_alerts)}, suppressed_quiet={suppressed_quiet}, suppressed_dark={suppressed_dark}, to_notify={len(final_alerts)}"
    )

    if not final_alerts or args.dry_run:
        if args.dry_run and final_alerts:
            print("DRY_RUN: Email skipped.")
        return 0

    top_tag = "🚨 极特殊专机/机型" if any(a["is_ultra"] for a in final_alerts) else "⚡ 突发拍机预警"
    first_item = final_alerts[0]
    subject = f"{top_tag}｜{first_item['airport']} {first_item['flight']} ({first_item['aircraft']}) 等 {len(final_alerts)} 条动态"
    send_email(subject, build_alert_html(final_alerts, now_cst, sunrise, sunset), args.smtp_config)

    ts_now = time.time()
    for a in final_alerts:
        notified[a["dedup_key"]] = {"ts": ts_now, "flight": a["flight"], "airport": a["airport"]}
    state["notified"] = notified
    save_state(state_file, state)
    print(f"ALERT_EMAIL_SENT: {subject}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
