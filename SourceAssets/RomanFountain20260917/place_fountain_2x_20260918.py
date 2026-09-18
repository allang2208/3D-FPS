"""Move the 2x fountain clear of the pavilion (its 960 foot overlapped RomanPavilion2_Base by
210 cm at the old 1x spot) and put the Niagara jet back on the pigna tip (it was found at
world z=370, buried in the tower). New site: (1350,-1550) - due south of the pavilion, south
edge 190 cm clear of the stylobate. Everything attached KEEP_WORLD then re-attached."""

import os
import time

import unreal

LEVEL = "/Game/GameMaps/DayNight_Lighting"
NEW = unreal.Vector(1350.0, -1550.0, -360.0)
TIP = unreal.Vector(1350.0, -1550.0, 720.0)
STARTED = time.time()
LOG = []


def log(m):
    print("[mv] " + m)


def check(label, ok):
    LOG.append((label, bool(ok)))
    log("%-26s %s" % (label, "OK" if ok else "FAIL"))


les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if not les.load_level(LEVEL):
    log("load FAILED")
    raise SystemExit(0)
actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
actors = actor_sub.get_all_level_actors()

fountains = [a for a in actors if a.get_actor_label() == "RomanFountain1"]
jets = [a for a in actors if a.get_actor_label() == "RomanFountainFX_Jet"]
check("fountain_found", len(fountains) == 1)
check("jet_found", len(jets) == 1)

# clash proof at the new site before moving anything
o, e = fountains[0].get_actor_bounds(False)
half_x, half_y = e.x, e.y
span = (NEW.x - half_x, NEW.x + half_x, NEW.y - half_y, NEW.y + half_y, 0.0, 720.0)
clash = None
for a in actors:
    if a in (fountains[0], jets[0]) if isinstance(a, unreal.Actor) else False:
        continue
    ao, ae = a.get_actor_bounds(False)
    b = (ao.x - ae.x, ao.x + ae.x, ao.y - ae.y, ao.y + ae.y, ao.z - ae.z, ao.z + ae.z)
    if (b[0] < span[1] and b[1] > span[0] and b[2] < span[3] and b[3] > span[2] and
            b[4] < span[5] and b[5] > span[4]):
        clash = a.get_actor_label() or a.get_name()
        break
check("new_site_clear", clash is None)
log("clash probe: %s" % (clash or "none"))

f = fountains[0]
f.set_actor_location(NEW, False, True)
loc = f.get_actor_location()
check("fountain_moved", abs(loc.x - 1350.0) < 1.0 and abs(loc.y + 1550.0) < 1.0 and abs(loc.z + 360.0) < 1.0)

if jets:
    j = jets[0]
    j.set_actor_location(TIP, False, True)
    j.attach_to_actor(f, unreal.Name(""), unreal.AttachmentRule.KEEP_WORLD,
                      unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, False)
    jl = j.get_actor_location()
    pa = j.get_attach_parent_actor()
    check("jet_on_tip", abs(jl.z - 720.0) < 1.0 and pa is not None and
          pa.get_actor_label() == "RomanFountain1")
    log("jet now at (%.0f,%.0f,%.0f)" % (jl.x, jl.y, jl.z))

saved = les.save_current_level()
umap = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir()) + \
    "GameMaps/DayNight_Lighting.umap"
st1 = os.stat(umap).st_mtime if os.path.exists(umap) else 0
check("umap_saved", bool(saved) and st1 >= STARTED - 5.0)

bad = [x for x in LOG if x[1] is False]
log("checks=%d failed=%d %s" % (len(LOG), len(bad), [b[0] for b in bad]))
log("RESULT: " + ("PASS" if not bad else "CHECK"))
