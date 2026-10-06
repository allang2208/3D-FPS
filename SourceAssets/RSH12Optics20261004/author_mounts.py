"""Narrow RSH rail saddles, retaining full-size common optical assemblies."""
import bpy,bmesh,json,math,numpy as np
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;P=O.parents[1];OUT=O/'Exports';OUT.mkdir(exist_ok=True)
bpy.context.preferences.filepaths.save_version=0
interfaces=json.loads((O/'interfaces.json').read_text())
align=np.array(json.loads((O.parent/'RSH12Speedloader20261003/Single/authoring.json').read_text())['alignment'])
center=np.array([0.,-.063721,.079125,1.]);reflect=np.diag([1.,-1.,1.,1.])
root_point=(reflect@align@center)[:3]
root_forward=(reflect@align@np.array([0.,-1.,0.,0.]))[:3]
root_up=(reflect@align@np.array([0.,0.,1.,0.]))[:3]
# Optical bodies keep their original canonical seat at z=0. The new upper
# crown is 6.5 mm above the measured RSH crown, with jaws below and clear slots.
specs={'holographic':(.078,.02260),'panoramic_red_dot':(.060,0.),
       'prism_scope_2x':(.059,0.),'lpvo_1_6x':(.080,.014),'eoth_holographic':(.078,-.026)}
record=dict(rail_part='2_l',rail_center_canonical_m=center[:3].tolist(),rail_top_m=.079125,
            rail_shoulder_width_m=.016536,root_point_m=root_point.tolist(),
            root_forward=root_forward.tolist(),root_up=root_up.tolist(),parts={})

def finish(ob):
    bpy.context.view_layer.objects.active=ob;ob.select_set(True)
    bevel=ob.modifiers.new('Machined edge breaks','BEVEL');bevel.width=.00018;bevel.segments=2
    bpy.ops.object.modifier_apply(modifier=bevel.name)
    for poly in ob.data.polygons:poly.use_smooth=False
    uv=ob.data.uv_layers.new(name='UV0')
    for poly in ob.data.polygons:
        axes=[i for i in range(3) if i!=max(range(3),key=lambda j:abs(poly.normal[j]))]
        for li in poly.loop_indices:
            p=ob.data.vertices[ob.data.loops[li].vertex_index].co;uv.data[li].uv=(p[axes[0]]/.04+.5,p[axes[1]]/.04+.5)
    ob.data.materials.append(bpy.data.materials.get('RSH_OpticMountSteel') or bpy.data.materials.new('RSH_OpticMountSteel'))
    ob.select_set(False);return ob

def extrude(name,x0,x1,section):
    points=[(x,y,z) for x in (x0,x1) for y,z in section];n=len(section)
    faces=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    me=bpy.data.meshes.new(name);me.from_pydata(points,[],faces);me.update()
    bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
    ob=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(ob);return finish(ob)

def box(name,location,size):
    bpy.ops.mesh.primitive_cube_add(size=1,location=location);ob=bpy.context.object;ob.name=name;ob.scale=size
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True);return finish(ob)

