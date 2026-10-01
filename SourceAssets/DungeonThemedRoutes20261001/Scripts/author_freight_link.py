"""Open the authored freight shutter, close its former side exit, retain the room."""
import copy,json,sys
from pathlib import Path
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1]
for folder in ('Authored','Config','Receipts','Backup'):(ROOT/folder).mkdir(parents=True,exist_ok=True)
source=PROJECT/'SourceAssets/DungeonVentFreight20260922/Scripts/author.py'
scope={'__file__':str(source),'__name__':'freight_route_library'}
exec(compile(source.read_text('utf-8').split("for index,room in enumerate(H['CFG']['rooms']):",1)[0],str(source),'exec'),scope)
h=scope['H'];room=copy.deepcopy(next(r for r in h['CFG']['rooms'] if r['id']=='FreightTransfer'))
room['id']='FreightWarehouseLink';room['origin_m']=[0,0,0];h['ROOM']=room;h['OUT']=ROOT/'Authored';h['GROUPS']={}
edges=list(zip(room['footprint'],room['footprint'][1:]+room['footprint'][:1]))
for edge,(a,b) in enumerate(edges):
    openings=[]
    for o in room['openings']:
        if o['edge']==edge and a[1]==0 and b[1]==0:openings.append(o)
    if a[1]==18 and b[1]==18:openings=[dict(center=9,width=4.65,height=3.74)]
    h['wall'](a,b,room['height_m'],openings)
# Preserve original interior bulkhead and columns belonging to the Shell group.
h['box']('Shell',(9,3.6,3.65),(10,.18,1.3),'Concrete')
for x,y in room['columns']:h['box']('Shell',(x,y,room['height_m']/2),(.32,.32,room['height_m']))
for a,b in room['beams']:h['bar']('Shell',a,b,.32,.32)
# A real descending throat adapts the 0.6 m loading dock to standard floor-zero ports.
for i in range(4):
    top=.60-.15*i;y=18+i*.30
    h['box']('Throat',(9,y+.15,(top-.20)/2),(4.65,.30,top+.20),'Concrete')
    h['box']('Throat',(9,y+.025,top+.004),(4.55,.045,.008),'BareSteel')
h['box']('Throat',(9,19.50,-.1),(3.34,.6,.2),'Concrete')
for sign in (-1,1):
    a=(9+sign*2.41,18,1.85);b=(9+sign*1.59,19.8,1.4)
    # Vertical side walls taper in plan, with a sloping top at the lintel.
    x0,x1=a[0],b[0];t=.09
    vs=[(x0-t,18,-.2),(x0+t,18,-.2),(x1+t,19.8,-.2),(x1-t,19.8,-.2),
        (x0-t,18,3.92),(x0+t,18,3.92),(x1+t,19.8,2.98),(x1-t,19.8,2.98)]
    h['poly']('Throat',vs,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],'Concrete')
vs=[(6.5,18,z) for z in (3.74,3.92)]+[(11.5,18,z) for z in (3.74,3.92)]+[(10.68,19.8,z) for z in (2.8,2.98)]+[(7.32,19.8,z) for z in (2.8,2.98)]
h['poly']('Throat',vs,[(0,2,4,6),(1,7,5,3),(0,1,3,2),(2,3,5,4),(4,5,7,6),(6,7,1,0)],'Concrete')
# Back-to-back box cover encloses the existing curtain's upward travel.
for x in (6.48,11.52):h['box']('ShutterHood',(x,17.69,5.24),(.08,.96,3.12),'PaintedSteel')
for y in (17.19,18.19):h['box']('ShutterHood',(9,y,5.24),(5.12,.06,3.12),'PaintedSteel')
h['box']('ShutterHood',(9,17.69,6.84),(5.12,1.06,.08),'PaintedSteel')
scope['freight_guardrails'](h)
h['export']()
# Use the existing precise shutter's split source, rather than a primitive door.
door_source=PROJECT/'SourceAssets/DungeonFreightDoor20260923/Scripts/door_geometry.py'
door_scope={'__file__':str(door_source),'__name__':'freight_split_library'}
exec(compile(door_source.read_text('utf-8').replace("'VAULT  01' if split else 'FREIGHT  02'","'FREIGHT  02'"),str(door_source),'exec'),door_scope)
h['GROUPS']={};door_scope['build'](h,split=True)
frame=door_scope['export_lift'](h,'DoorFrame','SM_ThemedFreight_DoorFrame')
leaf=door_scope['export_lift'](h,'DoorLeaf','SM_ThemedFreight_DoorLeaf')
origin=Vector((9,17.72,.6))
for v in leaf.data.vertices:v.co-=origin
bpy.ops.object.select_all(action='DESELECT');leaf.select_set(True);bpy.context.view_layer.objects.active=leaf
bpy.ops.export_scene.fbx(filepath=str(ROOT/'Authored/SM_ThemedFreight_DoorLeaf.fbx'),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False)
records=h['RECORDS']
for item in records:
    item['asset']='/Game/Dungeons/ThemedRoutes20261001/Meshes/'+item['name']
    item['nanite']=item['kind']!='DoorLeaf'
    item['collision']=item['kind'] not in ('DoorLeaf','Frames','ShutterHood')
    obj=bpy.data.objects[item['name']];item['triangles']=sum(len(p.vertices)-2 for p in obj.data.polygons)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authored/FreightWarehouseLink.blend'))
(ROOT/'Authored/manifest.json').write_text(json.dumps(dict(objects=records),indent=2),encoding='utf-8')
print('FREIGHT_LINK_AUTHORED',len(records),flush=True)
