"""Offline fit views of the existing saved/source geometry, not generated artwork."""
import bpy,json,sys,math
import numpy as np
from pathlib import Path
from mathutils import Vector
P=Path('D:/FPS3D/FPSGAME');S=P/'SourceAssets/ModernTacticalSet20261113';R=S/'SetFitReview20261115';OUT=R/'Views';OUT.mkdir(exist_ok=True)
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
rig=sys.argv[sys.argv.index('--')+1];plan=read(R/'plan.json')
def data(key):
    row=next(x for x in plan['rows'] if x['key']==key);cap=R/'Captured'/(key+'.json')
    if cap.exists():
        c=read(cap)
        if 'source_model' in c and c['source_model'].get('uv'):return c['source_model']
    return read(row['candidates'][0])
bpy.ops.wm.read_factory_settings(use_empty=True)
def material(name):
    mat=bpy.data.materials.get(name)
    if mat:return mat
    mat=bpy.data.materials.new(name);mat.use_nodes=True;bs=mat.node_tree.nodes.get('Principled BSDF');bs.inputs['Roughness'].default_value=.8
    stem=name.split('/')[-1].split('.')[0].removeprefix('M_').removeprefix('TS01_')
    root=S/'CombatShirtR3/Textures' if stem.startswith('Combat') else S/'Textures'
    base=root/(stem+'_BaseColor.png')
    if not base.exists():
        bs.inputs['Base Color'].default_value=(.42,.24,.14,1) if name=='Native reference skin' else (.13,.08,.042,1)
        return mat
    nodes=mat.node_tree.nodes;links=mat.node_tree.links;coord=nodes.new('ShaderNodeTexCoord');scale=nodes.new('ShaderNodeVectorMath');scale.operation='SCALE';scale.inputs[3].default_value=8/28.8 if stem.startswith('Combat') else 1.;links.new(coord.outputs['UV'],scale.inputs[0])
    for ch in ['BaseColor','NormalGL','ORM']:
        file=root/(stem+'_'+ch+'.png')
        if not file.exists():continue
        im=bpy.data.images.load(str(file),check_existing=True)
        if ch!='BaseColor':im.colorspace_settings.name='Non-Color'
        tex=nodes.new('ShaderNodeTexImage');tex.image=im;links.new(scale.outputs['Vector'],tex.inputs['Vector'])
        if ch=='BaseColor':links.new(tex.outputs['Color'],bs.inputs['Base Color'])
        elif ch=='NormalGL':
            normal=nodes.new('ShaderNodeNormalMap');links.new(tex.outputs['Color'],normal.inputs['Color']);links.new(normal.outputs['Normal'],bs.inputs['Normal'])
        else:
            sep=nodes.new('ShaderNodeSeparateColor');links.new(tex.outputs['Color'],sep.inputs[0]);links.new(sep.outputs['Green'],bs.inputs['Roughness']);links.new(sep.outputs['Blue'],bs.inputs['Metallic'])
    if stem.startswith('Combat'):bs.inputs['Sheen Weight'].default_value=.28
    return mat
def mesh(d,name,mask=None,skin=False):
    f=np.array(d['triangles'],int);m=np.array(d['triangle_materials']);ids=np.arange(len(f)) if mask is None else np.flatnonzero(mask)
    me=bpy.data.meshes.new(name);me.from_pydata((np.array(d['positions'])*[.01,-.01,.01]).tolist(),[],f[ids].tolist());me.update();ob=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(ob)
    for mat in d.get('materials',d['material_slots']):me.materials.append(material('Native reference skin' if skin or '/AsianMale_' in mat or '/KaitlinPlayer' in mat else mat))
    uv=me.uv_layers.new()
    for poly,idx in zip(me.polygons,ids):
        poly.material_index=int(m[idx]);poly.use_smooth=True
        if d.get('uv'):
            for li,tex in zip(poly.loop_indices,d['uv'][idx]):uv.data[li].uv=(tex[0],1-tex[1])
    if d.get('normals'):
        ns=np.array(d['normals'])[ids]*[1,-1,1]
        if np.isfinite(ns).all():me.normals_split_custom_set(ns.reshape(-1,3).tolist())
    return ob
