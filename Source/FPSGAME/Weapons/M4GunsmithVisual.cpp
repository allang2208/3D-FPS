#include "../FPSGAMECharacter.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "A762Attachments.h"
#include "SVDAttachments.h"
#include "PKMAttachments.h"
#include "PSO1AttachmentAssets.h"
#include "M16Attachments.h"
#include "A762WeaponAssets.h"
#include "AKMAttachmentVisual.h"
#include "ASH12WeaponAssets.h"
#include "QBZ191Attachments.h"
#include "M1911WeaponAssets.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshSocket.h"
#include "Engine/SkeletalMesh.h"
#include "Camera/CameraComponent.h"
#include "GameFramework/PlayerController.h"

void AFPSGAMECharacter::SetGunsmithOptic(bool bHolographic)
{
    SetGunsmithOpticVariant(bHolographic?TEXT("holographic"):TEXT("false"));
}
void AFPSGAMECharacter::SetGunsmithOpticVariant(const FString& Variant)
{
    const bool bSVD=SVDWeaponAssets::Matches(AKMViewmodel);
    if(bSVD)
    {
        const bool Modern=bInventoryWeaponReady&&(Variant==TEXT("holographic")||Variant==TEXT("panoramic_red_dot")||Variant==TEXT("prism_scope_2x")||Variant==TEXT("lpvo_1_6x"));
        SVDAttachments::FactorySections(AKMViewmodel,TEXT("Scope"),!Modern);
        AKMOpticBridge=SVDAttachments::Configure(this,AKMViewmodel,AKMOpticBridge,TEXT("optic_bridge"),Modern);
    }
    const bool bPKM=PKMLowpolyWeaponAssets::Matches(AKMViewmodel);
    PKMAttachments::ConfigureRail(this,AKMViewmodel,bInventoryWeaponReady&&(Variant==TEXT("holographic")||Variant==TEXT("panoramic_red_dot")||Variant==TEXT("prism_scope_2x")||Variant==TEXT("lpvo_1_6x")));
    if(Variant==PSO1AttachmentAssets::Variant)
    {
        if(!PSO1AttachmentAssets::Supports(ActiveInventoryWeaponDefinition))
        {
            SetGunsmithOpticVariant(TEXT("false"));return;
        }
        const bool Enabled=bInventoryWeaponReady;
        if(Enabled)
        {
            auto* PSOMesh=LoadObject<UStaticMesh>(nullptr,*PSO1AttachmentAssets::MeshPath(ActiveInventoryWeaponDefinition));
            if(!PSOMesh){UE_LOG(LogTemp,Error,TEXT("PSO1: missing fitted optic for %s"),*ActiveInventoryWeaponDefinition);return;}
            if(!HolographicOptic)
            {
                HolographicOptic=NewObject<UStaticMeshComponent>(this,TEXT("PSO1Optic"));
                HolographicOptic->SetupAttachment(AKMViewmodel,TEXT("WPN_root"));
                HolographicOptic->SetCollisionEnabled(ECollisionEnabled::NoCollision);
                HolographicOptic->SetCastShadow(false);HolographicOptic->bReceivesDecals=false;
                HolographicOptic->RegisterComponent();
            }
            HolographicOptic->EmptyOverrideMaterials();HolographicOptic->SetStaticMesh(PSOMesh);
            // PKM's side receiver interface stays on the receiver when its lid opens.
            HolographicOptic->AttachToComponent(AKMViewmodel,FAttachmentTransformRules::KeepRelativeTransform,TEXT("WPN_root"));
            HolographicMount=PSO1AttachmentAssets::Mount();
            HolographicOptic->SetRelativeTransform(HolographicMount);
        }
        if(AKMOpticBridge)AKMOpticBridge->SetVisibility(false);
        if(LPVORing)LPVORing->SetVisibility(false);
        if(bHolographicOptic!=Enabled||OpticVariant!=Variant)bSightCalibrated=false;
        bHolographicOptic=Enabled;OpticVariant=Enabled?Variant:FString();
        if(HolographicOptic)HolographicOptic->SetVisibility(Enabled);
        UpdateFoldingSights(0.f);return;
    }
    if (bUseDanWesson715) { SetDanWesson715Optic(Variant); return; }
    if (bUseM1911) { SetM1911Optic(Variant); return; }
    const bool LPVO=Variant==TEXT("lpvo_1_6x");
    const bool Panoramic=Variant==TEXT("panoramic_red_dot");
    const bool Scope2X=Variant==TEXT("prism_scope_2x");
    bool bHolographic=Variant==TEXT("holographic")||Panoramic||Scope2X||LPVO;
    if(LPVORing&&!LPVO)LPVORing->SetVisibility(false);
    if (bSVD || A762WeaponAssets::Matches(AKMViewmodel) || bPKM)
    {
        bHolographic=bHolographic&&bInventoryWeaponReady;
        if (bHolographic)
        {
            const TCHAR* Name=LPVO?TEXT("SM_LPVO1to6X"):Scope2X?TEXT("SM_PrismScope2X"):Panoramic?TEXT("SM_PanoramicRedDot"):TEXT("SM_M4_Holographic");
            auto* Optic=LoadObject<UStaticMesh>(nullptr,*(bSVD?SVDAttachments::MeshPath(Variant):bPKM?PKMAttachments::MeshPath(Variant):A762Attachments::MeshPath(Variant)));
            if (!Optic) return;
            if (!HolographicOptic)
            {
                HolographicOptic=NewObject<UStaticMeshComponent>(this,TEXT("A762Optic"));
                HolographicOptic->SetupAttachment(AKMViewmodel,bPKM?TEXT("PKM_Cover"):TEXT("WPN_root"));
                HolographicOptic->SetCollisionEnabled(ECollisionEnabled::NoCollision);HolographicOptic->SetCastShadow(false);HolographicOptic->bReceivesDecals=false;HolographicOptic->RegisterComponent();
            }
            HolographicOptic->EmptyOverrideMaterials();HolographicOptic->SetStaticMesh(Optic);
            HolographicMount=bSVD?SVDAttachments::OpticMount(Variant):bPKM?PKMAttachments::OpticMount(Variant):A762Attachments::OpticMount(Variant);
            HolographicOptic->AttachToComponent(AKMViewmodel,FAttachmentTransformRules::KeepRelativeTransform,bPKM?TEXT("PKM_Cover"):TEXT("WPN_root"));
            HolographicOptic->SetRelativeTransform(HolographicMount);
        }
        if (bHolographicOptic!=bHolographic || OpticVariant!=Variant) bSightCalibrated=false;
        if (OpticVariant!=Variant) LPVOMagnification=1.f;
        bHolographicOptic=bHolographic;OpticVariant=bHolographic?Variant:FString();
        if (HolographicOptic) HolographicOptic->SetVisibility(bHolographic);
        if (LPVO&&bHolographic)
        {
            auto* RingMesh=LoadObject<UStaticMesh>(nullptr,*(bSVD?SVDAttachments::MeshPath(TEXT("lpvo_ring")):bPKM?PKMAttachments::MeshPath(TEXT("lpvo_ring")):A762Attachments::MeshPath(TEXT("lpvo_ring"))));
            if (RingMesh)
            {
                if(!LPVORing)LPVORing=NewObject<UStaticMeshComponent>(this);LPVORing->EmptyOverrideMaterials();LPVORing->SetStaticMesh(RingMesh);LPVORing->SetCollisionEnabled(ECollisionEnabled::NoCollision);LPVORing->SetCastShadow(false);
                if(!LPVORing->IsRegistered()){LPVORing->SetupAttachment(HolographicOptic);LPVORing->RegisterComponent();}LPVORing->SetRelativeLocation(FVector(-7.1f,0,4.f));
            }
        }
        if (LPVORing){LPVORing->SetVisibility(LPVO&&bHolographic);LPVORing->SetRelativeRotation(FRotator(0,0,(LPVOMagnification-1.f)*24.f));}
        UpdateFoldingSights(0.f);return;
    }
    if(AKMSoviet::Matches(AKMViewmodel)){
        bHolographic=bHolographic&&bInventoryWeaponReady;
        const bool Modern=bHolographic&&(Panoramic||Scope2X||LPVO);
        if(Modern){
            const TCHAR* Path=LPVO?TEXT("/Game/Weapons/AKMIntegration/SovietFab/OpticSteel/SM_LPVO1to6X"):Scope2X?TEXT("/Game/Weapons/AKMIntegration/SovietFab/OpticSteel/SM_PrismScope2X"):TEXT("/Game/Weapons/AKMIntegration/SovietFab/OpticSteel/SM_PanoramicRedDot");
            auto* AKMOpticMesh=LoadObject<UStaticMesh>(nullptr,Path);
            auto* Bridge=LoadObject<UStaticMesh>(nullptr,*(TEXT("/Game/Weapons/AKMIntegration/SovietFab/Optics/SM_AKM_Mount_")+Variant));
            if(!AKMOpticMesh||!Bridge){UE_LOG(LogTemp,Error,TEXT("AKM_OPTIC missing model or bridge for %s"),*Variant);return;}
            auto MakePart=[&](UStaticMeshComponent* Part){if(!Part){Part=NewObject<UStaticMeshComponent>(this);Part->SetupAttachment(AKMViewmodel,TEXT("WPN_root"));Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);Part->SetCastShadow(false);Part->bReceivesDecals=false;Part->RegisterComponent();}return Part;};
            HolographicOptic=MakePart(HolographicOptic);HolographicOptic->EmptyOverrideMaterials();HolographicOptic->SetStaticMesh(AKMOpticMesh);
            HolographicMount=FTransform(FQuat(FVector::UpVector,PI*.5f),FVector(.0008f,LPVO?.16f:Scope2X?.105f:.06f,.113f),FVector(.01f));
            HolographicOptic->SetRelativeTransform(HolographicMount);
            AKMOpticBridge=MakePart(AKMOpticBridge);AKMOpticBridge->SetStaticMesh(Bridge);AKMOpticBridge->SetRelativeTransform(FTransform(FQuat::Identity,FVector::ZeroVector,FVector(.01f)));
        }else{
            HolographicOptic=AKMAttachment::Configure(this,AKMViewmodel,HolographicOptic,TEXT("optic"),bHolographic);
            HolographicMount=FTransform(FQuat::Identity,FVector::ZeroVector,FVector(.01f));
        }
        if(AKMOpticBridge)AKMOpticBridge->SetVisibility(Modern);
        if(bHolographicOptic!=bHolographic||OpticVariant!=Variant)bSightCalibrated=false;
        if(OpticVariant!=Variant)LPVOMagnification=1.f;
        bHolographicOptic=bHolographic;OpticVariant=bHolographic?Variant:FString();
        if(LPVO&&bHolographic&&!LPVORing){
            auto* RingMesh=LoadObject<UStaticMesh>(nullptr,TEXT("/Game/Weapons/AKMIntegration/SovietFab/OpticSteel/SM_LPVORing"));
            if(RingMesh){LPVORing=NewObject<UStaticMeshComponent>(this);LPVORing->SetStaticMesh(RingMesh);LPVORing->SetCollisionEnabled(ECollisionEnabled::NoCollision);LPVORing->SetCastShadow(false);LPVORing->SetupAttachment(HolographicOptic);LPVORing->RegisterComponent();LPVORing->SetRelativeLocation(FVector(-7.1f,0,4.f));}
        }
        if(LPVORing){LPVORing->SetVisibility(LPVO&&bHolographic);LPVORing->SetRelativeRotation(FRotator(0,0,(LPVOMagnification-1.f)*24.f));}
        if(HolographicOptic)HolographicOptic->SetVisibility(bHolographic);
        return;
    }
    bHolographic = bHolographic && bUsingM4Infima && bInventoryWeaponReady;
    if(bHolographic && (!HolographicOptic || OpticVariant!=Variant))
    {
        const TCHAR* MeshPath=LPVO?TEXT("/Game/Weapons/AttachmentFinish20260913/M4/Meshes/SM_LPVO1to6X"):Scope2X?TEXT("/Game/Weapons/AttachmentFinish20260913/M4/Meshes/SM_PrismScope2X"):(Panoramic?TEXT("/Game/Weapons/AttachmentFinish20260913/M4/Meshes/SM_PanoramicRedDot"):TEXT("/Game/Weapons/AttachmentFinish20260913/M4/Meshes/SM_M4_Holographic"));
        const FString SelectedMeshPath = bUseM16 ? M16Attachments::MeshPath(Variant) : bUseASH12 ? ASH12WeaponAssets::OpticMeshPath(Variant)
            : bUseQBZ191 ? QBZ191Attachments::MeshPath(Variant) : FString(MeshPath);
        auto* OpticMesh=LoadObject<UStaticMesh>(nullptr,*SelectedMeshPath);
        if(!OpticMesh){UE_LOG(LogTemp,Error,TEXT("M4_HOLO: missing optic mesh"));return;}
        if(!HolographicOptic){
        HolographicOptic=NewObject<UStaticMeshComponent>(this,TEXT("M4HolographicOptic"));
        HolographicOptic->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        HolographicOptic->SetCastShadow(false);HolographicOptic->bReceivesDecals=false;
        HolographicOptic->SetupAttachment(AKMViewmodel,TEXT("WPN_root"));
        HolographicOptic->RegisterComponent();
        }
        if(HolographicOptic->GetStaticMesh()!=OpticMesh)HolographicOptic->EmptyOverrideMaterials();
        HolographicOptic->SetStaticMesh(OpticMesh);
        const auto& Ref=AKMViewmodel->GetSkeletalMeshAsset()->GetRefSkeleton();
        auto Bone=[&](const TCHAR* Name){FTransform T=FTransform::Identity;for(int32 I=Ref.FindBoneIndex(Name);I!=INDEX_NONE;I=Ref.GetParentIndex(I))T=T*Ref.GetRefBonePose()[I];return T;};
        const auto Root=Bone(TEXT("WPN_root"));const auto Rear=Bone(TEXT("WPN_RearSight"));const auto Front=Bone(TEXT("WPN_FrontSight"));
        const FVector Axis=(Front.GetLocation()-Rear.GetLocation()).GetSafeNormal();
        // The source weapon is canted in the bind pose. Its authored sight frame,
        // not component/world Z, defines the rail normal for a rigid attachment.
        const FVector RailUp=Rear.GetRotation().RotateVector(FVector::UpVector);
        const FQuat Rotation=FRotationMatrix::MakeFromXZ(Axis,RailUp).ToQuat();
        // The 3.2 cm saddle drop belongs to the M4/QBZ marker height: their rear
        // sight marker sits above the rail. The ASH-12's markers are measured on
        // the rail crown itself, so its saddle goes straight on it.
        const float RailDrop=bUseASH12?ASH12WeaponAssets::OpticRailDrop:3.2f;
        const float Along=bUseASH12?ASH12WeaponAssets::OpticAlongCM(Variant):8.f;
        const FTransform Mount(Rotation,Rear.GetLocation()+Axis*Along-RailUp*RailDrop,FVector::OneVector);
        HolographicMount=bUseM16?M16Attachments::OpticMount():bUseQBZ191?QBZ191Attachments::OpticMount(Variant):Mount.GetRelativeTransform(Root);
        HolographicOptic->SetRelativeTransform(HolographicMount);
    }
    if(bHolographicOptic!=bHolographic || OpticVariant!=Variant)bSightCalibrated=false;
    bHolographicOptic=bHolographic;
    if(OpticVariant!=Variant)LPVOMagnification=1.f;
    OpticVariant=bHolographic?Variant:FString();
    UpdateFoldingSights(0.f);
    if(LPVO&&bHolographic&&!LPVORing){
        const FString RingMeshPath = bUseM16 ? M16Attachments::MeshPath(TEXT("lpvo_ring")) : bUseASH12 ? ASH12WeaponAssets::OpticMeshPath(TEXT("lpvo_ring"))
            : bUseQBZ191 ? QBZ191Attachments::MeshPath(TEXT("lpvo_ring")) : FString(TEXT("/Game/Weapons/AttachmentFinish20260913/M4/Meshes/SM_LPVORing"));
        auto* RingMesh=LoadObject<UStaticMesh>(nullptr,*RingMeshPath);
        if(RingMesh){LPVORing=NewObject<UStaticMeshComponent>(this,TEXT("LPVOMagnificationRing"));LPVORing->SetStaticMesh(RingMesh);LPVORing->SetCollisionEnabled(ECollisionEnabled::NoCollision);LPVORing->SetCastShadow(false);LPVORing->SetupAttachment(HolographicOptic);LPVORing->RegisterComponent();LPVORing->SetRelativeLocation(FVector(-7.1f,0,4.f));}
    }
    if(LPVORing){LPVORing->SetVisibility(LPVO&&bHolographic);LPVORing->SetRelativeRotation(FRotator(0,0,(LPVOMagnification-1.f)*24.f));}
    if(HolographicOptic)HolographicOptic->SetVisibility(bHolographic);
    for(auto Head:FoldingSightHeads)Head->SetVisibility(bUsingM4Infima&&bInventoryWeaponReady);
}
FVector AFPSGAMECharacter::HolographicAimPoint() const
{
    return HolographicOptic?HolographicOptic->GetComponentTransform().TransformPosition(OpticLocalAimPoint()):FVector::ZeroVector;
}
FVector AFPSGAMECharacter::OpticLocalAimPoint() const
{
    if ((bUseDanWesson715 || OpticVariant==PSO1AttachmentAssets::Variant) && HolographicOptic && HolographicOptic->GetStaticMesh())
        if (const auto* Center = HolographicOptic->GetStaticMesh()->FindSocket(TEXT("AimCenter")))
            return Center->RelativeLocation;
    if(bUseM1911)return OpticVariant==TEXT("panoramic_red_dot")
        ?FVector(2.125f,0,3.25f)*M1911WeaponAssets::PanoramicBodyScale
        :FVector(-.653782f,0,5.175324f)*M1911WeaponAssets::HolographicBodyScale;
    if(AKMSoviet::Matches(AKMViewmodel)&&OpticVariant==TEXT("holographic"))return AKMAttachment::HoloPointCM;
    if(OpticVariant==TEXT("lpvo_1_6x"))return FVector(-12.15f,0,4.f);
    if(OpticVariant==TEXT("prism_scope_2x"))return FVector(-6.15f,0,4.f);
    return OpticVariant==TEXT("panoramic_red_dot")?FVector(2.125f,0,3.25f):FVector(-.653782f,0,5.175324f);
}
float AFPSGAMECharacter::EffectiveADSVerticalFOV() const
{
    return FMath::RadiansToDegrees(2.f*FMath::Atan(FMath::Tan(FMath::DegreesToRadians(ADSVerticalFieldOfView)*.5f)/GetOpticMagnification()));
}
bool AFPSGAMECharacter::ValidateGunsmithSight(float& PixelError) const
{
    PixelError=MAX_flt;if(!HolographicOptic||!HolographicOptic->IsVisible())return false;
    const auto* PC=Cast<APlayerController>(GetController());if(!PC)return false;
    FVector2D Point;int32 W,H;PC->GetViewportSize(W,H);
    if(!PC->ProjectWorldLocationToScreen(HolographicAimPoint(),Point))return false;
    PixelError=FVector2D::Distance(Point,FVector2D(W*.5,H*.5));
    return PixelError<2.f;
}
bool AFPSGAMECharacter::ValidateHolographicShot() const
{
    if(GetScopePresentationAlpha()>.5f)return bHolographicOptic&&WeaponADSFactor>.98f&&FVector::DotProduct(ComputeShotDirection(),FirstPersonCamera->GetForwardVector())>.99999f;
    return bHolographicOptic&&WeaponADSFactor>.98f&&FVector::DotProduct(ComputeShotDirection(),(HolographicAimPoint()-FirstPersonCamera->GetComponentLocation()).GetSafeNormal())>.99999f;
}
bool AFPSGAMECharacter::MeasureHolographicOrientation(float& ScreenRollDegrees,float& RailErrorDegrees) const
{
    ScreenRollDegrees=RailErrorDegrees=180.f;
    if(!bHolographicOptic||!HolographicOptic)return false;
    const FVector OpticUp=HolographicOptic->GetUpVector();
    const FVector RailUp=AKMViewmodel->GetSocketTransform(AKMSoviet::Matches(AKMViewmodel)?TEXT("WPN_root"):TEXT("WPN_RearSight")).GetRotation().RotateVector(FVector::UpVector);
    RailErrorDegrees=FMath::RadiansToDegrees(FMath::Acos(FMath::Clamp(FVector::DotProduct(OpticUp,RailUp),-1.0,1.0)));
    const auto* PC=Cast<APlayerController>(GetController());if(!PC)return false;
    FVector2D Center,Top;
    if(!PC->ProjectWorldLocationToScreen(HolographicAimPoint(),Center)||!PC->ProjectWorldLocationToScreen(HolographicAimPoint()+OpticUp*2.f,Top))return false;
    const FVector2D Delta=Top-Center;
    ScreenRollDegrees=FMath::RadiansToDegrees(FMath::Atan2(Delta.X,-Delta.Y));
    return true;
}

