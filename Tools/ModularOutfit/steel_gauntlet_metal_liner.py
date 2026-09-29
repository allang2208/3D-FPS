"""Reuse the existing under-plate fine grey metal across the full glove liner.

Background Blender authoring only: bake a seamless material tile, update the
three current editable sources, and export the existing pickup. No renders.
"""
import json
import shutil
import sys
from pathlib import Path
import bpy

P=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(P/'Tools/ModularOutfit'))
R=P/'SourceAssets/MetalGauntlet20260927/SteelGauntletV1'
OUT=R/'FullMetal20260928'
T=OUT/'Textures'
NAME='GreyMetalLiner_Baked'
# Eight columns and eight staggered rows, matching the original mail recipe.
TILE=(.0007*8,.0006*8)
REPEAT=(.25/TILE[0],.25/TILE[1])


def blender_material():
    existing=bpy.data.materials.get(NAME)
    if existing:return existing
    mat=bpy.data.materials.new(NAME);mat.use_nodes=True
    n=mat.node_tree.nodes;l=mat.node_tree.links;bs=n.get('Principled BSDF')
    uv=n.new('ShaderNodeTexCoord');scale=n.new('ShaderNodeVectorMath');scale.operation='MULTIPLY'
    l.new(uv.outputs['UV'],scale.inputs[0]);scale.inputs[1].default_value=(*REPEAT,1.)
    for label in ('BaseColor','ORM','Normal'):
        image=bpy.data.images.load(str(T/('T_GauntletGreyMail_'+label+'.png')),check_existing=True)
        image.colorspace_settings.name='sRGB' if label=='BaseColor' else 'Non-Color';image.pack()
        tex=n.new('ShaderNodeTexImage');tex.image=image;l.new(scale.outputs[0],tex.inputs['Vector'])
        if label=='BaseColor':l.new(tex.outputs['Color'],bs.inputs['Base Color'])
        elif label=='ORM':
            split=n.new('ShaderNodeSeparateColor');l.new(tex.outputs['Color'],split.inputs['Color'])
            l.new(split.outputs['Green'],bs.inputs['Roughness']);l.new(split.outputs['Blue'],bs.inputs['Metallic'])
        else:
            normal=n.new('ShaderNodeNormalMap');l.new(tex.outputs['Color'],normal.inputs['Color']);l.new(normal.outputs['Normal'],bs.inputs['Normal'])
    mat['Source']='Exact flexible_mail branch from steel_gauntlet_finish.material; full glove coverage'
    return mat


def apply_to_liner(obj):
    obj.data.materials[0]=blender_material()
    obj['Construction']='Full grey flexible-metal liner; original topology, fitting and skin weights retained'


def bake_tile():
    import steel_gauntlet_finish as finish
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.mesh.primitive_plane_add(size=1)
    obj=bpy.context.object;obj.name='GreyMail_SeamlessProductionTile'
    obj.scale=(TILE[0],TILE[1],1.);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    obj.data.uv_layers[0].name='SteelPanelUV';obj.color=(*TILE,.70,1.)
    mat,color,orm,bs,out=finish.material();obj.data.materials.append(mat)
    nt=mat.node_tree
    # The donor's bevel and geometry AO belong to the plates, not this seamless tile.
    bump=next(n for n in nt.nodes if n.type=='BUMP')
    nt.links.new(bump.outputs['Normal'],bs.inputs['Normal'])
    pack=next(n for n in nt.nodes if n.type=='COMBINE_COLOR')
    for link in list(pack.inputs['Red'].links):nt.links.remove(link)
    pack.inputs['Red'].default_value=1.
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=4
    scene.render.bake.margin=0
    for label,kind,source in [('BaseColor','EMIT',color),('ORM','EMIT',orm),('Normal','NORMAL',None)]:
        image=bpy.data.images.new('T_GauntletGreyMail_'+label,width=512,height=512,alpha=False)
        image.colorspace_settings.name='sRGB' if label=='BaseColor' else 'Non-Color'
        target=nt.nodes.new('ShaderNodeTexImage');target.image=image;nt.nodes.active=target
        if source is not None:
            emit=nt.nodes.new('ShaderNodeEmission');nt.links.new(source,emit.inputs['Color']);nt.links.new(emit.outputs[0],out.inputs['Surface'])
        else:nt.links.new(bs.outputs[0],out.inputs['Surface'])
        bpy.ops.object.bake(type=kind,normal_space='TANGENT')
        image.filepath_raw=str(T/(image.name+'.png'));image.file_format='PNG';image.save();image.pack()
        print('GREY_MAIL_BAKED '+label,flush=True)
    nt.links.new(bs.outputs[0],out.inputs['Surface'])
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'GreyMetalLiner_Material.blend'))


def main():
    T.mkdir(parents=True,exist_ok=True)
    before=OUT/'Before';before.mkdir(exist_ok=True)
    bake_tile();changed=[]
    for filename in ('SteelGauntlet_Authored.blend','SteelGauntlet_M4.blend','SteelGauntlet_Icon.blend'):
        path=R/filename
        if not (before/filename).exists():shutil.copy2(path,before/filename)
        bpy.ops.wm.open_mainfile(filepath=str(path));bpy.context.preferences.filepaths.save_version=0
        metal=blender_material()
        for obj in bpy.data.objects:
            if obj.type!='MESH':continue
            for i,mat in enumerate(obj.data.materials):
                if mat and (mat.name.startswith('Accepted_TailoredLeather_Liner') or mat.name==NAME):
                    obj.data.materials[i]=metal;obj['LinerFinish']='Grey flexible metal, no leather';changed.append([filename,obj.name,i])
        if filename=='SteelGauntlet_Icon.blend':
            obj=bpy.data.objects['SM_SteelGauntlet_Pickup']
            fbx=R/'SM_SteelGauntlet_Pickup.fbx'
            if not (before/fbx.name).exists():shutil.copy2(fbx,before/fbx.name)
            bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
            bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},bake_anim=False,mesh_smooth_type='FACE',path_mode='STRIP')
        bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(path))
    (OUT/'author-receipt.json').write_text(json.dumps(dict(complete=True,changed=changed,tile_meters=TILE,
        uv_repeat=REPEAT,source='steel_gauntlet_finish.material flexible_mail branch',
        geometry_changed=False,preview_rendered=False,runtime_tested=False),indent=2),encoding='utf-8')
    print('STEEL_GREY_METAL_LINER_AUTHORED',flush=True)


if __name__=='__main__':main()
