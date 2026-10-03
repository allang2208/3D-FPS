"""Connect the authored revision to fixed furniture and seeded dressing states."""
import copy,json,random
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1];PARENT=ROOT.parent;PROJECT=PARENT.parents[1]
BASE='/Game/Dungeons/StationWorkshop20261003/RefineV2'
read=lambda p:json.loads(p.read_text('utf-8-sig'))
manifest=read(ROOT/'Authored/manifest.json')
im=Image.new('RGB',(2048,1024),(36,36,36));draw=ImageDraw.Draw(im)
for e in manifest['keylabels']:
    i=e['index'];text=e['text'];font=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',31 if len(text)<3 else 24 if len(text)<5 else 19)
    draw.text((i%16*128+64,i//16*128+64),text,font=font,fill=(214,219,212),anchor='mm')
im.save(ROOT/'Authored/T_Office_KeyLegends.png')

def apply(rules):
    rules=copy.deepcopy(rules);origin=rules['origin_cm'];world=lambda p:[p[i]+origin[i] for i in range(3)]
    repl={e['kind']:e['asset'] for e in manifest['objects']}
    remove={'ObservationGlass','OpenedDoors','RackSpares'}
    updated=[]
    for p in rules['fixed_parts']:
        key=p['mesh'].rsplit('SM_SW_',1)[-1]
        if key in remove:continue
        if key in repl:p['mesh']=repl[key]
        updated.append(p)
    rules['fixed_parts']=updated
    for i,v in enumerate(rules['variants']):
        for p in v['parts']:
            key=p['mesh'].rsplit('SM_SW_',1)[-1]
            if key in repl:p['mesh']=repl[key]
        v['parts']=[p for p in v['parts'] if not p.get('station_workshop_spares')]
        v['parts'].append(dict(mesh=repl['RackSpares_'+str(i)],position=origin,yaw=0,scale=[1,1,1],
            collision=False,affects_navigation=False,materials=[],fluid=False,station_workshop_part=True,station_workshop_spares=True))
        r=random.Random(71031+i)
        for c in v['containers']:
            for key in ('body','door'):
                kind=c[key].rsplit('SM_SW_',1)[-1]
                if kind in repl:c[key]=repl[kind]
            if '.Rack.Tote' in c['container_id']:
                x=705 if c['container_id'].endswith('A') else 817
                c['position']=world([x+r.uniform(-3,3),646+r.uniform(-4,4),31.5]);c['yaw']=r.uniform(-6,6)
    runtime=[]
    for i,x in enumerate((343.335,500,656.665)):
        runtime.append(dict(type='glass_window',position=world([x,0,181]),yaw=90,
            pane=repl['WindowPaneV5'],fracture=repl['WindowFractureV5'],dimensions_cm=[151.67,143,.65],
            fracture_material='/Game/Dungeons/IsolationWard20260929/Materials/M_WardGlassFragmentsV5',
            impact_particles='/Game/NiagaraExamples/FX_Weapons/Impacts/NS_Impact_Glass',
            sound='/Game/Weapons/GunplayFX/Impacts/S_Impact_Glass_0',id='ObservationPane'+str(i),station_workshop_actor=True))
    for id,x,kind,hinge in [('PersonnelEntrance',120,'PersonnelLeaf',True),('ServiceLeft',817,'ServiceLeaf',True),('ServiceRight',923,'ServiceLeaf',False)]:
        runtime.append(dict(type='solid_door',id=id,position=world([x,0,1]),yaw=90,leaf=repl[kind],
            positive_hinge=hinge,open_seconds=.55,auto_close_seconds=0,station_workshop_actor=True))
    catalog=read(PARENT/'Config/catalog.json');chest=copy.deepcopy(next(m for m in catalog['modules'] if m['id']=='Treasure')['props'][0])
    # Bridge footprint x2225..2765, deck top480. East rail side leaves the west walking lane clear.
    chest.update(position=[2650,0,480.8],yaw=180,role='station_upper_platform',identity='station_upper_platform',station_workshop_prop=True)
    rules.update(revision=2,runtime_actors=runtime,props=[chest],preview_chest_blueprint=BASE+'/Blueprints/BP_StationUpperTreasure',
        text_direction='UE camera-right mapped to texture U; native aspect retained',
        shelf_variation='Seed-selected piles, canister lengths, bin yaw and irregular copper stock; constrained to decks',
        door_initial_state='Closed; E normal door interaction and existing sprint DoorPush',glass_breakage='Existing hospital component, fitted pane/fracture meshes')
    remap_file=ROOT/'Config/text-asset-remap.json'
    if remap_file.exists():
        remap=read(remap_file)
        def replace(value):
            if isinstance(value,str):return remap.get(value,value)
            if isinstance(value,list):return [replace(v) for v in value]
            if isinstance(value,dict):return {k:replace(v) for k,v in value.items()}
            return value
        rules=replace(rules);rules['text_asset_remap']=remap
    return rules

if __name__=='__main__':
    rules=apply(read(PARENT/'Config/workshop.json'))
    (ROOT/'Config/workshop.json').write_text(json.dumps(rules,ensure_ascii=False,indent=2),encoding='utf8')
    print('STATION_WORKSHOP_V2_LAYOUT_SAVED',len(rules['fixed_parts']),len(rules['runtime_actors']),flush=True)