void AFPSGAMECharacter::SetLPVOMagnification(float Value)
{
    if(OpticVariant!=TEXT("lpvo_1_6x"))return;
    LPVOMagnification=FMath::Clamp(Value,1.f,6.f);
    if(LPVORing)LPVORing->SetRelativeRotation(FRotator(0,0,(LPVOMagnification-1.f)*24.f));
}
bool AFPSGAMECharacter::AdjustOpticMagnification(float Delta)
{
    if(OpticVariant!=TEXT("lpvo_1_6x")||!IsAiming())return false;
    SetLPVOMagnification(LPVOMagnification+Delta);return true;
}

float AFPSGAMECharacter::GetScopePresentationAlpha() const
{
    if((!HasPSO1Scope()&&OpticVariant!=TEXT("lpvo_1_6x"))||!bInventoryWeaponReady||IsTraversing()||IsWeaponBusy())return 0.f;
    return FMath::SmoothStep(.65f,.98f,CameraADSFactor);
}

// Seconds since the last shot, or a large value so callers can treat it as
// "no recent shot". Presentation only - the firing path itself is untouched.
float AFPSGAMECharacter::GetLastShotAgeSeconds() const
{
    if(!GetWorld()||LastShotWorldTime<0.0)return 1.e6f;
    return static_cast<float>(FMath::Max(0.0,GetWorld()->GetTimeSeconds()-LastShotWorldTime));
}

