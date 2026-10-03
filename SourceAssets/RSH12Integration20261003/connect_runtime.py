"""Publish RSH-12 routing after its meshes and shared-motion profiles are saved."""
from pathlib import Path
import json,re,sys
O=Path(__file__).parent;P=O.parents[1];changed=[]
if not json.loads((O/'import_receipt.json').read_text())['complete'] and '--authoring-build' not in sys.argv:
    raise RuntimeError('RSH-12 assets must be saved before runtime publication')

def edit(relative,fn):
    path=P/relative;raw=path.read_bytes();bom=raw.startswith(b'\xef\xbb\xbf');text=raw.decode('utf-8-sig');new=fn(text)
    if new==text:return
    if path.read_bytes()!=raw:raise RuntimeError('Concurrent source edit: '+relative)
    backup=O/'BeforeSource'/relative;backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists():backup.write_bytes(raw)
    path.write_bytes((b'\xef\xbb\xbf' if bom else b'')+new.encode('utf-8'));changed.append(relative)

def replace(t,a,b):
    if b in t:return t
    if a not in t:raise RuntimeError('Source entry differs: '+a[:90])
    return t.replace(a,b)

def family(t):
    # Match complete definition comparisons, preserving each expression's precedence.
    return re.sub(r'([A-Za-z_][A-Za-z0-9_]*(?:->|\.)Definition)\s*(==|!=)\s*TEXT\("ue_dan_wesson715"\)',
        lambda m:'('+m[0]+('||' if m[2]=='==' else '&&')+m[1]+m[2]+'TEXT("ue_rsh12"))' if 'ue_rsh12' not in t else m[0],t)

for f in ('FPSGAMECharacterProfile.cpp','UI/ColdSteelPickupWeapon.cpp','UI/ColdSteelPickupStudio.cpp','UI/M4StandalonePreview.cpp',
    'UI/ColdSteelWeaponIcons.cpp','UI/ColdSteelInventoryTypes.h','UI/ColdSteelProfileRuntime.cpp','UI/ColdSteelAmmoRuntime.cpp'):
    edit('Source/FPSGAME/'+f,family)
edit('Source/FPSGAME/FPSGAMECharacter.h',lambda t:replace(t,
    '    bool IsG18Weapon() const { return ActiveInventoryWeaponDefinition == TEXT("ue_g18"); }',
    '    bool IsRSH12Weapon() const { return ActiveInventoryWeaponDefinition == TEXT("ue_rsh12"); }\n    bool SampleRSH12Presentation(UAnimSequence* Clip);\n    bool IsG18Weapon() const { return ActiveInventoryWeaponDefinition == TEXT("ue_g18"); }'))

def character(t):
    t=replace(t,'#include "Weapons/DanWesson715WeaponAssets.h"','#include "Weapons/DanWesson715WeaponAssets.h"\n#include "Weapons/RSH12WeaponAssets.h"')
    t=replace(t,'ViewmodelMesh = LoadObject<USkeletalMesh>(nullptr, DanWesson715WeaponAssets::MeshPath);',
        'ViewmodelMesh = LoadObject<USkeletalMesh>(nullptr, IsRSH12Weapon() ? RSH12WeaponAssets::MeshPath : DanWesson715WeaponAssets::MeshPath);')
    t=replace(t,'if (LMG201WeaponAssets::Matches(AKMViewmodel))\n    {\n        TMap<TObjectPtr<UAnimSequence>, TObjectPtr<UAnimSequence>> BaseSupport;',
        'if (LMG201WeaponAssets::Matches(AKMViewmodel) || IsRSH12Weapon())\n    {\n        TMap<TObjectPtr<UAnimSequence>, TObjectPtr<UAnimSequence>> BaseSupport;')
    t=replace(t,'bPistolWorkbench ? 6 : MagazineAmmo','bPistolWorkbench ? MagazineCapacity : MagazineAmmo')
    t=replace(t,'bPistolWorkbench ? 6 : RevolverCaseCount','bPistolWorkbench ? MagazineCapacity : RevolverCaseCount')
    t=replace(t,'HasInfiniteReserveAmmo() ? 6 : FMath::Min(6, MagazineAmmo + ReserveAmmo)',
        'HasInfiniteReserveAmmo() ? MagazineCapacity : FMath::Min(MagazineCapacity, MagazineAmmo + ReserveAmmo)')
    t=replace(t,'        GunplayAnimation->IdleClip = IdleAnimation;',
        '        if(IsRSH12Weapon())GunplayAnimation->GripProfile=WeaponGripProfileFor(EM4SprintGrip::Base);\n        GunplayAnimation->IdleClip = IdleAnimation;')
    # ADS uses the same marker corrections as the rendered pose.
    t=replace(t,'    const auto PositionAtRestAim = [&](int32 BoneIndex)',
        '    const auto* SightProfile=IsRSH12Weapon()?WeaponGripProfileFor(EM4SprintGrip::Base):nullptr;\n    const auto* SightLayer=SightProfile?SightProfile->Find(AimAnimation):nullptr;\n    const auto PositionAtRestAim = [&](int32 BoneIndex)')
    t=replace(t,'            AimAnimation->GetBoneTransform(Local, FSkeletonPoseBoneIndex(Index), FAnimExtractContext(0.0, false), false);\n            Transform = Transform * Local;',
        '            AimAnimation->GetBoneTransform(Local, FSkeletonPoseBoneIndex(Index), FAnimExtractContext(0.0, false), false);\n            if(SightLayer)SightLayer->ApplyLocal(Ref.GetBoneName(Index),0.f,Local);\n            Transform = Transform * Local;')
    # Share the installed 12.7 mm firing cue; the 715 still supplies mechanical cues.
    t=replace(t,'    FireSound = LoadAKMSound(TEXT("S_AKM_Fire"));',
        '    FireSound = LoadAKMSound(TEXT("S_AKM_Fire"));\n    if(IsRSH12Weapon())FireSound=LoadObject<USoundBase>(nullptr,ASH12WeaponAssets::FireSoundPath);')
    return t
