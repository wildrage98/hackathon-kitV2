"""배정·묶음·순서·시간표 휴리스틱 (stdlib, 결정적). 많은 지점 → 한 거점(depot) 유형.

    cover_assign(points, candidates, limits=(10, 15), walk_fn=geo.walk_min, min_group=0, prefer=None, seed_ids=None)
        points=[(pid, lat, lon)], candidates=[(cid, lat, lon)]
        → ({pid: {"cand", "walk_min", "dist_m", "tier": "primary|extended|exception"}}, used_cids)
        1차 한도 내 greedy set-cover → 1차 후보 없는 지점만 2차 한도 → 그래도 없으면 최근접(예외).
        min_group: 이 인원 미만 후보는 전원이 2차 한도 내 다른 선정 후보로 옮길 수 있으면 통합.
        prefer(cid)→숫자: 동률 시 큰 값 우선.  seed_ids: 먼저 쓸 후보(기존 시설) — 2차 한도 내면 최근접 seed 에 배정.
    make_routes(demand, depot, T, cap, detour_max=1.5, dwell=1, backtrack_slack=8, abs_slack=10)
        demand={stop: [item,...]}, T(a,b)=분(진행 방향 기준; 거점→밖 방향이면 T=lambda a,b: tt[(b,a)])
        → [[(stop, items), ...], ...]  각 노선은 거점 쪽으로 진행하는 순서. 정원 초과 정류장은 직행 분리.
        제약: 적재 ≤ cap, 각 승객 탑승시간 ≤ max(detour_max×직행, 직행+abs_slack), 거점에서 멀어지는 이동 ≤ backtrack_slack.
    timetable(route, inbound, depot, tt, anchor, dwell=1)
        inbound=True: anchor=거점 도착시각(datetime) → 역산.  False: anchor=거점 출발시각 → 순산(노선 순서는 뒤집어 사용).
        → (stops=[{seq, stop_id, time(ISO 분), boardings, alightings}], ride_min={stop: 분})
    route_cost(seq, depot, T, dwell) → 분
"""
import datetime as dt


def _iso(d):
    return d.strftime("%Y-%m-%dT%H:%M")


# ----------------------------------------------------------------------------- assignment
def cover_assign(points, candidates, limits=(10, 15), walk_fn=None, min_group=0, prefer=None, seed_ids=None):
    from . import geo
    walk_fn = walk_fn or geo.walk_min
    p_lim, e_lim = limits
    cands = {c[0]: c for c in candidates}
    cand_of, nearest = {}, {}
    for pid, lat, lon in points:
        best, lst = None, []
        for cid, clat, clon in candidates:
            d = geo.haversine_m(lat, lon, clat, clon)
            w = walk_fn(d)
            if w <= e_lim:
                lst.append((w, d, cid))
            if best is None or d < best[1]:
                best = (w, d, cid)
        lst.sort()
        cand_of[pid], nearest[pid] = lst, best

    assign, selected = {}, set()

    def put(pid, w, d, cid):
        assign[pid] = {"cand": cid, "walk_min": round(w, 1), "dist_m": round(d), "tier": "primary" if w <= p_lim else "extended"}
        selected.add(cid)

    if seed_ids:
        seeds = set(seed_ids)
        for pid, _, _ in points:
            pick = next(((w, d, c) for w, d, c in cand_of[pid] if c in seeds), None)
            if pick:
                put(pid, *pick)

    def greedy(pids, limit):
        cover = {}
        for pid in pids:
            for w, d, cid in cand_of[pid]:
                if w <= limit:
                    cover.setdefault(cid, {})[pid] = (w, d)
        uncovered = {pid for pid in pids if any(w <= limit for w, _, _ in cand_of[pid])}
        while uncovered:
            best = None
            for cid, m in cover.items():
                n = sum(1 for pid in m if pid in uncovered)
                if n == 0:
                    continue
                key = (n, prefer(cid) if prefer else 0, -sum(m[pid][0] for pid in m if pid in uncovered), cid)
                if best is None or key > best[0]:
                    best = (key, cid)
            if best is None:
                break
            cid = best[1]
            for pid, (w, d) in cover[cid].items():
                if pid in uncovered:
                    put(pid, w, d, cid)
                    uncovered.discard(pid)
        return uncovered

    rest = [pid for pid, _, _ in points if pid not in assign]
    no_primary = [pid for pid in rest if not any(w <= p_lim for w, _, _ in cand_of[pid])]
    greedy(rest, p_lim)
    rest2 = []
    for pid in no_primary:
        if pid in assign:
            continue
        pick = next(((w, d, c) for w, d, c in cand_of[pid] if c in selected), None)
        if pick:
            put(pid, *pick)
        else:
            rest2.append(pid)
    if rest2:
        greedy(rest2, e_lim)
    for pid, _, _ in points:
        if pid not in assign:
            w, d, cid = nearest[pid]
            assign[pid] = {"cand": cid, "walk_min": round(w, 1), "dist_m": round(d), "tier": "exception"}
            selected.add(cid)

    # 소규모 후보 통합
    while min_group > 0:
        sizes = {}
        for a in assign.values():
            sizes[a["cand"]] = sizes.get(a["cand"], 0) + 1
        moved = False
        for _, cid in sorted((n, c) for c, n in sizes.items() if n < min_group):
            members = [pid for pid, a in assign.items() if a["cand"] == cid]
            moves = {}
            for pid in members:
                alt = next(((w, d, c2) for w, d, c2 in cand_of[pid] if c2 in sizes and c2 != cid), None)
                if alt is None:
                    moves = None
                    break
                moves[pid] = alt
            if not moves:
                continue
            for pid, (w, d, c2) in moves.items():
                assign[pid] = {"cand": c2, "walk_min": round(w, 1), "dist_m": round(d), "tier": "primary" if w <= p_lim else "extended"}
            selected.discard(cid)
            moved = True
            break
        if not moved:
            break
    # 같은 등급 안에서 더 가까운 선정 후보로
    used = {a["cand"] for a in assign.values()}
    for pid, _, _ in points:
        a = assign[pid]
        lim = p_lim if a["tier"] == "primary" else e_lim
        for w, d, cid in cand_of[pid]:
            if w > lim:
                break
            if cid in used and w < a["walk_min"]:
                a.update({"cand": cid, "walk_min": round(w, 1), "dist_m": round(d)})
                break
    return assign, {a["cand"] for a in assign.values()}


