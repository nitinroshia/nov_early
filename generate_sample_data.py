#!/usr/bin/env python3
"""
Seeded sample-data generator for the stock-UI chart template.

Fictional company: Veltrix Engineering Ltd (VELT), INR crore, FY ends 31 March.
  - 12 fiscal years (FY2015-FY2026) + TTM
  - 50 quarters (Q1 FY2015 - Q2 FY2027)
  - ~3,000 trading days of OHLCV + Nifty (2014-11-17 -> 2026-11-13)
  - ratio history, monthly valuation history, quarterly shareholding history
  - 30-peer universe with 12Y history + monthly returns
Field codes mirror RELI_data.json / the master hierarchy.

Usage:  python generate_sample_data.py --seed 42 --out sample_data
"""
import argparse, json, math, os, bisect
from datetime import date, timedelta
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("--seed", type=int, default=42)
ap.add_argument("--out", default="sample_data")
A = ap.parse_args()
rng = np.random.default_rng(A.seed)
N = lambda sd=1.0, mean=0.0: float(rng.normal(mean, sd))

def cagr(a, b, n):
    if a is None or b is None or a <= 0 or b <= 0 or n <= 0:
        return None
    return ((b / a) ** (1.0 / n) - 1) * 100

def clean(o, nd=2):
    if isinstance(o, dict):
        return {k: clean(v, nd) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v, nd) for v in o]
    if isinstance(o, (np.floating, float)):
        o = float(o)
        if math.isnan(o) or math.isinf(o):
            return None
        return round(o, nd)
    if isinstance(o, np.integer):
        return int(o)
    return o

def iso(d): return d.isoformat() + "T00:00:00.000Z"

# =====================================================================
# 1. ANNUAL MODEL (FY2014 internal opening year, FY2015-FY2026 output)
# =====================================================================
FYS = list(range(2014, 2027))
growth_base = {2015: 8.2, 2016: 8.0, 2017: 6.0, 2018: 12.0, 2019: 16.0, 2020: 4.0,
               2021: -11.0, 2022: 26.0, 2023: 21.0, 2024: 12.0, 2025: 10.0, 2026: 13.0}
m_base = dict(zip(FYS, [16.2, 16.5, 16.8, 17.4, 17.9, 18.3, 17.0, 14.5, 17.6, 18.6, 19.3, 19.9, 20.4]))
capex_pct = dict(zip(FYS[1:], [9.0, 8.2, 7.6, 7.5, 8.0, 7.0, 4.5, 5.5, 7.0, 8.0, 8.5, 8.5]))
payout_p = dict(zip(FYS[1:], [0.16, 0.17, 0.17, 0.18, 0.19, 0.18, 0.10, 0.15, 0.19, 0.21, 0.23, 0.24]))
de_target = dict(zip(FYS, [0.60, 0.62, 0.60, 0.57, 0.55, 0.62, 0.66, 0.58, 0.46, 0.40, 0.34, 0.28, 0.24]))
shares = {fy: 125.0 * 1.0015 ** (fy - 2014) for fy in FYS}

rev = {2014: 8500.0}
growth = {}
for fy in FYS[1:]:
    growth[fy] = growth_base[fy] + N(0.7)
    rev[fy] = rev[fy - 1] * (1 + growth[fy] / 100)

# --- cost structure
C = {}
for i, fy in enumerate(FYS):
    rv = rev[fy]
    raw = rv * (51.5 + (1.5 if fy == 2019 else 0) + (2.2 if fy == 2023 else 0) + N(0.7)) / 100
    pfc = rv * (2.6 + N(0.15)) / 100
    epc = rv * (8.6 + (2.2 if fy == 2021 else 0) - 0.03 * i + N(0.15)) / 100
    sga = rv * (7.0 + (1.0 if fy == 2021 else 0) + N(0.15)) / 100
    ebitda = rv * (m_base[fy] + N(0.25)) / 100
    ope = rv - raw - pfc - epc - sga - ebitda
    assert ope > 0, (fy, ope)
    C[fy] = dict(raw=raw, pfc=pfc, epc=epc, sga=sga, ope=ope, ebitda=ebitda)

dso = {fy: 60 + N(2.5) + (10 if fy == 2021 else 0) + (2 if fy == 2022 else 0) for fy in FYS}
dio = {fy: 80 + N(3) + (14 if fy == 2021 else 0) + (4 if fy == 2023 else 0) for fy in FYS}
dpo = {fy: 60 + N(2.5) - (3 if fy == 2021 else 0) for fy in FYS}
taxr = {fy: (31 + N(1.2)) if fy <= 2019 else (27.5 if fy == 2020 else 25.8 + N(1.0)) for fy in FYS}
intr = {fy: 9.2 - (9.2 - 8.0) * (fy - 2014) / 12 + (-0.7 if fy == 2021 else 0) + N(0.1) for fy in FYS}

