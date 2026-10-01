"""Scoped, anchored G18 integration. Backups preserve the existing worktree."""
from pathlib import Path
import shutil
P=Path('D:/FPS3D/FPSGAME');O=Path(__file__).parent
def edit(path,fn):
    p=P/path;old=p.read_text(encoding='utf-8-sig');new=fn(old)
    if new==old:return
    b=O/'CodeBefore'/path;b.parent.mkdir(parents=True,exist_ok=True)
    if not b.exists():shutil.copy2(p,b)
    p.write_text(new,encoding='utf-8')
def include(t):
    if '#include "G18WeaponAssets.h"' not in t:t='#include "G18WeaponAssets.h"\n'+t
    return t
def character(t):
    t=t.replace('#include "Weapons/M1911WeaponAssets.h"','#include "Weapons/M1911WeaponAssets.h"\n#include "Weapons/G18WeaponAssets.h"')
    t=t.replace('LoadObject<USkeletalMesh>(nullptr, M1911Source::MeshPath)','LoadObject<USkeletalMesh>(nullptr, IsG18Weapon() ? G18WeaponAssets::MeshPath : M1911Source::MeshPath)')
    t=t.replace('LoadObject<UAnimSequence>(nullptr, M1911WeaponAssets::QuickCombatAnimationPath)','LoadObject<UAnimSequence>(nullptr, IsG18Weapon() ? *G18WeaponAssets::AnimationPath(TEXT("quickcombat")) : M1911WeaponAssets::QuickCombatAnimationPath)')
    t=t.replace('*PistolLocomotionAssets::AnimationPath(bUseDanWesson715)','*(IsG18Weapon() ? G18WeaponAssets::AnimationPath(TEXT("sprint")) : PistolLocomotionAssets::AnimationPath(bUseDanWesson715))')
    t=t.replace('*PistolLocomotionAssets::AnimationPath(false, true)','*(IsG18Weapon() ? G18WeaponAssets::AnimationPath(TEXT("sprint_empty")) : PistolLocomotionAssets::AnimationPath(false, true))')
    t=t.replace('Gunsmith->Weapon(bUseDanWesson715 ? DanWesson715WeaponAssets::Definition : TEXT("ue_m1911"))','Gunsmith->Weapon(ActiveInventoryWeaponDefinition)')
    t=t.replace('return LoadObject<UAnimSequence>(nullptr, *M1911WeaponAssets::AnimationPath(*Clip));','return LoadObject<UAnimSequence>(nullptr, *(IsG18Weapon() ? G18WeaponAssets::AnimationPath(*Clip) : M1911WeaponAssets::AnimationPath(*Clip)));')
    marker='USoundBase* AFPSGAMECharacter::LoadAKMSound(const TCHAR* AssetName)\n{'
    t=t.replace(marker,marker+'\n    if (IsG18Weapon())\n    {\n        FString Cue(AssetName); Cue.RemoveFromStart(TEXT("S_AKM_"));\n        return LoadObject<USoundBase>(nullptr, *G18WeaponAssets::SoundPath(Cue));\n    }')
    return t
edit('Source/FPSGAME/FPSGAMECharacter.cpp',character)
edit('Source/FPSGAME/FPSGAMECharacter.h',lambda t:t.replace('bool UsesSingleShotTrigger() const { return IsPistolWeapon() || bSingleShotTrigger; }','bool IsG18Weapon() const { return ActiveInventoryWeaponDefinition == TEXT("ue_g18"); }\n    bool UsesSingleShotTrigger() const { return !IsG18Weapon() && (IsPistolWeapon() || bSingleShotTrigger); }'))
# Existing bUseM1911 is the magazine-fed-pistol presentation family. Identity,
# cadence and every actual mesh/clip remain separately selected by Definition.
for path in ['Source/FPSGAME/FPSGAMECharacterProfile.cpp','Source/FPSGAME/UI/ColdSteelPickupWeapon.cpp','Source/FPSGAME/UI/ColdSteelPickupStudio.cpp','Source/FPSGAME/UI/M4StandalonePreview.cpp','Source/FPSGAME/UI/ColdSteelWeaponIcons.cpp','Source/FPSGAME/UI/ColdSteelInventoryTypes.h']:
    def broaden(t):
        for expr in ('I->Definition','Item.Definition','I.Definition'):
            t=t.replace(expr+'==TEXT("ue_m1911")','('+expr+'==TEXT("ue_m1911")||'+expr+'==TEXT("ue_g18"))')
            t=t.replace(expr+'!=TEXT("ue_m1911")',expr+'!=TEXT("ue_m1911")&&'+expr+'!=TEXT("ue_g18")')
        return t
    edit(path,broaden)
