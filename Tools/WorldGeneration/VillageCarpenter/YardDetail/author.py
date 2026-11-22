"""Export editable centimeter-scaled cluster meshes, physical surface UVs and three authored LODs."""
import json
import sys
from pathlib import Path
import bpy

here=Path(__file__).resolve().parent
sys.path.insert(0,str(here))
from geometry import SurfaceMesh
from debris import Deck, scatter
from timber import seasoning,crib,flitches
from layout import PLACEMENTS

out=here.parents[3]/'SourceAssets/HillsVillageCarpenter/YardDetail'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version=0
deck=Deck(out/'deck-contact.json')
builders={'SeasoningBoards':seasoning,'OffcutCrib':crib,'YardFlitches':flitches}
# Low stock uses simple boxes on the solid masses, leaving upper air free.
boxes={'SeasoningBoards':[((0,0,32),(236,73,42)),((0,0,6.5),(184,70,13))],
       'OffcutCrib':[((0,0,15),(94,54,30))],
       'YardFlitches':[((0,0,17),(190,79,31)),((0,0,39),(174,58,19))]}
manifest=[]
for i,key in enumerate(PLACEMENTS):
    name='SM_Carpenter'+key
    group=bpy.data.objects.new(name+'_LODs',None)
    group['fbx_type']='LodGroup'
    bpy.context.collection.objects.link(group)
    children=[]
    counts=[]
    for level in range(3):
        draft=SurfaceMesh(level)
        if key in builders: builders[key](draft)
        else: scatter(draft,key,deck)
        obj=draft.object(name+'_LOD'+str(level))
        obj.parent=group
        counts.append(sum(len(p.vertices)-2 for p in obj.data.polygons))
        obj.modifiers.new('Game triangulation','TRIANGULATE')
        children.append(obj)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in [group]+children: obj.select_set(True)
    fbx=out/(name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH','EMPTY'},
        axis_forward='-Y',axis_up='Z',mesh_smooth_type='FACE',use_tspace=True,
        bake_anim=False,use_custom_props=True,add_leaf_bones=False)
    manifest.append(dict(key=key,name=name,file=fbx.name,triangles=counts,boxes=boxes.get(key,[])))
    group.location=(i%3*3.4,i//3*2.2,0)
    for child in children[1:]:
        child.hide_set(True)
        child.hide_render=True
bpy.ops.wm.save_as_mainfile(filepath=str(out/'CarpenterYardDetail.blend'))
(out/'models.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
