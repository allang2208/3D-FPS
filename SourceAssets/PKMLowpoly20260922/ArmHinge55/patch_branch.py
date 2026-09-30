from pathlib import Path
p = Path(__file__).with_name('author.py')
s = p.read_text(encoding='utf8')
rep = [
    ("SWIVEL = np.radians(20.0)\nPSI = np.radians(np.arange(-20, 21, 2.0))",
     "SWIVEL = np.radians(45.0)\nPSI = np.radians(np.arange(-45, 46, 3.0))"),
    ("""    wrap = lambda x: (x + np.pi) % (2 * np.pi) - np.pi
""", """    wrap = lambda x: (x + np.pi) % (2 * np.pi) - np.pi

    def branch(tau, prev):
        # anatomical branch (-180..180 from the bind), with hysteresis near +-180 so a hand
        # held flipped does not jitter between the two forearm limits
        w = wrap(tau)
        if prev is not None and abs(w) > np.radians(150) and abs(w - prev) > np.pi:
            w += 2 * np.pi * np.round((prev - w) / (2 * np.pi))
        return w
"""),
("""            u, f, h, Dl, tau = pron(k, elbow(k, p), h_prev, 0.0)
            tau = wrap(tau)
""", """            u, f, h, Dl, tau = pron(k, elbow(k, p), h_prev, 0.0)
            tau = branch(tau, tprev)
"""),
("""            if best is None or cost < best[0]:
                best = (cost, p, h)
        _, p, h_prev = best""", """            if best is None or cost < best[0]:
                best = (cost, p, h, tau)
        _, p, h_prev, tprev = best"""),
("""    psi_raw, h_prev, psi_prev = [], None, 0.0""", """    psi_raw, h_prev, psi_prev, tprev = [], None, 0.0, None"""),
("""    rows, h_prev = [], None
    for k in range(n):
        E = elbow(k, psi[k])
        u, f, h, Dl, tau = pron(k, E, h_prev, 0.0)
        h_prev = h
        rows.append((E, u, f, h, Dl, wrap(tau)))""", """    rows, h_prev, tprev = [], None, None
    for k in range(n):
        E = elbow(k, psi[k])
        u, f, h, Dl, tau = pron(k, E, h_prev, 0.0)
        h_prev = h
        tprev = branch(tau, tprev)
        rows.append((E, u, f, h, Dl, tprev))"""),
("    tu = wrap(tau - tf)\n", "    tu = tau - tf\n"),
]
for a, b in rep:
    assert a in s, a[:60]
    s = s.replace(a, b)
p.write_text(s, encoding='utf8')
print('patched')
