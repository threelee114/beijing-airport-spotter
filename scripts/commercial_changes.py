"""Compare the commercial arrivals shown in successive digests."""
import re
from datetime import datetime


# Equivalent equipment codes found in schedules, plus family-only designations.
FAMILY_MODELS = {
    "747": "747", "B747": "747", "741": "747-100", "B741": "747-100",
    "742": "747-200", "B742": "747-200", "743": "747-300", "B743": "747-300",
    "744": "747-400", "B744": "747-400", "74Y": "747-400F", "74F": "747F",
    "748": "747-8", "B748": "747-8", "74N": "747-8F", "B74S": "747SP",
    "74H": "747-8", "74J": "747-400", "74E": "747-400 Combi", "74M": "747 Combi",
    "74T": "747-100F", "74C": "747-200", "74X": "747-200F", "74D": "747-300 Combi",
    "74L": "747SP", "74R": "747SR", "B74R": "747SR", "B74D": "747-400D", "BLCF": "747-400LCF",
    "380": "A380", "A380": "A380", "388": "A380-800", "A388": "A380-800",
    "340": "A340", "A340": "A340", "342": "A340-200", "A342": "A340-200",
    "343": "A340-300", "A343": "A340-300", "345": "A340-500", "A345": "A340-500",
    "346": "A340-600", "A346": "A340-600",
}


def commercial_number(number, iata):
    return len(iata) == 2 and number.startswith(iata) and bool(re.fullmatch(r"[0-9]{1,4}[A-Z]?", number[2:]))


def family_model(code, description):
    if code in FAMILY_MODELS:
        return FAMILY_MODELS[code]
    match = re.search(r"\bB?(747(?:SP|SR|-[0-9A-Z]+)?|A(?:340|380)(?:-[0-9A-Z]+)?)\b", f"{description} {code}".upper())
    return match.group(1) if match else ""


def compare_assignment(previous, current, tz):
    """Keep the last confirmed registration while a feed temporarily omits it."""
    current = current.copy()
    messages = []
    old_reg, reg = previous["reg"], current["reg"]
    if previous["livery"]:
        if not reg:
            current.update(reg=old_reg, livery=previous["livery"], pending=True)
            if not previous.get("pending"):
                messages.append(f"原定彩绘 {previous['livery']}，注册号待确认")
        elif old_reg and reg != old_reg:
            if current["livery"]:
                messages.append(f"彩绘换机：{previous['livery']}（{old_reg}）→ {current['livery']}（{reg}）")
            else:
                messages.append(f"原定彩绘已换走：{previous['livery']}（{old_reg}）→ {reg}")
        elif not old_reg and not current["livery"]:
            current.update(reg="", livery=previous["livery"], pending=True)
            if not previous.get("pending"):
                messages.append(f"当前注册号 {reg}，原定彩绘是否更换待确认")
        else:
            current["livery"] = current["livery"] or previous["livery"]
            if previous.get("pending"):
                messages.append(f"注册号已确认：{reg}")
    elif current["livery"]:
        label = "换上彩绘" if reg and old_reg and reg != old_reg else "新识别彩绘"
        messages.append(f"{label}：{current['livery']}（{reg or '注册号待确认'}）")

    old_model = previous["model"]
    if not current["equipment"]:
        current["model"] = old_model
    elif old_model != current["model"]:
        if current["model"]:
            messages.append(f"换入重点机型：{old_model or previous['equipment'] or '原机型待定'} → {current['model']}")
        elif old_model:
            messages.append(f"重点机型已换走：{old_model} → {current['equipment']}")
    elif old_model and old_reg and reg and reg != old_reg and not (previous["livery"] or current["livery"]):
        messages.append(f"重点机型换机：{old_model}，{old_reg} → {reg}")

    before, after = previous["arrival"], current["arrival"]
    if current["estimated"] and after // 60 != before // 60:
        delta = after // 60 - before // 60
        when = datetime.fromtimestamp(after, tz).strftime("%m-%d %H:%M")
        messages.append(f"预计到达{'推迟' if delta > 0 else '提前'} {abs(delta)} 分钟，现为 {when}")
    elif previous["estimated"] and not current["estimated"]:
        current.update(arrival=before, estimated=True)

    if not any((previous["livery"], current["livery"], old_model, current["model"])):
        messages.clear()
    return current, messages
