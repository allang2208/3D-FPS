"""Scoped additions to existing weapon routes; no class layout changes."""
from pathlib import Path
import json,copy
O=Path(__file__).parent;P=O.parents[2];W=P/'Source/FPSGAME/Weapons'
changed=[]
def edit(path,fn):
 old=path.read_text(encoding='utf-8-sig');new=fn(old)
 if new!=old:path.write_text(new,encoding='utf-8');changed.append(str(path.relative_to(P)))
def one(s,a,b):
 if s.count(a)!=1:raise RuntimeError('Expected single edit: '+a[:100])
 return s.replace(a,b,1)
def include(s):return one(s,'#include "A762Attachments.h"','#include "A762Attachments.h"\n#include "PKMAttachments.h"')
for file,family,component,table in [('M4VerticalForegrip.cpp','vertical','VerticalForegrip','VerticalGripAnimations'),('M4CantedForegrip.cpp','canted','CantedForegrip','CantedGripAnimations'),('M4AngledForegrip.cpp','angled','AngledForegrip','ForegripAnimations'),('M4HandstopVisual.cpp','prism','PrismHandstop','PrismGripAnimations')]:
 def grip(s):
  s=include(s)
  s=one(s,'&&!A762WeaponAssets::Matches(AKMViewmodel))return;','&&!A762WeaponAssets::Matches(AKMViewmodel)&&!PKMLowpolyWeaponAssets::Matches(AKMViewmodel))return;')
  s=one(s,'if((bUseQBZ191||bUseASH12||bUseM16)&&!Pair.Key)continue;','if(!Pair.Key)continue;')
  old=f'A762WeaponAssets::Matches(AKMViewmodel)?A762Attachments::AnimationPath(TEXT("{family}"),Pair.Value)'
  s=one(s,old,f'PKMLowpolyWeaponAssets::Matches(AKMViewmodel)?PKMAttachments::AnimationPath(TEXT("{family}"),Pair.Value):'+old)
  s=one(s,'if(bUseM16&&InspectAnimation)','if((bUseM16||PKMLowpolyWeaponAssets::Matches(AKMViewmodel))&&InspectAnimation)')
  old=f'*M16Attachments::AnimationPath(TEXT("{family}"),TEXT("inspect"))'
  s=one(s,old,f'*(PKMLowpolyWeaponAssets::Matches(AKMViewmodel)?PKMAttachments::AnimationPath(TEXT("{family}"),TEXT("inspect")):M16Attachments::AnimationPath(TEXT("{family}"),TEXT("inspect")))')
  start=f'    if(A762WeaponAssets::Matches(AKMViewmodel)){{{component}='
  i=s.index(start);end=s.index('\n',i);line=s[i:end]
  s=s[:i]+line.replace('A762WeaponAssets::Matches','PKMLowpolyWeaponAssets::Matches').replace('A762Attachments::Configure','PKMAttachments::Configure')+'\n'+s[i:]
  if family=='prism':
   s=one(s,'    if(PKMLowpolyWeaponAssets::Matches(AKMViewmodel))return;\n','')
   old='A762WeaponAssets::Matches(AKMViewmodel)?A762Attachments::MeshPath(TEXT("tactical_vertical"))'
   s=one(s,old,'PKMLowpolyWeaponAssets::Matches(AKMViewmodel)?PKMAttachments::MeshPath(TEXT("tactical_vertical")):'+old)
  return s
 edit(W/file,grip)

