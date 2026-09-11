"""Verify actual audit screenshots, not only camera FOV/mesh existence."""
from pathlib import Path
from PIL import Image
import json, math, sys

folder = Path(sys.argv[1])
hidden_hud = "--hidden-hud" in sys.argv[2:]
results = []
for phase in ("write", "reload"):
    for name in ("lpvo-1x", "lpvo-2x", "lpvo-4x", "lpvo-6x", "lpvo-reopen-4x", "lpvo-reopen-2x"):
        path = folder / f"{phase}-{name}.png"
        im = Image.open(path).convert("RGB")
        w, h = im.size
        cx, cy = w // 2, h // 2
        offset = round(h / 15)
        y = cy + offset
        def clear(x):
            return min(im.getpixel((x, y))) > 100
        assert clear(cx), (path, "physical model still occludes center")
        # Find the outer rim against the black surround, rather than treating
        # dark world objects inside the 1x view as physical bore obstruction.
        lit = [x for x in range(w) if max(im.getpixel((x, y))) > 10]
        span = lit[-1] - lit[0] + 1
        expected = 2 * math.sqrt((min(w, h) * (.425 + 9/900)) ** 2 - offset ** 2)
        assert abs(span - expected) < 8, (path, span, expected)
        assert max(im.getpixel((20, cy - 60))) < 5, (path, "scope surround missing")
        if hidden_hud:
            for point in ((cx,25),(cx,h-40),(20,cy),(60,h-95),(w-90,h-40)):
                assert max(im.getpixel(point)) < 5, (path, "HUD panel remains", point)
            assert min(im.getpixel((cx,round(h*.12)))) > 100, (path, "timeline remains inside scope")
        else:
            assert sum(im.getpixel((cx, 25))) > 30, (path, "health HUD masked")
        red = im.getpixel((cx, cy))
        assert red[0] > 150 and red[0] > red[1] * 2, (path, "center reticle missing")
        results.append(dict(file=path.name, measured_chord_px=span, expected_chord_px=expected,
                            clear_diameter_screen_fraction=.85, reticle_center=True, hud_visible=not hidden_hud))
    if hidden_hud:
        hip = Image.open(folder / f"{phase}-lpvo-hip-restored.png").convert("RGB")
        assert sum(hip.getpixel((hip.width//2,25))) > 30, "health HUD did not restore"
        assert sum(hip.getpixel((hip.width//2,hip.height-40))) > 30, "hotbar did not restore"
report = dict(status="PASS", screenshots=len(results), hud_restoration_checked=hidden_hud, measurements=results)
(folder / "aperture_acceptance.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(dict(status="PASS", screenshots=len(results))))
