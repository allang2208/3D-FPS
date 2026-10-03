import sys,json,bpy,numpy as np
from pathlib import Path
O=Path(__file__).parent;sys.path.insert(0,str(O))
g={'__file__':str(O/'fit_cock_contact.py'),'__name__':'compare'}
exec((O/'fit_cock_contact.py').read_text().split('x=[-sign')[0],g)
c=g['c'];recipe=json.loads((O/'cock_contact_single.json').read_text());x=recipe['hand_translation_canonical']+recipe['wrist_rotation_xyz']+recipe['grasp_target_translation_canonical']
for digit in g['hold']:x+=recipe['digit_target_offsets'][digit]
from mathutils import Vector,Matrix
x+=list(Vector(recipe['thumb_center_offset_canonical'])-Vector((.0035,.0015,.008)))
expected,_=g['pose'](x,.5)
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'RSH12SingleAction20261003/single/A_RSH12_aim_fire_Editable.blend'));r=next(o for o in bpy.data.objects if o.type=='ARMATURE');bpy.context.scene.frame_set(54);bpy.context.view_layer.update()
can=(r.pose.bones['WPN_root'].matrix@c['scope']['alignment']).inverted();actual={b.name:can@b.matrix for b in r.pose.bones}
for n in ('hand_r','thumb_01_r','thumb_03_r','middle_metacarpal_r','index_metacarpal_r','pinky_02_r','WPN_Hammer'):
 print('BAKE_COMPARE',n,'expected',list(expected[n].translation),'actual',list(actual[n].translation),'mm',(expected[n].translation-actual[n].translation).length*1000,flush=True)
pts=g['skin'](c,actual);ob=next(o for o in bpy.data.objects if o.type=='MESH');ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();labels={v.index:max(v.groups,key=lambda a:a.weight).group for v in ob.data.vertices if v.groups};names={v.index:v.name for v in ob.vertex_groups}
sample=[can@r.matrix_world.inverted()@ob.matrix_world@v.co for v,source in zip(me.vertices,ob.data.vertices) if any(names[w.group].endswith('_r') and names[w.group].startswith(('hand','thumb','index','middle','ring','pinky')) and w.weight>.5 for w in source.groups)]
errors=[(Vector(p)-q).length*1000 for p,q in zip(pts,sample)];print('BAKE_SKIN_FORMULA',len(pts),len(sample),max(errors),flush=True)
