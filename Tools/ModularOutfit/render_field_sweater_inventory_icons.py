"""Current full-body garments -> production inventory PNGs, independently of export.

Blender background entry. Writes icons and separate display scenes only; production
garment meshes, pickups, skeletons, animations and item definitions stay untouched.
"""
import ast
import hashlib
import json
import math
import shutil
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector

P=Path(__file__).resolve().parents[2]
FAMILY=P/'SourceAssets/FieldSweaterKnit20260929'
OUT=P/'SourceAssets/FieldSweaterInventoryIcons20260930'
MATERIAL_SOURCE=P/'Tools/ModularOutfit/import_field_sweater_knit.py'
ITEMS={'Olive':'ue_field_sweater','Charcoal':'ue_field_sweater_charcoal'}


def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def production_variants():
    # Use the exact tint/cotton/source-directory tuples of the UE material author
    # without importing unreal or executing any asset creation operations.
    tree=ast.parse(MATERIAL_SOURCE.read_text(encoding='utf-8-sig'))
    for node in ast.walk(tree):
        if isinstance(node,ast.For) and isinstance(node.target,ast.Tuple):
            if [getattr(n,'id',None) for n in node.target.elts]==['variant','cotton','color','folder']:
                return ast.literal_eval(node.iter)
    raise RuntimeError('UE garment material recipe changed; update this reader')


def material(variant,slot,tint,cotton):
    pattern='Rib' if slot==1 and not cotton else 'Knit'
    color=tuple(c*(.7 if slot==2 else 1.) for c in tint)
    mat=bpy.data.materials.new(variant+'_Inventory_'+str(slot));mat.use_nodes=True
    n,l=mat.node_tree.nodes,mat.node_tree.links;n.clear()
    bs=n.new('ShaderNodeBsdfPrincipled');out=n.new('ShaderNodeOutputMaterial');l.new(bs.outputs['BSDF'],out.inputs['Surface'])
    uv=n.new('ShaderNodeTexCoord');scale=n.new('ShaderNodeVectorMath');scale.operation='SCALE'
    scale.inputs[3].default_value=25/1.92*(8 if cotton else 1);l.new(uv.outputs['UV'],scale.inputs[0])
    maps={}
    for channel in ('BaseColor','ORM','Normal'):
        image=bpy.data.images.load(str(FAMILY/'Textures'/pattern/(channel+'.png')),check_existing=False)
        image.colorspace_settings.name='sRGB' if channel=='BaseColor' else 'Non-Color';image.pack()
        tex=n.new('ShaderNodeTexImage');tex.image=image;tex.extension='REPEAT';l.new(scale.outputs[0],tex.inputs['Vector']);maps[channel]=tex
    tint_node=n.new('ShaderNodeMixRGB');tint_node.blend_type='MULTIPLY';tint_node.inputs[0].default_value=1.
    tint_node.inputs[2].default_value=(*color,1.);l.new(maps['BaseColor'].outputs['Color'],tint_node.inputs[1])
    orm=n.new('ShaderNodeSeparateColor');l.new(maps['ORM'].outputs['Color'],orm.inputs['Color'])
    cavity=n.new('ShaderNodeMixRGB');cavity.blend_type='MULTIPLY';cavity.inputs[0].default_value=1.
    l.new(tint_node.outputs[0],cavity.inputs[1]);l.new(orm.outputs['Red'],cavity.inputs[2]);l.new(cavity.outputs[0],bs.inputs['Base Color'])
    l.new(orm.outputs['Green'],bs.inputs['Roughness']);bs.inputs['Metallic'].default_value=0.
    normal=n.new('ShaderNodeNormalMap');l.new(maps['Normal'].outputs['Color'],normal.inputs['Color']);l.new(normal.outputs['Normal'],bs.inputs['Normal'])
    bs.inputs['Sheen Weight'].default_value=.15 if cotton else .28
    bs.inputs['Specular IOR Level'].default_value=.3
    mat['ProductionTint']=color;mat['UEAuthorSource']=str(MATERIAL_SOURCE)
    return mat


