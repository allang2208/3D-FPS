"""Animated outgoing belt and leading tab; visual game asset, not mechanical CAD."""
import bpy,json,math,sys
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;R=O.parent;E=O/'Exports';E.mkdir(exist_ok=True)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(R/'CarryHandle18/PKM_CarryHandle_Editable.blend'),use_scripts=False)
r=bpy.data.objects['PKM_Manny_Rig'];r.data.pose_position='REST'
fit=Matrix(json.loads((R/'Animation03/animation_manifest.json').read_text())['fit_matrix'])
B=r.data.bones['WPN_root'].matrix_local@fit;Bi=B.inverted()
layout=json.loads((R/'Belt08/belt_layout.json').read_text());centers=[Vector(v) for v in layout['centers']]
pitch=(centers[1]-centers[0]).length;origin=centers[0];hinge=Vector((.015, .03879157,.07286614))

def active(ob):
 bpy.ops.object.select_all(action='DESELECT');ob.hide_set(False);ob.select_set(True);bpy.context.view_layer.objects.active=ob

def bind(ob,bone,material):
 ob['mechanical_bone']=bone;ob['outgoing_revision']='OutgoingBelt19'
 ob.parent=r;ob.matrix_parent_inverse=Matrix.Identity(4);ob.matrix_basis=Matrix.Identity(4)
 ob.vertex_groups.clear();ob.vertex_groups.new(name=bone).add(list(range(len(ob.data.vertices))),1,'REPLACE')
 for mod in list(ob.modifiers):
  if mod.type=='ARMATURE':ob.modifiers.remove(mod)
 ob.modifiers.new('Rigid outgoing belt piece','ARMATURE').object=r
 ob.data.materials.clear();ob.data.materials.append(bpy.data.materials[material])
 ob.hide_set(False);ob.hide_render=bone.startswith('New_')

# Leaf bones only: hiding a spent link never scales a receiver or hand parent.
specs={'PKM_OutgoingTab':hinge,'New_PKM_OutgoingTab':hinge}
for i in range(25):
 # Park unused units inside the covered feedway even in a static asset preview.
 specs[f'PKM_OutgoingClip_{i:02}']=origin.copy()
 specs[f'PKM_OutgoingBridge_{i:02}']=origin.copy()
active(r);bpy.ops.object.mode_set(mode='EDIT')
for name,point in specs.items():
 bone=r.data.edit_bones.new(name);bone.head=(0,0,0);bone.tail=(0,.012,0)
 bone.matrix=B@Matrix.Translation(point);bone.parent=r.data.edit_bones['WPN_root'];bone.use_connect=False
bpy.ops.object.mode_set(mode='OBJECT')

# Keep the original rolled-end shape and UVs. Shorten only its protruding
# direction, then hang it from the belt hinge rather than a fixed gun surface.
tab=bpy.data.objects['PKM_Part_113'];active(tab)
for mod in list(tab.modifiers):
 if mod.type!='ARMATURE':bpy.ops.object.modifier_apply(modifier=mod.name)
shape=B@Matrix.Translation(hinge)@Matrix.Rotation(math.radians(18),4,'Y')@Matrix.Diagonal((.86,1,1,1))@Matrix.Translation(-hinge)@Bi
tab.data.transform(shape)
bind(tab,'PKM_OutgoingTab','PKM_QBZ_Body__OldBelt')
new=tab.copy();new.data=tab.data.copy();bpy.context.scene.collection.objects.link(new);new.name='New_PKM_LeadingTab'
for key in ['source_part_id','source_name','source_parent']:
 if key in new:del new[key]
bind(new,'New_PKM_OutgoingTab','PKM_QBZ_Body__NewBelt')

def frame(center,direction):
 x=direction.normalized();y=Vector((0,1,0));z=x.cross(y).normalized();y=z.cross(x).normalized()
 out=Matrix((x,y,z)).transposed().to_4x4();out.translation=center;return out

# Reuse the accepted empty C-clips and connecting strips, including their UVs
# and steel maps. Cartridges themselves are never duplicated on the outlet.
prototypes=[('Clip',bpy.data.objects['PKM_Belt08_Clip_00'],frame(centers[0],centers[1]-centers[0])),
 ('Bridge',bpy.data.objects['PKM_Belt08_Link_00'],frame((centers[0]+centers[1])*.5,centers[1]-centers[0]))]
for kind,prototype,source_frame in prototypes:
 for i in range(25):
  name=f'PKM_Outgoing{kind}_{i:02}';ob=prototype.copy();ob.data=prototype.data.copy();bpy.context.scene.collection.objects.link(ob);ob.name=name
  ob.data.transform(B@Matrix.Translation(specs[name])@source_frame.inverted()@Bi)
  bind(ob,name,'PKM_BeltLinkSteel__OldBelt')
  for key in ['source_part_id','source_name','source_parent']:
   if key in ob:del ob[key]

r.data.pose_position='POSE';bpy.context.view_layer.update()
sys.path.insert(0,str(R/'Belt08'));from mesh_export import export_mesh
export_mesh(r,E/'SK_PKM_Manny_Modular.fbx')
bpy.ops.wm.save_as_mainfile(filepath=str(O/'PKM_OutgoingBelt_Editable.blend'))
(O/'authoring.json').write_text(json.dumps({'source':'CarryHandle18/PKM_CarryHandle_Editable.blend',
 'original_part':113,'pitch_cm':pitch*100,'origin_gun_m':list(origin),'tab_hinge_gun_m':list(hinge),
 'tab_protrusion_scale':.86,'tab_extra_droop_degrees':18,'empty_link_count':25,
 'new_bones':list(specs),'animations_reimported':False,'materials':'existing QBZ steel / Belt08 link maps',
 'target_mesh':'/Game/Weapons/PKMLowpoly20260922/Accessories14/SK_PKM_Manny_Modular'},indent=2))
print('PKM19_OUTGOING_BELT_EXPORTED',flush=True)
