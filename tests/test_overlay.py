"""kitlib.overlay 테스트. 실행: python -m unittest discover -s tests -v"""
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from kitlib import groupstats, overlay  # noqa: E402


def _sites(params, noise=0.0, seed=1, field=False):
    rnd = random.Random(seed)
    rows = []
    for X in range(-120, 121, 40):
        for Y in range(-120, 121, 40):
            if X * X + Y * Y > 140 * 140:
                continue
            for fx, fy in ((-10, -10), (10, 10), (-10, 10), (10, -10)) if field else ((0, 0),):
                x, y = X + fx, Y + fy
                dx = params["Tx"] + params["Mx"] * x - params["Rx"] * y
                dy = params["Ty"] + params["My"] * y + params["Ry"] * x
                if field:
                    dx += params["mx"] * fx - params["rx"] * fy
                    dy += params["my"] * fy + params["ry"] * fx
                rows.append({"x": x, "y": y, "fx": fx, "fy": fy,
                             "dx": dx + rnd.gauss(0, noise), "dy": dy + rnd.gauss(0, noise)})
    return rows


P6 = {"Tx": 1.5, "Ty": -0.8, "Mx": 0.02, "My": -0.01, "Rx": 0.015, "Ry": 0.005}


class TestOverlay(unittest.TestCase):
    def test_fit_wafer6_exact(self):
        fit = overlay.fit_linear(_sites(P6))
        for k, v in P6.items():
            self.assertAlmostEqual(fit["params"][k], v, places=6)
        self.assertAlmostEqual(fit["params"]["rotation"], 0.01, places=6)
        self.assertAlmostEqual(fit["params"]["non_ortho"], 0.01, places=6)
        self.assertLess(max(abs(r["rdx"]) for r in fit["residuals"]), 1e-6)

    def test_fit_wafer10_exact(self):
        p = dict(P6, mx=0.03, rx=-0.02, my=0.01, ry=0.04)
        fit = overlay.fit_linear(_sites(p, field=True), model="wafer10")
        for k, v in p.items():
            self.assertAlmostEqual(fit["params"][k], v, places=6)

    def test_rank_deficient_and_skip(self):
        rows = [{"x": i, "y": 0, "dx": 1, "dy": 1} for i in range(5)]  # 한 줄 위 → 회전 항 결정 불가
        with self.assertRaises(ValueError):
            overlay.fit_linear(rows)
        rows = _sites(P6) + [{"x": "", "y": 1, "dx": 1, "dy": 1}]
        self.assertEqual(overlay.fit_linear(rows)["skipped"], 1)

    def test_stats_and_flyers(self):
        st = overlay.axis_stats([1, -1, 1, -1])
        self.assertAlmostEqual(st["mean"], 0)
        self.assertAlmostEqual(st["m3s"], 3 * st["sigma"])
        rows = _sites(P6, noise=0.3)
        rows[3]["dx"] = 500.0
        flags = overlay.flag_flyers(rows, k=5)
        self.assertTrue(flags[3])
        self.assertEqual(sum(flags), 1)

    def test_wafer_summary_and_factors(self):
        rows = []
        for w in range(6):
            base = dict(P6, Mx=0.002, My=-0.001, Rx=0.0015, Ry=0.0005)
            p = dict(base, Tx=6.0) if w < 2 else base       # W0, W1: 평행이동 큰 웨이퍼
            for r in _sites(p, noise=0.2, seed=w):
                r.update(wafer=f"W{w}", tool="EX1" if w < 2 else "EX2")
                rows.append(r)
        summ = overlay.wafer_summary(rows, spec=5.0, flyer_k=6, keep_cols=["tool"])
        self.assertEqual(len(summ), 6)
        self.assertEqual([s["fail"] for s in summ], [True, True, False, False, False, False])
        self.assertAlmostEqual(summ[0]["Tx"], 6.0, places=1)
        top = overlay.contributions(summ[0], radius=150, residual_3s=summ[0]["res_x_3s"])[0]
        self.assertEqual(top["term"], "Tx")
        self.assertIn("APC", top["hint"])
        rank = groupstats.rank_factors(summ, ["tool"], flag=lambda r: r["fail"], min_n=1)
        self.assertEqual(rank[0]["worst_group"], "EX1")

    def test_equal_spec_boundary(self):
        rows = [{"wafer": "W", "x": x, "y": y, "dx": 2.0, "dy": 0.0} for x, y in ((0, 0), (1, 0), (0, 1), (1, 1), (2, 1))]
        self.assertFalse(overlay.wafer_summary(rows, spec=2.0)[0]["fail"])
        self.assertTrue(overlay.wafer_summary(rows, spec=2.0, fail_on_equal=True)[0]["fail"])

    def test_radial_and_svg(self):
        fit = overlay.fit_linear(_sites(P6, noise=0.1))
        prof = overlay.radial_profile(fit["residuals"], bins=3)
        self.assertEqual(sum(b["n"] for b in prof), fit["n"])
        svg = overlay.vector_map_svg(_sites(P6), title="W1 <test>")
        self.assertTrue(svg.startswith("<svg") and svg.endswith("</svg>"))
        self.assertIn("&lt;test&gt;", svg)


if __name__ == "__main__":
    unittest.main()
