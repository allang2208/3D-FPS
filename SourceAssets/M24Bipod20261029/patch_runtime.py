"""Apply scoped native integrations; other weapon branches retain their behavior."""
from pathlib import Path
P=Path(__file__).resolve().parents[2]
def edit(file,pairs):
 p=P/file;s=p.read_text(encoding='utf-8-sig')
 for a,b in pairs:
  if a not in s:raise RuntimeError('Missing edit anchor '+file+' '+a[:80])
  s=s.replace(a,b)
 p.write_text(s,encoding='utf-8')
edit('Source/FPSGAME/Weapons/PKMBipodComponent.cpp',[
 ('#include "PKMBipodContacts.h"','#include "PKMBipodContacts.h"\n#include "M24Bipod.h"\n#include "M24Attachments.h"\n#include "WeaponGripProfile.h"'),
 ('return LMG201WeaponAssets::Matches(Rifle)?LMG201WeaponAssets::BipodPivotsCm[I]', 'return M24Bipod::Matches(Rifle)?M24Bipod::Pivots[I]:LMG201WeaponAssets::Matches(Rifle)?LMG201WeaponAssets::BipodPivotsCm[I]'),
 ('return LMG201WeaponAssets::Matches(Rifle)?LMG201WeaponAssets::BipodFeetCm[I]', 'return M24Bipod::Matches(Rifle)?M24Bipod::Tips[I]:LMG201WeaponAssets::Matches(Rifle)?LMG201WeaponAssets::BipodFeetCm[I]'),
 ('return LMG201WeaponAssets::Matches(Rifle)?LMG201WeaponAssets::BipodHingeCm','return M24Bipod::Matches(Rifle)?M24Bipod::Hinge:LMG201WeaponAssets::Matches(Rifle)?LMG201WeaponAssets::BipodHingeCm'),
 ('!PKMLowpolyWeaponAssets::Matches(Rifle)&&!LMG201WeaponAssets::Matches(Rifle)', '!PKMLowpolyWeaponAssets::Matches(Rifle)&&!LMG201WeaponAssets::Matches(Rifle)&&!M24Bipod::Matches(Rifle)'),
 ('nullptr,LMG201WeaponAssets::Matches(Rifle)?*LMG201WeaponAssets::PartPath(TEXT("BipodBase"))','nullptr,M24Bipod::Matches(Rifle)?M24Bipod::Base:LMG201WeaponAssets::Matches(Rifle)?*LMG201WeaponAssets::PartPath(TEXT("BipodBase"))'),
 ('nullptr,LMG201WeaponAssets::Matches(Rifle)?*LMG201WeaponAssets::PartPath(TEXT("BipodLegA"))','nullptr,M24Bipod::Matches(Rifle)?M24Bipod::LegA:LMG201WeaponAssets::Matches(Rifle)?*LMG201WeaponAssets::PartPath(TEXT("BipodLegA"))'),
 ('nullptr,LMG201WeaponAssets::Matches(Rifle)?*LMG201WeaponAssets::PartPath(TEXT("BipodLegB"))','nullptr,M24Bipod::Matches(Rifle)?M24Bipod::LegB:LMG201WeaponAssets::Matches(Rifle)?*LMG201WeaponAssets::PartPath(TEXT("BipodLegB"))'),
 ('SetRelativeTransform(FTransform(FQuat::Identity,FVector::ZeroVector,FVector(.01)));','SetRelativeTransform(M24Bipod::Matches(Rifle)?M24Attachments::Mount(Rifle):FTransform(FQuat::Identity,FVector::ZeroVector,FVector(.01)));\n    SetOnlyOwnerSee(Rifle->bOnlyOwnerSee);SetFirstPersonPrimitiveType(Rifle->FirstPersonPrimitiveType);'),
 ('Leg->SetRelativeTransform(FTransform(FQuat::Identity,BipodPivot(Rifle,Index)));','Leg->SetRelativeTransform(FTransform(FQuat::Identity,BipodPivot(Rifle,Index)));\n        Leg->SetOnlyOwnerSee(Rifle->bOnlyOwnerSee);Leg->SetFirstPersonPrimitiveType(Rifle->FirstPersonPrimitiveType);'),
 ('const FQuat FreeRotation(FVector::ForwardVector,Angles[I]);','const FQuat FreeRotation=M24Bipod::Matches(Weapon.Get())?M24Bipod::LegRotation(I,Angles[I]):FQuat(FVector::ForwardVector,Angles[I]);'),
 ('void UPKMBipodComponent::SetLegsFrozen(bool bFrozen)\n{','void UPKMBipodComponent::SetM24DeploymentTime(float Seconds)\n{\n    if(!M24Bipod::Matches(Weapon.Get()))return;\n    for(int32 I=0;I<2;++I)Angles[I]=M24Bipod::LegWeight(I,Seconds);\n    ApplyAngle();\n}\n\nvoid UPKMBipodComponent::SetLegsFrozen(bool bFrozen)\n{\n    if(M24Bipod::Matches(Weapon.Get()))return;'),
 ('if(bLegsFrozen)return;', 'if(M24Bipod::Matches(Weapon.Get()))return;\n    if(bLegsFrozen)return;'),
 ('!Matches(Weapon)&&!LMG201WeaponAssets::Matches(Weapon)', '!Matches(Weapon)&&!LMG201WeaponAssets::Matches(Weapon)&&!M24Bipod::Matches(Weapon)'),
 ('PKMLowpolyWeaponAssets::ConfigureBipod(this,AKMViewmodel,bInventoryWeaponReady&&(LMG201WeaponAssets::Matches(AKMViewmodel)?Variant!=TEXT("lmg201_no_bipod"):Variant==TEXT("pkm_bipod")));', '''const bool bM24=M24Bipod::Matches(AKMViewmodel);
    const bool Enabled=bInventoryWeaponReady&&(bM24?Variant==M24Bipod::Id:LMG201WeaponAssets::Matches(AKMViewmodel)?Variant!=TEXT("lmg201_no_bipod"):Variant==TEXT("pkm_bipod"));
    if(bM24&&Enabled&&!WeaponGripProfiles.Contains(TEXT("bipod")))
        if(auto* Profile=LoadObject<UWeaponGripProfile>(nullptr,M24Bipod::Profile))WeaponGripProfiles.Add(TEXT("bipod"),Profile);
    if(BipodDeployment&&(!Enabled||bM24))BipodDeployment->Release(true);
    PKMLowpolyWeaponAssets::ConfigureBipod(this,AKMViewmodel,Enabled);''')])