def optic(s):
 s=include(s)
 start=s.index('    if (A762WeaponAssets::Matches(AKMViewmodel))');end=s.index('    if(AKMSoviet::Matches',start);b=s[start:end]
 b=one(b,'if (A762WeaponAssets::Matches(AKMViewmodel))','if (A762WeaponAssets::Matches(AKMViewmodel) || bPKM)')
 b=b.replace('*A762Attachments::MeshPath(Variant)','*(bPKM?PKMAttachments::MeshPath(Variant):A762Attachments::MeshPath(Variant))')
 b=one(b,'HolographicOptic->SetupAttachment(AKMViewmodel,TEXT("WPN_root"));','HolographicOptic->SetupAttachment(AKMViewmodel,bPKM?TEXT("PKM_Cover"):TEXT("WPN_root"));')
 b=one(b,'HolographicMount=A762Attachments::OpticMount(Variant);','HolographicMount=bPKM?PKMAttachments::OpticMount(Variant):A762Attachments::OpticMount(Variant);\n            HolographicOptic->AttachToComponent(AKMViewmodel,FAttachmentTransformRules::KeepRelativeTransform,bPKM?TEXT("PKM_Cover"):TEXT("WPN_root"));')
 b=one(b,'if (LPVO&&bHolographic&&!LPVORing)','if (LPVO&&bHolographic)')
 b=one(b,'*A762Attachments::MeshPath(TEXT("lpvo_ring"))','*(bPKM?PKMAttachments::MeshPath(TEXT("lpvo_ring")):A762Attachments::MeshPath(TEXT("lpvo_ring")))')
 b=one(b,'LPVORing=NewObject<UStaticMeshComponent>(this);LPVORing->SetStaticMesh(RingMesh);','if(!LPVORing)LPVORing=NewObject<UStaticMeshComponent>(this);LPVORing->EmptyOverrideMaterials();LPVORing->SetStaticMesh(RingMesh);')
 b=one(b,'LPVORing->SetupAttachment(HolographicOptic);LPVORing->RegisterComponent();','if(!LPVORing->IsRegistered()){LPVORing->SetupAttachment(HolographicOptic);LPVORing->RegisterComponent();}')
 s=s[:start]+b+s[end:]
 return one(s,'    if (bUseDanWesson715) { SetDanWesson715Optic', '    const bool bPKM=PKMLowpolyWeaponAssets::Matches(AKMViewmodel);\n    PKMAttachments::ConfigureRail(this,AKMViewmodel,bInventoryWeaponReady&&(Variant==TEXT("holographic")||Variant==TEXT("panoramic_red_dot")||Variant==TEXT("prism_scope_2x")||Variant==TEXT("lpvo_1_6x")));\n    if (bUseDanWesson715) { SetDanWesson715Optic')
edit(W/'M4GunsmithVisual.cpp',optic)
def muzzle(s):
 s=include(s);s=one(s,'    if (A762WeaponAssets::Matches(AKMViewmodel))','    const bool bPKM=PKMLowpolyWeaponAssets::Matches(AKMViewmodel);\n    if (A762WeaponAssets::Matches(AKMViewmodel) || bPKM)')
 s=one(s,'const FString Path=A762Attachments::MeshPath(Key);','const FString Path=bPKM?PKMAttachments::MeshPath(Key):A762Attachments::MeshPath(Key);')
 s=one(s,'A762WeaponAssets::MuzzleMount,FVector(.01f)','bPKM?PKMAttachments::MuzzleMount:A762WeaponAssets::MuzzleMount,FVector(.01f)')
 return one(s,'if (Rifle->GetMaterials()[M].MaterialSlotName==TEXT("M_A762_Flash_Hider"))','if (Rifle->GetMaterials()[M].MaterialSlotName==TEXT("M_A762_Flash_Hider") || (bPKM&&Rifle->GetMaterials()[M].MaterialSlotName.ToString().Contains(TEXT("__FactoryMuzzle"))))')
edit(W/'M4MuzzleVisual.cpp',muzzle)
def stock(s):
 s=include(s);s=one(s,'const bool A762=A762WeaponAssets::Matches(Rifle);','const bool A762=A762WeaponAssets::Matches(Rifle);\n    const bool PKM=PKMLowpolyWeaponAssets::Matches(Rifle);')
 s=one(s,'bUsingM4Infima||AKM||bUseQBZ191||A762','bUsingM4Infima||AKM||bUseQBZ191||A762||PKM')
 s=one(s,'nullptr,A762?*A762Attachments::MeshPath(Variant)','nullptr,PKM?*PKMAttachments::MeshPath(Variant):A762?*A762Attachments::MeshPath(Variant)')
 return one(s,'(bUseM16||bUseQBZ191||A762)?','(bUseM16||bUseQBZ191||A762||PKM)?')
edit(W/'SkeletonStockVisual.cpp',stock)
edit(W/'PhantomRearGripVisual.cpp',lambda s:one(include(s),'const FString Path=A762WeaponAssets::Matches(Rifle)?','const FString Path=PKMLowpolyWeaponAssets::Matches(Rifle)?PKMAttachments::MeshPath(Variant):A762WeaponAssets::Matches(Rifle)?'))
def tactical(s):
 s=include(s);s=one(s,'const FString Path=Family==TEXT("A762")?','const FString Path=Family==TEXT("PKM")?PKMAttachments::MeshPath(Variant):Family==TEXT("A762")?')
 s=s.replace('!Pistol&&!ASH&&Family!=TEXT("A762")','!Pistol&&!ASH&&Family!=TEXT("PKM")&&Family!=TEXT("A762")')
 return one(s,'const FString Family=A762WeaponAssets::Matches(AKMViewmodel)?','const FString Family=PKMLowpolyWeaponAssets::Matches(AKMViewmodel)?TEXT("PKM"):A762WeaponAssets::Matches(AKMViewmodel)?')
