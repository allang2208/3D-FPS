"""Fit the retained green cords to the wooden contact surface; preserve UVs."""
import bpy, bmesh, json, math
import numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

P=Path(__file__).parent
OUT=P/'Export';OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'BowModular20260926/Bow_ModularParts.blend'))
bpy.context.preferences.filepaths.save_version=0
body=bpy.data.objects['SM_Bow_BodyModular']
grip=bpy.data.objects['SM_Bow_GripWrap']
for obj in list(bpy.data.objects):
    if obj not in (body,grip):bpy.data.objects.remove(obj,do_unlink=True)
grip.name='SM_Bow_GripWrap_Fitted'
grip.data=grip.data.copy()
verts=[v.co.copy() for v in grip.data.vertices]
wood=[v.co.copy() for v in body.data.vertices]
tree=BVHTree.FromPolygons(wood,[list(p.vertices) for p in body.data.polygons])
zmin=min(v.z for v in verts);zmax=max(v.z for v in verts)
NA,NZ=192,256
gap=.04  # 0.4 mm seating clearance, in centimetres.
field=np.zeros((NZ,NA),dtype=float)
samples=[]
for p in verts:
    center=Vector((-.7,0,p.z));radial=p-center;r=radial.length;radial.normalize()
    hit,_,_,_=tree.ray_cast(center+radial*12,-radial,24)
    if hit is None:raise RuntimeError('Missing wooden contact surface at '+str(tuple(p)))
    needed=max(0.,(hit-center).dot(radial)+gap-r)
    az=(math.atan2(radial.y,radial.x)/math.tau%1)*NA
    zz=(p.z-zmin)/(zmax-zmin)*(NZ-1)
    ia=int(az)%NA;iz=min(NZ-2,int(zz))
    # Store on the surrounding grid corners before extending the correction
    # over the cord thickness. This moves a local strand, not only its inner face.
    for k in (iz,iz+1):
        for j in (ia,(ia+1)%NA):field[k,j]=max(field[k,j],needed)
    samples.append((radial,needed,az,zz))
for _ in range(3):
    pad=np.pad(field,((1,1),(0,0)),mode='edge')
    field=np.maximum.reduce([pad[:-2],pad[1:-1],pad[2:],np.roll(field,1,1),np.roll(field,-1,1)])
for _ in range(3):
    pad=np.pad(field,((1,1),(0,0)),mode='edge')
    field=(pad[:-2]+2*pad[1:-1]+pad[2:])/4
    field=(np.roll(field,1,1)+2*field+np.roll(field,-1,1))/4
moved=0;maximum=0.
for v,p,(direction,needed,az,zz) in zip(grip.data.vertices,verts,samples):
    j=int(az)%NA;k=min(NZ-2,int(zz));ta=az-int(az);tz=zz-k
    shift=(field[k,j]*(1-ta)+field[k,(j+1)%NA]*ta)*(1-tz)+(field[k+1,j]*(1-ta)+field[k+1,(j+1)%NA]*ta)*tz
    shift=max(float(shift),needed)
    v.co=p+direction*shift
    moved+=int(shift>.001);maximum=max(maximum,shift)
bpy.ops.object.select_all(action='DESELECT');grip.select_set(True);bpy.context.view_layer.objects.active=grip
if grip.data.has_custom_normals:bpy.ops.mesh.customdata_custom_splitnormals_clear()
bm=bmesh.new();bm.from_mesh(grip.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(grip.data);bm.free()
grip.data.update()
bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=.01
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Bow_GripContact.blend'))
bpy.ops.export_scene.fbx(filepath=str(OUT/(grip.name+'.fbx')),use_selection=True,object_types={'MESH'},
    axis_forward='-Y',axis_up='Z',apply_unit_scale=True,bake_anim=False,use_tspace=True)
result={'asset':grip.name,'source':'BowModular20260926/Bow_ModularParts.blend','clearance_cm':gap,
    'moved_vertices':moved,'maximum_local_shift_cm':maximum,'vertices':len(grip.data.vertices),
    'triangles':sum(len(p.vertices)-2 for p in grip.data.polygons),'uv_and_material_retained':True,'gameplay_tested':False}
(P/'authoring.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print('BOW_GRIP_CONTACT_AUTHORED',json.dumps(result))
