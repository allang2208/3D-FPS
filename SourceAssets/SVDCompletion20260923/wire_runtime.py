from pathlib import Path
import shutil
R=Path('D:/FPS3D/FPSGAME');O=R/'SourceAssets/SVDCompletion20260923';B=O/'Before';B.mkdir(exist_ok=True)
def edit(rel,changes):
 p=R/rel;raw=p.read_bytes();s=raw.decode('utf-8-sig');nl='\r\n' if '\r\n' in s else '\n';s=s.replace('\r\n','\n')
 backup=B/rel;backup.parent.mkdir(parents=True,exist_ok=True)
 if not backup.exists():backup.write_bytes(raw)
 for old,new in changes:
  if s.count(old)!=1:raise RuntimeError(f'{rel}: expected one match, found {s.count(old)} for {old[:90]}')
  s=s.replace(old,new,1)
 p.write_bytes(s.replace('\n',nl).encode('utf-8'))
header='''#pragma once
#include "CoreMinimal.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"

// SVD-specific actions and contacts. Shared Manny mesh/rest/skin remain unchanged.
// Markers are baked from the actual SVD into every action (metres in WPN_root).
namespace SVDWeaponAssets
{
    inline constexpr const TCHAR* Definition=TEXT("ue_svd");
    inline constexpr const TCHAR* MeshPath=TEXT("/Game/Weapons/SVDDragunov20260922/Complete20260923/SK_SVD_Manny.SK_SVD_Manny");
    inline constexpr const TCHAR* ItemAmmoId=TEXT("ammo_pkm_762x54r");
    inline constexpr float ADSRearEyeDistance=7.f;
    inline constexpr float Magnification=4.f;
    inline constexpr bool bSingleShotTrigger=true;
    inline constexpr float MagazineOut=52.f/120.f;
    inline constexpr float MagazineInsert=220.f/120.f;
    inline constexpr float MagazineSeat=240.f/120.f;
    inline constexpr float ChargeStart=268.f/120.f;
    inline constexpr float ChargePull=310.f/120.f;
    inline constexpr float ChargeRelease=350.f/120.f;
    inline constexpr float EquipPull=64.f/120.f;
    inline constexpr float EquipRelease=100.f/120.f;
    inline bool Matches(const USkeletalMeshComponent* Mesh)
    {
        return Mesh&&Mesh->GetSkeletalMeshAsset()&&Mesh->GetSkeletalMeshAsset()->GetPathName().StartsWith(TEXT("/Game/Weapons/SVDDragunov20260922/"));
    }
    inline FString AnimationPath(const TCHAR* Clip)
    {
        return FString::Printf(TEXT("/Game/Weapons/SVDDragunov20260922/Complete20260923/Animations/A_SVD_%s.A_SVD_%s"),Clip,Clip);
    }
    inline FString FireSoundPath(int32 Variant)
    {
        return FString::Printf(TEXT("/Game/Weapons/SVDDragunov20260922/Complete20260923/Audio/S_SVD_Fire_%02d"),Variant);
    }
}
'''
p=R/'Source/FPSGAME/Weapons/SVDWeaponAssets.h';b=B/'Source/FPSGAME/Weapons/SVDWeaponAssets.h';b.parent.mkdir(parents=True,exist_ok=True);b.write_bytes(p.read_bytes());p.write_text(header,encoding='utf-8')
edit('Source/FPSGAME/FPSGAMECharacter.h',[
 ('    float GetOpticMagnification() const { return OpticVariant==TEXT("lpvo_1_6x")?LPVOMagnification:(OpticVariant==TEXT("prism_scope_2x")?2.f:1.f); }','    bool HasSVDFactoryScope() const { return ActiveInventoryWeaponDefinition==TEXT("ue_svd"); }\n    float GetOpticMagnification() const { return HasSVDFactoryScope()?4.f:(OpticVariant==TEXT("lpvo_1_6x")?LPVOMagnification:(OpticVariant==TEXT("prism_scope_2x")?2.f:1.f)); }')])