edit(W/'TacticalDeviceComponent.cpp',tactical)
def sprint(s):
 s=include(s)
 old='for (int32 Grip=0;Grip<6;++Grip)\n            for (const TCHAR* Clip:{TEXT("sprint_enter"),TEXT("sprint_loop"),TEXT("sprint_exit")})\n                Clips.Add(LoadObject<UAnimSequence>(nullptr,*PKMLowpolyWeaponAssets::AnimationPath(Clip)));'
 new='for (const TCHAR* Family:{TEXT("base"),TEXT("base"),TEXT("angled"),TEXT("vertical"),TEXT("canted"),TEXT("prism")})\n            for (const TCHAR* Clip:{TEXT("sprint_enter"),TEXT("sprint_loop"),TEXT("sprint_exit")})\n                Clips.Add(LoadObject<UAnimSequence>(nullptr,*(FCString::Strcmp(Family,TEXT("base"))==0?PKMLowpolyWeaponAssets::AnimationPath(Clip):PKMAttachments::AnimationPath(Family,Clip))));'
 return one(s,old,new)
edit(W/'M4TacticalSprintComponent.cpp',sprint)
def character(s):
 s=one(s,'#include "Weapons/PKMLowpolyWeaponAssets.h"','#include "Weapons/PKMLowpolyWeaponAssets.h"\n#include "Weapons/PKMAttachments.h"')
 s=one(s,'if (!IsPistolWeapon() && !PKMLowpolyWeaponAssets::Matches(AKMViewmodel))','if (!IsPistolWeapon())')
 s=s.replace('PKMLowpolyWeaponAssets::RemoveBipod(this);','PKMLowpolyWeaponAssets::RemoveBipod(this);PKMAttachments::RemoveRail(this);')
 s=one(s,'if (PKMLowpolyWeaponAssets::Matches(AKMViewmodel)) return QuickCombatAnimation;','''if (PKMLowpolyWeaponAssets::Matches(AKMViewmodel))
    {
        const TCHAR* Families[]={TEXT("base"),TEXT("base"),TEXT("angled"),TEXT("vertical"),TEXT("canted"),TEXT("prism")};
        const int32 Index=static_cast<int32>(Grip);
        return Index>1&&Index<UE_ARRAY_COUNT(Families)?LoadObject<UAnimSequence>(nullptr,*PKMAttachments::AnimationPath(Families[Index],TEXT("quick_melee"))):QuickCombatAnimation.Get();
    }''')
 return one(s,'Ref.FindBoneIndex(bUseM1911 ? TEXT("WPN_Slide") : TEXT("WPN_root"))','Ref.FindBoneIndex(bUseM1911 ? TEXT("WPN_Slide") : PKMLowpolyWeaponAssets::Matches(AKMViewmodel) ? TEXT("PKM_Cover") : TEXT("WPN_root"))')
edit(P/'Source/FPSGAME/FPSGAMECharacter.cpp',character)

p=P/'Content/ColdSteelData/gunsmith.json';text=p.read_text(encoding='utf-8-sig');catalog=json.loads(text)
donor=next(w for w in catalog['weapons'] if w['id']=='ue_a762');pkm=next(w for w in catalog['weapons'] if w['id']=='ue_pkm_lowpoly')
pkm['allowed']=['optic','muzzle','underbarrel','stock','reargrip','tactical']
bipod=next(x for x in pkm['options']['underbarrel'] if x['id']=='pkm_bipod')
for slot in pkm['allowed']:pkm['options'][slot]=copy.deepcopy(donor['options'][slot])
pkm['options']['underbarrel'].append(bipod)
for slot,options in pkm['options'].items():
 for entry in options:
  if entry['id']=='false':
   entry['name']={'underbarrel':'原厂托握（无脚架）','stock':'PKM 原厂枪托','reargrip':'PKM 原厂后握把','optic':'原厂机械瞄具','muzzle':'原厂枪口','tactical':'无战术设备'}[slot]
  if slot=='underbarrel' and entry['id']!='pkm_bipod':entry['description']='安装于 PKM 弹箱前方的专用下连接座，配套独立抓握动作。' if entry['id']!='false' else '保持当前机匣前下方托握。'
  else:entry['description']=entry.get('description','').replace('A762','PKM').replace('AKM','PKM')
start=text.rfind('{',0,text.index('"id": "ue_pkm_lowpoly"'));old,end=json.JSONDecoder().raw_decode(text[start:]);replacement=json.dumps(pkm,ensure_ascii=False,indent=2).replace('\n','\n    ')
p.write_text(text[:start]+replacement+text[start+end:],encoding='utf-8');changed.append(str(p.relative_to(P)))
(O/'code_changes.json').write_text(json.dumps(changed,indent=2));print('PKM14_CODE_INTEGRATED',len(changed))
