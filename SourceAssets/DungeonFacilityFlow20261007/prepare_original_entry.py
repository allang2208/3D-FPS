"""Compose the saved original entrance from its existing authoring records."""
from pathlib import Path
import json, re
ROOT=Path(__file__).resolve().parent
SOURCE=ROOT.parent
def read(path):return json.loads(path.read_text('utf8'))
def label(name):return name.replace('DGN_', 'DGN_A_', 1)
rows=read(ROOT/'Sources/fixed-actors.json')
surroundings=read(SOURCE/'DungeonWorkbenchKit20260921/Config/surroundings.json')
surround={label(a['label']):a for a in surroundings['actors']}
room=read(SOURCE/'DungeonRoomInteriors20260921/Authored/room-manifest.json')
shrine=read(SOURCE/'DungeonShrineV2_20260927/Config/room.json')
hidden=set(read(SOURCE/'DungeonShrineV2_20260927/Receipts/install.json')['hidden'])
hidden.update(label(n) for n in room['hidden_existing']+surroundings['retired_lights'])
hidden.update(['DGN_A_AV2_Damp_0']+['DGN_A_AV2_TilePolish_Leak_'+str(i) for i in range(3)])
hidden.update(k for k,v in surround.items() if v.get('hidden'))
placements={'DGN_A_AV2_'+a['label']:a for a in read(SOURCE/'DungeonAtmosphereV2_20260921/Receipts/placement-manifest.json')}
collisions={label(a['actor_label']):a['collision'] for a in room['objects']}
collisions.update({'DGN_A_ShrineV2_'+a['kind']:a['collision'] for a in read(SOURCE/'DungeonShrineV2_20260927/Authored/manifest.json')['objects']})
for k,a in surround.items():collisions[k]=a.get('collision','BlockAll')!='NoCollision'
for k,a in placements.items():collisions.setdefault(k,a['collision'])

decal_data={}
for i,size in enumerate([[22,57,150],[22,43,123],[23,51,141],[20,68,166],[23,113,141],[23,99,143],[22,91,123],[22,66,165],[23,136,175]]):
    decal_data['DGN_A_AV2_Damp_'+str(i)]=dict(material='/Game/Dungeons/AtmosphereV2/Materials/M_LocalDampStreak',size=size,sort=1)
for i,size in enumerate([[5,77,178],[5,72,141],[5,58,110],[5,75,138],[5,68,142],[5,64,137]]):
    decal_data['DGN_A_AV2_TilePolish_Leak_'+str(i)]=dict(material='/Game/Dungeons/AtmosphereV2/TilePolish/Materials/M_TileLeak',size=size,sort=2)
for name,size in [('Leak',[5,85,188]),('Wet',[5,32,73]),('Silt',[5,22,77]),('Dust',[5,30,60])]:
    decal_data['DGN_A_AV2_Natural_Decal_'+name]=dict(material='/Game/Dungeons/AtmosphereV2/NaturalPass/Materials/M_Natural'+('LeakVertical' if name=='Leak' else name),size=size,sort=4 if name=='Leak' else 3)
materials=read(SOURCE/'DungeonRoomInteriors20260921/Receipts/asset-import.json')['materials']
for a in room['decals']:
    decal_data['DGN_A_Room_Decal_'+a['label']]=dict(material=materials[a['material']],size=a['extent'],sort=5)

light_data={}
intensities={'Entry':2900,'Workshop':2400,'Corridor':3600,'MachineBay':3100,'Recess':1450,'Breach':450,'Ruin':650,'Turn':3000,'Exit':2300}
radii={'Entry':540,'Workshop':490,'Corridor':580,'MachineBay':450,'Recess':320,'Breach':500,'Ruin':580,'Turn':570,'Exit':440}
for a in read(SOURCE/'DungeonAtmosphereV2_20260921/Authored/structure-manifest.json')['lights']:
    name=a['id']
    light_data['DGN_A_AV2_Light_'+name]=dict(intensity=intensities[name],attenuation_radius=radii[name],
        color=[1,.59,.29] if a['warm'] else [.71,.83,1],source_radius=7,source_length=65,cast_shadows=True)
light_data['DGN_A_AV2_Light_Breach'].update(use_temperature=True,temperature=4400,color=[1,1,1])
for a in shrine['lights']:
    light_data[a['label']]=dict(intensity=a['intensity'],attenuation_radius=a['radius_cm'],
        use_temperature=True,temperature=a['temperature'],source_radius=7,cast_shadows=True,color=[1,1,1])
for k,a in surround.items():
    if 'light' in a:light_data[k]={k:v for k,v in a['light'].items() if k not in ('intensity_units','light_color')}
light_data['DGN_Link_InspectionLight']=dict(intensity=350,attenuation_radius=360,color=[.78,.87,1],source_radius=5,cast_shadows=False)

actors=[]
for row in rows:
    name=row['label']
    if not (name.startswith(('DGN_A_','DGN_Start_')) or name in ('DGN_Link_A_B','DGN_Link_InspectionLight','DGN_AV2_PlayerStart')):continue
    if name in hidden:continue
    a=dict(label=name,class_name=row['class_name'],position=row['position'],
        rotation={k:float(v) for k,v in re.findall(r'(pitch|yaw|roll):\s*(-?[\d.]+)',row['rotation'])},
        scale=placements.get(name,{}).get('scale',[1,1,1]),tags=row['tags'])
    if name in ('DGN_A_WorkbenchKit_Main','DGN_Start_WarehouseCabinet','DGN_Start_ShrineStatue','DGN_AV2_PlayerStart'):
        a['existing_service']=True
    elif row['class_name']=='StaticMeshActor':
        a['mesh']=row['meshes'][0]
        a['materials']=surround.get(name,{}).get('materials',[])
        # Authored tiles, piping and service bodies have physical collision;
        # small dressings and decal-like films retain their original exclusions.
        a['collision']=collisions.get(name,not any(s in name for s in ('Wear','Markings','WhiteboardFace','HangingCables','WetPatches','LightFixtures')))
        a['cast_shadow']=surround.get(name,{}).get('cast_shadow',True)
    elif row['class_name']=='DecalActor':a['decal']=decal_data[name]
    elif row['class_name'] in ('PointLight','RectLight'):a['light']=light_data[name]
    else:raise RuntimeError('Unmapped original entry actor '+name)
    actors.append(a)
result=dict(revision='original_workshop_shrine_entry_20261008',actors=actors,
    omitted_retired_labels=sorted(hidden),source='Sources/fixed-actors.json and original authoring manifests',tests_run=False)
(ROOT/'Config/original-entry-actors.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
print('ORIGINAL_ENTRY_AUTHORING_READY',len(actors),'actors')