edit('Source/FPSGAME/Weapons/WeaponReloadStages.cpp',lambda t:t.replace('if (Definition == TEXT("ue_m1911"))','if (Definition == TEXT("ue_m1911") || Definition == TEXT("ue_g18"))'))
edit('Source/FPSGAME/Weapons/GunsmithSystem.cpp',lambda t:include(t).replace('if(W.Id==TEXT("ue_m1911"))','if(W.Id==TEXT("ue_m1911") || W.Id==G18WeaponAssets::Definition)').replace('*M1911WeaponAssets::AnimationPath(TEXT("reload"))','*(W.Id==G18WeaponAssets::Definition ? G18WeaponAssets::AnimationPath(TEXT("reload")) : M1911WeaponAssets::AnimationPath(TEXT("reload")))').replace('*M1911WeaponAssets::AnimationPath(TEXT("reload_empty"))','*(W.Id==G18WeaponAssets::Definition ? G18WeaponAssets::AnimationPath(TEXT("reload_empty")) : M1911WeaponAssets::AnimationPath(TEXT("reload_empty")))'))
def dual(t):
    t=include(t)
    t=t.replace('const FString Base=Root(H.Revolver,Index),Name=Stem(H.Revolver,Index);','const bool G18=Item.Definition==G18WeaponAssets::Definition;\n    const FString Base=G18?G18WeaponAssets::DualRoot(Index):Root(H.Revolver,Index),Name=G18?G18WeaponAssets::DualStem(Index):Stem(H.Revolver,Index);')
    t=t.replace('const TCHAR* Revision=Kind.StartsWith(TEXT("sprint"))?', 'if(G18){H.Clips.Add(Kind,LoadObject<UAnimSequence>(nullptr,*G18WeaponAssets::DualAnimationPath(Index,Kind)));return;}\n        const TCHAR* Revision=Kind.StartsWith(TEXT("sprint"))?')
    t=t.replace('if(H.Revolver && FString(Kind).EndsWith(TEXT("_empty")))continue;','if(G18){Clip(Kind);continue;}\n        if(H.Revolver && FString(Kind).EndsWith(TEXT("_empty")))continue;')
    t=t.replace('H.Sounds.Add(CueName,LoadObject<USoundBase>(nullptr,*Path));','if(G18)Path=G18WeaponAssets::SoundPath(CueName);\n        H.Sounds.Add(CueName,LoadObject<USoundBase>(nullptr,*Path));')
    t=t.replace('if(Created){Rig->bUseM4Infima', 'if(Created){Rig->ActiveInventoryWeaponDefinition=Item.Definition;Rig->bUseM4Infima')
    t=t.replace('Hands[1].Revolver?TEXT("DanWesson715"):TEXT("M1911")','Hands[1].Item.Definition==G18WeaponAssets::Definition?TEXT("G18"):Hands[1].Revolver?TEXT("DanWesson715"):TEXT("M1911")')
    t=t.replace('*M1911WeaponAssets::AnimationPath(TEXT("inspect_empty"))','*(Player && Player->IsG18Weapon() ? G18WeaponAssets::AnimationPath(TEXT("inspect_empty")) : M1911WeaponAssets::AnimationPath(TEXT("inspect_empty")))')
    return t
edit('Source/FPSGAME/Weapons/PistolDualWieldComponent.cpp',dual)
def dualcombat(t):
    t=include(t).replace('if(!H.Pending || !H.Held','if((!H.Pending && H.Item.Definition!=G18WeaponAssets::Definition) || !H.Held')
    t=t.replace('else if(auto* Sound=H.Sounds.FindRef(TEXT("DryClick")).Get())UGameplayStatics::PlaySound2D(this,Sound,.65f);','else { if(auto* Sound=H.Sounds.FindRef(TEXT("DryClick")).Get())UGameplayStatics::PlaySound2D(this,Sound,.65f); H.Held=false; }')
    return t
