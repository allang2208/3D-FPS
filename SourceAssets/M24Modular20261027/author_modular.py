"""Split the installed M24 without rebaking its V9 hands or animations."""
import bpy, json
from pathlib import Path
from mathutils import Matrix, Vector

O=Path(__file__).resolve().parent
SRC=O.parent/'M24CustomScope20261026'
X=O/'Exports';X.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(SRC/'M24_V9_Gameplay_Editable.blend'),use_scripts=False)
s=bpy.context.scene;r=bpy.data.objects['M24_V9_Rig'];r.animation_data.action=None
for pb in r.pose.bones:pb.matrix_basis=Matrix.Identity(4)
s.frame_set(0);bpy.context.view_layer.update()
skin=bpy.data.objects['M24_V9_BareArms']
parts=[o for o in s.objects if o.type=='MESH' and o!=skin]
mechanical={'M24_'+n for n in ('base','bolt','boltrear','bullet','cheekrest','clip','silencer','trigger')}
scope=[o for o in parts if o.name not in mechanical]
groups={'m24_custom_scope_6x':scope,'m24_factory_suppressor':[bpy.data.objects['M24_silencer']],
        'm24_cheekrest':[bpy.data.objects['M24_cheekrest']]}
source=json.loads((SRC/'gameplay_authoring.json').read_text())
def ue(v):return [v[0]*100,-v[1]*100,v[2]*100]
def points(obs):return [v.co.copy() for o in obs for v in o.data.vertices]
body=points([bpy.data.objects['M24_base']]);front=max(p.y for p in body)
rim=[p for p in body if p.y>front-.001]
bare=Vector((sum(p.x for p in rim)/len(rim),front,sum(p.z for p in rim)/len(rim)))
report={'models':{},'component_space':'FBX -Y/Z; UE centimetres (x,-y,z)',
        'registration_ue_cm':{n:ue(source['markers'][n]) for n in ('WPN_RearSight','WPN_FrontSight','WPN_SOCKET_Magazine')},
        'bare_muzzle_ue_cm':ue(bare),'source_parts':[o.name for o in parts],
        'source_blend':str(SRC/'M24_V9_Gameplay_Editable.blend'),'tested':False}
def select(obs):
    bpy.ops.object.select_all(action='DESELECT')
    for ob in obs:ob.hide_set(False);ob.select_set(True)
    bpy.context.view_layer.objects.active=obs[0]
def export(obs,path,skinned=False):
    select(obs)
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,
        object_types={'ARMATURE','MESH'} if skinned else {'MESH'},
        axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,
        mesh_smooth_type='FACE',use_tspace=True,use_mesh_modifiers=False)
for key,obs in groups.items():
    copies=[]
    for ob in obs:
        c=ob.copy();c.data=ob.data.copy();s.collection.objects.link(c)
        c.parent=None;c.matrix_world=Matrix.Identity(4);c.modifiers.clear();copies.append(c)
    select(copies);bpy.ops.object.join();combined=bpy.context.object
    combined.name='SM_M24_'+key
    path=X/(combined.name+'.fbx');export([combined],path)
    row={'file':str(path),'objects':[o.name for o in obs],'sockets_ue_cm':{}}
    if key=='m24_custom_scope_6x':
        row['sockets_ue_cm']={n:ue(source['markers']['WPN_'+n]) for n in ('RearSight','FrontSight')}
        row['sockets_ue_cm']={'SightRear':row['sockets_ue_cm']['RearSight'],'SightFront':row['sockets_ue_cm']['FrontSight']}
        up=row['sockets_ue_cm']['SightRear'].copy();up[2]+=1
        row['sockets_ue_cm']['SightUp']=up
    if key=='m24_factory_suppressor':row['sockets_ue_cm']['Muzzle']=ue(source['markers']['WPN_SOCKET_Muzzle'])
    report['models'][key]=row
    bpy.data.objects.remove(combined,do_unlink=True)
# Independent assemblies are removed from the skinned viewmodel, not merely
# covered with another mesh. The animated magazine/bolt/trigger keep their weights.
detached={ob for obs in groups.values() for ob in obs}
for ob in parts:
    if ob in detached:continue
    section={'M24_clip':'M24_FactoryMagazine','M24_bolt':'M24_BoltHandle',
        'M24_boltrear':'M24_BoltCarrier','M24_trigger':'M24_FactoryTrigger'}.get(ob.name)
    if section:
        for i,mat in enumerate(ob.data.materials):
            m=mat.copy();m.name=section;ob.data.materials[i]=m
kept=[o for o in parts if o not in detached]
report['mesh']=str(X/'SK_M24_ModularV9.fbx')
export([r,skin,*kept],Path(report['mesh']),True)
report['section_material_source']={k:'M24_Body' for k in ('M24_FactoryMagazine','M24_BoltHandle','M24_BoltCarrier','M24_FactoryTrigger')}
# Keep detached components in the editable scene for exact reassembly, but exclude
# them from the exported skeletal mesh selection.
r.animation_data.action=bpy.data.actions['A_M24_idle'];r.animation_data.action_slot=r.animation_data.action.slots[0]
s.frame_set(0)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(O/'M24_Modular_Editable.blend'))
(O/'authoring.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('M24_MODULAR_EXPORTED',json.dumps(report),flush=True)