IS, BS, CF = {}, {}, {}
for fy in FYS:
    rv = rev[fy]; c = C[fy]; cogs = c["raw"] + c["pfc"]
    prev = BS.get(fy - 1)
    # --- opening balance sheet for FY2014
    if fy == 2014:
        b = {}
        b["rec"] = dso[fy] * rv / 365; b["inv"] = dio[fy] * cogs / 365; b["ap"] = dpo[fy] * cogs / 365
        b["oca"] = 0.035 * rv; b["ppe"] = 0.85 * rv; b["gint"] = 380.0; b["lti"] = 900.0
        b["dta"] = 0.003 * rv; b["otha"] = 0.02 * rv
        b["coms"] = 2 * shares[fy]; b["apic"] = 1800.0; b["res"] = 4600.0
        b["mi"] = 0.022 * (b["coms"] + b["apic"] + b["res"])
        b["teq"] = b["coms"] + b["apic"] + b["res"] + b["mi"]
        b["debt"] = de_target[fy] * b["teq"]; b["ltd"] = 0.68 * b["debt"]; b["std"] = b["debt"] - b["ltd"]
        b["ocl_other"] = 0.05 * rv; b["ocl"] = b["ocl_other"] + b["std"]; b["tcl"] = b["ap"] + b["ocl"]
        b["dtl"] = 0.045 * b["ppe"]; b["othl"] = 0.013 * rv
        b["ncl"] = b["ltd"] + b["dtl"] + b["othl"]; b["totl"] = b["tcl"] + b["ncl"]
        noncash = b["rec"] + b["inv"] + b["oca"] + b["ppe"] + b["gint"] + b["lti"] + b["dta"] + b["otha"]
        b["cash"] = b["totl"] + b["teq"] - noncash
        assert b["cash"] > 0, b["cash"]
        dep = 0.047 * rv; intexp = 0.092 * 0.95 * b["debt"]; othinc = 0.06 * 0.9 * (b["cash"] + 0.6 * b["lti"])
    else:
        dep = 0.055 * prev["ppe"]; intexp = intr[fy] / 100 * prev["debt"]
        othinc = 0.06 * (prev["cash"] + 0.6 * prev["lti"])
    pbit = c["ebitda"] - dep; ioi = intexp - othinc; pbt = pbit - ioi
    tax = pbt * taxr[fy] / 100; ni = pbt - tax
    eps = ni / shares[fy]
    pay = payout_p.get(fy, 0.15); dps = pay * eps; div = dps * shares[fy]
    IS[fy] = dict(rev=rv, **c, dep=dep, pbit=pbit, intexp=intexp, ioi=ioi, pbt=pbt, tax=tax, ni=ni,
                  eps=eps, dps=dps, payout=pay, div=div, taxrate=taxr[fy], shares=shares[fy])
    if fy == 2014:
        BS[fy] = b; continue
    # --- roll-forward
    p = prev; b = {}
    b["rec"] = dso[fy] * rv / 365; b["inv"] = dio[fy] * cogs / 365; b["ap"] = dpo[fy] * cogs / 365
    b["oca"] = 0.035 * rv; b["ocl_other"] = (5.0 + N(0.2)) / 100 * rv
    b["otha"] = 0.02 * rv * (1 + N(0.03)); b["othl"] = 0.013 * rv * (1 + N(0.03)); b["dta"] = 0.003 * rv * (1 + N(0.1))
    capex = capex_pct[fy] / 100 * rv
    b["ppe"] = p["ppe"] + capex - dep
    b["gint"] = p["gint"] * 1.02 + {2019: 350.0, 2024: 500.0}.get(fy, 0.0)
    b["dtl"] = 0.045 * b["ppe"]
    b["res"] = p["res"] + ni - div
    b["coms"] = 2 * shares[fy]; b["apic"] = p["apic"]
    b["mi"] = 0.022 * (b["coms"] + b["apic"] + b["res"])
    b["teq"] = b["coms"] + b["apic"] + b["res"] + b["mi"]
    ciwc = -(b["rec"] - p["rec"]) - (b["inv"] - p["inv"]) - (b["oca"] - p["oca"]) + (b["ap"] - p["ap"]) + (b["ocl_other"] - p["ocl_other"])
    otherop = (b["dtl"] - p["dtl"]) - (b["dta"] - p["dta"]) + (b["othl"] - p["othl"]) - (b["otha"] - p["otha"])
    cfo = ni + dep + ciwc + otherop
    dgint = b["gint"] - p["gint"]
    dlti = float(np.clip(0.25 * max(0.0, cfo - capex - div) + N(40), -50, 700))
    b["lti"] = p["lti"] + dlti
    cfi = -capex - dgint - dlti
    dmi = b["mi"] - p["mi"]; diss = (b["coms"] + b["apic"]) - (p["coms"] + p["apic"])
    ddebt = de_target[fy] * b["teq"] - p["debt"]
    cash = p["cash"] + cfo + cfi - div + dmi + diss + ddebt
    minc = 0.05 * rv
    if cash < minc:
        ddebt += minc - cash; cash = minc
    b["cash"] = cash; b["debt"] = p["debt"] + ddebt
    ltd_share = (0.74 if fy == 2021 else 0.68) + N(0.03)
    b["ltd"] = ltd_share * b["debt"]; b["std"] = b["debt"] - b["ltd"]
    b["ocl"] = b["ocl_other"] + b["std"]; b["tcl"] = b["ap"] + b["ocl"]
    b["ncl"] = b["ltd"] + b["dtl"] + b["othl"]; b["totl"] = b["tcl"] + b["ncl"]
    BS[fy] = b
    cff = ddebt - div + dmi + diss
    CF[fy] = dict(ciwc=ciwc, cfo=cfo, capex=capex, cfi=cfi, div=div, cff=cff, ncic=cfo + cfi + cff, fcf=cfo - capex)

for fy in FYS:
    b = BS[fy]
    b["tca"] = b["cash"] + b["rec"] + b["inv"] + b["oca"]
    b["nca"] = b["ppe"] + b["gint"] + b["lti"] + b["dta"]
    b["tota"] = b["tca"] + b["nca"] + b["otha"]
    b["tlse"] = b["totl"] + b["teq"]
    b["bvps"] = (b["coms"] + b["apic"] + b["res"]) / shares[fy]
    assert abs(b["tota"] - b["tlse"]) < 1e-6, (fy, b["tota"], b["tlse"])
for fy in FYS[1:]:
    assert abs(CF[fy]["ncic"] - (BS[fy]["cash"] - BS[fy - 1]["cash"])) < 1e-6

# =====================================================================
# 2. QUARTERLY (FY2014 Q1 .. FY2027 Q2)
# =====================================================================
QEND = {1: (6, 30, -1), 2: (9, 30, -1), 3: (12, 31, -1), 4: (3, 31, 0)}
REP = {1: (8, 10, -1), 2: (11, 10, -1), 3: (2, 10, 0), 4: (5, 20, 0)}
qend = lambda fy, q: date(fy + QEND[q][2], QEND[q][0], QEND[q][1])
rdate = lambda fy, q: date(fy + REP[q][2], REP[q][0], REP[q][1])
ITEMS = ["rev", "raw", "pfc", "epc", "sga", "ope", "dep", "ioi"]
base_w = np.array([0.225, 0.245, 0.255, 0.275])
QD = {}
for fy in FYS:
    w_rev = base_w * (1 + rng.normal(0, 0.02, 4)); w_rev /= w_rev.sum()
    ws = {}
    for it in ITEMS:
        if it == "rev": w = w_rev
        elif it == "dep": w = np.array([.25] * 4) * (1 + rng.normal(0, 0.006, 4))
        elif it == "ioi": w = np.array([.25] * 4) * (1 + rng.normal(0, 0.04, 4))
        else: w = w_rev * (1 + rng.normal(0, 0.025, 4))
        ws[it] = w / w.sum()
    for q in range(1, 5):
        QD[(fy, q)] = {it: IS[fy][it] * ws[it][q - 1] for it in ITEMS}
        QD[(fy, q)]["_taxr"] = IS[fy]["tax"] / IS[fy]["pbt"]; QD[(fy, q)]["_sh"] = shares[fy]
sh27 = shares[2026] * 1.0008
for q, g in ((1, 11.5), (2, 10.8)):
    pq = QD[(2026, q)]; gq = g + N(1.0)
    d = {"rev": pq["rev"] * (1 + gq / 100)}
    for it in ("raw", "pfc", "epc", "sga", "ope"):
        d[it] = pq[it] / pq["rev"] * d["rev"] * (1 + N(0.01))
    d["dep"] = pq["dep"] * 1.06; d["ioi"] = pq["ioi"] * 0.95; d["_taxr"] = 0.256; d["_sh"] = sh27
    QD[(2027, q)] = d
QL = sorted(QD.keys())
for k in QL:
    d = QD[k]
    d["ebitda"] = d["rev"] - d["raw"] - d["pfc"] - d["epc"] - d["sga"] - d["ope"]
    d["opex"] = d["rev"] - d["ebitda"]
    d["pbit"] = d["ebitda"] - d["dep"]; d["pbt"] = d["pbit"] - d["ioi"]
    d["tax"] = d["pbt"] * d["_taxr"]; d["ni"] = d["pbt"] - d["tax"]; d["eps"] = d["ni"] / d["_sh"]
# reconcile quarterly vs annual
for fy in FYS:
    s = sum(QD[(fy, q)]["ni"] for q in range(1, 5))
    assert abs(s - IS[fy]["ni"]) < 1e-6 and abs(sum(QD[(fy, q)]["rev"] for q in range(1, 5)) - IS[fy]["rev"]) < 1e-6
qpos = {k: j for j, k in enumerate(QL)}
def ttm_sum(j, key): return sum(QD[QL[j - t]][key] for t in range(4))

