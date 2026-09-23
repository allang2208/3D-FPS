"""Convert GLB-derived UV0 to the original 4K texture atlas, without touching skin/actions."""
import bpy,json,hashlib,shutil
from pathlib import Path
O=Path(__file__).parent;C=O.parent;S=C.parent/'SVDDragunov20260922';PARTS=['Body','Magazine','Trigger','ChargingHandle','SafetyLever','ScopeBody','ScopeMount','ScopeLens'];report={}
if (O/'uv_repair_source.json').exists():raise RuntimeError('Repair already applied. Re-author with the corrected splitter rather than flipping twice.')
bpy.context.preferences.filepaths.save_version=0

def backup(p):
 q=O/'Before'/p.relative_to(C.parent);q.parent.mkdir(parents=True,exist_ok=True)
 if q.exists():raise RuntimeError('Backup already exists: '+str(q))
 shutil.copy2(p,q)
def poshash(o):
 return hashlib.sha256(repr([tuple(v.co) for v in o.data.vertices]).encode()).hexdigest()
def uvhash(o):return hashlib.sha256(repr([tuple(x.uv) for x in o.data.uv_layers[0].data]).encode()).hexdigest()
def flip(o):
 assert len(o.data.uv_layers)>0,o.name
 old=poshash(o);before=uvhash(o)
 for x in o.data.uv_layers[0].data:x.uv.y=1.0-x.uv.y
 assert old==poshash(o)
 o.data['svd_uv_original_4k']=True
 return {'vertices':len(o.data.vertices),'loops':len(o.data.loops),'uv_layers':len(o.data.uv_layers),'geometry_unchanged':True,'uv_before':before,'uv_after':uvhash(o)}
def select(obs):
 bpy.ops.object.select_all(action='DESELECT')
 for o in obs:o.hide_set(False);o.select_set(True)
 bpy.context.view_layer.objects.active=obs[-1]
# Preserve source part positions and material-slot identities; only texture coordinates change.
for part in PARTS:
 p=S/'Authored'/('SM_SVD_'+part+'.fbx');backup(p);bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(p));obs=[o for o in bpy.context.scene.objects if o.type=='MESH'];assert len(obs)==1
 report[part]=flip(obs[0]);select(obs)
 bpy.ops.export_scene.fbx(filepath=str(p),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False)
# Update both editable assemblies; the legacy viewmodel only donates arms to author_svd.py.
for p in [S/'Authored/SVD_Mechanical.blend',C/'SVD_Complete_Editable.blend']:
 backup(p);bpy.ops.wm.open_mainfile(filepath=str(p));changed={}
 for part in PARTS:
  ob=bpy.data.objects.get('SM_SVD_'+part);assert ob is not None,(str(p),part)
  changed[part]=flip(ob)
 report[p.name]=changed
 if p.parent==C:
  arms=bpy.data.objects['SK_Manny_Arms_Export'];before_arm={'positions':poshash(arms),'uv':uvhash(arms)}
  rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');a=bpy.data.actions['A_SVD_idle'];rig.animation_data.action=a;rig.animation_data.action_slot=a.slots[0];bpy.context.scene.frame_set(0)
  meshes=[o for o in bpy.context.scene.objects if o.type=='MESH'];select(meshes+[rig]);fbx=C/'Exports/SK_SVD_Manny.fbx';backup(fbx)
  bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH','ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',use_tspace=False)
  assert before_arm=={'positions':poshash(arms),'uv':uvhash(arms)}
  report['arms_untouched']=before_arm;report['animations_unchanged']=[a.name for a in bpy.data.actions if a.name.startswith('A_SVD_')]
 bpy.ops.wm.save_as_mainfile(filepath=str(p))
report['correction']='UV0.v = 1 - UV0.v for eight original SVD parts. Original 4K images are unchanged.'
(O/'uv_repair_source.json').write_text(json.dumps(report,indent=2));print('SVD_UV_SOURCE_REPAIRED',len(PARTS),flush=True)
