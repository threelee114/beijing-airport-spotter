#!/usr/bin/env python3
"""Chinese localization maps for airlines, airports/cities, countries, aircraft, and FR24 livery names."""

import re

AIRLINE_BY_IATA = {
    # Mainland China
    "CA": "中国国际航空",
    "MU": "中国东方航空",
    "CZ": "中国南方航空",
    "HU": "海南航空",
    "MF": "厦门航空",
    "3U": "四川航空",
    "ZH": "深圳航空",
    "SC": "山东航空",
    "FM": "上海航空",
    "HO": "吉祥航空",
    "9C": "春秋航空",
    "GS": "天津航空",
    "KN": "中国联合航空",
    "EU": "成都航空",
    "JD": "首都航空",
    "GJ": "长龙航空",
    "KY": "昆明航空",
    "TV": "西藏航空",
    "PN": "西部航空",
    "8L": "祥鹏航空",
    "NS": "河北航空",
    "JR": "幸福航空",
    "DZ": "东海航空",
    "QW": "青岛航空",
    "FU": "福州航空",
    "G5": "华夏航空",
    "AQ": "九元航空",
    "BK": "奥凯航空",
    "DR": "瑞丽航空",
    "GX": "北部湾航空",
    "LT": "龙江航空",
    "RY": "江西航空",
    "GT": "桂林航空",
    "UQ": "乌鲁木齐航空",
    "Y2": "天骄航空",
    "OQ": "重庆航空",
    "CN": "大新华航空",
    "9H": "长安航空",
    "A6": "湖南航空",
    "GY": "多彩贵州航空",
    # Cargo (China & Intl)
    "O3": "顺丰航空",
    "CF": "中国邮政航空",
    "JG": "京东航空",
    "CK": "中国货运航空",
    "Y8": "金鹏航空",
    "YG": "圆通航空",
    "HT": "天津货运航空",
    "GI": "中原龙浩航空",
    "I9": "中州航空",
    "LD": "香港华民航空",
    "CV": "卢森堡货运航空",
    "7L": "丝绸之路西部航空",
    "RU": "空桥货运航空",
    "FX": "联邦快递 FedEx",
    "5X": "联合包裹 UPS",
    "D0": "DHL 货运",
    "PO": "极地货运航空",
    "5Y": "阿特拉斯航空",
    "K4": "卡利塔航空",
    "KZ": "日本货物航空",
    "LH": "汉莎航空",
    # HK / MO / TW
    "CX": "国泰航空",
    "HX": "香港航空",
    "UO": "香港快运",
    "HB": "大湾区航空",
    "NX": "澳门航空",
    "BR": "长荣航空",
    "CI": "中华航空",
    "JX": "星宇航空",
    # East & Southeast Asia
    "NH": "全日空 ANA",
    "JL": "日本航空 JAL",
    "IJ": "春秋航空日本",
    "KE": "大韩航空",
    "OZ": "韩亚航空",
    "7C": "济州航空",
    "LJ": "真航空",
    "TW": "德威航空",
    "OM": "蒙古民用航空 MIAT",
    "MR": "蒙古匈奴航空",
    "JS": "高丽航空",
    "SQ": "新加坡航空",
    "TR": "酷航",
    "TG": "泰国国际航空",
    "FD": "泰国亚洲航空",
    "MH": "马来西亚航空",
    "AK": "亚洲航空",
    "D7": "亚航 X",
    "OD": "峇迪航空",
    "VN": "越南航空",
    "VJ": "越捷航空",
    "PR": "菲律宾航空",
    "5J": "宿务太平洋航空",
    "BI": "文莱皇家航空",
    "GA": "印尼鹰航",
    "QV": "老挝航空",
    "K6": "柬埔寨国家航空",
    "8M": "缅甸国际航空",
    # Middle East & Africa
    "EK": "阿联酋航空",
    "EY": "阿提哈德航空",
    "QR": "卡塔尔航空",
    "SV": "沙特阿拉伯航空",
    "GF": "海湾航空",
    "WY": "阿曼航空",
    "KU": "科威特航空",
    "W5": "马汉航空",
    "IR": "伊朗航空",
    "TK": "土耳其航空",
    "ET": "埃塞俄比亚航空",
    "MS": "埃及航空",
    "AT": "摩洛哥皇家航空",
    "AH": "阿尔及利亚航空",
    "KQ": "肯尼亚航空",
    "WB": "卢旺达航空",
    # Europe & Russia / CIS
    "AF": "法国航空",
    "KL": "荷兰皇家航空",
    "BA": "英国航空",
    "LX": "瑞士国际航空",
    "OS": "奥地利航空",
    "AY": "芬兰航空",
    "SK": "北欧航空",
    "LO": "波兰航空",
    "IB": "伊比利亚航空",
    "AZ": "意大利航空 ITA",
    "JU": "塞尔维亚航空",
    "SU": "俄罗斯航空",
    "FV": "俄罗斯国家航空",
    "S7": "西伯利亚航空 S7",
    "U6": "乌拉尔航空",
    "EO": "伊卡航空",
    "N4": "北风航空",
    "HZ": "奥罗拉航空",
    "IO": "伊尔航空",
    "B2": "白俄罗斯航空",
    "KC": "阿斯塔纳航空",
    "DV": "斯卡特航空 SCAT",
    "HY": "乌兹别克斯坦航空",
    "J2": "阿塞拜疆航空",
    "T5": "土库曼斯坦航空",
    "SZ": "索蒙航空",
    # Americas & Oceania
    "UA": "美国联合航空",
    "AA": "美国航空",
    "DL": "达美航空",
    "AC": "加拿大航空",
    "CU": "古巴航空",
    "AM": "墨西哥航空",
    "QF": "澳洲航空",
    "NZ": "新西兰航空",
    "PK": "巴基斯坦国际航空",
    "UL": "斯里兰卡航空",
    "BG": "孟加拉航空",
    "RA": "尼泊尔航空",
}

