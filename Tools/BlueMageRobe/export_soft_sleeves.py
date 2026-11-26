"""Export native sleeve FBXs and an editable M4 master; no preview rendering."""
import gc, json, sys
from pathlib import Path
import bpy
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/BlueMageRobe20261018/FPSoftSleeves20261020'
sys.path.insert(0,str(P/'Tools/BlueMageRobe'))
import save_editable as io
OUT=R/'Exports';OUT.mkdir(parents=True,exist_ok=True)
bpy.context.preferences.filepaths.save_version=0
def surface(name,family,lining=False):
    mat=bpy.data.materials.new(name);mat.use_nodes=True
    nodes,links=mat.node_tree.nodes,mat.node_tree.links
    bs=nodes['Principled BSDF'];bs.inputs['Sheen Weight'].default_value=.24
    for channel in ('BaseColor','Normal','ORM'):
        image=bpy.data.images.load(str(R/'Textures'/('T_'+family+'_'+channel+'.png')),check_existing=True)
        if channel!='BaseColor':image.colorspace_settings.name='Non-Color'
        sample=nodes.new('ShaderNodeTexImage');sample.image=image
        if channel=='BaseColor':
            if lining:
                mul=nodes.new('ShaderNodeMixRGB');mul.blend_type='MULTIPLY';mul.inputs[0].default_value=1
                mul.inputs[2].default_value=(.38,.42,.52,1);links.new(sample.outputs[0],mul.inputs[1])
                links.new(mul.outputs[0],bs.inputs['Base Color'])
            else:links.new(sample.outputs[0],bs.inputs['Base Color'])
        elif channel=='Normal':
            normal=nodes.new('ShaderNodeNormalMap');links.new(sample.outputs[0],normal.inputs['Color'])
            links.new(normal.outputs[0],bs.inputs['Normal'])
        else:
            split=nodes.new('ShaderNodeSeparateColor');links.new(sample.outputs[0],split.inputs[0])
            if lining:bs.inputs['Roughness'].default_value=.92
            else:links.new(split.outputs['Green'],bs.inputs['Roughness'])
            links.new(split.outputs['Blue'],bs.inputs['Metallic'])
    return mat
exports=[]
for record in json.loads((R/'manifest.json').read_text())['records']:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    data=json.loads(Path(record['file']).read_text())
    fabric=surface('RobeSoftTwill','RobeSoftTwill')
    cuff=surface('RobeSoftCuff','RobeSoftCuff')
    lining=surface('RobeSoftLining','RobeSoftTwill',True)
    mats=[fabric]*len(data['material_slots']);mats[2]=cuff;mats[3]=lining
    rig=io.rig_for(data);ob=io.mesh_for(data,rig,mats)
    colors=ob.data.color_attributes.new(name='CuffInertia',type='FLOAT_COLOR',domain='POINT')
    for i,color in enumerate(data['colors']):colors.data[i].color=color
    bpy.context.view_layer.update()
    bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);ob.select_set(True)
    bpy.context.view_layer.objects.active=ob
    filename=OUT/(record['profile']+'_RobeSoftSleeves.fbx')
    bpy.ops.export_scene.fbx(filepath=str(filename),use_selection=True,object_types={'MESH','ARMATURE'},
        add_leaf_bones=False,use_armature_deform_only=True,bake_anim=False,axis_forward='-Y',
        axis_up='Z',mesh_smooth_type='FACE')
    exports.append(str(filename))
    if record['profile']=='M4':
        ob['CuffPhysics']='R/G left/right shared outer-inner mask; 4.5 Hz, damping .9, max .28 cm'
        bpy.ops.file.pack_all()
        bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'M4_RobeSoftSleeves.blend'))
    print('SOFT_ROBE_NATIVE_EXPORTED',record['profile'],flush=True)
    del data;gc.collect()
(R/'editable_receipt.json').write_text(json.dumps(dict(completed=True,exports=exports,
    editable_master=str(OUT/'M4_RobeSoftSleeves.blend'),native_sources='Authored/*.json',
    runtime_tested=False),indent=2),encoding='utf-8')
