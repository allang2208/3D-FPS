import bpy,json
from pathlib import Path
root=Path('D:/FPS3D/FPSGAME/SourceAssets/M4Infima');bpy.ops.wm.open_mainfile(filepath=str(root/'Original/Blender_Source_Files_FreeFpsTemplate/Animations/Animations_Assault_Rifle.blend'))
rows=[]
for o in bpy.context.scene.objects:
 if o.type not in {'ARMATURE','CAMERA'} and not o.name.startswith(('SK_','SM_')):continue
 row={'name':o.name,'type':o.type,'hide':o.hide_render,'world':[list(r)for r in o.matrix_world],'constraints':[{'type':c.type,'target':c.target.name if getattr(c,'target',None) else None,'subtarget':getattr(c,'subtarget',None)}for c in o.constraints]}
 if o.type=='ARMATURE':row['action']=o.animation_data.action.name if o.animation_data and o.animation_data.action else None;row['bones']=[{'name':b.name,'head':list(b.head_local),'tail':list(b.tail_local),'deform':b.use_deform}for b in o.data.bones if o.name!='Armature' or b.name in ['hand_r','hand_l','ik_hand_gun']]
 if o.type=='MESH':row['materials']=[m.name for m in o.data.materials];row['modifiers']=[(m.type,m.object.name if m.type=='ARMATURE' and m.object else '')for m in o.modifiers]
 rows.append(row)
(root/'source_detail.json').write_text(json.dumps(rows,indent=2))
scene=bpy.context.scene;scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=1000;scene.render.resolution_y=650;scene.render.resolution_percentage=100
scene.render.filepath=str(root/'original_reference.png');bpy.ops.render.render(write_still=True)
