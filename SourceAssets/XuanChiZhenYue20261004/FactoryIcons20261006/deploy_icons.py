"""Deploy only Zhenyue factory blade-II and horizontal grip icons."""
import json
import shutil
from pathlib import Path

P = Path(__file__).resolve().parent
ROOT = P.parents[2]
D = ROOT / 'Content/ColdSteelData/AttachmentIcons20260913'
ASSET_ROOT = '/Game/ColdSteelData/AttachmentIcons20260913/'
SOURCES = {
    'ue_xuanchi_zhenyue_blade_2_false': ('blade_2_factory_framed.png', 'blade_2'),
    'ue_xuanchi_zhenyue_grip_false': ('grip_factory_horizontal_framed.png', 'grip'),
    'ue_xuanchi_zhenyue_category_grip': ('grip_factory_horizontal_framed.png', 'grip'),
}

def deploy():
    before = P / 'Before'
    before.mkdir(exist_ok=True)
    manifest = P.parent / 'ModelV1/Icons/deployments.json'
    if not (before / 'deployments.json').exists():
        shutil.copy2(manifest, before / 'deployments.json')
    jobs = json.loads(manifest.read_text(encoding='utf-8-sig'))
    changed = []
    for key, (filename, slot) in SOURCES.items():
        source = P / 'Icons' / filename
        for extension in ('.png', '.uasset'):
            old = D / (key + extension)
            if old.exists() and not (before / old.name).exists():
                shutil.copy2(old, before / old.name)
        destination = D / (key + '.png')
        shutil.copy2(source, destination)
        job = {'source': str(source), 'file': str(destination),
               'asset': ASSET_ROOT + key, 'slot': slot}
        index = next((i for i, entry in enumerate(jobs) if entry['asset'] == job['asset']), None)
        if index is None:
            jobs.append(job)
        else:
            jobs[index] = job
        changed.append(job)
    manifest.write_text(json.dumps(jobs, indent=2) + '\n', encoding='utf-8')
    (P / 'deployments.json').write_text(json.dumps(changed, indent=2) + '\n', encoding='utf-8')
    return changed

if __name__ == '__main__':
    deploy()
