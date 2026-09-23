"""Apply narrowly anchored SVD branches to the current shared source files."""
from pathlib import Path
import json,copy
O=Path(__file__).parent;R=O.parents[1];B=O/'Before';B.mkdir(exist_ok=True)
def edit(rel,fn):
 p=R/rel;old=p.read_text(encoding='utf-8-sig');new=fn(old)
 backup=B/rel.replace('/','__')
 if not backup.exists():backup.write_text(old,encoding='utf-8')
 if new!=old:p.write_text(new,encoding='utf-8')
def replace(s,a,b):
 if s.count(a)!=1:raise RuntimeError('Ambiguous edit '+a[:110])
 return s.replace(a,b,1)
def include(s):return replace(s,'#include "A762Attachments.h"','#include "A762Attachments.h"\n#include "SVDAttachments.h"')
edit('Source/FPSGAME/Weapons/SVDWeaponAssets.h',lambda s:replace(s,'/Complete20260923/SK_SVD_Manny.SK_SVD_Manny','/Accessories20260923/SK_SVD_Modular.SK_SVD_Modular'))
edit('Source/FPSGAME/FPSGAMECharacter.h',lambda s:replace(s,'return ActiveInventoryWeaponDefinition==TEXT("ue_svd");','return ActiveInventoryWeaponDefinition==TEXT("ue_svd") && !bHolographicOptic;'))
def optics(s):
 s=include(s)
 s=replace(s,'''    if(HasSVDFactoryScope())
    {
        // PSO-1 is part of the SVD assembly, independent of an empty optic slot.
        bHolographicOptic=false;OpticVariant.Reset();return;
    }''','''    const bool bSVD=SVDWeaponAssets::Matches(AKMViewmodel);
    if(bSVD)
    {
        const bool Modern=bInventoryWeaponReady&&(Variant==TEXT("holographic")||Variant==TEXT("panoramic_red_dot")||Variant==TEXT("prism_scope_2x")||Variant==TEXT("lpvo_1_6x"));
        SVDAttachments::FactorySections(AKMViewmodel,TEXT("Scope"),!Modern);
        AKMOpticBridge=SVDAttachments::Configure(this,AKMViewmodel,AKMOpticBridge,TEXT("optic_bridge"),Modern);
    }''')
 s=replace(s,'if (A762WeaponAssets::Matches(AKMViewmodel) || bPKM)','if (bSVD || A762WeaponAssets::Matches(AKMViewmodel) || bPKM)')
 s=replace(s,'bPKM?PKMAttachments::MeshPath(Variant):A762Attachments::MeshPath(Variant)','bSVD?SVDAttachments::MeshPath(Variant):bPKM?PKMAttachments::MeshPath(Variant):A762Attachments::MeshPath(Variant)')
 s=replace(s,'HolographicMount=bPKM?','HolographicMount=bSVD?SVDAttachments::OpticMount(Variant):bPKM?')
 s=replace(s,'bPKM?PKMAttachments::MeshPath(TEXT("lpvo_ring")):A762Attachments::MeshPath(TEXT("lpvo_ring"))','bSVD?SVDAttachments::MeshPath(TEXT("lpvo_ring")):bPKM?PKMAttachments::MeshPath(TEXT("lpvo_ring")):A762Attachments::MeshPath(TEXT("lpvo_ring"))')
 return s
edit('Source/FPSGAME/Weapons/M4GunsmithVisual.cpp',optics)
def muzzles(s):
 s=include(s)
 s=replace(s,'const bool bPKM=PKMLowpolyWeaponAssets::Matches(AKMViewmodel);','const bool bPKM=PKMLowpolyWeaponAssets::Matches(AKMViewmodel);\n    const bool bSVD=SVDWeaponAssets::Matches(AKMViewmodel);')
 s=replace(s,'if (A762WeaponAssets::Matches(AKMViewmodel) || bPKM)','if (bSVD || A762WeaponAssets::Matches(AKMViewmodel) || bPKM)')
 s=replace(s,'const FString Path=bPKM?','const FString Path=bSVD?SVDAttachments::MeshPath(Key):bPKM?')
 s=replace(s,'bPKM?PKMAttachments::MuzzleMount:A762WeaponAssets::MuzzleMount','bSVD?SVDAttachments::MuzzleMount:bPKM?PKMAttachments::MuzzleMount:A762WeaponAssets::MuzzleMount')
 s=replace(s,'        MuzzleVariant=Enabled?Variant:FString();','        if(bSVD)SVDAttachments::FactorySections(AKMViewmodel,TEXT("FactoryMuzzle"),!Enabled);\n        MuzzleVariant=Enabled?Variant:FString();')
 return s
