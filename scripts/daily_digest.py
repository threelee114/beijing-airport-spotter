#!/usr/bin/env python3
"""
Cloud-ready Daily Beijing (PEK / PKX) Notable Arrivals & Special Liveries Digest.
Zero third-party dependencies (pure Python 3 stdlib).
"""

import argparse
import html
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
from collections import Counter
from datetime import datetime, timedelta, timezone
from email.header import Header
from email.mime.text import MIMEText
from email.utils import formataddr

from zh_l10n import zh_aircraft, zh_airline, zh_country, zh_livery, zh_origin

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

COMMON_CN_CARRIERS = {
    "CA", "MU", "CZ", "HU", "MF", "3U", "ZH", "SC", "FM", "HO", "9C", "GS",
    "KN", "EU", "JD", "GJ", "KY", "TV", "PN", "8L", "NS", "JR", "DZ", "QW",
    "FU", "G5", "AQ", "BK", "DR", "GX", "LT", "RY", "GT", "UQ", "Y2", "OQ",
    "CN", "9H", "A6", "GY",
}
COMMON_CN_SUBSIDIARIES = {"dalian airlines", "beijing airlines", "inner mongolia airlines"}

# Fix known FR24 IATA 2-letter airline code collisions on Beijing routes
FR24_AIRLINE_FIXES = {
    ("JL", "HND"): ("Japan Airlines (日本航空)", "JL", "JAL"),
    ("JL", "NRT"): ("Japan Airlines (日本航空)", "JL", "JAL"),
    ("MR", "UBN"): ("Hunnu Air (蒙古匈奴航空)", "MR", "MML"),
    ("HT", "CRK"): ("Tianjin Air Cargo (天津货运航空)", "HT", "CTJ"),
}

CARGO_KEYWORDS = (
    "cargo", "freight", "airbridge", "silk way", "cargolux", "polar air",
    "kalitta", "atlas air", "fedex", "ups", "dhl", "sf airlines", "central airlines",
    "yunda", "yto", "longhao", "suparna", "air china cargo", "china cargo",
    "china southern cargo", "china postal", "volga-dnepr", "aviacon", "my freighter",
    "aerotranscargo", "challenge", "nippon cargo", "korean air cargo", "lufthansa cargo",
    "air hong kong", "jdl airlines",
)

VIP_GOV_KEYWORDS = (
    "government", "air force", "armed forces", "state aviation", "royal flight",
    "royal air force", "royal squadron", "vip", "presidential", "ministry",
    "defense", "defence", "special flight", "executive", "private owner",
    "charter", "vista", "netjets", "deer jet", "sino jet", "tag aviation",
    "luxaviation", "execujet", "comlux", "amjet", "gulfstream", "bombardier",
    "dassault", "avcon", "bjet", "metrojet", "hongkong jet", "amber aviation",
    "minshen", "capital jet",
)

SPECIAL_LIVERY_KEYWORDS = (
    "livery", "sticker", "retro", "special", "panda", "star alliance",
    "skyteam", "oneworld", "expo", "olympic", "anniversary", "disney",
    "pokemon", "pikachu", "hello kitty", "peony", "phoenix", "ciie",
    "smiling", "love china", "winter games", "national games", "peacock",
    "museum", "wuliangye", "zhejiang", "sichuan livery", "city of",
)

KNOWN_SPECIAL_LIVERIES = {
    "B-2006": "国航「爱China」彩绘 (B777-300ER)",
    "B-2032": "国航「微笑中国 / Smiling China」彩绘 (B777-300ER)",
    "B-2047": "国航「星空联盟 Star Alliance」涂装 (B777-300ER)",
    "B-308M": "国航「世园号」彩绘 (A350-900)",
    "B-1083": "国航「爱China」彩绘 (A350-900)",
    "B-919X": "国航首架五星红旗涂装 C919",
    "B-2002": "东航「进博号 CIIE」彩绘 (B777-300ER)",
    "B-919A": "东航全球首架交付 C919（全球首架特别标识）",
    "B-301D": "川航「熊猫之路」彩绘 (A350-900)",
    "B-304V": "川航「熊猫之路」彩绘 (A350-900)",
    "B-304U": "川航「熊猫之路」彩绘 (A350-900)",
    "B-306N": "川航「大运号」彩绘 (A350-900)",
    "B-1356": "厦航「联合梦想号 UN SDGs」彩绘 (B787-9)",
    "B-209R": "吉祥航空「绚彩花瓣」彩绘 (B787-9)",
    "B-207N": "吉祥航空「梦旅生花」彩绘 (B787-9)",
    "B-208A": "吉祥航空「丝路飘带」彩绘 (B787-9)",
    "B-20D1": "吉祥航空「中国牡丹」彩绘 (B787-9)",
    "B-20EC": "吉祥航空「原神号」彩绘 (B787-9)",
    "B-1111": "上航「第100架飞机」特别彩绘 (B787-9)",
    "PH-BVA": "荷航「Orange Pride 橙色骄傲」彩绘 (B777-300ER)",
    "JA894A": "全日空 ANA「皮卡丘」彩绘 (B787-9)",
    "B-18101": "中华航空「皮卡丘」彩绘 (A321neo)",
}

# Routine daily East Asia / HK-TW carriers are lower priority unless rare aircraft or livery
ROUTINE_REGIONAL_CARRIERS = {"CX", "HX", "UO", "NX", "KE", "OZ", "NH", "JL", "BR", "CI", "SQ", "TG", "VN", "MH", "AK", "VJ", "S7"}

