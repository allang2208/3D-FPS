"""Author UE-ready geometry and placements from the accepted Blender layout, without rendering."""
import bpy, json, math
import numpy as np
from pathlib import Path
from mathutils import Vector, Matrix

ROOT=Path(__file__).parent
SOURCE=ROOT.parent
OUT=ROOT/'Exported'
OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE/'GodSpace_Layout_V1.blend'))
scene=bpy.context.scene
scene.unit_settings.system='METRIC'
scene.unit_settings.scale_length=1
exports=json.loads((SOURCE/'exported_meshes.json').read_text(encoding='utf8'))
assets={Path(x['file']).stem:x for x in exports}
library={bpy.data.objects['LIB_'+key].data.name:key for key in assets}
placements=[]
structure=[]
core=[]
terrain=bpy.data.objects['NEW remote earth backdrop']

# The original player-built service facilities remain at their existing world
# coordinates. This XY translation puts them inside the new east service court.
WORLD_OFFSET_CM=[-2400,-1300,0]
for o in list(scene.objects):
    if o.type!='MESH' or o.hide_render: continue
    if o.data.name in library:
        key=library[o.data.name]
        if key in ['SM_GamedevPortal_Frame','SM_BlastFurnace','SM_CastingStation','SM_WarehouseCrate_T1_Wood_v2']: continue
        placements.append(dict(label=o.name,mesh=assets[key]['mesh'],location_m=list(o.location),yaw=math.degrees(o.rotation_euler.z),scale=list(o.scale)))
        continue
    name=o.name.lower()
    if o==terrain or 'cloud' in name or 'portal energy' in name or 'reserved future' in name: continue
    if name.startswith('new portal pad'):
        # Keep only the retained hills portal pad, at local (+22,-29).
        if abs(o.location.x-22)>1 or abs(o.location.y+29)>1: continue
    if any(slot.material and 'water' in slot.material.name.lower() for slot in o.material_slots): continue
    if 'deity core' in name or 'orbit ring' in name:
        core.append(o)
    else:
        if name=='workshop courtyard':
            o.location.x=20
            o.dimensions.x=28
            # Existing buildables rest at Z=20 cm. Keep this inset flush below them.
            o.location.z=.18
            o.dimensions.z=.02
        structure.append(o)

# An accessible side ramp joins the altar terrace while the front keeps its steps.
verts=[(9,18,.2),(12,18,.2),(12,32,.2),(9,32,.2),(9,18,.2),(12,18,.2),(12,32,1.1),(9,32,1.1)]
faces=[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
me=bpy.data.meshes.new('Altar side access ramp');me.from_pydata(verts,[],faces);me.update()
ramp=bpy.data.objects.new('Altar side access ramp',me);scene.collection.objects.link(ramp)
me.materials.append(bpy.data.materials['Preview white marble - simplified UE material']);structure.append(ramp)

def export_combined(objects,name):
    bpy.ops.object.select_all(action='DESELECT')
    copies=[]
    for src in objects:
        o=src.copy();o.data=src.data.copy();scene.collection.objects.link(o)
        o.hide_render=False;o.hide_viewport=False;o.hide_set(False)
        o.select_set(True);copies.append(o)
    bpy.context.view_layer.objects.active=copies[0]
    bpy.ops.object.convert(target='MESH')
    bpy.ops.object.join()
    o=bpy.context.object;o.name=name
    # Bake the assembly at local (0,0,0), ensuring the FBX pivot matches placement.
    o.data.transform(o.matrix_world);o.matrix_world=Matrix.Identity(4)
    uv=o.data.uv_layers.new(name='SurfaceUV')
    for poly in o.data.polygons:
        axis=max(range(3),key=lambda k:abs(poly.normal[k]))
        axes=[k for k in range(3) if k!=axis]
        for li in poly.loop_indices:
            co=o.data.vertices[o.data.loops[li].vertex_index].co
            uv.data[li].uv=(co[axes[0]]*.5,co[axes[1]]*.5)
    # Reflect Y in the export copy; UE's handedness conversion reflects it back.
    # Existing UE meshes are placed from their own centimeter-space bounding boxes.
    o.data.transform(Matrix.Diagonal((1,-1,1,1)))
    for p in o.data.polygons: p.flip()
    if name=='SM_GodSpaceStructure':
        import runpy
        runpy.run_path(str(ROOT/'refine_floor_trim.py'))['refine_structure'](o)
    bpy.ops.export_scene.fbx(filepath=str(OUT/(name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',add_leaf_bones=False)
    result=dict(name=name,file=str(OUT/(name+'.fbx')),materials=[m.name if m else '' for m in o.data.materials],vertices=len(o.data.vertices),triangles=sum(len(p.vertices)-2 for p in o.data.polygons))
    bpy.data.objects.remove(o,do_unlink=True)
    return result

records=[export_combined(structure,'SM_GodSpaceStructure'),export_combined(core,'SM_GodSpaceCore')]
# The accepted below-hub backdrop is now a visual-only curved ocean.
import runpy
ocean_author=runpy.run_path(str(ROOT/'author_distant_ocean.py'))
records.append(ocean_author['author']())
(ROOT/'placements.json').write_text(json.dumps(dict(world_offset_cm=WORLD_OFFSET_CM,placements=placements,new_meshes=records,portal_local_m=[22,-29,.5],warehouse_world_cm=[500,-500,20],cloud_bottom_km=.62,cloud_height_km=.70,atmosphere_ground_z_cm=-150000,retired_maps=['/Game/Clearwater/L_ClearwaterWater','/Game/GameMaps/L_GrassDeformDenseTest']),ensure_ascii=False,indent=2),encoding='utf8')
print('GODSPACE_GEOMETRY_EXPORTED '+json.dumps({'placements':len(placements),'meshes':records},ensure_ascii=False))