edit('Source/FPSGAME/Weapons/PistolDualWieldCombat.cpp',dualcombat)
def attachments(t):
    return include(t).replace('*M1911WeaponAssets::AttachmentPath(Variant)','*(IsG18Weapon()?G18WeaponAssets::AttachmentPath(Variant):M1911WeaponAssets::AttachmentPath(Variant))').replace('*M1911WeaponAssets::AttachmentPath(Part)','*(IsG18Weapon()?G18WeaponAssets::AttachmentPath(Part):M1911WeaponAssets::AttachmentPath(Part))').replace('Up * .598f','Up * (IsG18Weapon()?0.f:.598f)').replace('TEXT("/Game/Weapons/M4MuzzlesV1/S_M4_Suppressed")','IsG18Weapon()?*G18WeaponAssets::SoundPath(TEXT("Suppressed")):TEXT("/Game/Weapons/M4MuzzlesV1/S_M4_Suppressed")')
edit('Source/FPSGAME/Weapons/M1911AttachmentVisual.cpp',attachments)
edit('Source/FPSGAME/Weapons/M1911MagazineVisual.cpp',lambda t:include(t).replace('Asset->GetMaterials()[M].MaterialSlotName == TEXT("M_M1911_Hero_Magazine")','(Asset->GetMaterials()[M].MaterialSlotName == TEXT("M_M1911_Hero_Magazine") || Asset->GetMaterials()[M].MaterialSlotName == TEXT("M_G18_Magazine"))').replace('*M1911WeaponAssets::AttachmentPath(TEXT("ext_mag"))','*(G18WeaponAssets::Matches(Host)?G18WeaponAssets::AttachmentPath(TEXT("ext_mag")):M1911WeaponAssets::AttachmentPath(TEXT("ext_mag")))'))
def icon(t):
    t=t.replace('#include "../Weapons/M1911WeaponAssets.h"','#include "../Weapons/M1911WeaponAssets.h"\n#include "../Weapons/G18WeaponAssets.h"')
    t=t.replace('else if(D==TEXT("ue_m1911")){Add(', 'else if(D==G18WeaponAssets::Definition){Add(G18WeaponAssets::MeshPath,true);Add(G18WeaponAssets::AnimationPath(TEXT("idle")),true);}\n        else if(D==TEXT("ue_m1911")){Add(')
    t=t.replace('else if(D==TEXT("ue_m1911"))Add(M1911WeaponAssets::AttachmentPath(Key));','else if(D==G18WeaponAssets::Definition)Add(G18WeaponAssets::AttachmentPath(Key));\n            else if(D==TEXT("ue_m1911"))Add(M1911WeaponAssets::AttachmentPath(Key));')
    return t
edit('Source/FPSGAME/UI/ColdSteelIconResources.cpp',icon)
def warehouse(t):
    t=t.replace('{TEXT("ue_svd"),','{TEXT("ue_g18"), TEXT("ue_svd"),')
    t=t.replace('Gun.Magazine=IsMeleeWeapon(Gun)?0:', 'Gun.Magazine=IsMeleeWeapon(Gun)?0:FString(Definition)==TEXT("ue_g18")?17:')
    t=t.replace('if(FString(Definition)==TEXT("ue_m1911"))','if(FString(Definition)==TEXT("ue_g18"))\n        {\n            if(!AddAmmoToState(State,TEXT("ammo_9"),170))return false;\n        }\n        if(FString(Definition)==TEXT("ue_m1911"))')
    return t
edit('Source/FPSGAME/UI/ColdSteelWarehouseModel.cpp',warehouse)
edit('Config/DefaultGame.ini',lambda t:t.replace('+DirectoriesToAlwaysCook=(Path="/Game/Weapons/M1911/RearFinish20260913")','+DirectoriesToAlwaysCook=(Path="/Game/Weapons/M1911/RearFinish20260913")\n+DirectoriesToAlwaysCook=(Path="/Game/Weapons/G18")'))
print('G18 scoped source integration written')