AIRLINE_NAME_OVERRIDES = {
    "klm asia": "荷兰皇家航空（亚洲涂装）",
    "dalian airlines": "大连航空",
    "beijing airlines": "北京航空",
    "inner mongolia airlines": "国航内蒙古",
    "china eastern": "中国东方航空",
    "china eastern airlines": "中国东方航空",
    "air china": "中国国际航空",
    "china southern airlines": "中国南方航空",
    "hainan airlines": "海南航空",
    "loong air": "长龙航空",
    "sichuan airlines": "四川航空",
    "china united airlines": "中国联合航空",
    "cargolux": "卢森堡货运航空",
    "air hong kong": "香港华民航空",
    "china postal airlines": "中国邮政航空",
    "sf airlines": "顺丰航空",
    "jdl airlines": "京东航空",
    "miat mongolian airlines": "蒙古民用航空",
    "hunnu air": "蒙古匈奴航空",
    "royal air maroc": "摩洛哥皇家航空",
    "royal brunei airlines": "文莱皇家航空",
    "ethiopian airlines": "埃塞俄比亚航空",
    "qatar airways": "卡塔尔航空",
    "emirates": "阿联酋航空",
    "etihad airways": "阿提哈德航空",
    "all nippon airways": "全日空 ANA",
    "japan airlines": "日本航空 JAL",
    "singapore airlines": "新加坡航空",
    "rossiya": "俄罗斯国家航空",
    "aeroflot": "俄罗斯航空",
    "ural airlines": "乌拉尔航空",
    "turkish airlines": "土耳其航空",
    "united airlines": "美国联合航空",
    "air france": "法国航空",
    "air canada": "加拿大航空",
    "philippine airlines": "菲律宾航空",
    "vietnam airlines": "越南航空",
    "vietjet air": "越捷航空",
    "malaysia airlines": "马来西亚航空",
    "airasia": "亚洲航空",
    "eva air": "长荣航空",
    "china airlines": "中华航空",
    "cathay pacific": "国泰航空",
    "hong kong airlines": "香港航空",
    "hk express": "香港快运",
    "air macau": "澳门航空",
    "korean air": "大韩航空",
    "asiana airlines": "韩亚航空",
    "thai airways": "泰国国际航空",
    "spring japan": "春秋航空日本",
    "donghai airlines": "东海航空",
    "colorful guizhou airlines": "多彩贵州航空",
}

