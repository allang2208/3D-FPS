"""Generate the village DEM, the three reusable relief variants and deterministic planting points.
Run with the directory containing study.f32 and edge_dirt.u8 exported by author_region.py.
Coordinates are in metres, elevation is stored in signed centimetres in little-endian order.
"""
import json
import struct
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt, gaussian_filter, map_coordinates


def smooth(a, b, v):
    t = np.clip((v - a) / (b - a), 0., 1.)
    return t * t * (3. - 2. * t)


def write_height(directory, name, heights):
    Image.fromarray(np.rint(32768 + heights).clip(0, 65535).astype("uint16")).save(directory / (name + ".png"))


def generate(directory):
    samples = np.fromfile(directory / "study.f32", dtype="<f4")
    study = samples[:505**2].reshape(505, 505)
    platform = samples[505**2:].reshape(146, 119)
    datum = float(study[-1, 144])
    # The approved road imprint belongs to the original. Extract broad shape and
    # middle frequencies, then resample them independently to avoid copying the road.
    broad = gaussian_filter(study, 12)
    low, high = np.percentile(broad, [5, 95])
    shape = np.clip((broad - (low + high) * .5) / max(10., (high - low) * .5), -1.6, 1.6)
    detail = gaussian_filter(study, 4) - gaussian_filter(study, 22)
    detail = np.clip(detail / max(1., np.percentile(np.abs(detail), 92)), -1.5, 1.5)
    row, col = np.mgrid[0:1025, 0:1025]
    x, y = col - 624, row - 320

    def sample(field, angle, scale, a, b):
        c, s = np.cos(angle), np.sin(angle)
        # Mirrored continuation has a smooth derivative after the source filtering.
        return map_coordinates(field, [(s*x+c*y)*scale+b, (c*x-s*y)*scale+a], order=1, mode="reflect")

    glade = 68*sample(shape, .44, .85, 180, 33) + 15*sample(detail, -.37, .75, 7, 210)
    shoulder = 240*sample(shape, -1.03, .72, 39, 114) + 35*sample(detail, .76, .83, 105, 15)
    ridge = 340*sample(shape, .92, .63, 240, 180) + 55*sample(detail, -.56, .64, 81, 129)
    for name, field in (("Glade", glade), ("Shoulder", shoulder), ("Ridge", ridge)):
        write_height(directory, "H_" + name, field[::2, ::2])

    def rise(cx, cy, along, across, angle):
        dx, dy = x-cx, y-cy
        u = (dx*np.cos(angle) + dy*np.sin(angle))/along
        v = (-dx*np.sin(angle) + dy*np.cos(angle))/across
        return 1 - smooth(0., 1., np.sqrt(u*u+v*v))

    west = rise(-475, 170, 345, 140, 1.10)
    north = rise(-270, 605, 287, 105, -.20)
    east = rise(297, 445, 218, 94, 1.02)
    ridge_mask = np.maximum.reduce([west, north, east])
    shoulder_mask = np.maximum(rise(-418, -159, 216, 118, .50), rise(76, 508, 234, 107, .39))
    height = datum + glade + shoulder_mask*(180+shoulder) + west*2050+north*1750+east*1220 + ridge_mask*ridge

    original = np.zeros(height.shape, dtype=bool)
    reference = np.zeros_like(height)
    dirt_reference = np.zeros_like(height)
    def place(xx, yy, data):
        iy, ix = yy+320, xx+624
        span = np.s_[iy:iy+data.shape[0], ix:ix+data.shape[1]]
        reference[span] = data
        original[span] = True
    place(-252, -252, study)
    place(-172, 252, platform)
    edge = np.fromfile(directory / "edge_dirt.u8", dtype=np.uint8).reshape(4, 505)/255.
    dirt_reference[68,372:877] = edge[0]
    dirt_reference[572,372:877] = edge[1]
    dirt_reference[68:573,372] = edge[2]
    dirt_reference[68:573,876] = edge[3]
    distance, near = distance_transform_edt(~original, return_indices=True)
    ny, nx = near
    near_z = reference[ny, nx]
    # Extend the incoming gradient for the first few metres. A filtered version
    # of the nearest-edge heights removes Voronoi creases farther out.
    ny_in = np.clip(ny + np.sign(ny-row), 0, 1024)
    nx_in = np.clip(nx + np.sign(nx-col), 0, 1024)
    run = np.maximum(1., np.hypot(nx-nx_in, ny-ny_in))
    gradient = np.where(original[ny_in,nx_in], (near_z-reference[ny_in,nx_in])/run, 0.)
    collar = near_z + np.clip(gradient,-25.,25.) * distance*np.exp(-distance/5.)
    collar += (gaussian_filter(near_z, 5)-near_z)*smooth(2., 14., distance)
    blend = smooth(0., 42., distance)
    height = np.where(original, reference, collar*(1-blend)+height*blend)

    grove = np.clip(.43 + .25*sample(shape, 1.7, 1.45, 46, 118)
                    +.16*np.sin(x*.021+y*.011)+.16*np.cos(y*.019-x*.008)
                    +.22*ridge_mask, 0., 1.)
    # Leave a grassy apron at the village. At the forest edges carry the canopy
    # out into the surrounding groves, then open it gradually into the meadows.
    village_gap = np.hypot(np.maximum.reduce([-172-x, x+54, np.zeros_like(x)]),
                           np.maximum.reduce([252-y, y-397, np.zeros_like(y)]))
    forest_gap = np.hypot(np.maximum(np.abs(x)-252,0), np.maximum(np.abs(y)-252,0))
    grove = np.maximum(grove, .90*(1-smooth(0.,38.,forest_gap))) * smooth(3.,30.,village_gap)
    moss = np.clip(.08+.78*grove+.08*sample(detail, .24, 1.4, 61, 48), 0, .94)
    dirt = np.clip(.025+.25*grove+.10*sample(detail, 1.5, 1.7, 159, 14), 0, .48)
    forest_edge = (forest_gap <= village_gap) & (forest_gap < 14.)
    fade = (1.-smooth(0.,14.,forest_gap))*forest_edge
    dirt = dirt*(1-fade) + dirt_reference[ny,nx]*fade
    moss = moss*(1-fade) + fade
    paint = np.stack((dirt,moss), axis=-1)
    paint = np.rint(255*paint).astype("uint8")
    paint.tofile(directory / "paint.rg8")
    hcm = np.rint(height).astype("<i2")
    hcm.tofile(directory / "region.i16")
    write_height(directory, "H_ForestVillage_1024m", height)
    slope_y, slope_x = np.gradient(height / 100.)
    slope = np.hypot(slope_y, slope_x)
    rng = np.random.default_rng(237146)
    counts = {}
    records = bytearray()

    def plant(name, spacing, weight, slots, lo, hi, setback):
        axis = np.arange(spacing/2, 1024-spacing*.43, spacing)
        gx, gy = np.meshgrid(axis, axis)
        px = gx + rng.uniform(-.43,.43,gx.shape)*spacing
        py = gy + rng.uniform(-.43,.43,gy.shape)*spacing
        ix, iy = np.rint(px).astype(int), np.rint(py).astype(int)
        keep = ((distance[iy,ix]>setback) & (village_gap[iy,ix]>setback+2)
                & (rng.random(gx.shape)<weight[iy,ix]) & (slope[iy,ix]<.57))
        px, py = px[keep]-624, py[keep]-320
        counts[name] = len(px)
        for data in zip(px*100, py*100, rng.uniform(0,360,len(px)),
                        rng.uniform(lo,hi,len(px)),rng.choice(slots,len(px))):
            records.extend(struct.pack("<ffffi", *data))

    plant("hornbeam",5.8,.96*smooth(.21,.84,grove),[0,1],.80,1.12,2.6)
    plant("hazel",8.5,.09+.52*grove,[2,3],140,275,2.)
    plant("stones",11.,.10+.17*ridge_mask+.05*grove,[4,5],18,47,.8)
    plant("deadwood",12.,.045+.21*grove,[6,7],42,91,1.)
    plant("herbs",4.5,.18+.26*(1-grove),[8,9],.60,.98,.7)
    plant("ground_decals",30.,.055+.11*grove,[10,11],.50,.96,2.)
    (directory / "planting.bin").write_bytes(records)
    outside = ~original
    stats = {"extent_m":[[-624,-320],[400,704]], "area_m2":1024**2,
             "new_ground_area_m2":1024**2-504**2-118*145,
             "source":"/Game/ForestPathStudy/Maps/L_ForestPathForest",
             "height_png_zero":32768, "height_cm_per_unit":1, "variant_spacing_m":2,
             "height_range_m":(np.array([height[outside].min(),height[outside].max()])/100.).round(2).tolist(),
             "outside_under_5deg_percent":round(100*float(np.mean(slope[outside]<np.tan(np.deg2rad(5)))),1),
             "instances":counts, "seed":237146}
    (directory / "generation.json").write_text(json.dumps(stats,indent=2),encoding="utf-8")


if __name__ == "__main__":
    generate(Path(sys.argv[1]))