for key,(length,offset) in specs.items():
    bpy.ops.wm.read_factory_settings(use_empty=True);parts=[]
    parts.append(extrude('Central sloped web',-length/2,length/2,[(-.0067,.00005),(.0067,.00005),(.0074,.0038),(-.0074,.0038)]))
    # Separate teeth leave transverse locking slots; a thin continuous web joins them.
    for x in np.arange(-length/2+.003,length/2,.01):
        x0=max(-length/2,x-.00295);x1=min(length/2,x+.00295)
        parts.append(extrude('Upper rail tooth',x0,x1,[(-.0067,.0020),(.0067,.0020),(.0114,.0040),(.0104,.0065),(-.0104,.0065),(-.0114,.0040)]))
    # Two small clamp blocks bear on the rail shoulders rather than the gun bbox.
    profile=[(.0056,.00005),(.0084,-.00195),(.00715,-.00425),(.0105,-.00425),(.0110,.0018),(.0080,.0030)]
    for x in (-.0184012,.0184012):
        for sign in (-1,1):
            parts.append(extrude('Split saddle jaw',x-.006,x+.006,[(sign*y,z) for y,z in profile]))
            bpy.ops.mesh.primitive_cylinder_add(vertices=12,radius=.0023,depth=.0016,location=(x,sign*.0112,-.0006),rotation=(math.pi/2,0,0))
            ob=bpy.context.object;ob.name='Clamp screw head';bpy.ops.object.transform_apply(location=True,rotation=True,scale=True);parts.append(finish(ob))
        parts.append(box('Recoil lug',(x,0,-.00205),(.00415,.0135,.0042)))
    bpy.ops.object.select_all(action='DESELECT')
    for ob in parts:ob.select_set(True)
    bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join();ob=bpy.context.object;ob.name='SM_RSH12_Rail_'+key
    tri=ob.modifiers.new('Export tangent triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=tri.name)
    fb=OUT/(ob.name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(fb),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,use_tspace=True,mesh_smooth_type='FACE')
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/(ob.name+'_Editable.blend')))
    record['parts'][key]=dict(name=ob.name,fbx=str(fb),body_offset_cm=[offset*100,0,.65],rail_length_m=length)
    print('RSH_OPTIC_SADDLE_AUTHORED',key,flush=True)
(O/'mounts.json').write_text(json.dumps(record,indent=2))

def vec(v):return 'FVector('+','.join(f'{float(x):.10f}f' for x in v)+')'
lines=['#pragma once','#include "CoreMinimal.h"','','// Generated by RSH12Optics20261004/author_mounts.py from the measured rail.',
       'namespace RSH12OpticAssets','{',
       'inline constexpr const TCHAR* Square = TEXT("rsh12_square_sight");',
       'inline constexpr const TCHAR* TacticalSquare = TEXT("rsh12_tactical_square_sight");',
       'inline bool IsSquare(const FString& Variant) { return Variant==Square || Variant==TacticalSquare; }',
       '// Call only for RSH items: other weapons retain their common optic IDs.',
       'inline FString Upgrade(const FString& Variant) { if(Variant==TEXT("holographic"))return Square;if(Variant==TEXT("eoth_holographic"))return TacticalSquare;return Variant; }',
       'inline FString SourceVariant(const FString& Variant) { if(Variant==Square)return TEXT("holographic");if(Variant==TacticalSquare)return TEXT("eoth_holographic");return Variant; }',
       'inline bool Supports(const FString& Variant) { const FString Source=SourceVariant(Variant);return '+ ' || '.join(f'Source==TEXT("{k}")' for k in [*specs,'pso1_4x'])+'; }',
       'inline FString MeshPath(const FString& Variant) { if(Variant==TEXT("pso1_4x"))return TEXT("/Game/Weapons/RSH12/PSO20261004/Meshes/SM_RSH12_PSO1");return TEXT("/Game/Weapons/RSH12/Optics20261004/Meshes/SM_RSH12_")+SourceVariant(Variant); }',
       'inline FString RailPath(const FString& Variant) { if(Variant==TEXT("pso1_4x"))return TEXT("/Game/Weapons/RSH12/PSO20261004/Meshes/SM_RSH12_PSOReceiverShoe");return TEXT("/Game/Weapons/RSH12/Optics20261004/Meshes/SM_RSH12_Rail_")+SourceVariant(Variant); }',
       'inline FTransform RailMount() { return FTransform(FRotationMatrix::MakeFromXZ('+vec(root_forward)+','+vec(root_up)+').ToQuat(),'+vec(root_point)+',FVector(.01f)); }',
       'inline FTransform OpticMount(const FString& Variant)','{','    FVector Offset(0.f,0.f,.65f);']
for key,(_,offset) in specs.items():
    if offset:lines.append(f'    if(SourceVariant(Variant)==TEXT("{key}"))Offset.X={offset*100:.7f}f;')
lines+=['    return FTransform(Offset)*RailMount();','}','}']
(P/'Source/FPSGAME/Weapons/RSH12OpticAssets.h').write_text('\n'.join(lines)+'\n',encoding='utf8')
