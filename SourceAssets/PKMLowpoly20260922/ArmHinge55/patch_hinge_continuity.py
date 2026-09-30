"""Near-straight elbows: the bend axis from cross(upper, forearm) becomes unreliable, and a
straightening arm with a held hand would otherwise swing the anatomical frame through +-180.
Blend the geometric bend axis with the previous frame's axis by elbow bend (5..25 deg)."""
from pathlib import Path
p = Path(__file__).with_name('author.py')
s = p.read_text(encoding='utf8')
a = """        u, f = E - a[k], t[k] - E
        h = np.cross(u, f)
        if np.linalg.norm(h) < 1e-3 * np.linalg.norm(u) * np.linalg.norm(f) and h_prev is not None:
            h = h_prev
        h = unit(h - unit(u) * (unit(u) @ h))"""
b = """        u, f = E - a[k], t[k] - E
        h = np.cross(u, f)
        bend = np.degrees(np.arctan2(np.linalg.norm(h), u @ f))
        if h_prev is not None:
            carried = h_prev - unit(u) * (unit(u) @ h_prev)
            w = np.clip((bend - 5.0) / 20.0, 0.0, 1.0)
            w = w * w * (3 - 2 * w)
            h = w * unit(h) + (1 - w) * unit(carried) if np.linalg.norm(h) > 1e-9 else carried
        h = unit(h - unit(u) * (unit(u) @ h))"""
assert a in s
s = s.replace(a, b)
p.write_text(s, encoding='utf8')
print('patched')
