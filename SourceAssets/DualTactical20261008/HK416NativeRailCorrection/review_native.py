"""Inspect source-shaped rail clamps and complete two-slot assemblies."""
import sys,json,bpy
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;sys.path.insert(0,str(O));import inspect_native as view
m=json.loads((O/'manifest.json').read_text());trees={};report={'pairs':{},'assemblies':{}}
for key,e in m.items():
    bpy.ops.wm.open_mainfile(filepath=str(O/'Editable'/(key+'.blend')))
    ob=next(o for o in bpy.context.scene.objects if o.type=='MESH')
    trees[key]=BVHTree.FromPolygons([v.co.copy() for v in ob.data.vertices],[list(p.vertices) for p in ob.data.polygons])
    bounds=[[float(f(v.co[i] for v in ob.data.vertices)) for i in range(3)] for f in (min,max)]
    report['assemblies'][key]={'bounds_gun_m':bounds,'added_bridge_count':e['generated_connector_count'],'native_clamp':e['native_clamp']}
    for mat in ob.data.materials:mat.diffuse_color=(.56,.48,.29,1)
    if '--metrics' not in sys.argv:
        view.load('host',host=True);view.render('corrected-'+e['kind']+'-'+str(e['side']),1 if e['side']==1 else -1)
for a in ('laser','flashlight','blessed_laser'):
    for b in ('laser','flashlight','blessed_laser'):
        one=f'HK416-{a}-1';two=f'HK416-{b}-2';hits=trees[one].overlap(trees[two]);report['pairs'][a+' + '+b]=len(hits)
for second in (() if '--metrics' in sys.argv else ('laser','flashlight')):
    bpy.ops.wm.open_mainfile(filepath=str(O/'Editable/HK416-laser-1.blend'))
    first=next(o for o in bpy.context.scene.objects if o.type=='MESH')
    with bpy.data.libraries.load(str(O/'Editable'/f'HK416-{second}-2.blend'),link=False) as (src,dst):dst.objects=[f'SM_{second}_2']
    ob=dst.objects[0];bpy.context.collection.objects.link(ob)
    for mat in first.data.materials:mat.diffuse_color=(.56,.48,.29,1)
    for mat in ob.data.materials:mat.diffuse_color=(.25,.54,.50,1)
    view.load('host',host=True);view.render('dual-laser-and-'+second,1)
    s=bpy.context.scene;c=s.camera;center=Vector((0,.21,.08));c.location=center+Vector((0,-.35,.52));c.rotation_euler=(center-c.location).to_track_quat('-Z','Y').to_euler();s.render.filepath=str(O/'Review'/('dual-laser-and-'+second+'-top.png'));bpy.ops.render.render(write_still=True)
(O/'review-report.json').write_text(json.dumps(report,indent=2));print('PAIR_INTERSECTIONS',json.dumps(report['pairs']))
