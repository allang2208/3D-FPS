"""Reusable skinned leaf and binding without fixed printable surfaces. No render."""
from pathlib import Path
import bpy, bmesh, json, math, runpy

ROOT=Path(__file__).resolve().parent
SOURCE=ROOT.parent/'AlchemyManualFinePress20261016/AlchemyManualFinePress.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE),load_ui=False,use_scripts=False)
bpy.context.preferences.filepaths.save_version=0
body=bpy.data.objects['SM_AlchemyManualOpen']
leaf=bpy.data.objects['SM_AlchemyManualLeaf']

# Keep the leather, lining, page block and metalwork. Remove the old printable
# sheets, including their connected thin rims, so they cannot cover moving ink.
bm=bmesh.new();bm.from_mesh(body.data)
removed={v for f in bm.faces if body.data.materials[f.material_index].name in ('RecipeLeft','RecipeRight') for v in f.verts}
todo=list(removed)
while todo:
    v=todo.pop()
    for edge in v.link_edges:
        other=edge.other_vert(v)
        if other not in removed:removed.add(other);todo.append(other)
bmesh.ops.delete(bm,geom=list(removed),context='VERTS')
bm.to_mesh(body.data);bm.free()
body.name='SM_AlchemyManualBinding'
runpy.run_path(str(ROOT.parent/'AlchemyManualBindingTangents20261016/repair_binding_uv.py'))['repair_binding_uv'](body)

# Reuse the fine rounded outline and independently oriented front/back UVs.
# Flatten its middle surface; the reusable rig owns all resting/turning curves.
layer=(48+1)*(24+1)
for i,v in enumerate(leaf.data.vertices):v.co.z=.016 if i<layer else -.016
leaf.name='SK_BookLeafTemplate'
width=15.51884842;segments=30
arm=bpy.data.armatures.new('BookLeafRig')
rig=bpy.data.objects.new('Armature',arm);bpy.context.scene.collection.objects.link(rig)
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
bpy.ops.object.mode_set(mode='EDIT')
root=arm.edit_bones.new('BookRoot');root.head=(0,0,0);root.tail=(0,0,1)
parent=root
for i in range(segments+1):
    bone=arm.edit_bones.new(f'Page_{i:02d}')
    bone.head=(width*i/segments,0,0);bone.tail=(width*(i+1)/segments,0,0)
    bone.parent=parent;bone.use_connect=i>0;parent=bone
bpy.ops.object.mode_set(mode='OBJECT')
leaf.parent=rig
modifier=leaf.modifiers.new('Continuous page skin','ARMATURE');modifier.object=rig
groups=[leaf.vertex_groups.new(name=f'Page_{i:02d}') for i in range(segments+1)]
for vertex in leaf.data.vertices:
    coordinate=max(0,min(segments,vertex.co.x/width*segments))
    left=min(segments-1,math.floor(coordinate));weight=coordinate-left
    groups[left].add([vertex.index],1-weight,'REPLACE')
    if weight>0:groups[left+1].add([vertex.index],weight,'REPLACE')

def export(name,objects,types):
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:obj.hide_set(False);obj.select_set(True)
    bpy.context.view_layer.objects.active=objects[0]
    bpy.ops.export_scene.fbx(filepath=str(ROOT/'Export'/name),use_selection=True,
        object_types=types,axis_forward='-Y',axis_up='Z',apply_unit_scale=True,
        apply_scale_options='FBX_SCALE_ALL',mesh_smooth_type='FACE',use_tspace=False,
        bake_anim=False,add_leaf_bones=False,path_mode='STRIP')

export('SM_AlchemyManualBinding.fbx',[body],{'MESH'})
export('SK_BookLeafTemplate.fbx',[rig,leaf],{'MESH','ARMATURE'})
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'AlchemyManualPersistentLeaves.blend'))
(ROOT/'model-source.json').write_text(json.dumps(dict(source=str(SOURCE),
    leaf_vertices=len(leaf.data.vertices),chain_bones=segments+1,thickness_cm=.032,
    template='front RecipeRight / back RecipeLeft / edge M_BookPages',
    fixed_print_surfaces_removed=True,rendered=False),indent=2),encoding='utf-8')
print('PERSISTENT_BOOK_TEMPLATE_EXPORTED')
