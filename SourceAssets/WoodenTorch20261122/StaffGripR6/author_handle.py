"""Fit the Fab wood to the default staff's measured grip. Keep the head rigid for its wrapped flame."""
import json
import math
import os
from pathlib import Path

import bpy
import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree

root = Path(os.environ["FPS_PROJECT_ROOT"])
family = root / "SourceAssets/WoodenTorch20261122"
out = family / "StaffGripR6/Export"
base = family / "HearthHeadR3"
profile = json.loads((root / "SourceAssets/ApprenticeStaff20260927/ArmSupportV13/grip-surfaces.json").read_text())
radii = profile["variants"]["false"]["radii"]
old = json.loads((base / "Export/fit.json").read_text())
bpy.ops.wm.open_mainfile(filepath=str(base / "HandheldTorch_HearthHead.blend"))
torch = next(obj for obj in bpy.context.scene.objects if obj.type == "MESH")
mesh = torch.data
wood = next(i for i,m in enumerate(mesh.materials) if m.name == "Wood")
bm = bmesh.new()
bm.from_mesh(mesh)
for cm in (-17, -11, -7, -5, -3, 0, 3, 5, 7, 11, 15, 19):
    bmesh.ops.bisect_plane(bm, geom=list(bm.verts)+list(bm.edges)+list(bm.faces),
                          plane_co=(0, 0, cm/100), plane_no=(0, 0, 1), dist=1e-7)
bm.to_mesh(mesh)
bm.free()

def eased(t):
    t = max(0., min(1., t))
    return t*t*(3.-2.*t)

def radius(z, angle):
    zi = min(len(radii)-1.001, max(0., (32.+z-profile["z"][0])/(profile["z"][1]-profile["z"][0])))
    ai = angle % math.tau / math.tau * profile["angle_count"]
    az = int(ai) % profile["angle_count"]
    nxt = (az+1) % profile["angle_count"]
    i, u, f = int(zi), zi-int(zi), ai-int(ai)
    return ((1.-f)*radii[i][az]+f*radii[i][nxt])*(1.-u) + ((1.-f)*radii[i+1][az]+f*radii[i+1][nxt])*u

wood_verts = {i for p in mesh.polygons if p.material_index==wood for i in p.vertices}
for vertex in mesh.vertices:
    x, y, z = (100*c for c in vertex.co)
    if vertex.index in wood_verts and z < 19. and math.hypot(x,y) > .9:
        angle = math.atan2(y,x)
        # Match the measured envelope under the whole palm and feather it into the Fab neck and butt.
        target = radius(z,angle) * (1.-.28*eased((-7.-z)/19.))
        influence = 1.-eased((z-7.)/12.)
        factor = 1.+influence*(target/math.hypot(x,y)-1.)
        x, y = x*factor, y*factor
    z -= 4.*eased((z-7.)/12.)
    if z < -7.:
        z = -7.+(z+7.)*.56
    vertex.co = Vector((x/100,y/100,z/100))
mesh.update()
torch.name = mesh.name = "SM_HandheldStaffGrip"
flame = list(old["flame_socket_ue_cm"])
flame[2] -= 4.
# Measure the finished polygons through the palm band in the donor shaft frame.
mesh.calc_loop_triangles()
tree = BVHTree.FromPolygons([v.co*100 for v in mesh.vertices],
                            [list(t.vertices) for t in mesh.loop_triangles if t.material_index==wood])
errors=[]; widths={}
for z in (-5,-3,0,3,5):
    ring=[]
    for i in range(128):
        a=math.tau*i/128
        direction=Vector((math.cos(a),math.sin(a),0))
        hit=tree.ray_cast(Vector((0,0,z))+direction*12,-direction,12)[0]
        if hit is None: raise ValueError("Open handle at grip")
        r=math.hypot(hit.x,hit.y)
        errors.append(abs(r-radius(z,a)));ring.append(r)
    widths[str(z)]=[round(ring[0]+ring[64],3),round(ring[32]+ring[96],3)]
zs=[v.co.z*100 for v in mesh.vertices]
fit={"length_cm":max(zs)-min(zs),"butt_below_grip_cm":-min(zs),"grip_width_depth_cm":widths,
     "max_radial_difference_cm":max(errors),"mean_radial_difference_cm":sum(errors)/len(errors),
     "flame_socket_ue_cm":flame,"head_translation_cm":-4}
(out/"fit.json").write_text(json.dumps(fit,indent=2),encoding="utf8")
bpy.ops.object.select_all(action="DESELECT")
torch.select_set(True)
bpy.context.view_layer.objects.active=torch
bpy.ops.export_scene.fbx(filepath=str(out/"SM_HandheldStaffGrip.fbx"),use_selection=True,object_types={"MESH"},
                         apply_unit_scale=True,bake_anim=False,axis_forward="-Y",axis_up="Z",
                         mesh_smooth_type="FACE",use_triangles=True,path_mode="STRIP")
bpy.ops.wm.save_as_mainfile(filepath=str(out.parent/"HandheldTorch_StaffGrip.blend"))
print("STAFF_GRIP_FIT",fit)
