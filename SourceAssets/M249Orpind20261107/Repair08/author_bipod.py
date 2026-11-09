"""Articulate the existing factory legs without changing the approved folded assembly."""
from pathlib import Path
import bpy,json,numpy as np
from mathutils import Vector,Matrix
r=Path(__file__).resolve().parent;root=r.parent;out=r/'Exports';out.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(root/'M249_Editable.blend'),use_scripts=False)
bpy.context.preferences.filepaths.save_version=0
bind=json.loads((root/'MotionInput/rig.json').read_text())['bind']['WPN_root']
from mathutils import Quaternion
q=Quaternion((bind[6],*bind[3:6]));origin=Vector(bind[:3])
base=Matrix([[0,1,0,.0545],[-1,0,0,.286],[0,0,1,-.053],[0,0,0,1]])
def rootpoint(p):
    return q.inverted()@(Vector((p.x,-p.y,p.z))*100-origin)
def bpoint(p):return Vector((p.x,-p.y,p.z))*.01
def export(source,name,positions):
    obj=source.copy();obj.data=source.data.copy();bpy.context.scene.collection.objects.link(obj)
    obj.parent=None;obj.matrix_world=Matrix.Identity(4)
    for m in list(obj.modifiers):obj.modifiers.remove(m)
    # Apply rigid transforms to vertices and normals together; retain original UV/materials.
    src=np.array([v.co[:] for v in obj.data.vertices]);dst=np.array([p[:] for p in positions])
    a,b=src.mean(0),dst.mean(0);u,s,vt=np.linalg.svd((src-a).T@(dst-b));rotation=vt.T@u.T
    xf=Matrix.Identity(4)
    for i in range(3):
        for j in range(3):xf[i][j]=float(rotation[i,j])
    xf.translation=Vector(b-rotation@a);obj.data.transform(xf)
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    bpy.ops.export_scene.fbx(filepath=str(out/(name+'.fbx')),use_selection=True,axis_forward='-Y',axis_up='Z',bake_anim=False,
        object_types={'MESH'},mesh_smooth_type='FACE',path_mode='STRIP')
    return obj
mount=bpy.data.objects['M249_BipodMount']
export(mount,'SM_M249_Bipod_Base',[bpoint(rootpoint(v.co)) for v in mount.data.vertices])
records=[]
for i,key in enumerate(('LegLeft','LegRight')):
    raw=np.load(root/'Geometry'/(key+'.npz'))['positions']
    anchor=Vector(raw[raw[:,2]>raw[:,2].max()-.009].mean(0));foot=Vector(raw[raw[:,2]<raw[:,2].min()+.011].mean(0))
    source=(foot-anchor).normalized();fold=Vector((-1,.08 if key=='LegRight' else -.08,-.11)).normalized()
    pivot=rootpoint(base@anchor);tip=rootpoint(base@foot)-pivot
    folded=(q.inverted()@Vector(((base.to_3x3()@fold).x,-(base.to_3x3()@fold).y,(base.to_3x3()@fold).z))).normalized()*tip.length
    # Existing scene contains folded legs. The original source positions recover the opened pose.
    obj=bpy.data.objects['M249_'+key]
    export(obj,'SM_M249_Bipod_Leg'+('A' if i==0 else 'B'),[bpoint(rootpoint(base@Vector(p))-pivot) for p in raw])
    records.append(dict(pivot=list(pivot),tip=list(tip),folded_tip=list(folded)))
hinge=(Vector(records[0]['pivot'])+Vector(records[1]['pivot']))*.5
(r/'bipod_geometry.json').write_text(json.dumps(dict(hinge=list(hinge),legs=records,frame='WPN_root cm; .01 instance scale compensates native root x100'),indent=2))
def vec(v):return 'FVector('+','.join(f'{x:.9f}' for x in v)+')'
header='''#pragma once
#include "CoreMinimal.h"
// Measured from the current factory meshes. Closed legs fold toward the muzzle.
namespace M249Bipod
{
inline constexpr const TCHAR* Base=TEXT("/Game/Weapons/M249/Bipod/SM_M249_Bipod_Base");
inline constexpr const TCHAR* LegA=TEXT("/Game/Weapons/M249/Bipod/SM_M249_Bipod_LegA");
inline constexpr const TCHAR* LegB=TEXT("/Game/Weapons/M249/Bipod/SM_M249_Bipod_LegB");
'''
header+='inline const FVector Hinge='+vec(hinge)+';\n'
for name,key in [('Pivots','pivot'),('Tips','tip'),('FoldedTips','folded_tip')]:header+='inline const FVector '+name+'[]={'+','.join(vec(row[key]) for row in records)+'};\n'
header+='''inline FQuat LegRotation(int32 I,float OpenWeight)
{
    const FQuat Closed=FQuat::FindBetweenNormals(Tips[I].GetSafeNormal(),FoldedTips[I].GetSafeNormal());
    const float T=FMath::Clamp(OpenWeight,0.f,1.f);
    return FQuat::Slerp(Closed,FQuat::Identity,T*T*(3.f-2.f*T));
}
}
'''
(root.parents[1]/'Source/FPSGAME/Weapons/M249Bipod.h').write_text(header,encoding='utf8')
bpy.ops.wm.save_as_mainfile(filepath=str(r/'M249_ArticulatedBipod.blend'))
print('M249_BIPOD_AUTHORED',json.dumps(records),flush=True)