# ----------------------------------------------------------------------------- routing
def make_routes(demand, depot, T, cap, detour_max=1.5, dwell=1, backtrack_slack=8, abs_slack=10):
    direct = {s: T(s, depot) for s in demand}
    allow = {s: max(detour_max * d, d + abs_slack) for s, d in direct.items()}
    routes, pending = [], []
    for s, items in demand.items():
        items = list(items)
        while len(items) > cap:
            routes.append([(s, items[:cap])])
            items = items[cap:]
        if items:
            pending.append((s, items))
    pending.sort(key=lambda x: (-direct[x[0]], str(x[0])))
    while pending:
        s0, e0 = pending.pop(0)
        route, load, cur = [(s0, e0)], len(e0), s0
        path_from = {s0: 0.0}
        while True:
            best = None
            for idx, (c, ec) in enumerate(pending):
                if load + len(ec) > cap or direct[c] > direct[cur] + backtrack_slack:
                    continue
                leg, fin = T(cur, c), T(c, depot)
                if not all(path_from[i] + leg + dwell + fin <= allow[i] for i in path_from):
                    continue
                extra = leg + fin - direct[cur]
                key = (leg + max(0.0, extra) * 0.5, -len(ec), str(c))
                if best is None or key < best[0]:
                    best = (key, idx, leg)
            if best is None:
                break
            _, idx, leg = best
            c, ec = pending.pop(idx)
            for i in path_from:
                path_from[i] += leg + dwell
            path_from[c] = 0.0
            route.append((c, ec))
            load += len(ec)
            cur = c
        routes.append(two_opt(route, depot, T, allow, dwell))
    return routes


def route_cost(seq, depot, T, dwell):
    t = sum(T(a[0], b[0]) + dwell for a, b in zip(seq, seq[1:]))
    return t + T(seq[-1][0], depot)


def _feasible(seq, depot, T, allow, dwell):
    for k in range(len(seq)):
        ride = sum(T(seq[j][0], seq[j + 1][0]) + dwell for j in range(k, len(seq) - 1)) + T(seq[-1][0], depot)
        if ride > allow[seq[k][0]] + 1e-9:
            return False
    return True


def two_opt(seq, depot, T, allow, dwell):
    if len(seq) < 3:
        return seq
    best, cost = seq, route_cost(seq, depot, T, dwell)
    improved = True
    while improved:
        improved = False
        for i in range(len(best) - 1):
            for j in range(i + 1, len(best)):
                cand = best[:i] + best[i:j + 1][::-1] + best[j + 1:]
                c = route_cost(cand, depot, T, dwell)
                if c + 1e-9 < cost and _feasible(cand, depot, T, allow, dwell):
                    best, cost, improved = cand, c, True
    return best


# ----------------------------------------------------------------------------- timetable
def timetable(route, inbound, depot, tt, anchor, dwell=1):
    stops, rides = [], {}
    n_items = sum(len(e) for _, e in route)
    if inbound:
        times = [None] * len(route)
        times[-1] = anchor - dt.timedelta(minutes=tt[(route[-1][0], depot)])
        for k in range(len(route) - 2, -1, -1):
            times[k] = times[k + 1] - dt.timedelta(minutes=tt[(route[k][0], route[k + 1][0])] + dwell)
        for k, (sid, items) in enumerate(route):
            stops.append({"seq": k + 1, "stop_id": sid, "time": _iso(times[k]), "boardings": len(items), "alightings": 0})
            rides[sid] = (anchor - times[k]).total_seconds() / 60
        stops.append({"seq": len(route) + 1, "stop_id": depot, "time": _iso(anchor), "boardings": 0, "alightings": n_items})
    else:
        order = route[::-1]
        stops.append({"seq": 1, "stop_id": depot, "time": _iso(anchor), "boardings": n_items, "alightings": 0})
        t = anchor + dt.timedelta(minutes=tt[(depot, order[0][0])])
        for k, (sid, items) in enumerate(order):
            if k > 0:
                t = t + dt.timedelta(minutes=dwell + tt[(order[k - 1][0], sid)])
            stops.append({"seq": k + 2, "stop_id": sid, "time": _iso(t), "boardings": 0, "alightings": len(items)})
            rides[sid] = (t - anchor).total_seconds() / 60
    return stops, rides