edit('Source/FPSGAME/FPSGAMECharacter.cpp',[
 ('        // The mesh is bound to the shared M4 skeleton, so it must ride the M4 pose/cue\n        // clock (clips, arm framing, HK416 mechanical audio) rather than the AKM one.', '        // Dedicated SVD clips share the Manny skeleton and source-time cue clock.'),
 ('        bSingleShotTrigger=SVDWeaponAssets::bSingleShotTrigger;', '        bSingleShotTrigger=SVDWeaponAssets::bSingleShotTrigger;\n        bPistolShotPending=false;\n        HipViewmodelLocation=M4HipViewmodelLocation+FVector(6.f,0.f,0.f);\n        QuickCombatAnimation=LoadObject<UAnimSequence>(nullptr,*SVDWeaponAssets::AnimationPath(TEXT("quick_melee")));'),
 ('InspectAnimation = bUseDanWesson715 || bUseM16 || PKMLowpolyWeaponAssets::Matches(AKMViewmodel)', 'InspectAnimation = SVDWeaponAssets::Matches(AKMViewmodel) || bUseDanWesson715 || bUseM16 || PKMLowpolyWeaponAssets::Matches(AKMViewmodel)'),
 ('if (bUsingM4Infima && !bUseQBZ191 && !bUseM16 && !IsPistolWeapon() && !PKMLowpolyWeaponAssets::Matches(AKMViewmodel))','if (bUsingM4Infima && !bUseQBZ191 && !bUseM16 && !IsPistolWeapon() && !SVDWeaponAssets::Matches(AKMViewmodel) && !PKMLowpolyWeaponAssets::Matches(AKMViewmodel))'),
 ('            : PKMLowpolyWeaponAssets::Matches(AKMViewmodel) ? ERifleSprintWeapon::PKM','            : SVDWeaponAssets::Matches(AKMViewmodel) ? ERifleSprintWeapon::SVD\n            : PKMLowpolyWeaponAssets::Matches(AKMViewmodel) ? ERifleSprintWeapon::PKM'),
 ('            if (!bUseASH12 && !bUseM16)','            if (!bUseASH12 && !bUseM16 && !SVDWeaponAssets::Matches(AKMViewmodel))'),
 ('        if (!RifleFireVariants.IsEmpty()) FireSound = RifleFireVariants[0];','        if (SVDWeaponAssets::Matches(AKMViewmodel))\n            for(int32 Index=1;Index<=4;++Index)\n                if(auto* Sound=LoadObject<USoundBase>(nullptr,*SVDWeaponAssets::FireSoundPath(Index)))RifleFireVariants.Add(Sound);\n        if (!RifleFireVariants.IsEmpty()) FireSound = RifleFireVariants[0];'),
 ('        else if (bUseASH12)\n        {\n            // Reference remake:', '        else if (SVDWeaponAssets::Matches(AKMViewmodel))\n        {\n            MechanicalCueTimes={SVDWeaponAssets::MagazineOut,SVDWeaponAssets::MagazineInsert,SVDWeaponAssets::MagazineSeat};\n            MechanicalCueSounds={MagOutSound,MagInsertSound,MagSeatSound};\n            if(bPendingEmptyReload)\n            {\n                MechanicalCueTimes.Append({SVDWeaponAssets::ChargePull,SVDWeaponAssets::ChargeRelease});\n                MechanicalCueSounds.Append({ChargePullSound,ChargeReleaseSound});\n            }\n        }\n        else if (bUseASH12)\n        {\n            // Reference remake:'),
 ('UAnimSequence* AFPSGAMECharacter::RifleQuickCombatClip(EM4SprintGrip Grip)\n{', 'UAnimSequence* AFPSGAMECharacter::RifleQuickCombatClip(EM4SprintGrip Grip)\n{\n    if(SVDWeaponAssets::Matches(AKMViewmodel))return QuickCombatAnimation;'),
 ('    else if (bUseM16 && IsReloading() && ActiveActionAnimation)','    else if ((bUseM16 || SVDWeaponAssets::Matches(AKMViewmodel)) && IsReloading() && ActiveActionAnimation)'),
 ('        const float ReturnSeconds = WeaponState == EAKMWeaponState::ReloadingEmpty\n            ? 19.f / 60.f : 18.f / 60.f;','        const float ReturnSeconds = SVDWeaponAssets::Matches(AKMViewmodel) ? .45f : WeaponState == EAKMWeaponState::ReloadingEmpty\n            ? 19.f / 60.f : 18.f / 60.f;'),
 ('    else if (IsPistolWeapon())\n    {\n        // Original P9 Unholster:', '    else if (SVDWeaponAssets::Matches(AKMViewmodel))\n    {\n        MechanicalCueTimes={SVDWeaponAssets::EquipPull,SVDWeaponAssets::EquipRelease};\n        MechanicalCueSounds={ChargePullSound,ChargeReleaseSound};\n    }\n    else if (IsPistolWeapon())\n    {\n        // Original P9 Unholster:'),
 ('WeaponStateDuration = bUsingM4Infima && !IsPistolWeapon() ? 0.72f : EquipAnimation->GetPlayLength();','WeaponStateDuration = bUsingM4Infima && !IsPistolWeapon() && !SVDWeaponAssets::Matches(AKMViewmodel) ? 0.72f : EquipAnimation->GetPlayLength();'),
 ('    const bool bFinishedM16Reload = bUseM16 && IsReloading();','    const bool bFinishedM16Reload = (bUseM16 || SVDWeaponAssets::Matches(AKMViewmodel)) && IsReloading();'),
 ('UAnimSequence* AFPSGAMECharacter::LoadAKMAnimation(const TCHAR* AssetName)\n{','UAnimSequence* AFPSGAMECharacter::LoadAKMAnimation(const TCHAR* AssetName)\n{\n    if(ActiveInventoryWeaponDefinition==SVDWeaponAssets::Definition)\n    {\n        FString Clip(AssetName);Clip.RemoveFromStart(TEXT("A_AKM_"));\n        if(Clip.StartsWith(TEXT("equip")))Clip=TEXT("equip");\n        return LoadObject<UAnimSequence>(nullptr,*SVDWeaponAssets::AnimationPath(*Clip));\n    }'),
 ('USoundBase* AFPSGAMECharacter::LoadAKMSound(const TCHAR* AssetName)\n{','USoundBase* AFPSGAMECharacter::LoadAKMSound(const TCHAR* AssetName)\n{\n    if(SVDWeaponAssets::Matches(AKMViewmodel))\n    {\n        if(FCString::Strcmp(AssetName,TEXT("S_AKM_Fire"))==0)\n            return LoadObject<USoundBase>(nullptr,*SVDWeaponAssets::FireSoundPath(1));\n        return LoadObject<USoundBase>(nullptr,*FString::Printf(TEXT("/Game/Weapons/AKM/Audio/%s.%s"),AssetName,AssetName));\n    }'),
 ('        Rear=Root.TransformPosition(SVDWeaponAssets::SightRear)*ViewmodelScale;\n        Front=Root.TransformPosition(SVDWeaponAssets::SightFront)*ViewmodelScale;', '        // SVD clips carry their measured ocular/objective marker positions.\n        SightUp=Root.GetRotation().RotateVector(FVector::UpVector);'),
 ('    if(bHolographicOptic || IsPistolWeapon())CalibratedADSRotation=', '    if(bHolographicOptic || IsPistolWeapon() || SVDWeaponAssets::Matches(AKMViewmodel))CalibratedADSRotation=')])
