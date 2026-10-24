"""Apply only the three resized furniture actors and their four nightstands."""
import json,runpy,shutil
from pathlib import Path
from datetime import datetime
import unreal as u
R=Path(__file__).resolve().parent;PROJECT=R.parents[2]
MAP='/Game/GameMaps/L_CyberpunkApartment';TAG='Apartment.V14.Furniture'
def apply_upgrade(world):
    if world.get_path_name().split('.')[0]!=MAP:raise RuntimeError('Apartment target required')
    receipt=json.loads((R/'assets_saved.json').read_text(encoding='utf8'))
    actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor)}
    rows=[]
    def place(name,position,scale=(1,1,1),mesh=None):
        a=actors[name];a.modify();a.set_actor_location(u.Vector(*position),False,False)
        a.set_actor_scale3d(u.Vector(*scale))
        if mesh:
            c=a.static_mesh_component;c.set_static_mesh(u.load_asset(receipt['meshes'][mesh]))
            c.set_editor_property('override_materials',[u.load_asset(p) if p else None for p in receipt['materials'][mesh]])
        tags=list(a.get_editor_property('tags'))
        if u.Name(TAG) not in tags:tags.append(u.Name(TAG));a.set_editor_property('tags',tags)
        rows.append(dict(actor=name,position_cm=position,scale=scale,mesh=mesh))
    # Headboard outer back is local Y=-123. Keep 5 cm off the finished wall.
    for room,x,wall in [('Bed2',2550.,-1012.5),('Bed3',2620.,-2040.)]:
        y=wall+5+123*1.4
        place('AP_'+room+'_Bed',(x,y,1.8),(1.4,1.4,1),'Bed')
        for side in (-1,1):
            place(f'AP_Container_{room}_Nightstand_{side}_1',(x+side*198,wall+50,1.8))
    # Rug top 4.65 cm. Enlarged seating keeps the coffee-table approach open.
    place('AP_Living_Sofa',(1125.,-502.5,4.65),(1.2,1.2,1),'Sofa')
    report=dict(furniture=rows,bed_mattress_m=[2.1,2.87],sofa_footprint_m=[3.,1.14],headboard_wall_gap_cm=5,minimum_bed2_door_to_headboard_cm=272.5,minimum_bed3_archive_to_headboard_cm=282.6,sofa_front_to_coffee_table_cm=171.5,standing_height_preserved=True)
    next_revision=R.parent/'RefinementV15'
    if (next_revision/'installed.json').exists():report['v15']=runpy.run_path(str(next_revision/'install_level.py'))['apply_upgrade'](world)
    return report

def main():
    if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve dirty map')
    backup=R/'Backups'/datetime.now().strftime('%Y%m%d-%H%M%S');backup.mkdir(parents=True,exist_ok=True)
    shutil.copy2(PROJECT/'Content/GameMaps/L_CyberpunkApartment.umap',backup/'L_CyberpunkApartment.umap')
    world=u.EditorLoadingAndSavingUtils.load_map(MAP);report=apply_upgrade(world)
    if not u.EditorLoadingAndSavingUtils.save_map(world,MAP):raise RuntimeError('Apartment map save failed')
    report.update(stage='map_saved',map=MAP,backup=str(backup),saved_at=datetime.now().astimezone().isoformat(),game_tested=False)
    (R/'installed.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print('AP14_MAP_SAVED',len(report['furniture']))
if __name__=='__main__':main()
