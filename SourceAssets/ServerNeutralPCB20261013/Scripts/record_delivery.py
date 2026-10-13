"""Record production output and native build completion without runtime tests."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
def read(name):return json.loads((ROOT/name).read_text('utf-8-sig'))
models=read('model_manifest.json');icons=read('inventory_icons.json')
installed=read('Receipts/installation.json');published=read('Receipts/publication.json')
builds=read('Receipts/native-build.json');imported=read('Receipts/ue-import.json')
legacy=read('Receipts/legacy-appearance.json')
report=dict(stage='neutral_pcb_models_and_icons_published',item_ids=list(published['after']),
    mesh_count=len(imported['meshes']),material_count=len(imported['materials']),texture_count=len(imported['textures']),
    installed_packages=len(installed['packages']),icon_count=len(icons['icons']),
    models={key:dict(mesh=a['mesh'],palette=a['palette'],dimensions_cm=a['actual_dimensions_cm'],
        triangles=a['triangles_lod0'],texture_size=a['size']) for key,a in models['assets'].items()},
    geometry='Existing detailed geometry retained; authored materials and exported models updated together',
    changed_surfaces=['PCB front and reverse','laminate edges','cache daughterboard','processor substrate',
        'board traces and printed labels','former green network port lenses'],
    icon_orientation='upper_left_45',old_assets_preserved=True,footprints_changed=False,rarities_changed=False,prices_changed=False,
    tests_run=False,game_started=False,additional_previews_rendered=False,
    native_build_attempt=builds,material_compile_errors=imported['material_compile_errors'],
    native_code_required=False,native_source_changes_retained=False,
    legacy_appearance=legacy,
    saved_instance_appearance='Six old BaseColor/ORM texture packages and three old PNG paths refreshed; saved mesh and icon references remain usable without native migration')
(ROOT/'delivery.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('NEUTRAL_PCB_DELIVERY_SAVED',report['models'],builds['stage'])