# TTM annual row
jlast = len(QL) - 1
TTM = {k: ttm_sum(jlast, k) for k in ["rev", "raw", "pfc", "epc", "sga", "ope", "ebitda", "dep", "pbit", "ioi", "pbt", "tax", "ni"]}
TTM["eps"] = TTM["ni"] / sh27; TTM["dps"] = IS[2026]["dps"]; TTM["payout"] = TTM["dps"] / TTM["eps"]

# =====================================================================
# 3. MARKET SERIES
# =====================================================================
d0, d1 = date(2014, 11, 17), date(2026, 11, 13)
HOL = {(1, 26), (3, 25), (4, 14), (5, 1), (8, 15), (10, 2), (12, 25)}
days = []; d = d0
while d <= d1:
    if d.weekday() < 5 and (d.month, d.day) not in HOL: days.append(d)
    d += timedelta(1)
T = len(days)
EV = [("2015-03-04", "2015-04-30", -0.06, 1.2), ("2015-08-10", "2015-09-08", -0.09, 1.6),
      ("2016-01-01", "2016-02-29", -0.08, 1.3), ("2016-11-08", "2016-12-26", -0.05, 1.5),
      ("2018-01-29", "2018-04-02", -0.07, 1.3), ("2018-09-20", "2018-10-26", -0.12, 1.7),
      ("2020-02-20", "2020-03-23", -0.38, 3.5), ("2020-03-24", "2020-06-08", 0.34, 2.0),
      ("2021-12-01", "2022-06-17", -0.14, 1.4), ("2024-09-27", "2025-03-01", -0.13, 1.2),
      ("2026-03-01", "2026-04-15", -0.07, 1.4)]
mu = np.zeros(T); vm = np.ones(T); inev = np.zeros(T, bool)
for s, e, tot, v in EV:
    ids = [i for i, dd in enumerate(days) if s <= dd.isoformat() <= e]
    for i in ids: mu[i] = tot / len(ids); vm[i] = v; inev[i] = True
target = math.log(25500 / 8500)
mu[~inev] = (target - sum(e[2] for e in EV)) / (~inev).sum()
rn = mu + 0.0082 * vm * rng.standard_normal(T)
rn -= (rn.sum() - target) / T
NIF = 8500 * np.exp(np.cumsum(rn))
nr = np.expm1(rn) * 100

# pointer: latest reported quarter per day
rep_dates = [rdate(*k) for k in QL]
kk = np.zeros(T, int); kp = 0
for i, dd in enumerate(days):
    while kp + 1 < len(QL) and rep_dates[kp + 1] <= dd: kp += 1
    kk[i] = kp
assert kk[0] >= 3
report_days = {bisect.bisect_left(days, rd) for rd in rep_dates if d0 <= rd <= d1}
eps_ttm = np.array([ttm_sum(kk[i], "eps") for i in range(T)])
yfrac = np.array([dd.year + (dd.timetuple().tm_yday - 1) / 365 for dd in days])
anchor_pts = [(2014.8, 22), (2018.0, 27), (2020.0, 20), (2021.5, 32), (2023.0, 27), (2025.0, 29), (2026.95, 26)]
anchor = lambda y: float(np.interp(y, [a for a, _ in anchor_pts], [b for _, b in anchor_pts]))
anchor_pe = np.array([anchor(y) for y in yfrac])

P = np.zeros(T); lr = np.zeros(T)
P[0] = eps_ttm[0] * anchor_pe[0]
for i in range(1, T):
    beta = 1.05 + 0.15 * math.sin(2 * math.pi * i / 756)
    pull = -0.004 * (math.log(P[i - 1]) - math.log(eps_ttm[i] * anchor_pe[i]))
    jump = 0.0
    if i in report_days:
        k = kk[i]; g = QD[QL[k]]["ni"] / QD[QL[k - 4]]["ni"] - 1 if k >= 4 else 0.1
        jump = N(0.025) + 0.012 * np.sign(g)
    idio = 0.0105 * (vm[i] ** 0.8) * N()
    lr[i] = beta * rn[i] + idio + pull + jump
    P[i] = P[i - 1] * math.exp(lr[i])
r_pct = np.zeros(T); r_pct[1:] = (P[1:] / P[:-1] - 1) * 100

O = np.zeros(T); H = np.zeros(T); L = np.zeros(T); V = np.zeros(T)
for i in range(T):
    o = P[i - 1] * (1 + N(0.003)) if i else P[0]
    c = P[i]
    O[i] = o; H[i] = max(o, c) * (1 + abs(N(0.004))); L[i] = min(o, c) * (1 - abs(N(0.004)))
    base = 5.0e6 * (1 + 0.04 * (yfrac[i] - 2014.9))
    V[i] = base * math.exp(N(0.28)) * (1 + 35 * abs(r_pct[i] / 100)) * (2.2 if i in report_days else 1.0)
V = np.round(V).astype(np.int64)

# month-end indices (through Oct 2026) + final day
me = {}
for i, dd in enumerate(days): me[(dd.year, dd.month)] = i
month_keys = sorted(me)
month_idx = [me[k] for k in month_keys if k != (2026, 11)]
month_dates = [days[i] for i in month_idx]
mret_stock = [(P[month_idx[j]] / P[month_idx[j - 1]] - 1) * 100 for j in range(1, len(month_idx))]
mret_nifty = [(NIF[month_idx[j]] / NIF[month_idx[j - 1]] - 1) * 100 for j in range(1, len(month_idx))]
mret_dates = [month_dates[j] for j in range(1, len(month_idx))]
RF = 0.065

def risk_at(i):
    out = {}
    if i >= 252:
        s = r_pct[i - 251:i + 1] / 100; n = nr[i - 251:i + 1] / 100
        vol = s.std(ddof=1) * math.sqrt(252) * 100; voln = n.std(ddof=1) * math.sqrt(252) * 100
        out["12mVol"] = vol; out["12mVolN"] = vol / voln
        out["beta"] = float(np.cov(s, n)[0, 1] / n.var(ddof=1))
        w = P[i - 251:i + 1]; out["maxDrawdown"] = float((w / np.maximum.accumulate(w) - 1).min() * 100)
    if i >= 756:
        s = r_pct[i - 755:i + 1] / 100; n = nr[i - 755:i + 1] / 100
        out["3Ywsh"] = (s.mean() * 252 - RF) / (s.std(ddof=1) * math.sqrt(252))
        es, en = s - RF / 252, n - RF / 252
        bb = np.cov(es, en)[0, 1] / en.var(ddof=1)
        out["3Ywal"] = (es.mean() - bb * en.mean()) * 252 * 100
    return out

# =====================================================================
# 4. VALUATION HISTORY (monthly) + sector benchmarks
# =====================================================================
def fy_avail(dd): return dd.year if (dd.month, dd.day) >= (5, 20) else dd.year - 1
ind_pe_s = 0.0
sec_rows = {}
for i in month_idx + [T - 1]:
    ind_pe_s = 0.8 * ind_pe_s + N(1.2)
    pe_sec = anchor_pe[i] * 0.88 + ind_pe_s
    sec_rows[i] = dict(indpe=pe_sec, indpb=0.14 * pe_sec * (1 + N(0.03)), indps=0.10 * pe_sec * (1 + N(0.03)),
                       inddy=max(0.4, 1.25 - 0.012 * (pe_sec - 24) + N(0.04)),
                       sub_k=1.06 + N(0.02))

