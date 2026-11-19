"""Model for gta6-twitch-ccu-forecast-01: comparables shape, similarity weighting, shrinkage, and calibrated log quantiles."""

import math
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

LEVELS = [0.05, 0.25, 0.5, 0.75, 0.95]
Z = [-1.645, -0.674, 0, 0.674, 1.645]
BASELINE_SIGMA = 0.15


def round2(x: float) -> float | int:
    scaled = x * 100
    whole = math.floor(scaled)
    if scaled - whole >= 0.5:
        whole += 1
    value = whole / 100
    return int(value) if value.is_integer() else value


def parse_hourly(comp, day_start_str):
    if not comp.get('hourly') or not day_start_str:
        return None
    try:
        ds = datetime.fromisoformat(day_start_str.replace('Z', '+00:00'))
    except Exception:
        return None

    hourly_map = {item['from']: item.get('viewers') for item in comp['hourly'] if item.get('viewers') is not None}
    
    viewers_h = []
    for h in range(1, 25):
        t = ds + timedelta(hours=h-1)
        t_str = t.strftime('%Y-%m-%dT%H:%M:%SZ')
        v = hourly_map.get(t_str)
        viewers_h.append(v)

    # Check hour 1
    if viewers_h[0] is None or viewers_h[0] <= 0:
        return None

    # Interpolate missing values in log space if any
    # First convert to log or handle missing
    log_v = []
    for v in viewers_h:
        if v is not None and v > 0:
            log_v.append(math.log(v))
        else:
            log_v.append(None)

    # If too many missing (> 4), reject
    if log_v.count(None) > 4:
        return None

    # Simple linear interpolation for missing log values
    n = len(log_v)
    for i in range(n):
        if log_v[i] is None:
            # find previous valid
            prev_idx = i - 1
            while prev_idx >= 0 and log_v[prev_idx] is None:
                prev_idx -= 1
            # find next valid
            next_idx = i + 1
            while next_idx < n and log_v[next_idx] is None:
                next_idx += 1
            
            if prev_idx >= 0 and next_idx < n:
                # linear interpolation
                fraction = (i - prev_idx) / (next_idx - prev_idx)
                log_v[i] = log_v[prev_idx] * (1 - fraction) + log_v[next_idx] * fraction
            elif prev_idx >= 0:
                log_v[i] = log_v[prev_idx]
            elif next_idx < n:
                log_v[i] = log_v[next_idx]
            else:
                log_v[i] = log_v[0] # fallback

    v1 = math.exp(log_v[0])
    log_ratios = [log_v[h-1] - log_v[0] for h in range(2, 25)]
    return v1, log_ratios


def extract_keywords(text):
    if not text:
        return set()
    words = text.lower().replace('/', ' ').replace(',', ' ').split()
    return set(w for w in words if len(w) > 2)


def extract_platforms(text):
    if not text:
        return set()
    text_lower = text.lower()
    platforms = set()
    if 'pc' in text_lower or 'windows' in text_lower:
        platforms.add('pc')
    if 'ps4' in text_lower or 'playstation 4' in text_lower:
        platforms.add('ps4')
    if 'ps5' in text_lower or 'playstation 5' in text_lower:
        platforms.add('ps5')
    if 'xbox' in text_lower:
        platforms.add('xbox')
    if 'switch' in text_lower:
        platforms.add('switch')
    return platforms


def compute_weight(target_p1, target_notes, comp, dt_ref=None):
    comp_p1, _ = parse_hourly(comp, comp.get('day_start'))
    if comp_p1 is None:
        return 0.0

    # Scale weight
    scale_diff = abs(math.log(comp_p1) - math.log(target_p1))
    w_scale = math.exp(-0.4 * scale_diff)

    # Unlock weight
    target_kw = extract_keywords(target_notes)
    comp_kw = extract_keywords(comp.get('unlock', ''))
    common_kw = target_kw.intersection(comp_kw)
    w_unlock = 1.0 + 0.3 * len(common_kw)

    # Platform weight
    target_plat = extract_platforms(target_notes)
    comp_plat = extract_platforms(comp.get('platforms', ''))
    if target_plat and comp_plat:
        union = target_plat.union(comp_plat)
        intersection = target_plat.intersection(comp_plat)
        jaccard = len(intersection) / len(union) if union else 0.0
        w_plat = 1.0 + 1.5 * jaccard
    else:
        w_plat = 1.0

    # Recency weight (half-life 3 years)
    w_recency = 1.0
    comp_day_start = comp.get('day_start')
    if comp_day_start and dt_ref:
        try:
            dt_comp = datetime.fromisoformat(comp_day_start.replace('Z', '+00:00'))
            age_years = (dt_ref - dt_comp).total_seconds() / (365.25 * 24 * 3600)
            w_recency = 2.0 ** (-age_years / 3.0)
        except Exception:
            pass

    return w_scale * w_unlock * w_plat * w_recency