def garment(data,variant,mats):
    # Recreate the recorded native reference rig in metres, retaining the actual
    # cloth topology, custom normals, per-corner UVs, material regions and weights.
    reflect=Matrix.Diagonal((1.,-1.,1.))
    arm=bpy.data.armatures.new(variant+'_IconReference');rig=bpy.data.objects.new(arm.name,arm)
    bpy.context.collection.objects.link(rig);bpy.context.view_layer.objects.active=rig;rig.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    names={b['index']:name for name,b in data['bones'].items()}
    for name,b in data['bones'].items():
        bone=arm.edit_bones.new(name);axes=Matrix(b['axes']).transposed()
        for j in range(3):axes.col[j]=axes.col[j].normalized()
        transform=(reflect@axes@reflect).to_4x4();transform.translation=reflect@Vector(b['position'])*.01
        bone.matrix=transform;bone.length=.025
    for name,b in data['bones'].items():
        if b['parent'] in names:arm.edit_bones[name].parent=arm.edit_bones[names[b['parent']]]
    bpy.ops.object.mode_set(mode='OBJECT')
    mesh=bpy.data.meshes.new(variant+'_Body_Inventory')
    mesh.from_pydata([(x*.01,-y*.01,z*.01) for x,y,z in data['positions']],[],data['triangles']);mesh.update()
    obj=bpy.data.objects.new(mesh.name,mesh);bpy.context.collection.objects.link(obj);obj.parent=rig
    obj.modifiers.new('NativeDisplayBinding','ARMATURE').object=rig
    for name in sorted({n for w in data['weights'] for n in w}):obj.vertex_groups.new(name=name)
    for i,weights in enumerate(data['weights']):
        for name,w in weights.items():obj.vertex_groups[name].add([i],w,'REPLACE')
    for mat in mats:mesh.materials.append(mat)
    uv=mesh.uv_layers.new(name='ProductionUV');normals=[]
    for face,uvs,ns,slot in zip(mesh.polygons,data['uv'],data['normals'],data['triangle_materials']):
        face.use_smooth=True;face.material_index=slot
        for li,(u,v),normal in zip(face.loop_indices,uvs,ns):
            uv.data[li].uv=(u,1-v);normals.append((normal[0],-normal[1],normal[2]))
    mesh.normals_split_custom_set(normals)
    bpy.context.view_layer.update()
    for side,angle in (('l',12.),('r',-12.)):
        bone=rig.pose.bones['upperarm_'+side];head=bone.matrix.translation.copy()
        bone.matrix=Matrix.Translation(head)@Matrix.Rotation(math.radians(angle),4,'Y')@Matrix.Translation(-head)@bone.matrix
    bpy.context.view_layer.update()
    obj['NativeBindingSource']=data['binding_source'];obj['DisplayOnly']='Both shoulders lowered 12 degrees; native proportions and bone lengths'
    return obj


def studio(obj,width,height):
    scene=bpy.context.scene
    coords=np.array([tuple(obj.matrix_world@v.co) for v in obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices])
    center=Vector((coords.min(0)+coords.max(0))*.5)
    cd=bpy.data.cameras.new('GarmentInventoryCamera');cd.type='ORTHO'
    camera=bpy.data.objects.new(cd.name,cd);scene.collection.objects.link(camera);scene.camera=camera
    camera.location=center+Vector((0.,-3.,.38));camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
    bpy.context.view_layer.update();inverse=camera.matrix_world.inverted()
    points=np.array([tuple(inverse@Vector(v)) for v in coords]);low,high=points.min(0),points.max(0)
    cd.ortho_scale=float(max(high[0]-low[0],(high[1]-low[1])*width/height)/.91)
    camera.location+=camera.rotation_euler.to_matrix()@Vector(((low[0]+high[0])*.5,(low[1]+high[1])*.5,0.))
    for name,offset,power,size in [('Key',(-1.1,-1.8,1.6),75.,1.3),('Fill',(1.2,-1.,.3),25.,1.6),('Rim',(.8,.7,1.2),45.,.85)]:
        light=bpy.data.lights.new(name,'AREA');light.energy=power;light.size=size
        lamp=bpy.data.objects.new(name,light);scene.collection.objects.link(lamp);lamp.location=center+Vector(offset)
        lamp.rotation_euler=(center-lamp.location).to_track_quat('-Z','Y').to_euler()
    world=bpy.data.worlds.new('GarmentNeutralStudio');world.use_nodes=True;scene.world=world
    nodes,links=world.node_tree.nodes,world.node_tree.links;nodes.clear()
    bg=nodes.new('ShaderNodeBackground');output=nodes.new('ShaderNodeOutputWorld');links.new(bg.outputs[0],output.inputs['Surface'])
    bg.inputs['Color'].default_value=(.35,.35,.35,1.);bg.inputs['Strength'].default_value=.12
    scene.render.engine='CYCLES';scene.cycles.samples=512;scene.cycles.adaptive_threshold=.003;scene.cycles.use_denoising=False
    scene.render.resolution_x=width;scene.render.resolution_y=height;scene.render.resolution_percentage=100
    scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
    scene.view_settings.view_transform='Standard';scene.view_settings.look='None';scene.view_settings.exposure=0.;scene.view_settings.gamma=1.
    return scene


