import json
from pathlib import Path
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont

base = Path(__file__).resolve().parent
run = base / (base / "latest.txt").read_text().strip()
labels = ["原厂带脚架", "卸下脚架", "重连 · 无脚架", "装回原厂脚架", "再次重连"]
boards = {r: [Image.open(run / f"{r}-{s}.png").convert("RGB") for s in range(5)] for r in ["host", "guest"]}
def grayscale(im):
    return cv2.cvtColor(np.asarray(im), cv2.COLOR_RGB2GRAY)

template_board = base.parents[1] / "M249BagIconWire/20261112-151132/run-152245/guest-0.png"
template = grayscale(Image.open(template_board).convert("RGB").crop((851, 768, 923, 784)))
def row(im):
    screen = grayscale(im)
    starts = []
    for xlo in (840,1084):
        patch = screen[410:884,xlo:xlo+112]
        _,score,_,pos = cv2.minMaxLoc(cv2.matchTemplate(patch, template, cv2.TM_CCOEFF_NORMED))
        assert score > .9, (score,pos)
        starts.append((xlo+pos[0],410+pos[1]))
    assert abs(starts[0][1]-starts[1][1]) <= 1
    return starts
anchors = {r:[row(im) for im in v] for r,v in boards.items()}
early = {r:Image.open(run/(r+"-immediate.png")).convert("RGB") for r in boards}
early_anchors = {r:row(im) for r,im in early.items()}
def cut(im, anchor):
    x,y = anchor
    return np.asarray(im.crop((x-4,y+17,x+178,y+71)), dtype=np.int16)
def delta(left, right):
    return int((np.abs(left-right).max(axis=2)>8).sum())
def pixels(role, first, last, card):
    pieces = []
    for step in (first,last):
        x,y = anchors[role][step][card]
        pieces.append(np.asarray(boards[role][step].crop((x-4,y+17,x+178,y+71)), dtype=np.int16))
    a,b = pieces
    return int((np.abs(a - b).max(axis=2) > 8).sum())

def receipt(role, step):
    lines = (run / f"{role}-{step}.sample").read_text(encoding="utf-8-sig").splitlines()
    return dict(s.split("=", 1) for s in lines)

stats = {}
for role, shots in boards.items():
    changes = []
    saved = [receipt(role, s) for s in range(5)]
    assert len({r["profile"] for r in saved}) == len({r["instance"] for r in saved}) == len({r["control"] for r in saved}) == 1
    assert all(r["mode"] == ("listen" if role == "host" else "client") for r in saved)
    assert saved[1]["recipe"] == saved[2]["recipe"] != saved[0]["recipe"] == saved[3]["recipe"] == saved[4]["recipe"]
    assert all(r["control_recipe"] == saved[0]["recipe"] for r in saved)
    for s in range(1, 5):
        changes.append({"from": s - 1, "to": s, "modified": pixels(role,s-1,s,0),
                        "control": pixels(role,s-1,s,1)})
    stats[role] = {"owner_profile": saved[0]["profile"], "modified_instance": saved[0]["instance"],
                   "control_instance": saved[0]["control"], "recipe": saved[1]["recipe"], "changes": changes,
                   "last_vs_original": [pixels(role,0,4,card) for card in (0,1)],
                   "processes": [r["process"] for r in saved],
                   "icons": [{"phase": s, "dynamic": saved[s]["dynamic"] == "1",
                              "control_dynamic": saved[s]["control_dynamic"] == "1",
                              "failure": saved[s]["fallback"],
                              "modified_vs_original": pixels(role,0,s,0),
                              "control_vs_original": pixels(role,0,s,1)} for s in range(5)]}

assert len({stats[r][k] for r in stats for k in ("modified_instance", "control_instance")}) == 4
assert stats["host"]["recipe"] != stats["guest"]["recipe"]
assert len(set(stats["host"]["processes"])) == 1 and len(set(stats["guest"]["processes"])) == 3
report = {"threshold": "max RGB channel delta > 8, icon interior only", "phases": labels, "roles": stats,
          "fitted_icon_failures": [f"{role}-{s}" for role in stats for s in (1,2)
                                   if not stats[role]["icons"][s]["dynamic"]]}
report["immediate"]={}
for role in boards:
    mod= cut(early[role], early_anchors[role][0])
    ref= cut(early[role], early_anchors[role][1])
    report["immediate"][role]={
        "modified_vs_own_factory":delta(mod,cut(boards[role][0],anchors[role][0][0])),
        "modified_vs_only_bipod_removed":delta(mod,cut(boards["host"][1],anchors["host"][1][0])),
        "control_vs_own_factory":delta(ref,cut(boards[role][0],anchors[role][0][1]))}
(run / "comparison.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 17)
small = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 15)
sheet = Image.new("RGB", (1090, 653), "#1d2126")
draw = ImageDraw.Draw(sheet)
for col, (role, title, parts) in enumerate([("host", "主机", "只卸脚架"), ("guest", "客户端", "卸脚架、换幻影后握把")]):
    x = 130 + col * 477
    draw.text((x, 10), title + "  ·  " + parts, font=font, fill="#efece5")
    draw.text((x, 40), "改装枪", font=small, fill="#bbd6c8")
    draw.text((x+245, 40), "同背包原厂对照", font=small, fill="#c2c9d1")
    displayed=[(boards[role][0],anchors[role][0][0],labels[0]),(early[role],early_anchors[role][0],"应用后首帧")]
    displayed.extend((boards[role][i],anchors[role][i][0],labels[i]) for i in range(1,5))
    for idx,(im,(left,top),label) in enumerate(displayed):
        y = 70 + idx * 96
        sheet.paste(im.crop((left-10,top-5,left+454,top+81)), (x, y))
        if col == 0:
            draw.text((10, y + 28), label, font=small, fill="#dce1e7")
sheet.save(run / "bag-wire-comparison.png")
print(json.dumps(stats, ensure_ascii=True))