def val_at(i):
    dd = days[i]; fy = fy_avail(dd); k = kk[i]
    price = P[i]; sh = shares[fy]; mcap = price * sh
    b = BS[fy]; inc = IS[fy]; cf = CF.get(fy)
    eps_t = ttm_sum(k, "eps"); rev_t = ttm_sum(k, "rev"); ebitda_t = ttm_sum(k, "ebitda"); ebit_t = ttm_sum(k, "pbit")
    ev = mcap + b["debt"] - b["cash"]; ic = b["teq"] + b["debt"] - b["cash"]
    g = IS[fy]["eps"] / IS[fy - 1]["eps"] - 1 if fy > 2014 else 0.1
    est_g = float(np.clip(0.9 * g * 100, 5, 20))
    sc = sec_rows[i]; sub_pe = sc["indpe"] * sc["sub_k"]; sub_pb = sc["indpb"] * (sc["sub_k"] + 0.03)
    sub_ps = sc["indps"] * (sc["sub_k"] - 0.02); sub_dy = sc["inddy"] * (2 - sc["sub_k"])
    dy = inc["dps"] / price * 100
    out = dict(date=days[i].isoformat(), price=price, marketCap=mcap, ttmPe=price / eps_t, apef=price / inc["eps"],
               pef=price / (eps_t * (1 + est_g / 100)), pbr=price / b["bvps"], ps=mcap / inc["rev"],
               psf=mcap / (rev_t * (1 + est_g / 100)), priceBySales=mcap / rev_t, ev=ev, evebitd=ev / ebitda_t,
               evebit=ev / ebit_t, evByRev=ev / rev_t, evByIc=ev / ic,
               lcpCafFcf=(mcap / cf["fcf"]) if cf and cf["fcf"] > 0 else None,
               evCafFcf=(ev / cf["fcf"]) if cf and cf["fcf"] > 0 else None,
               priceCfoR=(mcap / cf["cfo"]) if cf and cf["cfo"] > 0 else None, divDps=dy,
               indpe=sc["indpe"], indpb=sc["indpb"], inddy=sc["inddy"], indps=sc["indps"],
               ped=(price / eps_t / sc["indpe"] - 1) * 100, pbd=(price / b["bvps"] / sc["indpb"] - 1) * 100,
               psfs=(mcap / inc["rev"] / sc["indps"] - 1) * 100, divSec=dy - sc["inddy"],
               subPe=sub_pe, subPb=sub_pb, subPs=sub_ps, subDy=sub_dy,
               pePremSi=(price / eps_t / sub_pe - 1) * 100, pbPremSi=(price / b["bvps"] / sub_pb - 1) * 100,
               psPremSi=(mcap / inc["rev"] / sub_ps - 1) * 100, dyPremSs=dy - sub_dy, estGrowth=est_g)
    return out
val_hist = [val_at(i) for i in month_idx]
val_now = val_at(T - 1)
def band(key):
    a = np.array([v[key] for v in val_hist if v[key] is not None])
    return {f"p{p}": float(np.percentile(a, p)) for p in (10, 25, 50, 75, 90)}
val_bands = {k: band(k) for k in ("ttmPe", "pbr", "evebitd", "priceBySales")}

# =====================================================================
# 5. ANNUAL RATIO HISTORY (groups 05 / 06 / 07 + FY-end valuation)
# =====================================================================
base_r = {}
for fy in FYS:
    i, b, c = IS[fy], BS[fy], CF.get(fy)
    pb = BS.get(fy - 1); avg = (lambda k: (b[k] + pb[k]) / 2) if pb else (lambda k: b[k])
    rv = i["rev"]; cogs = i["raw"] + i["pfc"]; wc = b["tca"] - b["tcl"]
    dio_ = b["inv"] / cogs * 365; dso_ = b["rec"] / rv * 365; dpo_ = b["ap"] / cogs * 365
    r_ = dict(aopm=i["ebitda"] / rv * 100, pftMrg=i["ni"] / rv * 100, roe=i["ni"] / avg("teq") * 100,
              rtnAsts=i["ni"] / avg("tota") * 100,
              aroi=i["pbit"] * (1 - i["taxrate"] / 100) / (avg("teq") + avg("debt")) * 100,
              roce=i["pbit"] / (b["tota"] - b["tcl"]) * 100,
              cafCfoaMgn=(c["cfo"] / rv * 100) if c else None,
              qcur=b["tca"] / b["tcl"], aqui=(b["tca"] - b["inv"]) / b["tcl"], dbtEqt=b["debt"] / b["teq"],
              ldbtEqt=b["ltd"] / b["teq"], aint=i["pbit"] / i["intexp"], netIncByLbl=i["ni"] / b["totl"],
              asstTurnR=rv / avg("tota"), wcTurnR=(rv / wc) if wc > 0 else None, invTurnR=cogs / avg("inv"),
              ccnc=dio_ + dso_ - dpo_, daysOfInvOstndng=dio_, daysSalesOstndng=dso_, daysPayOstndng=dpo_,
              erngPwrR=i["pbit"] / b["tota"] * 100)
    base_r[fy] = r_
def avg5(fy, key):
    v = [base_r[y][key] for y in range(max(2014, fy - 4), fy + 1) if base_r[y].get(key) is not None]
    return float(np.mean(v)) if len(v) >= 3 else None
for fy in FYS:
    for k5, k in (("opmg", "aopm"), ("5YpftMrg", "pftMrg"), ("5Yroe", "roe"), ("5YrtnAsts", "rtnAsts"),
                  ("5Yaroi", "aroi"), ("5YcafCfoaMgn", "cafCfoaMgn")):
        base_r[fy][k5] = avg5(fy, k)
    g = {}
    if fy > 2014:
        g["rvng"] = (IS[fy]["rev"] / IS[fy - 1]["rev"] - 1) * 100
        g["ebitg"] = (IS[fy]["ebitda"] / IS[fy - 1]["ebitda"] - 1) * 100
        g["epsg"] = (IS[fy]["eps"] / IS[fy - 1]["eps"] - 1) * 100
    if fy > 2015: g["cfog"] = (CF[fy]["cfo"] / CF[fy - 1]["cfo"] - 1) * 100
    if fy >= 2019:
        g["5YrevChg"] = cagr(IS[fy - 5]["rev"], IS[fy]["rev"], 5); g["earnings"] = cagr(IS[fy - 5]["ebitda"], IS[fy]["ebitda"], 5)
        g["epsGwth"] = cagr(IS[fy - 5]["eps"], IS[fy]["eps"], 5)
    if fy >= 2020: g["cfotr"] = cagr(CF[fy - 5]["cfo"], CF[fy]["cfo"], 5)
    if fy >= 2017: g["3YdivGwth"] = cagr(IS[fy - 3]["dps"], IS[fy]["dps"], 3)
    base_r[fy].update(g)
fy_end_idx = {}
for fy in FYS[1:]:
    e = date(fy, 3, 31)
    fy_end_idx[fy] = max(j for j, dd in enumerate(days) if dd <= e)

