"""Build and save the real skinned M09 rig from V02; background authoring only."""
import bpy,json,math,time
import numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
ROOT=Path("D:/FPS3D/FPSGAME/SourceAssets/HangingBellM09Meshy20261003")
OUT=ROOT/"RigV03"
recipe=json.loads((OUT/"Authoring/rig_recipe_v03.json").read_text())
weights=np.load(OUT/"Authoring/skin_weights_v03.npz")
bpy.ops.wm.open_mainfile(filepath=recipe["source"])
scene=bpy.context.scene
scene.frame_set(1)
collection=bpy.data.collections.new("M09_Rig_V03");scene.collection.children.link(collection)
ad=bpy.data.armatures.new("M09_Skeleton_V03");rig=bpy.data.objects.new("M09_Rig_V03",ad);collection.objects.link(rig)
rig.show_in_front=True;rig.data.display_type="OCTAHEDRAL"
bpy.ops.object.select_all(action="DESELECT");rig.select_set(True);bpy.context.view_layer.objects.active=rig
bpy.ops.object.mode_set(mode="EDIT")
for entry in recipe["bones"]:
 eb=ad.edit_bones.new(entry["name"]);eb.head=entry["head"];eb.tail=entry["tail"];eb.use_deform=entry["deform"]
 if entry["parent"]:eb.parent=ad.edit_bones[entry["parent"]]
 axis=(eb.tail-eb.head).normalized();front=Vector((0,-1,0))
 if abs(axis.dot(front))>.95:front=Vector((0,0,1))
 eb.align_roll(front)
bpy.ops.object.mode_set(mode="OBJECT")
groups={}
for entry in recipe["bones"]:
 name=entry["group"]
 if name not in groups:groups[name]=ad.collections.new(name)
 b=ad.bones[entry["name"]];groups[name].assign(b);b.use_inherit_rotation=True
 b.inherit_scale="NONE"
 if name=="IK controls":b.color.palette="THEME04"
 elif "Membrane" in name:b.color.palette="THEME03"
 elif name in ["Main eyes","Eye crown"]:b.color.palette="THEME02"
 else:b.color.palette="THEME01"
 p=rig.pose.bones[b.name];p.rotation_mode="XYZ"
 p["anatomical_role"]=name
 if entry["deform"] and b.name not in ["root","suspension"]:
  p.lock_location=(True,True,True);p.lock_scale=(True,True,True)
for name in ["Hook fingers","Small fingers","Main eyes"]:
 groups[name].is_visible=False
# Animator handles, excluded from export. No actions or posed demonstration are generated.
shapes=bpy.data.collections.new("M09_Control_Shapes");scene.collection.children.link(shapes);shapes.hide_render=True
def shape(name,points,cyclic=True):
 curve=bpy.data.curves.new(name,"CURVE");curve.dimensions="3D";sp=curve.splines.new("POLY");sp.points.add(len(points)-1)
 for pt,co in zip(sp.points,points):pt.co=(*co,1)
 sp.use_cyclic_u=cyclic
 ob=bpy.data.objects.new(name,curve);shapes.objects.link(ob);ob.hide_render=True
 return ob
circle=shape("M09_Shape_Grip",[(math.cos(t),0,math.sin(t)) for t in np.linspace(0,2*math.pi,25)[:-1]])
diamond=shape("M09_Shape_Pole",[(1,0,0),(0,0,1),(-1,0,0),(0,0,-1)])
rootshape=shape("M09_Shape_Root",[(math.cos(t),math.sin(t),0) for t in np.linspace(0,2*math.pi,33)[:-1]])
shapes.hide_viewport=True
for name,size in [("root",.65),("suspension",.12)]:
 pb=rig.pose.bones[name];pb.custom_shape=rootshape;pb.use_custom_shape_bone_size=False;pb.custom_shape_scale_xyz=(size,)*3
bpy.context.view_layer.update()
def influence_driver(constraint,prop):
 f=constraint.driver_add("influence");d=f.driver;d.type="SCRIPTED"
 v=d.variables.new();v.name="ik";v.type="SINGLE_PROP";v.targets[0].id=rig;v.targets[0].data_path=f'["{prop}"]'
 d.expression="ik"
