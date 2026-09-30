"""Scoped source/catalog edits for the 201's shared attachment families."""
import json,copy
from pathlib import Path
O=Path(__file__).resolve().parent;P=O.parents[2];W=P/'Source/FPSGAME/Weapons'
def edit(path,fn):
    before=path.read_text(encoding='utf8');after=fn(before)
    if after!=before:
        backup=O/'Before'/path.relative_to(P);backup.parent.mkdir(parents=True,exist_ok=True)
        if not backup.exists():backup.write_text(before,encoding='utf8')
        path.write_text(after,encoding='utf8')
def include(t):return t if '#include "LMG201Attachments.h"' in t else '#include "LMG201Attachments.h"\n'+t
for file,family,mapname,part in [('M4VerticalForegrip.cpp','vertical','VerticalGripAnimations','VerticalForegrip'),('M4CantedForegrip.cpp','canted','CantedGripAnimations','CantedForegrip'),('M4AngledForegrip.cpp','angled','ForegripAnimations','AngledForegrip'),('M4HandstopVisual.cpp','prism','PrismGripAnimations','PrismHandstop')]:
    def update(t):
        t=include(t);marker=f'    {mapname}.Reset();'
        t=t.replace(marker,marker+f'\n    if(LMG201WeaponAssets::Matches(AKMViewmodel)){{LMG201Attachments::LoadGripFamily(TEXT("{family}"),{mapname});return;}}',1)
        marker=f'    if(PKMLowpolyWeaponAssets::Matches(AKMViewmodel)){{{part}='
        pos=t.index(marker)
        flag='Variant==TEXT("prism_handstop")' if family=='prism' else 'bEnabled'
        t=t[:pos]+f'    if(LMG201WeaponAssets::Matches(AKMViewmodel)){{{part}=LMG201Attachments::Configure(this,AKMViewmodel,{part},TEXT("{family}"),{flag}&&bInventoryWeaponReady);return;}}\n'+t[pos:]
        if family=='prism':t=t.replace('const FString Path=SVDWeaponAssets::','const FString Path=LMG201WeaponAssets::Matches(AKMViewmodel)?LMG201Attachments::MeshPath(TEXT("tactical_vertical")):SVDWeaponAssets::',1)
        return t
    edit(W/file,update)
def stocks(t):
    t=include(t).replace('const bool PKM=','const bool LMG201=LMG201WeaponAssets::Matches(Rifle);\n    const bool PKM=',1)
    t=t.replace('||PKM||SVD','||PKM||SVD||LMG201')
    return t.replace('nullptr,SVD?*SVDAttachments::','nullptr,LMG201?*LMG201Attachments::MeshPath(Variant):SVD?*SVDAttachments::',1)
edit(W/'SkeletonStockVisual.cpp',stocks)
edit(W/'PhantomRearGripVisual.cpp',lambda t:include(t).replace('const FString Path=PKMLowpolyWeaponAssets::','const FString Path=LMG201WeaponAssets::Matches(Rifle)?LMG201Attachments::MeshPath(Variant):PKMLowpolyWeaponAssets::',1))
def tactical(t):
    return include(t).replace('const FString Path=Family==TEXT("SVD")','const FString Path=Family==TEXT("LMG201")?LMG201Attachments::MeshPath(Variant):Family==TEXT("SVD")',1).replace('Family!=TEXT("SVD")','Family!=TEXT("LMG201")&&Family!=TEXT("SVD")').replace('const FString Family=SVDWeaponAssets::','const FString Family=LMG201WeaponAssets::Matches(AKMViewmodel)?TEXT("LMG201"):SVDWeaponAssets::',1)
edit(W/'TacticalDeviceComponent.cpp',tactical)
def sprint(t):
    t=include(t)
    old='for(int32 Family=0;Family<6;++Family)\n            for(const TCHAR* Clip:{TEXT("sprint_enter"),TEXT("sprint_loop"),TEXT("sprint_exit")})\n                Clips.Add(LoadObject<UAnimSequence>(nullptr,*LMG201WeaponAssets::AnimationPath(Clip)));'
    new='for(const TCHAR* Family:{TEXT("base"),TEXT("base"),TEXT("angled"),TEXT("vertical"),TEXT("canted"),TEXT("prism")})\n            for(const TCHAR* Clip:{TEXT("sprint_enter"),TEXT("sprint_loop"),TEXT("sprint_exit")})\n                Clips.Add(LoadObject<UAnimSequence>(nullptr,*(FCString::Strcmp(Family,TEXT("base"))==0?LMG201WeaponAssets::AnimationPath(Clip):LMG201Attachments::AnimationPath(Family,Clip))));'
    return t.replace(old,new,1)
edit(W/'M4TacticalSprintComponent.cpp',sprint)
def character(t):
    t='#include "Weapons/LMG201Attachments.h"\n'+t
    t=t.replace('if (!IsPistolWeapon() && !LMG201WeaponAssets::Matches(AKMViewmodel))','if (!IsPistolWeapon())',1)
    return t.replace('if(LMG201WeaponAssets::Matches(AKMViewmodel))return QuickCombatAnimation.Get();','''if(LMG201WeaponAssets::Matches(AKMViewmodel))
    {
        const TCHAR* Families[]={TEXT("base"),TEXT("base"),TEXT("angled"),TEXT("vertical"),TEXT("canted"),TEXT("prism")};
        const int32 Index=static_cast<int32>(Grip);
        return Index>1&&Index<UE_ARRAY_COUNT(Families)?LoadObject<UAnimSequence>(nullptr,*LMG201Attachments::AnimationPath(Families[Index],TEXT("quick_melee"))):QuickCombatAnimation.Get();
    }''',1)
edit(P/'Source/FPSGAME/FPSGAMECharacter.cpp',character)
def catalog(t):
    data=json.loads(t);donor=next(w for w in data['weapons'] if w['id']=='ue_a762')
    pos=t.index('"id": "ue_lmg201"');start=t.rfind('{',0,pos);w,size=json.JSONDecoder().raw_decode(t[start:])
    for slot in ['underbarrel','stock','reargrip','tactical']:
        if slot not in w['allowed']:w['allowed'].append(slot)
        w['options'][slot]=copy.deepcopy(donor['options'][slot])
    # User scope: PSO-1 belongs only to Russian weapons, not universal optics.
    w['options']['optic']=[a for a in w['options']['optic'] if a['id']!='pso1_4x']
    w['traits'][1]['text']='原厂双脚架支持在适合的支撑面架设；支持瞄具、枪口、前握把、枪托、后握把与战术设备，也可卸下脚架。'
    body=json.dumps(w,ensure_ascii=False,indent=2);indent=t[t.rfind('\n',0,start)+1:start]
    return t[:start]+body.replace('\n','\n'+indent)+t[start+size:]
edit(P/'Content/ColdSteelData/gunsmith.json',catalog)
print('LMG20122_RUNTIME_AND_CATALOG_WRITTEN')
