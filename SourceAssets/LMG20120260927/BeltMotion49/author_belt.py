"""Isolate the current incoming belt into closed, rigid indexing cells.
Keep six reload contact bones. The seventh cell recycles inside the pouch.
"""
import bpy,bmesh,json,gzip,hashlib
from pathlib import Path
from mathutils import Matrix,Quaternion,Vector
O=Path(__file__).parent;D=O.parent/'Drum46';P=O.parents[2];S=json.loads((D/'sources.json').read_text());bpy.context.preferences.filepaths.save_version=0
bodyfile=P/'Content/Weapons/LMG201/Cover10/SK_LMG201_Cover10.uasset'
if hashlib.sha256(bodyfile.read_bytes()).hexdigest()!=S['rigs']['201']['sha256']:raise RuntimeError('Current body changed; refresh source export')
with gzip.open(S['clips']['201_base_idle']['file'],'rt') as f:idle=json.load(f)[0]
def ue(v):return Matrix.LocRotScale(Vector(v['p']),Quaternion((v['q'][3],*v['q'][:3])),Vector(v['s']))
def convert(m):
 p,q,s=m.decompose();return Matrix.LocRotScale(Vector((p.x,-p.y,p.z))*.01,Quaternion((q.w,-q.x,q.y,-q.z)),s*.01)
def flip(v):return [v.x,-v.y,v.z]
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(D/'Inputs/Current201.fbx'),use_anim=False)
rig=next(a for a in bpy.data.objects if a.type=='ARMATURE');body=next(a for a in bpy.data.objects if a.type=='MESH' and len(a.data.materials)==len(S['rigs']['201']['slots']))
rest={b.name:rig.matrix_world@b.matrix_local for b in rig.data.bones};root=rest['WPN_root'];ir=convert(ue(idle['WPN_root']['world']))
indices=[i for i,s in enumerate(S['rigs']['201']['slots']) if s['name'].startswith('M_LMG201_Cloth33__OldBelt')]
origmats=[body.data.materials[i] for i in indices];slotnames=[S['rigs']['201']['slots'][i]['name'] for i in indices]
inside=next(i for i,s in enumerate(slotnames) if 'Interior' in s)
bm=bmesh.new();bm.from_mesh(body.data);bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.material_index not in indices],context='FACES');bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS')
xf=root.inverted()@body.matrix_world
for v in bm.verts:v.co=xf@v.co
for f in bm.faces:f.material_index=indices.index(f.material_index)
zlo=min(v.co.z for v in bm.verts);zhi=max(v.co.z for v in bm.verts);pitch=(zhi-zlo)/6
template=bpy.data.meshes.new('CurrentClothBelt49');bm.to_mesh(template);bm.free();parts=[];centers=[];newcenters=[];rootcenters=[];locals_=[]
materials=[]
for m,name in zip(origmats,slotnames):copy=m.copy();copy.name=name+'49';materials.append(copy)
for i in range(6):
 me=template.copy();cut=bmesh.new();cut.from_mesh(me)
 for z,no in [(zhi-i*pitch,(0,0,-1)),(zhi-(i+1)*pitch,(0,0,1))]:
  bmesh.ops.bisect_plane(cut,geom=list(cut.verts)+list(cut.edges)+list(cut.faces),dist=1e-8,plane_co=(0,0,z),plane_no=no,clear_inner=True,clear_outer=False)
  edges=[e for e in cut.edges if e.is_boundary and all(abs(v.co.z-z)<1e-6 for v in e.verts)]
  if edges:
   for f in bmesh.ops.holes_fill(cut,edges=edges,sides=0)['faces']:f.material_index=inside
 bmesh.ops.delete(cut,geom=[v for v in cut.verts if not v.link_faces],context='VERTS');bmesh.ops.recalc_face_normals(cut,faces=list(cut.faces));cut.to_mesh(me);cut.free();me.transform(root)
 part=bpy.data.objects.new('201_IndexedBelt_%02d'%i,me);bpy.context.collection.objects.link(part);parts.append(part)
 # Cells keep their source surface coordinates and the same six reload bones.
 bone='LMG201_Belt_%02d'%i;c=sum((v.co for v in me.vertices),Vector())/len(me.vertices);lc=rest[bone].inverted()@c
 centers.append(flip(lc));newcenters.append(flip(rest['New_'+bone].inverted()@c));posed=convert(ue(idle[bone]['world']))@lc;rootcenters.append(flip(ir.inverted()@posed));locals_.append(idle[bone]['local'])
 # Parent space is held fixed while the armature modifier uses the imported rig.
 part.parent=rig;part.matrix_parent_inverse=rig.matrix_world.inverted();part.matrix_basis=Matrix.Identity(4);part.vertex_groups.new(name=bone).add(list(range(len(me.vertices))),1.,'REPLACE');part.modifiers.new('Native belt cell','ARMATURE').object=rig
 me.materials.clear()
 for m in materials:me.materials.append(m)
