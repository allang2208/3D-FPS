"""Headless probe: what does Rotator(...) + Transform + append_mesh_at_transforms really do?

Places one box at the north pole, then rotates it into place with the call the dome build
uses, and prints the bounds so the rotation convention can be read off directly.
"""

import unreal

SV = unreal.ModelingService


def tf(x=0.0, y=0.0, z=0.0, pitch=0.0, yaw=0.0, roll=0.0):
    t = unreal.Transform()
    t.translation = unreal.Vector(x, y, z)
    t.rotation = unreal.Rotator(pitch, yaw, roll).quaternion()
    t.scale3d = unreal.Vector(1.0, 1.0, 1.0)
    return t


def show(label, handle):
    i = SV.get_mesh_info(handle)
    print("[rot] %-34s z %.1f .. %.1f   x %.1f .. %.1f   y %.1f .. %.1f" % (
        label, i.bounds_min.z, i.bounds_max.z, i.bounds_min.x, i.bounds_max.x,
        i.bounds_min.y, i.bounds_max.y))


r = unreal.Rotator(10.0, 20.0, 30.0)
print("[rot] Rotator(10, 20, 30) -> pitch=%.1f yaw=%.1f roll=%.1f" % (r.pitch, r.yaw, r.roll))
print("[rot]   up=(%.2f, %.2f, %.2f) forward=(%.2f, %.2f, %.2f)" % (
    r.get_up_vector().x, r.get_up_vector().y, r.get_up_vector().z,
    r.get_forward_vector().x, r.get_forward_vector().y, r.get_forward_vector().z))

src = SV.create_mesh().handle
SV.append_box(src, tf(0.0, 0.0, 360.0), 10.0, 10.0, 10.0, 0, 0, 0, "Center", 0)
show("source box (north pole, r=360)", src)

# pitch = -60 should swing it down to alpha=60 (z=180, x=312); yaw 45 then spins it round Z
for label, args in (("pitch=-60 yaw=45", (0.0, 0.0, 0.0, -60.0, 45.0, 0.0)),
                    ("pitch=-60 yaw=0", (0.0, 0.0, 0.0, -60.0, 0.0, 0.0)),
                    ("pitch=0 yaw=45", (0.0, 0.0, 0.0, 0.0, 45.0, 0.0)),
                    ("pitch=60 yaw=45", (0.0, 0.0, 0.0, 60.0, 45.0, 0.0))):
    m = SV.create_mesh().handle
    SV.append_mesh_at_transforms(m, src, [tf(*args)])
    show(label, m)
    SV.release_mesh(m)

SV.release_mesh(src)
print("[rot] RESULT: DONE")
