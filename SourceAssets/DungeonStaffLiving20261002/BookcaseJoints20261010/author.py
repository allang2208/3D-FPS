"""Repair the shared bookcase body only; preserve assembly poses and materials."""
import json, shutil, hashlib, random
from pathlib import Path
from datetime import datetime
import bpy

TASK=Path(__file__).resolve().parent
STAFF=TASK.parent
NAME='SM_Staff_BookcaseBody_V4'
SOURCE=STAFF/'ScenePolishV4/Authored'
BACKUP=TASK/'Backups'/datetime.now().strftime('%Y%m%d-%H%M%S')
BACKUP.mkdir(parents=True,exist_ok=True)
(TASK/'Receipts').mkdir(exist_ok=True)
(TASK/'Authored').mkdir(exist_ok=True)

def backup(path):
    dst=BACKUP/path.relative_to(STAFF)
    dst.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(path,dst)

for path in (SOURCE/(NAME+'.fbx'),SOURCE/'manifest.json'):
    backup(path)

# Load only geometry helpers and this furniture recipe, not the room rebuild.
entry=STAFF/'Scripts/author_living.py'
env={'__file__':str(STAFF/'Scripts/author_scene_polish_v4.py'),
     '__name__':'bookcase_joint_author','_STAFF_REFINEMENT_HELPERS':True}
exec(compile(entry.read_text('utf8').split('for key,fn in PROTOTYPES.items():')[0],str(entry),'exec'),env)
for key in ('BookPaper','BookGreen','BookBlue','BookRed'):
    env['MAPPING'][key]=env['CFG']['ue_base']+'/DormitoryVariantsV2/Materials/M_Dorm_'+key
    env['MATS'][key]=bpy.data.materials.new('RS_'+key)
recipe=STAFF/'Scripts/author_scene_polish_v4.py'
code=recipe.read_text('utf8')
exec(compile(code[code.index('def solid('):code.index('def bookshelf_v4(')],str(recipe),'exec'),env)
env.update(OUT=SOURCE,G={},HULLS=[],records=[],random=random)
env['bookcase_v4']()
env['export_mesh'](NAME,env['merge_groups'](),kind='Body',hulls=env['HULLS'])
item=env['records'][-1]
item['asset']=env['CFG']['ue_base']+'/ScenePolishV4/Meshes/'+NAME
item['joint_revision']='20261010_inner_shelves_and_butt_cap'
manifest=json.loads((SOURCE/'manifest.json').read_text('utf8'))
for i,old in enumerate(manifest['objects']):
    if old['name']==NAME:
        manifest['objects'][i]=item
        break
else:raise RuntimeError('Missing shared bookcase manifest entry')
(SOURCE/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
authored=TASK/'Authored/BookcaseJoints.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(authored))

# These living-room sources inherit the same body by mesh data. Replace only
# that body and its ten collision hulls; keep every object transform/door.
updated=[]
sources=[
    SOURCE/'StaffLivingTheme_ScenePolishV4.blend',
    STAFF/'RoomDetailsV5/Authored/StaffLivingTheme_RoomDetailsV5.blend',
    STAFF/'WallInsetV6/Authored/StaffLivingTheme_WallInsetV6.blend',
    STAFF/'CoffeePolishV7/Authored/StaffLivingTheme_CoffeePolishV7.blend',
]
for path in sources:
    backup(path)
    bpy.ops.wm.open_mainfile(filepath=str(path))
    bodies=[o for o in bpy.data.objects if o.type=='MESH' and o.name.startswith(NAME)]
    if not bodies:raise RuntimeError('Missing bookcase body in '+str(path))
    body_data={o.data for o in bodies}
    targets={NAME:[o for o in bpy.data.objects if o.type=='MESH' and o.data in body_data]}
    for i in range(len(env['HULLS'])):
        key='UCX_'+NAME+'_'+str(i)
        # Match complete names (Blender may add a .001 suffix), not hull 1 to 10.
        targets[key]=[o for o in bpy.data.objects if o.type=='MESH' and (o.name==key or o.name.startswith(key+'.'))]
    with bpy.data.libraries.load(str(authored),link=False) as (src,dst):
        dst.meshes=[k for k in targets if targets[k]]
    new_data=dict(zip([k for k in targets if targets[k]],dst.meshes))
    for key,objects in targets.items():
        for obj in objects:obj.data=new_data[key]
    bpy.ops.wm.save_as_mainfile(filepath=str(path))
    updated.append(dict(source=str(path),body_instances=len(targets[NAME])))

report=dict(asset=item['asset'],fbx=item['fbx'],triangles=item['triangles'],
    collision_hulls=item['simple_collision_hulls'],source_sha256=hashlib.sha256(Path(item['fbx']).read_bytes()).hexdigest(),
    shelf_width_cm=90,shelf_front_recess_cm=.6,panel_top_cm=194.25,
    sources=updated,backup=str(BACKUP),rendered=False,game_run=False)
(TASK/'Receipts/source.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print('BOOKCASE_JOINT_SOURCE_SAVED',json.dumps(report,ensure_ascii=False),flush=True)
