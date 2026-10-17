import bpy,json
from pathlib import Path
O=Path(__file__).parent;S=O.parent/'M870UrbanAnimations20261015/Original/870'
bpy.ops.wm.open_mainfile(filepath=str(S/'Renmington 870 unfucked.blend'),use_scripts=False)
data={'fps':bpy.context.scene.render.fps,'frame':bpy.context.scene.frame_current,'units':bpy.context.scene.unit_settings.scale_length,'objects':[],'actions':[]}
for ob in bpy.context.scene.objects:
 row={'name':ob.name,'type':ob.type,'parent':ob.parent.name if ob.parent else None,'matrix':[list(v) for v in ob.matrix_world]}
 if ob.type=='MESH':row.update(vertices=len(ob.data.vertices),materials=[m.name if m else None for m in ob.data.materials],groups=[g.name for g in ob.vertex_groups][:12])
 if ob.type=='ARMATURE':row.update(bones=[b.name for b in ob.data.bones],action=ob.animation_data.action.name if ob.animation_data and ob.animation_data.action else None)
 data['objects'].append(row)
for a in bpy.data.actions:data['actions'].append({'name':a.name,'range':list(a.frame_range)})
(O/'reference_inventory.json').write_text(json.dumps(data,indent=2))
print('REFERENCE',data['fps'],data['units'],[(v['name'],v['type'],v.get('vertices')) for v in data['objects']],flush=True)
print('ACTIONS',data['actions'],flush=True)
