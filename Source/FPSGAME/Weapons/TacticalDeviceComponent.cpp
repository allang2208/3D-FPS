#include "TacticalDeviceComponent.h"
#include "A762Attachments.h"
#include "SVDAttachments.h"
#include "PKMAttachments.h"
#include "../FPSGAMECharacter.h"
#include "M16Attachments.h"
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
FTransform ASH12TacticalMount(const USkeletalMeshComponent* Mesh)
{
    const auto& Ref=Mesh->GetSkeletalMeshAsset()->GetRefSkeleton();
    auto Bone=[&Ref](const TCHAR* Name)
    {
        FTransform Pose=FTransform::Identity;
        for(int32 I=Ref.FindBoneIndex(Name);I!=INDEX_NONE;I=Ref.GetParentIndex(I))
            Pose=Pose*Ref.GetRefBonePose()[I];
        return Pose;
    };
    const FTransform Root=Bone(TEXT("WPN_root")),Rear=Bone(TEXT("WPN_RearSight"));
    const FVector Forward=(Bone(TEXT("WPN_FrontSight")).GetLocation()-Rear.GetLocation()).GetSafeNormal();
    const FQuat Rotation=FRotationMatrix::MakeFromXZ(Forward,Rear.GetRotation().GetAxisZ()).ToQuat();
    // Local mesh is centimetres, +X forward, +Y outboard. Rotate around the
    // barrel to put the existing clamp on the left rail without mirroring or
    // scaling the body. The location is measured in the upright sight frame.
    const FQuat LeftSideRotation=Rotation*FQuat(FVector::ForwardVector,PI);
    const FTransform Mount(LeftSideRotation,Rear.GetLocation()+Rotation.RotateVector(FVector(29.5f,-3.19f,-8.25f)));
    return Mount.GetRelativeTransform(Root);
}

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

/**
 * 光束方向：取武器自身的瞄具轴线，而不是战术件网格的 Emitter->AimGuide 插座。
 *
 * 实测（见 SourceAssets/PKMLowpolyLaserBug20260922）：步枪族 TacticalDevices20260913 的
 * 两个插座沿武器本地 +Y（横向）排布，而枪管是 +X，于是 Emitter->AimGuide 给出的是与枪管
 * 垂直的方向。ASH 文档要求"Emitter / AimGuide 沿枪口前向"，ASH 自己又额外旋转了挂载网格，
 * 所以插座方向与网格旋转互相耦合、各家不一致。
 * 改用前/后瞄具轴线后，方向与 ComputeShotDirection/瞄具标定同一权威，
 * 腰射与开镜都沿枪管，不再依赖各网格的插座约定。
 */