AIRPORT_CITY_ZH = {
    # China Mainland
    "PEK": "北京首都", "PKX": "北京大兴", "SHA": "上海虹桥", "PVG": "上海浦东",
    "CAN": "广州", "SZX": "深圳", "CTU": "成都双流", "TFU": "成都天府",
    "CKG": "重庆", "HGH": "杭州", "NKG": "南京", "XIY": "西安",
    "CSX": "长沙", "WUH": "武汉", "KMG": "昆明", "XMN": "厦门",
    "HAK": "海口", "SYX": "三亚", "TAO": "青岛", "DLC": "大连",
    "SHE": "沈阳", "HRB": "哈尔滨", "CGQ": "长春", "TNA": "济南",
    "CGO": "郑州", "TYN": "太原", "HET": "呼和浩特", "URC": "乌鲁木齐",
    "LHW": "兰州", "INC": "银川", "XNN": "西宁", "KWE": "贵阳",
    "NNG": "南宁", "FOC": "福州", "KHN": "南昌", "HFE": "合肥",
    "WNZ": "温州", "NGB": "宁波", "ZUH": "珠海", "SWA": "揭阳",
    "WUX": "无锡", "NTG": "南通", "YCU": "运城", "DLU": "大理",
    "LJG": "丽江", "JHG": "西双版纳", "YBP": "宜宾", "MIG": "绵阳",
    "WDS": "十堰", "EHU": "鄂州", "WHA": "芜湖", "CIH": "长治",
    "HLH": "乌兰浩特", "JUZ": "衢州", "HNY": "衡阳", "TSN": "天津",
    "SJW": "石家庄", "BAV": "包头", "HLD": "海拉尔", "LXA": "拉萨",
    # HK / MO / TW
    "HKG": "香港", "MFM": "澳门", "TPE": "台北桃园", "TSA": "台北松山", "KHH": "高雄",
    # International
    "HND": "东京羽田", "NRT": "东京成田", "KIX": "大阪关西", "NGO": "名古屋",
    "FUK": "福冈", "CTS": "札幌", "ICN": "首尔仁川", "GMP": "首尔金浦",
    "PUS": "釜山", "CJU": "济州", "UBN": "乌兰巴托", "FNJ": "平壤",
    "SIN": "新加坡", "BKK": "曼谷素万那普", "DMK": "曼谷廊曼", "HKT": "普吉",
    "KUL": "吉隆坡", "BKI": "亚庇", "PEN": "槟城", "SGN": "胡志明市",
    "HAN": "河内", "DAD": "岘港", "MNL": "马尼拉", "CRK": "克拉克",
    "BWN": "斯里巴加湾市", "CGK": "雅加达", "DPS": "巴厘岛", "PNH": "金边",
    "VTE": "万象", "RGN": "仰光", "DEL": "新德里", "BOM": "孟买",
    "ISB": "伊斯兰堡", "KHI": "卡拉奇", "CMB": "科伦坡", "DAC": "达卡",
    "KTM": "加德满都", "DXB": "迪拜", "AUH": "阿布扎比", "DOH": "多哈",
    "RUH": "利雅得", "JED": "吉达", "BAH": "巴林", "MCT": "马斯喀特",
    "IKA": "德黑兰", "IST": "伊斯坦布尔", "ADD": "亚的斯亚贝巴", "CAI": "开罗",
    "CMN": "卡萨布兰卡", "ALG": "阿尔及尔", "NBO": "内罗毕", "JNB": "约翰内斯堡",
    "AMS": "阿姆斯特丹", "CDG": "巴黎戴高乐", "LHR": "伦敦希思罗", "LGW": "伦敦盖特威克",
    "FRA": "法兰克福", "MUC": "慕尼黑", "ZRH": "苏黎世", "GVA": "日内瓦",
    "VIE": "维也纳", "MAD": "马德里", "BCN": "巴塞罗那", "FCO": "罗马",
    "MXP": "米兰", "BRU": "布鲁塞尔", "LUX": "卢森堡", "WAW": "华沙",
    "HEL": "赫尔辛基", "ARN": "斯德哥尔摩", "CPH": "哥本哈根", "BEG": "贝尔格莱德",
    "BUD": "布达佩斯", "ATH": "雅典", "MSQ": "明斯克",
    "SVO": "莫斯科谢列梅捷沃", "VKO": "莫斯科伏努科沃", "DME": "莫斯科多莫杰多沃",
    "LED": "圣彼得堡", "OVB": "新西伯利亚", "IKT": "伊尔库茨克",
    "KJA": "克拉斯诺亚尔斯克", "SVX": "叶卡捷琳堡", "VVO": "符拉迪沃斯托克(海参崴)",
    "KHV": "哈巴罗夫斯克", "ALA": "阿拉木图", "NQZ": "阿斯塔纳",
    "TAS": "塔什干", "GYD": "巴库", "ASB": "阿什哈巴德", "FRU": "比什凯克",
    "IAD": "华盛顿杜勒斯", "JFK": "纽约肯尼迪", "EWR": "纽约纽瓦克",
    "LAX": "洛杉矶", "SFO": "旧金山", "SEA": "西雅图", "ORD": "芝加哥",
    "DFW": "达拉斯", "DTW": "底特律", "BOS": "波士顿", "ADW": "安德鲁斯空军基地",
    "YVR": "温哥华", "YYZ": "多伦多", "YUL": "蒙特利尔", "HAV": "哈瓦那",
    "MEX": "墨西哥城", "GRU": "圣保罗", "SYD": "悉尼", "MEL": "墨尔本", "AKL": "奥克兰",
}

