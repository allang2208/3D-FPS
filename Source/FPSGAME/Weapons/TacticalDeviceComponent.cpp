#include "TacticalDeviceComponent.h"
#include "../FPSGAMECharacter.h"
#include "AKMSovietCalibration.h"
#include "GunsmithSystem.h"
#include "DanWesson715WeaponAssets.h"
#include "Engine/GameInstance.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/SpotLightComponent.h"
#include "Camera/CameraComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/SkeletalMesh.h"
#include "Materials/MaterialInterface.h"
#include "Engine/World.h"

namespace
{
FTransform PistolTacticalMount(const USkeletalMeshComponent* Mesh)
{
    const auto& Ref=Mesh->GetSkeletalMeshAsset()->GetRefSkeleton();
    auto Bone=[&Ref](const TCHAR* Name)
    {
        FTransform Pose=FTransform::Identity;
        for(int32 I=Ref.FindBoneIndex(Name);I!=INDEX_NONE;I=Ref.GetParentIndex(I))
            Pose=Pose*Ref.GetRefBonePose()[I];
        return Pose;
    };
    const FTransform Root=Bone(TEXT("WPN_root"));
    const FVector Up=Root.GetRotation().GetAxisZ();
    const FVector Forward=FVector::VectorPlaneProject(
        Bone(TEXT("WPN_FrontSight")).GetLocation()-Bone(TEXT("WPN_RearSight")).GetLocation(),Up).GetSafeNormal();
    // The fitted FBX is in centimetres, with +Y along the barrel and +Z up.
    // Resolve the skeletal bone frame without inheriting the rifles' metre scale.
    const FQuat SourceFrame=FRotationMatrix::MakeFromXZ(FVector::RightVector,FVector::UpVector).ToQuat();
    const FTransform Mount(FRotationMatrix::MakeFromXZ(Forward,Up).ToQuat()*SourceFrame.Inverse(),Root.GetLocation());
    return Mount.GetRelativeTransform(Root);
}
}