edit('Source/FPSGAME/Weapons/M4MuzzleVisual.cpp',muzzles)
for filename,family,component,method in [('M4VerticalForegrip.cpp','vertical','VerticalForegrip','SetVerticalForegrip'),('M4CantedForegrip.cpp','canted','CantedForegrip','SetCantedForegrip'),('M4AngledForegrip.cpp','angled','AngledForegrip','SetAngledForegrip'),('M4HandstopVisual.cpp','prism','PrismHandstop','')]:
 def grip(s):
  s=include(s)
  token=f'PKMLowpolyWeaponAssets::Matches(AKMViewmodel)?PKMAttachments::AnimationPath(TEXT("{family}"),Pair.Value)'
  s=replace(s,token,f'SVDWeaponAssets::Matches(AKMViewmodel)?SVDAttachments::AnimationPath(TEXT("{family}"),Pair.Value):'+token)
  s=replace(s,'if((bUseM16||PKMLowpolyWeaponAssets::Matches(AKMViewmodel))&&InspectAnimation)','if((bUseM16||SVDWeaponAssets::Matches(AKMViewmodel)||PKMLowpolyWeaponAssets::Matches(AKMViewmodel))&&InspectAnimation)')
  token=f'PKMLowpolyWeaponAssets::Matches(AKMViewmodel)?PKMAttachments::AnimationPath(TEXT("{family}"),TEXT("inspect"))'
  s=replace(s,token,f'SVDWeaponAssets::Matches(AKMViewmodel)?SVDAttachments::AnimationPath(TEXT("{family}"),TEXT("inspect")):'+token)
  token=f'    if(PKMLowpolyWeaponAssets::Matches(AKMViewmodel)){{{component}=PKMAttachments::Configure'
  enabled='Variant==TEXT("prism_handstop")' if family=='prism' else 'bEnabled'
  s=replace(s,token,f'    if(SVDWeaponAssets::Matches(AKMViewmodel)){{{component}=SVDAttachments::Configure(this,AKMViewmodel,{component},TEXT("{family}"),{enabled}&&bInventoryWeaponReady);return;}}\n'+token)
  if family=='prism':
   token='const FString Path=PKMLowpolyWeaponAssets::Matches(AKMViewmodel)?PKMAttachments::MeshPath(TEXT("tactical_vertical"))'
   s=replace(s,token,'const FString Path=SVDWeaponAssets::Matches(AKMViewmodel)?SVDAttachments::MeshPath(TEXT("tactical_vertical")):PKMLowpolyWeaponAssets::Matches(AKMViewmodel)?PKMAttachments::MeshPath(TEXT("tactical_vertical"))')
  return s
 edit('Source/FPSGAME/Weapons/'+filename,grip)
def character(s):
 s=replace(s,'#include "Weapons/SVDWeaponAssets.h"','#include "Weapons/SVDWeaponAssets.h"\n#include "Weapons/SVDAttachments.h"')
 s=replace(s,'if (!IsPistolWeapon() && !SVDWeaponAssets::Matches(AKMViewmodel))','if (!IsPistolWeapon())')
 s=replace(s,'    if(SVDWeaponAssets::Matches(AKMViewmodel))return QuickCombatAnimation;','''    if(SVDWeaponAssets::Matches(AKMViewmodel))
    {
        const TCHAR* Families[]={TEXT("base"),TEXT("base"),TEXT("angled"),TEXT("vertical"),TEXT("canted"),TEXT("prism")};
        const int32 Index=static_cast<int32>(Grip);
        return Index>1&&Index<UE_ARRAY_COUNT(Families)?LoadObject<UAnimSequence>(nullptr,*SVDAttachments::AnimationPath(Families[Index],TEXT("quick_melee"))):QuickCombatAnimation.Get();
    }''')
 return s
edit('Source/FPSGAME/FPSGAMECharacter.cpp',character)
def sprint(s):
 s=include(s)
 s=replace(s,'''        for(int32 Grip=0;Grip<6;++Grip)
            for(const TCHAR* Clip:{TEXT("sprint_enter"),TEXT("sprint_loop"),TEXT("sprint_exit")})
                Clips.Add(LoadObject<UAnimSequence>(nullptr,*SVDWeaponAssets::AnimationPath(Clip)));''','''        for(const TCHAR* Family:{TEXT("base"),TEXT("base"),TEXT("angled"),TEXT("vertical"),TEXT("canted"),TEXT("prism")})
            for(const TCHAR* Clip:{TEXT("sprint_enter"),TEXT("sprint_loop"),TEXT("sprint_exit")})
                Clips.Add(LoadObject<UAnimSequence>(nullptr,*(FCString::Strcmp(Family,TEXT("base"))==0?SVDWeaponAssets::AnimationPath(Clip):SVDAttachments::AnimationPath(Family,Clip))));''')
 return s