# =====================================================================
# 6. SHAREHOLDING (quarterly)
# =====================================================================
SQ = [(2014, 3), (2014, 4)] + [k for k in QL if k[0] >= 2015]
SQ = [k for k in SQ if k in QD]
def nif_q_ret(k):
    e = qend(*k); s = qend(k[0] - (1 if k[1] == 1 else 0), (k[1] - 2) % 4 + 1)
    ie = max((j for j, dd in enumerate(days) if dd <= min(e, d1)), default=0); isx = max((j for j, dd in enumerate(days) if dd <= s), default=0)
    return (NIF[ie] / NIF[isx] - 1) * 100
sh_rows = []
prom, fii, mf, ins, odii = 56.0, 13.0, 4.0, 3.5, 1.2
pl_pts = [(2014.9, 3.5), (2017.9, 5.0), (2020.2, 14.0), (2021.9, 2.0), (2022.9, 0.3), (2026.9, 0.2)]
ns_pts = [(2014.9, 150e3), (2018, 230e3), (2020, 300e3), (2022, 560e3), (2024, 640e3), (2026.9, 700e3)]
for j, k in enumerate(SQ):
    nq = nif_q_ret(k) if j else 0.0
    prom = float(np.clip(prom - 0.07 + N(0.12), 50, 58)); fii = float(np.clip(fii + 0.0 + 0.09 * nq / 10 + N(0.25), 10, 20))
    mf = float(np.clip(mf + 0.05 - 0.03 * nq / 10 + N(0.12), 3, 12)); ins = float(np.clip(ins + 0.018 + N(0.05), 3, 6.5))
    odii = float(np.clip(odii + 0.008 + N(0.04), 1, 2.5))
    dii = mf + ins + odii; oth = float(np.clip(4.0 + N(0.15), 3, 5.5)); ret = 100 - prom - fii - dii - oth
    yq = qend(*k).year + (qend(*k).month - 1) / 12
    sh_rows.append(dict(fy=k[0], q=k[1], endDate=qend(*k).isoformat(), strown=prom,
                        promShrPled=max(0.0, float(np.interp(yq, *zip(*pl_pts))) + N(0.15)),
                        domInstHldng=dii, forInstHldng=fii, instown=mf, insHolding=ins, otherDiiHolding=odii,
                        retailHolding=ret, othersHolding=oth,
                        nShareholders=int(float(np.interp(yq, *zip(*ns_pts))) * (1 + N(0.015)))))
for j, row in enumerate(sh_rows):
    for key, c3, c6 in (("strown", "strown3", "chPromHldng6M"), ("domInstHldng", "domInstHldng3M", "domInstHldng6M"),
                         ("forInstHldng", "forInstHldng3M", "forInstHldng6M"), ("instown", "instown3", "chMutHldng6M")):
        row[c3] = row[key] - sh_rows[j - 1][key] if j >= 1 else None
        row[c6] = row[key] - sh_rows[j - 2][key] if j >= 2 else None
sh_rows = [r for r in sh_rows if r["fy"] >= 2015]
for r in sh_rows:
    assert abs(r["strown"] + r["forInstHldng"] + r["domInstHldng"] + r["retailHolding"] + r["othersHolding"] - 100) < 1e-6

# =====================================================================
# 7. PEER UNIVERSE (30 fictional peers)
# =====================================================================
PEER_NAMES = ["Arcline Machinery", "Brightforge Industries", "Cobaltis Dynamics", "Dravik Engineering", "Eastmark Heavy",
              "Ferrovia Systems", "Granite Peak Tools", "Halcyon Drives", "Ionic Motion", "Jaivik Controls",
              "Kestrel Fabrication", "Lumora Automation", "Meridian Gearworks", "Norvane Hydraulics", "Orbis Precision",
              "Pragati Castings", "Quantro Turbines", "Raventek Industrial", "Solvane Pumps", "Tarkin Rail Systems",
              "Umbra Forge", "Vantora Compressors", "Westvale Equipments", "Xylon Bearings", "Yardley Cranes",
              "Zenith Rotors", "Altura Power Gear", "Bharani Foundry", "Corvus Motion", "Delmar Valves"]
OUT_FYS = FYS[1:]
nmo = len(mret_nifty)
peers = []
for pi_, nm in enumerate(PEER_NAMES):
    size = math.exp(N(0.7)); a_p = N(2.0) + 1.0
    m0 = float(np.clip(N(3.2, 15), 8, 24)); at0 = N(0.18, 0.95); em0 = float(np.clip(N(0.3, 1.9), 1.3, 2.8))
    f_pe = N(0.22); pe_off = N(0.08)
    rv_p = rev[2014] * size; ni_prev = None; hist = []
    for fy in OUT_FYS:
        g = 0.65 * growth_base[fy] + N(4.5) + a_p
        rv_p *= 1 + g / 100
        m_p = float(np.clip(m0 + 0.75 * (m_base[fy] - m_base[2014]) + N(0.8), 5, 30))
        nm_p = float(np.clip(0.5 * m_p + N(0.7), 1.5, 20))
        at = at0 * (1 + 0.01 * (fy - 2014)); em = em0 * (1 - 0.015 * (fy - 2014))
        roe_p = nm_p * at * em; roce_p = roe_p * float(np.clip(N(0.12, 1.05), 0.7, 1.4))
        de_p = float(np.clip((em - 1) * 0.55 + N(0.05), 0.02, 1.8))
        ni_p = rv_p * nm_p / 100
        pe_p = float(np.clip(anchor(fy + 0.25 - 1 + 0.0) * math.exp(f_pe + N(0.08) + pe_off), 6, 70))
        hist.append(dict(fy=fy, revenue=rv_p, aopm=m_p, pftMrg=nm_p, roe=roe_p, roce=roce_p, dbtEqt=de_p,
                         rvng=g, epsg=None if ni_prev is None else (ni_p / ni_prev - 1) * 100,
                         ttmPe=pe_p, pbr=pe_p * roe_p / 100, marketCap=ni_p * pe_p, netIncome=ni_p))
        ni_prev = ni_p
    # monthly returns & risk
    beta_p = float(np.clip(N(0.25, 1.0), 0.5, 1.6)); sg = float(rng.uniform(0.04, 0.09)); al = N(0.004, 0.002)
    mr = [beta_p * mret_nifty[j] + sg * 100 * N() + al * 100 for j in range(nmo)]
    ar = np.array(mr) / 100
    last36 = ar[-36:]; nn = np.array(mret_nifty[-36:]) / 100
    ann = (np.prod(1 + last36) ** (1 / 3) - 1)
    vol_p = ar[-12:].std(ddof=1) * math.sqrt(12) * 100
    cum = np.cumprod(1 + ar[-12:]); mdd = float((cum / np.maximum.accumulate(np.concatenate([[1], cum]))[1:] - 1).min() * 100)
    es, en = last36 - RF / 12, nn - RF / 12; bb = np.cov(es, en)[0, 1] / en.var(ddof=1)
    last = hist[-1]; h5 = hist[-6]
    snap = dict(aopm=last["aopm"], pftMrg=last["pftMrg"], roe=last["roe"], roce=last["roce"], dbtEqt=last["dbtEqt"],
                qcur=float(np.clip(N(0.4, 1.6), 0.8, 3.2)), aint=float(np.clip(N(3.5, 8), 1.5, 25)),
                ccnc=float(np.clip(N(25, 75), 10, 160)), rvng=last["rvng"],
                **{"5YrevChg": cagr(h5["revenue"], last["revenue"], 5)}, epsg=last["epsg"],
                epsGwth=cagr(h5["netIncome"], last["netIncome"], 5), ttmPe=last["ttmPe"], pbr=last["pbr"],
                evebitd=float(np.clip(last["ttmPe"] * 0.55 * (1 + N(0.1)), 4, 45)), divDps=float(rng.uniform(0.3, 2.2)),
                marketCap=last["marketCap"], **{"12mVol": vol_p}, beta=beta_p,
                **{"3Ywsh": (es.mean() * 12) / (last36.std(ddof=1) * math.sqrt(12)),
                   "3Ywal": (es.mean() - bb * en.mean()) * 12 * 100},
                maxDrawdown=mdd, **{"52wpct": (np.prod(1 + ar[-12:]) - 1) * 100},
                strown=float(np.clip(N(11, 50), 20, 75)), forInstHldng=float(np.clip(N(6, 14), 2, 35)))
    tick = nm.split()[0].upper()[:6]
    peers.append(dict(sid=tick, ticker=tick, name=nm, snapshot=snap, history=hist, monthlyReturns=mr))

