"""Scoped runtime routing for the saved PitViper2011 family; retain other edits."""
from pathlib import Path
import json
O=Path(__file__).parent;P=O.parents[1];changed=[]
def edit(relative,transform):
    path=P/relative;raw=path.read_bytes();bom=raw.startswith(b'\xef\xbb\xbf');text=raw.decode('utf-8-sig');new=transform(text)
    if new==text:return
    if path.read_bytes()!=raw:raise RuntimeError('Source changed during edit: '+str(path))
    backup=O/'BeforeSource'/relative;backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists():backup.write_bytes(raw)
    path.write_bytes((b'\xef\xbb\xbf' if bom else b'')+new.encode('utf8'));changed.append(relative)
def exact(text,old,new):
    if new in text:return text
    if old in text:return text.replace(old,new)
    raise RuntimeError('Routing source differs at: '+old[:110])
family=['Source/FPSGAME/FPSGAMECharacterProfile.cpp','Source/FPSGAME/UI/ColdSteelPickupWeapon.cpp','Source/FPSGAME/UI/ColdSteelPickupStudio.cpp','Source/FPSGAME/UI/M4StandalonePreview.cpp','Source/FPSGAME/UI/ColdSteelWeaponIcons.cpp','Source/FPSGAME/UI/ColdSteelInventoryTypes.h']
def extend_family(text):
    for field in ['I->Definition','I.Definition','Item.Definition']:
        for op,join in [('==','||'),('!=','&&')]:
            old=field+op+'TEXT("ue_g18")';new=old+join+field+op+'TEXT("ue_pit_viper2011")'
            if new not in text:text=text.replace(old,new)
    return text
for path in family:edit(path,extend_family)
edit('Source/FPSGAME/FPSGAMECharacter.h',lambda t:exact(t,'    bool IsG18Weapon() const { return ActiveInventoryWeaponDefinition == TEXT("ue_g18"); }','    bool IsG18Weapon() const { return ActiveInventoryWeaponDefinition == TEXT("ue_g18"); }\n    bool IsPitViperWeapon() const { return ActiveInventoryWeaponDefinition == TEXT("ue_pit_viper2011"); }'))
def character(t):
    pairs=[('#include "Weapons/G18WeaponAssets.h"','#include "Weapons/G18WeaponAssets.h"\n#include "Weapons/PitViper2011WeaponAssets.h"'),
      ('IsG18Weapon() ? G18WeaponAssets::MeshPath : M1911Source::MeshPath','IsPitViperWeapon() ? PitViper2011WeaponAssets::MeshPath : IsG18Weapon() ? G18WeaponAssets::MeshPath : M1911Source::MeshPath'),
      ('IsG18Weapon() ? *G18WeaponAssets::AnimationPath(TEXT("quickcombat")) : M1911WeaponAssets::QuickCombatAnimationPath','IsPitViperWeapon() ? *PitViper2011WeaponAssets::AnimationPath(TEXT("quickcombat")) : IsG18Weapon() ? *G18WeaponAssets::AnimationPath(TEXT("quickcombat")) : M1911WeaponAssets::QuickCombatAnimationPath'),
      ('bUseM1911 ? M1911WeaponAssets::ViewmodelBoundsScale : 1.f','IsPitViperWeapon() ? PitViper2011WeaponAssets::ViewmodelBoundsScale : bUseM1911 ? M1911WeaponAssets::ViewmodelBoundsScale : 1.f'),
      ('IsG18Weapon() ? G18WeaponAssets::AnimationPath(TEXT("sprint")) : PistolLocomotionAssets::AnimationPath(bUseDanWesson715)','IsPitViperWeapon() ? PitViper2011WeaponAssets::AnimationPath(TEXT("sprint")) : IsG18Weapon() ? G18WeaponAssets::AnimationPath(TEXT("sprint")) : PistolLocomotionAssets::AnimationPath(bUseDanWesson715)'),
      ('IsG18Weapon() ? G18WeaponAssets::AnimationPath(TEXT("sprint_empty")) : PistolLocomotionAssets::AnimationPath(false, true)','IsPitViperWeapon() ? PitViper2011WeaponAssets::AnimationPath(TEXT("sprint_empty")) : IsG18Weapon() ? G18WeaponAssets::AnimationPath(TEXT("sprint_empty")) : PistolLocomotionAssets::AnimationPath(false, true)'),
      ('IsG18Weapon() ? G18WeaponAssets::AnimationPath(*Clip) : M1911WeaponAssets::AnimationPath(*Clip)','IsPitViperWeapon() ? PitViper2011WeaponAssets::AnimationPath(*Clip) : IsG18Weapon() ? G18WeaponAssets::AnimationPath(*Clip) : M1911WeaponAssets::AnimationPath(*Clip)'),
      ('    if (IsG18Weapon())\n    {\n        FString Cue(AssetName); Cue.RemoveFromStart(TEXT("S_AKM_"));',
       '    if (IsPitViperWeapon())\n    {\n        FString Cue(AssetName); Cue.RemoveFromStart(TEXT("S_AKM_"));\n        return LoadObject<USoundBase>(nullptr, *PitViper2011WeaponAssets::SoundPath(Cue));\n    }\n    if (IsG18Weapon())\n    {\n        FString Cue(AssetName); Cue.RemoveFromStart(TEXT("S_AKM_"));')]
    for old,new in pairs:t=exact(t,old,new)
    return t
