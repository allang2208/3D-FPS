"""Capture the final authored asset choices once, without replaying historic revisions."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT.parent
for name in ('Config','Authored','Receipts','Sources'):(ROOT/name).mkdir(parents=True,exist_ok=True)
def read(path):return json.loads(path.read_text(encoding='utf-8'))
packs={
 'Sculpt':BASE/'DungeonWorkshopSculpt20260921',
 'Surface':BASE/'DungeonWorkshopSurface20260921',
 'Fab':BASE/'DungeonWorkshopFabTools20260921',
 'Bench':BASE/'DungeonWorkshopBenchPolish20260921'}
selected={'Sculpt':{'BenchFrame','Rag'},'Surface':{'Organizer','Toolboard','UtilityDetail'},'Bench':{'BenchTop','BenchWear','TaskLamp'},'Fab':None}
entries=[];material_sources={}
for key,path in packs.items():
    manifest=read(path/'Authored/manifest.json');assets=read(path/'Receipts/asset-import.json')
    prefix={'Sculpt':'SM_WSSculpt_','Surface':'SM_WSFinish_','Fab':'SM_WSFab_','Bench':'SM_WSBench_'}[key]
    for e in manifest['objects']:
        suffix=e['name'].removeprefix(prefix)
        if (selected[key] is not None and suffix not in selected[key]) or not e.get('actor'):continue
        group='Wall' if suffix in ('Organizer','Toolboard','UtilityDetail','LabelsRetained','Mounts') or suffix.startswith('Wall_') else 'Table'
        if suffix=='BenchFrame':group='Frame'
        if suffix=='TaskLamp':group='Lamp'
        comp=key+'_'+suffix
        entries.append(dict(id=comp,source_blend=manifest['source_blend'],source_object=e['name'],old_actor=e['actor'],expected_mesh=assets['meshes'][e['name']],
                            group=group,collision=e.get('collision',False),cast_shadow=e.get('cast_shadow',True),individual=suffix.startswith(('Wall_','Bench_'))))
        aliases=dict(manifest.get('material_aliases',{}))
        for slot in e.get('materials',[]):
            if slot=='FabGarage_Atlas':pathmat=assets['materials'][e['garage_material']]
            else:
                slotkey=slot.removeprefix({'Sculpt':'WSSculpt_','Surface':'WSFinish_','Bench':'WSBench_','Fab':'__none__'}[key])
                pathmat=aliases.get(slot) or assets['materials'].get(slotkey)
            if not pathmat:raise RuntimeError('Material source missing '+slot+' in '+comp)
            material_sources[comp+'|'+slot]=pathmat
# Cable source contains workshop-local edit objects. Split its lamp-bound parts from wall-bound parts.
entries.extend([
 dict(id='LampFlex',source_blend=str(packs['Bench']/'Authored/DungeonWorkshopBenchPolish.blend'),source_collection='EDITABLE_TaskCable',part_filter='lamp',group='Lamp',collision=False,cast_shadow=True),
 dict(id='SocketPlug',source_blend=str(packs['Bench']/'Authored/DungeonWorkshopBenchPolish.blend'),source_collection='EDITABLE_TaskCable',part_filter='socket',group='Wall',collision=False,cast_shadow=True)])
benchmat=read(packs['Bench']/'Receipts/asset-import.json')['materials']
for comp in ('LampFlex','SocketPlug','PowerLead'):
    for slot in ('CableRubber','LampPaint'):material_sources[comp+'|WSBench_'+slot]=benchmat[slot]
sources=dict(components=entries,material_sources=material_sources,legacy_cable='DGN_WSBench_TaskCable',legacy_light='DGN_WSTools_TaskSpot')
source_path=ROOT/'Config/sources.json'
if not source_path.exists():source_path.write_text(json.dumps(sources,indent=2),encoding='utf-8')
config={
 'id':'WorkshopBench_L','schema':1,'units':'centimetres',
 'root':{'world_location':[1000,148,0],'world_rotation':[0,0,0],'front_axis':'-X','wall_axis':'+X'},
 'table_height_cm':93.9,'original_table_height_cm':93.9,'table_thickness_cm':6.2,
 'supports':{'Main':{'x':[-93,-17],'y':[0,226]},'Return':{'x':[-259,-95],'y':[191,259]}},
 'anchors':{'LampBase':[-27,65,93.9],'LampEntry':[-20.2,65,95.8],'SocketExit':[-30,111,131],
            'WallOrigin':[0,0,115],'MainWorkArea':[-65,125,93.9],'ReturnWorkArea':[-180,222,93.9]},
 'anchor_offsets_cm':{'LampEntry':[6.8,0,1.9],'SocketExit':[-30,111,16]},
 'power_cable':{'diameter_mm':5.0,'arm_diameter_mm':3.3,'surface_clearance_mm':3.0},
 'task_light':read(packs['Bench']/'Authored/manifest.json')['task_light'],
 'operator_clearance':{'center':[-138,94,90],'extent':[44,70,90]},
 'default_variant':'InUse','layout_seed':21921,
 'variants':{
   'InUse':{'label':'使用中','dust':0.035,'roughness_bias':0.0,'surface_tint':[1,1,1],'lamp_on':True,'tool_wear_add':0.0,'omit':[], 'tool_offsets':{}},
   'Idle':{'label':'闲置','dust':0.12,'roughness_bias':0.035,'surface_tint':[.97,.98,1.0],'lamp_on':False,'tool_wear_add':.08,
           'omit':['Fab_Bench_Chisel','Fab_Bench_Pliers'],'tool_offsets':{'Fab_Bench_Wrench':{'translation':[0,7,0],'yaw':14},'Fab_Bench_Screwdriver':{'translation':[-5,1,0],'yaw':-12}}},
   'Abandoned':{'label':'废弃','dust':0.30,'roughness_bias':0.09,'surface_tint':[.87,.90,.92],'lamp_on':False,'tool_wear_add':.20,
                'omit':['Fab_Bench_Chisel','Fab_Bench_Screwdriver','Fab_Wall_Bolt_Cutter','Fab_Wall_Adjustable_Wrench','Fab_Wall_Pliers'],
                'tool_offsets':{'Fab_Bench_Wrench':{'translation':[-3,9,0],'yaw':32},'Fab_Bench_Pliers':{'translation':[-6,-8,0],'yaw':-26}}}},
 'placement':{'actor_label':'DGN_WorkbenchKit_Main','variant':'InUse','locked':True}
}
path=ROOT/'Config/workbench.json'
if not path.exists():path.write_text(json.dumps(config,ensure_ascii=False,indent=2),encoding='utf-8')
print('WORKBENCH_KIT_SOURCE_SELECTION_READY',len(entries))