bottom=parts[-1];me=bottom.data.copy();bone='LMG201_Belt_06';pose6=convert(ue(idle[bone]['world']));pose5=convert(ue(idle['LMG201_Belt_05']['world']));shift=Vector(rootcenters[5])-Vector(rootcenters[4]);shift=Vector((shift.x,-shift.y,shift.z));worldshift=ir.to_3x3()@shift
offset=Matrix.Translation(worldshift);me.transform(rest[bone]@pose6.inverted()@offset@pose5@rest['LMG201_Belt_05'].inverted())
extra=bpy.data.objects.new('201_IndexedBelt_06_HiddenReturn',me);bpy.context.collection.objects.link(extra);extra.parent=rig;extra.matrix_parent_inverse=rig.matrix_world.inverted();extra.matrix_basis=Matrix.Identity(4);extra.vertex_groups.new(name=bone).add(list(range(len(me.vertices))),1.,'REPLACE');extra.modifiers.new('Native hidden belt cell','ARMATURE').object=rig;parts.append(extra)
c=sum((v.co for v in me.vertices),Vector())/len(me.vertices);lc=rest[bone].inverted()@c;centers.append(flip(lc));rootcenters.append(flip(ir.inverted()@(pose6@lc)));locals_.append(idle[bone]['local'])
# Endpoints are art-space contacts. A short inboard continuation enters the
# closed receiver; the last point lies one cell below the pouch mouth.
entry=list(rootcenters[0]);entry[0]-=.024
guide=[entry]+rootcenters
for a in list(bpy.data.objects):
 if a!=rig and a not in parts:bpy.data.objects.remove(a,do_unlink=True)
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True)
for a in parts:a.select_set(True)
bpy.context.view_layer.objects.active=rig
(O/'Exports').mkdir(exist_ok=True);fbx=O/'Exports/SK_LMG201_Belt49.fbx'
bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH','ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE')
bpy.ops.wm.save_as_mainfile(filepath=str(O/'LMG201_BeltMotion49.blend'))
report={'fbx':str(fbx),'source_body_sha256':S['rigs']['201']['sha256'],'source_idle':S['clips']['201_base_idle'],'old_slots':slotnames,'slots':[m.name for m in materials],'centers_bone_local':centers,'new_centers_bone_local':newcenters,'guide_root':guide,'idle_bone_local':locals_,'pitch_bind_m':pitch,'runtime_tested':False}
(O/'layout.json').write_text(json.dumps(report,indent=2))
def vec(v):return 'FVector('+','.join('%.10g'%x for x in v)+')'
lines=['#pragma once','#include "CoreMinimal.h"','// Generated from the current 201 mesh/idle by BeltMotion49/author_belt.py.','namespace LMG201BeltLayout','{','inline const FVector Centers[] = {'+','.join(map(vec,centers))+'};','inline const FVector NewCenters[] = {'+','.join(map(vec,newcenters))+'};','inline const FVector Guide[] = {'+','.join(map(vec,guide))+'};','inline const FTransform Idle[] = {']
for t in locals_:lines.append('FTransform(FQuat('+','.join('%.10g'%x for x in t['q'])+'),'+vec(t['p'])+','+vec(t['s'])+'),')
lines.extend(['};','}']);(P/'Source/FPSGAME/Weapons/LMG201BeltLayout.h').write_text('\n'.join(lines)+'\n');print('BELT49_SOURCE_SAVED',pitch,rootcenters,flush=True)
