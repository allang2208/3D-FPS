"""Export the five owned masters and render requested inventory artwork only."""
import bpy,bmesh,json,sys,math
from pathlib import Path
import numpy as np
from mathutils import Vector,Matrix
P=Path('D:/FPS3D/FPSGAME');S=P/'SourceAssets/ModernTacticalSet20261113';R=S/'Integration';D=R/'Delivery';OUT=R/'Icons'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,d):p.write_text(json.dumps(d,separators=(',',':'),ensure_ascii=False),encoding='utf-8')
bones=read(P/'SourceAssets/JasonPlayer20261003/Jason.json')['bones'];names={b['name']:b['index'] for b in bones}
SPECS=[('vest','01_KevlarVest','ue_modern_kevlar_vest',3,3),('helmet','02_TacticalHelmet','ue_modern_tactical_helmet',2,2),('gloves','03_TacticalGloves','ue_modern_tactical_gloves',2,2),('pants','04_TacticalTrousers','ue_modern_tactical_pants',2,3),('pants_boot','04_TacticalTrousers_BootTuck',None,2,3),('boots','05_TacticalBoots','ue_modern_tactical_boots',2,3)]
def combine():
    bpy.ops.object.select_all(action='DESELECT');objects=[o for o in bpy.context.scene.objects if o.type=='MESH']
    for o in objects:
        o.hide_set(False);o.select_set(True)
        for mod in list(o.modifiers):
            if mod.type=='ARMATURE':o.modifiers.remove(mod)
    bpy.context.view_layer.objects.active=objects[0];bpy.ops.object.join();ob=bpy.context.object
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True);return ob
def export(ob):
    me=ob.data;me.calc_loop_triangles();uv=me.uv_layers.active;groups={g.index:names[g.name] for g in ob.vertex_groups if g.name in names}
    mats=[];mapping={}
    for i,m in enumerate(me.materials):
        name=m.name.split('.')[0];mapping[i]=mats.index(name) if name in mats else len(mats)
        if name not in mats:mats.append(name)
    d=dict(positions=[],triangles=[],uv=[],normals=[],weights=[],triangle_materials=[],material_slots=mats,bones=bones,source='/Game/Characters/ModularOutfit20260924/ArmoredBoots20261004/SK_Jason_Base.SK_Jason_Base',contract='TS01 actual Blender master, native UE cm, reflected Y, original corner normals and UV, original Jason skin weights')
    for v in me.vertices:
        d['positions'].append([v.co.x*100,-v.co.y*100,v.co.z*100]);ws=sorted([(groups[g.group],g.weight) for g in v.groups if g.group in groups and g.weight>1e-7],key=lambda p:-p[1])[:8];total=sum(w for _,w in ws)
        if not total:raise RuntimeError('Unbound author vertex '+ob.name)
        d['weights'].append([[i,w/total] for i,w in ws])
    for t in me.loop_triangles:
        d['triangles'].append(list(t.vertices));d['triangle_materials'].append(mapping[t.material_index]);d['uv'].append([[uv.data[i].uv.x,1-uv.data[i].uv.y] for i in t.loops]);d['normals'].append([[me.corner_normals[i].vector.x,-me.corner_normals[i].vector.y,me.corner_normals[i].vector.z] for i in t.loops])
    return d
