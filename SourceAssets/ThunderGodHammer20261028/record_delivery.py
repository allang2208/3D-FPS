"""Collect production receipts and existing animation dependencies; no tests or runtime session."""
import json,re
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=P.parents[1]
BASE='/Game/Weapons/SteelWarhammer20261014/'
PICKAXE='/Game/Items/ProductionTools/RusticPickaxe20260919/A_RusticPickaxe_'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def write(name,value):(P/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def asset(package):return package+'.'+package.rsplit('/',1)[-1]
roles={r:asset(PICKAXE+r) for r in ('Idle','Equip','Swing','HitRecover')}
roles['SprintCarry']=asset(BASE+'SprintDragV1/A_Warhammer_SprintCarry')
header=(ROOT/'Source/FPSGAME/Production/ProductionBluntCombo.h').read_text(encoding='utf-8-sig')
match=re.search(r'Clips\[\].*?\{(.*?)\}',header,re.S)
if match:
    for r in re.findall(r'TEXT\("([^"]+)"\)',match[1]):roles[r]=asset(BASE+'NormalComboV4/A_Warhammer_'+r)
for r in ('HeavyCharge','HeavyRelease'):roles[r]=asset(BASE+'HeavySlamV4/A_Warhammer_'+r)
for r,folder in [('Whirlwind','WhirlwindV1'),('Uppercut','UppercutV1'),('Inspect','InspectV1'),
                 ('InspectWalk','InspectV1'),('QuickCombat','QuickCombatLeftWristV7')]:
    roles[r]=asset(BASE+folder+'/A_Warhammer_'+r)
for r in ('GuardEnter','GuardHold','GuardHit','GuardBreak','GuardExit'):
    roles[r]=asset(BASE+'GuardV1/A_Warhammer_'+r)
body_roles={}
def collect(value):
    if isinstance(value,dict):
        for key,entry in value.items():
            if key.startswith('Warhammer.') and isinstance(entry,str):body_roles[key]=entry
            collect(entry)
    elif isinstance(value,list):
        for entry in value:collect(entry)
collect(read(ROOT/'Content/ColdSteelData/player_body.json'))
manifest={'weapon':'ue_thunder_god_hammer','name':'雷神之锤','first_person':roles,
    'shared_grip_profile':asset(BASE+'RhythmClearanceV2/DA_Warhammer_Clearance'),
    'procedural':['two-hand walking stride','sprint blend','charge return/cancellation',
                  'ground planting / impact hold / recovery','left-hand casting and return'],
    'third_person':{'configuration':'Content/ColdSteelData/player_body.json (existing shared configuration)',
       'dispatch':'Tool / warhammer','shared_roles':body_roles,
       'consumers':['FPSPlayerBodyActions.cpp','FPSPlayerBodyAnimInstance.cpp','FPSPlayerBodyMotion.cpp'],
       'policy':'Reuse current warhammer locomotion/action/casting mappings and capture the new static attachment from the viewmodel'},
    'animation_assets_created':0,'tested':False}
write('animation_manifest.json',manifest)
stages={key:read(P/file) for file,key in [
    ('build-game-receipt.json','game_build'),('build-editor-receipt.json','editor_build'),
    ('import_receipt.json','base_assets'),('ModulesV1/import_receipt.json','module_assets'),
    ('publication_receipt.json','catalogs'),('InventoryIconV2/production_receipt.json','inventory_icon'),
    ('ModulesV1/icon_receipt.json','module_icons'),('icon_import_receipt.json','saved_icons')]}
delivery={'weapon':'ue_thunder_god_hammer','name':'雷神之锤','authoring':read(P/'authored.json'),
    'stages':stages,'source':'User-provided Meshy GLB; archived without public redistribution',
    'inventory':'GrantStartingArmory: existing idempotent grant to existing/new profiles',
    'parts_policy':'Six factory modules; sixteen host-fitted common options; five shared runes',
    'animation_manifest':str(P/'animation_manifest.json'),'animation_assets_copied':0,
    'balance':'Independent strength/constitution formula initialized from current steel warhammer',
    'innate_lightning_gameplay_added':False,'source_emission':'No emissive channel in supplied GLB',
    'editor_ui_started':False,'game_started':False,'tested':False,
    'acceptance':'Production and necessary builds only; user will test in game'}
write('delivery.json',delivery)
print('Thunder God hammer production delivery recorded')
