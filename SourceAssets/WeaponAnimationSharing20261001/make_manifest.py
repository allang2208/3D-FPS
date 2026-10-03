"""Authoring inputs resolved from the current C++ loaders; never scans old clips."""
from pathlib import Path
import json
P=Path('D:/FPS3D/FPSGAME');O=Path(__file__).parent
ROOT='/Game/Weapons/'
FAMILIES=('angled','vertical','canted','prism')
MESHES={
 'ue_m4a1':'M4HK416Replica/SK_M4_FoldingSights_HK416',
 'ue_hk416':'HK416/Reworked20260930/SK_HK416_Manny',
 'ue_akm':'AKMIntegration/SovietFab/RearGrip20260913/SK_AKM_MannyNative',
 'ue_qbz191':'QBZ191/RearGrip20260913/SK_QBZ191_Manny',
 'ue_ash12':'ASH12/Surface20260919/SK_ASH12_Surface',
 'ue_m16a2':'M16A2/Gameplay20260919/SK_M16_Manny',
 'ue_a762':'A762/Integrated20260920/SK_A762_Manny',
 'ue_pkm_lowpoly':'PKMLowpoly20260922/Accessories14/SK_PKM_Manny_Modular',
 'ue_lmg201':'LMG201/Cover10/SK_LMG201_Cover10',
 'Melee':'FrostCrystalSword20260915/Modules20260915/SK_FrostSword_Arms',
}
REGULAR=('idle','aim','fire','aim_fire','equip','reload','reload_empty')
MANIFEST=[];absent=[]
def path(s):return ROOT+s
def disk(s):return P/'Content'/(s.removeprefix('/Game/')+'.uasset')
def add(w,f,pairs):
 rows=[]
 for role,b,a in pairs:
  if not disk(b).exists() or not disk(a).exists():
   absent.append(dict(weapon=w,family=f,role=role,base=b,authored=a));continue
  rows.append(dict(role=role,base=b,authored=a))
 if rows:
  entry=dict(weapon=w,family=f,mesh=path(MESHES[w]),asset=path('AnimationProfiles20261001/'+w+'/DA_'+f),pairs=rows)
  if w.startswith('ue_pit_viper2011/'):entry['author']='WeaponAnimationSharing20261002'
  MANIFEST.append(entry)
def q(weapon,f):
 cap=f.capitalize()
 if weapon=='M4':return path(f'M4QuickMeleeReplica20260919/{cap}/A_M4_QuickCombat_{cap}')
 return path(f'RifleQuickMelee20260919/{weapon}/{cap}/A_{weapon}_QuickCombat_{cap}')
def sprint(weapon,f,k):
 cap=f.capitalize();kind=k.removeprefix('sprint_').capitalize()
 if weapon=='M4':return path(f'M4TacticalSprint20260915/{cap}/A_M4_TacticalSprint_{cap}_{kind}')
 return path(f'RifleTacticalSprint20260915/{weapon}/{cap}/A_{weapon}_TacticalSprint_{cap}_{kind}')
SPRINT=('sprint_enter','sprint_loop','sprint_exit')
def m4base(k):
 if k in ('drum_reload','drum_reload_empty'):return path('M4DrumDrop/Contact/A_M4_DrumContact_'+k.removeprefix('drum_'))
 if k=='equip':return path('M4WrapGripFinal/A_M4_HK416_equip_charge')
 if k=='reload':return path('M4TacticalTossFinal/A_M4_HK416_reload')
 if k=='reload_empty':return path('M4SlapImpactFinal/A_M4_HK416_reload_empty')
 return path('M4ContactImpactFinal/A_AKM_'+k)
def m4family(f,k):
 pre={'angled':'M4ForegripWristNatural/A_M4_Foregrip_',
      'vertical':'M4VerticalGripVRENatural/Vertical/A_M4_Vertical_',
      'canted':'M4VREGripExtensions/Canted/A_M4_Canted_',
      'prism':'M4VREGripExtensions/Prism/A_M4_Prism_'}[f]
 return path(pre+k)
for f in FAMILIES:
 pairs=[(k,m4base(k),m4family(f,k)) for k in REGULAR+('drum_reload','drum_reload_empty')]
 pairs += [(k,sprint('M4','base',k),sprint('M4',f,k)) for k in SPRINT]
 pairs += [('quick_melee',q('M4','base'),q('M4',f))]
 add('ue_m4a1',f,pairs)
