"""Save only the two flight systems and their materials; no previews or tests."""
import importlib
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
import unreal as u

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'SourceAssets/MeteorFlightSurface20261114'
DEST='/Game/Skills/FireMagic20260921/MeteorCombustionV6/'
sys.path.insert(0,str(ROOT/'Tools/Skills'))
if hasattr(u,'DragonBreathAuthorLibrary'):u.RainAssetEditor=u.DragonBreathAuthorLibrary
import meteor_flight_surface_recipe as recipe
importlib.reload(recipe)

def run():
    if Path(u.Paths.project_content_dir()).resolve()!=(ROOT/'Content').resolve():
        raise RuntimeError('Use the live FPSGAME content author host')
    names=['NS_MeteorSheathV6','NS_MeteorSlipstreamV6','M_MeteorSheathV6','M_MeteorWakeSmokeV6']
    dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    conflicts=dirty.intersection(DEST+n for n in names)
    if conflicts:raise RuntimeError('Preserve unsaved flight targets: '+str(sorted(conflicts)))
    backup=OUT/'BeforeAssets';backup.mkdir(parents=True,exist_ok=True)
    for name in names:
        source=ROOT/'Content'/DEST.removeprefix('/Game/')/(name+'.uasset')
        target=backup/source.name
        if not target.exists():shutil.copy2(source,target)
    profile=recipe.sample_surface()
    (OUT/'rock-flame-surface.json').write_text(json.dumps(profile,indent=2),encoding='utf8')
    mantle,tail,fire,smoke=[u.load_asset(DEST+n) for n in names]
    recipe.apply(mantle,tail,fire,smoke,profile)
    compiler=u.DragonBreathAuthorLibrary if hasattr(u,'DragonBreathAuthorLibrary') else u.PoisonMaggotMonster
    if not compiler.compile_material_assets([fire,smoke]):raise RuntimeError('Flight material compile failed')
    for system in [mantle,tail]:
        if not u.RainAssetEditor.compile_rain(system,True):raise RuntimeError('Flight Niagara compile failed: '+system.get_name())
    saved=[]
    for asset in [fire,smoke,mantle,tail]:
        if not u.EditorAssetLibrary.save_loaded_asset(asset,False):raise RuntimeError('Save failed: '+asset.get_path_name())
        saved.append(asset.get_path_name())
    receipt=dict(saved_at=datetime.now().isoformat(),saved_assets=saved,source_rock=profile['mesh'],surface_samples=48,
        mantle_emission_rate=66,trail_emission_rate_max=124,flight_particle_upper_bound=90,
        source_texture='unchanged original Mantaflow wake atlas',added_lights=0,added_components=0,
        added_runtime_geometry_queries=0,rendered=False,tested=False,
        protected=['current V7 impact and radial sparks','V4 low ground fire','rock mesh and material','gameplay values','sound','camera'])
    (OUT/'assets-saved.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
    print('METEOR_FLIGHT_SURFACE_SAVED '+json.dumps(receipt),flush=True)

if __name__=='__main__':run()