edit('Source/FPSGAME/Weapons/WeaponReloadStages.cpp',[
 ('#include "ASH12WeaponAssets.h"','#include "ASH12WeaponAssets.h"\n#include "SVDWeaponAssets.h"'),
 ('    if (Definition == TEXT("ue_m1911"))', '    if (Definition == SVDWeaponAssets::Definition)\n        return {SVDWeaponAssets::MagazineInsert,SVDWeaponAssets::ChargeStart,Empty?SVDWeaponAssets::ChargeRelease:SVDWeaponAssets::MagazineInsert};\n    if (Definition == TEXT("ue_m1911"))')])
edit('Source/FPSGAME/Weapons/M4TacticalSprintComponent.h', [('None, M4, AKM, QBZ191, ASH12, M16, PKM','None, M4, AKM, QBZ191, ASH12, M16, PKM, SVD')])
edit('Source/FPSGAME/Weapons/M4TacticalSprintComponent.cpp',[
 ('#include "A762WeaponAssets.h"','#include "A762WeaponAssets.h"\n#include "SVDWeaponAssets.h"'),
 ('    if (Weapon==ERifleSprintWeapon::PKM)','    if (Weapon==ERifleSprintWeapon::SVD)\n    {\n        for(int32 Grip=0;Grip<6;++Grip)\n            for(const TCHAR* Clip:{TEXT("sprint_enter"),TEXT("sprint_loop"),TEXT("sprint_exit")})\n                Clips.Add(LoadObject<UAnimSequence>(nullptr,*SVDWeaponAssets::AnimationPath(Clip)));\n        return;\n    }\n    if (Weapon==ERifleSprintWeapon::PKM)')])