COUNTRY_ZH = {
    "China": "中国", "Hong Kong": "中国香港", "Macao": "中国澳门", "Taiwan": "中国台湾",
    "Japan": "日本", "South Korea": "韩国", "North Korea": "朝鲜", "Mongolia": "蒙古",
    "Singapore": "新加坡", "Thailand": "泰国", "Malaysia": "马来西亚", "Vietnam": "越南",
    "Philippines": "菲律宾", "Brunei": "文莱", "Indonesia": "印度尼西亚", "Cambodia": "柬埔寨",
    "Laos": "老挝", "Myanmar": "缅甸", "India": "印度", "Pakistan": "巴基斯坦",
    "Sri Lanka": "斯里兰卡", "Bangladesh": "孟加拉国", "Nepal": "尼泊尔",
    "United Arab Emirates": "阿联酋", "Qatar": "卡塔尔", "Saudi Arabia": "沙特阿拉伯",
    "Iran": "伊朗", "Turkey": "土耳其", "Ethiopia": "埃塞俄比亚", "Egypt": "埃及",
    "Morocco": "摩洛哥", "Algeria": "阿尔及利亚", "South Africa": "南非",
    "Netherlands": "荷兰", "France": "法国", "United Kingdom": "英国", "Germany": "德国",
    "Switzerland": "瑞士", "Austria": "奥地利", "Spain": "西班牙", "Italy": "意大利",
    "Belgium": "比利时", "Luxembourg": "卢森堡", "Poland": "波兰", "Finland": "芬兰",
    "Sweden": "瑞典", "Denmark": "丹麦", "Serbia": "塞尔维亚", "Hungary": "匈牙利",
    "Greece": "希腊", "Belarus": "白俄罗斯", "Russia": "俄罗斯",
    "Kazakhstan": "哈萨克斯坦", "Uzbekistan": "乌兹别克斯坦", "Azerbaijan": "阿塞拜疆",
    "Turkmenistan": "土库曼斯坦", "United States": "美国", "Canada": "加拿大",
    "Cuba": "古巴", "Mexico": "墨西哥", "Brazil": "巴西", "Australia": "澳大利亚",
    "New Zealand": "新西兰",
}

