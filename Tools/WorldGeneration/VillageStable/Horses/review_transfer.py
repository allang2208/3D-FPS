"""Draw both native 60 Hz rider captures over the source Warhorse silhouette."""
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.spatial.transform import Rotation
from prepare_horse import Horse, OUT


def frames(path):
    grouped = defaultdict(lambda: defaultdict(list))
    with path.open(encoding="utf-8-sig") as stream:
        for row in csv.DictReader(stream):
            grouped[row["body"], row["action"]][row["bone"].lower()].append(
                [float(row[k]) for k in ("x", "y", "z", "qx", "qy", "qz", "qw")])
    return {key: {bone: np.array(track) for bone, track in bones.items()} for key, bones in grouped.items()}


def horse_surface():
    horse = Horse((OUT / "Warhorse_Stable.glb").read_bytes())
    doc = horse.doc
    prim = doc["meshes"][0]["primitives"][0]
    pos = horse.accessor(prim["attributes"]["POSITION"])[:, [2, 0, 1]] * [100, -100, 100]
    index = doc["accessors"][prim["indices"]]
    view = doc["bufferViews"][index["bufferView"]]
    ids = np.frombuffer(horse.bin, {5123: "<u2", 5125: "<u4"}[index["componentType"]],
                        index["count"], view.get("byteOffset", 0) + index.get("byteOffset", 0))
    return pos, ids.reshape(-1, 3)


def animated_croup(samples, triangles):
    horse = Horse((OUT / "Warhorse_Stable.glb").read_bytes())
    skin = horse.doc["skins"][0]
    prim = horse.doc["meshes"][0]["primitives"][0]
    idle = horse.clips["idle_loop"]
    period = horse.sample(idle)[0][-1]
    _, tracks = horse.sample(idle, np.arange(samples) / (60.0 * period))

    def raw(index, width):
        a = horse.doc["accessors"][index]
        b = horse.doc["bufferViews"][a["bufferView"]]
        dtype = {5121:"u1", 5123:"<u2", 5126:"<f4"}[a["componentType"]]
        return np.frombuffer(horse.bin, dtype, a["count"] * width,
                             b.get("byteOffset", 0) + a.get("byteOffset", 0)).reshape(-1, width)
    rest = horse.accessor(prim["attributes"]["POSITION"])
    bind = raw(skin["inverseBindMatrices"], 16).reshape(-1, 4, 4).transpose(0, 2, 1)
    joints = raw(prim["attributes"]["JOINTS_0"], 4)
    weights = horse.accessor(prim["attributes"]["WEIGHTS_0"])
    verts = np.zeros((samples, len(rest), 3))
    for ji, node in enumerate(skin["joints"]):
        weight = ((joints == ji) * weights).sum(axis=1)
        used = np.flatnonzero(weight > 0)
        if not len(used):
            continue
        local = rest[used] @ bind[ji,:3,:3].T + bind[ji,:3,3]
        rotation = horse.world_rot(node, tracks, samples).as_matrix()
        location = horse.world_pos(node, tracks, samples)
        verts[:, used] += (np.einsum("fij,vj->fvi", rotation, local) + location[:, None]) * weight[used,None]
    verts = verts[:,:,[2,0,1]] * [100,-100,100]
    # Restrict queries to the saddle and rump, excluding limbs, tack below the girth and the head.
    select = np.all((rest[triangles,1] > 1.05) & (rest[triangles,2] < .35), axis=1)
    return verts[:,triangles[select]]


def crossing_clearance(bones, surface):
    clear = []
    for f, (ankle, toe, seat) in enumerate(zip(bones["foot_r"], bones["ball_r"], bones["saddle_socket"])):
        for point in (ankle, toe):
            if abs(point[1]-seat[1]) > 15 or point[0] > seat[0]-8:
                continue
            a, b, c = surface[f].transpose(1,0,2)
            dx, dy = point[:2]-a[:,:2], b[:,:2]-a[:,:2]
            dc = c[:,:2]-a[:,:2]
            det = dy[:,0]*dc[:,1]-dy[:,1]*dc[:,0]
            valid = abs(det) > .00001
            u = np.divide(dx[:,0]*dc[:,1]-dx[:,1]*dc[:,0],det,out=np.zeros_like(det),where=valid)
            v = np.divide(dy[:,0]*dx[:,1]-dy[:,1]*dx[:,0],det,out=np.zeros_like(det),where=valid)
            hit = valid & (u>=0) & (v>=0) & (u+v<=1)
            if hit.any():
                z=(a[:,2]+u*(b[:,2]-a[:,2])+v*(c[:,2]-a[:,2]))[hit].max()
                clear.append((float(point[2]-z),f))
    return min(clear) if clear else (None,None)