UTacticalDeviceComponent::UTacticalDeviceComponent()
{
    PrimaryComponentTick.bCanEverTick=true;
    PrimaryComponentTick.bStartWithTickEnabled=false;
    PrimaryComponentTick.TickGroup=TG_PostUpdateWork;
}
void UTacticalDeviceComponent::HideEffects()
{
    if(Dot)Dot->SetVisibility(false);
    if(Beam)Beam->SetVisibility(false);
    if(Light)Light->SetVisibility(false);
}
void UTacticalDeviceComponent::Configure(const FString& Family,const FString& Variant,USkeletalMeshComponent* Rifle,bool Enabled)
{
    HideEffects();Kind=Variant;Host=Rifle;
    if(Body)Body->SetVisibility(false);
    const bool Active=Enabled&&Rifle&&(Variant==TEXT("laser")||Variant==TEXT("flashlight"));
    SetComponentTickEnabled(Active);
    if(!Active)return;
    const bool Revolver=Family==TEXT("DanWesson715");
    const bool Pistol=Family==TEXT("M1911")||Revolver;
    const FString Path=Revolver?DanWesson715WeaponAssets::AttachmentPath(Variant):Pistol
        ?FString::Printf(TEXT("/Game/Weapons/M1911/CompactFit20260913/%s/SM_TacticalDevice"),*Variant)
        :Variant==TEXT("flashlight")
        ?FString::Printf(TEXT("/Game/Weapons/TacticalDevices20260913/HunyuanV3/%s/flashlight/SM_TacticalDevice"),*Family)
        :FString::Printf(TEXT("/Game/Weapons/TacticalDevices20260913/%s/%s/SM_TacticalDevice"),*Family,*Variant);
    if(!Body)
    {
        Body=NewObject<UStaticMeshComponent>(GetOwner(),TEXT("TacticalDeviceBody"));
        Body->SetCollisionEnabled(ECollisionEnabled::NoCollision);Body->SetCastShadow(false);Body->bReceivesDecals=false;
        Body->SetupAttachment(Rifle,TEXT("WPN_root"));Body->RegisterComponent();
        AddTickPrerequisiteComponent(Rifle);
    }
    if(AssetPath!=Path||!Body->GetStaticMesh())
    {
        Body->EmptyOverrideMaterials();
        Body->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,*Path));AssetPath=Path;
    }
    if(!Pistol&&Variant==TEXT("laser"))
    {
        const FString OpticalPath=FString::Printf(TEXT("/Game/Weapons/TacticalDevices20260913/%s/laser/M_%s_laser_Body_OpticalV2"),*Family,*Family);
        if(auto* Optical=LoadObject<UMaterialInterface>(nullptr,*OpticalPath))
        {
            const int32 Slot=Body->GetMaterialIndex(TEXT("M_Tactical_laser"));
            if(Slot!=INDEX_NONE)Body->SetMaterial(Slot,Optical);
        }
    }
    if(!Pistol&&Variant==TEXT("flashlight"))
    {
        const FString MaterialPath=FString::Printf(TEXT("/Game/Weapons/TacticalDevices20260913/HunyuanV3/%s/flashlight/M_%s_flashlight_Body_MetalTail"),*Family,*Family);
        if(auto* MetalTail=LoadObject<UMaterialInterface>(nullptr,*MaterialPath))
        {
            const int32 Slot=Body->GetMaterialIndex(TEXT("M_Tactical_flashlight"));
            if(Slot!=INDEX_NONE)Body->SetMaterial(Slot,MetalTail);
        }
    }
    Body->SetRelativeTransform(Pistol?PistolTacticalMount(Rifle):FTransform(FQuat::Identity,FVector::ZeroVector,FVector(.01f)));
    Body->SetVisibility(Body->GetStaticMesh()!=nullptr);
    auto MakeEffect=[&](const TCHAR* Name,const TCHAR* Mesh,const TCHAR* Material)
    {
        auto* C=NewObject<UStaticMeshComponent>(GetOwner(),Name);
        C->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,Mesh));C->SetMaterial(0,LoadObject<UMaterialInterface>(nullptr,Material));
        C->SetCollisionEnabled(ECollisionEnabled::NoCollision);C->SetCastShadow(false);C->bReceivesDecals=false;C->SetVisibility(false);C->RegisterComponent();return C;
    };
    if(!Dot)Dot=MakeEffect(TEXT("TacticalLaserDot"),TEXT("/Engine/BasicShapes/Sphere"),TEXT("/Game/Weapons/TacticalDevices20260913/Effects/M_LaserDot"));
    if(!Beam)Beam=MakeEffect(TEXT("TacticalLaserBeam"),TEXT("/Engine/BasicShapes/Cylinder"),TEXT("/Game/Weapons/TacticalDevices20260913/Effects/M_LaserBeam"));
    if(!Light)
    {
        Light=NewObject<USpotLightComponent>(GetOwner(),TEXT("TacticalFlashlight"));
        Light->SetMobility(EComponentMobility::Movable);Light->SetIntensityUnits(ELightUnits::Lumens);Light->SetIntensity(850.f);
        Light->SetAttenuationRadius(4000.f);Light->SetInnerConeAngle(9.f);Light->SetOuterConeAngle(30.f);
        Light->SetSourceRadius(.6f);Light->SetSoftSourceRadius(.9f);
        Light->SetLightColor(FLinearColor(1.f,.97f,.91f));Light->SetCastShadows(true);Light->SetVisibility(false);Light->RegisterComponent();
    }
}
void UTacticalDeviceComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Function)
{
    Super::TickComponent(Delta,Type,Function);HideEffects();
    const auto* C=Cast<AFPSGAMECharacter>(GetOwner());
    // Preview and dropped-weapon rigs keep geometry, never illuminate the live world.
    if(!C||!C->GetController()||!C->IsLocallyControlled()||C->IsHidden()||!C->HasInventoryWeapon()||C->IsTraversing()||!Host||!Host->IsVisible()||!Body||!Body->IsVisible()||!Body->GetStaticMesh())return;
    if(auto* G=C->GetGameInstance()->GetSubsystem<UGunsmithSystem>();G&&G->IsOpen())return;
    if(!Body->DoesSocketExist(TEXT("Emitter"))||!Body->DoesSocketExist(TEXT("AimGuide")))return;
    const FVector Origin=Body->GetSocketLocation(TEXT("Emitter"));
    FVector Direction=(Body->GetSocketLocation(TEXT("AimGuide"))-Origin).GetSafeNormal();
    FCollisionQueryParams Params(SCENE_QUERY_STAT(TacticalDevice),true,C);FHitResult Hit;
    const FVector Eye=C->FirstPersonCamera->GetComponentLocation();
    // An emitter clipping through a wall must not light or lase the far side.
    if(GetWorld()->LineTraceSingleByChannel(Hit,Eye,Origin,ECC_Visibility,Params))return;
    if(Kind==TEXT("flashlight"))
    {
        // Soften the near-wall hotspot while preserving full output at range.
        FHitResult NearHit;
        float Brightness=850.f;
        if(GetWorld()->LineTraceSingleByChannel(NearHit,Origin,Origin+Direction*150.f,ECC_Visibility,Params))
        {
            if(NearHit.bStartPenetrating)return;
            const float Blend=FMath::SmoothStep(15.f,150.f,NearHit.Distance);
            Brightness=FMath::Lerp(85.f,850.f,Blend);
        }
        Light->SetIntensity(FMath::FInterpTo(Light->Intensity,Brightness,Delta,10.f));
        Light->SetWorldLocationAndRotation(Origin,Direction.Rotation());Light->SetVisibility(true);return;
    }
    constexpr float Range=8000.f;
    if(C->IsAiming()||C->WeaponADSFactor>.98f)
    {
        FVector Target=Eye+C->ComputeShotDirection()*Range;
        if(GetWorld()->LineTraceSingleByChannel(Hit,Eye,Target,ECC_Visibility,Params))Target=Hit.ImpactPoint;
        Direction=(Target-Origin).GetSafeNormal();
    }
    FVector End=Origin+Direction*Range;
    if(GetWorld()->LineTraceSingleByChannel(Hit,Origin,End,ECC_Visibility,Params))
    {
        End=Hit.ImpactPoint;
        const FVector Normal=Hit.ImpactNormal.GetSafeNormal();
        // A volumetric sphere can protrude through thin receivers or walls.
        // Keep the entire shallow spot on the struck side of the surface.
        const FVector Spot=End+Normal*.03f;
        FHitResult Occlusion;
        if(!Hit.bStartPenetrating&&FVector::DotProduct(Normal,Eye-End)>0.f&&
            !GetWorld()->LineTraceSingleByChannel(Occlusion,Eye,Spot,ECC_Visibility,Params))
        {
            Dot->SetWorldLocationAndRotation(Spot,FRotationMatrix::MakeFromZ(Normal).ToQuat());
            Dot->SetWorldScale3D(FVector(.016f,.016f,.0004f));
            Dot->SetVisibility(true);
        }
    }
    const float Length=FVector::Distance(Origin,End);
    if(Length>.1f)
    {
        Beam->SetWorldLocationAndRotation((Origin+End)*.5f,FRotationMatrix::MakeFromZ(End-Origin).ToQuat());
        Beam->SetWorldScale3D(FVector(.004f,.004f,Length/100.f));Beam->SetVisibility(true);
    }
}
void UTacticalDeviceComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    HideEffects();
    for(auto* C:{Body.Get(),Dot.Get(),Beam.Get()})if(C)C->DestroyComponent();
    if(Light)Light->DestroyComponent();
    Super::EndPlay(Reason);
}
void AFPSGAMECharacter::SetGunsmithTactical(const FString& Variant)
{
    if(!TacticalDevice)
    {
        if(Variant!=TEXT("laser")&&Variant!=TEXT("flashlight"))return;
        TacticalDevice=NewObject<UTacticalDeviceComponent>(this,TEXT("TacticalDevice"));TacticalDevice->RegisterComponent();
    }
    const FString Family=bUseDanWesson715?TEXT("DanWesson715"):bUseM1911?TEXT("M1911"):bUseQBZ191?TEXT("QBZ191"):AKMSoviet::Matches(AKMViewmodel)?TEXT("AKM"):TEXT("M4");
    TacticalDevice->Configure(Family,Variant,AKMViewmodel,bInventoryWeaponReady);
}
