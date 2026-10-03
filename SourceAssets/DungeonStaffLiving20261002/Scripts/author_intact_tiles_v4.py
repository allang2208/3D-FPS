"""Replace only staff tile walls; preserve the full V3 furniture/surface source."""
from pathlib import Path
SCRIPT=Path(__file__).resolve().parent
_STAFF_REFINEMENT_HELPERS=True
entry=SCRIPT/'author_living.py';code=entry.read_text('utf8')
exec(compile(code.split('for key,fn in PROTOTYPES.items():')[0],str(entry),'exec'))
from staff_intact_tiles import IntactStaffTiles
if not isinstance(SURFACES,IntactStaffTiles):SURFACES=IntactStaffTiles(SURFACES)
OUT=ROOT/'IntactTilesV4/Authored';OUT.mkdir(parents=True,exist_ok=True)
CFG['wall_finish']='intact';records=[]
original_export=export_mesh
def export_mesh(name,g,room_id=None,prototype=None,collision=True,nanite=True,kind='',hulls=()):
    if kind!='Tiles':return
    original_export(name+'_V4',g,room_id=room_id,prototype=prototype,collision=False,nanite=True,kind=kind)
    records[-1]['asset']=CFG['ue_base']+'/IntactTilesV4/Meshes/'+name+'_V4'
    records[-1]['replaces']=name

begin=code.index("for room in CFG['rooms']:\n    G={};HULLS=[];ROOM['id']")
end=code.index('# The editable source also contains the actual room furniture')
exec(compile(code[code.index('def wall(a,b,height'):begin],str(entry),'exec'))
exec(compile(code[begin:end],str(entry),'exec'))

old_names={r['replaces'] for r in records}
old_names.add('SM_Staff_Link_Tiles_Second')
with bpy.data.libraries.load(str(ROOT/'RefinementV3/Authored/StaffLivingTheme_RefinementV3.blend'),link=False) as (src,dst):
    dst.objects=[n for n in src.objects if n not in old_names]
for obj in dst.objects:
    if obj:bpy.context.scene.collection.objects.link(obj)
source=bpy.data.objects['SM_Staff_Link_Tiles_V4']
inst=source.copy();inst.data=source.data;inst.name='SM_Staff_Link_Tiles_V4_Second'
bpy.context.scene.collection.objects.link(inst);inst.location=(48,0,0)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'StaffLivingTheme_IntactTilesV4.blend'))
(OUT/'manifest.json').write_text(json.dumps(dict(objects=records,wall_finish='intact',
    revision='staff_living_intact_tiles_v4_20261002',placements=SURFACES.placements,
    tests_run=False,rendered=False,source_units='metres; UE centimetres'),indent=2),encoding='utf8')
print('STAFF_INTACT_TILES_AUTHORED',len(records),flush=True)
