"""Extract accepted station equipment from its saved mesh; do not remodel it."""
import json
from mathutils import Vector

def desktop(h):
    bpy,bmesh=h['bpy'],h['bmesh']
    root=h['PROJECT']/'SourceAssets/StationWorkshop20261003/RefineV2/Authored'
    source=next(i for i in json.loads((root/'manifest.json').read_text('utf8'))['objects'] if i['kind']=='DispatchElectronics')
    with bpy.data.libraries.load(str(root/'StationWorkshop_RefineV2.blend'),link=False) as (data,dest):
        dest.objects=['SM_SW_DispatchElectronics']
    ob=dest.objects[0];bpy.context.scene.collection.objects.link(ob)
    bm=bmesh.new();bm.from_mesh(ob.data)
    # Keep complete connected pieces for the monitor, stand, keyboard and mouse.
    # The telephone, PC and wall socket/cables remain part of the station assembly.
    seen=set();remove=[]
    for seed in bm.verts:
        if seed in seen:continue
        component=[];stack=[seed];seen.add(seed)
        while stack:
            v=stack.pop();component.append(v)
            for e in v.link_edges:
                q=e.other_vert(v)
                if q not in seen:seen.add(q);stack.append(q)
        if not all(5.66<=v.co.x<=6.39 and -1.065<=v.co.y<=-.51 and .772<=v.co.z<=1.28 for v in component):remove.extend(component)
    bmesh.ops.delete(bm,geom=remove,context='VERTS')
    for v in bm.verts:v.co-=Vector((5.95,-.60,.775))
    bm.to_mesh(ob.data);bm.free();ob.location=(0,0,0)
    ob.name='SM_Eco_StationDesktopReuse'
    # Retain original UVs, vertex colours, normals and material slots.
    bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
    path=h['OUT']/(ob.name+'.fbx')
    if ob.name in h['REUSED']:
        h['records'].append(dict(h['REUSED'][ob.name],reused=True))
        print('ECOLOGY_STATION_DESKTOP_RETAINED',flush=True)
        return
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False)
    h['records'].append(dict(name=ob.name,kind='StationDesktopReuse',room_id='Reusable',asset=h['MESHBASE']+'/Meshes/'+ob.name,
        fbx=str(path),materials=source['materials'],triangles=len(ob.data.polygons),collision=False,nanite=True,simple_collision_hulls=0,
        reused_source=source['asset'],extracted_without_remodeling=True))
    print('ECOLOGY_STATION_DESKTOP_REUSED',len(ob.data.polygons),flush=True)