def weighted_median(values_weights):
    # values_weights is list of (val, weight)
    vw = [vw for vw in values_weights if vw[1] > 0]
    if not vw:
        return 0.0
    vw.sort(key=lambda x: x[0])
    total_w = sum(w for v, w in vw)
    if total_w <= 0:
        return sum(v for v, w in vw) / len(vw)
    
    half_w = total_w / 2.0
    cum_w = 0.0
    for v, w in vw:
        cum_w += w
        if cum_w >= half_w:
            return v
    return vw[-1][0]


def weighted_percentile(values_weights, q):
    vw = [vw for vw in values_weights if vw[1] > 0]
    if not vw:
        return 0.0
    vw.sort(key=lambda x: x[0])
    total_w = sum(w for v, w in vw)
    if total_w <= 0:
        return vw[0][0]
    
    target_w = q * total_w
    cum_w = 0.0
    for v, w in vw:
        cum_w += w
        if cum_w >= target_w:
            return v
    return vw[-1][0]


def forecast_case(case: dict, name: str) -> dict:
    if case["levels"] != LEVELS:
        raise ValueError(f"{name} asks for levels {case['levels']}, not {LEVELS}")
    first = next((k for k in case["known"] if k["hour"] == 1), None)
    if first is None:
        raise ValueError(f"{name} has no hour-1 print")
    p1 = max(1, first["viewers"])
    notes = case.get("notes", "")

    comparables = case.get("comparables", [])
    valid_comp_dates = []
    for comp in comparables:
        ds = comp.get('day_start')
        if ds:
            try:
                valid_comp_dates.append(datetime.fromisoformat(ds.replace('Z', '+00:00')))
            except Exception:
                pass

    ref_date_str = case.get('day_start') or case.get('date')
    dt_ref = None
    if ref_date_str:
        try:
            dt_ref = datetime.fromisoformat(ref_date_str.replace('Z', '+00:00'))
        except Exception:
            pass
    if dt_ref is None and valid_comp_dates:
        dt_ref = max(valid_comp_dates)
    if dt_ref is None:
        dt_ref = datetime.now(timezone.utc)

    valid_comps = []
    for comp in comparables:
        res = parse_hourly(comp, comp.get('day_start'))
        if res is not None:
            comp_p1, log_ratios = res
            w = compute_weight(p1, notes, comp, dt_ref)
            if w > 0:
                valid_comps.append((w, log_ratios))

    # If no valid comparables, fallback to persistence
    if not valid_comps:
        return {"hours": [{"hour": row["hour"], "q": persistence_quantiles(p1, row["hour"])} for row in case["forecast"]]}

    # Total effective sample size
    sum_w = sum(w for w, lr in valid_comps)
    sum_w2 = sum(w**2 for w, lr in valid_comps)
    n_eff = (sum_w ** 2) / sum_w2 if sum_w2 > 0 else 0
    shrink = n_eff / (n_eff + 5.0)

    # Compute shape r(h) and dispersion sigma(h) for each hour index h_idx (0 to 22, representing hours 2..24)
    r_curves = []
    sigma_curves = []

    for h_idx in range(23):
        # h from 2 to 24 corresponds to h_idx 0 to 22 in log_ratios
        lr_weights = [(lr[h_idx], w) for w, lr in valid_comps]
        
        # Weighted median log ratio
        wm = weighted_median(lr_weights)
        r_h = shrink * wm
        r_curves.append(r_h)

        # Weighted IQR for dispersion
        q25 = weighted_percentile(lr_weights, 0.25)
        q75 = weighted_percentile(lr_weights, 0.75)
        iqr = q75 - q25
        sigma_iqr = iqr / 1.349 if iqr > 0 else 0.0

        # Floor by persistence sigma
        h = h_idx + 2
        base_sigma = BASELINE_SIGMA * math.sqrt(h - 1)
        sig = max(sigma_iqr, base_sigma)
        sigma_curves.append(sig)

    # Smooth sigma across hours (moving average window 3)
    smoothed_sigma = []
    for i in range(len(sigma_curves)):
        window = sigma_curves[max(0, i-1):min(len(sigma_curves), i+2)]
        smoothed_sigma.append(sum(window) / len(window))

    hours_out = []
    for h_idx, row in enumerate(case["forecast"]):
        h = row["hour"]
        r_h = r_curves[h_idx]
        sig = smoothed_sigma[h_idx]

        q50_val = p1 * math.exp(r_h)
        
        raw_qs = []
        for z in Z:
            q_val = q50_val * math.exp(z * sig)
            # clamps
            q_val = max(1e-3, min(1e9, q_val))
            raw_qs.append(q_val)

        # Enforce non-decreasing quantiles
        raw_qs.sort()

        hours_out.append({
            "hour": h,
            "q": [round2(q) for q in raw_qs]
        })

    return {"hours": hours_out}


def persistence_quantiles(p1: float, h: int) -> list[float | int]:
    sig = BASELINE_SIGMA * math.sqrt(h - 1)
    return [round2(p1 * math.exp(z * sig)) for z in Z]
