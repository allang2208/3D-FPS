"""Restore only the warehouse's four original floor material bindings."""
from pathlib import Path
from datetime import datetime
import json,shutil,traceback
import unreal as u
ROOT=Path(__file__).resolve().parent;TASK=ROOT.parent;PROJECT=TASK.parents[1]
TARGET='/Game/GameMaps/Design/L_FreightTransit_Theme_Subject'
RECEIPT=ROOT/'install.json'

def main():
    if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
    editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if editor and editor.get_game_world():raise RuntimeError('Preserve active gameplay')
    if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved maps')
    suffix=TARGET.removeprefix('/Game/').lower()
    prefixes=tuple('/game/'+folder+'/'+suffix+'/' for folder in ('__externalactors__','__externalobjects__'))
    if any(p.get_name().lower().startswith(prefixes) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
        raise RuntimeError('Preserve unsaved subject actor packages')
    previous=editor.get_editor_world().get_path_name().split('.')[0] if editor and editor.get_editor_world() else ''
    rows=[r for r in json.loads((TASK/'Receipts/install.json').read_text('utf8'))['material_bindings'] if r['after']=='Floor']
    if len(rows)!=4:raise RuntimeError('Original warehouse floor bindings unavailable')
    report=dict(stage='preparing',map=TARGET,bindings=[],tests_run=False,game_run=False,rendered=False)
    def record():RECEIPT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    try:
        world=u.EditorLoadingAndSavingUtils.load_map(TARGET)
        if not world:raise RuntimeError('Subject map unavailable')
        actors={a.get_name():a for a in u.GameplayStatics.get_all_actors_of_class(world,u.StaticMeshActor)}
        components=[]
        revised='/Game/SceneTests/FreightWarehouseWeathering20261110/Materials/'
        allowed={revised+n+'.'+n for n in ('MI_FloorAged','MI_FloorReliefV2')}
        for row in rows:
            actor=actors[row['actor']]
            c=next(c for c in actor.get_components_by_class(u.StaticMeshComponent) if c.get_name()==row['component'])
            current=c.get_material(row['slot']).get_path_name()
            if c.static_mesh.get_path_name()!=row['mesh'] or current not in allowed|{row['before']}:
                raise RuntimeError('Preserve changed floor binding '+row['actor'])
            original=u.load_asset(row['before'])
            if not original:raise RuntimeError('Original floor material unavailable')
            components.append((actor,c,row,original,current))
        backup=ROOT/'Backups'/datetime.now().strftime('%Y%m%d-%H%M%S')
        relative=TARGET.removeprefix('/Game/')
        for path in [PROJECT/'Content'/(relative+'.umap')]+[PROJECT/'Content'/folder/relative for folder in ('__ExternalActors__','__ExternalObjects__')]:
            if not path.exists():continue
            dest=backup/path.relative_to(PROJECT);dest.parent.mkdir(parents=True,exist_ok=True)
            if path.is_dir():shutil.copytree(path,dest)
            else:shutil.copy2(path,dest)
        report['backup']=str(backup);record()
        for actor,c,row,original,current in components:
            actor.modify();c.modify();c.set_material(row['slot'],original)
            report['bindings'].append(dict(actor=actor.get_name(),mesh=row['mesh'],before=current,after=original.get_path_name()))
        dirty=list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())
        owned=[p for p in dirty if p.get_name()==TARGET or p.get_name().lower().startswith(prefixes)]
        if owned and not u.EditorLoadingAndSavingUtils.save_packages(owned,False):raise RuntimeError('Subject package save failed')
        if not u.EditorLoadingAndSavingUtils.save_map(world,TARGET):raise RuntimeError('Subject map save failed')
        current=TASK/'Receipts/assets.json'
        state=json.loads(current.read_text('utf8'))
        if not (ROOT/'assets-before-rollback.json').exists():shutil.copy2(current,ROOT/'assets-before-rollback.json')
        state['materials']['Floor']=rows[0]['before']
        state['revision']='original_surfaces_restored'
        state['materials']['saved_assets']=[]
        current.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf8')
        report.update(stage='map_saved',entry_command='open '+TARGET,
            preserved=['restored wall','props','decals','lighting','layout','gameplay','comparison map'])
        record();print('FREIGHT_ORIGINAL_FLOORS_RESTORED '+TARGET,flush=True)
        if previous and not previous.startswith('/Temp/') and previous!=TARGET:u.EditorLoadingAndSavingUtils.load_map(previous)
    except Exception:
        report['error']=traceback.format_exc();record();raise

if __name__=='__main__':main()
