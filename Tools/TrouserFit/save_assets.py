"""Background save of the six corrected wearables and two display/pickup pairs."""
import importlib.util,json,hashlib,gc
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/TrouserFit20261018';DEST='/Game/Characters/ModularOutfit20260924/TrouserFit20261018'
spec=importlib.util.spec_from_file_location('trouser_native_mesh_writer',str(P/'Tools/ST6LowerSet/save_assets.py'));core=importlib.util.module_from_spec(spec);spec.loader.exec_module(core)
core.R=R;core.DEST=DEST;core.io.DEST=DEST;core.receipt_path=R/'saved_assets.json'
core.receipt=json.loads(core.receipt_path.read_text()) if core.receipt_path.exists() else dict(saved=[],meshes={},runtime_tested=False)
def main():
    core.E.make_directory(DEST);rows=json.loads((R/'fit_inventory.json').read_text())['paths']
    for item,old,label,slots in [
        ('ue_leather_pants','BrownLeatherSet20261004','LeatherPants',['Steel','Leather','UnusedSole','Thread','Reinforcement']),
        ('ue_chainmail_pants','ChainmailPants20261004/ArmorRefineV2','ChainmailPants',['Mail','ForgedSteel','Lining'])]:
        materials=[core.load(p) for p in json.loads((P/'SourceAssets'/old/'saved_assets.json').read_text())['materials']]
        core.receipt.setdefault('materials',{})[item]=[m.get_path_name() for m in materials]
        for row in rows:
            if row['item']!=item:continue
            file=Path(row['output']);sha=hashlib.sha256(file.read_bytes()).hexdigest();same_source=core.receipt.get('source_sha256',{}).get(str(file))==sha
            mesh_path=core.receipt.get('meshes',{}).get('SK_'+file.stem)
            existing=u.load_asset(mesh_path) if mesh_path else None
            if not (same_source and existing and core.E.get_metadata_tag(existing,'ST6SourceSHA')==sha):core.skeletal(file,'SK_'+file.stem,materials,slots)
            existing=None
            if 'standard' in row['uses']:
                already_saved=same_source and all(core.E.does_asset_exist(core.receipt.get('meshes',{}).get(label+'_'+kind,'')) for kind in ('icon','pickup'))
                if not already_saved:core.displays(file,label,materials)
            gc.collect();u.SystemLibrary.collect_garbage()
    core.receipt['completed']=True;core.record();print('TROUSER_FIT_ASSETS_SAVED',flush=True)
    import runpy
    runpy.run_path(str(P/'Tools/TrouserFit/save_icons.py'),run_name='__main__')
    runpy.run_path(str(P/'Tools/TrouserFit/publish.py'),run_name='__main__')
if __name__=='__main__':main()
