"""Author the editable Blender scene and engine LOD groups for the indoor fittings."""
import json
import sys
from math import cos, sin, pi
from pathlib import Path
import bpy

here=Path(__file__).resolve().parent
sys.path[:0]=[str(here),str(here.parent/'YardDetail')]
from models import Model, BUILDERS

out=here.parents[3]/'SourceAssets/HillsVillageCarpenter/InteriorR1'
out.mkdir(exist_ok=True,parents=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version=0


def collision(key):
    if key=='WashBarrel':
        # Hollow walls: radial collision strips leave the water exposed from above.
        walls=[((0,0,2),(42,42,4),0)]
        for i in range(16):
            a=2*pi*i/16
            for r,z,h in ((25.5,9,18),(28.5,44.5,53)):
                walls.append(((r*cos(a),r*sin(a),z),(3.9,r*.42,h),i*360/16))
        return walls
    if key=='StackedCases':return [((0,0,17.6),(69,48,35.2),-3),((4,1,46.2),(48,34,22),7)]
    if key=='JoinersChest':
        return [((0,0,2.5),(74,47,5),0),((0,-22.4,18.5),(73,4.5,34),0),
                ((0,22.4,18.5),(73,4.5,34),0),((-35.3,0,18.5),(4,43,34),0),((35.3,0,18.5),(4,43,34),0)]
    if key=='JoinersChestLid':return [((0,-24,1.5),(75,48,4),0)]
    return []


rows=[]
for index,(key,create) in enumerate(BUILDERS.items()):
    name='SM_Carpenter'+key
    group=bpy.data.objects.new(name+'_LODs',None)
    group['fbx_type']='LodGroup'
    bpy.context.collection.objects.link(group)
    children=[]
    tris=[]
    levels=1 if key=='WashWater' else 3
    for n in range(levels):
        draft=Model(n)
        create(draft)
        obj=draft.object(name+'_LOD'+str(n))
        obj.parent=group
        tris.append(sum(len(p.vertices)-2 for p in obj.data.polygons))
        obj.modifiers.new('Game triangulation','TRIANGULATE')
        children.append(obj)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in [group,*children]:obj.select_set(True)
    file=out/(name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'MESH','EMPTY'},
        axis_forward='-Y',axis_up='Z',mesh_smooth_type='FACE',use_tspace=True,
        bake_anim=False,use_custom_props=True,add_leaf_bones=False)
    rows.append(dict(key=key,name=name,file=file.name,triangles=tris,boxes=collision(key)))
    group.location=((index%3)*1.3,(index//3)*1.25,0)
    for lod in children[1:]:
        lod.hide_set(True)
        lod.hide_render=True
bpy.ops.wm.save_as_mainfile(filepath=str(out/'CarpenterInterior.blend'))
(out/'models.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
