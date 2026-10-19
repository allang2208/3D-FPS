"""Export the four corrected native bodies and their 3D inventory subject."""
import json,sys,gc,math
from pathlib import Path
import bpy,numpy as np
from mathutils import Vector,Matrix
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/BlueMageRobe20261018';OUT=R/'FacingFix20261020';EXPORT=OUT/'Exports'
sys.path.insert(0,str(P/'Tools/BlueMageRobe'));import save_editable as io
sys.path.insert(0,str(P/'Tools/BlueMageSetIcons'));from render_icons import export_display

def main():
    EXPORT.mkdir(exist_ok=True);exports=[]
    for profile in ('Body','Body_Owner','Jason','Jason_Owner'):
        bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
        d=json.loads((OUT/'Authored'/(profile+'.json')).read_text());mats=io.materials();rig=io.rig_for(d);ob=io.mesh_for(d,rig,mats);bpy.context.view_layer.update()
        bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);rig.select_set(True);bpy.context.view_layer.objects.active=ob
        fbx=EXPORT/(profile+'_BlueMageRobe.fbx')
        bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH','ARMATURE'},add_leaf_bones=False,use_armature_deform_only=True,bake_anim=False,axis_forward='-Y',axis_up='Z',mesh_smooth_type='FACE')
        proxy=io.mesh_for(d,rig,mats,True);proxy.hide_render=True;proxy.hide_set(True);proxy['Usage']='Unchanged Chaos skirt source, not visible garment'
        bpy.ops.file.pack_all();blend=EXPORT/(profile+'_BlueMageRobe.blend');bpy.ops.wm.save_as_mainfile(filepath=str(blend));exports.extend([str(fbx),str(blend)])
        if profile=='Jason':
            # Model-only icon source; preserve the existing PNG and do not run
            # a preview render. Blender reflects native +Y forward to -Y.
            for side,angle in (('l',12.),('r',-12.)):
                bone=rig.pose.bones['upperarm_'+side];h=bone.matrix.translation.copy();bone.matrix=Matrix.Translation(h)@Matrix.Rotation(math.radians(angle),4,'Y')@Matrix.Translation(-h)@bone.matrix
            bpy.context.view_layer.update();points=np.array([tuple(ob.matrix_world@v.co) for v in ob.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices]);center=Vector((points.min(0)+points.max(0))*.5);span=float(np.max(points.max(0)-points.min(0)))
            camera=bpy.data.objects.new('InventoryFront',bpy.data.cameras.new('InventoryFront'));bpy.context.scene.collection.objects.link(camera);camera.location=center+Vector((0,-3,.12))*span;camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler();bpy.context.view_layer.update()
            display=P/'SourceAssets/BlueMageSetIcons20261019/ue_blue_mage_robe-display.json';backup=OUT/'Before'/'inventory-display.json'
            if display.exists() and not backup.exists():backup.write_bytes(display.read_bytes())
            export_display('ue_blue_mage_robe',ob,camera)
        print('ROBE_FACING_EXPORT',profile,flush=True);del d;gc.collect()
    (OUT/'editable_receipt.json').write_text(json.dumps(dict(completed=True,exports=exports,preview_rendered=False,icon_png_unchanged=True),indent=2),encoding='utf-8')
    path=R/'editable_receipt.json';receipt=json.loads(path.read_text());receipt['exports']=[p for p in receipt.get('exports',[]) if Path(p).name not in {Path(x).name for x in exports}]+[p for p in exports if p.endswith('.fbx')];receipt['active_body_revision']='FacingFix20261020';path.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
if __name__=='__main__':main()
