"""Make the split pose-deterministic: the same pose gives the same arm in every clip."""
from pathlib import Path
p = Path(__file__).with_name('author.py')
s = p.read_text(encoding='utf8')
a = s.index('    wrap = lambda x: (x + np.pi) % (2 * np.pi) - np.pi')
b = s.index('    # before: current helper roll off the bend axis (report)')
new = '''    wrap = lambda x: (x + np.pi) % (2 * np.pi) - np.pi
    # 1. elbow adjust, decided per pose (no history): least upper-arm remainder beyond the
    #    forearm cap, elbow moved at most ELBOW_CM on the shoulder-wrist circle.
    psi_raw, h_prev = [], None
    for k in range(n):
        best = None
        for p in PSI:
            E = elbow(k, p)
            d = np.linalg.norm(E - e[k])
            if d > ELBOW_CM:
                continue
            u, f, h, Dl, tau = pron(k, E, h_prev, 0.0)
            tau = wrap(tau)
            rem = abs(tau) - CAP if abs(tau) > CAP else 0.0
            cost = rem ** 2 + .02 * (d / 5.0) ** 2
            if best is None or cost < best[0] - 1e-9:
                best = (cost, p, h)
        _, p, h_prev = best
        psi_raw.append(p)
    psi = gaussian_filter1d(np.unwrap(psi_raw), 6, mode='nearest')
    # 2. pronation split with the smoothed elbow
    rows, h_prev = [], None
    for k in range(n):
        E = elbow(k, psi[k])
        u, f, h, Dl, tau = pron(k, E, h_prev, 0.0)
        h_prev = h
        rows.append((E, u, f, h, Dl, wrap(tau)))
    tau = np.array([r[5] for r in rows])
    tf = np.clip(gaussian_filter1d(np.clip(tau, -CAP, CAP), 4, mode='nearest'), -CAP, CAP)
    tu = wrap(tau - tf)
'''
s = s[:a] + new + s[b:]
s = s.replace("SWIVEL = np.radians(45.0)\nPSI = np.radians(np.arange(-45, 46, 3.0))",
              "ELBOW_CM = 6.0  # the elbow may move this far on the shoulder-wrist circle\nPSI = np.radians(np.arange(-90, 91, 3.0))")
s = s.replace("  1. elbow may swivel on the shoulder-wrist circle (|psi| <= 20 deg, smoothed) to reduce\n     the roll that cannot go into the forearm;",
              "  1. elbow may move up to 6 cm on the shoulder-wrist circle (decided per pose, then\n     smoothed) to reduce the roll that cannot go into the forearm;")
p.write_text(s, encoding='utf8')
print('patched', 'ELBOW_CM' in s)