edit('Source/FPSGAME/FPSGAMECharacter.cpp',[
 ('WeaponADSFactor = CameraADSFactor;\n    AdvanceScopeOptics', 'if(BipodDeployment)CameraADSFactor*=BipodDeployment->AimPresentationWeight();\n    WeaponADSFactor = CameraADSFactor;\n    AdvanceScopeOptics'),
 ('    if (IsRevolverFireActionPlaying())\n    {\n        // A fired round', '    if(BipodDeployment&&BipodDeployment->DeferReload())return;\n    if (IsRevolverFireActionPlaying())\n    {\n        // A fired round'),
 ('    GunplayAnimation->bRevolver = bUseDanWesson715;', '    if(BipodDeployment)BipodDeployment->ApplyHandPose(*GunplayAnimation);\n    GunplayAnimation->bRevolver = bUseDanWesson715;')])
edit('Source/FPSGAME/Weapons/WeaponBipodDeploymentComponent.cpp',[
 ('#include "LMG201WeaponAssets.h"','#include "LMG201WeaponAssets.h"\n#include "M24Bipod.h"\n#include "M24WeaponAssets.h"\n#include "M24Attachments.h"\n#include "WeaponGripProfile.h"\n#include "FPSGunplayAnimInstance.h"\n#include "GunsmithSystem.h"\n#include "TimerManager.h"'),
 ('!LMG201WeaponAssets::Matches(C->AKMViewmodel)))','!LMG201WeaponAssets::Matches(C->AKMViewmodel)&&!M24Bipod::Matches(C->AKMViewmodel)))'),
 ('if(Blend>UE_SMALL_NUMBER)Release(true);','if(Blend>UE_SMALL_NUMBER)\n    {\n        if(IsM24())return false; // Finish folding before a new acquisition.\n        Release(true);\n    }'),
 ('if(!Eligible() || !C || !C->bIsAiming || C->bFireHeld || !Part)return false;','if(!Eligible() || !C || !C->bIsAiming || C->bFireHeld || !Part)return false;\n    if(IsM24()&&!C->WeaponGripProfiles.Contains(TEXT("bipod")))return false;'),
 ('if(auto* Part=Bipod.Get())Part->SetDeploymentContacts(FVector::ZeroVector,FVector::ZeroVector,0.f);','if(auto* Part=Bipod.Get()){Part->SetDeploymentContacts(FVector::ZeroVector,FVector::ZeroVector,0.f);Part->SetM24DeploymentTime(0.f);}'),
 ('bRequested?1.f/.32f:1.f/.16f','1.f/TransitionDuration(bRequested)'),
 ('    if(bRequested)ClampAim();\n    // 完全', '    if(auto* Part=Bipod.Get())Part->SetM24DeploymentTime(Blend*M24Bipod::Duration);\n    if(bRequested)ClampAim();\n    // 完全'),
 ('const FVector Full=(Support.Anchor-Part->GetHingeWorld())*FMath::SmoothStep(0.f,1.f,Blend);','const FVector Full=(Support.Anchor-Part->GetHingeWorld())*FMath::SmoothStep(0.f,1.f,PlacementBlend());'),
 ('    Part->SetLegsFrozen(bRequested);\n    if(!bRequested)Part->SetDeploymentContacts(FVector::ZeroVector,FVector::ZeroVector,0.f);','''    if(IsM24())
    {
        Part->SetM24DeploymentTime(Blend*M24Bipod::Duration);
        Part->SetDeploymentContacts(Support.Feet[0],Support.Feet[1],PlacementBlend());
    }
    else
    {
        Part->SetLegsFrozen(bRequested);
        if(!bRequested)Part->SetDeploymentContacts(FVector::ZeroVector,FVector::ZeroVector,0.f);
    }'''),
 ('if(bAfterPose&&SettleClock>=0.f&&C->AKMViewmodel)', 'if(bAfterPose&&!IsM24()&&SettleClock>=0.f&&C->AKMViewmodel)'),
 ('return FMath::Min(Blend,float(FMath::Clamp((Now-NetDeployment.StartedAt)/.32,0.,1.)));','const float Confirmed=FMath::Min(Blend,float(FMath::Clamp((Now-NetDeployment.StartedAt)/TransitionDuration(true),0.,1.)));\n    return IsM24()?M24Bipod::Seat(Confirmed):Confirmed;'),
 ('if(Definition!=PKMLowpolyWeaponAssets::Definition&&Definition!=LMG201WeaponAssets::Definition)return false;', '''if(Definition!=PKMLowpolyWeaponAssets::Definition&&Definition!=LMG201WeaponAssets::Definition&&Definition!=M24WeaponAssets::Definition)return false;
    if(Definition==M24WeaponAssets::Definition)
    {
        const auto* Model=C->GetNetShadowProfile();
        if(!Model&&C->IsLocallyControlled())Model=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
        const auto* Item=Model?Model->Equipped():nullptr;
        const auto* Gunsmith=GetWorld()->GetGameInstance()->GetSubsystem<UGunsmithSystem>();
        if(!Item||!Gunsmith||Gunsmith->Installed(*Item).FindRef(TEXT("bipod"))!=M24Bipod::Id)return false;
    }'''),
 ('const float Span=LMG?', 'const float Span=EquippedDefinition()==M24WeaponAssets::Definition?float((M24Bipod::Pivots[0]+M24Bipod::Tips[0]-M24Bipod::Pivots[1]-M24Bipod::Tips[1]).Size()):LMG?'),
 ('const float Weight=FMath::SmoothStep(0.f,1.f,Blend);','const float Weight=FMath::SmoothStep(0.f,1.f,PlacementBlend());')])
print('M24_BIPOD_NATIVE_INTEGRATION_WRITTEN')