for c in recipe["controls"]:
 rig[c["property"]]=c["default"]
 rig.id_properties_ui(c["property"]).update(min=0,max=1,soft_min=0,soft_max=1,
  description="0 FK rest authoring; 1 grip IK. Animate this property for a handoff.")
 fore=rig.pose.bones[c["forearm"]];con=fore.constraints.new("IK");con.name="Grip IK";con.target=rig;con.subtarget=c["target"]
 con.pole_target=rig;con.pole_subtarget=c["pole"];con.chain_count=2;con.use_stretch=False;con.iterations=96
 base=ad.bones[c["upper"]];end=ad.bones[c["forearm"]]
 pole=ad.bones[c["pole"]].head_local
 axis=(base.tail_local-base.head_local).normalized()
 pole_normal=(end.tail_local-base.head_local).cross(pole-base.head_local)
 projected=pole_normal.cross(axis).normalized()
 xaxis=base.matrix_local.to_3x3().col[0].normalized()
 con.pole_angle=math.atan2(axis.dot(xaxis.cross(projected)),xaxis.dot(projected))
 influence_driver(con,c["property"])
 rot=rig.pose.bones[c["hand"]].constraints.new("COPY_ROTATION")
 rot.name="Grip orientation";rot.target=rig;rot.subtarget=c["target"];rot.target_space="WORLD";rot.owner_space="WORLD"
 influence_driver(rot,c["property"])
 pb=rig.pose.bones[c["target"]];pb.custom_shape=circle;pb.use_custom_shape_bone_size=False
 size=.075 if c["kind"]=="big" else .045;pb.custom_shape_scale_xyz=(size,)*3
 pb=rig.pose.bones[c["pole"]];pb.custom_shape=diamond;pb.use_custom_shape_bone_size=False;pb.custom_shape_scale_xyz=(.045,)*3
# Soft forearm helpers follow half the local hand twist, while cuffs use the stable forearm group.
for side in ["L","R"]:
 tw=rig.pose.bones[f"big_forearm_twist_{side}"];driver=tw.driver_add("rotation_euler",1).driver;driver.type="SCRIPTED"
 var=driver.variables.new();var.name="twist";var.type="TRANSFORMS";target=var.targets[0];target.id=rig
 target.bone_target=f"big_hand_{side}";target.transform_type="ROT_Y";target.transform_space="LOCAL_SPACE"
 driver.expression="0.5*twist"