bool WeaponForwardAxis(const USkeletalMeshComponent* Mesh,FVector& OutRootForward)
{
    if(!Mesh||!Mesh->GetSkeletalMeshAsset())return false;
    const auto& Ref=Mesh->GetSkeletalMeshAsset()->GetRefSkeleton();
    if(Ref.FindBoneIndex(TEXT("WPN_FrontSight"))==INDEX_NONE)return false;
    if(Ref.FindBoneIndex(TEXT("WPN_RearSight"))==INDEX_NONE)return false;
    USkeletalMeshComponent* Mutable=const_cast<USkeletalMeshComponent*>(Mesh);
    const FVector Front=Mutable->GetSocketLocation(TEXT("WPN_FrontSight"));
    const FVector Rear=Mutable->GetSocketLocation(TEXT("WPN_RearSight"));
    // FRotator has no axis accessors; go through the quaternion.
    const FQuat Root=Mutable->GetSocketRotation(TEXT("WPN_root")).Quaternion();
    const FVector Axis=FVector::VectorPlaneProject(Front-Rear,Root.GetUpVector());
    if(Axis.IsNearlyZero())return false;
    // Report in the weapon root's own frame; the caller rotates it to world space
    // with that bone's socket rotation.
    OutRootForward=Root.Inverse().RotateVector(Axis.GetSafeNormal());
    return true;
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
void UTacticalDeviceComponent::ResetLaserAim()
{
    bLaserSettled=false;
    LaserSettleElapsed=0.f;
}
void UTacticalDeviceComponent::SetPresentationHidden(bool Hidden)
{
    bPresentationHidden=Hidden;if(Body)Body->SetVisibility(!Hidden && IsComponentTickEnabled());if(Hidden)HideEffects();
}
void UTacticalDeviceComponent::Configure(const FString& Family,const FString& Variant,USkeletalMeshComponent* Rifle,bool Enabled)
{
    HideEffects();Kind=Variant;Host=Rifle;
    // A new attachment or weapon must not inherit the previous one's alignment.
    ResetLaserAim();
    if(Body)Body->SetVisibility(false);
    const bool Active=Enabled&&Rifle&&(Variant==TEXT("laser")||Variant==TEXT("flashlight"));
    SetComponentTickEnabled(Active);
    if(!Active)return;
    const bool Revolver=Family==TEXT("DanWesson715");
    const bool Pistol=Family==TEXT("M1911")||Revolver;
    const bool ASH=Family==TEXT("ASH12");
    const FString Path=Family==TEXT("SVD")?SVDAttachments::MeshPath(Variant):Family==TEXT("PKM")?PKMAttachments::MeshPath(Variant):Family==TEXT("A762")?A762Attachments::MeshPath(Variant):Family==TEXT("M16")?M16Attachments::MeshPath(Variant):ASH
        ?FString::Printf(TEXT("/Game/Weapons/ASH12/TacticalDevices20260920/%s/SM_ASH12_%s"),*Variant,*Variant)
        :Revolver?DanWesson715WeaponAssets::AttachmentPath(Variant):Pistol
        ?FString::Printf(TEXT("/Game/Weapons/M1911/CompactFit20260913/%s/SM_TacticalDevice"),*Variant)
        :Variant==TEXT("flashlight")
        ?FString::Printf(TEXT("/Game/Weapons/TacticalDevices20260913/HunyuanV3/%s/flashlight/SM_TacticalDevice"),*Family)
        :FString::Printf(TEXT("/Game/Weapons/TacticalDevices20260913/%s/%s/SM_TacticalDevice"),*Family,*Variant);
    if(!Body)
    {
        Body=NewObject<UStaticMeshComponent>(GetOwner());
        Body->SetCollisionEnabled(ECollisionEnabled::NoCollision);Body->SetCastShadow(false);Body->bReceivesDecals=false;
        Body->SetupAttachment(Rifle,TEXT("WPN_root"));Body->RegisterComponent();
        AddTickPrerequisiteComponent(Rifle);
    }
    if(AssetPath!=Path||!Body->GetStaticMesh())
    {
        Body->EmptyOverrideMaterials();
        Body->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,*Path));AssetPath=Path;
    }
    if(!Pistol&&!ASH&&Family!=TEXT("SVD")&&Family!=TEXT("PKM")&&Family!=TEXT("A762")&&Family!=TEXT("M16")&&Variant==TEXT("laser"))
    {
        const FString OpticalPath=FString::Printf(TEXT("/Game/Weapons/TacticalDevices20260913/%s/laser/M_%s_laser_Body_OpticalV2"),*Family,*Family);
        if(auto* Optical=LoadObject<UMaterialInterface>(nullptr,*OpticalPath))
        {
            const int32 Slot=Body->GetMaterialIndex(TEXT("M_Tactical_laser"));
            if(Slot!=INDEX_NONE)Body->SetMaterial(Slot,Optical);
        }
    }
    if(!Pistol&&!ASH&&Family!=TEXT("SVD")&&Family!=TEXT("PKM")&&Family!=TEXT("A762")&&Family!=TEXT("M16")&&Variant==TEXT("flashlight"))
    {
        const FString MaterialPath=FString::Printf(TEXT("/Game/Weapons/TacticalDevices20260913/HunyuanV3/%s/flashlight/M_%s_flashlight_Body_MetalTail"),*Family,*Family);
        if(auto* MetalTail=LoadObject<UMaterialInterface>(nullptr,*MaterialPath))
        {
            const int32 Slot=Body->GetMaterialIndex(TEXT("M_Tactical_flashlight"));
            if(Slot!=INDEX_NONE)Body->SetMaterial(Slot,MetalTail);
        }
    }
    Body->SetRelativeTransform(ASH?ASH12TacticalMount(Rifle):Pistol?PistolTacticalMount(Rifle):FTransform(FQuat::Identity,FVector::ZeroVector,FVector(.01f)));
    Body->SetVisibility(Body->GetStaticMesh()!=nullptr);
    auto MakeEffect=[&](const TCHAR* Name,const TCHAR* Mesh,const TCHAR* Material)
    {
        auto* C=NewObject<UStaticMeshComponent>(GetOwner());
        C->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,Mesh));C->SetMaterial(0,LoadObject<UMaterialInterface>(nullptr,Material));
        C->SetCollisionEnabled(ECollisionEnabled::NoCollision);C->SetCastShadow(false);C->bReceivesDecals=false;C->SetVisibility(false);C->RegisterComponent();return C;
    };
    if(!Dot)Dot=MakeEffect(TEXT("TacticalLaserDot"),TEXT("/Engine/BasicShapes/Sphere"),TEXT("/Game/Weapons/TacticalDevices20260913/Effects/M_LaserDot"));
    if(!Beam)Beam=MakeEffect(TEXT("TacticalLaserBeam"),TEXT("/Engine/BasicShapes/Cylinder"),TEXT("/Game/Weapons/TacticalDevices20260913/Effects/M_LaserBeam"));
    if(!Light)
    {
        Light=NewObject<USpotLightComponent>(GetOwner());
        Light->SetMobility(EComponentMobility::Movable);Light->SetIntensityUnits(ELightUnits::Lumens);Light->SetIntensity(850.f);
        Light->SetAttenuationRadius(4000.f);Light->SetInnerConeAngle(9.f);Light->SetOuterConeAngle(30.f);
        Light->SetSourceRadius(.6f);Light->SetSoftSourceRadius(.9f);
        Light->SetLightColor(FLinearColor(1.f,.97f,.91f));Light->SetCastShadows(true);Light->SetVisibility(false);Light->RegisterComponent();
    }
}
void UTacticalDeviceComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Function)
{
    Super::TickComponent(Delta,Type,Function);HideEffects();
    if(bPresentationHidden)return;
    const auto* C=Cast<AFPSGAMECharacter>(GetOwner());
    // Preview and dropped-weapon rigs keep geometry, never illuminate the live world.
    if(!C||!C->GetController()||!C->IsLocallyControlled()||C->IsHidden()||!C->HasInventoryWeapon()||C->IsTraversing()||!Host||!Host->IsVisible()||!Body||!Body->IsVisible()||!Body->GetStaticMesh())return;
    if(auto* G=C->GetGameInstance()->GetSubsystem<UGunsmithSystem>();G&&G->IsOpen())return;
    if(!Body->DoesSocketExist(TEXT("Emitter")))return;
    const FVector Origin=Body->GetSocketLocation(TEXT("Emitter"));
    // Direction comes from the weapon's own sight axis; the mesh sockets only
    // supply the emitter position the player sees. See WeaponForwardAxis above.
    FVector LocalForward;
    FVector Direction;
    if(WeaponForwardAxis(Host,LocalForward))
        Direction=Host->GetSocketRotation(TEXT("WPN_root")).RotateVector(LocalForward);
    else if(Body->DoesSocketExist(TEXT("AimGuide")))
        Direction=(Body->GetSocketLocation(TEXT("AimGuide"))-Origin).GetSafeNormal();
    else
        return;
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
    // Converge only once ADS has actually settled. bIsAiming is true from the
    // instant the aim input lands, but WeaponADSFactor needs the whole ADS
    // duration (0.45 s for PKM versus 0.24 s for M4), so keying off IsAiming
    // swung the beam onto the crosshair for the entire raise. During the raise
    // the beam stays on the barrel; afterwards it aligns inside a short window.
    // The blend is evaluated from the elapsed settle time, not accumulated per
    // frame: a repeated frame-to-frame lerp only approaches asymptotically and
    // would take about 0.28 s at 60 fps to land a nominal 0.08 s window.
    const bool bADSSettled = C->WeaponADSFactor >= ADSSettleThreshold;
    if(!bADSSettled)
    {
        bLaserSettled=false;
        LaserSettleElapsed=0.f;
    }
    else if(Kind==TEXT("laser"))
    {
        if(!bLaserSettled)
        {
            bLaserSettled=true;
            LaserSettleElapsed=0.f;
        }
        else LaserSettleElapsed+=Delta;
        FVector Target=Eye+C->ComputeShotDirection()*Range;
        if(GetWorld()->LineTraceSingleByChannel(Hit,Eye,Target,ECC_Visibility,Params))Target=Hit.ImpactPoint;
        const FVector AimDirection=(Target-Origin).GetSafeNormal();
        // Barrel is this frame's Direction; at t=0 the beam is untouched, and by
        // t=LaserConvergeSeconds it is exactly on the crosshair.
        const float Blend=LaserConvergeSeconds>KINDA_SMALL_NUMBER
            ? FMath::Clamp(LaserSettleElapsed/LaserConvergeSeconds,0.f,1.f) : 1.f;
        Direction=FMath::Lerp(Direction,AimDirection,Blend).GetSafeNormal();
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
    const FString Family=SVDWeaponAssets::Matches(AKMViewmodel)?TEXT("SVD"):PKMLowpolyWeaponAssets::Matches(AKMViewmodel)?TEXT("PKM"):A762WeaponAssets::Matches(AKMViewmodel)?TEXT("A762"):bUseM16?TEXT("M16"):bUseASH12?TEXT("ASH12"):bUseDanWesson715?TEXT("DanWesson715"):bUseM1911?TEXT("M1911"):bUseQBZ191?TEXT("QBZ191"):AKMSoviet::Matches(AKMViewmodel)?TEXT("AKM"):TEXT("M4");
    TacticalDevice->Configure(Family,Variant,AKMViewmodel,bInventoryWeaponReady);
}
