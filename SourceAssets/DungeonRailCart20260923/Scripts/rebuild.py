"""Rebuild four installed mesh groups in place, retaining the surrounding assemblies."""
import json
import re
import shutil
import sys
from pathlib import Path
import bpy

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT.parent
sys.path.insert(0, str(ROOT/'Scripts'))
from rail_geometry import corridor

for folder in ('Authored', 'Sources', 'Receipts'):
    (ROOT/folder).mkdir(parents=True, exist_ok=True)
FREIGHT = ASSETS/'DungeonVentFreight20260922'
CORRIDOR = ASSETS/'DungeonAtmosphereV2_20260921'
freight_blend = FREIGHT/'Authored/Dungeon_VentFreight.blend'
corridor_blend = CORRIDOR/'Authored/DungeonAtmosphereV2_Structure.blend'
freight_manifest = FREIGHT/'Authored/manifest.json'
corridor_manifest = CORRIDOR/'Authored/structure-manifest.json'
kinds = ('Dock', 'Frames', 'Props')
names = ['SM_RS_FreightTransfer_'+k for k in kinds]
corridor_name = 'SM_V2_EndStairRails'

for source in (freight_blend, corridor_blend, freight_manifest, corridor_manifest,
    *(FREIGHT/'Authored'/(name+'.fbx') for name in names),
    CORRIDOR/'Authored'/(corridor_name+'.fbx')):
    target = ROOT/'Sources'/source.parent.parent.name/source.name
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        shutil.copy2(source, target)

source = FREIGHT/'Scripts/author.py'
scope = {'__file__':str(source), '__name__':'freight_partial_rebuild'}
exec(compile(source.read_text(encoding='utf-8').split("for index,room in enumerate(H['CFG']['rooms']):",1)[0],str(source),'exec'),scope)
h = scope['H']
room = next(r for r in h['CFG']['rooms'] if r['id']=='FreightTransfer')
h['ROOM'] = room
h['R'] = scope['random'].Random(h['CFG']['seed']+1)
scope['freight']()
# Door jambs and skirting share the Frames asset; retain them during its rebuild.
for edge,(a,b) in enumerate(zip(room['footprint'],room['footprint'][1:]+room['footprint'][:1])):
    h['wall'](a,b,room['height_m'],[o for o in room['openings'] if o['edge']==edge])
h['GROUPS'] = {k:v for k,v in h['GROUPS'].items() if k in kinds}
h['export']()
records = list(h['RECORDS'])

# Apply small physical arrises to the cart channels, plates and cast pump body.
# Frames already receives the existing structural bevel in the shared exporter.
props = bpy.data.objects['SM_RS_FreightTransfer_Props']
bpy.context.view_layer.objects.active=props
bpy.ops.object.select_all(action='DESELECT');props.select_set(True)
bevel=props.modifiers.new('Pallet jack machined edges','BEVEL')
bevel.width=.0015;bevel.segments=2;bevel.limit_method='ANGLE';bevel.angle_limit=.65
bpy.ops.object.modifier_apply(modifier=bevel.name)
tri=props.modifiers.new('Finished triangles','TRIANGULATE')
bpy.ops.object.modifier_apply(modifier=tri.name)
# Export in local space; the source assembly origin is restored immediately.
origin=props.location.copy();props.location=(0,0,0)
bpy.ops.export_scene.fbx(filepath=str(FREIGHT/'Authored'/(props.name+'.fbx')),
    use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',
    bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False)
props.location=origin
replacement=ROOT/'Authored/FreightReplacements.blend'
bpy.data.libraries.write(str(replacement),{bpy.data.objects[n] for n in names})

# Use the same fitted rail geometry for the original corridor. Preserve V2 slot names.
h['GROUPS']={};corridor(h)
g=h['GROUPS']['EndStairRails']
old_manifest=json.loads(corridor_manifest.read_text(encoding='utf-8'))
old_record=next(r for r in old_manifest['objects'] if r['name']==corridor_name)
mesh=bpy.data.meshes.new(corridor_name);mesh.from_pydata(g['v'],[],g['f']);mesh.update()
obj=bpy.data.objects.new(corridor_name,mesh);bpy.context.scene.collection.objects.link(obj)
palette=old_record['materials']
for name in palette:
    mesh.materials.append(bpy.data.materials.new('V2_'+name))
uv=mesh.uv_layers.new(name='UVMap')
for face,mat,authored,smooth in zip(mesh.polygons,g['m'],g['uv'],g['smooth']):
    face.material_index=palette.index(mat);face.use_smooth=smooth
    axis=max(range(3),key=lambda i:abs(face.normal[i]));dims=[i for i in range(3) if i!=axis]
    for corner,li in enumerate(face.loop_indices):
        co=mesh.vertices[mesh.loops[li].vertex_index].co
        uv.data[li].uv=authored[corner] if authored is not None else (co[dims[0]]/2,co[dims[1]]/2)
bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
bevel=obj.modifiers.new('Base plate arrises','BEVEL');bevel.width=.001;bevel.segments=2
bevel.limit_method='ANGLE';bevel.angle_limit=.65
bpy.ops.object.modifier_apply(modifier=bevel.name)
tri=obj.modifiers.new('Export triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=tri.name)
bpy.ops.export_scene.fbx(filepath=old_record['fbx'],use_selection=True,object_types={'MESH'},
    axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False)
corridor_replacement=ROOT/'Authored/CorridorReplacement.blend'
bpy.data.libraries.write(str(corridor_replacement),{obj})

def merge_source(blend, replacement, names):
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    for name in names:
        previous=bpy.data.objects.get(name)
        if previous is None:
            raise RuntimeError('Missing source object '+name)
        bpy.data.objects.remove(previous,do_unlink=True)
    with bpy.data.libraries.load(str(replacement),link=False) as (src,dst):
        dst.objects=list(names)
    for obj in dst.objects:
        bpy.context.scene.collection.objects.link(obj)
        for slot in obj.material_slots:
            key=re.sub(r'\.\d{3}$','',slot.material.name)
            if key in bpy.data.materials:
                slot.material=bpy.data.materials[key]
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))

merge_source(freight_blend,replacement,names)
merge_source(corridor_blend,corridor_replacement,[corridor_name])
manifest=json.loads(freight_manifest.read_text(encoding='utf-8'))
updates={r['name']:r for r in records}
manifest['objects']=[updates.get(r['name'],r) for r in manifest['objects']]
freight_manifest.write_text(json.dumps(manifest,indent=2),encoding='utf-8')
items=[dict(r,asset='/Game/Dungeons/VentFreight20260922/Meshes/'+r['name']) for r in records]
items.append(dict(old_record,asset='/Game/Dungeons/AtmosphereV2/Structure/'+corridor_name,
    materials={'V2_'+n:'/Game/Dungeons/AtmosphereV2/Materials/M_'+n for n in palette}))
(ROOT/'Authored/manifest.json').write_text(json.dumps({'objects':items},indent=2),encoding='utf-8')
receipt=dict(stage='authored',meshes=[r['asset'] for r in items],
    sources=[str(freight_blend),str(corridor_blend)],tests_run=False,rendered=False)
(ROOT/'Receipts/authoring.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('RAIL_CART_AUTHORED',json.dumps(receipt),flush=True)
