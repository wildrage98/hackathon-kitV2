"""overlay — 오버레이(층간 정렬 오차) 사이트 데이터: 성분 분해 · 지표 · flyer · 벡터맵 (stdlib 전용).

  fit_linear(rows, x, y, dx, dy, model="wafer6", fx, fy) → {params, residuals, n, skipped, model}
      wafer6 : dx = Tx + Mx·x − Rx·y          dy = Ty + My·y + Ry·x        (x, y = 웨이퍼 좌표)
      wafer10: wafer6 + mx·fx − rx·fy  /  + my·fy + ry·fx                   (fx, fy = 필드 내 좌표)
      단위: T* = dx 단위, M*/R* = dx 단위 / 좌표 단위 (nm/mm = ppm). 회전 = (Rx+Ry)/2, 직교성 = Rx − Ry
      ※ 부호·단위 규약은 현장마다 다르다 → 담당자와 확인하고 HOW_TO_RUN 에 적는다.
  lstsq(A, b) → 계수 리스트 (정규방정식 + 부분 피벗 가우스 소거, 특이 행렬이면 ValueError)
  axis_stats(values) → n, mean, sigma, m3s(|mean|+3σ), max_abs
  site_stats(rows, dx, dy) → {"x": axis_stats, "y": axis_stats}
  flag_flyers(rows, dx, dy, k=5.0) → [bool] (X/Y 각각 중앙값 ± k·1.4826·MAD 밖이면 True)
  wafer_summary(rows, wafer_col, ..., spec=None, flyer_k=None, fail_on_equal=False) → 웨이퍼별 지표·성분·판정
  contributions(params, radius, field_half=None) → 성분별 크기(가장자리 반경 기준), 큰 순
  TERM_HINTS / hint_for(term) → 우세 성분별 의심 원인 후보 (확정 아님)
  radial_profile(rows, x, y, rdx, rdy, bins=4) → 반경 구간별 평균 잔차 크기 (가장자리 패턴 확인)
  vector_map_svg(rows, x, y, dx, dy, scale=None, title="") → inline SVG 문자열 (웨이퍼 벡터맵)
"""
from __future__ import annotations

import html
import math
import statistics
from collections import OrderedDict
from typing import Dict, Iterable, List, Optional, Sequence


# ---------------------------------------------------------------- 수치 기본

def _num(v) -> Optional[float]:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        f = float(v)
    else:
        s = str(v).strip().replace(",", "")
        if s == "" or s.lower() in {"nan", "na", "n/a", "null", "none", "-"}:
            return None
        try:
            f = float(s)
        except ValueError:
            return None
    return None if math.isnan(f) or math.isinf(f) else f


def lstsq(A: Sequence[Sequence[float]], b: Sequence[float]) -> List[float]:
    """최소제곱 해 (AᵀA p = Aᵀb). 열이 선형 종속이면 ValueError."""
    m = len(A[0])
    ata = [[0.0] * m for _ in range(m)]
    atb = [0.0] * m
    for row, bi in zip(A, b):
        for i in range(m):
            ri = row[i]
            atb[i] += ri * bi
            for j in range(m):
                ata[i][j] += ri * row[j]
    M = [ata[i][:] + [atb[i]] for i in range(m)]
    scale = max(abs(ata[i][i]) for i in range(m)) or 1.0
    for c in range(m):
        piv = max(range(c, m), key=lambda r: abs(M[r][c]))
        if abs(M[piv][c]) <= 1e-12 * scale:
            raise ValueError("rank deficient: 측정점이 부족하거나 한 줄 위에 있음 (모델 항 수 확인)")
        M[c], M[piv] = M[piv], M[c]
        for r in range(m):
            if r != c:
                f = M[r][c] / M[c][c]
                if f:
                    for k in range(c, m + 1):
                        M[r][k] -= f * M[c][k]
    return [M[i][m] / M[i][i] for i in range(m)]