SPECIAL_AIRCRAFT_CODES = {
    "A388": "空客 A380-800 超大型双层宽体机",
    "388": "空客 A380-800 超大型双层宽体机",
    "B748": "波音 747-8 珍稀四发巨无霸",
    "748": "波音 747-8 珍稀四发巨无霸",
    "74N": "波音 747-8F 珍稀四发全货机",
    "B744": "波音 747-400 经典四发巨无霸",
    "744": "波音 747-400 经典四发巨无霸",
    "74Y": "波音 747-400F 经典四发全货机",
    "74F": "波音 747 全货机",
    "B742": "波音 747-200 经典老旧四发机",
    "B743": "波音 747-300 经典老旧四发机",
    "B74S": "波音 747SP 绝版短体四发机",
    "A346": "空客 A340-600 罕见四发宽体机",
    "A345": "空客 A340-500 罕见四发宽体机",
    "A343": "空客 A340-300 罕见四发宽体机",
    "A342": "空客 A340-200 罕见四发宽体机",
    "A124": "安东诺夫 An-124 巨型战略运输机",
    "IL96": "伊留申 Il-96 俄制四发宽体机/专机",
    "IL76": "伊留申 Il-76 俄制重型运输机",
    "IL62": "伊留申 Il-62 经典俄制四发客机",
    "T204": "图波列夫 Tu-204 俄制客/货机",
    "T214": "图波列夫 Tu-214 俄制特种/客机",
    "SU95": "苏霍伊 SSJ-100 俄制支线机",
    "MD11": "麦道 MD-11 三发宽体货机",
    "DC10": "麦道 DC-10 三发宽体机",
    "A306": "空客 A300-600 经典宽体机",
    "A310": "空客 A310 罕见经典宽体机",
    "B752": "波音 757-200 经典窄体/货机",
    "B753": "波音 757-300 罕见加长757",
    "75F": "波音 757F 经典全货机",
    "B762": "波音 767-200 少见宽体机",
    "B763": "波音 767-300 少见767宽体机",
    "763": "波音 767-300 少见767宽体机",
    "76F": "波音 767F 宽体全货机",
    "B764": "波音 767-400ER 罕见767子型号",
    "B77L": "波音 777-200LR / 777F 远程宽体/货机",
    "B77F": "波音 777F 宽体全货机",
    "77X": "波音 777F 宽体全货机",
    "B772": "波音 777-200ER 早期经典777",
    "A35K": "空客 A350-1000 旗舰大型宽体机",
    "351": "空客 A350-1000 旗舰大型宽体机",
    "B78X": "波音 787-10 加长梦想客机",
    "781": "波音 787-10 加长梦想客机",
    "A338": "空客 A330-800neo 极罕见宽体机",
    "A339": "空客 A330-900neo 少见新一代宽体机",
    "339": "空客 A330-900neo 少见新一代宽体机",
    "A33F": "空客 A330-200F 宽体全货机",
    "A318": "空客 A318 罕见小型A320家族/VIP",
    "BCS1": "空客 A220-100 少见窄体机",
    "BCS3": "空客 A220-300 少见窄体机",
    "E290": "巴航工业 E190-E2 新一代支线机",
    "E295": "巴航工业 E195-E2 新一代支线机",
}

BIZJET_CODES = {
    "G650", "GLF6", "GLF5", "G550", "G500", "G600", "G700", "GLF4", "G450",
    "GL7T", "GLEX", "GL5T", "GL6T", "FA7X", "FA8X", "F900", "F2TH", "FA50",
    "CL60", "CL35", "CL30", "C680", "C68A", "C700", "C750", "C56X", "E35L",
    "E55P", "LJ60", "LJ45", "H25B", "HDJT", "PC24", "PRM1",
}


def airport_sunrise_sunset(dt_local: datetime, lat: float = BEIJING_LAT, lon: float = BEIJING_LON) -> tuple[datetime, datetime]:
    day_of_year = dt_local.timetuple().tm_yday
    lat_rad = math.radians(lat)
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
    sunrise_utc_min = 720.0 - 4.0 * (lon + ha_deg) - eqtime
    sunset_utc_min = 720.0 - 4.0 * (lon - ha_deg) - eqtime
    tz = dt_local.tzinfo or CST
    tz_offset_min = (tz.utcoffset(dt_local) or timedelta(hours=8)).total_seconds() / 60.0
    midnight_local = dt_local.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=tz)
    return (
        midnight_local + timedelta(minutes=sunrise_utc_min + tz_offset_min),
        midnight_local + timedelta(minutes=sunset_utc_min + tz_offset_min),
    )


def beijing_sunrise_sunset(dt_cst: datetime) -> tuple[datetime, datetime]:
    return airport_sunrise_sunset(dt_cst, BEIJING_LAT, BEIJING_LON)


def fetch_page(airport_code: str, timestamp: int, page: int, limit: int = 100) -> dict:
    params = urllib.parse.urlencode({
        "code": airport_code.lower(),
        "plugin[]": "schedule",
        "plugin-setting[schedule][mode]": "arrivals",
        "plugin-setting[schedule][timestamp]": str(timestamp),
        "limit": str(limit),
        "page": str(page),
    })
    url = f"https://api.flightradar24.com/common/v1/airport.json?{params}"
    req = urllib.request.Request(url, headers=HEADERS)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code == 403:
                raise RuntimeError(f"FR24 HTTP 403 for {airport_code} page {page}") from exc
            if attempt == 2:
                raise
            time.sleep(1.5 * (attempt + 1))
        except (urllib.error.URLError, TimeoutError):
            if attempt == 2:
                raise
            time.sleep(1.5 * (attempt + 1))
    return {}


