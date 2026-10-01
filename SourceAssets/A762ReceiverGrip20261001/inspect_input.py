import bpy,json,sys
from pathlib import Path
import numpy as np
from mathutils import Vector
O=Path(__file__).parent;sys.path.insert(0,str(O));import geometry as G
bpy.ops.wm.read_factory_settings(use_empty=True)
out=O/'Inspection';out.mkdir(exist_ok=True)
h,raw,p,t,m,uv,n,bone=G.body();stats={};objects=[]
def create(name,p,t,uv,n,color):
    vi,inv=np.unique(t,return_inverse=True)
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(p[vi].tolist(),[],inv.reshape(-1,3).tolist());mesh.update()
    ob=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(ob)
    layer=mesh.uv_layers.new(name='UVMap');v=uv.copy();v[:,:,1]=1-v[:,:,1];layer.data.foreach_set('uv',v.ravel())
    for f in mesh.polygons:f.use_smooth=True
    mesh.normals_split_custom_set(n.reshape(-1,3).tolist())
    mat=bpy.data.materials.new(name);mat.diffuse_color=(*color,1);mesh.materials.append(mat)
    return ob
for sid,name in enumerate(h['slots']):
    if any(s in (h['materials'][sid] or '') for s in ('Manny','BarePalm','BareNative','BareFamily')):continue
    for b in np.unique(bone[t[m==sid,0]]):
        sel=(m==sid)&(bone[t[:,0]]==b)
        if not sel.any():continue
        co=p[t[sel]];key=name+'__'+b
        stats[key]={'triangles':int(sel.sum()),'min_m':co.min((0,1)).tolist(),'max_m':co.max((0,1)).tolist()}
        color=(.48,.5,.52) if 'Grip' not in name else (.24,.26,.28)
        ob=create(key,p,t[sel],uv[sel],n[sel],color);ob['slot']=name;ob['bone']=b;objects.append(ob)
grips={}
for key in ['phantom_reargrip','balanced_reargrip','stable_antislip_reargrip']:
    ah,ap,at,am,au,an=G.read(key);ap=ap*G.FLIP;an=an*[1,-1,1];grips[key]=[]
    for sid,name in enumerate(ah['slots']):
        sel=am==sid
        if not sel.any():continue
        ob=create(key+'__'+name,ap,at[sel],au[sel],an[sel],(.26,.28,.3) if 'Interface' not in name else (.48,.5,.52))
        ob['key']=key;ob['slot']=name;grips[key].append(ob);ob.hide_render=True
        co=ap[at[sel]];stats[key+'__'+name]={'triangles':int(sel.sum()),'min_m':co.min((0,1)).tolist(),'max_m':co.max((0,1)).tolist()}
(out/'input_parts.json').write_text(json.dumps(stats,indent=2))
scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH'
scene.display.shading.light='STUDIO';scene.display.shading.studiolight_rotate_z=.3
scene.display.shading.color_type='MATERIAL';scene.display.shading.show_shadows=True
scene.display.shading.show_cavity=True;scene.display.shading.cavity_type='BOTH';scene.display.shading.curvature_ridge_factor=1.;scene.display.shading.curvature_valley_factor=1.
scene.display.shading.background_type='WORLD';scene.world=bpy.data.worlds.new('World');scene.world.color=(.085,.085,.085)
scene.render.resolution_x=1400;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
camdata=bpy.data.cameras.new('Camera');camera=bpy.data.objects.new('Camera',camdata);scene.collection.objects.link(camera);scene.camera=camera;camdata.type='ORTHO';camdata.ortho_scale=.34
def render(label,loc,target=(0,-.055,.015),scale=.34):
    camera.location=loc;camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler();camdata.ortho_scale=scale
    scene.render.filepath=str(out/(label+'.png'));bpy.ops.render.render(write_still=True)
for key in ['factory','balanced_reargrip','stable_antislip_reargrip','phantom_reargrip']:
    for ob in objects:ob.hide_render='FactoryRearGrip' in ob.name and key!='factory'
    for g,obs in grips.items():
        for ob in obs:ob.hide_render=g!=key
    render('before_'+key,(.6,-.055,.015))
    if key=='factory':render('before_factory_reverse',(-.6,.0,.035))
for ob in objects:ob.hide_render=False
for obs in grips.values():
    for ob in obs:ob.hide_render=True
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(O/'A762_AssemblyBefore.blend'))
print('A762_DETAIL_INSPECTED',len(stats),flush=True)
