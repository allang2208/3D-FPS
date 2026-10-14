"""Render repaired contact assemblies and measure the actual saved mesh seats."""
import bpy,json,sys,math
from pathlib import Path
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;X=O/'Repaired';out=O/'After';out.mkdir(exist_ok=True)
manifest=json.loads((X/'manifest.json').read_text());selected=sys.argv[sys.argv.index('--')+1].split(',') if '--' in sys.argv else None
report=json.loads((out/'contact-report.json').read_text()) if (out/'contact-report.json').exists() else {}
for key,e in manifest.items():
    if selected and e['family'] not in selected:continue
    bpy.ops.wm.open_mainfile(filepath=str(X/(key+'.blend')))
    parts=[ob for ob in bpy.context.scene.objects if ob.type=='MESH'];body=parts[0]
    old=json.loads((O/'Cache'/(e['family']+'-'+e['kind']+'.json')).read_text());h=json.loads((O/'Cache'/(key+'-host.json')).read_text())
    update=Matrix(e['canonical'])@Matrix(old['canonical']).inverted();hv=[update@Vector(v) for v in h['vertices']]
    # Measure mesh-to-surface distance on the actual repaired bearing vertices.
    # A rail's slots/openings are deliberately spanned; they are not contact lands.
    tree=BVHTree.FromPolygons([v.co for v in body.data.vertices],[list(p.vertices) for p in body.data.polygons]);distances=[]
    for p in e['bearing_points']:
        hit,normal,face,d=tree.find_nearest(Vector(p))
        if hit is not None:distances.append(d*1000)
    edge_counts={}
    pad_faces=[f for f in body.data.polygons if body.data.materials[f.material_index].name.startswith('Tactical_Fitted_Bearing')]
    for face in pad_faces:
        ids=list(face.vertices)
        for a,b in zip(ids,ids[1:]+ids[:1]):
            pair=tuple(sorted((a,b)));edge_counts[pair]=edge_counts.get(pair,0)+1
    open_edges=sum(n!=2 for n in edge_counts.values())
    report[key]={'bearing_samples':len(distances),'max_contact_distance_mm':max(distances) if distances else None,'open_bearing_edges':open_edges,'body_outward_mm':e['body_outward_mm'],'passed_contact':bool(distances) and max(distances)<.20 and open_edges==0}
    clay=bpy.data.materials.new('Host inspection clay');clay.diffuse_color=(.23,.31,.38,1)
    data=bpy.data.meshes.new('Current host');data.from_pydata(hv,[],h['faces']);data.update();host=bpy.data.objects.new('Current host',data);bpy.context.collection.objects.link(host);data.materials.append(clay)
    for ob in parts:
        for m in ob.data.materials:m.diffuse_color=(.65,.35,.10,1) if m.name.startswith(('Tactical_Fitted','Blessed')) or 'mount' in m.name.lower() else (.12,.13,.14,1)
    scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH';scene.render.resolution_x=720;scene.render.resolution_y=520;scene.render.resolution_percentage=100;scene.world=bpy.data.worlds.new('Mount review');scene.world.color=(.035,.035,.035)
    sh=scene.display.shading;sh.light='STUDIO';sh.color_type='MATERIAL';sh.show_shadows=True;sh.show_cavity=True;sh.cavity_type='BOTH';sh.show_specular_highlight=True;sh.background_type='WORLD';scene.view_settings.view_transform='Standard'
    camera=bpy.data.objects.new('Review camera',bpy.data.cameras.new('Review camera'));bpy.context.collection.objects.link(camera);scene.camera=camera
    center=Vector((-.045,0,.025));camera.location=center+Vector((-.11,-.24,.082));camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.type='ORTHO';camera.data.ortho_scale=.23 if e['family']=='M16' else .16
    scene.render.image_settings.file_format='PNG';scene.render.filepath=str(out/(key+'.png'));bpy.ops.render.render(write_still=True)
    (out/'contact-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('TACTICAL_REVIEW',key,report[key],flush=True)
if any(not row['passed_contact'] for row in report.values()):raise RuntimeError('One or more bearing contacts remain outside tolerance')
