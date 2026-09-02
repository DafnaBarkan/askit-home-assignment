"""Within- and between-audience variation for the real reviews in A and B.

Scores every review in audiences A and B on the three committed axes, then:

  Between-audience separation - PERMANOVA. Partitions the total sum of squares
      SST = SSW + SSB and reports R2 = SSB/SST with a pseudo-F and a p-value
      from 999 label permutations.
  Within-audience heterogeneity - betadisper / PERMDISP. Distance from each
      review's vector to its own audience centroid; groups compared by F on
      those distances, p from 999 label permutations.

Distances are Euclidean, so the group centroid in PCoA space is the ordinary
arithmetic centroid and both statistics can be computed from group means
directly - no N x N distance matrix is materialised.

Both statistics are reported twice: on the raw axis values, and on axes
z-scored over the pooled A+B sample. The axes have different natural spreads,
so the raw version lets positivity dominate the distance; the z-scored version
weights the three axes equally. Neither is more correct, they answer slightly
different questions, so both are shown.

Run: .venv/bin/python src/analyze_audiences.py
"""

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from metrics import score_texts  # noqa: E402

AUDIENCES_PATH = "data/audiences.json"
VECTORS_PATH = "data/metrics_AB.json"

GROUPS = ["A", "B"]
AXES = ["positivity", "self_other", "tense"]
N_PERMUTATIONS = 999
SEED = 42


def section(title):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def sums_of_squares(X, labels, group_ids):
    """(SST, SSW, SSB) for Euclidean distances, from centroids only."""
    grand = X.mean(axis=0)
    sst = float(((X - grand) ** 2).sum())
    ssw = 0.0
    for g in group_ids:
        Xg = X[labels == g]
        ssw += float(((Xg - Xg.mean(axis=0)) ** 2).sum())
    return sst, ssw, sst - ssw


def permanova(X, labels, rng, n_perm=N_PERMUTATIONS):
    group_ids = np.unique(labels)
    n, a = len(X), len(group_ids)
    sst, ssw, ssb = sums_of_squares(X, labels, group_ids)
    f_obs = (ssb / (a - 1)) / (ssw / (n - a))

    perm_labels = labels.copy()
    count = 0
    for _ in range(n_perm):
        rng.shuffle(perm_labels)
        _, ssw_p, ssb_p = sums_of_squares(X, perm_labels, group_ids)
        f_p = (ssb_p / (a - 1)) / (ssw_p / (n - a))
        if f_p >= f_obs:
            count += 1
    p = (count + 1) / (n_perm + 1)

    return {"SST": sst, "SSW": ssw, "SSB": ssb, "R2": ssb / sst, "F": f_obs, "p": p}


def betadisper(X, labels, rng, n_perm=N_PERMUTATIONS):
    """Distance of each point to its group centroid, then an F test on those."""
    group_ids = np.unique(labels)
    dists = np.empty(len(X))
    for g in group_ids:
        mask = labels == g
        dists[mask] = np.linalg.norm(X[mask] - X[mask].mean(axis=0), axis=1)

    def f_stat(d, lab):
        grand = d.mean()
        n, a = len(d), len(group_ids)
        between = sum(int((lab == g).sum()) * (d[lab == g].mean() - grand) ** 2 for g in group_ids)
        within = sum(float(((d[lab == g] - d[lab == g].mean()) ** 2).sum()) for g in group_ids)
        return (between / (a - 1)) / (within / (n - a))

    f_obs = f_stat(dists, labels)
    perm_labels = labels.copy()
    count = 0
    for _ in range(n_perm):
        rng.shuffle(perm_labels)
        if f_stat(dists, perm_labels) >= f_obs:
            count += 1

    per_group = {g: {
        "n": int((labels == g).sum()),
        "mean_dist": float(dists[labels == g].mean()),
        "median_dist": float(np.median(dists[labels == g])),
        "sd_dist": float(dists[labels == g].std(ddof=1)),
    } for g in group_ids}

    return {"F": f_obs, "p": (count + 1) / (n_perm + 1), "per_group": per_group}, dists