edit('Source/FPSGAME/FPSGAMECharacter.cpp',character)
def dual(t):
    pairs=[('#include "G18WeaponAssets.h"','#include "G18WeaponAssets.h"\n#include "PitViper2011WeaponAssets.h"'),
      ('    const bool G18=Item.Definition==G18WeaponAssets::Definition;','    const bool G18=Item.Definition==G18WeaponAssets::Definition;\n    const bool PitViper=Item.Definition==PitViper2011WeaponAssets::Definition;'),
      ('Base=G18?G18WeaponAssets::DualRoot(Index):Root(H.Revolver,Index),Name=G18?G18WeaponAssets::DualStem(Index):Stem(H.Revolver,Index);','Base=PitViper?PitViper2011WeaponAssets::DualRoot(Index):G18?G18WeaponAssets::DualRoot(Index):Root(H.Revolver,Index),Name=PitViper?PitViper2011WeaponAssets::DualStem(Index):G18?G18WeaponAssets::DualStem(Index):Stem(H.Revolver,Index);'),
      ('        if(G18){H.Clips.Add(Kind,LoadObject<UAnimSequence>(nullptr,*G18WeaponAssets::DualAnimationPath(Index,Kind)));return;}','        if(PitViper){H.Clips.Add(Kind,LoadObject<UAnimSequence>(nullptr,*PitViper2011WeaponAssets::DualAnimationPath(Index,Kind)));return;}\n        if(G18){H.Clips.Add(Kind,LoadObject<UAnimSequence>(nullptr,*G18WeaponAssets::DualAnimationPath(Index,Kind)));return;}'),
      ('        if(G18){Clip(Kind);continue;}','        if(G18 || PitViper){Clip(Kind);continue;}'),
      ('        if(G18)Path=G18WeaponAssets::SoundPath(CueName);','        if(PitViper)Path=PitViper2011WeaponAssets::SoundPath(CueName);\n        if(G18)Path=G18WeaponAssets::SoundPath(CueName);'),
      ('OwnerPlayer && OwnerPlayer->IsG18Weapon() ? G18WeaponAssets::AnimationPath(TEXT("inspect_empty")) : M1911WeaponAssets::AnimationPath(TEXT("inspect_empty"))','OwnerPlayer && OwnerPlayer->IsPitViperWeapon() ? PitViper2011WeaponAssets::AnimationPath(TEXT("inspect_empty")) : OwnerPlayer && OwnerPlayer->IsG18Weapon() ? G18WeaponAssets::AnimationPath(TEXT("inspect_empty")) : M1911WeaponAssets::AnimationPath(TEXT("inspect_empty"))'),
      ('(IsEquipping() && H.Item.Definition!=G18WeaponAssets::Definition)','(IsEquipping() && H.Item.Definition!=G18WeaponAssets::Definition && H.Item.Definition!=PitViper2011WeaponAssets::Definition)')]
    for a,b in pairs:t=exact(t,a,b)
    return t
edit('Source/FPSGAME/Weapons/PistolDualWieldComponent.cpp',dual)
def dual_combat(t):
    t=exact(t,'#include "G18WeaponAssets.h"','#include "G18WeaponAssets.h"\n#include "PitViper2011WeaponAssets.h"')
    return exact(t,'(IsEquipping() && H.Item.Definition!=G18WeaponAssets::Definition)','(IsEquipping() && H.Item.Definition!=G18WeaponAssets::Definition && H.Item.Definition!=PitViper2011WeaponAssets::Definition)')
