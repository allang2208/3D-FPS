"""Editable native garments and matching production inventory assets."""
import gc,importlib.util,json,math,sys
from pathlib import Path
import bpy
from mathutils import Matrix
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ChainmailTorsoRepair20261021';OUT=R/'Exports'
OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(P/'Tools/FieldRangerTop'))
import export_editable as io
sys.path.insert(0,str(P/'Tools/ModularOutfit'))
import build_chainmail_interlace as surface
io.R=R;io.OUT=OUT;io.display_io.OUT=R/'Display';io.display_io.OUT.mkdir(exist_ok=True)
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def materials(d):
    mats=[surface.baked_material(),surface.plain_material('ForgedSteel',(.32,.34,.36),1.,.34),surface.plain_material('DarkBinding',(.023,.019,.016),0.,.78)]
    for m,path in zip(mats,d['materials']):m['UE_Material']=path
    return mats*2 if d['profile']=='Owner_Jason' else mats
io.materials=materials
exports=[]
for profile in ('Body','Jason','Owner_Jason'):
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
    d=read(R/'Authored/ue_chainmail_shirt'/(profile+'.json'));rig=io.rig_io.rig_for(d);ob=io.mesh_for(d,rig)
    if profile=='Owner_Jason':
        for poly in ob.data.polygons:poly.hide=poly.material_index>=3
    bpy.context.view_layer.update();bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);ob.select_set(True);bpy.context.view_layer.objects.active=ob
    fbx=OUT/(profile+'_ChainmailTorso.fbx')
    bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH','ARMATURE'},add_leaf_bones=False,use_armature_deform_only=True,bake_anim=False,axis_forward='-Y',axis_up='Z',mesh_smooth_type='FACE')
    blend=OUT/(profile+'_ChainmailTorso.blend');bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(blend));exports.extend([str(fbx),str(blend)])
    if profile=='Jason':
        for side,angle in (('l',12.),('r',-12.)):
            bone=rig.pose.bones['upperarm_'+side];h=bone.matrix.translation.copy();bone.matrix=Matrix.Translation(h)@Matrix.Rotation(math.radians(angle),4,'Y')@Matrix.Translation(-h)@bone.matrix
        bpy.context.view_layer.update();scene=io.icon_io.studio(ob,320,320);scene.cycles.samples=128
        scene.render.filepath=str(R/'ue_chainmail_shirt.png');bpy.ops.render.render(write_still=True)
        io.display_io.export_display('ue_chainmail_shirt',ob,scene.camera)
        bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'ChainmailTorso_Inventory.blend'))
    print('CHAINMAIL_EXPORT',profile,flush=True);del d;gc.collect()
(R/'editable.json').write_text(json.dumps(dict(completed=True,exports=exports,icon=str(R/'ue_chainmail_shirt.png'),display=str(R/'Display/ue_chainmail_shirt-display.json'),runtime_tested=False),indent=2),encoding='utf-8')