def parse_flight(entry: dict, airport_code: str, local_tz: timezone = CST) -> dict | None:
    f = entry.get("flight") or {}
    time_info = f.get("time") or {}
    arr_ts = (time_info.get("scheduled") or {}).get("arrival") or (time_info.get("estimated") or {}).get("arrival")
    if not arr_ts:
        return None

    ident = f.get("identification") or {}
    flight_num = ((ident.get("number") or {}).get("default") or "").upper()
    callsign = (ident.get("callsign") or "").upper()

    aircraft = f.get("aircraft") or {}
    model = aircraft.get("model") or {}
    ac_code = (model.get("code") or "").upper()
    ac_text = model.get("text") or ""
    reg = (aircraft.get("registration") or "").upper()
    restricted = bool(aircraft.get("restricted"))

    airline = f.get("airline") or {}
    airline_name = airline.get("name") or ""
    airline_iata = ((airline.get("code") or {}).get("iata") or "").upper()
    airline_icao = ((airline.get("code") or {}).get("icao") or "").upper()

    owner_name = (f.get("owner") or {}).get("name") or ""
    origin = (f.get("airport") or {}).get("origin") or {}
    origin_iata = ((origin.get("code") or {}).get("iata") or "").upper()
    origin_pos = origin.get("position") or {}
    origin_city = (origin_pos.get("region") or {}).get("city") or ""
    origin_country = (origin_pos.get("country") or {}).get("name") or ""

    # Apply known FR24 IATA collision corrections
    fix = FR24_AIRLINE_FIXES.get((airline_iata, origin_iata))
    if fix:
        airline_name, airline_iata, airline_icao = fix

    arr_dt = datetime.fromtimestamp(arr_ts, tz=local_tz)
    return {
        "airport": airport_code.upper(),
        "arrival_ts": arr_ts,
        "arrival_cst": arr_dt.strftime("%Y-%m-%d %H:%M"),
        "arrival_time": arr_dt.strftime("%H:%M"),
        "flight_number": flight_num,
        "callsign": callsign,
        "airline": airline_name,
        "airline_iata": airline_iata,
        "airline_icao": airline_icao,
        "owner": owner_name,
        "origin_iata": origin_iata,
        "origin_city": origin_city,
        "origin_country": origin_country,
        "aircraft_code": ac_code,
        "aircraft_text": ac_text,
        "registration": reg,
        "restricted": restricted,
    }


def fetch_airport_for_date(airport_code: str, target_date: datetime) -> dict:
    # First probe page 1 to discover airport's exact lat/lon & timezone offset for local sunrise/sunset
    lat, lon, tz_offset_sec = BEIJING_LAT, BEIJING_LON, 28800
    airport_name = zh_origin(airport_code.upper())
    local_tz = CST
    start_dt = target_date.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=local_tz)
    end_dt = start_dt + timedelta(days=1) - timedelta(seconds=1)
    start_ts = int(start_dt.timestamp())
    end_ts = int(end_dt.timestamp())

    anchor_timestamps = [start_ts - 3600, start_ts + 8 * 3600, start_ts + 16 * 3600]
    seen_keys = set()
    flights = []
    errors = []
    max_seen_ts = 0
    meta_loaded = False

    for anchor in anchor_timestamps:
        if max_seen_ts >= end_ts:
            break
        page = 1
        while page <= 12:
            try:
                payload = fetch_page(airport_code, anchor, page, limit=100)
            except Exception as exc:
                errors.append(str(exc))
                if "403" in str(exc):
                    return {
                        "airport": airport_code.upper(),
                        "airport_name": airport_name,
                        "lat": lat, "lon": lon, "tz_offset_sec": tz_offset_sec,
                        "date": start_dt.strftime("%Y-%m-%d"),
                        "total_flights": 0,
                        "first_arrival": None,
                        "last_arrival": None,
                        "errors": errors,
                        "flights": [],
                    }
                break
            try:
                plugin_data = payload["result"]["response"]["airport"]["pluginData"]
                if not meta_loaded:
                    details = plugin_data.get("details") or {}
                    pos = details.get("position") or {}
                    if pos.get("latitude") is not None and pos.get("longitude") is not None:
                        lat = float(pos["latitude"])
                        lon = float(pos["longitude"])
                    tz_info = details.get("timezone") or {}
                    if tz_info.get("offset") is not None:
                        tz_offset_sec = int(tz_info["offset"])
                        local_tz = timezone(timedelta(seconds=tz_offset_sec))
                        start_dt = target_date.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=local_tz)
                        end_dt = start_dt + timedelta(days=1) - timedelta(seconds=1)
                        start_ts = int(start_dt.timestamp())
                        end_ts = int(end_dt.timestamp())
                    meta_loaded = True
                arrivals = plugin_data["schedule"]["arrivals"]
            except (KeyError, TypeError):
                break
            rows = arrivals.get("data") or []
            if not rows:
                break

            page_min_ts = None
            page_max_ts = None
            for row in rows:
                parsed = parse_flight(row, airport_code, local_tz)
                if not parsed:
                    continue
                ts = parsed["arrival_ts"]
                page_min_ts = ts if page_min_ts is None else min(page_min_ts, ts)
                page_max_ts = ts if page_max_ts is None else max(page_max_ts, ts)
                max_seen_ts = max(max_seen_ts, ts)
                if start_ts <= ts <= end_ts:
                    k = (parsed["flight_number"] or parsed["callsign"], parsed["arrival_ts"], parsed["origin_iata"])
                    if k not in seen_keys:
                        seen_keys.add(k)
                        flights.append(parsed)

            total_pages = (arrivals.get("page") or {}).get("total") or 1
            if (page_min_ts and page_min_ts > end_ts) or (page_max_ts and page_max_ts >= end_ts) or page >= total_pages:
                break
            page += 1
            time.sleep(0.25)

    flights.sort(key=lambda x: x["arrival_ts"])
    return {
        "airport": airport_code.upper(),
        "airport_name": airport_name,
        "lat": lat,
        "lon": lon,
        "tz_offset_sec": tz_offset_sec,
        "date": start_dt.strftime("%Y-%m-%d"),
        "total_flights": len(flights),
        "first_arrival": flights[0]["arrival_time"] if flights else None,
        "last_arrival": flights[-1]["arrival_time"] if flights else None,
        "errors": errors,
        "flights": flights,
    }