edit('Source/FPSGAME/Weapons/PistolDualWieldCombat.cpp',dual_combat)
def gunsmith(t):
    t=exact(t,'#include "G18WeaponAssets.h"','#include "G18WeaponAssets.h"\n#include "PitViper2011WeaponAssets.h"')
    t=exact(t,'W.Id==TEXT("ue_m1911") || W.Id==G18WeaponAssets::Definition','W.Id==TEXT("ue_m1911") || W.Id==G18WeaponAssets::Definition || W.Id==PitViper2011WeaponAssets::Definition')
    for clip in ['reload','reload_empty']:
        old='W.Id==G18WeaponAssets::Definition ? G18WeaponAssets::AnimationPath(TEXT("'+clip+'")) : M1911WeaponAssets::AnimationPath(TEXT("'+clip+'"))'
        t=exact(t,old,'W.Id==PitViper2011WeaponAssets::Definition ? PitViper2011WeaponAssets::AnimationPath(TEXT("'+clip+'")) : '+old)
    return t
edit('Source/FPSGAME/Weapons/GunsmithSystem.cpp',gunsmith)
edit('Source/FPSGAME/Weapons/WeaponReloadStages.cpp',lambda t:exact(t,'Definition == TEXT("ue_m1911") || Definition == TEXT("ue_g18")','Definition == TEXT("ue_m1911") || Definition == TEXT("ue_g18") || Definition == TEXT("ue_pit_viper2011")'))
def resources(t):
    t=exact(t,'#include "../Weapons/G18WeaponAssets.h"','#include "../Weapons/G18WeaponAssets.h"\n#include "../Weapons/PitViper2011WeaponAssets.h"')
    old='else if(D==G18WeaponAssets::Definition){Add(G18WeaponAssets::MeshPath,true);Add(G18WeaponAssets::AnimationPath(TEXT("idle")),true);}'
    return exact(t,old,'else if(D==PitViper2011WeaponAssets::Definition){Add(PitViper2011WeaponAssets::MeshPath,true);Add(PitViper2011WeaponAssets::AnimationPath(TEXT("idle")),true);}\n        '+old)
edit('Source/FPSGAME/UI/ColdSteelIconResources.cpp',resources)
edit('Source/FPSGAME/UI/ColdSteelWeaponIconCatalogCommandlet.cpp',lambda t:exact(t,'TEXT("ue_m1911"),TEXT("ue_g18"),','TEXT("ue_m1911"),TEXT("ue_pit_viper2011"),TEXT("ue_g18"),'))
def warehouse(t):
    t=exact(t,'TEXT("ue_hk416"), TEXT("ue_g18"),','TEXT("ue_hk416"), TEXT("ue_pit_viper2011"), TEXT("ue_g18"),')
    t=exact(t,'IsMeleeWeapon(Gun)?0:FString(Definition)==TEXT("ue_g18")?17:','IsMeleeWeapon(Gun)?0:FString(Definition)==TEXT("ue_pit_viper2011")?15:FString(Definition)==TEXT("ue_g18")?17:')
    return exact(t,'        if(FString(Definition)==TEXT("ue_g18"))','        if(FString(Definition)==TEXT("ue_pit_viper2011"))\n        {\n            if(!AddAmmoToState(State,TEXT("ammo_9"),150))return false;\n        }\n        if(FString(Definition)==TEXT("ue_g18"))')
edit('Source/FPSGAME/UI/ColdSteelWarehouseModel.cpp',warehouse)
def cook(t):
    line='+DirectoriesToAlwaysCook=(Path="/Game/Weapons/PitViper2011")'
    return t if line in t else t+'\r\n; Pit Viper 2011 runtime string-loaded assets.\r\n[/Script/UnrealEd.ProjectPackagingSettings]\r\n'+line+'\r\n'
edit('Config/DefaultGame.ini',cook)
(O/'runtime_edits.json').write_text(json.dumps({'modified':sorted(str(f.relative_to(O/'BeforeSource')).replace('\\','/') for f in (O/'BeforeSource').rglob('*') if f.is_file()),'scope':'PitViper2011 family routing and starting armory; semiautomatic existing input path','runtime_tested':False},indent=2),encoding='utf8')
print('PitViper2011 runtime source connected:',len(changed),'files')