edit('Source/FPSGAME/Weapons/M4GunsmithVisual.cpp',[
 ('void AFPSGAMECharacter::SetGunsmithOpticVariant(const FString& Variant)\n{','void AFPSGAMECharacter::SetGunsmithOpticVariant(const FString& Variant)\n{\n    if(HasSVDFactoryScope())\n    {\n        // PSO-1 is part of the SVD assembly, independent of an empty optic slot.\n        bHolographicOptic=false;OpticVariant.Reset();return;\n    }'),
 ('    if(OpticVariant!=TEXT("lpvo_1_6x")||!bInventoryWeaponReady||IsTraversing()||IsWeaponBusy())return 0.f;','    if((!HasSVDFactoryScope()&&OpticVariant!=TEXT("lpvo_1_6x"))||!bInventoryWeaponReady||IsTraversing()||IsWeaponBusy())return 0.f;')])
# PSO-style chevrons are a presentation reticle; auxiliary marks do not claim
# metre-range ballistic zeroes for the game's fantasy damage/range model.
edit('Source/FPSGAME/UI/LPVOScopeWidget.cpp',[
 ('const FScopeFx& Fx)\n{\n    const FVector2f Size(G.GetLocalSize()),Center=Size*.5f;', 'const FScopeFx& Fx,bool bSVD)\n{\n    const FVector2f Size(G.GetLocalSize()),Center=Size*.5f;'),
 ('    const FLinearColor Red(1,.045f,.025f,Alpha);','''    if(bSVD)
    {
        const FLinearColor Ink(.035f,.045f,.035f,Alpha);
        auto Stroke=[&](TArray<FVector2D> Points)
        {
            for(auto& P:Points)P=FVector2D(Center)+P*S;
            FSlateDrawElement::MakeLines(Out,Layer+1,G.ToPaintGeometry(),Points,ESlateDrawEffect::None,Ink,true,1.6f*S);
        };
        Stroke({{-18,14},{0,0},{18,14}});
        for(float Y:{40.f,70.f,100.f})Stroke({{-12,Y+10},{0,Y},{12,Y+10}});
        Stroke({{-180,0},{-45,0}});Stroke({{45,0},{180,0}});
        for(float X:{-150.f,-120.f,-90.f,-60.f,60.f,90.f,120.f,150.f})Stroke({{X,-5},{X,5}});
        Stroke({{-170,150},{-50,150}});
        Stroke({{-170,85},{-145,101},{-120,115},{-95,126},{-70,134},{-50,139}});
        return;
    }
    const FLinearColor Red(1,.045f,.025f,Alpha);'''),
 ('        PaintLPVOScope(Elements,Result,Geometry,Alpha,Fx);','        PaintLPVOScope(Elements,Result,Geometry,Alpha,Fx,Character&&Character->HasSVDFactoryScope());')])
print('SVD_RUNTIME_WIRED')