# subject's own universe entry
subj_hist = []
for fy in OUT_FYS:
    r_ = base_r[fy]; i = IS[fy]
    subj_hist.append(dict(fy=fy, revenue=i["rev"], aopm=r_["aopm"], pftMrg=r_["pftMrg"], roe=r_["roe"], roce=r_["roce"],
                          dbtEqt=r_["dbtEqt"], rvng=r_["rvng"], epsg=r_["epsg"],
                          ttmPe=P[fy_end_idx[fy]] / (ttm_sum(kk[fy_end_idx[fy]], "eps")),
                          pbr=P[fy_end_idx[fy]] / BS[fy]["bvps"],
                          marketCap=P[fy_end_idx[fy]] * shares[fy], netIncome=i["ni"]))
for rk in ("rvng", "roe", "epsg", "marketCap"):
    for fy_i, fy in enumerate(OUT_FYS):
        vals = [(h["history"][fy_i][rk], h["sid"]) for h in peers] + [(subj_hist[fy_i][rk], "VELT")]
        vals = [(v if v is not None else -1e18, s) for v, s in vals]
        vals.sort(key=lambda t: -t[0])
        rank = {s: n + 1 for n, (v, s) in enumerate(vals)}
        for h in peers + [dict(sid="VELT", history=subj_hist)]:
            h["history"][fy_i].setdefault("rank", {})[rk] = rank[h["sid"]]

# =====================================================================
# 8. SNAPSHOT RATIOS FOR THE SUBJECT (info.ratios)
# =====================================================================
last_fy = 2026; iL = T - 1
S = {}
S.update(base_r[last_fy])
g_est = dict(estrvng=12.5 + N(0.4), estAvg=14.0 + N(0.5), **{"12mEpsg": 15.5 + N(0.5)}, ecfog=12.0 + N(0.5))
S.update(g_est)
S["5yCagrPct"] = cagr(P[iL - 1260], P[iL], 5)
for k in ("ttmPe", "apef", "pef", "pbr", "ps", "psf", "priceBySales", "ev", "evebitd", "evebit", "evByRev", "evByIc",
          "lcpCafFcf", "evCafFcf", "priceCfoR", "divDps", "indpe", "indpb", "inddy", "ped", "pbd", "psfs", "divSec",
          "pePremSi", "pbPremSi", "psPremSi", "dyPremSs"):
    S[k] = val_now[k]
S["mrktCapf"] = val_now["marketCap"]; S["marketCap"] = val_now["marketCap"]
S["lastPrice"] = P[iL]; S["bookValue"] = BS[last_fy]["bvps"]; S["faceValue"] = 2
S["eps"] = TTM["eps"]; S["pe"] = val_now["apef"]; S["pb"] = val_now["pbr"]; S["bps"] = BS[last_fy]["bvps"]
S["divYield"] = val_now["divDps"]
S["pr1d"] = r_pct[iL]; S["pr1w"] = (P[iL] / P[iL - 5] - 1) * 100; S["4wpct"] = (P[iL] / P[iL - 21] - 1) * 100
S["26wpct"] = (P[iL] / P[iL - 126] - 1) * 100; S["52wpct"] = (P[iL] / P[iL - 252] - 1) * 100
nrel = lambda n: (NIF[iL] / NIF[iL - n] - 1) * 100
S["pr1wN"] = S["pr1w"] - nrel(5); S["4wpctN"] = S["4wpct"] - nrel(21)
S["6mpctN"] = S["26wpct"] - nrel(126); S["12mpctN"] = S["52wpct"] - nrel(252)
S["acVol"] = int(V[iL]); S["vol1mAvg"] = float(V[iL - 20:iL + 1].mean()); S["vol3mAvg"] = float(V[iL - 62:iL + 1].mean())
S["3mAvgVol"] = S["vol3mAvg"]
S["vol1dChPct"] = (V[iL] / V[iL - 1] - 1) * 100
S["vol1wChPct"] = (V[iL - 4:iL + 1].mean() / V[iL - 9:iL - 4].mean() - 1) * 100
S["52wHigh"] = float(H[iL - 251:iL + 1].max()); S["52wLow"] = float(L[iL - 251:iL + 1].min())
S["52whd"] = (P[iL] / S["52wHigh"] - 1) * 100; S["52wld"] = (P[iL] / S["52wLow"] - 1) * 100
S.update(risk_at(iL)); S["risk"] = S["12mVolN"]
sh_last = sh_rows[-1]
for k in ("strown", "strown3", "chPromHldng6M", "promShrPled", "domInstHldng", "domInstHldng3M", "domInstHldng6M",
          "forInstHldng", "forInstHldng3M", "forInstHldng6M", "instown", "instown3", "chMutHldng6M", "insHolding",
          "retailHolding", "nShareholders"):
    S[k] = sh_last[k]
S["beta"] = S.get("beta"); S["roe"] = base_r[last_fy]["roe"]
all_mcaps = sorted([p_["snapshot"]["marketCap"] for p_ in peers] + [S["marketCap"]], reverse=True)
S["mrktCapRank"] = all_mcaps.index(S["marketCap"]) + 1
S["marketCapLabel"] = "Largecap" if S["marketCap"] > 20000 else "Midcap"

# =====================================================================
# 9. OUTPUT ASSEMBLY
# =====================================================================
def inc_row(fy=None, ttm=False):
    i = TTM if ttm else IS[fy]
    cogs = i["raw"] + i["pfc"]
    return dict(displayPeriod="TTM" if ttm else f"FY {fy}", endDate=iso(qend(2027, 2) if ttm else date(fy, 3, 31)),
                reporting="consolidated", incTrev=i["rev"], incCrev=None, incGpro=i["rev"] - cogs, incOpc=None,
                balCogs=cogs, incRaw=i["raw"], incPfc=i["pfc"], incEpc=i["epc"], incSga=i["sga"], incOpe=i["ope"],
                incEbi=i["ebitda"], incDep=i["dep"], incPbi=i["pbit"], incIoi=i["ioi"], incPbt=i["pbt"], incToi=i["tax"],
                incNinc=i["ni"], incEps=i["eps"], incDps=i["dps"], incPyr=i["payout"])