def analyze_flights(airport_result: dict) -> dict:
    flights = airport_result["flights"]
    airline_counts = Counter(f["airline"] or f["airline_iata"] or "Unknown" for f in flights)

    vip_or_unusual = []
    special_liveries = []
    special_aircraft = []
    intl_cargo = []
    rare_airlines = []
    c919_count = 0
    c919_highlights = []

    for f in flights:
        airline_raw = f["airline"] or ""
        airline_lower = (airline_raw + " " + f["owner"]).lower()
        ac_code = f["aircraft_code"]
        iata = f["airline_iata"]
        reg = f["registration"]
        origin_country = f["origin_country"]

        if ac_code == "C919":
            c919_count += 1
            if reg in {"B-919A", "B-919X"} or origin_country not in {"China", ""}:
                c919_highlights.append(f"{f['arrival_time']} {f['flight_number']}（{zh_origin(f['origin_iata'], f['origin_city'], origin_country)}，{reg or 'C919'}）")

        # 1. Special liveries
        livery_reasons = []
        if "(" in airline_raw:
            s_i = airline_raw.find("(") + 1
            e_i = airline_raw.rfind(")")
            p_txt = (airline_raw[s_i:e_i] if e_i > s_i else airline_raw[s_i:]).strip()
            # Skip our own Chinese translation suffixes in FR24_AIRLINE_FIXES
            if p_txt and not any(ch >= "\u4e00" for ch in p_txt) and p_txt.lower() not in {"cargo", "express", "regional"}:
                livery_reasons.append(f"🎨 {zh_livery(p_txt)}")
        elif any(kw in airline_raw.lower() for kw in SPECIAL_LIVERY_KEYWORDS):
            livery_reasons.append(f"🎨 {zh_livery(airline_raw)}")
        elif reg in KNOWN_SPECIAL_LIVERIES:
            livery_reasons.append(f"🎨 {KNOWN_SPECIAL_LIVERIES[reg]}")
        if livery_reasons:
            special_liveries.append({**f, "reasons": livery_reasons})

        # 2. VIP / Gov / Bizjet / Restricted / Unscheduled
        is_vip_kw = any(kw in airline_lower for kw in VIP_GOV_KEYWORDS)
        is_bizjet = ac_code in BIZJET_CODES
        is_no_flt = not f["flight_number"]
        if is_vip_kw or is_bizjet or f["restricted"] or is_no_flt:
            reasons = []
            if is_vip_kw:
                reasons.append("🏛️ 政府/军政/公务包机特征")
            if is_bizjet:
                reasons.append(f"🛩️ 公务/专机机型 ({ac_code})")
            if f["restricted"]:
                reasons.append("🔒 FR24 受限注册号")
            if is_no_flt:
                reasons.append("📋 无常规商业航班号（疑为包机/调机）")
            vip_or_unusual.append({**f, "reasons": reasons})

        # 3. Special / iconic aircraft (excluding high-volume C919 which is summarized cleanly)
        if ac_code in SPECIAL_AIRCRAFT_CODES:
            special_aircraft.append({**f, "reasons": [f"✈️ {SPECIAL_AIRCRAFT_CODES[ac_code]}"]})

        # 4. International or widebody cargo
        is_cargo = any(kw in airline_lower for kw in CARGO_KEYWORDS) or ac_code in {"B77F", "77X", "75F", "74Y", "74F", "74N", "76F", "A33F", "MD11"}
        if is_cargo and (origin_country not in {"China", ""} or ac_code in {"B748", "74N", "B744", "74Y", "74F", "B77F", "77X", "75F", "A333", "A33F", "MD11"}):
            intl_cargo.append({**f, "reasons": ["📦 重点/国际/宽体全货机"]})

        # 5. Uncommon / rare foreign airlines (1-2 daily flights, excluding common regional shuttles)
        is_common_cn_sub = airline_raw.lower() in COMMON_CN_SUBSIDIARIES
        if iata not in COMMON_CN_CARRIERS and not is_common_cn_sub and not is_cargo and iata not in ROUTINE_REGIONAL_CARRIERS:
            freq = airline_counts[airline_raw or iata or "Unknown"]
            if freq <= 2:
                rare_airlines.append({
                    **f,
                    "reasons": [f"🌍 稀缺/低频航司（{zh_country(origin_country)} · 当日仅 {freq} 班）"],
                })

    return {
        "airport": airport_result["airport"],
        "airport_name": airport_result.get("airport_name") or zh_origin(airport_result["airport"]),
        "lat": airport_result.get("lat", BEIJING_LAT),
        "lon": airport_result.get("lon", BEIJING_LON),
        "tz_offset_sec": airport_result.get("tz_offset_sec", 28800),
        "date": airport_result["date"],
        "total_flights": airport_result["total_flights"],
        "first_arrival": airport_result["first_arrival"],
        "last_arrival": airport_result["last_arrival"],
        "errors": airport_result["errors"],
        "c919_count": c919_count,
        "c919_highlights": c919_highlights,
        "vip_or_unusual": vip_or_unusual,
        "special_liveries": special_liveries,
        "special_aircraft": special_aircraft,
        "intl_cargo": intl_cargo,
        "rare_airlines": rare_airlines,
    }


