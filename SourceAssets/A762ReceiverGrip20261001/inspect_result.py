import bpy,bmesh,json,sys
from pathlib import Path
import numpy as np
from mathutils import Vector
O=Path(__file__).parent;sys.path.insert(0,str(O));import geometry as G
bpy.ops.wm.open_mainfile(filepath=str(O/'A762_ReceiverGrip08.blend'))
production=[ob for ob in bpy.context.scene.objects if ob.type=='MESH'];report={'new_parts':{},'runtime_tested':False}
for ob in production:
    bm=bmesh.new();bm.from_mesh(ob.data)
    report['new_parts'][ob.name]={'boundary_edges':sum(e.is_boundary for e in bm.edges),'nonmanifold_edges':sum(not e.is_manifold and not e.is_boundary for e in bm.edges),
        'zero_area_faces':sum(f.calc_area()<1e-15 for f in bm.faces),'triangles':len(ob.data.loop_triangles),'retained_source':ob.name.endswith('_RetainedGrip')}
    bm.free()
h,raw,p,t,m,uv,n,bone=G.body();plan=json.loads((O/'authoring.json').read_text());keep=np.ones(len(t),bool);keep[plan['Body']['delete_triangles']]=False
for sid,name in enumerate(h['slots']):
    if any(s in (h['materials'][sid] or '') for s in ('Manny','BarePalm','BareNative','BareFamily')):continue
    sel=(m==sid)&keep
    if not sel.any():continue
    vi,inv=np.unique(t[sel],return_inverse=True);mesh=bpy.data.meshes.new('Retained_'+name);mesh.from_pydata(p[vi].tolist(),[],inv.reshape(-1,3).tolist());mesh.update()
    ob=bpy.data.objects.new('Retained_'+name,mesh);bpy.context.collection.objects.link(ob)
    for f in mesh.polygons:f.use_smooth=True
    mesh.normals_split_custom_set(n[sel].reshape(-1,3).tolist())
    mat=bpy.data.materials.new('Render_'+name);mat.diffuse_color=(.48,.5,.52,1);mesh.materials.append(mat)
scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH';scene.world=bpy.data.worlds.new('World');scene.world.color=(.085,.085,.085)
s=scene.display.shading;s.light='STUDIO';s.studiolight_rotate_z=.3;s.color_type='MATERIAL';s.show_shadows=True;s.show_cavity=True;s.cavity_type='BOTH';s.curvature_ridge_factor=1.;s.curvature_valley_factor=1.;s.background_type='WORLD'
scene.render.resolution_x=1400;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
data=bpy.data.cameras.new('Camera');camera=bpy.data.objects.new('Camera',data);scene.collection.objects.link(camera);scene.camera=camera;data.type='ORTHO'
def render(label,loc,target=(0,-.055,.015),scale=.34):
    camera.location=loc;camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler();data.ortho_scale=scale
    scene.render.filepath=str(O/'Inspection'/(label+'.png'));bpy.ops.render.render(write_still=True)
for key in ['factory','balanced_reargrip','stable_antislip_reargrip','phantom_reargrip']:
    for ob in production:
        ob.hide_render=(ob['target']!='Body' and ob['target']!=key) or ('FactoryRearGrip' in ob['slot'] and key!='factory')
    render('after_'+key,(.6,-.055,.015))
    if key=='factory':render('after_factory_reverse',(-.6,.0,.035))
    if key in ['balanced_reargrip','stable_antislip_reargrip']:
        render('after_'+key+'_junction',(.3,.16,-.13),(0,.035,.005),.125)
(O/'Inspection/result.json').write_text(json.dumps(report,indent=2))
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(O/'A762_AssemblyAfter.blend'))
print('A762_DETAIL_INSPECTED_RESULT',len(production),flush=True)
