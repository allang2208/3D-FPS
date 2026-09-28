"""Background authoring: a single curved ocean shell; no collision or render."""
import math,json,runpy
from pathlib import Path
import bpy
ROOT=Path(__file__).parent
OUT=ROOT/'Exported'

def author():
    OUT.mkdir(parents=True,exist_ok=True)
    # Regular 31.25 m cells resolve the scaled fountain spectrum below the hub. Its
    # displacement fades before this grid joins the coarse circular far shell.
    runpy.run_path(str(ROOT/'build_reused_ocean_spectrum.py'))['build']()
    planet=6360000.; sea=-1500.; n=256; half=4000.
    verts=[];faces=[]
    def point(x,y):return (x,y,sea+math.sqrt(planet*planet-x*x-y*y)-planet)
    for j in range(n+1):
        for i in range(n+1):verts.append(point(-half+2*half*i/n,-half+2*half*j/n))
    for j in range(n):
        for i in range(n):
            a=j*(n+1)+i;faces.append((a,a+1,a+n+2,a+n+1))
    # CCW square perimeter becomes circular at 6 km, sharing the same vertices.
    boundary=list(range(n+1))+[j*(n+1)+n for j in range(1,n+1)]+[n*(n+1)+i for i in range(n-1,-1,-1)]+[j*(n+1) for j in range(n-1,0,-1)]
    directions=[(verts[i][0]/math.hypot(verts[i][0],verts[i][1]),verts[i][1]/math.hypot(verts[i][0],verts[i][1])) for i in boundary]
    previous=boundary
    for radius in [6000,8000,10000,12000,17000,22000,28000,36000,46000,58000,72000,88000,106000,126000,148000,172000,198000,220000]:
        ring=[]
        for x,y in directions:ring.append(len(verts));verts.append(point(x*radius,y*radius))
        for j in range(len(ring)):
            q=(j+1)%len(ring);faces.append((previous[j],ring[j],ring[q],previous[q]))
        previous=ring
    mesh=bpy.data.meshes.new('GodSpaceOcean_CurvedShell');mesh.from_pydata(verts,[],faces);mesh.update()
    for name in ['OceanNear','OceanFar']:mesh.materials.append(bpy.data.materials.get(name) or bpy.data.materials.new(name))
    uv=mesh.uv_layers.new(name='OceanUV')
    for loop in mesh.loops:
        p=mesh.vertices[loop.vertex_index].co;uv.data[loop.index].uv=(p.x/256,p.y/256)
    for p in mesh.polygons:
        p.use_smooth=True
        # Both sections use the same DefaultLit reflection/fog response. The
        # wide irregular detail transition finishes before this boundary.
        p.material_index=1 if p.center.xy.length>12000 else 0
    obj=bpy.data.objects.new('SM_GodSpaceDistantOcean',mesh);bpy.context.scene.collection.objects.link(obj)
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    bpy.ops.export_scene.fbx(filepath=str(OUT/'SM_GodSpaceDistantOcean.fbx'),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',add_leaf_bones=False)
    report=dict(name=obj.name,file=str(OUT/'SM_GodSpaceDistantOcean.fbx'),materials=['OceanNear','OceanFar'],vertices=len(verts),triangles=sum(len(p)-2 for p in faces),outer_radius_m=220000,near_radius_m=12000,transition_m=[1800,12000],regular_grid_cell_m=2*half/n,displacement_fade_m=[2200,3800],sea_level_m=sea,planet_radius_m=planet,collision=False,tick=False,rendered=False)
    (ROOT/'Receipts/ocean-authored.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    bpy.data.objects.remove(obj,do_unlink=True)
    return report

if __name__=='__main__':
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=1
    result=author()
    data_path=ROOT/'placements.json';data=json.loads(data_path.read_text(encoding='utf8'))
    data['new_meshes']=[m for m in data['new_meshes'] if m['name'] not in ['SM_GodSpaceDistantEarth','SM_GodSpaceDistantOcean']]+[result]
    data.update(cloud_bottom_km=.62,cloud_height_km=.70,atmosphere_ground_z_cm=-150000)
    data_path.write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding='utf8')
    print('GODSPACE_OCEAN_AUTHORED '+json.dumps(result))