// 0..1 deterministic per-shot variation (flash lean/elongation) without storing
// extra state: the shot clock already identifies a shot uniquely.
float AFPSGAMECharacter::GetLastShotSeed() const
{
    if(LastShotWorldTime<0.0)return 0.f;
    const double Value=FMath::Sin(LastShotWorldTime*12.9898)*43758.5453;
    return static_cast<float>(Value-FMath::FloorToDouble(Value));
}

void AFPSGAMECharacter::UpdateScopePresentation()
{
    const bool bScopeHidesViewmodel=GetScopePresentationAlpha()>.5f;
    if(!bScopeHidesViewmodel&&ScopeHiddenParts.IsEmpty())return;
    const auto* Body=FindComponentByClass<UFPSPlayerBodyComponent>();
    const bool bThirdPerson=Body&&Body->IsThirdPersonViewEnabled();
    // Owner-only hiding preserves attachment visibility and other world views.
    if(bScopeHidesViewmodel){
        TArray<USceneComponent*> Parts;AKMViewmodel->GetChildrenComponents(true,Parts);Parts.Add(AKMViewmodel);
        for(auto* Part:Parts)if(auto* Primitive=Cast<UPrimitiveComponent>(Part)){
            // Track a scope request even when third person already hides the part,
            // so switching back to first person cannot reveal it inside the scope.
            if(!Primitive->bOwnerNoSee||bThirdPerson)ScopeHiddenParts.AddUnique(Primitive);
            if(!Primitive->bOwnerNoSee)Primitive->SetOwnerNoSee(true);
        }
    }else{
        // Releasing the scope must not undo the third-person camera's hide request.
        for(const auto& Part:ScopeHiddenParts)
            if(Part.IsValid()&&Part->bOwnerNoSee!=bThirdPerson)Part->SetOwnerNoSee(bThirdPerson);
        ScopeHiddenParts.Reset();
    }
}