def main():
    with open(AUDIENCES_PATH, encoding="utf-8") as f:
        audiences = json.load(f)

    records = []
    for g in GROUPS:
        for rec in audiences[g]:
            records.append({"group": g, "user_id": rec["user_id"],
                            "age": int(rec["age"]), "rating": int(rec["rating"]),
                            "text": rec["review_text"]})

    sizes = ", ".join(f"{g}={sum(1 for r in records if r['group'] == g):,}" for g in GROUPS)
    print(f"scoring {len(records):,} reviews ({sizes}) ...", flush=True)

    scored = list(score_texts([r["text"] for r in records]))
    for rec, s in zip(records, scored):
        rec.update(s)

    with open(VECTORS_PATH, "w", encoding="utf-8") as out:
        json.dump([{k: v for k, v in r.items() if k != "text"} for r in records],
                  out, ensure_ascii=False, indent=1)

    # --- completeness --------------------------------------------------------
    section("AXIS COMPLETENESS (NaN = empty denominator)")
    print(f"  {'group':<7}{'n':>8}" + "".join(f"{a:>14}" for a in AXES) + f"{'complete':>11}")
    usable = []
    for g in GROUPS:
        rows = [r for r in records if r["group"] == g]
        nan_counts = [sum(1 for r in rows if np.isnan(r[a])) for a in AXES]
        complete = [r for r in rows if not any(np.isnan(r[a]) for a in AXES)]
        usable.extend(complete)
        print(f"  {g:<7}{len(rows):>8,}" + "".join(f"{c:>14,}" for c in nan_counts)
              + f"{len(complete):>11,}")

    X = np.array([[r[a] for a in AXES] for r in usable], dtype=float)
    labels = np.array([r["group"] for r in usable])

    # --- per-axis descriptives ----------------------------------------------
    section("AXIS DESCRIPTIVES (complete cases)")
    print(f"  {'axis':<12}{'group':<7}{'mean':>10}{'sd':>10}{'median':>10}{'min':>9}{'max':>9}")
    for i, axis in enumerate(AXES):
        for g in GROUPS:
            v = X[labels == g, i]
            print(f"  {axis:<12}{g:<7}{v.mean():>10.4f}{v.std(ddof=1):>10.4f}"
                  f"{np.median(v):>10.4f}{v.min():>9.3f}{v.max():>9.3f}")
        d = X[labels == "A", i].mean() - X[labels == "B", i].mean()
        pooled = X[:, i].std(ddof=1)
        print(f"  {'':<12}{'A-B':<7}{d:>10.4f}   (Cohen's d = {d / pooled:+.4f})")

    rng = np.random.default_rng(SEED)

    for scaling in ("raw", "z-scored"):
        Xs = X if scaling == "raw" else (X - X.mean(axis=0)) / X.std(axis=0, ddof=1)

        section(f"BETWEEN-AUDIENCE SEPARATION - PERMANOVA ({scaling} axes)")
        res = permanova(Xs, labels, np.random.default_rng(SEED))
        print(f"  SST : {res['SST']:>14.4f}")
        print(f"  SSW : {res['SSW']:>14.4f}   ({100 * res['SSW'] / res['SST']:.3f}% of SST)")
        print(f"  SSB : {res['SSB']:>14.4f}   ({100 * res['SSB'] / res['SST']:.3f}% of SST)")
        print(f"  R2  : {res['R2']:>14.6f}")
        print(f"  F   : {res['F']:>14.4f}")
        print(f"  p   : {res['p']:>14.4f}   ({N_PERMUTATIONS} permutations)")

        section(f"WITHIN-AUDIENCE HETEROGENEITY - betadisper ({scaling} axes)")
        disp, _ = betadisper(Xs, labels, np.random.default_rng(SEED))
        print(f"  {'group':<7}{'n':>8}{'mean dist':>12}{'median':>10}{'sd':>10}")
        for g in GROUPS:
            s = disp["per_group"][g]
            print(f"  {g:<7}{s['n']:>8,}{s['mean_dist']:>12.4f}"
                  f"{s['median_dist']:>10.4f}{s['sd_dist']:>10.4f}")
        print(f"\n  F : {disp['F']:.4f}    p : {disp['p']:.4f}   "
              f"({N_PERMUTATIONS} permutations)")

    section("OUTPUT")
    print(f"  per-review vectors written to {VECTORS_PATH} ({len(records):,} rows)")
    print(f"  seed {SEED}; {N_PERMUTATIONS} permutations per test")


if __name__ == "__main__":
    main()
