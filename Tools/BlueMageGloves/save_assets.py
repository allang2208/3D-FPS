"""Save each native glove and its shared surface maps under the new item family."""
import sys,json,hashlib,gc,importlib.util
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/BlueMageGloves20261019';DEST='/Game/Characters/ModularOutfit20260924/BlueMageGloves20261019'
sys.path.insert(0,str(P/'Tools/ModularOutfit'));sys.path.insert(0,str(Path(__file__).parent));import materials
import import_tailored_fingerless_candidate as native
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();S=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem);native.S=S
receipt_path=R/'saved_assets.json';receipt=json.loads(receipt_path.read_text()) if receipt_path.exists() else dict(profiles={},runtime_tested=False)
def record():receipt_path.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
def save(asset):
    if not asset.get_path_name().startswith(DEST+'/'):raise RuntimeError('Outside mage glove output scope')
    asset.modify()
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Cannot save '+asset.get_path_name())
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,str(P/path));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def display_dynamic(d):
    positions=[];normals=[];uv=[];triangles=[]
    for fi,face in enumerate(d['triangles']):
        start=len(positions)
        for ci,vi in enumerate(face):positions.append(u.Vector(*d['positions'][vi]));normals.append(u.Vector(*d['normals'][fi][ci]));uv.append(u.Vector2D(*d['uv'][fi][ci]))
        triangles.append(u.IntVector(start,start+1,start+2))
    dm=u.DynamicMesh();u.GeometryScript_MeshEdits.append_buffers_to_mesh(dm,u.GeometryScriptSimpleMeshBuffers(vertices=positions,normals=normals,uv0=uv,triangles=triangles),0,True)
    for fi,slot in enumerate(d['triangle_materials']):u.GeometryScript_Materials.set_triangle_material_id(dm,fi,slot,True)
    return dm
def main():
    if '-run=' not in u.SystemLibrary.get_command_line().lower():
        level=u.get_editor_subsystem(u.LevelEditorSubsystem)
        if level and level.is_in_play_in_editor():raise RuntimeError('Preserve current PIE assets')
    receipt['completed']=False;record();E.make_directory(DEST)
    if receipt.get('materials'):mats={k:[native.load(p) for p in paths] for k,paths in receipt['materials'].items()}
    else:
        metal=native.load('/Game/Characters/ModularOutfit20260924/BlueMageRobe20261018/Materials/M_BlueMage_Silver');gem=native.load('/Game/Characters/ModularOutfit20260924/BlueMageRobe20261018/Materials/M_BlueMage_Gem')
        mats={name:[materials.build(name,R,DEST,save,native.load,P/'Tools/ModularOutfit/black_leather_relief.ush'),metal,gem] for name in ('M4','Body')};receipt['materials']={k:[m.get_path_name() for m in v] for k,v in mats.items()};record()
    for row in json.loads((R/'manifest.json').read_text())['rows']:
        name=row['profile'];raw=Path(row['authored']).read_bytes();sha=hashlib.sha256(raw).hexdigest();old=receipt['profiles'].get(name)
        if old and old['source_sha256']==sha:continue
        d=json.loads(raw);mesh=native.build_mesh(d,'SK_'+name+'_BlueMageGloves',mats[row['group']],d['material_slots'],DEST)
        E.set_metadata_tag(mesh,'EquipmentDefinition','ue_blue_mage_gloves');E.set_metadata_tag(mesh,'BlueMageGlovesSHA',sha);save(mesh)
        receipt['profiles'][name]=dict(asset=mesh.get_path_name(),source=row['source'],source_sha256=sha,triangles=row['triangles'],lod_count=S.get_lod_count(mesh),group=row['group'],aliases=row['aliases']);record();print('MAGE_GLOVES_SAVED',name,flush=True);gc.collect();u.SystemLibrary.collect_garbage()
    if (R/'Authored/Display.json').exists():
        static=module('mage_glove_static_io','Tools/ChainmailPants/save_assets.py');static.DEST=DEST
        data=json.loads((R/'Authored/Display.json').read_text())
        for kind in ('Icon','Pickup'):
            if receipt.get(kind.lower()):continue
            dm=display_dynamic(data);receipt[kind.lower()]=static.static(dm,DEST+'/'+kind+'s/SM_BlueMageGlove_'+kind,mats['M4']);record()
    if (R/'ue_blue_mage_gloves.png').exists() and not receipt.get('icon_texture'):
        task=u.AssetImportTask();task.filename=str(R/'ue_blue_mage_gloves.png');task.destination_path=DEST+'/Icons';task.destination_name='T_BlueMageGloves_Icon';task.automated=True;task.replace_existing=True;task.save=False;A.import_asset_tasks([task]);tex=native.load(DEST+'/Icons/T_BlueMageGloves_Icon')
        for prop,value in dict(lod_group=u.TextureGroup.TEXTUREGROUP_UI,compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON,mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS,srgb=True).items():tex.set_editor_property(prop,value)
        save(tex);receipt['icon_texture']=tex.get_path_name();record()
    sys.path.insert(0,str(P/'Tools/BlueMageSetIcons'))
    from save_icons import apply_item
    apply_item('ue_blue_mage_gloves')
    receipt['completed']=bool(receipt.get('icon_texture') and receipt.get('pickup') and receipt.get('icon'));record();print('MAGE_GLOVES_ASSETS_COMPLETE',receipt['completed'],len(receipt['profiles']),flush=True)
if __name__=='__main__':main()
