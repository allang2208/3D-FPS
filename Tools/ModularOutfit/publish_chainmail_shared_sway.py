"""Publish the complete shared-layer family after its native module is built."""

if __name__ == "__main__":
    raise RuntimeError("Historical garment publication retired. Use garment_pipeline.py candidates and gate; do not overwrite current rig-specific repairs.")

import json
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ChainmailSharedSway20260929'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,data):p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def main():
    path=P/'Content/ColdSteelData/modular_outfits.json';config=read(path);recipe=config['items']['ue_chainmail_shirt']
    before=read(R/'before.json')['recipe'];interim=read(R/'interim.json')['recipe']
    if recipe not in [before,interim] and recipe.get('appearance_family')!=R.name:raise RuntimeError('Concurrent chainmail recipe change; keep current data')
    records={r['profile']:read(R/'Saved'/(r['profile']+'.json')) for r in read(R/'manifest.json')}
    build=read(R/'native-build.json')
    if not build.get('complete'):raise RuntimeError('Native full build still pending')
    rigs=dict(interim['rig_meshes']);rigs.update({k:v['mesh'] for k,v in records.items()})
    recipe.update(appearance_family=R.name,secondary_motion='chainmail_shared_sway_v1',material='',rig_meshes=rigs)
    write(path,config)
    write(R/'published.json',dict(recipe=recipe,profiles=records,native_build=build,cloth_particles=0,
        new_animations=0,stats_changed=False,icon_preserved=True,body_preserved=True,runtime_tested=False,refresh='next game session'))
    print('CHAINMAIL_SHARED_SWAY_PUBLISHED',len(records),'first-person profiles')
if __name__=='__main__':main()