# Ultra-special targets that ALWAYS stay in the main section regardless of sunrise/sunset
ULTRA_SPECIAL_TYPES = {
    "A124", "A225", "IL96", "IL62", "MD11", "DC10", "B74S", "B742", "B743",
    "A345", "A346", "A3ST", "A337", "BLCF", "C5M", "C5", "C17", "VC25", "E4B", "C32A", "E3CF", "B703",
}
ULTRA_VIP_CALLSIGN_PREFIXES = (
    "AF1", "AF2", "AIRFORCE1", "EXEC1", "SAM", "VENUS", "RSD", "GAF", "COTAM",
    "JPN001", "JPN002", "JF001", "JF002", "KAF001", "KAF002", "KRH", "RRR",
    "CFC01", "SUI", "AME", "IAM", "FAB01", "ASY",
    "CCA001", "CCA002", "CCA003", "CCA004", "CCA005", "CCA006", "CCA007", "CCA008", "CCA009",
)
ULTRA_VIP_REGS = {"B-2479", "82-8000", "92-9000", "73-1676", "73-1677", "74-0787", "75-0125"}


def is_ultra_special(f: dict) -> bool:
    cs = (f.get("callsign") or "").upper()
    reg = (f.get("registration") or "").upper()
    ac = (f.get("aircraft_code") or "").upper()
    return (
        ac in ULTRA_SPECIAL_TYPES
        or reg in ULTRA_VIP_REGS
        or any(cs.startswith(p) for p in ULTRA_VIP_CALLSIGN_PREFIXES)
    )


def split_by_daylight(items: list[dict], win_start: datetime, win_end: datetime) -> tuple[list[dict], list[dict]]:
    """Split items into (main_shootable_or_ultra, dark_filtered_reference)."""
    main_list, dark_list = [], []
    for f in items:
        arr_dt = datetime.fromtimestamp(f["arrival_ts"], tz=CST)
        if (win_start < arr_dt < win_end) or is_ultra_special(f):
            main_list.append(f)
        else:
            dark_list.append(f)
    return main_list, dark_list


def esc(s: str) -> str:
    return html.escape(str(s or ""))


def render_rows(items: list[dict], win_start: datetime, win_end: datetime, empty_msg: str, muted: bool = False) -> str:
    if not items:
        return f'<tr><td colspan="5" style="border:1px solid #e2e8f0;padding:10px;color:#64748b;text-align:center;">{esc(empty_msg)}</td></tr>'
    out = []
    for f in items:
        arr_dt = datetime.fromtimestamp(f["arrival_ts"], tz=CST)
        shootable = win_start < arr_dt < win_end
        ultra = is_ultra_special(f)
        if muted:
            bg = "#f8fafc"
            tag = ' <span style="font-size:11px;color:#64748b;">🌙夜间</span>'
        elif ultra and not shootable:
            bg = "#fef2f2"
            tag = ' <span style="font-size:11px;color:#b91c1c;">🚨直通</span>'
        else:
            bg = "#fefce8"
            tag = ' <span style="font-size:11px;color:#b45309;">☀可拍</span>'
        flt = f["flight_number"] or f["callsign"] or "N/A"
        reg_html = f'<br><span style="color:#2563eb;">{esc(f["registration"])}</span>' if f["registration"] else ""
        ac_disp = zh_aircraft(f["aircraft_text"], f["aircraft_code"])
        airline_disp = zh_airline(f["airline"], f["airline_iata"], f["owner"])
        orig_disp = zh_origin(f["origin_iata"], f["origin_city"], f["origin_country"])
        out.append(f"""
        <tr style="background-color:{bg};">
          <td style="border:1px solid #e2e8f0;padding:7px;white-space:nowrap;"><strong>{esc(f['arrival_time'])}</strong>{tag}</td>
          <td style="border:1px solid #e2e8f0;padding:7px;"><strong>{esc(flt)}</strong></td>
          <td style="border:1px solid #e2e8f0;padding:7px;">{esc(airline_disp)}<br><span style="color:#64748b;font-size:12px;">{esc(orig_disp)}</span></td>
          <td style="border:1px solid #e2e8f0;padding:7px;">{esc(ac_disp)}{reg_html}</td>
          <td style="border:1px solid #e2e8f0;padding:7px;">{'<br>'.join(esc(r) for r in f['reasons'])}</td>
        </tr>""")
    return "".join(out)