LIVERY_PHRASES_ZH = [
    ("picturesque & dynamic zhejiang livery", "「诗画江南·活力浙江」彩绘"),
    ("picturesque and dynamic zhejiang livery", "「诗画江南·活力浙江」彩绘"),
    ("national museum of china", "「国博号」主题彩绘"),
    ("harbin 2025 asian winter games", "「哈尔滨 2025 亚冬会」主题彩绘"),
    ("asian winter games livery", "「亚冬会」主题彩绘"),
    ("star alliance livery", "「星空联盟」涂装"),
    ("star alliance", "「星空联盟」涂装"),
    ("skyteam livery", "「天合联盟」涂装"),
    ("skyteam", "「天合联盟」涂装"),
    ("oneworld livery", "「寰宇一家」涂装"),
    ("oneworld", "「寰宇一家」涂装"),
    ("spdb leasing sticker", "浦银金租特别贴纸"),
    ("wuliangye livery", "「五粮液」主题彩绘"),
    ("beautiful sichuan livery", "「秀美四川」彩绘"),
    ("city of wuhu livery", "「芜湖号」全机彩绘"),
    ("yunnan peacock livery", "东航云南「孔雀」彩绘"),
    ("panda route livery", "「熊猫之路」彩绘"),
    ("kung fu panda livery", "「功夫熊猫」彩绘"),
    ("smiling china livery", "「微笑中国」彩绘"),
    ("love china livery", "「爱China」彩绘"),
    ("ciie livery", "「进博号」主题彩绘"),
    ("china international import expo", "「进博号」主题彩绘"),
    ("united dream livery", "「联合梦想号」彩绘"),
    ("toy story livery", "迪士尼「玩具总动员」彩绘"),
    ("zootopia livery", "迪士尼「疯狂动物城」彩绘"),
    ("duffy", "迪士尼「达菲」主题彩绘"),
    ("frozen livery", "迪士尼「冰雪奇缘」彩绘"),
    ("pixar livery", "迪士尼「皮克斯」彩绘"),
    ("mickey", "迪士尼「米奇」主题彩绘"),
    ("pikachu jet", "「皮卡丘」主题彩绘"),
    ("pokemon", "「宝可梦」主题彩绘"),
    ("hello kitty", "「Hello Kitty」三丽鸥彩绘"),
    ("orange pride", "「橙色骄傲」彩绘"),
    ("retro livery", "复古经典涂装"),
    ("peony livery", "「牡丹」系列彩绘"),
    ("universiade", "「大运号」主题彩绘"),
    ("national games", "「全运会」主题彩绘"),
    ("genshin", "「原神号」彩绘"),
]


def zh_airline(airline_raw: str, iata: str = "", owner_raw: str = "") -> str:
    raw = (airline_raw or "").strip()
    base = raw.split("(")[0].strip() if "(" in raw else raw
    if not base and owner_raw:
        base = owner_raw.strip()

    low_full = raw.lower()
    low_base = base.lower()
    if low_full in AIRLINE_NAME_OVERRIDES:
        return AIRLINE_NAME_OVERRIDES[low_full]
    if low_base in AIRLINE_NAME_OVERRIDES:
        return AIRLINE_NAME_OVERRIDES[low_base]
    code = (iata or "").strip().upper()
    if code in AIRLINE_BY_IATA:
        return AIRLINE_BY_IATA[code]
    # Preserve original if already Chinese or unknown foreign charter/VIP operator
    return base or owner_raw or "未知/私人"


