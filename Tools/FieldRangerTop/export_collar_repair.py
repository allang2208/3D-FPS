"""Export repaired native bodies, current inventory image, and collar diagnosis views."""
import gc, json, math, sys
from pathlib import Path
import bpy
from mathutils import Vector,Matrix
P=Path('D:/FPS3D/FPSGAME');BASE=P/'SourceAssets/FieldRangerTop20261020';R=BASE/'CollarRepair20261021'
sys.path.insert(0,str(P/'Tools/FieldRangerTop'))
import export_editable as io
OUT=R/'Exports';io.display_io.OUT=R/'Display'
def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))

def build(d):
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
    rig=io.rig_io.rig_for(d);ob=io.mesh_for(d,rig);bpy.context.view_layer.update()
    return ob,rig

def diagnosis(d,name,side=False):
    ob,rig=build(d);scene=io.icon_io.studio(ob,960,900);scene.cycles.samples=64;scene.cycles.use_denoising=True
    target=Vector((0,-.015,1.395));camera=scene.camera
    camera.location=target+Vector((1.05,-2.4,.56) if side else (0,-2.6,.32));camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=.53
    scene.render.film_transparent=False;scene.world.node_tree.nodes.get('Background').inputs['Color'].default_value=(.12,.14,.16,1)
    skin=read(P/'SourceAssets/FieldHat20261019/native_head_jason.json')
    mesh=bpy.data.meshes.new('ReferenceNativeNeck');mesh.from_pydata([(x*.01,-y*.01,z*.01) for x,y,z in skin['positions']],[],skin['triangles']);mesh.update()
    head=bpy.data.objects.new('ReferenceNativeNeck_NotExported',mesh);bpy.context.collection.objects.link(head)
    mesh.materials.append(io.mat('NativeNeckReference',color=(.28,.18,.12)))
    for poly in mesh.polygons:poly.use_smooth=True
    bpy.context.view_layer.update();scene.render.filepath=str(R/'Evidence'/(name+'.png'));bpy.ops.render.render(write_still=True)

def main():
    exports=[]
    for row in read(R/'authored.json')['records']:
        d=read(Path(row['authored']));ob,rig=build(d)
        bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);rig.select_set(True);bpy.context.view_layer.objects.active=ob
        fbx=OUT/(row['profile']+'_FieldRangerTop_CollarRepair.fbx')
        bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH','ARMATURE'},add_leaf_bones=False,use_armature_deform_only=True,bake_anim=False,axis_forward='-Y',axis_up='Z',mesh_smooth_type='FACE')
        if row['profile']=='Jason':io.high_sources()
        bpy.ops.file.pack_all();blend=OUT/(row['profile']+'_FieldRangerTop_CollarRepair.blend');bpy.ops.wm.save_as_mainfile(filepath=str(blend));exports.extend([str(fbx),str(blend)])
        if row['profile']=='Jason':
            for side,angle in (('l',12.),('r',-12.)):
                bone=rig.pose.bones['upperarm_'+side];h=bone.matrix.translation.copy();bone.matrix=Matrix.Translation(h)@Matrix.Rotation(math.radians(angle),4,'Y')@Matrix.Translation(-h)@bone.matrix
            bpy.context.view_layer.update();scene=io.icon_io.studio(ob,320,320);scene.cycles.samples=128
            scene.render.filepath=str(R/'ue_field_sweater.png');bpy.ops.render.render(write_still=True)
            io.display_io.export_display('ue_field_sweater',ob,scene.camera)
            bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'FieldRangerTop_CollarRepair_Inventory.blend'))
        print('COLLAR_EXPORT',row['profile'],flush=True);del d;gc.collect()
    (R/'editable.json').write_text(json.dumps(dict(completed=True,exports=exports,icon=str(R/'ue_field_sweater.png'),display=str(R/'Display/ue_field_sweater-display.json'),runtime_tested=False),indent=2),encoding='utf-8')
    diagnosis(read(R/'Before/Jason.json'),'Jason_Before_Front')
    diagnosis(read(R/'Authored/ue_field_sweater/Jason.json'),'Jason_After_Front')
    diagnosis(read(R/'Authored/ue_field_sweater/Jason.json'),'Jason_After_Oblique',True)

if __name__=='__main__':main()
