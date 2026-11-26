"""Save the detailed ranger hat in a new family; reuse the shirt's materials."""
import gc,hashlib,importlib.util,json,sys
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/FieldRangerFeatherHat20261021';DEST='/Game/Characters/ModularOutfit20260924/FieldRangerFeatherHat20261021'
KEY='ue_ranger_feather_hat';E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary;G=u.GeometryScript_AssetUtils
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,str(P/path));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def save(a):
    if not a.get_path_name().startswith(DEST+'/'):raise RuntimeError('Outside new hat asset scope')
    a.modify()
    if not E.save_loaded_asset(a,False):raise RuntimeError('Could not save '+a.get_path_name())
def material_assets():
    shared=read(P/'SourceAssets/FieldRangerTop20261020/materials.json')['materials'];mats=[u.load_asset(x) for x in shared]
    if not all(mats):raise RuntimeError('Shared ranger shirt materials are missing')
    feather=u.load_asset(DEST+'/Materials/M_RangerFeather')
    if not feather:
        feather=A.create_asset('M_RangerFeather',DEST+'/Materials',u.Material,u.MaterialFactoryNew());L.set_material_usage(feather,u.MaterialUsage.MATUSAGE_SKELETAL_MESH);L.set_material_usage(feather,u.MaterialUsage.MATUSAGE_STATIC_MESH)
        for channel in ('BaseColor','Normal','ORM'):
            task=u.AssetImportTask();task.filename=str(R/'Textures'/('Feather_'+channel+'.png'));task.destination_path=DEST+'/Textures';task.destination_name='T_RangerFeather_'+channel;task.automated=True;task.replace_existing=True;task.save=False
            A.import_asset_tasks([task]);texture=u.load_asset(DEST+'/Textures/'+task.destination_name)
            texture.set_editor_property('srgb',channel=='BaseColor');texture.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if channel=='Normal' else u.TextureCompressionSettings.TC_MASKS if channel=='ORM' else u.TextureCompressionSettings.TC_DEFAULT)
            texture.set_editor_property('never_stream',False)
            if channel=='Normal':texture.set_editor_property('flip_green_channel',True)
            save(texture);n=L.create_material_expression(feather,u.MaterialExpressionTextureSampleParameter2D);n.set_editor_property('parameter_name',channel);n.set_editor_property('texture',texture)
            n.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL if channel=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_MASKS if channel=='ORM' else u.MaterialSamplerType.SAMPLERTYPE_COLOR)
            outputs=[('RGB',u.MaterialProperty.MP_BASE_COLOR)] if channel=='BaseColor' else [('RGB',u.MaterialProperty.MP_NORMAL)] if channel=='Normal' else [('R',u.MaterialProperty.MP_AMBIENT_OCCLUSION),('G',u.MaterialProperty.MP_ROUGHNESS),('B',u.MaterialProperty.MP_METALLIC)]
            for pin,prop in outputs:
                if not L.connect_material_property(n,pin,prop):raise RuntimeError('Feather material connection failed')
        errors=L.recompile_material(feather)
        if errors:raise RuntimeError('Feather material compile failed '+str(errors))
        save(feather)
    quill=u.load_asset(DEST+'/Materials/M_RangerQuill')
    if not quill:
        quill=A.create_asset('M_RangerQuill',DEST+'/Materials',u.Material,u.MaterialFactoryNew());L.set_material_usage(quill,u.MaterialUsage.MATUSAGE_SKELETAL_MESH);L.set_material_usage(quill,u.MaterialUsage.MATUSAGE_STATIC_MESH)
        n=L.create_material_expression(quill,u.MaterialExpressionConstant3Vector);n.set_editor_property('constant',u.LinearColor(.36,.27,.16,1));L.connect_material_property(n,'',u.MaterialProperty.MP_BASE_COLOR)
        n=L.create_material_expression(quill,u.MaterialExpressionConstant);n.set_editor_property('r',.48);L.connect_material_property(n,'',u.MaterialProperty.MP_ROUGHNESS)
        errors=L.recompile_material(quill)
        if errors:raise RuntimeError('Quill material compile failed '+str(errors))
        save(quill)
    return mats+[feather,quill]