def axis_stats(values: Iterable) -> Dict:
    v = [f for f in (_num(x) for x in values) if f is not None]
    if not v:
        return {"n": 0, "mean": None, "sigma": None, "m3s": None, "max_abs": None}
    mean = statistics.fmean(v)
    sigma = statistics.stdev(v) if len(v) > 1 else 0.0
    return {"n": len(v), "mean": mean, "sigma": sigma, "m3s": abs(mean) + 3 * sigma, "max_abs": max(abs(x) for x in v)}


def site_stats(rows: Sequence[Dict], dx: str = "dx", dy: str = "dy") -> Dict:
    return {"x": axis_stats(r.get(dx) for r in rows), "y": axis_stats(r.get(dy) for r in rows)}


# ---------------------------------------------------------------- flyer

def flag_flyers(rows: Sequence[Dict], dx: str = "dx", dy: str = "dy", k: float = 5.0) -> List[bool]:
    """X/Y 각각 중앙값 ± k·1.4826·MAD 밖이면 flyer. 값이 없는 행도 True(분석 제외 대상)."""
    out = [False] * len(rows)
    for col in (dx, dy):
        vals = [_num(r.get(col)) for r in rows]
        ok = [v for v in vals if v is not None]
        if len(ok) < 3:
            continue
        med = statistics.median(ok)
        mad = statistics.median(abs(v - med) for v in ok) * 1.4826
        lim = k * mad if mad > 0 else None
        for i, v in enumerate(vals):
            if v is None or (lim is not None and abs(v - med) > lim):
                out[i] = True
    return out


# ---------------------------------------------------------------- 성분 분해

WAFER6 = ("Tx", "Mx", "Rx", "Ty", "My", "Ry")
WAFER10 = WAFER6 + ("mx", "rx", "my", "ry")


def fit_linear(rows: Sequence[Dict], x: str = "x", y: str = "y", dx: str = "dx", dy: str = "dy",
               model: str = "wafer6", fx: str = "fx", fy: str = "fy") -> Dict:
    """선형 성분 분해. dx 식과 dy 식은 서로 독립이라 축별로 따로 푼다."""
    if model not in ("wafer6", "wafer10"):
        raise ValueError("model 은 wafer6 | wafer10")
    pts, skipped = [], 0
    for r in rows:
        vals = [_num(r.get(c)) for c in ((x, y, dx, dy, fx, fy) if model == "wafer10" else (x, y, dx, dy))]
        if any(v is None for v in vals):
            skipped += 1
            continue
        pts.append(vals)
    if model == "wafer6":
        ax = [[1.0, p[0], -p[1]] for p in pts]
        ay = [[1.0, p[1], p[0]] for p in pts]
        need = 3
    else:
        ax = [[1.0, p[0], -p[1], p[4], -p[5]] for p in pts]
        ay = [[1.0, p[1], p[0], p[5], p[4]] for p in pts]
        need = 5
    if len(pts) < need + 1:
        raise ValueError(f"측정점 {len(pts)}개 < 필요 {need + 1}개 ({model})")
    cx = lstsq(ax, [p[2] for p in pts])
    cy = lstsq(ay, [p[3] for p in pts])
    if model == "wafer6":
        params = OrderedDict(zip(WAFER6, cx + cy))
    else:
        params = OrderedDict([("Tx", cx[0]), ("Mx", cx[1]), ("Rx", cx[2]), ("Ty", cy[0]), ("My", cy[1]), ("Ry", cy[2]),
                              ("mx", cx[3]), ("rx", cx[4]), ("my", cy[3]), ("ry", cy[4])])
    residuals = []
    for p, rx_, ry_ in zip(pts, ax, ay):
        mxv = sum(a * c for a, c in zip(rx_, cx))
        myv = sum(a * c for a, c in zip(ry_, cy))
        residuals.append({"x": p[0], "y": p[1], "rdx": p[2] - mxv, "rdy": p[3] - myv})
    params["rotation"] = (params["Rx"] + params["Ry"]) / 2
    params["non_ortho"] = params["Rx"] - params["Ry"]
    return {"model": model, "n": len(pts), "skipped": skipped, "params": dict(params), "residuals": residuals}