def zh_origin(iata: str, city_en: str = "", country_en: str = "") -> str:
    code = (iata or "").strip().upper()
    city = AIRPORT_CITY_ZH.get(code)
    if city:
        return f"{city} ({code})"
    if city_en:
        c_zh = COUNTRY_ZH.get(country_en, country_en)
        suffix = f" · {c_zh}" if c_zh and c_zh != "中国" else ""
        return f"{city_en}{suffix} ({code})" if code else f"{city_en}{suffix}"
    return code or "未知"


def zh_country(country_en: str) -> str:
    return COUNTRY_ZH.get((country_en or "").strip(), country_en or "海外")


def zh_livery(raw_text: str) -> str:
    txt = (raw_text or "").strip()
    if not txt:
        return ""
    if any("\u4e00" <= ch <= "\u9fff" for ch in txt):
        return txt
    low = txt.lower()
    for pat, zh in LIVERY_PHRASES_ZH:
        if pat in low:
            return zh
    # Graceful fallback for unseen English livery names: translate common terms + keep original
    zh_guess = txt
    zh_guess = re.sub(r"\bLivery\b", "彩绘", zh_guess, flags=re.IGNORECASE)
    zh_guess = re.sub(r"\bSticker\b", "特别贴纸", zh_guess, flags=re.IGNORECASE)
    zh_guess = re.sub(r"\bSpecial\b", "特别版", zh_guess, flags=re.IGNORECASE)
    zh_guess = re.sub(r"\bAnniversary\b", "周年纪念", zh_guess, flags=re.IGNORECASE)
    zh_guess = re.sub(r"\bCity of\b", "", zh_guess, flags=re.IGNORECASE).strip()
    return f"{zh_guess}（{txt}）" if zh_guess != txt else f"特别涂装：{txt}"


def zh_aircraft(ac_text: str, ac_code: str = "") -> str:
    txt = (ac_text or "").strip()
    if not txt:
        code = (ac_code or "").strip().upper()
        code_map = {
            "A388": "空客 A380-800", "388": "空客 A380-800",
            "B748": "波音 747-8", "748": "波音 747-8", "74N": "波音 747-8F",
            "B744": "波音 747-400", "744": "波音 747-400", "74Y": "波音 747-400F",
            "A35K": "空客 A350-1000", "351": "空客 A350-1000",
            "A339": "空客 A330-900neo", "339": "空客 A330-900neo",
            "A338": "空客 A330-800neo", "B78X": "波音 787-10", "781": "波音 787-10",
            "B789": "波音 787-9", "B788": "波音 787-8",
            "B77W": "波音 777-300ER", "B772": "波音 777-200ER", "B77F": "波音 777F",
            "B763": "波音 767-300", "763": "波音 767-300",
            "75F": "波音 757F 全货机", "B752": "波音 757-200",
            "B738": "波音 737-800", "B737": "波音 737-700", "73F": "波音 737F 货机",
            "A359": "空客 A350-900", "A333": "空客 A330-300", "A332": "空客 A330-200",
            "A321": "空客 A321", "A21N": "空客 A321neo",
            "A320": "空客 A320", "A20N": "空客 A320neo", "A319": "空客 A319",
            "E190": "巴航工业 E190", "C919": "国产大飞机 C919",
        }
        return code_map.get(code, code or "未知机型")
    out = txt
    out = re.sub(r"^Boeing\b", "波音", out)
    out = re.sub(r"^Airbus\b", "空客", out)
    out = re.sub(r"^Comac\b", "国产", out, flags=re.IGNORECASE)
    out = re.sub(r"^Embraer\b", "巴航工业", out)
    out = re.sub(r"^Antonov\b", "安东诺夫", out)
    out = re.sub(r"^Ilyushin\b", "伊留申", out)
    out = re.sub(r"^Tupolev\b", "图波列夫", out)
    out = re.sub(r"^McDonnell Douglas\b", "麦道", out)
    out = re.sub(r"^Gulfstream\b", "湾流", out)
    out = re.sub(r"^Bombardier\b", "庞巴迪", out)
    out = re.sub(r"^Dassault\b", "达索", out)
    out = out.replace("Dreamliner", "梦想客机")
    return out
