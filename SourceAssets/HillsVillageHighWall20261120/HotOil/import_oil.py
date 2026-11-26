from pathlib import Path
import json,os,sys
import unreal as ue
src=Path(__file__).resolve().parent
root=src.parents[2]
os.environ['HIGH_VILLAGE_PROJECT']=str(root)
sys.path.insert(0,str(root/'Tools/WorldGeneration/HighVillageDefense'))
import import_kit as kit
dest='/Game/WorldGeneration/TemperateHills/HotOil'
front='/Game/WorldGeneration/TemperateHills/VillageMechanicalWorkshop/Frontage/Materials/MI_'
paths={key:front+key for key in ('ForgedStrap','WheelBrass','SignOak')}
paths.update(Footing='/Game/WorldGeneration/TemperateHills/OldChapel/Materials/M_ChapelFooting',
             Bronze=dest+'/FlowR2/M_OilBody')
hand_only=os.environ.get('VILLAGE_OIL_HAND_POT_ONLY')=='1'
surface_only=os.environ.get('VILLAGE_OIL_SURFACE_ONLY')=='1'
if hand_only:
    roles=('SM_OilHandPot',)
    needed=('SignOak','ForgedStrap','WheelBrass')
elif surface_only:
    roles=('SM_OilSurface',)
    needed=('Bronze',)
else:
    roles=('SM_OilHearth','SM_OilHandPot','SM_OilSurface')
    needed=tuple(paths)
materials={key:kit.require(paths[key]) for key in needed}
kit.E.make_directory(dest)
receipt={'saved':{}}
out=Path(ue.Paths.convert_relative_path_to_full(ue.Paths.project_dir()))/'oil-saved.json'
for role in roles:
    kit.create_role(role,materials,receipt,package_root=dest,source_dir=src,receipt_file=out,preserve_silhouette=True)

if 'SM_OilSurface' in roles:
    liquid=kit.require(dest+'/SM_OilSurface').get_material(0)
    if not liquid or liquid.get_path_name()!=materials['Bronze'].get_path_name():
        raise RuntimeError('Saved oil disc has a different surface')
    receipt['default_liquid']=liquid.get_path_name()
    out.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
