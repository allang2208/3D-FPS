"""Replace only Blizzard's grid cloud with the current StormDomain cloud layers.

Run through mcp_call_codex.ps1 -PythonScript when the editor is already open.
No level, gameplay, source storm, gathering cloud or material is modified.
"""
import importlib
import json
import sys
from pathlib import Path
import unreal as u

ROOT = Path(u.Paths.project_dir())
sys.path.insert(0, str(ROOT / 'Tools/Skills'))
import build_rolling_storm_clouds as clouds

def run(resume_save=False):
    global clouds
    clouds = importlib.reload(clouds)
    clouds.SOURCE = ROOT / 'SourceAssets/BlizzardStormCloudReuse20261012'
    clouds.SOURCE.mkdir(parents=True, exist_ok=True)
    clouds.REPORT = {'revision': 'BlizzardStormCloudReuse20261012', 'saved_assets': [],
                     'gameplay_tested': False, 'rendered': False}
    material = u.load_asset(clouds.DEST + '/M_RollingStormCloud')
    if not material:
        raise RuntimeError('Restore RollingV1 cloud material first')
    with u.ScopedEditorTransaction('Blizzard - reuse storm domain cloud layers'):
        if resume_save:
            # Resume the known save failure without rebuilding the already
            # authored emitters or overwriting unrelated dirty packages.
            system = u.load_asset(clouds.DEST + '/NS_BlizzardStormCloud')
            if not system or clouds.EAL.get_metadata_tag(system, 'Blizzard.CloudLayout') != 'StormDomainLayers20261012':
                raise RuntimeError('No authored Blizzard cloud to resume')
            for name in clouds.emitters(system):
                clouds.detach_cloud_parent(system, name)
            clouds.REPORT.update(blizzard_layout='StormDomainLayers20261012',
                                 blizzard_source=clouds.DEST + '/NS_StormDomainCloud.NS_StormDomainCloud',
                                 blizzard_cloud_emitters=clouds.emitters(system))
            clouds.persist(system)
        else:
            clouds.blizzard(material)
    clouds.REPORT.update(stage='assets_saved', core_particles=48, fringe_max_approx=8,
                         source_cloud_modified=False, gameplay_modified=False,
                         native_build_required=False)
    (clouds.SOURCE / 'asset-authoring.json').write_text(json.dumps(clouds.REPORT, indent=2), encoding='utf-8')
    print('BLIZZARD_STORM_CLOUD_REUSED ' + json.dumps(clouds.REPORT))


if __name__ == '__main__':
    run()
