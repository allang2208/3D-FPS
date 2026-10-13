"""Save the scoped reception light correction; no generation, PIE or rendering."""
from pathlib import Path
from datetime import datetime
import copy
import json
import runpy
import shutil
import traceback
import unreal as u

ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parents[1]
FLOW=PROJECT/'SourceAssets/DungeonFacilityFlow20261007'
TARGET='/Game/GameMaps/L_Dungeon_Randomized'
SUBJECT='/Game/GameMaps/Design/L_ReceptionHall_Subject'
R=runpy.run_path(str(ROOT/'recipe.py'))


def fixture_rows(module):
    """Inspect every stored diffuser face against its assigned emitter."""
    mesh=u.load_asset('/Game/Dungeons/ReceptionHall20261006/Meshes/SM_Reception_LightDiffusers')
    vertices=[]
    for section in range(mesh.get_num_sections(0)):
        data=u.ProceduralMeshLibrary.get_section_from_static_mesh(mesh,0,section)
        vertices += [[v.x,v.y,v.z] for v in data[0]]
    if not vertices:raise RuntimeError('Could not read the imported diffuser geometry')
    rows=[]
    for light in module['lights']:
        x,y,z=light['fixture_anchor_cm']
        verts=[v for v in vertices if abs(v[0]-x)<145 and abs(v[1]-y)<20 and abs(v[2]-(z+14.4))<2]
        if not verts:raise RuntimeError('Missing imported diffuser for '+light['id'])
        lo=[min(v[k] for v in verts) for k in range(3)]
        hi=[max(v[k] for v in verts) for k in range(3)]
        center=[(a+b)*.5 for a,b in zip(lo,hi)]
        rotation=u.Rotator(pitch=light['pitch'],yaw=light.get('yaw',0),roll=light.get('roll',0))
        forward=u.MathLibrary.get_forward_vector(rotation)
        offset=lo[2]-light['position'][2]
        rect=light['type']=='rect'
        if max(abs(center[k]-light['position'][k]) for k in (0,1))>.05 or not .9<offset<1.1 or forward.z>-.9999:
            raise RuntimeError('Fixture direction/placement mismatch: '+light['id'])
        if rect:
            right=u.MathLibrary.get_right_vector(rotation)
            up=u.MathLibrary.get_up_vector(rotation)
            size=[abs(getattr(right,k))*light['source_width_cm']+abs(getattr(up,k))*light['source_height_cm'] for k in ('x','y')]
            if any(abs(size[k]-(hi[k]-lo[k]))>.05 for k in (0,1)):
                raise RuntimeError('Rect source dimensions do not match diffuser: '+light['id'])
        rows.append(dict(id=light['id'],type=light['type'],position_cm=light['position'],
            diffuser_min_cm=lo,diffuser_max_cm=hi,emitter_below_diffuser_cm=offset,
            forward=[forward.x,forward.y,forward.z],intensity=light['intensity'],
            enabled=light['intensity']>0,light_function=light.get('light_function'),
            alignment_ok=True,direction_ok=True))
    return rows


def main():
    report=dict(stage='preparing',revision=R['REVISION'],maps=[],generated=False,
        game_run=False,rendered=False,editor_opened=False,scope='23 reception fixtures')
    receipt=ROOT/'Receipts/install.json'
    def record():receipt.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    previous=None
    try:
        if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
        editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
        if editor and editor.get_game_world():raise RuntimeError('Preserve active PIE')
        if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved maps')
        previous=editor.get_editor_world().get_path_name().split('.')[0] if editor and editor.get_editor_world() else None
        backup=ROOT/'Backups'/datetime.now().strftime('%Y%m%d-%H%M%S')
        for target in (TARGET,SUBJECT):
            rel=target.removeprefix('/Game/')
            sources=[PROJECT/'Content'/(rel+'.umap')]
            for category in ('__ExternalActors__','__ExternalObjects__'):
                folder=PROJECT/'Content'/category/rel
                if folder.exists():sources.extend(p for p in folder.rglob('*') if p.is_file())
            for source in sources:
                dest=backup/source.relative_to(PROJECT)
                dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest)
        for source in (FLOW/'Config/catalog.json',FLOW/'Config/layout-bank-v1.json'):
            dest=backup/source.relative_to(PROJECT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest)
        report['backup']=str(backup);record()
        world=u.EditorLoadingAndSavingUtils.load_map(TARGET)
        generators=u.GameplayStatics.get_all_actors_of_class(world,u.AuthoredDungeonGenerator)
        if len(generators)!=1:raise RuntimeError('Expected one production generator')
        generator=generators[0]
        before=generator.get_editor_property('module_catalog_json')
        (backup/'catalog-before.json').write_text(before,encoding='utf8')
        catalog=json.loads(before)
        contract=runpy.run_path(str(FLOW/'restore_entry_recipe.py'))['contract_hash']
        bank=catalog['facility_flow']['layout_bank']
        old_hash=contract(catalog)
        if bank['contract_sha1']!=old_hash:raise RuntimeError('Preserve unrelated layout-bank changes')
        placements=copy.deepcopy(bank['entries'])
        module=next(m for m in catalog['modules'] if m['id']==R['MODULE_ID'])
        report['changes']=R['apply_module'](module)
        report['per_fixture']=fixture_rows(module)
        bank['contract_sha1']=contract(catalog)
        bank['reception_fixture_lighting_update']=dict(revision=R['REVISION'],source_contract_sha1=old_hash,placement_data_changed=False)
        if bank['entries']!=placements:raise RuntimeError('Unexpected layout placement change')
        generator.modify();generator.set_editor_property('module_catalog_json',json.dumps(catalog,ensure_ascii=False))
        dirty=list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())
        owned=[p for p in dirty if p.get_name()==TARGET or any(p.get_name().lower().startswith('/game/'+f+'/gamemaps/l_dungeon_randomized/') for f in ('__externalactors__','__externalobjects__'))]
        if owned and not u.EditorLoadingAndSavingUtils.save_packages(owned,False):raise RuntimeError('Production external actor save failed')
        if not u.EditorLoadingAndSavingUtils.save_map(world,TARGET):raise RuntimeError('Production map save failed')
        (FLOW/'Config/catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf8')
        (FLOW/'Config/layout-bank-v1.json').write_text(json.dumps(bank,ensure_ascii=False,separators=(',',':')),encoding='utf8')
        report['maps'].append(dict(path=TARGET,saved=True,lights=23));report['stage']='production_saved';record()
        world=u.EditorLoadingAndSavingUtils.load_map(SUBJECT)
        if not world:raise RuntimeError('Could not load reception subject')
        changed=R['apply_subject']()
        if len(changed)!=23:raise RuntimeError('Expected 23 existing reception subject lamps')
        u.EditorAssetLibrary.set_metadata_tag(world,'Reception.FixtureLighting',R['REVISION'])
        if not u.EditorLoadingAndSavingUtils.save_map(world,SUBJECT):raise RuntimeError('Reception subject save failed')
        report['maps'].append(dict(path=SUBJECT,saved=True,lights=len(changed)))
        report.update(stage='maps_saved',subject_lights=changed,bank_contract_sha1=bank['contract_sha1'],
            fixture_alignment_checked=True,rendered=False,runtime_tested=False)
        record()
        print('RECEPTION_LIGHTING_SAVED',len(report['per_fixture']),'fixtures;',len(report['maps']),'maps;',bank['contract_sha1'])
    except Exception:
        report['error']=traceback.format_exc();record();raise
    finally:
        if previous and previous.startswith('/Game/') and '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
            u.EditorLoadingAndSavingUtils.load_map(previous)


if __name__=='__main__':main()