add('ue_m4a1','drum',[(k,m4base(k),path('M4DrumGripRebuilt/Support/'+m4base(k).rsplit('/',1)[1])) for k in REGULAR[:5]]
 +[(k,sprint('M4','base',k),sprint('M4','drum',k)) for k in SPRINT]+[('quick_melee',q('M4','base'),q('M4','drum'))])
def hk(f,k):return path(f'HK416/Reworked20260930/Animations/{f}/A_HK416_{f}_{"equip_charge" if k=="equip" else k}')
for f in FAMILIES+('drum',):
 kinds=REGULAR+('drum_reload','drum_reload_empty','inspect') if f!='drum' else REGULAR[:5]+('inspect',)
 add('ue_hk416',f,[(k,hk('base',k),hk(f,k)) for k in kinds+SPRINT+('quick_melee',)])
def akmbase(k):
 if k.startswith('drum_reload'):return path('AKMDrumFreeDrop20260920/base/A_AKM_'+k)
 if k.startswith('reload'):return path('AKMIntegration/SovietFab/ReloadPolish/base/A_AKM_'+k)
 if k=='equip':return path('AKMIntegration/EquipCharge/A_AKM_equip')
 return path('AKMIntegration/SourceMatched/A_AKM_'+k)
def akmfamily(f,k):
 if k.startswith('drum_reload'):return path(f'AKMDrumFreeDrop20260920/{f}/A_AKM_{f}_{k}')
 folder='GripVRENatural' if f=='vertical' else 'GripVREExtensions' if f in ('canted','prism') else 'GripErgonomic'
 return path(f'AKMIntegration/SovietFab/{folder}/{f}/A_AKM_{f}_{k}')
for f in FAMILIES:
 add('ue_akm',f,[(k,akmbase(k),akmfamily(f,k)) for k in REGULAR+('drum_reload','drum_reload_empty')]
  +[(k,sprint('AKM','base',k),sprint('AKM',f,k)) for k in SPRINT]+[('quick_melee',q('AKM','base'),q('AKM',f))])
def qbz(f,k):
 k='equip_charge' if k=='equip' else k
 rev='Attachments20260913' if 'reload' in k or k=='equip_charge' else 'Refined20260913'
 return path(f'QBZ191/{rev}/Animations/{f}/A_QBZ191_'+('' if f=='base' else f+'_')+k)
for f in FAMILIES:
 add('ue_qbz191',f,[(k,qbz('base',k),qbz(f,k)) for k in REGULAR+('drum_reload','drum_reload_empty')]
  +[(k,sprint('QBZ191','base',k),sprint('QBZ191',f,k)) for k in SPRINT]+[('quick_melee',q('QBZ191','base'),q('QBZ191',f))])
def ashbase(k):
 if k.startswith('drum_reload'):return m4base(k) # Preserves the existing unavailable-drum route.
 k='equip_charge' if k=='equip' else k
 rev='ReloadReference20260919' if k.startswith('reload') else 'Integrated20260917/Animations'
 return path(f'ASH12/{rev}/A_ASH12_{k}')
def ashfamily(f,k):return path(f'ASH12/UniversalAttachments20260919/Animations/{f}/A_ASH12_{f}_{k}')
for f in FAMILIES:
 add('ue_ash12',f,[(k,ashbase(k),ashfamily(f,k)) for k in REGULAR+('drum_reload','drum_reload_empty')]
  +[(k,path('ASH12/TacticalSprint20260919/A_ASH12_TacticalSprint_'+k[7:].capitalize()),ashfamily(f,'Sprint'+k[7:].capitalize())) for k in SPRINT]
  +[('quick_melee',q('ASH12','base'),ashfamily(f,'QuickCombat'))])
def m16base(k):return path('M16A2/Gameplay20260919/Animations/A_M16_'+('equip_charge' if k=='equip' else k))
def m16family(f,k):return path(f'M16A2/UniversalAttachments20260920/Animations/{f}/A_M16_{f}_{k}')
for f in FAMILIES+('drum',):
 kinds=REGULAR+('drum_reload','drum_reload_empty','inspect') if f!='drum' else REGULAR[:5]+('inspect',)
 pairs=[(k,m16family('base',k) if k.startswith('drum_reload') else m16base(k),m16family(f,k)) for k in kinds]
 pairs += [(k,m16base(k),m16family(f,'Sprint'+k[7:].capitalize())) for k in SPRINT]
 pairs += [('quick_melee',m16base('quick_melee'),m16family(f,'QuickCombat'))]
 add('ue_m16a2',f,pairs)
