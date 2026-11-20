"""Retouch the existing 4K atlas using the front view and visible rigged triangles.

Run with the project Python (NumPy, OpenCV, Numba, SciPy, Pillow).
The optional --proof directory receives unlit, rest-pose before/after closeups.
This standalone pass targets the original rest mesh. FaceR2/bake_orbital_finish.py
uses these features with the revised eye geometry for the production atlases.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from numba import njit
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from prepare_surface import BODY, glb_chunks

R1 = BODY / "UEAuthoringR1"
R2 = HERE.parents[2] / "Saved/HerbalistFaceReview/_work/original-mesh-atlas"
COLOR = "T_VillageHerbalist_Color.png"
W, H = 600, 490
# The drawing coordinates are a 2 px / mm front orthographic view of the rest head.
# The RigR1 input stores metres with +Y up and +Z forward.
PROJECTION_SCALE = 2000.
SS = 2


def primitive():
    doc, blob = glb_chunks(BODY / "RigR1/rigged.glb")
    mesh, = doc["meshes"]
    prim, = mesh["primitives"]

    def values(accessor_index):
        accessor = doc["accessors"][accessor_index]
        view = doc["bufferViews"][accessor["bufferView"]]
        width = {"VEC3": 3, "VEC2": 2, "SCALAR": 1}[accessor["type"]]
        dtype = np.dtype({5126: "<f4", 5125: "<u4", 5123: "<u2"}[accessor["componentType"]])
        span = view.get("byteStride", width * dtype.itemsize)
        offset = view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
        return np.ndarray((accessor["count"], width), dtype=dtype, buffer=blob, offset=offset,
                          strides=(span, dtype.itemsize))

    pos = values(prim["attributes"]["POSITION"])
    uv = values(prim["attributes"]["TEXCOORD_0"])
    faces = values(prim["indices"]).reshape(-1, 3).astype(np.int32)
    xy = np.column_stack([300. + pos[:, 0] * PROJECTION_SCALE, (1.681 - pos[:, 1]) * PROJECTION_SCALE])
    return xy.astype(np.float32), pos[:, 2].copy(), uv, faces


@njit
def barycentric(x, y, a, b, c, determinant):
    u = ((b[1] - c[1]) * (x - c[0]) + (c[0] - b[0]) * (y - c[1])) / determinant
    v = ((c[1] - a[1]) * (x - c[0]) + (a[0] - c[0]) * (y - c[1])) / determinant
    return u, v, 1. - u - v


@njit
def det(a, b, c):
    return (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])


@njit
def projection(xy, depth, uv, faces):
    depth_buffer = np.full((H * SS, W * SS), -np.inf, np.float32)
    face_ids = np.full(depth_buffer.shape, -1, np.int32)
    texcoord = np.zeros((H * SS, W * SS, 2), np.float32)
    project = xy * SS
    for face_id, indices in enumerate(faces):
        i, j, k = indices
        a, b, c = project[i], project[j], project[k]
        determinant = det(a, b, c)
        if abs(determinant) < 1e-7:
            continue
        for y in range(max(0, int(np.ceil(min(a[1], b[1], c[1])))),
                       min(H * SS, int(np.floor(max(a[1], b[1], c[1]))) + 1)):
            for x in range(max(0, int(np.ceil(min(a[0], b[0], c[0])))),
                           min(W * SS, int(np.floor(max(a[0], b[0], c[0]))) + 1)):
                u, v, w = barycentric(x, y, a, b, c, determinant)
                if min(u, v, w) < -1e-6:
                    continue
                z = u * depth[i] + v * depth[j] + w * depth[k]
                if z > depth_buffer[y, x]:
                    face_ids[y, x] = face_id
                    depth_buffer[y, x] = z
                    texcoord[y, x] = u * uv[i] + v * uv[j] + w * uv[k]
    return depth_buffer, face_ids, texcoord


def mask_polygon(points, feather):
    binary = np.zeros((H * SS, W * SS), np.uint8)
    cv2.fillPoly(binary, [np.rint(np.array(points) * SS).astype(np.int32)], 255)
    inside = cv2.distanceTransform(binary, cv2.DIST_L2, 5)
    f = np.clip(inside / (feather * SS), 0., 1.)
    return f * f * (3. - 2. * f)


def patch_layer(ref, src_view):
    y, x = np.indices((H * SS, W * SS), dtype=np.float32) / SS
    target = np.zeros_like(src_view, dtype=np.float32)
    weight = np.zeros_like(x)

    def feature(ref_center, fitted_center, scale, slope, outline, feather, strength, gain, offset):
        xx = (x - fitted_center[0]) / scale[0] + ref_center[0]
        yy = (y - fitted_center[1] - slope * (x - fitted_center[0])) / scale[1] + ref_center[1]
        mapped = cv2.remap(ref, xx, yy, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        fitted = mapped * np.array(gain, np.float32) + np.array(offset, np.float32)
        alpha = mask_polygon(outline, feather) * strength
        on = alpha > 0
        weight[on] = alpha[on]
        target[on] = fitted[on]

    # Isolate each eyelid aperture and its immediate crease. The upper rim and bridge
    # sit just above these polygons. The higher outer corner on image-right is a
    # discontinuity in the generated albedo; include both sides of it in the feather.
    feature((233., 85.), (231.5, 231.6), (3.05, 2.95), -.065,
            [(199,229), (208,222), (221,218.6), (239,218.5), (254,222), (262,229),
             (263,241), (253,246), (231,249), (214,248), (201,244)], 5.5, .88,
            (1.04, 1.04, 1.04), (13, 12, 11))
    feature((267.1, 84.8), (349.9, 231.1), (3., 2.95), .015,
            [(318,232), (327,223), (341,219), (357,218.5), (370,219), (382,221),
             (389,225), (388,237), (380,245), (361,249), (342,249), (327,247), (318,242)],
            5.5, .94, (1.04, 1.04, 1.04), (13, 12, 11))

    # Keep native brow hairs and taper the dense squared sections toward the browns
    # in the turnaround. These target samples end above the upper eyeglass rims.
    feature((232.5, 75.), (230.5, 196.7), (3.06, 2.5), .032,
            [(186,201), (200,193), (214,186), (234,185), (252,188), (266,195),
             (271,210), (260,210), (240,204), (215,202), (198,204), (187,206)],
            5., .6, (1., 1., 1.), (9, 8, 7))
    feature((267.1, 74.6), (351.7, 196.), (3.13, 2.6), -.014,
            [(309,206), (315,193), (328,188), (347,183), (366,184), (385,190),
             (399,199), (404,207), (394,205), (381,200), (363,201), (337,203), (320,211), (311,211)],
            5., .6, (1., 1., 1.), (9, 8, 7))

    # Follow the generated nostril centres and retain the surface response of the
    # original nose. The painted cue is limited to its underside and the wings.
    feature((250.2, 106.1), (291.6, 304.4), (3.32, 2.78), -.014,
            [(255,295), (258,285), (271,281), (289,286), (306,280), (321,282),
             (327,295), (324,310), (311,316), (293,320), (275,317), (263,311)],
            8., .50, (.92, .92, .92), (26, 24, 22))

    # Only the mouth and immediate vermilion border. The target has a narrow warm
    # upper lip, a more legible closure and a soft central lower-lip highlight.
    feature((250.1, 119.15), (291., 352.4), (3.15, 2.95), -.012,
            [(233,348), (245,344), (257,340), (276,336), (289,338), (300,335),
             (323,340), (337,345), (348,345), (349,356), (337,361), (321,368),
             (303,374), (281,374), (261,370), (247,364), (236,359)],
            7., .76, (1., 1., 1.), (12, 11, 9))
    # Borrow only high-frequency iris structure from the intact source eye. The
    # two reference patches still determine iris placement, aperture and color.
    source = src_view.astype(np.float32)
    residual = source - cv2.GaussianBlur(source, (0, 0), 2.1 * SS)
    for center_x, center_y in [(231.5, 231.6), (349.9, 231.1)]:
        dx = x - center_x
        dy = y - center_y
        xmap = (231.1 + dx * .98) * SS
        ymap = (231.7 + dy * .98) * SS
        detail = cv2.remap(residual, xmap, ymap, cv2.INTER_LINEAR)
        ellipse = np.exp(-.5 * ((dx / 10.6) ** 2 + (dy / 4.1) ** 2))
        target += detail * (.56 * ellipse[:, :, None])
    return np.clip(target, 0, 255), weight


def spectacle_surfaces(src, target, weight, zbuffer, ref):
    """Remove the displaced painted upper rim and recolor the actual fused rim."""
    y, x = np.indices(weight.shape, dtype=np.float32) / SS
    native = src.astype(np.float32)
    smooth = cv2.GaussianBlur(native, (0, 0), 3. * SS)
    new_view = native * (1. - weight[:, :, None]) + target * weight[:, :, None]
    combined = weight.copy()

    def layer(pigment, coverage):
        nonlocal new_view, combined
        new_view = new_view + (pigment - new_view) * coverage[:, :, None]
        combined = 1. - (1. - combined) * (1. - coverage)

    # The source brows touch the top of the mesh frames. Preserve their natural
    # texture while opening the narrow line of skin visible in the reference.
    for brow_index, (samples, widths, boundary) in enumerate([
        ([(182,199),(191,194),(202,189),(215,186.5),(227,186.7),
          (239,188),(251,191),(260,194),(267,199)],
         [0,1.7,3.,4.0,4.6,4.9,4.9,4.4,0],
         [(181,199),(192,190),(211,181),(228,179),(245,182),(260,187),
          (270,195),(273,210),(259,211),(234,205),(206,207),(189,207),(181,205)]),
        ([(311,198),(317,194),(327,191),(340,187.2),(354,185.7),
          (367,185.1),(381,188),(393,192.8),(404,198.7)],
         [0,3.8,4.8,5.,4.9,4.1,3.5,2.,0],
         [(306,203),(313,192),(324,185),(340,181),(360,178),(379,181),
          (393,186),(406,195),(406,207),(390,205),(370,202),(345,204),(324,210),(311,212)])
    ]):
        pts = np.asarray(samples, np.float32)
        # Nearby forehead albedo supplies the skin under the old dark brow.
        height = np.interp(x, pts[:,0], pts[:,1]).astype(np.float32)
        radius = np.interp(x, pts[:,0], widths).astype(np.float32)
        distance = np.abs(y - height)
        skin = cv2.remap(smooth, np.clip(x,198.,387.)*SS,
                         (height-15.)*SS, cv2.INTER_LINEAR)
        pigment = cv2.remap(native,x*SS,(y+6.7)*SS,cv2.INTER_LINEAR)
        # Blend the source hair detail with the dark warm color in the front view.
        pigment = np.clip(.60*pigment+np.array([25.,16.,13.],np.float32), 0., 151.)
        if brow_index == 0:
            ref_x = (x - 230.5)/3.05 + 232.5
            ref_mid = np.interp(ref_x,[217,222,226,231,236,240,244],
                                [79.,76.9,74.7,74.7,75.4,76.1,77.8])
        else:
            ref_x = (x - 351.7)/3.13 + 267.1
            ref_mid = np.interp(ref_x,[254,259,263,268,273,277,282],
                                [77.6,75.7,74.9,74.4,74.2,75.5,79.])
        sample_y = ref_mid.astype(np.float32)
        ref_hair = cv2.remap(ref,ref_x,(sample_y+(y-height)/2.7),cv2.INTER_CUBIC)
        ref_skin = cv2.remap(ref,ref_x,sample_y-5.,cv2.INTER_CUBIC)
        contrast = np.clip((ref_skin.mean(2)-ref_hair.mean(2)+12.)/83.,0.,1.)
        strand = np.clip((radius+2.1-distance)/3.9,0.,1.) * (.26+.74*contrast)
        hair = strand[:,:,None]
        brow_color = skin*(1.-hair) + pigment*hair
        layer(brow_color, mask_polygon(boundary, 3.5)*.96)

    # A second dark upper arc is baked into the skin *behind* the actual frame.
    # Estimate its surrounding lid color from clean, nearby skin inside the same
    # lens opening, graduating softly towards the crease at the outer eye.
    for points, cheek_span in [
        ([(183,220),(192,210),(205,206),(221,201),(236,201),(253,204),
          (263,209),(276,219),(279,229),(271,232),(260,225),(246,220),
          (234,217),(217,218),(200,223),(193,227),(185,230)], (205,253)),
        ([(305,223),(315,214),(328,207),(341,203),(356,201),(369,201),
          (381,205),(391,211),(397,220),(394,230),(383,230),(374,227),
          (360,222),(346,218),(331,221),(319,226),(311,231)], (329,378))
    ]:
        projection = mask_polygon(points, 3.5)
        cheek_x = np.clip(x, *cheek_span) * SS
        cheek_y = (258.5 + .0006 * (x - np.mean(cheek_span))**2) * SS
        skin = cv2.remap(smooth, cheek_x.astype(np.float32), cheek_y.astype(np.float32), cv2.INTER_LINEAR)
        # The lid has a soft fold below the rim, darker at the inner corners.
        upper_lid = 222.3 + .0017 * (x - np.mean(cheek_span))**2
        fold = np.exp(-((y - upper_lid + 2.7)/3.8)**2)
        ambient = .942 - .115*fold - .035*np.clip((np.abs(x-291.)-58.)/55.,0.,1.)
        skin *= (ambient[:,:,None]*np.array([1.,.992,.982],np.float32))
        layer(skin, projection * .98)

    bridge = mask_polygon([(274,218),(283,216),(301,216),(310,218),(309,230),
                           (303,231),(299,228),(284,228),(279,231),(274,230)], 2.)
    bridge_skin = cv2.remap(smooth, np.clip(x,283,300)*SS,
                            np.full_like(y,235.5*SS), cv2.INTER_LINEAR)
    layer(bridge_skin, bridge * .97)

    # The upper band is in front of the brow. Bound it against the top and
    # inner edges measured on the actual geometry, particularly where the
    # bridge meets the nose and their projected depths coincide.
    upper = [(165,214),(171,210),(183,206),(196,201),(209,198),(220,197),
             (233,196.2),(242,197.6),(251,200.3),(262,204.9),(272,209.6),
             (283,211.8),(292,212),(302,211),(310,208.8),(322,202.7),
             (333,198.3),(346,195.8),(358,195.1),(370,195.6),(381,198.5),
             (393,203.7),(405,209.1),(415,212.9),(417,217.8),(407,225.5),
             (397,227.6),(393,221),(387,214),(379,209.3),(370,206.4),
             (358,204.6),(347,204.4),(337,206),(327,209.5),(318,214.9),
             (311,225.7),(306.5,232),(302.7,226.5),(297.5,221.6),
             (292,220),(285.7,221.6),(280.8,226.1),(275.5,232),
             (270.2,224.6),(265,217.6),(257,212.4),(246,208.2),
             (234,205.8),(220,205.6),(209,207),(201,210),(193,215),
             (188,222),(184,228),(179,225.7),(173,222.1),(166,222.4)]
    top = mask_polygon(upper, 1.65)
    # The circular lower rims occupy their own thin depth layer. Project a
    # slightly oversized guide corridor and keep only points in that layer.
    left_curve = [(184,219),(184,236),(188,252),(195,266),(202,276),(212,283),
                  (222,287),(237,287),(250,284),(260,278),(268,268),
                  (273,254),(275,237),(275,226)]
    right_curve = [(306,225),(308,240),(311,255),(317,269),(326,279),
                   (338,285),(351,286),(365,285),(375,280),(384,269),
                   (391,253),(398,234),(400,220)]
    ring = np.zeros(weight.shape, np.uint8)
    for path in (left_curve, right_curve):
        cv2.polylines(ring, [np.round(np.asarray(path)*SS).astype(np.int32)], False,
                      255, 14*SS, cv2.LINE_AA)
    predicted_mm = 71.5 - .00040 * (x - 277.)**2 - .039 * (y - 210.)
    depth_error = np.abs(zbuffer * 1000. - predicted_mm)
    low = ring.astype(np.float32)/255. * np.clip((5.1-depth_error)/1.6,0.,1.)
    # As the inner lower arcs pass the nose, the nose is at comparable depth;
    # keep these corners inside the hand-traced edge.
    left_nose_edge = np.interp(y, [218,230,247,261,274,283,290],
                              [280,280,279,275,267,258,251])
    right_nose_edge = np.interp(y, [218,230,247,261,273,282,290],
                               [302,302,304,309,315,323,333])
    low *= np.where(x<291,np.clip((left_nose_edge-x)/1.6,0,1),
                         np.clip((x-right_nose_edge)/1.6,0,1))
    frame = np.maximum(top, low)
    # Upper brow and sleeve-like folds are close to the frame center depth.
    # The spatial masks already exclude them. At their outer limits additionally
    # reject front skin and hair seen through the opening.
    frame *= np.clip((6.5 - depth_error) / 1.6, 0., 1.)
    # A dark, warm acetate with irregular honey-colored flecks, following the
    # single physical contour. Existing value detail modulates its finish.
    filament = (np.sin(x*.155 + y*.139 + np.sin(x*.083-y*.094)*1.8) +
                .58*np.sin(x*.41 - y*.29 + .7*np.sin(y*.14)))
    amber = np.clip((filament+.26)/1.66, 0., 1.)**1.7
    grain = np.clip((native.mean(2)-95.)/.95, -30.,60.)*.10
    shell = (np.array([47.,32.,26.],np.float32) +
             amber[:,:,None]*np.array([67.,46.,26.],np.float32) + grain[:,:,None])
    layer(shell, frame*.96)

    # Recover one pigment/alpha pair for direct sampling into the original UV.
    denom = np.maximum(combined[:,:,None], 1.e-6)
    mixed = (new_view - native*(1. - combined[:,:,None]))/denom
    return np.clip(mixed,0.,255.).astype(np.float32), combined.astype(np.float32)



@njit
def bake_visible(xy, depth, faces, atlas_xy, face_ids, zbuffer, target, weight, atlas):
    out = atlas.copy()
    modified = np.zeros(atlas.shape[:2], np.uint8)
    visible = np.zeros(len(faces), np.bool_)
    for sy in range(180 * SS, 377 * SS):
        for sx in range(159 * SS, 421 * SS):
            face_id = face_ids[sy, sx]
            if face_id >= 0 and weight[sy, sx] > 0.:
                visible[face_id] = True
    for face_id in np.where(visible)[0]:
        i, j, k = faces[face_id]
        a, b, c = atlas_xy[i], atlas_xy[j], atlas_xy[k]
        determinant = det(a, b, c)
        if abs(determinant) < 1e-7:
            continue
        for y in range(max(0, int(np.ceil(min(a[1], b[1], c[1])))),
                       min(atlas.shape[0], int(np.floor(max(a[1], b[1], c[1]))) + 1)):
            for x in range(max(0, int(np.ceil(min(a[0], b[0], c[0])))),
                           min(atlas.shape[1], int(np.floor(max(a[0], b[0], c[0]))) + 1)):
                u, v, w = barycentric(x, y, a, b, c, determinant)
                if min(u, v, w) < -1e-6:
                    continue
                screen = (u * xy[i] + v * xy[j] + w * xy[k]) * SS
                sx, sy = int(round(screen[0])), int(round(screen[1]))
                if sx < 0 or sy < 0 or sx >= W * SS or sy >= H * SS:
                    continue
                alpha = weight[sy, sx]
                if alpha <= 0.:
                    continue
                # Allow the adjacent triangle at a shared edge if the surfaces are
                # within 0.45 mm; a second layer behind the eyelid cannot receive paint.
                z = u * depth[i] + v * depth[j] + w * depth[k]
                if face_ids[sy, sx] != face_id and abs(z - zbuffer[sy, sx]) > .00045:
                    nearby = False
                    for yy in range(max(0, sy-1),min(H*SS, sy+2)):
                        for xx in range(max(0, sx-1),min(W*SS, sx+2)):
                            if face_ids[yy,xx] == face_id:
                                sx, sy = xx, yy
                                alpha = weight[sy,sx]
                                nearby = True
                                break
                        if nearby:
                            break
                    if not nearby or alpha <= 0.:
                        continue
                for ch in range(3):
                    dst = round((1. - alpha) * atlas[y, x, ch] + alpha * target[sy, sx, ch])
                    out[y, x, ch] = max(0, min(255, dst))
                modified[y, x] = 1
    return out, modified


@njit
def occupied_texels(atlas_xy, faces, height, width):
    occupied = np.zeros((height,width),np.uint8)
    for face in faces:
        a,b,c = atlas_xy[face[0]],atlas_xy[face[1]],atlas_xy[face[2]]
        determinant = det(a,b,c)
        if abs(determinant)<1.e-7:
            continue
        for yy in range(max(0,int(np.ceil(min(a[1],b[1],c[1])))),
                        min(height,int(np.floor(max(a[1],b[1],c[1])))+1)):
            for xx in range(max(0,int(np.ceil(min(a[0],b[0],c[0])))),
                            min(width,int(np.floor(max(a[0],b[0],c[0])))+1)):
                if min(barycentric(xx,yy,a,b,c,determinant))>=-1.e-6:
                    occupied[yy,xx]=1
    return occupied


def extend_seams(before,after,changed,atlas_xy,faces):
    # Some tiny facial islands have one or two active texels at the boundary.
    # Color filtering reads their padding too; extend the local delta only
    # into unused atlas space and only where the closest UV belongs to the edit.
    from scipy.ndimage import distance_transform_edt
    occupied=occupied_texels(atlas_xy,faces,*changed.shape)
    h,w=changed.shape
    tile=256
    count=0
    for yi in range(0,h,tile):
        for xi in range(0,w,tile):
            top=max(0,yi-6)
            left=max(0,xi-6)
            bottom=min(h,yi+tile+6)
            right=min(w,xi+tile+6)
            active=changed[top:bottom,left:right]
            if not active.any():
                continue
            blank=occupied[top:bottom,left:right]==0
            distances,nearest=distance_transform_edt(blank,return_indices=True)
            border=blank & (distances<=4.) & (active[nearest[0],nearest[1]]!=0)
            border[:yi-top,:]=False
            border[:,:xi-left]=False
            border[yi+tile-top:,:]=False
            border[:,xi+tile-left:]=False
            yy,xx=np.where(border)
            ny=top+nearest[0,yy,xx]
            nx=left+nearest[1,yy,xx]
            orig_y,orig_x=top+yy,left+xx
            delta=after[ny,nx,:3].astype(np.int16)-before[ny,nx,:3].astype(np.int16)
            value=before[orig_y,orig_x,:3].astype(np.int16)+delta
            after[orig_y,orig_x,:3]=np.clip(value,0,255).astype(np.uint8)
            count+=len(yy)
    return count


def render_texels(atlas, texcoord, ids):
    sample = texcoord * np.array([atlas.shape[1], atlas.shape[0]], np.float32) - .5
    color = cv2.remap(atlas[:, :, :3], sample, None, cv2.INTER_LINEAR)
    color[ids < 0] = 119
    return color


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proof", type=Path)
    args = parser.parse_args()
    R2.mkdir(parents=True, exist_ok=True)
    color_path = R1 / COLOR
    rig_path = BODY / "RigR1/rigged.glb"
    ref_path = BODY / "MeshyR1/Inputs/01_front.png"
    atlas = np.asarray(Image.open(color_path)).copy()
    ref = np.asarray(Image.open(ref_path).convert("RGB")).astype(np.float32)
    xy, depth, uv, faces = primitive()
    zbuffer, ids, texcoord = projection(xy, depth, uv, faces)
    before = render_texels(atlas, texcoord, ids)
    target, weight = patch_layer(ref, before)
    target, weight = spectacle_surfaces(before, target, weight, zbuffer, ref)
    atlas_xy = uv * np.array([atlas.shape[1], atlas.shape[0]], np.float32) - .5
    after, changed = bake_visible(xy, depth, faces, atlas_xy, ids, zbuffer, target, weight, atlas)
    padding = extend_seams(atlas, after, changed, atlas_xy, faces)
    out = R2 / COLOR
    Image.fromarray(after).save(out)
    if args.proof:
        args.proof.mkdir(parents=True, exist_ok=True)
        for name, view in [("before", before), ("after", render_texels(after, texcoord, ids))]:
            image = Image.fromarray(view).resize((W, H), Image.Resampling.LANCZOS)
            image.save(args.proof / ("atlas_" + name + ".png"))
    report = {
        "source": {str(p.relative_to(BODY).as_posix()): file_hash(p) for p in (color_path, BODY / "Herbalist_Turnaround.png", ref_path, rig_path)},
        "output": {"file": COLOR, "sha256": file_hash(out), "size": [int(atlas.shape[1]), int(atlas.shape[0])]},
        "method": "Separate reference-aligned eye, brow, lower-nose and lip masks. Restore the upper lid under the misplaced painted arc and tint the existing glasses using their measured shape and depth. Bake into original UVs on front-visible rigged triangles.",
        "affected_texels_rgb": int(np.count_nonzero((after[:, :, :3] != atlas[:, :, :3]).any(axis=2))),
        "written_visibility_mask_texels": int(changed.sum()),
        "unused_uv_padding_texels": padding,
        "material_channels": ["BaseColor.RGB"],
        "review": "Unlit orthographic software projection of the actual rigged head and source atlas. UE lighting and in-game presentation are outside this texture proof."
    }
    (R2 / "face_texture_source.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