edit('Source/FPSGAME/Weapons/M4TacticalSprintComponent.cpp',sprint)
def tactical(s):
 s=include(s)
 s=replace(s,'const FString Path=Family==TEXT("PKM")?','const FString Path=Family==TEXT("SVD")?SVDAttachments::MeshPath(Variant):Family==TEXT("PKM")?')
 s=s.replace('!Pistol&&!ASH&&Family!=TEXT("PKM")','!Pistol&&!ASH&&Family!=TEXT("SVD")&&Family!=TEXT("PKM")')
 s=replace(s,'const FString Family=PKMLowpolyWeaponAssets::Matches(AKMViewmodel)?','const FString Family=SVDWeaponAssets::Matches(AKMViewmodel)?TEXT("SVD"):PKMLowpolyWeaponAssets::Matches(AKMViewmodel)?')
 return s
edit('Source/FPSGAME/Weapons/TacticalDeviceComponent.cpp',tactical)
def resources(s):
 s=replace(s,'#include "../Weapons/SVDWeaponAssets.h"','#include "../Weapons/SVDWeaponAssets.h"\n#include "../Weapons/SVDAttachments.h"')
 token='            if(D==TEXT("ue_a762"))Add(A762Attachments::MeshPath(Key));'
 s=replace(s,token,'''            if(D==TEXT("ue_svd"))
            {
                if(Part.Key==TEXT("muzzle")&&Key==TEXT("true"))Key=TEXT("suppressor");
                if(Part.Key!=TEXT("barrel"))Add(SVDAttachments::MeshPath(Key));
                if(Part.Key==TEXT("optic"))Add(SVDAttachments::MeshPath(TEXT("optic_bridge")));
                if(Key==TEXT("lpvo_1_6x"))Add(SVDAttachments::MeshPath(TEXT("lpvo_ring")));
                continue;
            }
'''+token)
 return s
edit('Source/FPSGAME/UI/ColdSteelIconResources.cpp',resources)
def weather(s):
 s=replace(s,'#include "Weapons/PSO1AttachmentAssets.h"','#include "Weapons/PSO1AttachmentAssets.h"\n#include "Weapons/SVDAttachments.h"')
 marker='        if(const auto* PSO1Materials=LoadObject<UWeatherPresentationAssets>(nullptr,PSO1AttachmentAssets::WetMaterialsPath))\n            for(const auto& Entry:PSO1Materials->WetMaterials)Assets->WetMaterials.Add(Entry.Key,Entry.Value);'
 return replace(s,marker,marker+'\n    if(Assets)\n        if(const auto* SVDMaterials=LoadObject<UWeatherPresentationAssets>(nullptr,SVDAttachments::WetMaterialsPath))\n            for(const auto& Entry:SVDMaterials->WetMaterials)Assets->WetMaterials.Add(Entry.Key,Entry.Value);')
edit('Source/FPSGAME/WeatherViewEffectsComponent.cpp',weather)
def overview(s):
 s=replace(s,'Optic==TEXT("pso1_4x")||G->Definition()==TEXT("ue_svd")','Optic==TEXT("pso1_4x")||(G->Definition()==TEXT("ue_svd")&&(Optic.IsEmpty()||Optic==TEXT("false")))')
 return replace(s,'else if(G->Definition()==TEXT("ue_akm")||G->Definition()==TEXT("ue_pkm_lowpoly"))','else if(G->Definition()==TEXT("ue_akm")||G->Definition()==TEXT("ue_pkm_lowpoly")||G->Definition()==TEXT("ue_svd"))')
edit('Source/FPSGAME/UI/M4GunsmithOverview.cpp',overview)
def config(s):
 marker='+DirectoriesToAlwaysCook=(Path="/Game/Weapons/PSO1Russian20260923")'
 return replace(s,marker,marker+'\n+DirectoriesToAlwaysCook=(Path="/Game/Weapons/SVDDragunov20260922/Accessories20260923")')
edit('Config/DefaultGame.ini',config)
def catalog(s):
 data=json.loads(s);svd=next(w for w in data['weapons'] if w['id']=='ue_svd');donor=next(w for w in data['weapons'] if w['id']=='ue_m4a1')
 svd['allowed']=['optic','muzzle','underbarrel','tactical'];svd['options']={k:copy.deepcopy(donor['options'][k]) for k in svd['allowed']}
 svd['options']['optic'][0].update(name='原厂 PSO-1 四倍镜',description='恢复 SVD 原厂侧置 PSO-1 和固定四倍分划。')
 svd['options']['muzzle'][0].update(name='原厂消焰器',description='使用 SVD 原厂长消焰器。')
 svd['options']['underbarrel'][0].update(name='原厂护木握持',description='卸下前握把和底部安装座，恢复 SVD 原厂护木握姿。')
 for slot in ['optic','muzzle','underbarrel','tactical']:
  for option in svd['options'][slot]:
   if option['id']!='false':option['description']=option['description'].replace('M4','SVD')
 start=s.index('    {\n      "id": "ue_svd"');end=s.index('\n    },',start)+len('\n    }')
 return s[:start]+'\n'.join('    '+line for line in json.dumps(svd,ensure_ascii=False,indent=2).splitlines())+s[end:]
edit('Content/ColdSteelData/gunsmith.json',catalog)
print('SVD_ATTACH_RUNTIME_WRITTEN')
