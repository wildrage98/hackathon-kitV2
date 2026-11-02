"""좌표 계산 (stdlib, 지도 API 없음).

    haversine_m(lat1, lon1, lat2, lon2) → m
    walk_min(dist_m, speed_m_per_min=80, path_factor=1.25) → 분 (직선거리 → 보행거리 보정 → 시간)
    nearest(lat, lon, points=[(id, lat, lon)], k=1) → [(dist_m, id)]
    within(lat, lon, points, radius_m) → [(dist_m, id)] 정렬
    project(points=[(id, lat, lon)], width=1000, height=700, pad=40) → {id: (x, y)}  화면 좌표(등장방형, 위도 보정)
    bbox(points) → (min_lat, min_lon, max_lat, max_lon)
"""
import math


def haversine_m(lat1, lon1, lat2, lon2):
    r = 6371008.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def walk_min(dist_m, speed_m_per_min=80.0, path_factor=1.25):
    return dist_m * path_factor / speed_m_per_min


def nearest(lat, lon, points, k=1):
    ds = sorted((haversine_m(lat, lon, p[1], p[2]), p[0]) for p in points)
    return ds[:k]


def within(lat, lon, points, radius_m):
    out = []
    for p in points:
        d = haversine_m(lat, lon, p[1], p[2])
        if d <= radius_m:
            out.append((d, p[0]))
    out.sort()
    return out


def bbox(points):
    lats = [p[1] for p in points]
    lons = [p[2] for p in points]
    return min(lats), min(lons), max(lats), max(lons)


def project(points, width=1000, height=700, pad=40):
    if not points:
        return {}
    lats = [p[1] for p in points]
    lons = [p[2] for p in points]
    lat0 = sum(lats) / len(lats)
    k = math.cos(math.radians(lat0))
    xs = [(p[2] - min(lons)) * k for p in points]
    ys = [(max(lats) - p[1]) for p in points]
    sx = (width - 2 * pad) / (max(xs) or 1e-9)
    sy = (height - 2 * pad) / (max(ys) or 1e-9)
    s = min(sx, sy)
    return {p[0]: (round(pad + x * s, 1), round(pad + y * s, 1)) for p, x, y in zip(points, xs, ys)}