def merge_highlights(ap_data: dict) -> list[dict]:
    """Merge VIP, special aircraft, intl cargo, and rare airlines into one deduplicated table per airport."""
    merged = {}
    for cat in ("vip_or_unusual", "special_aircraft", "intl_cargo", "rare_airlines"):
        for f in ap_data.get(cat) or []:
            k = (f["flight_number"] or f["callsign"], f["arrival_ts"])
            if k not in merged:
                merged[k] = {**f, "reasons": list(f["reasons"])}
            else:
                for r in f["reasons"]:
                    if r not in merged[k]["reasons"]:
                        merged[k]["reasons"].append(r)
    return sorted(merged.values(), key=lambda x: x["arrival_ts"])


def merge_dark_reference(dark_by_airport: list[tuple[str, list[dict]]]) -> list[dict]:
    """Combine all dark-hour filtered flights (liveries + highlights) across all airports."""
    merged = {}
    for ap_tag, items in dark_by_airport:
        for f in items:
            k = (ap_tag, f["flight_number"] or f["callsign"], f["arrival_ts"])
            if k not in merged:
                merged[k] = {
                    **f,
                    "flight_number": f"[{ap_tag}] {f['flight_number'] or f['callsign'] or 'N/A'}",
                    "reasons": list(f["reasons"]),
                }
            else:
                for r in f["reasons"]:
                    if r not in merged[k]["reasons"]:
                        merged[k]["reasons"].append(r)
    return sorted(merged.values(), key=lambda x: x["arrival_ts"])


def build_html(summary: dict, target_dt: datetime, edition_label: str = "次日亮点与彩绘到港汇总") -> str:
    airports = summary["airports"]
    codes = list(airports.keys())
    first_ap = airports[codes[0]]
    local_tz = timezone(timedelta(seconds=first_ap.get("tz_offset_sec", 28800)))
    sunrise, sunset = airport_sunrise_sunset(
        target_dt.replace(tzinfo=local_tz),
        first_ap.get("lat", BEIJING_LAT),
        first_ap.get("lon", BEIJING_LON),
    )
    win_start = sunrise - timedelta(hours=1)
    win_end = sunset + timedelta(hours=1)

    thead_livery = """
      <thead>
        <tr style="background-color:#fdf2f8;color:#831843;">
          <th style="border:1px solid #f5d0fe;padding:7px;text-align:left;width:86px;">预计到达</th>
          <th style="border:1px solid #f5d0fe;padding:7px;text-align:left;width:76px;">航班号</th>
          <th style="border:1px solid #f5d0fe;padding:7px;text-align:left;">航司 / 出发地</th>
          <th style="border:1px solid #f5d0fe;padding:7px;text-align:left;">机型 / 注册号</th>
          <th style="border:1px solid #f5d0fe;padding:7px;text-align:left;">彩绘 / 涂装主题</th>
        </tr>
      </thead>"""
    thead_std = """
      <thead>
        <tr style="background-color:#f1f5f9;color:#0f172a;">
          <th style="border:1px solid #cbd5e1;padding:7px;text-align:left;width:86px;">预计到达</th>
          <th style="border:1px solid #cbd5e1;padding:7px;text-align:left;width:88px;">航班号</th>
          <th style="border:1px solid #cbd5e1;padding:7px;text-align:left;">航司 / 出发地</th>
          <th style="border:1px solid #cbd5e1;padding:7px;text-align:left;">机型 / 注册号</th>
          <th style="border:1px solid #cbd5e1;padding:7px;text-align:left;">亮点说明</th>
        </tr>
      </thead>"""

    livery_sections = []
    highlight_sections = []
    dark_by_airport = []
    scan_stats = []
    livery_stats = []
    c919_parts = []

    for code in codes:
        ap = airports[code]
        ap_name = ap.get("airport_name") or zh_origin(code)
        ap_tz = timezone(timedelta(seconds=ap.get("tz_offset_sec", 28800)))
        ap_sr, ap_ss = airport_sunrise_sunset(
            target_dt.replace(tzinfo=ap_tz),
            ap.get("lat", BEIJING_LAT),
            ap.get("lon", BEIJING_LON),
        )
        ap_ws, ap_we = ap_sr - timedelta(hours=1), ap_ss + timedelta(hours=1)

        liv_main, liv_dark = split_by_daylight(ap["special_liveries"], ap_ws, ap_we)
        hi_main, hi_dark = split_by_daylight(merge_highlights(ap), ap_ws, ap_we)
        dark_by_airport.append((code, liv_dark + hi_dark))

        scan_stats.append(f"{code} {ap['total_flights']} 班")
        livery_stats.append(f"{code} {len(liv_main)} 班")
        if ap.get("c919_count"):
            c919_parts.append(
                f"{code} 共 {ap['c919_count']} 班 C919"
                + (f"（亮点：{'、'.join(ap['c919_highlights'])}）" if ap.get("c919_highlights") else "")
            )

        livery_sections.append(f"""
    <h3 style="margin:14px 0 6px 0;color:#0f172a;">🎨 {esc(ap_name)} 可拍时段彩绘（{len(liv_main)} 班）</h3>
    <table style="width:100%;border-collapse:collapse;font-size:13px;margin-bottom:14px;">
      {thead_livery}
      <tbody>{render_rows(liv_main, ap_ws, ap_we, f'可拍时段内暂未检出已排机 {code} 彩绘')}</tbody>
    </table>""")

        highlight_sections.append(f"""
    <h3 style="margin:18px 0 8px 0;color:#0f172a;">🛬 {esc(ap_name)} 专机 / 特殊机型 / 罕见航司（{len(hi_main)} 班）</h3>
    <table style="width:100%;border-collapse:collapse;font-size:13px;margin-bottom:18px;">
      {thead_std}
      <tbody>{render_rows(hi_main, ap_ws, ap_we, f'可拍时段内 {code} 暂无额外特殊机型或低频航司')}</tbody>
    </table>""")

    dark_ref = merge_dark_reference(dark_by_airport)
    title_codes = " / ".join(codes)
    c919_html = f"<strong>国产 C919 概览：</strong>{esc('；'.join(c919_parts))}。<br>" if c919_parts else ""

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="utf-8"><title>机场({title_codes}){edition_label} - {summary['target_date']}</title></head>
<body style="font-family:'Microsoft YaHei','PingFang SC',Arial,sans-serif;color:#1f2937;line-height:1.6;max-width:860px;margin:0 auto;padding:18px;background:#f8fafc;">
  <div style="background:#ffffff;border-radius:10px;padding:24px;border:1px solid #e2e8f0;">
    <h2 style="margin:0 0 8px 0;color:#0f172a;border-bottom:2px solid #2563eb;padding-bottom:10px;">
      ✈️ 机场（{esc(title_codes)}）{esc(edition_label)}
    </h2>
    <p style="margin:6px 0 16px 0;color:#475569;font-size:13px;">
      <strong>目标日期：</strong>{summary['target_date']}（当地时间） &nbsp;|&nbsp;
      <strong>扫描规模：</strong>{' / '.join(scan_stats)} &nbsp;|&nbsp;
      <strong>当地日出/日落：</strong>{sunrise.strftime('%H:%M')} / {sunset.strftime('%H:%M')}（主区仅展示可拍窗口 <strong>{win_start.strftime('%H:%M')}–{win_end.strftime('%H:%M')}</strong> 及 🚨24h直通目标）
    </p>

    {''.join(livery_sections)}
    {''.join(highlight_sections)}

    <div style="border-top:2px dashed #cbd5e1;padding-top:14px;margin-top:8px;">
      <h3 style="margin:0 0 6px 0;font-size:14px;color:#475569;">🌙 夜间被过滤参考区（{win_start.strftime('%H:%M')} 前或 {win_end.strftime('%H:%M')} 后 · 共 {len(dark_ref)} 班）</h3>
      <p style="margin:0 0 10px 0;font-size:12px;color:#64748b;">以下航班落于暗光时段（常规不建议拍机），单独归档在此供查漏参考；MD-11/DC-10/AF1/IL-96/AN-124 等直通目标不受此过滤。</p>
      <table style="width:100%;border-collapse:collapse;font-size:12px;color:#475569;">
        {thead_std}
        <tbody>{render_rows(dark_ref, win_start, win_end, '夜间时段无额外亮点航班', muted=True)}</tbody>
      </table>
    </div>

    <p style="font-size:12px;color:#475569;background:#f8fafc;padding:10px 12px;border-radius:6px;margin:14px 0 0 0;">
      {c919_html}<strong>提示：</strong>外事访问新闻总结将在你上线 Antigravity 时由本地 AI 单独补充发送；出差想看其他城市机场，可在 GitHub Actions 手动运行填入任意机场三字码（如 PVG,SHA）。
    </p>
  </div>
