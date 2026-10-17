#include "TacticalDeviceComponent.h"
#include "TacticalDeviceVariants.h"
#include "HK416WeaponAssets.h"
#include "HK416Attachments.h"
#include "G18WeaponAssets.h"
#include "PitViper2011WeaponAssets.h"
#include "LMG201Attachments.h"
#include "A762Attachments.h"
#include "SVDAttachments.h"
#include "PKMAttachments.h"
#include "../FPSGAMECharacter.h"
#include "PistolDualWieldComponent.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "M16Attachments.h"
#include "AKMSovietCalibration.h"
#include "GunsmithSystem.h"
#include "DanWesson715WeaponAssets.h"
#include "RSH12TacticalAssets.h"
#include "Engine/GameInstance.h"
#include "GameFramework/PlayerController.h"
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
FTransform ASH12TacticalMount(const USkeletalMeshComponent* Mesh,bool OppositeSide)
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
    const FQuat SideRotation=OppositeSide?Rotation:Rotation*FQuat(FVector::ForwardVector,PI);
    const FTransform Mount(SideRotation,Rear.GetLocation()+Rotation.RotateVector(FVector(29.5f,OppositeSide?3.19f:-3.19f,-8.25f)));
    return Mount.GetRelativeTransform(Root);
}

FTransform Super90TacticalMount(const USkeletalMeshComponent* Mesh)
{
    const auto& Ref=Mesh->GetSkeletalMeshAsset()->GetRefSkeleton();
    FTransform Root=FTransform::Identity;
    for(int32 I=Ref.FindBoneIndex(TEXT("WPN_root"));I!=INDEX_NONE;I=Ref.GetParentIndex(I))Root=Root*Ref.GetRefBonePose()[I];
    const FQuat Forward=FRotationMatrix::MakeFromXZ(FVector(0,-1,0),FVector::UpVector).ToQuat();
    // Canonical underside assembly: +X follows the barrel, +Z faces the host.
    // The fitted bearing sits ahead of the foregrip; source emitter is the origin.
    const FTransform Seat(Forward,FVector(0,-32.f,-84.f));
    return Seat.GetRelativeTransform(Root);
}

FTransform OppositeTacticalMount(const FString& Family,const FTransform& Original)
{
    // Centimetres in each fitted mesh's authored frame. Pivots use paired host
    // surfaces, not an assumed origin or a negative mesh scale.
    // Source: SourceAssets/DualTactical20261008/authoring.json.
    FVector Pivot(-.015049f,0,7.799936f);
    if(Family==TEXT("AKM"))Pivot=FVector(.080003f,0,5.699731f);
    else if(Family==TEXT("QBZ191"))Pivot=FVector(.084883f,0,6.999806f);
    else if(Family==TEXT("M16"))Pivot=FVector(-.003821f,0,9.154936f);
    else if(Family==TEXT("A762"))Pivot=FVector(.056531f,0,6.199731f);
    else if(Family==TEXT("SVD"))Pivot=FVector(.003636f,0,5.699731f);
    else if(Family==TEXT("PKM"))Pivot=FVector(-.003824f,0,6.985000f);
    else if(Family==TEXT("LMG201"))Pivot=FVector(.080003f,0,4.585000f);
    else if(Family==TEXT("HK416"))Pivot=FVector(5.025823f,0,-.547877f);
    const FQuat Turn(FVector::RightVector,PI);
    return FTransform(Turn,Pivot-Turn.RotateVector(Pivot))*Original;
}

