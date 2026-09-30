"""Pin the smoothed elbow swivel and forearm share to their per-pose values at both clip
ends, so a clip that starts or ends in an idle pose matches that idle exactly."""
from pathlib import Path
p = Path(__file__).with_name('author.py')
s = p.read_text(encoding='utf8')
rep = [
    ("""    psi = gaussian_filter1d(np.unwrap(psi_raw), 6, mode='nearest')""",
     """    psi = pinned_smooth(np.unwrap(psi_raw), 6)"""),
    ("""    tf = np.clip(gaussian_filter1d(np.clip(tau, -CAP, CAP), 4, mode='nearest'), -CAP, CAP)""",
     """    tf = np.clip(pinned_smooth(np.clip(tau, -CAP, CAP), 4), -CAP, CAP)"""),
    ("""def solve(Wall, bind):""",
     """def pinned_smooth(x, sigma):
    \"\"\"Gaussian smoothing whose first/last values equal the raw per-pose values (the
    correction fades out over 3 sigma), so clip boundaries match their idle poses.\"\"\"
    x = np.asarray(x, float)
    y = gaussian_filter1d(x, sigma, mode='nearest')
    n = len(x)
    if n < 2:
        return x.copy()
    i = np.arange(n)
    fade = lambda d: np.clip(1 - d / (3 * sigma), 0, 1) ** 2
    return y + (x[0] - y[0]) * fade(i) + (x[-1] - y[-1]) * fade(n - 1 - i)


def solve(Wall, bind):"""),
]
for a, b in rep:
    assert a in s, a[:60]
    s = s.replace(a, b)
p.write_text(s, encoding='utf8')
print('patched')