def bal_row(fy):
    b = BS[fy]
    return dict(displayPeriod=f"FY {fy}", endDate=iso(date(fy, 3, 31)), reporting="consolidated",
                balCsti=b["cash"], balTrec=b["rec"], balTinv=b["inv"], balOca=b["oca"], balTca=b["tca"], balNetl=None,
                balNppe=b["ppe"], balGint=b["gint"], balLti=b["lti"], balOtha=b["otha"], balTota=b["tota"],
                balAccp=b["ap"], balTdep=None, balOcl=b["ocl"], balTcl=b["tcl"], balTltd=b["ltd"], balTdeb=b["debt"],
                balDit=b["dtl"], balMint=b["mi"], balOthl=b["othl"], balTotl=b["totl"], balComs=b["coms"],
                balApic=b["apic"], balRtne=b["res"], balOeq=0, balTeq=b["teq"], balTlse=b["tlse"],
                balTcso=shares[fy], balTpso=None, balNca=b["nca"], balCa=b["tca"], balNcl=b["ncl"], balDta=b["dta"],
                faceValue=2, bookValue=b["bvps"])
def cf_row(fy):
    c = CF[fy]
    return dict(displayPeriod=f"FY {fy}", endDate=iso(date(fy, 3, 31)), reporting="consolidated", cafCiwc=c["ciwc"],
                cafCfoa=c["cfo"], cafCexp=c["capex"], cafCfia=c["cfi"], cafTcdp=c["div"], cafCffa=c["cff"], cafFee=None,
                cafNcic=c["ncic"], cafFcf=c["fcf"])
def q_row(k):
    d = QD[k]; fy, q = k
    return dict(displayPeriod=f"Q{q} FY {fy}", fiscalYear=fy, quarter=q, endDate=iso(qend(fy, q)),
                reportDate=rdate(fy, q).isoformat(), reporting="consolidated", qIncTrevK=d["rev"], qIncOpeK=d["opex"],
                qIncEbiK=d["ebitda"], qIncPbiK=d["pbit"], qIncPbtK=d["pbt"], qIncNincK=d["ni"], qIncEpsK=d["eps"])

fin_inc = [inc_row(fy) for fy in OUT_FYS] + [inc_row(ttm=True)]
fin_bal = [bal_row(fy) for fy in OUT_FYS]
fin_cf = [cf_row(fy) for fy in OUT_FYS]
fin_q = [q_row(k) for k in QL if k[0] >= 2015]
ratios_hist = []
for fy in OUT_FYS:
    row = dict(displayPeriod=f"FY {fy}", endDate=iso(date(fy, 3, 31)))
    row.update(base_r[fy]); ratios_hist.append(row)
fyend_val = []
for fy in OUT_FYS:
    v = val_at(fy_end_idx[fy]); v["displayPeriod"] = f"FY {fy}"; fyend_val.append(v)

# peers table for universe (subject first)
subj_snap = {k: S.get(k) for k in peers[0]["snapshot"].keys()}
universe = [dict(sid="VELT", ticker="VELTRIX", name="Veltrix Engineering Ltd", isSubject=True, snapshot=subj_snap, history=subj_hist)]
for p_ in peers:
    universe.append(dict(sid=p_["sid"], ticker=p_["ticker"], name=p_["name"], isSubject=False,
                         snapshot=p_["snapshot"], history=p_["history"]))
monthly_returns = dict(dates=[d.isoformat() for d in mret_dates], stock=mret_stock, nifty=mret_nifty,
                       peers={p_["sid"]: p_["monthlyReturns"] for p_ in peers})

price_rows = [dict(d=days[i].isoformat(), o=O[i], h=H[i], l=L[i], c=P[i], v=int(V[i]), r=r_pct[i], n=NIF[i], nr=nr[i])
              for i in range(T)]
run_max = np.maximum.accumulate(P)
drawdown = [dict(d=days[i].isoformat(), dd=(P[i] / run_max[i] - 1) * 100) for i in range(T)]
risk_hist = []
for i in month_idx + [T - 1]:
    rr = risk_at(i); rr["date"] = days[i].isoformat(); risk_hist.append(rr)
w = slice(iL - 251, iL + 1); lo, hi = float(L[w].min()), float(H[w].max()); nb = 40; step = (hi - lo) / nb
vp = [dict(lo=lo + j * step, hi=lo + (j + 1) * step, vol=0, upVol=0, downVol=0) for j in range(nb)]
for i in range(iL - 251, iL + 1):
    j = min(nb - 1, int((P[i] - lo) / step)); vp[j]["vol"] += int(V[i])
    vp[j]["upVol" if r_pct[i] >= 0 else "downVol"] += int(V[i])

info = dict(
    type="stock",
    info=dict(sector="Capital Goods - Industrial Machinery", name="Veltrix Engineering Ltd", ticker="VELTRIX", exchange="NSE",
              description="Veltrix Engineering Limited (fictional) designs and manufactures industrial machinery, drives and "
                          "motion-control systems for infrastructure, energy and manufacturing customers.",
              tags=[dict(name="Capital Goods - Industrial Machinery", visible=True, type="sub-sector")]),
    ratios=S, sid="VELT",
    gic=dict(sector="Industrials", industrygroup="Capital Goods", industry="Machinery", subindustry="Industrial Machinery", short="Industrials"),
    isin="INE000V01018", slug="/stocks/veltrix-engineering-VELT", tradable=True,
    labels=dict(sector=dict(title="Industrials", extra="", description="Capital Goods - Industrial Machinery"),
                marketCap=dict(title=S["marketCapLabel"], extra="Companies with market capitalisation above 20,000 cr are considered large cap",
                               description=f"With a market cap of ₹{S['marketCap']:,.0f} cr, stock is ranked {S['mrktCapRank']}"),
                risk=dict(title="Low Risk" if S["risk"] < 2 else "High Risk", extra="Stocks which are <2 times as volatile as Nifty are considered low risk stocks",
                          description=f"Stock is {S['risk']:.2f}x as volatile as Nifty")))
top5 = sorted(peers, key=lambda p_: abs(math.log(p_["snapshot"]["marketCap"] / S["marketCap"])))[:5]
summary = dict(
    financialSummary=dict(fiscalYearToData=[dict(year=str(fy), revenue=IS[fy]["rev"], profit=IS[fy]["ni"]) for fy in OUT_FYS]),
    aboutAndPeers=[dict(name="Veltrix Engineering Ltd", ticker="VELTRIX", sid="VELT", sector="Capital Goods - Industrial Machinery",
                        slug="/stocks/veltrix-engineering-VELT",
                        ratios=dict(ttmPe=S["ttmPe"], breco=71, **{"52wpct": S["52wpct"]}, marketCap=S["marketCap"], apef=S["apef"]))] +
                   [dict(name=p_["name"], ticker=p_["ticker"], sid=p_["sid"], sector="Capital Goods - Industrial Machinery",
                         ratios=dict(ttmPe=p_["snapshot"]["ttmPe"], breco=float(rng.uniform(40, 90)), **{"52wpct": p_["snapshot"]["52wpct"]},
                                     marketCap=p_["snapshot"]["marketCap"], apef=p_["snapshot"]["ttmPe"] * 1.03)) for p_ in top5],
    forecast=dict(totalReco=24, percBuyReco=71),
    keyRatios=[dict(backL=k, value=S[k]) for k in ("ttmPe", "pbr", "divYield", "indpe", "indpb", "inddy")])