def imported_fit(mesh,d):
    dm,status=G.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot obtain imported attachment frame')
    bones={str(b.name):b.world_transform.translation for b in u.GeometryScript_BoneWeights.get_all_bones_info(dm)[1]};names=['HatRoot','FitFront','FitLeft'];K=u.MathLibrary
    authored=[u.Vector(*d['bones'][n]['position']) for n in names];actual=[bones[n] for n in names]
    scale=(actual[1]-actual[0]).length()/(authored[1]-authored[0]).length()
    before=u.Transform(location=authored[0],rotation=K.make_rot_from_xy(authored[1]-authored[0],authored[2]-authored[0]))
    after=u.Transform(location=actual[0],rotation=K.make_rot_from_xy(actual[1]-actual[0],actual[2]-actual[0]),scale=u.Vector(scale,scale,scale))
    correction=K.compose_transforms(K.invert_transform(after),before);result={}
    for key,fit in read(R/'fit.json')['fits'].items():
        pitch,yaw,roll=fit['rotation'];target=u.Transform(location=u.Vector(*fit['location']),rotation=u.Rotator(pitch=pitch,yaw=yaw,roll=roll),scale=u.Vector(*fit['scale']))
        target=K.compose_transforms(correction,target);rot=target.rotation.rotator()
        result[key]=dict(location=[target.translation.x,target.translation.y,target.translation.z],rotation=[rot.pitch,rot.yaw,rot.roll],scale=[target.scale3d.x,target.scale3d.y,target.scale3d.z])
    return result,{n:[bones[n].x,bones[n].y,bones[n].z] for n in names}
def main():
    if '-run=' not in u.SystemLibrary.get_command_line().lower():
        level=u.get_editor_subsystem(u.LevelEditorSubsystem)
        if level and level.is_in_play_in_editor():raise RuntimeError('End play before importing the ranger hat')
    production=read(R/'authored.json')
    if not production['completed']:raise RuntimeError('Complete Blender production first')
    d=read(R/'Authored/hat.json');mats=material_assets()
    io=module('ranger_hat_mesh_io','Tools/FieldHat/save_assets.py');io.SRC=R;io.DEST=DEST;io.SLOTS=d['material_slots'];io.receipt_path=R/'saved_assets.json';io.receipt=read(io.receipt_path) if io.receipt_path.exists() else dict(runtime_tested=False)
    io.receipt.update(completed=False,materials=[m.get_path_name() for m in mats]);io.record()
    mesh=io.skeletal(mats,d)
    # FBX can reorder material slots. Assign each struct back by index.
    slots=list(mesh.get_editor_property('materials'));byname=dict(zip(d['material_slots'],mats))
    for i,slot in enumerate(slots):
        name=str(slot.get_editor_property('imported_material_slot_name'));slot.set_editor_property('material_interface',byname[name]);slot.set_editor_property('material_slot_name',name);slots[i]=slot
    mesh.set_editor_property('materials',slots);E.set_metadata_tag(mesh,'EquipmentDefinition',KEY);save(mesh)
    fits,frames=imported_fit(mesh,d)
    static=module('ranger_hat_static_io','Tools/ChainmailPants/save_assets.py');static.DEST=DEST
    dynamic=module('ranger_hat_display_io','Tools/BlueMageSetIcons/save_icons.py').dynamic;T=u.GeometryScript_MeshTransforms
    dm=dynamic(d);center=[(min(p[i] for p in d['positions'])+max(p[i] for p in d['positions']))*.5 for i in range(3)];T.translate_mesh(dm,u.Vector(*[-x for x in center]))
    io.receipt['pickup']=static.static(dm,DEST+'/Pickups/SM_RangerFeatherHat',mats);io.record()
    dm=dynamic(read(R/(KEY+'-display.json')));T.inverse_transform_mesh(dm,u.Transform(rotation=u.Rotator(pitch=0,yaw=-90,roll=0)))
    io.receipt['icon']=static.static(dm,DEST+'/Icons/SM_RangerFeatherHat_Icon',mats);io.record()
    task=u.AssetImportTask();task.filename=str(R/(KEY+'.png'));task.destination_path=DEST+'/Icons';task.destination_name='T_RangerFeatherHat_Icon';task.automated=True;task.replace_existing=True;task.save=False
    A.import_asset_tasks([task]);texture=u.load_asset(DEST+'/Icons/T_RangerFeatherHat_Icon')
    for k,v in dict(lod_group=u.TextureGroup.TEXTUREGROUP_UI,compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON,mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS,srgb=True).items():texture.set_editor_property(k,v)
    save(texture)
    io.receipt.update(completed=True,icon_texture=texture.get_path_name(),fit=fits,imported_fit_frame=frames,source_triangles=len(d['triangles']),source_vertices=len(d['positions']),tip_bones=['FeatherBase','FeatherMid','FeatherTip'],runtime_tested=False)
    io.record();print('RANGER_FEATHER_HAT_SAVED',flush=True)
if __name__=='__main__':main()