# ---------------------------------------------------------------- 웨이퍼별 요약

def wafer_summary(rows: Sequence[Dict], wafer_col: str = "wafer", x: str = "x", y: str = "y", dx: str = "dx",
                  dy: str = "dy", model: str = "wafer6", fx: str = "fx", fy: str = "fy", spec: Optional[float] = None,
                  flyer_k: Optional[float] = None, fail_on_equal: bool = False, keep_cols: Sequence[str] = ()) -> List[Dict]:
    """웨이퍼별: n, flyer 수, X/Y |mean|+3σ(원값), X/Y 잔차 3σ, 성분, 판정(spec 있으면).
    판정: max(raw_x_m3s, raw_y_m3s) > spec → fail (fail_on_equal=True 면 ≥). keep_cols: 첫 행에서 복사할 컨텍스트 컬럼."""
    groups: "OrderedDict[str, List[Dict]]" = OrderedDict()
    for r in rows:
        groups.setdefault(str(r.get(wafer_col)), []).append(r)
    out = []
    for w, rs in groups.items():
        flags = flag_flyers(rs, dx, dy, flyer_k) if flyer_k else [False] * len(rs)
        use = [r for r, f in zip(rs, flags) if not f]
        st = site_stats(use, dx, dy)
        rec = {"wafer": w, "n": len(rs), "n_flyer": sum(flags),
               "raw_x_m3s": st["x"]["m3s"], "raw_y_m3s": st["y"]["m3s"],
               "raw_x_mean": st["x"]["mean"], "raw_y_mean": st["y"]["mean"]}
        for c in keep_cols:
            rec[c] = rs[0].get(c)
        try:
            fit = fit_linear(use, x, y, dx, dy, model, fx, fy)
            rec.update({k: v for k, v in fit["params"].items()})
            rec["res_x_3s"] = 3 * statistics.pstdev([q["rdx"] for q in fit["residuals"]])
            rec["res_y_3s"] = 3 * statistics.pstdev([q["rdy"] for q in fit["residuals"]])
            rec["fit_error"] = ""
        except ValueError as e:
            rec["fit_error"] = str(e)
        if spec is not None and rec["raw_x_m3s"] is not None:
            worst = max(rec["raw_x_m3s"], rec["raw_y_m3s"])
            rec["fail"] = worst >= spec if fail_on_equal else worst > spec
        out.append(rec)
    return out


# ---------------------------------------------------------------- 해석 보조

TERM_HINTS = {
    "Tx": "평행이동 — 정렬, APC 보정값", "Ty": "평행이동 — 정렬, APC 보정값",
    "Mx": "배율 — 열(웨이퍼 팽창), 보정값", "My": "배율 — 열(웨이퍼 팽창), 보정값",
    "Rx": "회전/직교성 — 웨이퍼 로딩·정렬, 스테이지", "Ry": "회전/직교성 — 웨이퍼 로딩·정렬, 스테이지",
    "mx": "필드 내 배율 — 레티클, 렌즈", "my": "필드 내 배율 — 레티클, 렌즈",
    "rx": "필드 내 회전 — 레티클, 렌즈", "ry": "필드 내 회전 — 레티클, 렌즈",
    "residual": "잔차(고차) — 증착 응력·CMP·열처리 변형, 척 가장자리, 계측",
}


def hint_for(term: str) -> str:
    return TERM_HINTS.get(term, "")