edit('Source/FPSGAME/FPSGAMECharacter.cpp',character)
edit('Source/FPSGAME/FPSGAMECharacterProfile.cpp',lambda t:replace(t,'MagazineAmmo, 6);','MagazineAmmo, MagazineCapacity);'))
edit('Source/FPSGAME/UI/ColdSteelProfileRuntime.cpp',lambda t:replace(t,
    'Equipped()->Definition != TEXT("ue_dan_wesson715")',
    '(Equipped()->Definition != TEXT("ue_dan_wesson715") && Equipped()->Definition != TEXT("ue_rsh12"))'))
edit('Source/FPSGAME/Weapons/WeaponReloadStages.cpp',lambda t:replace(t,
    'Definition == TEXT("ue_dan_wesson715")','(Definition == TEXT("ue_dan_wesson715") || Definition == TEXT("ue_rsh12"))'))

def gunsmith(t):
    t=replace(t,'if(W.Id==DanWesson715WeaponAssets::Definition)','if(W.Id==DanWesson715WeaponAssets::Definition || W.Id==TEXT("ue_rsh12"))')
    t=replace(t,'DanWesson715WeaponAssets::SingleDuration(5);','DanWesson715WeaponAssets::SingleDuration(W.Base.Capacity-1);')
    t=replace(t,'DanWesson715WeaponAssets::SingleDuration(6, true);','DanWesson715WeaponAssets::SingleDuration(W.Base.Capacity, true);')
    t=replace(t,'DanWesson715WeaponAssets::SingleAnimationPath(1,5)','DanWesson715WeaponAssets::SingleAnimationPath(1,W.Base.Capacity-1)')
    t=replace(t,'DanWesson715WeaponAssets::SingleAnimationPath(0,6)','DanWesson715WeaponAssets::SingleAnimationPath(0,W.Base.Capacity)')
    return t
edit('Source/FPSGAME/Weapons/GunsmithSystem.cpp',gunsmith)

def dual(t):
    t=replace(t,'#include "DanWesson715WeaponAssets.h"','#include "DanWesson715WeaponAssets.h"\n#include "RSH12WeaponAssets.h"')
    t=family(t)
    t=replace(t,'H.Mesh->SetSkeletalMesh(LoadObject<USkeletalMesh>(nullptr,*(Base+TEXT("/SK_")+Name)));',
        'H.Mesh->SetSkeletalMesh(LoadObject<USkeletalMesh>(nullptr,*(Item.Definition==RSH12WeaponAssets::Definition ? RSH12WeaponAssets::DualMeshPath(Index) : Base+TEXT("/SK_")+Name)));')
    t=replace(t,'for(const TCHAR* Family:{TEXT("fitted"),TEXT("long")})','for(const TCHAR* Family:{TEXT("base"),TEXT("fitted"),TEXT("long")})')
    t=replace(t,'for(int32 Start=0;Start<6;++Start)for(int32 Count=1;Count<=6-Start;++Count)',
        'for(int32 Start=0,Capacity=Item.Definition==RSH12WeaponAssets::Definition?5:6;Start<Capacity;++Start)for(int32 Count=1;Count<=Capacity-Start;++Count)')
    t=replace(t,'H.Rounds,6):H.Rounds','H.Rounds,H.Stats.Capacity):H.Rounds')
    t=replace(t,'H.Anim->GripProfile=H.Action?H.PoseProfiles.FindRef(H.ActionPoseProfile).Get():nullptr;',
        'H.Anim->GripProfile=H.Action?H.PoseProfiles.FindRef(H.ActionPoseProfile).Get():nullptr;\n    if(!H.Anim->GripProfile && H.Item.Definition==RSH12WeaponAssets::Definition)H.Anim->GripProfile=H.PoseProfiles.FindRef(TEXT("base")).Get();')
    t=replace(t,'        if(PitViper)Path=PitViper2011WeaponAssets::SoundPath(CueName);',
        '        if(Item.Definition==RSH12WeaponAssets::Definition && FString(CueName)==TEXT("Fire"))Path=ASH12WeaponAssets::FireSoundPath;\n        if(PitViper)Path=PitViper2011WeaponAssets::SoundPath(CueName);')
    t=replace(t,'#include "RSH12WeaponAssets.h"','#include "RSH12WeaponAssets.h"\n#include "ASH12WeaponAssets.h"')
    return t