def icon(ob,key,w,h,kind):
    # Separate display-only object. No hand/boot poses or transforms are written back.
    if kind in ['gloves','boots']:
        bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.delete(bm,geom=[v for v in bm.verts if v.co.x<0],context='VERTS');bm.to_mesh(ob.data);bm.free()
    if kind=='gloves':
        bp={b['name']:Vector((b['position'][0],-b['position'][1],b['position'][2]))*.01 for b in bones}
        wrist=bp['hand_l'];forward=(bp['middle_01_l']-wrist).normalized();across=bp['index_01_l']-bp['pinky_01_l'];across=(across-forward*across.dot(forward)).normalized();normal=across.cross(forward).normalized()
        if normal.y<0:normal=-normal;across=-across
        basis=Matrix((across,-normal,forward))
        for v in ob.data.vertices:v.co=basis@(v.co-wrist)
        ob.data.update()
    coords=np.array([v.co[:] for v in ob.data.vertices]);center=Vector((coords.min(0)+coords.max(0))*.5);span=max(coords.max(0)-coords.min(0))
    camdata=bpy.data.cameras.new('Inventory_Orthographic');camdata.type='ORTHO';camdata.clip_start=.001
    cam=bpy.data.objects.new(camdata.name,camdata);bpy.context.collection.objects.link(cam);scene=bpy.context.scene;scene.camera=cam
    offsets={'vest':(.35,-3,.30),'helmet':(.85,-3,1.1),'gloves':(.25,-3,.5),'pants':(0,-3,.08),'boots':(.95,-3,.9)}
    cam.location=center+Vector(offsets[kind])*span;cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();bpy.context.view_layer.update()
    projected=np.array([(cam.matrix_world.inverted()@Vector(p))[:] for p in coords]);lo,hi=projected.min(0),projected.max(0);aspect=w/h
    camdata.ortho_scale=float(max((hi[0]-lo[0])/min(1,aspect),(hi[1]-lo[1])*max(1,aspect))/.91)
    cam.location+=cam.rotation_euler.to_matrix()@Vector(((lo[0]+hi[0])*.5,(lo[1]+hi[1])*.5,0));bpy.context.view_layer.update()
    basis=cam.rotation_euler.to_matrix()
    for name,offset,power,size in [('Key',(-.8,.7,1.5),35,1.2),('Fill',(.9,.1,1.2),12,1.5),('Rim',(.2,1,-.8),20,.8)]:
        light=bpy.data.lights.new(name,'AREA');light.energy=power*span*span;light.size=size*span;lamp=bpy.data.objects.new(name,light);scene.collection.objects.link(lamp);lamp.location=center+basis@(Vector(offset)*span);lamp.rotation_euler=(center-lamp.location).to_track_quat('-Z','Y').to_euler()
    world=bpy.data.worlds.new('Inventory_Neutral');world.use_nodes=True;world.node_tree.nodes.clear();bg=world.node_tree.nodes.new('ShaderNodeBackground');output=world.node_tree.nodes.new('ShaderNodeOutputWorld');world.node_tree.links.new(bg.outputs[0],output.inputs[0]);bg.inputs[0].default_value=(.35,.35,.35,1);bg.inputs[1].default_value=.12;scene.world=world
    scene.render.engine='CYCLES';scene.cycles.samples=128;scene.cycles.use_denoising=True;scene.render.resolution_x=160*w;scene.render.resolution_y=160*h;scene.render.resolution_percentage=100;scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA';scene.view_settings.view_transform='Standard';scene.view_settings.look='None';scene.view_settings.exposure=0
    prefs=bpy.context.preferences.addons['cycles'].preferences
    try:
        prefs.compute_device_type='OPTIX';prefs.refresh_devices()
        if any(device.type=='OPTIX' for device in prefs.devices):
            for device in prefs.devices:device.use=device.type=='OPTIX'
            scene.cycles.device='GPU'
    except (TypeError,RuntimeError):
        scene.cycles.device='CPU'
    for o in scene.objects:
        if o.type=='MESH':o.hide_render=o!=ob
    scene.render.filepath=str(OUT/(key+'.png'));bpy.ops.render.render(write_still=True)
    # Save the independent camera-aligned geometry used by the equipment UI.
    ns={'__name__':'ts01_icon_export'};path=P/'Tools/FieldHat/render_icon.py';exec(compile(path.read_text(encoding='utf-8-sig'),str(path),'exec'),ns);ns['OUT']=OUT;ns['export_display'](key,ob,cam)
    display=OUT/(key+'-display.json')
    payload=read(display);payload['material_slots']=[m.name.split('.')[0] for m in ob.data.materials];write(display,payload)
    bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(OUT/(key+'-icon.blend')))
    return dict(png=str(OUT/(key+'.png')),display=str(OUT/(key+'-display.json')),resolution=[160*w,160*h],fill_target=.91,single_empty_glove=kind=='gloves')
def main():
    selected=set(sys.argv[sys.argv.index('--parts')+1].split(',')) if '--parts' in sys.argv else None
    rows=read(R/'prepared.json')['rows'] if selected else []
    for kind,filename,key,w,h in SPECS:
        if selected and kind not in selected:continue
        bpy.ops.wm.open_mainfile(filepath=str(S/'Models'/(filename+'.blend')))
        for img in bpy.data.images:
            path=S/'Textures'/Path(img.filepath).name
            if path.is_file():
                if img.packed_file:img.unpack(method='REMOVE')
                img.filepath=str(path);img.reload()
        bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(S/'Models'/(filename+'.blend')))
        ob=combine();ob.name='TS01_'+kind;data=export(ob);write(D/(kind+'_Jason.json'),data)
        item=dict(kind=kind,key=key,file=str(D/(kind+'_Jason.json')),material_slots=data['material_slots'],grid_w=w,grid_h=h)
        if key:item['icon']=icon(ob,key,w,h,kind)
        rows=[r for r in rows if r['kind']!=kind]+[item]
        rows.sort(key=lambda r:next(i for i,s in enumerate(SPECS) if s[0]==r['kind']))
        write(R/'prepared.json',dict(completed=False,rows=rows));print('TS01_DELIVERY_AUTHORED',kind,flush=True)
    write(R/'prepared.json',dict(completed=True,rows=rows,runtime_tested=False))

if __name__=="__main__":main()
