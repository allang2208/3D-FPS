"""Production export of 416 furniture fitted to the accepted M4/M16 interfaces.
Preserve source UV0, real dimensions, palm surface and native material slots.
"""
import bpy,json
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;S=O.parent;H=S/'HK416Reworked20260930'
I=json.loads((H/'authoring.json').read_text());R=Matrix(I['root_matrix']);A=Matrix(I['source_to_weapon_root'])
bpy.context.preferences.filepaths.save_version=0
report={'parts':{},'source':'HK416 Full ReWorked by MojoLeeDa; CC BY 4.0','testing':'Not run'}
def append(file,name):
 with bpy.data.libraries.load(str(file),link=False) as (src,dst):dst.objects=[name]
 ob=dst.objects[0];bpy.context.collection.objects.link(ob);ob.hide_set(False)
 ob.data.transform(ob.matrix_world);ob.parent=None;ob.matrix_world=Matrix.Identity(4);ob.modifiers.clear();ob.vertex_groups.clear()
 return ob
for family in ('M4','M16'):
 for part,key in (('stock','factory_stock'),('reargrip','factory_grip')):
  bpy.ops.wm.read_factory_settings(use_empty=True)
  name='SM_416_Stock' if part=='stock' else 'SM_416_RearGrip'
  ob=append(H/'Exports/Attachments'/('SM_HK416_'+key+'_Editable.blend'),'SM_HK416_'+key)
  ob.data.transform(R.inverted())
  fit={}
  if part=='stock':
   # The receiver shoulder and buffer axis are measured interfaces from the
   # existing HK416, M4 and M16 attachment authoring sources (not whole bounds).
   source=A@Vector((0,-.0385,.01945))
   target=Vector((0,.0385,.0725)) if family=='M4' else Vector((-.000038,.041045,.0917))
   ob.data.transform(Matrix.Translation(target-source))
   fit={'source_shoulder':list(source),'target_shoulder':list(target),'physical_scale':1.0}
  else:
   # The HK source palm was already registered to M4's accepted contact.
   # Only the neck above the palm adapts to the recipient receiver.
   if family=='M4':
    reference=append(S/'PhantomRearGripSeamFit20260913/M4_Assembly_Editable.blend','FactoryMountReference')
    target=max(v.co.z for v in reference.data.vertices)
    bpy.data.objects.remove(reference,do_unlink=True)
   else:target=.01657
   top=max(v.co.z for v in ob.data.vertices);floor=.008
   for v in ob.data.vertices:
    if v.co.z>floor:v.co.z=floor+(v.co.z-floor)*(target-floor)/(top-floor)
   fit={'unchanged_palm_below_z':floor,'source_neck_top':top,'target_neck_top':target,'physical_scale':1.0}
  ob.name=name;ob.data.update()
  bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
  out=O/family;out.mkdir(exist_ok=True);file=out/(name+'.fbx')
  bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=False)
  bpy.data.libraries.write(str(out/(name+'_Editable.blend')),{ob},fake_user=True)
  report['parts'][family+'_'+part]={'name':name,'family':family,'source_key':key,'fbx':str(file),'fit':fit,'slots':[m.name for m in ob.data.materials]}
(O/'models.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('416_AR_MODELS_AUTHORED',len(report['parts']),flush=True)