# Four influences, integer-normalized in the production recipe. Preserve original authoring masks.
objects=[]
for part in recipe["parts"]:
 ob=bpy.data.objects[part["name"]];pid=part["id"]
 bi=weights[f"p{pid}_bones"];qw=weights[f"p{pid}_weights"]
 vid=np.repeat(np.arange(len(bi),dtype=np.int32),4)
 flatbone=bi.ravel().astype(np.int32);flatweight=qw.ravel().astype(np.int32)
 keep=flatweight>0;vid=vid[keep];flatbone=flatbone[keep];flatweight=flatweight[keep]
 key=flatbone*2048+flatweight;order=np.argsort(key,kind="stable");key=key[order];vid=vid[order]
 unique,starts=np.unique(key,return_index=True);ends=np.r_[starts[1:],len(key)];vgs={}
 for val,start,end in zip(unique,starts,ends):
  boneid=int(val//2048);weight=float(val%2048)/1024
  if boneid not in vgs:
   vgs[boneid]=ob.vertex_groups.new(name=recipe["bones"][boneid]["name"])
  vgs[boneid].add(vid[start:end].tolist(),weight,"REPLACE")
 # Identity armature object transform: existing mesh locations/pivots stay in place.
 ob.parent=rig;ob.matrix_parent_inverse=Matrix.Identity(4)
 mod=ob.modifiers.new("M09_SkeletalDeform_V03","ARMATURE");mod.object=rig
 mod.use_vertex_groups=True;mod.use_bone_envelopes=False;mod.use_deform_preserve_volume=False
 if "not_animation_ready" in ob:del ob["not_animation_ready"]
 ob["rig_version"]="M09_RigV03";ob["skin_influence_limit"]=4
 ob["rigging_status"]="Bound and exported; deformation acceptance not performed"
 objects.append(ob)
 print("SKIN_WRITTEN",ob.name,"bone_groups",len(vgs),flush=True)
rig["source_geometry"]="M09_Separated_Adjusted_v02.blend"
rig["rig_version"]="M09_RigV03";rig["unit"]="meter";rig["height_m"]=2.8
rig["deform_influence_limit"]=4;rig["user_testing_pending"]=True
rig["control_usage"]="FK default. Enable IK_big_L/R or IK_small_L/R for grip + elbow pole control."
rig["eye_usage"]="Five rotating visible main-eye domes; eyelids stay on the eye-crown mesh."
rig["membrane_usage"]="Six independent four-bone tissue chains. Animate root for opening, middle/tip for wave."
notes=bpy.data.texts.new("M09_RIG_README")
notes.write("""M-09 悬钟 / Rig V03
源：V02 拆分修整模型；25 个网格，原 UV/PBR 及切口封闭面保留。
骨架：专用悬挂骨架，长臂与腹前小臂、20 指三节链、6 片四节背叶、眼冠与 5 主眼。
默认 FK。物体自定义属性 IK_big_L / IK_big_R / IK_small_L / IK_small_R：
0 = FK；1 = IK。CTRL_*_grip 移动抓握点，CTRL_*_elbow 调整肘向。
小手指、长指及主眼骨集合默认隐藏，需要时在 Armature 骨集合展开。
大臂腕箍使用前臂权重，避免跟随手指卷曲。各片背叶根部采用主体相同权重。
背叶独立组织骨链通过转动首段开合，后续骨段控制弯折和颤动。
旋转 eye_crown 制作眼冠摆锤，crown_neck 控制上方软连接；eye_01..05 控制主眼。
本次未制作动作片段、眨眼形态键、碰撞或 UE 资产；未做姿态测试、渲染、引擎验收。
这是保留高模的绑骨制作源，不等于已优化的游戏 LOD。
""")
for image in bpy.data.images:
 if image.source=="FILE" and not image.packed_file:
  try:image.pack()
  except RuntimeError:pass
for coll in list(bpy.data.collections):
 if coll.name=="M09_Adjusted_Source_Parts_V02":coll.name="M09_Skinned_Parts_V03"
bpy.ops.object.select_all(action="DESELECT")
rig.select_set(True);bpy.context.view_layer.objects.active=rig
scene["M09_delivery_stage"]="Skeleton and skin authored; user deformation testing pending"
bpy.context.view_layer.update()
blend=OUT/"Authoring/M09_Rigged_v03.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(blend),compress=True)
print("BLEND_SAVED",str(blend),flush=True)
# Export the same meshes plus the actual armature; Blender-only controls are excluded.
for ob in objects:ob.select_set(True)
glb=OUT/"Exports/M09_Rigged_v03.glb";fbx=OUT/"Exports/M09_Rigged_v03.fbx"
kwargs=dict(filepath=str(glb),export_format="GLB",use_selection=True,export_yup=True,
            export_normals=True,export_tangents=True,export_animations=False,export_extras=True,
            export_skins=True,export_def_bones=True,export_all_influences=False)
available=set(bpy.ops.export_scene.gltf.get_rna_type().properties.keys())
if "export_influence_nb" in available:kwargs["export_influence_nb"]=4
bpy.ops.export_scene.gltf(**kwargs)
print("GLB_SAVED",str(glb),flush=True)
bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={"ARMATURE","MESH"},
                       apply_unit_scale=True,apply_scale_options="FBX_SCALE_UNITS",
                       axis_forward="-Z",axis_up="Y",bake_anim=False,path_mode="COPY",
                       embed_textures=True,mesh_smooth_type="FACE",add_leaf_bones=False,
                       use_armature_deform_only=True,armature_nodetype="NULL",
                       use_mesh_modifiers=False)
print("FBX_SAVED",str(fbx),flush=True)
receipt={"stage":"Rig V03 saved and exported","files":[str(blend),str(glb),str(fbx)],
         **recipe["counts"],"source_triangles_including_closures":1890032,
         "source_geometry_preserved":True,"max_influences":4,"rest_pose":"V02 suspended form",
         "animation_clips_created":0,"engine_assets_imported":False,
         "tests_or_renders_performed":False}
(OUT/"Records/rig_delivery_v03.json").write_text(json.dumps(receipt,indent=2),encoding="utf8")
print("RIG_DELIVERY_SAVED",json.dumps(receipt),flush=True)
