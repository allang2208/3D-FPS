# 只读核对：刚从 Door System 包迁移进来的门蓝图（父类、编译状态、组件网格、接口、可调用入口）。

import unreal

BASE = "/Game/DoorSystem/Blueprints/Doors/"
DOORS = ["BP_AutoDoor", "BP_DragDoor", "BP_KeyDoor", "BP_KeyDoorAutoClose", "BP_PhysicsDoor",
         "BP_PhysicsDoubleDoor", "BP_RotatingDoor", "BP_RotatingDoors", "BP_RotatingPhysicsDoors",
         "BP_SlidingDoors", "BP_WrongSideDoor"]
KEYWORDS = ("door", "interact", "open", "close", "toggle", "has_key", "stop", "auto", "slide", "rotate")
COMPONENTS = ("door", "frame", "box", "cube", "mesh", "root", "collision")


def log(message):
    # commandlet 里 print 不会进日志，用 unreal.log 才能读回结果。
    unreal.log("[door-audit] " + message)


unreal.AssetRegistryHelpers.get_asset_registry().scan_paths_synchronous(["/Game/DoorSystem"], True)

for name in DOORS:
    path = BASE + name
    bp = unreal.load_asset(path)
    cls = unreal.load_class(None, path + "." + name + "_C")
    log("%-24s bp=%s class=%s" % (name, bp is not None, cls is not None))
    if bp is None or cls is None:
        continue
    try:
        parent = bp.get_editor_property("parent_class")
        log("   parent=%s status=%s" % (parent.get_name() if parent else None, bp.get_editor_property("status")))
    except Exception as exc:
        log("   parent/status failed: %s" % exc)
    try:
        cdo = unreal.get_default_object(cls)
    except Exception as exc:
        log("   cdo failed: %s" % exc)
        continue
    for member in dir(cdo):
        low = member.lower()
        if not any(hint in low for hint in COMPONENTS):
            continue
        try:
            value = getattr(cdo, member)
        except Exception:
            continue
        if isinstance(value, unreal.StaticMeshComponent):
            mesh = value.static_mesh
            log("   comp %-14s %-24s mesh=%s" % (member, value.get_class().get_name(), mesh.get_name() if mesh else "None"))
        elif isinstance(value, unreal.ShapeComponent):
            log("   comp %-14s %s" % (member, value.get_class().get_name()))
    entries = [m for m in dir(cls) if any(k in m.lower() for k in KEYWORDS) and not m.startswith("_")]
    log("   entries: " + ", ".join(sorted(entries)[:22]))

for iface in ("BI_Interact", "BPI_Interact", "BI_GrabObjects", "BPI_GrabObjects"):
    cls = unreal.load_class(None, "/Game/DoorSystem/Player/Blueprints/" + iface + "." + iface + "_C")
    log("interface %-16s class=%s members=%s" % (
        iface, cls is not None, ", ".join(sorted(m for m in dir(cls) if not m.startswith("_"))[:16]) if cls else "-"))

log("done")
