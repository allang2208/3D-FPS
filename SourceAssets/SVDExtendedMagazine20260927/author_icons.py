"""Produce three catalog resources from the actual factory/extended meshes."""
import bpy,json,shutil
from pathlib import Path
from mathutils import Matrix,Vector

O=Path(__file__).parent;I=O/'Icons';I.mkdir(exist_ok=True)
DEST=O.parents[1]/'Content/ColdSteelData/AttachmentIcons20260913'
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(O/'SVD_ExtendedMagazine_Editable.blend'))
root=Matrix(json.loads((O/'source_geometry.json').read_text())['root_matrix'])
params=json.loads((O/'source_materials.json').read_text())['parameters']
T=O.parent/'SVDMatteDetail20260923/Textures'

def working_material(m):
    m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links;n.clear()
    bs=n.new('ShaderNodeBsdfPrincipled');out=n.new('ShaderNodeOutputMaterial');l.new(bs.outputs[0],out.inputs[0])
    def tex(role,srgb):
        node=n.new('ShaderNodeTexImage');node.image=bpy.data.images.load(str(T/('T_SVD_Magazine_'+role+'.png')),check_existing=True)
        node.image.colorspace_settings.name='sRGB' if srgb else 'Non-Color';return node.outputs['Color']
    def op(kind,a,b):
        node=n.new('ShaderNodeMath');node.operation=kind
        for v,p in zip([a,b],node.inputs):
            if isinstance(v,(int,float)):p.default_value=v
            else:l.new(v,p)
        return node.outputs[0]
    bc=tex('BaseColor',True);packed=n.new('ShaderNodeSeparateColor');l.new(tex('ORM',False),packed.inputs[0])
    lum=n.new('ShaderNodeRGBToBW');l.new(bc,lum.inputs[0])
    shading=op('MINIMUM',1.30,op('MAXIMUM',.72,op('DIVIDE',lum.outputs[0],.034)))
    tint=n.new('ShaderNodeVectorMath');tint.operation='SCALE';tint.inputs[0].default_value=params['vector']['SVD_RefinedColor'][:3];l.new(shading,tint.inputs[3])
    blend=n.new('ShaderNodeMixRGB');blend.inputs[0].default_value=params['scalar']['SVD_RefinedColorWeight'];l.new(bc,blend.inputs[1]);l.new(tint.outputs[0],blend.inputs[2]);l.new(blend.outputs[0],bs.inputs['Base Color'])
    base_rough=op('MAXIMUM',.61,packed.outputs['Green'])
    structure=op('MINIMUM',.018,op('MAXIMUM',-.018,op('MULTIPLY',op('SUBTRACT',base_rough,.5),.08)))
    rough=op('ADD',params['scalar']['SVD_RefinedRoughness'],structure);l.new(rough,bs.inputs['Roughness'])
    bs.inputs['Metallic'].default_value=params['scalar']['SVD_RefinedMetallic']
    normal=n.new('ShaderNodeNormalMap');normal.uv_map='UVMap';l.new(tex('Normal',False),normal.inputs['Color']);l.new(normal.outputs[0],bs.inputs['Normal'])

parts=[bpy.data.objects['SM_SVD_ext_mag'],bpy.data.objects['SM_SVD_factory_magazine']]
for ob in parts:
    ob.hide_set(False);ob.data.transform(root.inverted());ob.matrix_world=Matrix.Identity(4)
    for i,mat in enumerate(ob.data.materials):
        mat=mat.copy();ob.data.materials[i]=mat;working_material(mat)
scene=bpy.context.scene
scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=True
try:
    prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
    for device in prefs.devices:device.use=device.type=='OPTIX'
    if any(d.use for d in prefs.devices):scene.cycles.device='GPU'
except Exception:pass
scene.render.resolution_x=scene.render.resolution_y=1024;scene.render.resolution_percentage=100
scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast'
scene.world=bpy.data.worlds.new('SVD_CatalogWorld');scene.world.use_nodes=True
scene.world.node_tree.nodes.clear()
background=scene.world.node_tree.nodes.new('ShaderNodeBackground');worldout=scene.world.node_tree.nodes.new('ShaderNodeOutputWorld')
scene.world.node_tree.links.new(background.outputs[0],worldout.inputs[0])
background.inputs['Color'].default_value=(.18,.18,.18,1);background.inputs['Strength'].default_value=.35
camera=bpy.data.objects.new('SVD_CatalogCamera',bpy.data.cameras.new('SVD_CatalogCamera'));scene.collection.objects.link(camera)
camera.data.type='ORTHO';camera.data.clip_start=.001;scene.camera=camera
lamps=[]
for name,offset,energy,size in [('Key',(.40,-.10,.42),32,.40),('Fill',(.20,.32,.13),18,.35),('Rim',(-.28,-.12,.30),35,.30)]:
    data=bpy.data.lights.new(name,'AREA');data.energy=energy;data.shape='DISK';data.size=size
    lamp=bpy.data.objects.new(name,data);scene.collection.objects.link(lamp);lamps.append((lamp,Vector(offset)))
records={}
for ob,key in zip(parts,['ue_svd_magazine_ext_mag','ue_svd_magazine_false']):
    for p in parts:p.hide_render=p!=ob
    pts=[v.co for v in ob.data.vertices];lo=Vector([min(p[i] for p in pts) for i in range(3)]);hi=Vector([max(p[i] for p in pts) for i in range(3)])
    center=(lo+hi)*.5;camera.location=center+Vector((1.5,0,0));camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
    camera.data.ortho_scale=max(hi.y-lo.y,hi.z-lo.z)/.82
    for lamp,offset in lamps:lamp.location=center+offset;lamp.rotation_euler=(center-lamp.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(I/(key+'.png'))
    bpy.ops.wm.save_as_mainfile(filepath=str(I/(key+'.blend')))
    bpy.ops.render.render(write_still=True)
    shutil.copy2(I/(key+'.png'),DEST/(key+'.png'))
    records[key]={'output':str(DEST/(key+'.png')),'source':str(O/'SVD_ExtendedMagazine_Editable.blend'),'object':ob.name,
        'size':[1024,1024],'forward':'SVD -Y forward at screen left, +Z up; +X orthographic camera',
        'material':'Current UE magazine textures and refined scalar/vector values; Blender translation omits UE procedural micrograin/rain',
        'purpose':'production catalog texture, not acceptance render'}
key='ue_svd_category_magazine'
shutil.copy2(I/'ue_svd_magazine_false.png',I/(key+'.png'));shutil.copy2(I/(key+'.png'),DEST/(key+'.png'))
records[key]={**records['ue_svd_magazine_false'],'output':str(DEST/(key+'.png'))}
(O/'icons.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
print('SVD_EXTMAG_ICONS_SAVED',len(records),flush=True)
