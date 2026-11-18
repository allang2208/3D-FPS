"""Read the owned source scans in an isolated background Blender process."""
import bpy, json
from pathlib import Path
from mathutils import Vector

ROOT = Path('D:/FPS3D')
OUT = ROOT/'FPSGAME/SourceAssets/HillsLandscapeRepair20261117/ScanInspection'
OUT.mkdir(parents=True, exist_ok=True)
report=[]
for folder in ('Quarry_Cliff-5c019f10','Quarry_Cliff-9caa4be4'):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    source=next((ROOT/'VaultCache/FabLibrary'/folder/'Extracted').glob('*.fbx'))
    bpy.ops.import_scene.fbx(filepath=str(source))
    objects=[o for o in bpy.context.scene.objects if o.type=='MESH']
    row={'source':str(source),'objects':[]}
    points=[]
    for o in objects:
        verts=[o.matrix_world@v.co for v in o.data.vertices];points+=verts
        parent=list(range(len(verts)))
        def root(i):
            while parent[i]!=i:
                parent[i]=parent[parent[i]];i=parent[i]
            return i
        for edge in o.data.edges:
            a,b=map(root,edge.vertices);parent[a]=b
        groups={}
        for i,v in enumerate(verts):groups.setdefault(root(i),[]).append(v)
        def bounds(vs):return [[min(v[i] for v in vs) for i in range(3)],[max(v[i] for v in vs) for i in range(3)]]
        edges={}
        for face in o.data.polygons:
            for edge in face.edge_keys:edges[edge]=edges.get(edge,0)+1
        row['objects'].append({'name':o.name,'vertices':len(verts),'bounds':bounds(verts),
            'open_boundary_edges':sum(n==1 for n in edges.values()),
            'boundary_bounds':bounds([verts[i] for edge,n in edges.items() if n==1 for i in edge]),
            'uv_layers':[{'name':uv.name,'min':[min(v.uv[i] for v in uv.data) for i in range(2)],'max':[max(v.uv[i] for v in uv.data) for i in range(2)]} for uv in o.data.uv_layers],
            'islands':[{'vertices':len(vs),'bounds':bounds(vs)} for vs in sorted(groups.values(),key=len,reverse=True)[:12]]})
        o.color=(.48,.46,.42,1)
    lo=Vector([min(v[i] for v in points) for i in range(3)])
    hi=Vector([max(v[i] for v in points) for i in range(3)])
    center=(lo+hi)/2;span=max(hi-lo)
    bpy.ops.object.camera_add(location=center+Vector((1.5,-2,1))*span)
    camera=bpy.context.object;camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
    camera.data.type='ORTHO';camera.data.ortho_scale=span*1.5
    scene=bpy.context.scene;scene.camera=camera;scene.render.engine='BLENDER_WORKBENCH'
    scene.display.shading.light='STUDIO';scene.display.shading.color_type='OBJECT'
    scene.display.shading.show_shadows=True;scene.display.shading.show_cavity=True
    scene.display.shading.cavity_type='BOTH';scene.display.shading.background_type='WORLD'
    scene.world=bpy.data.worlds.new('Inspection');scene.world.color=(.12,.12,.12)
    scene.render.resolution_x=1000;scene.render.resolution_y=800;scene.render.resolution_percentage=100
    scene.render.filepath=str(OUT/(folder+'.png'));bpy.ops.render.render(write_still=True)
    report.append(row)
(OUT/'geometry.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