</body>
</html>"""


def send_smtp(subject: str, html_body: str, config_path: str | None = None) -> None:
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

    msg = MIMEText(html_body, "html", "utf-8")
    msg["From"] = formataddr((str(Header("北京机场航班简报", "utf-8")), user))
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = Header(subject, "utf-8")

    ctx = ssl.create_default_context()
    with smtplib.SMTP_SSL(host, port, context=ctx, timeout=25) as server:
        server.login(user, auth_code)
        server.sendmail(user, recipients, msg.as_string())
    print(f"DAILY_DIGEST_SENT_OK: {subject} -> {', '.join(recipients)}")


def load_previous_sent_keys(arrivals_path: str, target_date: str) -> set[tuple[str, str, str]]:
    """Load (airport, flight_number, registration) already reported in last evening's digest for target_date."""
    keys = set()
    if not os.path.exists(arrivals_path):
        return keys
    try:
        with open(arrivals_path, "r", encoding="utf-8") as fh:
            prev = json.load(fh)
        if prev.get("target_date") != target_date:
            return keys
        for code, ap in (prev.get("airports") or {}).items():
            for cat in ("special_liveries", "vip_or_unusual", "special_aircraft", "intl_cargo", "rare_airlines"):
                for f in ap.get(cat) or []:
                    flt = (f.get("flight_number") or f.get("callsign") or "").upper()
                    reg = (f.get("registration") or "").upper()
                    keys.add((code.upper(), flt, reg))
    except Exception:
        pass
    return keys


def filter_summary_diff(summary: dict, prev_keys: set[tuple[str, str, str]], min_hour: int | None = None) -> tuple[dict, int]:
    """Keep only newly discovered / newly assigned flights not in prev_keys (and >= min_hour if set)."""
    new_summary = {**summary, "airports": {}}
    new_count = 0
    for code, ap in summary["airports"].items():
        new_ap = {**ap}
        ap_tz = timezone(timedelta(seconds=ap.get("tz_offset_sec", 28800)))
        ap_seen = set()
        for cat in ("special_liveries", "vip_or_unusual", "special_aircraft", "intl_cargo", "rare_airlines"):
            kept = []
            for f in ap.get(cat) or []:
                if min_hour is not None:
                    arr_local = datetime.fromtimestamp(f["arrival_ts"], tz=ap_tz)
                    if arr_local.hour < min_hour:
                        continue
                flt = (f.get("flight_number") or f.get("callsign") or "").upper()
                reg = (f.get("registration") or "").upper()
                if (not prev_keys) or ((code.upper(), flt, reg) not in prev_keys):
                    kept.append(f)
                    ap_seen.add((flt, reg, f.get("arrival_ts")))
            new_ap[cat] = kept
        new_count += len(ap_seen)
        new_summary["airports"][code] = new_ap
    return new_summary, new_count


