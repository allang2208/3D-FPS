"""Export three collision-ready clusters, their authored LODs and the editable Blender source."""
import json
import sys
from pathlib import Path
import bpy

here=Path(__file__).resolve().parent
sys.path[:0]=[str(here),str(here.parent),str(here.parent/'TradeSign'),str(here.parents[1]/'VillageCarpenter/YardDetail')]
from geometry import SurfaceMesh,PALETTE
from sign import boards,board_straps,fixed,chain
from forge import body,fuel

def panel(m):
    boards(m,weathered=True)
    board_straps(m)

out=here.parents[3]/'SourceAssets/HillsVillageBlacksmith20261117/ForgeR2'
PALETTE.update(Fireclay=(.19,.13,.09),Soot=(.09,.08,.066),HotCoal=(.17,.063,.023),Paint=(.36,.074,.036),Iron=(.096,.079,.071),Rubbed=(.19,.18,.16))
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version=0
items=[('SignBracketR2',fixed,[]),('SignLinksR2',chain,[]),('SignBoardR2',panel,[]),
       ('SideBlastHearth',body,[((10,1,38),(122,102,76)),((9,0,77),(138,108,11)),((4,43,119),(120,15,76))]),
       ('SideBlastFuel',fuel,[])]
rows=[]
for layout,(key,builder,boxes) in enumerate(items):
    name='SM_Smith'+key
    group=bpy.data.objects.new(name+'_LODs',None)
    group['fbx_type']='LodGroup'
    bpy.context.collection.objects.link(group)
    children=[];triangles=[]
    for index in range(3):
        draft=SurfaceMesh(index)
        builder(draft)
        # Put the origins at the two real contacts between the interlocking rings.
        shift={'SignLinksR2':4.2,'SignBoardR2':10.35}.get(key,0.)
        if shift:draft.verts=[(x,y,z+shift*.01) for x,y,z in draft.verts]
        obj=draft.object(name+'_LOD'+str(index))
        if key=='SideBlastFuel':
            col=obj.data.color_attributes.new(name='EmberHeat',type='FLOAT_COLOR',domain='CORNER')
            obj.data.color_attributes.active_color=col
            for loop in obj.data.loops:
                col.data[loop.index].color=draft.fuel_colors.get(loop.vertex_index,(0.,0.,0.,1.))
        obj.parent=group
        obj.modifiers.new('Export triangle mesh','TRIANGULATE')
        triangles.append(sum(len(p.vertices)-2 for p in obj.data.polygons))
        children.append(obj)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in [group]+children:obj.select_set(True)
    bpy.ops.export_scene.fbx(filepath=str(out/(name+'.fbx')),use_selection=True,object_types={'MESH','EMPTY'},
        axis_forward='-Y',axis_up='Z',mesh_smooth_type='FACE',use_tspace=True,bake_anim=False,
        use_custom_props=True,colors_type='LINEAR',add_leaf_bones=False)
    rows.append(dict(name=name,file=name+'.fbx',triangles=triangles,boxes=boxes))
    group.location.x=layout*1.65
    for obj in children[1:]:
        obj.hide_set(True)
        obj.hide_render=True
bpy.ops.wm.save_as_mainfile(filepath=str(out/'SmithSideBlastAndSuspension.blend'))
(out/'models.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
