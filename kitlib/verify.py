"""결과물 규칙 검증기 골격 (stdlib). 생성 코드와 별도로 규칙을 다시 센다.

    v = Violations(max_items=50)
    v.add("over_capacity", "정원 초과 %d/%d" % (n, cap), route=rid)      # code, message, **위치
    v.result(checked={"routes": 120, "rows": 3000}) → {"ok", "violations", "counts", "checked"}
    report_markdown(result) → 표 포함 마크다운
    mutate_check(check_fn, good_output, mutations) → [(이름, 잡힘여부)]  검증기 자체 검증: 일부러 깨뜨린 출력이 잡히는지
        mutations=[("정원 1로", lambda o: ...바꾼 복사본 반환), ...]
"""
import copy


class Violations:
    def __init__(self, max_items=50):
        self.items, self.counts, self.max_items = [], {}, max_items

    def add(self, code, message, **where):
        if len(self.items) < self.max_items:
            self.items.append({"code": code, "message": message, **where})
        self.counts[code] = self.counts.get(code, 0) + 1

    def result(self, checked=None):
        return {"ok": not self.counts, "violations": self.items, "counts": self.counts, "checked": checked or {}}


def report_markdown(res):
    total = sum(res["counts"].values())
    lines = ["# 규칙 검증", "", "- 검사: " + ", ".join("%s %s" % (k, v) for k, v in res.get("checked", {}).items()),
             "- 결과: **%s**" % ("통과" if res["ok"] else "위반 %d건" % total)]
    if res["counts"]:
        lines += ["", "| 코드 | 건수 |", "|---|---|"] + ["| %s | %d |" % kv for kv in sorted(res["counts"].items())]
        lines += ["", "| 코드 | 내용 | 위치 |", "|---|---|---|"]
        for x in res["violations"]:
            where = ", ".join("%s=%s" % (k, v) for k, v in x.items() if k not in ("code", "message"))
            lines.append("| %s | %s | %s |" % (x["code"], x["message"], where))
    return "\n".join(lines)


def mutate_check(check_fn, good_output, mutations):
    out = []
    base = check_fn(good_output)
    out.append(("원본 통과", bool(base["ok"])))
    for name, fn in mutations:
        bad = fn(copy.deepcopy(good_output))
        r = check_fn(bad)
        out.append((name, not r["ok"]))
    return out