edit('Source/FPSGAME/Weapons/PistolDualWieldComponent.cpp',dual)

def resources(t):
    t=replace(t,'#include "../Weapons/DanWesson715WeaponAssets.h"','#include "../Weapons/DanWesson715WeaponAssets.h"\n#include "../Weapons/RSH12WeaponAssets.h"')
    a='else if(D==TEXT("ue_dan_wesson715")){Add(DanWesson715WeaponAssets::MeshPath,true);Add(DanWesson715WeaponAssets::AnimationPath(TEXT("idle")),true);}'
    return replace(t,a,'else if(D==RSH12WeaponAssets::Definition){Add(RSH12WeaponAssets::MeshPath,true);Add(RSH12WeaponAssets::AnimationPath(TEXT("idle")),true);Add(TEXT("/Game/Weapons/AnimationProfiles20261001/ue_rsh12/DA_base"),true);}\n        '+a)
edit('Source/FPSGAME/UI/ColdSteelIconResources.cpp',resources)
edit('Source/FPSGAME/UI/ColdSteelPickupWeapon.cpp',lambda t:replace(t,
    'Source->PlayAnimation(Rig->IdleAnimation,false);Source->SetPosition(0,false);',
    'if(!Rig->SampleRSH12Presentation(Rig->IdleAnimation)){Source->PlayAnimation(Rig->IdleAnimation,false);Source->SetPosition(0,false);}'))
edit('Source/FPSGAME/UI/ColdSteelWeaponIcons.cpp',lambda t:replace(t,
    'Mesh->PlayAnimation(Rig->IdleAnimation,false);Mesh->SetPosition(0.f,false);',
    'if(!Rig->SampleRSH12Presentation(Rig->IdleAnimation)){Mesh->PlayAnimation(Rig->IdleAnimation,false);Mesh->SetPosition(0.f,false);}'))
edit('Source/FPSGAME/UI/M4StandalonePreview.cpp',lambda t:replace(t,
    'Mesh->PlayAnimation(bAimPreview?Rig->AimAnimation:Rig->IdleAnimation,false);Mesh->SetPosition(0.f,false);',
    'if(!Rig->SampleRSH12Presentation(bAimPreview?Rig->AimAnimation:Rig->IdleAnimation)){Mesh->PlayAnimation(bAimPreview?Rig->AimAnimation:Rig->IdleAnimation,false);Mesh->SetPosition(0.f,false);}'))
def weather(t):
    t=replace(t,'#include "Weapons/DanWesson715WeaponAssets.h"','#include "Weapons/DanWesson715WeaponAssets.h"\n#include "Weapons/RSH12WeaponAssets.h"')
    return replace(t,'    Assets=InAssets;',
        '    Assets=InAssets;\n    if(Assets)\n        if(const auto* RSH12Materials=LoadObject<UWeatherPresentationAssets>(nullptr,RSH12WeaponAssets::WetMaterialsPath))\n            for(const auto& Entry:RSH12Materials->WetMaterials)Assets->WetMaterials.Add(Entry.Key,Entry.Value);')
edit('Source/FPSGAME/WeatherViewEffectsComponent.cpp',weather)

def warehouse(t):
    t=replace(t,'TEXT("ue_m1911"), TEXT("ue_dan_wesson715"),','TEXT("ue_m1911"), TEXT("ue_rsh12"), TEXT("ue_dan_wesson715"),')
    t=replace(t,'FString(Definition)==TEXT("ue_dan_wesson715")?6:', 'FString(Definition)==TEXT("ue_rsh12")?5:FString(Definition)==TEXT("ue_dan_wesson715")?6:')
    t=replace(t,'        if(FString(Definition)==TEXT("ue_dan_wesson715"))',
        '        if(FString(Definition)==TEXT("ue_rsh12"))\n        {\n            if(!AddAmmoToState(State,TEXT("ammo_127"),50))return false;\n        }\n        if(FString(Definition)==TEXT("ue_dan_wesson715"))')
    return t
edit('Source/FPSGAME/UI/ColdSteelWarehouseModel.cpp',warehouse)
edit('Config/DefaultGame.ini',lambda t:t if 'Path="/Game/Weapons/RSH12"' in t else t+'\n[/Script/UnrealEd.ProjectPackagingSettings]\n+DirectoriesToAlwaysCook=(Path="/Game/Weapons/RSH12")\n+DirectoriesToAlwaysCook=(Path="/Game/Weapons/AnimationProfiles20261001/ue_rsh12")\n')
(O/'runtime_edits.json').write_text(json.dumps(dict(modified=changed,runtime_tested=False),indent=2),encoding='utf-8')
print('RSH12_RUNTIME_SOURCE_PUBLISHED',len(changed))
