"""Native editable exports and the production inventory icon; no acceptance renders."""
import gc,json,math,sys
from pathlib import Path
import bpy
from mathutils import Matrix
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/FieldRangerTop20261020/TailoredFinish20261021';OUT=R/'Exports'
DEST='/Game/Characters/ModularOutfit20260924/FieldRangerTop20261020/TailoredFinish20261021'
sys.path.insert(0,str(P/'Tools/FieldRangerTop'))
import export_editable as io
io.R=R;io.display_io.OUT=R/'Display';base_mat=io.mat
def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def mat(name,family=None,color=None,rough=.8,metal=0):
    m=base_mat(name,family,color,rough,metal);m['UE_Material']=DEST+'/Materials/M_'+name
    bs=m.node_tree.nodes['Principled BSDF'];bs.inputs['Specular IOR Level'].default_value=.22 if family=='RangerTwill' else .30
    if family:
        nodes=m.node_tree.nodes;links=m.node_tree.links;vertex=nodes.new('ShaderNodeVertexColor');vertex.layer_name='Col'
        source=bs.inputs['Base Color'].links[0].from_socket;mul=nodes.new('ShaderNodeMixRGB');mul.blend_type='MULTIPLY';mul.inputs[0].default_value=1;links.new(source,mul.inputs[1]);links.new(vertex.outputs['Color'],mul.inputs[2]);links.new(mul.outputs[0],bs.inputs['Base Color'])
        source=bs.inputs['Roughness'].links[0].from_socket;mul=nodes.new('ShaderNodeMath');mul.operation='MULTIPLY';links.new(source,mul.inputs[0]);links.new(vertex.outputs['Alpha'],mul.inputs[1]);links.new(mul.outputs[0],bs.inputs['Roughness'])
    return m
def materials(d):
    result=[mat('RangerCloth','RangerTwill'),mat('RangerLeather','RangerLeather'),mat('RangerLining',color=(.021,.023,.016),rough=.90),mat('RangerBrass',color=(.19,.115,.047),rough=.48,metal=.9),mat('RangerThread',color=(.105,.071,.039),rough=.86),mat('ExposedTorsoSkin',color=(.30,.18,.12),rough=.65)]
    return result*2 if len(d['material_slots'])>6 else result
io.materials=materials
def main():
    exports=[]
    for row in read(R/'authored.json')['records']:
        bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
        d=read(Path(row['authored']));rig=io.rig_io.rig_for(d);ob=io.mesh_for(d,rig)
        colors=ob.data.color_attributes.new(name='Col',type='FLOAT_COLOR',domain='POINT');colors.data.foreach_set('color',[x for c in d['colors'] for x in c]);ob.data.color_attributes.active_color=colors
        bpy.context.view_layer.update();bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);ob.select_set(True);bpy.context.view_layer.objects.active=ob
        fbx=OUT/(row['profile']+'_RangerTailored.fbx');bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH','ARMATURE'},add_leaf_bones=False,use_armature_deform_only=True,bake_anim=False,axis_forward='-Y',axis_up='Z',mesh_smooth_type='FACE')
        if row['profile']=='Jason':io.high_sources()
        blend=OUT/(row['profile']+'_RangerTailored.blend');bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(blend));exports.extend([str(fbx),str(blend)])
        if row['profile']=='Jason':
            for side,angle in (('l',12.),('r',-12.)):
                bone=rig.pose.bones['upperarm_'+side];h=bone.matrix.translation.copy();bone.matrix=Matrix.Translation(h)@Matrix.Rotation(math.radians(angle),4,'Y')@Matrix.Translation(-h)@bone.matrix
            bpy.context.view_layer.update();scene=io.icon_io.studio(ob,320,320);scene.cycles.samples=128;scene.render.filepath=str(R/'ue_field_sweater.png');bpy.ops.render.render(write_still=True)
            display=io.display_io.export_display('ue_field_sweater',ob,scene.camera);data=read(display);data['colors']=d['colors'];display.write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
            bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'RangerTailored_Inventory.blend'))
        print('TAILORED_EXPORT',row['profile'],flush=True);del d;gc.collect()
    (R/'editable.json').write_text(json.dumps(dict(completed=True,exports=exports,icon=str(R/'ue_field_sweater.png'),display=str(R/'Display/ue_field_sweater-display.json'),preview_rendered=False,runtime_tested=False),indent=2),encoding='utf-8')
if __name__=='__main__':main()