FTransform PistolTacticalMount(const USkeletalMeshComponent* Mesh, bool CanonicalForward)
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
    const FQuat SourceFrame=CanonicalForward?FQuat::Identity:FRotationMatrix::MakeFromXZ(FVector::RightVector,FVector::UpVector).ToQuat();
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
 * 此轴用于手电与非射击姿态；准备就绪的镭射另行向真实瞄准落点归零。
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
    bLaserSampleValid=false;
    ResetLaserAim();
    if(Dot)Dot->SetVisibility(false);
    if(Beam)Beam->SetVisibility(false);
    if(Light)Light->SetVisibility(false);
}
void UTacticalDeviceComponent::ResetLaserAim()
{
    LaserAimBlend=0.f;
}
void UTacticalDeviceComponent::SetPresentationHidden(bool Hidden)
{
    bPresentationHidden=Hidden;if(Body)Body->SetVisibility(!Hidden && IsComponentTickEnabled());if(Hidden)HideEffects();
}
bool UTacticalDeviceComponent::DescribePart(const UStaticMeshComponent* Part,FName& Variant,bool& bAuthoredAxis) const
{
    if(bWorldPresentation||Part!=Body||!IsComponentTickEnabled())return false;
    Variant=FName(*Kind);bAuthoredAxis=bUseAuthoredEmitterAxis;return true;
}
bool UTacticalDeviceComponent::ReadLaserSample(FFPSBodyLaserSample& Out) const
{
    if(bWorldPresentation||!bLaserSampleValid||!IsComponentTickEnabled()
        ||!GetWorld()||GetWorld()->GetTimeSeconds()-LaserSampleAt>.15)return false;
    Out.End=LaserSampleEnd;Out.Normal=LaserSampleNormal;Out.bDot=bLaserSampleDot;return true;
}
void UTacticalDeviceComponent::ConfigureWorld(const FString& Variant,USkeletalMeshComponent* Rifle,UStaticMeshComponent* Device,
    bool bAuthoredAxis,uint8 RigIndex,uint8 PartIndex,uint32 Schema)
{
    HideEffects();bWorldPresentation=true;Body=Device;Host=Rifle;Kind=Variant;
    bUseAuthoredEmitterAxis=bAuthoredAxis;WorldRigIndex=RigIndex;WorldPartIndex=PartIndex;WorldSchema=Schema;
    const bool Active=Rifle&&Device&&Device->GetStaticMesh();SetComponentTickEnabled(Active);
    if(!Active)return;
    // The world manifest already owns the correct mesh, fit and visibility.
    // Configure effects only; never replace it with a Super90 attachment.
    if(auto* WorldBody=GetOwner()->FindComponentByClass<UFPSPlayerBodyComponent>())
    {
        AddTickPrerequisiteComponent(WorldBody);
        if(auto* WorldMesh=WorldBody->GetBodyMesh())AddTickPrerequisiteComponent(WorldMesh);
    }
    AddTickPrerequisiteComponent(Rifle);
    InitializeEffects();
}
void UTacticalDeviceComponent::Configure(const FString& Family,const FString& RequestedVariant,USkeletalMeshComponent* Rifle,bool Enabled,bool OppositeSide)
{
    HideEffects();Kind=RequestedVariant;Host=Rifle;
    const FString Variant=TacticalDeviceVariants::MeshVariant(RequestedVariant);
    // A new attachment or weapon must not inherit the previous one's alignment.
    ResetLaserAim();
    // The world body publishes its posed weapon after the first-person rig.
    // Read the emitter only after that pose and its attached parts are current.
    if(auto* WorldBody=GetOwner()->FindComponentByClass<UFPSPlayerBodyComponent>())
    {
        AddTickPrerequisiteComponent(WorldBody);
        if(auto* WorldMesh=WorldBody->GetBodyMesh())AddTickPrerequisiteComponent(WorldMesh);
    }
    if(Body)Body->SetVisibility(false);
    const bool Active=Enabled&&Rifle&&Rifle->GetSkeletalMeshAsset()&&(Variant==TEXT("laser")||Variant==TEXT("flashlight"));
    SetComponentTickEnabled(Active);
    if(!Active)return;
    const bool RSH=Family==TEXT("RSH12");
    // Super90's WPN_root up axis is not the gun's up axis. Projecting its sight
    // line onto that plane sends the hip beam down; the fitted sockets encode
    // the actual barrel axis and follow the same native root through all poses.
    bUseAuthoredEmitterAxis=RSH||Family==TEXT("Super90")||Family==TEXT("M870");
    const bool Revolver=Family==TEXT("DanWesson715");
    const bool PitViper=Family==TEXT("PitViper2011");
    const bool Pistol=Family==TEXT("M1911")||Family==TEXT("G18")||PitViper||Revolver||RSH;
    const bool ASH=Family==TEXT("ASH12");
    const bool Super90=Family==TEXT("Super90");
    const bool M870=Family==TEXT("M870");
    const FString Path=!Pistol?TacticalDeviceVariants::FittedMeshPath(Family,Kind,OppositeSide)
        :Kind==TacticalDeviceVariants::BlessedLaser?TacticalDeviceVariants::BlessedMeshPath(Family)
        :RSH?RSH12TacticalAssets::MeshPath(Variant):PitViper?PitViper2011WeaponAssets::AttachmentPath(Variant)
        :Family==TEXT("G18")?G18WeaponAssets::AttachmentPath(Variant):Revolver?DanWesson715WeaponAssets::AttachmentPath(Variant)
        :FString::Printf(TEXT("/Game/Weapons/M1911/CompactFit20260913/%s/SM_TacticalDevice"),*Variant);
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
    if(!Super90&&!M870&&Kind!=TacticalDeviceVariants::BlessedLaser&&Family!=TEXT("HK416")&&!Pistol&&!ASH&&Family!=TEXT("LMG201")&&Family!=TEXT("SVD")&&Family!=TEXT("PKM")&&Family!=TEXT("A762")&&Family!=TEXT("M16")&&Variant==TEXT("laser"))
    {
        const FString OpticalPath=FString::Printf(TEXT("/Game/Weapons/TacticalDevices20260913/%s/laser/M_%s_laser_Body_OpticalV2"),*Family,*Family);
        if(auto* Optical=LoadObject<UMaterialInterface>(nullptr,*OpticalPath))
        {
            const int32 Slot=Body->GetMaterialIndex(TEXT("M_Tactical_laser"));
            if(Slot!=INDEX_NONE)Body->SetMaterial(Slot,Optical);
        }
    }
    if(!Super90&&!M870&&Family!=TEXT("HK416")&&!Pistol&&!ASH&&Family!=TEXT("LMG201")&&Family!=TEXT("SVD")&&Family!=TEXT("PKM")&&Family!=TEXT("A762")&&Family!=TEXT("M16")&&Variant==TEXT("flashlight"))
    {
        const FString MaterialPath=FString::Printf(TEXT("/Game/Weapons/TacticalDevices20260913/HunyuanV3/%s/flashlight/M_%s_flashlight_Body_MetalTail"),*Family,*Family);
        if(auto* MetalTail=LoadObject<UMaterialInterface>(nullptr,*MaterialPath))
        {
            const int32 Slot=Body->GetMaterialIndex(TEXT("M_Tactical_flashlight"));
            if(Slot!=INDEX_NONE)Body->SetMaterial(Slot,MetalTail);
        }
    }
    // Reused components inherit the current host, including when leaving RSH.
    if(!bWorldPresentation)Body->AttachToComponent(Rifle,FAttachmentTransformRules::KeepRelativeTransform,TEXT("WPN_root"));
    Body->SetOnlyOwnerSee(Rifle->bOnlyOwnerSee);
    Body->SetFirstPersonPrimitiveType(Rifle->FirstPersonPrimitiveType);
    FTransform Mount=M870?M870TacticalAssets::Mount(Rifle):Super90?Super90TacticalMount(Rifle):RSH?RSH12TacticalAssets::Mount():Family==TEXT("HK416")?HK416Attachments::ReferenceMount(Rifle):ASH?ASH12TacticalMount(Rifle,OppositeSide):Pistol?PistolTacticalMount(Rifle,PitViper):FTransform(FQuat::Identity,FVector::ZeroVector,FVector(.01f));
    if(OppositeSide&&!ASH&&!Pistol&&!Super90&&!M870)Mount=OppositeTacticalMount(Family,Mount);
    if(!bWorldPresentation)Body->SetRelativeTransform(Mount);
    Body->SetVisibility(!bPresentationHidden&&Body->GetStaticMesh()!=nullptr);
    InitializeEffects();
}
void UTacticalDeviceComponent::InitializeEffects()
{
    auto MakeEffect=[&](const TCHAR* Name,const TCHAR* Mesh,const TCHAR* Material)
    {
        auto* C=NewObject<UStaticMeshComponent>(GetOwner());
        C->SetMobility(EComponentMobility::Movable);
        C->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,Mesh));C->SetMaterial(0,LoadObject<UMaterialInterface>(nullptr,Material));
        // These tiny projected effects should not seed cached indirect lighting.
        C->SetAffectDynamicIndirectLighting(false);C->SetAffectDistanceFieldLighting(false);
        C->SetCollisionEnabled(ECollisionEnabled::NoCollision);C->SetCastShadow(false);C->bReceivesDecals=false;C->SetVisibility(false);C->RegisterComponent();return C;
    };
    if(!Dot)Dot=MakeEffect(TEXT("TacticalLaserDot"),TEXT("/Engine/BasicShapes/Sphere"),TEXT("/Game/Weapons/ScopeOptics20260927/M_ScopeAwareLaserDot"));
    if(!Beam)Beam=MakeEffect(TEXT("TacticalLaserBeam"),TEXT("/Engine/BasicShapes/Cylinder"),TEXT("/Game/Weapons/ScopeOptics20260927/M_ScopeAwareLaserBeam"));
    // Shared, immutable materials; cache per component instead of loading or
    // creating material instances during Tick. Swapping back restores red.
    if(Kind==TacticalDeviceVariants::BlessedLaser)
    {
        if(!BlessedDotMaterial)BlessedDotMaterial=LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/Weapons/TacticalDevices20260913/BlessedLaser20261006/M_BlessedLaserDot"));
        if(!BlessedBeamMaterial)BlessedBeamMaterial=LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/Weapons/TacticalDevices20260913/BlessedLaser20261006/M_BlessedLaserBeam"));
        Dot->SetMaterial(0,BlessedDotMaterial);Beam->SetMaterial(0,BlessedBeamMaterial);
    }
    else
    {
        if(!RedDotMaterial)RedDotMaterial=LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/Weapons/ScopeOptics20260927/M_ScopeAwareLaserDot"));
        if(!RedBeamMaterial)RedBeamMaterial=LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/Weapons/ScopeOptics20260927/M_ScopeAwareLaserBeam"));
        Dot->SetMaterial(0,RedDotMaterial);Beam->SetMaterial(0,RedBeamMaterial);
    }
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
    Super::TickComponent(Delta,Type,Function);
    // Keep visible primitives registered between frames so their previous
    // transforms survive for velocity/temporal reconstruction. Visibility is
    // resolved once below, or cleared immediately by an inactive/occluded path.
    if(bPresentationHidden){HideEffects();return;}
    const auto* C=Cast<AFPSGAMECharacter>(GetOwner());
    // Preview and dropped-weapon rigs keep geometry, never illuminate the live world.
    if(!C||C->IsHidden()||!Host||!Host->IsVisible()||Host->bHiddenInGame||!Body||!Body->IsVisible()||Body->bHiddenInGame||!Body->GetStaticMesh()){HideEffects();return;}
    if(!bWorldPresentation&&(!C->GetController()||!C->FirstPersonCamera||!C->IsLocallyControlled()||(!C->HasInventoryWeapon()&&!C->HasOffhandPistol())||C->IsTraversing())){HideEffects();return;}
    if(!bWorldPresentation)if(auto* G=C->GetGameInstance()->GetSubsystem<UGunsmithSystem>();G&&G->IsOpen()){HideEffects();return;}
    USkeletalMeshComponent* VisibleHost=Host;
    UStaticMeshComponent* VisibleDevice=Body;
    const auto* WorldBody=C->FindComponentByClass<UFPSPlayerBodyComponent>();
    const bool ThirdPerson=bWorldPresentation||(WorldBody&&WorldBody->IsThirdPersonViewEnabled());
    if(ThirdPerson&&!bWorldPresentation&&!WorldBody->ResolveWorldWeaponPart(Host,Body,VisibleHost,VisibleDevice))
    {HideEffects();return;}
    if(ThirdPerson)VisibleHost->UpdateChildTransforms();
    if(!VisibleDevice->DoesSocketExist(TEXT("Emitter"))){HideEffects();return;}
    const FVector RenderOrigin=VisibleDevice->GetSocketLocation(TEXT("Emitter"));
    // F6 changes only the visible emitter, not the gameplay ray or shared dot.
    const bool NativeRay=!bWorldPresentation&&TacticalDeviceVariants::IsLaser(Kind);
    auto* RayDevice=NativeRay?Body.Get():VisibleDevice;
    auto* RayHost=NativeRay?Host.Get():VisibleHost;
    const FVector Origin=RayDevice->GetSocketLocation(TEXT("Emitter"));
    // Direction comes from the weapon's own sight axis; the mesh sockets only
    // supply the emitter position the player sees. See WeaponForwardAxis above.
    FVector LocalForward;
    FVector Direction;
    if(bUseAuthoredEmitterAxis && RayDevice->DoesSocketExist(TEXT("AimGuide")))
        Direction=(RayDevice->GetSocketLocation(TEXT("AimGuide"))-Origin).GetSafeNormal();
    else if(WeaponForwardAxis(RayHost,LocalForward))
        Direction=RayHost->GetSocketRotation(TEXT("WPN_root")).RotateVector(LocalForward);
    else if(RayDevice->DoesSocketExist(TEXT("AimGuide")))
        Direction=(RayDevice->GetSocketLocation(TEXT("AimGuide"))-Origin).GetSafeNormal();
    else
        {HideEffects();return;}
    FCollisionQueryParams Params(SCENE_QUERY_STAT(TacticalDevice),true,C);FHitResult Hit;
    FVector Eye=bWorldPresentation?C->GetPawnViewLocation():C->FirstPersonCamera->GetComponentLocation();
    // An emitter clipping through a wall must not light or lase the far side.
    if((!bWorldPresentation||Kind==TEXT("flashlight"))
        &&GetWorld()->LineTraceSingleByChannel(Hit,Eye,Origin,ECC_Visibility,Params)){HideEffects();return;}
    if(Kind==TEXT("flashlight"))
    {
        Dot->SetVisibility(false);Beam->SetVisibility(false);
        // Soften the near-wall hotspot while preserving full output at range.
        FHitResult NearHit;
        float Brightness=850.f;
        if(GetWorld()->LineTraceSingleByChannel(NearHit,Origin,Origin+Direction*150.f,ECC_Visibility,Params))
        {
            if(NearHit.bStartPenetrating){HideEffects();return;}
            const float Blend=FMath::SmoothStep(15.f,150.f,NearHit.Distance);
            Brightness=FMath::Lerp(85.f,850.f,Blend);
        }
        Light->SetIntensity(FMath::FInterpTo(Light->Intensity,Brightness,Delta,10.f));
        Light->SetWorldLocationAndRotation(Origin,Direction.Rotation());Light->SetVisibility(true);return;
    }
    Light->SetVisibility(false);
    constexpr float Range=8000.f;
    // The beam and surface spot are independent world primitives, so hiding
    // the viewmodel for LPVO/PSO does not hide them. Fade the near-eye beam out
    // with the actual optical overlay and reduce spot emission before bloom.
    // Primitive data is instance-local; the shared material and hipfire
    // appearance remain unchanged. No new trace or per-frame material load.
    const auto* PC=Cast<APlayerController>(C->GetController());
    const float ScopeAlpha=!ThirdPerson&&PC&&!PC->bShowMouseCursor?C->GetScopePresentationAlpha():0.f;
    Dot->SetCustomPrimitiveDataFloat(0,ScopeAlpha);
    Beam->SetCustomPrimitiveDataFloat(0,ScopeAlpha);
    // Hip lasers zero to the same deterministic centre as the reticle and
    // projectile spread. Never call ComputeShotDirection here: hip shots sample
    // randomness, which would make a supposedly steady laser wander every tick.
    // Observers reuse the owner's final endpoint (including physical occlusion),
    // indexed by the replicated equipment manifest, instead of tracing a new aim.
    FFPSBodyLaserSample WorldSample;
    if(bWorldPresentation&&(!WorldBody||!WorldBody->ResolveLaserSample(WorldRigIndex,WorldPartIndex,WorldSchema,WorldSample)))
    {HideEffects();return;}
    const bool ContinuousPistolAim=!C->HasOffhandPistol()&&C->IsPistolWeapon();
    bool Ready=!bWorldPresentation&&!C->IsSprinting()&&!C->IsDodging()
        &&!C->IsDoorPushActive()&&C->NearWallAlpha<.01f;
    if(Ready&&C->HasOffhandPistol())
    {
        // A reloading left gun must not disable the independently firing right
        // gun's laser (or a staff's independently usable pistol).
        Ready=false;
        for(int32 Side=C->DualPistols->IsOffhandOnly()?1:0;Side<2;++Side)
        {
            const auto& Hand=C->DualPistols->Hand(Side);
            if(Hand.Mesh!=Host)continue;
            const bool Firing=Hand.Action&&(Hand.Action==Hand.Clips.FindRef(TEXT("fire"))
                ||Hand.Action==Hand.Clips.FindRef(TEXT("fire_last")));
            Ready=!Hand.Reloading&&Hand.Sprint<.01f&&(!Hand.Action||Firing)
                &&(Side!=1||!C->IsCastBlockingLeftHandAction());
            break;
        }
    }
    else if(Ready)
    {
        const bool HipReady=!C->IsAiming()&&C->WeaponADSFactor<.001f;
        const bool ADSReady=C->WeaponADSFactor>=ADSSettleThreshold;
        // A single pistol is still ready while being raised/lowered. Releasing
        // zero here made its beam sweep to the barrel and then back to the sight.
        // Retain the rifles' deliberately delayed ADS convergence.
        Ready=C->GetWeaponState()==EAKMWeaponState::Idle&&!C->IsWeaponBusy()
            &&FMath::SmoothStep(0.f,1.f,C->SprintPoseFactor)<.01f
            &&(ContinuousPistolAim||HipReady||ADSReady);
    }
    LaserAimBlend=LaserConvergeSeconds>KINDA_SMALL_NUMBER
        ?FMath::FInterpConstantTo(LaserAimBlend,Ready?1.f:0.f,Delta,1.f/LaserConvergeSeconds)
        :(Ready?1.f:0.f);
    if(LaserAimBlend>0.f&&TacticalDeviceVariants::IsLaser(Kind))
    {
        FVector Sight;
        if(ContinuousPistolAim)
        {
            const FVector Forward=C->FirstPersonCamera->GetForwardVector();
            FVector ADSSight=Forward;
            if(C->bHolographicOptic)
                ADSSight=(C->HolographicAimPoint()-Eye).GetSafeNormal();
            else if(Host->DoesSocketExist(TEXT("WPN_FrontSight")))
                ADSSight=(Host->GetSocketLocation(TEXT("WPN_FrontSight"))-Eye).GetSafeNormal();
            // Keep the hip centre during the initial lift, then smoothly pick up
            // the actual sight as it arrives. The pose clock works in both
            // directions, including reversing ADS midway; input state does not.
            // At full ADS, retain the same sight/recoil direction as the shot.
            const float SightWeight=FMath::SmoothStep(.65f,1.f,C->WeaponADSFactor)
                *(1.f-C->GetScopePresentationAlpha());
            Sight=FMath::Lerp(Forward,ADSSight,SightWeight).GetSafeNormal();
        }
        else Sight=C->ComputeWeaponAimDirection();
        FVector Target=Eye+Sight*Range;
        if(GetWorld()->LineTraceSingleByChannel(Hit,Eye,Target,ECC_Visibility,Params))Target=Hit.ImpactPoint;
        const FVector ToTarget=Target-Origin;
        // A close surface behind the emitter cannot be reached by bending the
        // beam backwards. The physical emitter ray/occlusion below stays active.
        if(FVector::DotProduct(ToTarget,Sight)>1.f)
        {
            const float Blend=LaserAimBlend*LaserAimBlend*(3.f-2.f*LaserAimBlend);
            Direction=FMath::Lerp(Direction,ToTarget.GetSafeNormal(),Blend).GetSafeNormal();
        }
    }
    bool bShowDot=false;
    FVector Normal=FVector::UpVector;
    FVector End=Origin+Direction*Range;
    if(bWorldPresentation)
    {
        End=WorldSample.End;Normal=WorldSample.Normal;bShowDot=WorldSample.bDot;
    }
    else if(GetWorld()->LineTraceSingleByChannel(Hit,Origin,End,ECC_Visibility,Params))
    {
        End=Hit.ImpactPoint;
        Normal=Hit.ImpactNormal.GetSafeNormal();
        // A volumetric sphere can protrude through thin receivers or walls.
        // Keep the entire shallow spot on the struck side of the surface.
        const FVector Spot=End+Normal*.03f;
        FHitResult Occlusion;
        bShowDot=!Hit.bStartPenetrating&&FVector::DotProduct(Normal,Eye-End)>0.f&&
            !GetWorld()->LineTraceSingleByChannel(Occlusion,Eye,Spot,ECC_Visibility,Params);
    }
    if(bShowDot)
    {
        const FVector Spot=End+Normal*.03f;
        float Diameter=1.6f;
        if(ScopeAlpha>0.f)
        {
            // Keep the real hit, parallax and depth test. Only cap its
            // visual diameter (0.3% of view height, about 3.2 px at 1080p)
            // so a close surface at 6x cannot cover the etched reticle.
            // Use this frame's camera FOV, including smooth zoom/recoil.
            const float Depth=FVector::DotProduct(Spot-Eye,C->FirstPersonCamera->GetForwardVector());
            if(Depth<=0.f){HideEffects();return;}
            const float TanHalfVFOV=FMath::Tan(FMath::DegreesToRadians(C->FirstPersonCamera->FieldOfView)*.5f)
                /FMath::Max(.01f,C->FirstPersonCamera->AspectRatio);
            const float CappedDiameter=FMath::Min(Diameter,2.f*Depth*TanHalfVFOV*.003f);
            Diameter=FMath::Lerp(Diameter,CappedDiameter,ScopeAlpha);
        }
        Dot->SetWorldTransform(FTransform(FRotationMatrix::MakeFromZ(Normal).ToQuat(),Spot,
            FVector(Diameter/100.f,Diameter/100.f,FMath::Min(.0004f,Diameter/100.f))));
    }
    Dot->SetVisibility(bShowDot);
    if(!bWorldPresentation)
    {
        bLaserSampleValid=true;LaserSampleAt=GetWorld()->GetTimeSeconds();
        LaserSampleEnd=End;LaserSampleNormal=Normal;bLaserSampleDot=bShowDot;
    }
    // Clip a differently positioned world/F6 beam at its own obstruction, but
    // never replace the shared surface spot with a second observer-only hit.
    FVector BeamEnd=End;
    if((bWorldPresentation||(NativeRay&&ThirdPerson))
        &&GetWorld()->LineTraceSingleByChannel(Hit,RenderOrigin,End,ECC_Visibility,Params))BeamEnd=Hit.ImpactPoint;
    const float Length=FVector::Distance(RenderOrigin,BeamEnd);
    const bool bShowBeam=Length>.1f&&ScopeAlpha<1.f;
    if(bShowBeam)
    {
        // Physical centimetres keep the subtle flowing threads the same size
        // as the ray shortens at walls; GPU time drives motion without CPU particles.
        if(Kind==TacticalDeviceVariants::BlessedLaser)Beam->SetCustomPrimitiveDataFloat(1,Length);
        Beam->SetWorldTransform(FTransform(FRotationMatrix::MakeFromZ(BeamEnd-RenderOrigin).ToQuat(),(RenderOrigin+BeamEnd)*.5f,
            FVector(.004f,.004f,Length/100.f)));
    }
    Beam->SetVisibility(bShowBeam);
}
void UTacticalDeviceComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    HideEffects();
    if(!bWorldPresentation&&Body)Body->DestroyComponent();
    for(auto* C:{Dot.Get(),Beam.Get()})if(C)C->DestroyComponent();
    if(Light)Light->DestroyComponent();
    Super::EndPlay(Reason);
}
void AFPSGAMECharacter::SetGunsmithTactical(const FString& Variant,const FString& SecondaryVariant)
{
    const FString Secondary=TacticalDeviceVariants::SupportsSecondary(ActiveInventoryWeaponDefinition)?SecondaryVariant:FString();
    const FString Family=IsM870Weapon()?TEXT("M870"):IsSuper90Weapon()?TEXT("Super90"):IsRSH12Weapon()?TEXT("RSH12"):IsHK416Weapon()?TEXT("HK416"):IsPitViperWeapon()?TEXT("PitViper2011"):IsG18Weapon()?TEXT("G18"):LMG201WeaponAssets::Matches(AKMViewmodel)?TEXT("LMG201"):SVDWeaponAssets::Matches(AKMViewmodel)?TEXT("SVD"):PKMLowpolyWeaponAssets::Matches(AKMViewmodel)?TEXT("PKM"):A762WeaponAssets::Matches(AKMViewmodel)?TEXT("A762"):bUseM16?TEXT("M16"):bUseASH12?TEXT("ASH12"):bUseDanWesson715?TEXT("DanWesson715"):bUseM1911?TEXT("M1911"):bUseQBZ191?TEXT("QBZ191"):AKMSoviet::Matches(AKMViewmodel)?TEXT("AKM"):TEXT("M4");
    auto ConfigureSlot=[&](TObjectPtr<UTacticalDeviceComponent>& Device,const FString& Id,bool Opposite)
    {
        if(!Device)
        {
            if(!TacticalDeviceVariants::IsLaser(Id)&&Id!=TEXT("flashlight"))return;
            Device=NewObject<UTacticalDeviceComponent>(this,Opposite?TEXT("SecondaryTacticalDevice"):TEXT("TacticalDevice"));
            Device->RegisterComponent();
        }
        // Each installed device emits independently. Laser priority only affects
        // the numeric modifiers resolved by UGunsmithSystem::Calculate.
        Device->Configure(Family,Id,AKMViewmodel,bInventoryWeaponReady,Opposite);
    };
    ConfigureSlot(TacticalDevice,Variant,false);
    ConfigureSlot(SecondaryTacticalDevice,Secondary,true);
}