def pixels(path):
    image=bpy.data.images.load(str(path),check_existing=False);image.colorspace_settings.name='Non-Color'
    values=np.empty(len(image.pixels),dtype=np.float32);image.pixels.foreach_get(values)
    width,height=image.size;rgba=values.reshape(height,width,4);opaque=rgba[:,:,3]>.99;encoded=rgba[:,:,:3][opaque]
    linear=np.where(encoded<=.04045,encoded/12.92,((encoded+.055)/1.055)**2.4)
    y,x=np.nonzero(rgba[:,:,3]>.05)
    result=dict(mean_linear=linear.mean(0).tolist(),mean_srgb=(encoded.mean(0)*255).tolist(),
        fill=max((x.max()-x.min()+1)/width,(y.max()-y.min()+1)/height),center=[float((x.max()+x.min()+1)/(2*width)),float((y.max()+y.min()+1)/(2*height))])
    bpy.data.images.remove(image)
    return result


def inventory(only_items=None):
    OUT.mkdir(parents=True,exist_ok=True)
    recipes=read(P/'Content/ColdSteelData/modular_outfits.json')['items'];items=read(P/'Content/ColdSteelData/items.json')
    results={}
    for variant,cotton,tint,folder in production_variants():
        item_id=ITEMS[variant]
        if only_items and item_id not in only_items:continue
        body=recipes[item_id]['rig_meshes']['Body']
        repaired='/Game/Characters/ModularOutfit20260924/CharcoalGarmentRepair20260930/BodyV4/SK_Body_Charcoal.SK_Body_Charcoal'
        if variant=='Charcoal' and body==repaired:
            source=P/'SourceAssets/CharcoalGarmentRepair20260930/Authored/Body.json'
        elif '/FieldSweaterKnit20260929/'+variant+'/Body/' in body:
            source=FAMILY/folder/'Body.json'
        else:raise RuntimeError('Current clothing Body family changed: '+item_id)
        data=read(source)
        bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
        obj=garment(data,variant,[material(variant,i,tint,cotton) for i in range(3)])
        item=items[item_id];width=max(256,round(320*item['grid_w']/max(1,item['grid_h'])));height=320
        scene=studio(obj,width,height);icon=OUT/(item_id+'.png');scene.render.filepath=str(icon)
        calibration=[]
        for attempt in range(3):
            bpy.ops.render.render(write_still=True)
            measured=pixels(icon);calibration.append(dict(exposure=scene.view_settings.exposure,**measured))
            delta=math.log2(max(float(np.mean(tint))/max(float(np.mean(measured['mean_linear'])),1.e-8),1.e-3))
            if abs(delta)<.035 or attempt==2:break
            scene.view_settings.exposure+=delta
        bpy.ops.file.pack_all();blend=OUT/(variant+'_InventoryIcon.blend');bpy.ops.wm.save_as_mainfile(filepath=str(blend))
        destinations=[P/'Content/ColdSteelData'/item['ue_icon'],FAMILY/(item_id+'.png')]
        alias=P/'Content/ColdSteelData/Icons/ModularOutfit20260924'/(item_id+'.png')
        if alias.exists():destinations.append(alias)
        installed=[]
        for dest in destinations:
            backup=OUT/'Before'/('_'.join(dest.relative_to(P).parts));backup.parent.mkdir(parents=True,exist_ok=True)
            if dest.exists() and not backup.exists():shutil.copy2(dest,backup)
            dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(icon,dest);installed.append(str(dest))
        results[item_id]=dict(icon=str(icon),blend=str(blend),source=str(source),source_sha256=digest(source),source_asset=body,
            material_author=str(MATERIAL_SOURCE),material_author_sha256=digest(MATERIAL_SOURCE),tint_linear=tint,size=[width,height],transparent=True,
            calibration=calibration,installed=installed,icon_sha256=digest(icon),gameplay_assets_changed=False,runtime_tested=False)
        (OUT/(item_id+'-production.json')).write_text(json.dumps(results[item_id],ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print('GARMENT_INVENTORY_ICON_SAVED',item_id,str(icon),'exposure',scene.view_settings.exposure,'rgb',measured['mean_srgb'],flush=True)
    return results


if __name__=='__main__':inventory()