body=data(rig+'_body')
config=read(R/'modular_outfits.snapshot.json');config=config if rig=='Jason' else config['body_variants']['kaitlin']
covered=set()
for key in ['ue_modern_kevlar_vest','ue_modern_tactical_pants','ue_modern_tactical_boots','ue_modern_tactical_gloves']:
    recipe=config['items'][key];covered.update(recipe.get('rig_world_covers',{}).get(rig,recipe.get('world_covers',recipe.get('covers',[2] if key.endswith('gloves') else []))))
bd=mesh(body,'Native body with configured equipment coverage',~np.isin(body['triangle_materials'],list(covered)),skin=True)
shirt=data(rig+'_shirt_tactical_world');cloth_source=read(S/'CombatShirtR3/Authored'/f'shirt_detail_{rig}.json')
# Split by exact original positions, because UE source models may reorder
# faces by material. The shirt occupies the initial authored vertex range;
# saved material channels alone are shared with the carrier.
author=read(next(x for x in plan['rows'] if x['key']==rig+'_shirt_tactical_world')['candidates'][0])
nc=len(cloth_source['positions']);f=np.array(author['triangles']);outer=(f<nc).all(1)|np.array([author['material_slots'][m].startswith('NATIVE:') for m in author['triangle_materials']])
garment=mesh(author,'Sewn shirt and native neck patch',outer);carrier=mesh(author,'Carrier',~outer)
pants=mesh(data(rig+'_pants_tactical'),'Tactical trousers');boots=mesh(data(rig+'_boots'),'Tactical boots');gloves=mesh(data(rig+'_gloves'),'Tactical gloves')
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True
try:
    pref=bpy.context.preferences.addons['cycles'].preferences;pref.compute_device_type='OPTIX';pref.get_devices()
    for dev in pref.devices:dev.use=dev.type!='CPU'
    scene.cycles.device='GPU'
except Exception:pass
scene.render.resolution_x=1200;scene.render.resolution_y=1400;scene.render.resolution_percentage=100;scene.view_settings.view_transform='AgX'
world=bpy.data.worlds.new('Neutral studio');world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.18,.18,.18,1);world.node_tree.nodes['Background'].inputs[1].default_value=.45;scene.world=world
target=Vector((0,0,1.15))
for i,(loc,energy,size) in enumerate([((1,-2.5,3),450,2.5),((-2,-1,2),300,2),((0,2,3),500,2)]):
    light=bpy.data.lights.new('Review light '+str(i),'AREA');light.energy=energy;light.shape='DISK';light.size=size;ob=bpy.data.objects.new(light.name,light);bpy.context.collection.objects.link(ob);ob.location=loc;ob.rotation_euler=(target-ob.location).to_track_quat('-Z','Y').to_euler()
cam=bpy.data.cameras.new('Camera');camera=bpy.data.objects.new('Camera',cam);bpy.context.collection.objects.link(camera);scene.camera=camera;cam.type='ORTHO'
(R/(rig+'-view-materials.json')).write_text(json.dumps([dict(name=m.name,textures=[n.image.filepath for n in m.node_tree.nodes if n.type=='TEX_IMAGE']) for m in bpy.data.materials if m.use_nodes],indent=2),encoding='utf-8')
for name,direction,center,scale,hide in [('shirt_front',(0,-4,.3),(0,0,1.24 if rig=='Kaitlin' else 1.30),1.10,True),('shirt_back',(0,4,.3),(0,0,1.24 if rig=='Kaitlin' else 1.30),1.10,True),('outfit_front',(1,-4,.5),(0,0,.83),1.9,False),('outfit_back',(-1,4,.5),(0,0,.83),1.9,False)]:
    carrier.hide_render=hide;target=Vector(center);cam.ortho_scale=scale;camera.location=target+Vector(direction);camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(OUT/(rig+'_'+name+'.png'));bpy.ops.render.render(write_still=True);print('FIT_VIEW',rig,name,flush=True)
