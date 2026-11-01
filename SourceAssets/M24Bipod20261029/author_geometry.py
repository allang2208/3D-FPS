"""Reuse the PKM split bipod; fit its clamp and shorten the legs for M24."""
import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).resolve().parent;E=O/'Exports';E.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'PKMLowpoly20260922/Bipod26/PKM_Bipod_Editable.blend'),use_scripts=False)
src=json.loads((O.parent/'PKMLowpoly20260922/Bipod26/authoring.json').read_text())
hinge=Vector(src['hinge_root_m']);target=Vector((0,.45,.022));scale=.8
# PKM forward is -Y, M24 forward is +Y in the authoring frame.
turn=Matrix.Rotation(math.pi,3,'Z');parts={};report={'source':'PKMLowpoly20260922/Bipod26','scale':scale,'hinge_cm':[0,-45,2.2],'parts':{}}
for key in ('Base','LegA','LegB'):
    obs=[o for o in bpy.data.objects if o.name.startswith('PKM26_'+key+'_')]
    pivot=Vector(src['parts'][key]['pivot_root_m'])
    # Widen the barrel collar only; the inherited pin and leg roots stay matched.
    pivot.x*=2.8
    mounted=target+turn@(pivot-hinge)*scale if key!='Base' else Vector()
    out=[]
    for ob in obs:
        mesh=ob.data.copy()
        for v in mesh.vertices:
            if key=='Base':
                p=v.co-hinge;p.x*=2.8;p.z*=1.2
                # The PKM collar is too broad fore/aft for the M24's hand space.
                # Narrow only its mounting strap; retain the transverse pin.
                if ob.name.endswith('_72'):p.y*=.45
                v.co=target+turn@p*scale
            else:v.co=turn@v.co*scale
        mesh.update();obj=bpy.data.objects.new('M24Bipod_'+key+'_'+ob.name.split('_')[-1],mesh)
        bpy.context.scene.collection.objects.link(obj);out.append(obj)
    bpy.ops.object.select_all(action='DESELECT')
    for o in out:o.select_set(True)
    bpy.context.view_layer.objects.active=out[0]
    bpy.ops.export_scene.fbx(filepath=str(E/('SM_M24_Bipod_'+key+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
    for o in out:o.location=mounted
    parts[key]=out
    report['parts'][key]={'pivot_cm':[mounted.x*100,-mounted.y*100,mounted.z*100],'materials':[m.name for o in out for m in o.data.materials if m]}
for o in bpy.context.scene.objects:
    o.hide_render=not o.name.startswith('M24Bipod_')
    if o.name in bpy.context.view_layer.objects:o.hide_set(not o.name.startswith('M24Bipod_'))
report['tips_cm']=[[-5.234397575*scale,-.514067337*scale,-29.212138057*scale],[5.234399438*scale,-.514068082*scale,-29.212146997*scale]]
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(O/'M24_Bipod_Editable.blend'))
(O/'geometry.json').write_text(json.dumps(report,indent=2));print('M24_BIPOD_GEOMETRY_AUTHORED',json.dumps(report),flush=True)