def a762base(k):return path('A762/Integrated20260920/Animations/A_A762_'+k)
def a762family(f,k):return path(f'A762/Accessories05/Animations/{f}/A_A762_{f}_{k}')
for f in FAMILIES:
 add('ue_a762',f,[(k,a762family('base',k) if k.startswith('drum_reload') else a762base(k),a762family(f,k)) for k in REGULAR+('drum_reload','drum_reload_empty')]
  +[(k,a762base(k),a762family(f,k)) for k in SPRINT]
  +[('quick_melee',q('AKM','base'),q('AKM',f))]) # Existing A762 quick-combat family.
for w,base,auth in (
 ('ue_pkm_lowpoly','PKMLowpoly20260922/Animations/A_PKM_','PKMLowpoly20260922/Accessories14/Animations/{f}/A_PKM_{f}_'),
 ('ue_lmg201','LMG201/BeltFeed08/Animations/A_LMG201_','LMG201/Accessories22/Animations/{f}/A_LMG201_{f}_')):
 for f in FAMILIES:
  pairs=[]
  for k in REGULAR+('inspect',)+SPRINT+('quick_melee',):
   b=path(base+k);a=path(auth.format(f=f)+k)
   if w=='ue_lmg201' and k.startswith('reload'):
    b=path('LMG201/Magazine24/Animations/base/A_LMG201_base_'+k)
    a=path(f'LMG201/Magazine24/Animations/{f}/A_LMG201_{f}_{k}')
   pairs.append((k,b,a))
  if w=='ue_lmg201':
   for mechanism,folder in (('cloth','ClothReload44'),('drum','Drum46')):
    for k in ('reload','reload_empty'):
     prefix='drum_' if mechanism=='drum' else ''
     pairs.append((mechanism+'_'+k,path(f'LMG201/{folder}/Animations/base/A_LMG201_base_{prefix}{k}'),path(f'LMG201/{folder}/Animations/{f}/A_LMG201_{f}_{prefix}{k}')))
  add(w,f,pairs)
BASE=path('AzureRunesword20260913');LONG=path('FrostCrystalSword20260915/Grips20260919/LongGripAnimations')
pairs=[]
for k in ('Idle','Walk','Whirlwind','Equip','Inspect','Overhead','Slash1','Slash2','Thrust','PommelStrike','HeavyCharge','HeavyRelease','Guard','GuardHit','GuardBreak','SprintEnter','SprintLoop','SprintExit','SprintOverhead'):
 suffix=('/TacticalSprint20260921' if k.startswith('Sprint') else '')+'/A_RuneSword_'+k+('V5' if k=='Whirlwind' else '')
 pairs.append((k,BASE+suffix,LONG+suffix))
add('Melee','Sword_LongGrip',pairs)
for weapon,name in (('ue_m1911','M1911'),('ue_g18','G18'),('ue_dan_wesson715','DW715'),('ue_pit_viper2011','PitViper2011')):
 for side in ('r','l'):
  dual_root=(f'G18/Integrated20260929/Dual/{side}' if name=='G18'
   else f'PitViper2011/Integrated20261002/Dual/{side}' if name=='PitViper2011'
   else f'PistolDualWield20260914/{name}/{side}')
  MESHES[weapon+'/Dual_'+side]=dual_root+f'/SK_Dual_{name}_{side}'
  for family in ('fitted','long'):
   def pistol(role):
    if name in ('G18','PitViper2011'):return path(dual_root+f'/Animations/A_Dual_{name}_{side}_{role}')
    return path(f'DualPistolQuickCombat20260920/SpinRecoveryV5/{name}/{side}/Animations/A_Dual_{name}_{side}_{role}')
   pairs=[]
   for role in ('quickcombat','quickcombat_empty','quickcombat_left','quickcombat_left_empty'):
    if name=='DW715' and role.endswith('_empty'):continue
    authored=role.removesuffix('_empty')+'_'+family+('_empty' if role.endswith('_empty') else '')
    pairs.append((role,pistol(role),pistol(authored)))
   add(weapon+'/Dual_'+side,family,pairs)
(O/'manifest.json').write_text(json.dumps(dict(profiles=MANIFEST,unavailable_legacy_routes=absent),indent=1),encoding='utf-8')
print(json.dumps(dict(profiles=len(MANIFEST),pairs=sum(len(x['pairs']) for x in MANIFEST),unavailable_legacy_routes=absent),indent=1))