meta = dict(
    company="Veltrix Engineering Ltd (fictional)", sid="VELT", currency="INR crore (prices in INR)", fiscalYearEnd="31 March",
    generatedBy="generate_sample_data.py", seed=A.seed, asOf=d1.isoformat(),
    coverage=dict(annual="FY2015-FY2026 (+TTM on income statement)", quarterly="Q1 FY2015 - Q2 FY2027 (50 quarters)",
                  prices=f"{days[0]} -> {days[-1]} ({T} trading days)", valuationHistory="monthly", shareholding="quarterly",
                  universe="1 subject + 30 fictional peers"),
    notes=["qIncOpeK = total operating expenses (revenue - EBITDA); annual incOpe = 'operating & other expenses' line only.",
           "OCL includes the short-term debt portion; balTdeb = long-term + short-term debt (RELI convention).",
           "5Y averages / CAGRs are null until 3 / 5 years of history exist.",
           "5yCagrPct = 5-year price CAGR. pr*N / *pctN fields = stock return minus Nifty return (percentage points).",
           "12mVolN = stock 12M volatility / Nifty 12M volatility (the 'risk' multiple).",
           "maxDrawdown = worst peak-to-trough fall over the trailing 252 trading days (negative %).",
           "Trading calendar is approximate (weekdays minus 7 fixed-date holidays). All numbers are synthetic."])

combined = dict(meta=meta, info=info, summary=summary, financials_income=fin_inc, financials_balance=fin_bal,
                financials_cashflow=fin_cf, financials_income_quarterly=fin_q, ratios_history=ratios_hist,
                valuation_history=dict(monthly=val_hist, fiscalYearEnd=fyend_val, bands=val_bands, latest=val_now),
                shareholding_history=sh_rows, price_history=price_rows, volume_profile_1y=vp,
                risk=dict(rolling=risk_hist, drawdownDaily=drawdown, monthlyReturns=monthly_returns),
                universe=universe)

def ratio_slice(keys): return {k: S.get(k) for k in keys}
G = {
 "02_income_statement": dict(meta=meta, annual=fin_inc, quarterly=fin_q),
 "03_balance_sheet": dict(meta=meta, annual=fin_bal),
 "04_cash_flow": dict(meta=meta, annual=fin_cf),
 "05_profitability": dict(meta=meta, snapshot=ratio_slice(["aopm", "opmg", "pftMrg", "5YpftMrg", "roe", "5Yroe", "rtnAsts", "5YrtnAsts", "aroi", "5Yaroi", "roce", "cafCfoaMgn", "5YcafCfoaMgn"]),
                         history=[{k: v for k, v in r_.items() if k in ("displayPeriod", "endDate", "aopm", "opmg", "pftMrg", "5YpftMrg", "roe", "5Yroe", "rtnAsts", "5YrtnAsts", "aroi", "5Yaroi", "roce", "cafCfoaMgn", "5YcafCfoaMgn")} for r_ in ratios_hist],
                         universe=universe),
 "06_growth": dict(meta=meta, snapshot=ratio_slice(["rvng", "5YrevChg", "ebitg", "earnings", "epsg", "epsGwth", "cfog", "cfotr", "3YdivGwth", "estrvng", "estAvg", "12mEpsg", "ecfog", "5yCagrPct"]),
                   history=[{k: v for k, v in r_.items() if k in ("displayPeriod", "endDate", "rvng", "5YrevChg", "ebitg", "earnings", "epsg", "epsGwth", "cfog", "cfotr", "3YdivGwth")} for r_ in ratios_hist],
                   universe=universe),
 "07_financial_health": dict(meta=meta, snapshot=ratio_slice(["qcur", "aqui", "dbtEqt", "ldbtEqt", "aint", "netIncByLbl", "asstTurnR", "wcTurnR", "invTurnR", "ccnc", "daysOfInvOstndng", "daysSalesOstndng", "daysPayOstndng", "erngPwrR"]),
                             history=[{k: v for k, v in r_.items() if k in ("displayPeriod", "endDate", "qcur", "aqui", "dbtEqt", "ldbtEqt", "aint", "netIncByLbl", "asstTurnR", "wcTurnR", "invTurnR", "ccnc", "daysOfInvOstndng", "daysSalesOstndng", "daysPayOstndng", "erngPwrR")} for r_ in ratios_hist],
                             universe=universe),
 "08_valuation": dict(meta=meta, snapshot={k: v for k, v in val_now.items()}, history=val_hist, fiscalYearEnd=fyend_val, bands=val_bands, universe=universe),
 "09_shareholding": dict(meta=meta, snapshot=ratio_slice(["strown", "strown3", "chPromHldng6M", "promShrPled", "domInstHldng", "domInstHldng3M", "domInstHldng6M", "forInstHldng", "forInstHldng3M", "forInstHldng6M", "instown", "instown3", "chMutHldng6M", "insHolding", "retailHolding", "nShareholders"]), history=sh_rows),
 "10_market_activity": dict(meta=meta, snapshot=ratio_slice(["lastPrice", "pr1d", "pr1w", "4wpct", "26wpct", "52wpct", "pr1wN", "4wpctN", "6mpctN", "12mpctN", "acVol", "vol1mAvg", "vol3mAvg", "vol1dChPct", "vol1wChPct", "52wHigh", "52wLow", "52whd", "52wld"]), prices=price_rows, volumeProfile1Y=vp),
 "11_risk": dict(meta=meta, snapshot=ratio_slice(["beta", "12mVol", "12mVolN", "3Ywal", "3Ywsh", "maxDrawdown"]), rolling=risk_hist,
                 drawdownDaily=drawdown, monthlyReturns=monthly_returns, universe=universe),
}

os.makedirs(os.path.join(A.out, "groups"), exist_ok=True)
def dump(obj, path):
    with open(path, "w") as f: json.dump(clean(obj), f, separators=(",", ":"))
dump(combined, os.path.join(A.out, "VELT_data.json"))
for name, obj in G.items(): dump(obj, os.path.join(A.out, "groups", name + ".json"))

# --------------------------- sanity report ---------------------------
print("FY   rev    EBITDA%  NI%   ROE%  D/E   cash   CFO    FCF   price")
for fy in OUT_FYS:
    r_ = base_r[fy]; px = P[fy_end_idx[fy]]
    print(f"{fy} {IS[fy]['rev']:7.0f} {r_['aopm']:6.1f} {r_['pftMrg']:6.1f} {r_['roe']:6.1f} {r_['dbtEqt']:5.2f} {BS[fy]['cash']:6.0f} {CF[fy]['cfo']:6.0f} {CF[fy]['fcf']:6.0f} {px:7.1f}")
print(f"TTM  rev {TTM['rev']:.0f}  NI {TTM['ni']:.0f}  EPS {TTM['eps']:.2f}")
print(f"Last price {P[-1]:.1f}  mcap {S['marketCap']:.0f} cr  PE {S['ttmPe']:.1f}  PB {S['pbr']:.2f}  Nifty {NIF[-1]:.0f}")
print(f"Vol12m {S['12mVol']:.1f}%  beta {S['beta']:.2f}  Sharpe3Y {S['3Ywsh']:.2f}  maxDD {S['maxDrawdown']:.1f}%")
print(f"PE range {min(v['ttmPe'] for v in val_hist):.1f}-{max(v['ttmPe'] for v in val_hist):.1f}; days {T}; quarters {len(fin_q)}")
print("ownership last q:", {k: round(sh_last[k], 1) for k in ("strown", "forInstHldng", "domInstHldng", "retailHolding")})
