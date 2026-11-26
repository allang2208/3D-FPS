"""Convert Meshy Y-up references into centimetre-controlled chapel components."""
import bpy
import numpy as np
from pathlib import Path
from mathutils import Matrix

PROJECT = Path(__file__).resolve().parents[3]
SOURCE = PROJECT / 'SourceAssets/TemperateHillsOldChapel/Concept01'
OUT = SOURCE / 'Authored'
OUT.mkdir(exist_ok=True)
SIZES = {'Bellcote':(300,70,260), 'Bell':(94,56,76), 'Portal':(228,52,335),
         'Door':(146,8,263), 'Lancet':(96,56,212), 'Buttress':(72,100,332),
         'Pew':(210,52,88), 'Altar':(205,78,98), 'Font':(78,78,106),
         'Lectern':(54,46,116), 'Headstone':(54,16,86)}

def export(obj, name):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.export_scene.fbx(filepath=str(OUT / ('SM_Chapel'+name+'.fbx')),use_selection=True,
        object_types={'MESH'},axis_forward='-Y',axis_up='Z',use_tspace=True,
        mesh_smooth_type='FACE',bake_anim=False,add_leaf_bones=False,path_mode='STRIP')

for folder in sorted((SOURCE/'Meshy').glob('[0-9]*')):
    role = folder.name.split('_',1)[1]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(folder/'downloads/model_urls_glb.glb'))
    objects = [o for o in bpy.context.scene.objects if o.type=='MESH']
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:
        world = obj.matrix_world.copy()
        obj.parent = None
        obj.matrix_world = world
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    if len(objects)>1: bpy.ops.object.join()
    obj=objects[0]
    obj.data.transform(obj.matrix_world)
    obj.matrix_world=Matrix.Identity(4)
    mesh=obj.data
    vertices=np.empty(len(mesh.vertices)*3,dtype=np.float32)
    mesh.vertices.foreach_get('co',vertices)
    coords=vertices.reshape(-1,3)
    # The buttress's long graduated projection is on its source X axis.
    if role=='Buttress':
        coords=coords[:,[1,0,2]].copy()
        coords[:,0]*=-1
    lo=coords.min(axis=0);hi=coords.max(axis=0)
    q=(coords-lo)/(hi-lo)
    width,depth,height=SIZES[role]
    w=(q[:,0]-.5)*width
    z=q[:,2]*height
    # Tie the surveyed reveal (as opposed to its outer bounds) to the jambs and spring.
    if role in ('Portal','Lancet'):
        fraction,opening,sill,spring,peak = ((.286,148,0,196,265) if role=='Portal' else (.225,54,20,135,184))
        t=q[:,0]-.5
        w=np.sign(t)*np.interp(np.abs(t),[0,fraction,.5],[0,opening/2,width/2])
        z=np.interp(q[:,2],[0,.12,.57 if role=='Portal' else .64,.825 if role=='Portal' else .853,1],
                    [0,40 if role=='Portal' else sill,spring,peak,height])
    if role=='Bellcote':
        t=q[:,0]-.5
        w=np.sign(t)*np.interp(np.abs(t),[0,.06,.29,.5],[0,25,115,150])
    if role=='Door':
        # Match the door tip and spring to the corrected stone opening.
        z=np.interp(q[:,2],[0,.64,1],[0,193,263])
    d=(q[:,1]-.5)*depth
    # FBX export/UE Y reflection. All fronts look toward -X in UE.
    coords=np.stack((d,-w,z),axis=1)*.01
    mesh.vertices.foreach_set('co',np.ascontiguousarray(coords,dtype=np.float32).ravel())
    mesh.update()
    # Custom loop normals came from a differently oriented and non-uniformly scaled mesh.
    if mesh.has_custom_normals:
        bpy.ops.mesh.customdata_custom_splitnormals_clear()
    mesh.materials.clear()
    mesh.materials.append(bpy.data.materials.new('Chapel'+role))
    obj.name='SM_Chapel'+role
    export(obj,role)
    print('CHAPEL_EXPORTED',role,flush=True)

