"""Read a 20 cm voxel building save (VBX snapshot) and print what was actually built.

Usage:
    python Tools/Building/read_voxel_save.py [Saved/SaveGames/Voxel20_XXXX.sav]

The format is the custom snapshot written by VoxelPersistence.cpp: magic VBX3, then
Version / CellSizeCm / WorldKey / Cells / FreeVolumes / Damage / BrokenBonds / Fragments /
LegacyProtected / Prefabs(v4) / Smelting(v5 wall-clock, v6 fuel model + Fuel(v6)).
Used for diagnosing placement, collapse reports and in-furnace smelting jobs.
"""

import glob
import os
import struct
import sys

MAGIC = 0x33584256


class Reader:
    def __init__(self, data):
        self.data = data
        self.off = 0

    def i32(self):
        value = struct.unpack_from("<i", self.data, self.off)[0]
        self.off += 4
        return value

    def i64(self):
        value = struct.unpack_from("<q", self.data, self.off)[0]
        self.off += 8
        return value

    def f64(self):
        value = struct.unpack_from("<d", self.data, self.off)[0]
        self.off += 8
        return value

    def vec3(self):
        value = struct.unpack_from("<3d", self.data, self.off)
        self.off += 24
        return value

    def quat(self):
        value = struct.unpack_from("<4d", self.data, self.off)
        self.off += 32
        return value

    def guid(self):
        value = self.data[self.off:self.off + 16]
        self.off += 16
        return value.hex()

    def string(self):
        count = self.i32()
        if count == 0:
            return ""
        if count < 0:
            count = -count
            text = self.data[self.off:self.off + count * 2].decode("utf-16-le")
            self.off += count * 2
            return text
        text = self.data[self.off:self.off + count].decode("latin-1")
        self.off += count
        return text

    def int_vector(self):
        value = struct.unpack_from("<3i", self.data, self.off)
        self.off += 12
        return value

    def key(self):
        return (self.guid(), self.int_vector())


def main():
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    pattern = sys.argv[1] if len(sys.argv) > 1 else os.path.join(root, "Saved", "SaveGames", "Voxel20_*.sav")
    paths = glob.glob(pattern)
    paths = [p for p in paths if not p.endswith((".pre-structure", ".pending"))]
    if not paths:
        print("no voxel save found for %s" % pattern)
        return 1
    path = max(paths, key=os.path.getmtime)
    raw = open(path, "rb").read()
    magic, size, crc = struct.unpack_from("<III", raw, 0)
    print("file      : %s (%d bytes, mtime %s)" % (path, len(raw), __import__("time").ctime(os.path.getmtime(path))))
    print("magic     : 0x%08X  payload=%d bytes" % (magic, size))
    if magic != MAGIC:
        print("not a VBX snapshot")
        return 1

    reader = Reader(raw[12:12 + size])
    version = reader.i32()
    cell_size = reader.i32()
    world_key = reader.string()
    print("version   : %d  cell=%d cm  world=%s" % (version, cell_size, world_key))

    count = reader.i32()
    cells = []
    for _ in range(count):
        position = reader.int_vector()
        material = reader.string()
        cells.append((position, material))
    print("cells     : %d" % len(cells))
    if cells:
        xs = [c[0][0] for c in cells]; ys = [c[0][1] for c in cells]; zs = [c[0][2] for c in cells]
        print("  x %d..%d  y %d..%d  z %d..%d  (height %.2f m, footprint %d x %d cells)" % (
            min(xs), max(xs), min(ys), max(ys), min(zs), max(zs),
            (max(zs) - min(zs) + 1) * 0.2, max(xs) - min(xs) + 1, max(ys) - min(ys) + 1))
        per_material = {}
        per_layer = {}
        for position, material in cells:
            per_material[material] = per_material.get(material, 0) + 1
            per_layer[position[2]] = per_layer.get(position[2], 0) + 1
        print("  materials: %s" % ", ".join("%s=%d" % kv for kv in sorted(per_material.items())))
        print("  top layers by z: %s" % ", ".join("z=%d:%d" % kv for kv in sorted(per_layer.items())[-8:]))
        print("  bottom layers by z: %s" % ", ".join("z=%d:%d" % kv for kv in sorted(per_layer.items())[:4]))

    volumes = reader.i32()
    for _ in range(volumes):
        reader.guid(); reader.vec3()
        inner = reader.i32()
        for _ in range(inner):
            reader.int_vector(); reader.string()
    print("free vols : %d" % volumes)

    damage = reader.i32()
    for _ in range(damage):
        reader.key(); reader.off += 4
    print("damage    : %d entries" % damage)

    bonds = reader.i32()
    for _ in range(bonds):
        reader.key(); reader.key()
    print("broken    : %d bonds" % bonds)

    fragments = reader.i32()
    fragment_cells = 0
    for _ in range(fragments):
        reader.guid(); reader.quat(); reader.vec3(); reader.vec3()
        inner = reader.i32()
        for _ in range(inner):
            reader.key(); reader.vec3(); reader.string(); reader.off += 4
        bonds_inner = reader.i32()
        for _ in range(bonds_inner):
            reader.key(); reader.key()
        reader.vec3(); reader.vec3(); reader.off += 1
        fragment_cells += inner
    print("fragments : %d actors, %d debris cells" % (fragments, fragment_cells))

    legacy = reader.i32()
    for _ in range(legacy):
        reader.key()
    print("legacy    : %d protected cells" % legacy)

    if version >= 4:
        prefabs = reader.i32()
        furnace_cells = []
        for _ in range(prefabs):
            pid = reader.string(); cell = reader.int_vector(); reader.off += 4; reader.int_vector()
            if pid == "blast_furnace":
                furnace_cells.append(cell)
        print("prefabs   : %d placed pieces (blast furnaces at %s)" % (
            prefabs, ", ".join(str(c) for c in furnace_cells) if furnace_cells else "-"))

    if version == 5:
        jobs = reader.i32()
        for _ in range(jobs):
            cell = reader.int_vector(); recipe = reader.string(); start = reader.i64()
            print("  legacy v5 job @%s recipe=%s start_ticks=%d (%.3f)" % (
                cell, recipe, start, start / 1e7))
        print("smelting  : %d legacy wall-clock job(s)" % jobs)
    elif version >= 6:
        jobs = reader.i32()
        for _ in range(jobs):
            cell = reader.int_vector(); recipe = reader.string()
            progress = reader.f64(); burn = reader.i64()
            print("  smelting job @%s recipe=%s progress=%.3fs burn_start=%d%s" % (
                cell, recipe, progress, burn, "" if burn else " (stalled)"))
        fuels = reader.i32()
        for _ in range(fuels):
            cell = reader.int_vector(); seconds = reader.f64()
            print("  furnace fuel @%s %.1f s" % (cell, seconds))
        print("smelting  : %d job(s), %d furnace(s) with stored fuel" % (jobs, fuels))

    print("leftover  : %d bytes unread" % (len(reader.data) - reader.off))
    return 0


if __name__ == "__main__":
    sys.exit(main())