def contributions(params: Dict, radius: float, field_half: Optional[float] = None,
                  residual_3s: Optional[float] = None) -> List[Dict]:
    """각 성분이 만드는 최대 변위(웨이퍼 반경 radius, 필드 반폭 field_half 기준). 큰 순."""
    out = []
    for t in ("Tx", "Ty"):
        if t in params:
            out.append({"term": t, "size": abs(params[t])})
    for t in ("Mx", "My", "Rx", "Ry"):
        if t in params:
            out.append({"term": t, "size": abs(params[t]) * radius})
    if field_half:
        for t in ("mx", "my", "rx", "ry"):
            if t in params:
                out.append({"term": t, "size": abs(params[t]) * field_half})
    if residual_3s is not None:
        out.append({"term": "residual", "size": residual_3s})
    for d in out:
        d["hint"] = hint_for(d["term"])
    out.sort(key=lambda d: -d["size"])
    return out


def radial_profile(points: Sequence[Dict], x: str = "x", y: str = "y", vx: str = "rdx", vy: str = "rdy",
                   bins: int = 4) -> List[Dict]:
    """반경 구간별 평균 벡터 크기. 바깥 구간만 크면 가장자리(공정 변형·척) 패턴."""
    pts = []
    for p in points:
        a, b, c, d = (_num(p.get(k)) for k in (x, y, vx, vy))
        if None not in (a, b, c, d):
            pts.append((math.hypot(a, b), math.hypot(c, d)))
    if not pts:
        return []
    rmax = max(r for r, _ in pts) or 1.0
    out = []
    for i in range(bins):
        lo, hi = rmax * i / bins, rmax * (i + 1) / bins
        sel = [m for r, m in pts if (lo <= r < hi) or (i == bins - 1 and r == hi)]
        out.append({"r_from": lo, "r_to": hi, "n": len(sel), "mean_mag": statistics.fmean(sel) if sel else None})
    return out


# ---------------------------------------------------------------- 벡터맵

def vector_map_svg(rows: Sequence[Dict], x: str = "x", y: str = "y", dx: str = "dx", dy: str = "dy",
                   scale: Optional[float] = None, size: int = 420, title: str = "") -> str:
    """웨이퍼 벡터맵 (화살표 = 오차 방향·크기, scale 배 확대). scale 없으면 95% 분위 화살표가 반경의 8%."""
    pts = []
    for r in rows:
        v = [_num(r.get(k)) for k in (x, y, dx, dy)]
        if None not in v:
            pts.append(v)
    pad, top = 20, (28 if title else 8)
    R = max((math.hypot(p[0], p[1]) for p in pts), default=1.0) or 1.0
    R *= 1.05
    if scale is None:
        mags = sorted(math.hypot(p[2], p[3]) for p in pts)
        q = mags[int(0.95 * (len(mags) - 1))] if mags else 0
        scale = (0.08 * R / q) if q else 1.0
    half = (size - 2 * pad) / 2
    cx, cy = pad + half, top + half

    def tx(px, py):
        return cx + px / R * half, cy - py / R * half

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{int(top + 2 * half + pad + 14)}" '
             f'viewBox="0 0 {size} {int(top + 2 * half + pad + 14)}" font-family="sans-serif" font-size="11">',
             '<defs><marker id="ah" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">'
             '<path d="M0,0 L6,3 L0,6 z" fill="#c0392b"/></marker></defs>']
    if title:
        parts.append(f'<text x="{size / 2}" y="18" text-anchor="middle" font-size="13">{html.escape(title)}</text>')
    parts.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{half:.1f}" fill="none" stroke="#999"/>')
    for p in pts:
        x0, y0 = tx(p[0], p[1])
        x1, y1 = tx(p[0] + p[2] * scale, p[1] + p[3] * scale)
        parts.append(f'<line x1="{x0:.1f}" y1="{y0:.1f}" x2="{x1:.1f}" y2="{y1:.1f}" stroke="#c0392b" '
                     f'stroke-width="1.2" marker-end="url(#ah)"/>')
    parts.append(f'<text x="{pad}" y="{int(top + 2 * half + pad + 8)}" fill="#555">화살표 = 오차 × {scale:.3g} '
                 f'(좌표 단위 환산), 점 {len(pts)}개</text></svg>')
    return "".join(parts)