def main() -> int:
    parser = argparse.ArgumentParser(description="Daily Airport Arrivals & Liveries Digest")
    parser.add_argument("--airports", default=os.environ.get("TARGET_AIRPORTS") or "PEK,PKX", help="Comma-separated IATA codes (e.g. PEK,PKX or PVG,SHA)")
    parser.add_argument("--date", help="Target date YYYY-MM-DD. Defaults to today if before 12:00 CST, else tomorrow.")
    parser.add_argument("--diff-only", action="store_true", help="Only email newly discovered/assigned flights compared to previous cached digest; skip email if none.")
    parser.add_argument("--min-hour", type=int, default=None, help="Optional minimum local arrival hour (e.g. 10 to exclude arrivals before 10:00).")
    parser.add_argument("--state-dir", default="state", help="Directory to save arrivals.json for live alert dedup")
    parser.add_argument("--html-out", help="Optional path to save generated HTML")
    parser.add_argument("--smtp-config", help="Optional local smtp_config.json fallback")
    parser.add_argument("--dry-run", action="store_true", help="Do not send email")
    args = parser.parse_args()

    sys.stdout.reconfigure(encoding="utf-8")
    airport_codes = [c.strip().upper() for c in (args.airports or "PEK,PKX").split(",") if c.strip()]
    if not airport_codes:
        airport_codes = ["PEK", "PKX"]

    now_cst = datetime.now(CST)
    if args.date:
        target_dt = datetime.strptime(args.date, "%Y-%m-%d").replace(tzinfo=CST)
        edition_label = "早8点补漏简报" if args.diff_only else "亮点与彩绘到港汇总"
    elif now_cst.hour < 12:
        target_dt = now_cst.replace(hour=0, minute=0, second=0, microsecond=0)
        edition_label = "早8点补漏简报" if args.diff_only else "当日亮点与彩绘汇总"
    else:
        target_dt = (now_cst + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        edition_label = "次日亮点与彩绘到港汇总"

    summary = {
        "generated_at_cst": now_cst.strftime("%Y-%m-%d %H:%M:%S +08:00"),
        "target_date": target_dt.strftime("%Y-%m-%d"),
        "airports": {},
    }
    for code in airport_codes:
        raw = fetch_airport_for_date(code, target_dt)
        summary["airports"][code] = analyze_flights(raw)

    os.makedirs(args.state_dir, exist_ok=True)
    arrivals_path = os.path.join(args.state_dir, "arrivals.json")

    render_summary = summary
    if args.diff_only:
        prev_keys = load_previous_sent_keys(arrivals_path, summary["target_date"])
        render_summary, new_count = filter_summary_diff(summary, prev_keys, min_hour=args.min_hour)
        # Also check if any new item is in shootable window or ultra-special (ignore dark-only noise in morning diff)
        shootable_new = 0
        for code, ap in render_summary["airports"].items():
            ap_tz = timezone(timedelta(seconds=ap.get("tz_offset_sec", 28800)))
            sr, ss = airport_sunrise_sunset(target_dt.replace(tzinfo=ap_tz), ap.get("lat", BEIJING_LAT), ap.get("lon", BEIJING_LON))
            ws, we = sr - timedelta(hours=1), ss + timedelta(hours=1)
            lm, _ = split_by_daylight(ap["special_liveries"], ws, we)
            hm, _ = split_by_daylight(merge_highlights(ap), ws, we)
            shootable_new += len(lm) + len(hm)
        print(f"DIFF_ONLY check: prev_keys={len(prev_keys)}, total_new={new_count}, shootable_or_ultra_new={shootable_new}")
        # Always refresh full state cache so live_alert stays up to date
        if set(airport_codes) & {"PEK", "PKX"}:
            with open(arrivals_path, "w", encoding="utf-8") as fh:
                json.dump(summary, fh, ensure_ascii=False, indent=2)
        if shootable_new == 0:
            print("DIFF_ONLY: No new shootable or ultra-special arrivals found. Skipping email.")
            return 0
    else:
        if set(airport_codes) & {"PEK", "PKX"}:
            with open(arrivals_path, "w", encoding="utf-8") as fh:
                json.dump(summary, fh, ensure_ascii=False, indent=2)

    html_body = build_html(render_summary, target_dt, edition_label=edition_label)
    if args.html_out:
        os.makedirs(os.path.dirname(os.path.abspath(args.html_out)), exist_ok=True)
        with open(args.html_out, "w", encoding="utf-8") as fh:
            fh.write(html_body)

    stats = " | ".join(
        f"{c}={render_summary['airports'][c]['total_flights']} (livery={len(render_summary['airports'][c]['special_liveries'])})"
        for c in airport_codes
    )
    print(f"Date={summary['target_date']} ({edition_label}) | {stats}")

    if args.dry_run:
        print("DRY_RUN: Email skipped.")
        return 0

    codes_str = "/".join(airport_codes)
    subject = f"机场({codes_str}){edition_label} - {summary['target_date']}"
    send_smtp(subject, html_body, args.smtp_config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