def review(folder):
    before, after = [frames(folder / (name + ".csv")) for name in ("before", "final")]
    pos, tris = horse_surface()
    surface = animated_croup(max(len(b["pelvis"]) for b in after.values()), tris)
    report = {}
    for key, now in after.items():
        row = {}
        for label, bones in (("before", before[key]), ("after", now)):
            end = -1 if key[1] == "mount" else 0
            clearance, at = crossing_clearance(bones, surface)
            row[label + "_croup"] = dict(min_right_ankle_or_ball_above_croup_cm=round(clearance,2), frame=at)
            for side in "lr":
                # Use the same animated tread location to compare both captures.
                err = bones["ball_" + side][end, :3] - now["tread_" + side][end, :3] - [0, 0, 3.5]
                rot = Rotation.from_quat(bones["calf_" + side][:, 3:])
                turns = np.degrees((rot[1:] * rot[:-1].inv()).magnitude())
                thigh = Rotation.from_quat(bones["thigh_" + side][:,3:])
                knee = thigh.inv() * rot
                flex = np.degrees((knee[1:] * knee[:-1].inv()).magnitude())
                row[label + "_" + side] = dict(peak_relative_knee_deg_per_frame=round(flex.max(),2), seated_ball_error_cm=round(np.linalg.norm(err), 2),
                    peak_calf_deg_per_frame=round(turns.max(), 2), peak_frame=int(np.argmax(turns) + 1))
        report["/".join(key)] = row
    (folder / "frames.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    width, height = 400, 278
    font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 15)
    small = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 12)

    def project(v):
        x, y, z = np.asarray(v).T[:3]
        return np.stack((214 + (-.78*x + .62*y)*1.17, 261 - (.92*z + .15*x + .19*y)*.93), axis=-1)
    xy = project(pos)
    tile = Image.new("RGB", (width, height), "#f3f0e8")
    d = ImageDraw.Draw(tile)
    for tri in tris:
        d.polygon([tuple(pt) for pt in xy[tri]], fill="#d7d5cb")
    d.line((13, 261, width-12, 261), fill="#c4c1b7")
    clips = []
    for action, chinese in (("mount", "上马"), ("dismount", "下马")):
        count = len(after["jason", action]["pelvis"])
        for i in range(count):
            im = Image.new("RGB", (2*width+2, 2*height+34), "#284241")
            for y, actor in enumerate(("jason", "kaitlin")):
                for x, (version, data) in enumerate((("修改前", before), ("修改后", after))):
                    panel = tile.copy()
                    draw = ImageDraw.Draw(panel)
                    bones = data[actor, action]
                    point = lambda n: tuple(project(bones[n][i, :3]))
                    draw.line([point(n) for n in ("pelvis", "spine_03", "head")], fill="#495860", width=5)
                    for side, colour in (("r", "#c25332"), ("l", "#147582")):
                        names = ["pelvis"] + [n+"_"+side for n in ("thigh", "calf", "foot", "ball")]
                        draw.line([point(n) for n in names], fill=colour, width=4)
                        for n in names[1:]:
                            a, b = point(n)
                            draw.ellipse((a-2,b-2,a+2,b+2),fill=colour)
                        a,b = project(after[actor, action]["tread_"+side][i,:3])
                        draw.line((a-5,b,a+5,b), fill="#29271f", width=2)
                    draw.text((12,8), actor.title()+"  ·  "+version,font=font,fill="#1b3d3d")
                    im.paste(panel, (x*(width+2), y*(height+1)+32))
            draw=ImageDraw.Draw(im)
            draw.text((12,5),f"{chinese}    {i/60:.2f} 秒    第 {i+1}/{count} 帧",font=font,fill="white")
            draw.text((402,8),"左腿 青色    右腿 橙色    黑线 马镫踏板",font=small,fill="white")
            clips.append(im)
    clips[0].save(folder/"transfer.gif", save_all=True, append_images=clips[1:], duration=35,
                  loop=0, optimize=True, disposal=1)
    print(json.dumps(report,indent=1))


if __name__ == "__main__":
    review(Path(sys.argv[1]))
