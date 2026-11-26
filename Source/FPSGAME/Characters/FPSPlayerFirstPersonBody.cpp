#include "FPSPlayerBodyComponent.h"
#include "FPSBodyPoseAnchorComponent.h"
#include "FPSPlayerBodyAnimInstance.h"
#include "FPSModularOutfitComponent.h"
#include "../FPSGAMECharacter.h"
#include "../Movement/FPSFurnitureRestComponent.h"
#include "../Movement/HorseRiderComponent.h"
#include "../Movement/StableRidingHorse.h"
#include "../Movement/PlayerKnockdownComponent.h"
#include "../Building/FPSForgeWorkComponent.h"
#include "Camera/CameraComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "HAL/IConsoleManager.h"
#include "Dom/JsonObject.h"
#include "Rendering/SkeletalMeshRenderData.h"

namespace FPSFirstPersonBody
{
TAutoConsoleVariable<int32> Enabled(TEXT("fps.body.FirstPersonLegs"),1,
    TEXT("Show the owning player's shared world body in first person."),ECVF_Default);
}

bool UFPSPlayerBodyComponent::ShouldShowFirstPersonLowerBody() const
{
    return Character.IsValid()&&Character->IsLocallyControlled()&&!IsThirdPersonViewEnabled()
        &&!FPSPlayerBodyWorldBodyHidden()&&!FPSPlayerBodyWorldBodySuppressed()
        &&FPSFirstPersonBody::Enabled.GetValueOnGameThread()!=0
        &&!UHorseRiderComponent::UsesSaddleHands(Character.Get())&&DisplayState.Action!=EFPSBodyAction::Dead&&!Character->IsTraversing()&&!IsWorkstationIdle();
}

void UFPSPlayerBodyComponent::InitializeFirstPersonLowerBody()
{
    if(bLowerBodyRequested||!Configuration||!Character.IsValid()||!Character->IsLocallyControlled()
        ||!GetBodyMesh()||!GetBodyMesh()->GetSkeletalMeshAsset())return;
    const TSharedPtr<FJsonObject>* Settings=nullptr;
    if(!Configuration->TryGetObjectField(TEXT("first_person_body"),Settings))return;
    const auto Read=[&](const TCHAR* Key,float Default)
    {double Value=Default;(*Settings)->TryGetNumberField(Key,Value);return float(Value);};
    OwnerCameraForward=Read(TEXT("camera_forward_cm"),56.f);
    OwnerCameraCrouchForward=Read(TEXT("camera_crouch_forward_cm"),62.f);
    OwnerCameraLookDownForward=Read(TEXT("look_down_forward_cm"),12.f);
    OwnerCameraLookDownDrop=Read(TEXT("look_down_drop_cm"),0.f);
    OwnerCameraTorsoClearance=Read(TEXT("torso_front_clearance_cm"),40.f);
    bLowerBodyRequested=true;
    auto* Body=GetBodyMesh();auto* Mesh=Body->GetSkeletalMeshAsset();
    auto* Lower=NewObject<UFPSBodyPoseAnchorComponent>(GetOwner(),TEXT("FirstPersonSharedBody"),RF_Transient);
    GetOwner()->AddInstanceComponent(Lower);
    Lower->ComponentTags.Append({TEXT("FirstPersonLowerBody"),TEXT("SharedOwnerBody"),TEXT("PreloadModularOutfit")});
    Lower->SetSkeletalMeshAsset(Mesh);
    Lower->SetupAttachment(Body);Lower->SetRelativeTransform(FTransform::Identity);
    Lower->SetCollisionEnabled(ECollisionEnabled::NoCollision);Lower->SetGenerateOverlapEvents(false);
    Lower->SetOnlyOwnerSee(true);Lower->SetOwnerNoSee(false);
    Lower->SetCastShadow(false);Lower->bCastHiddenShadow=false;
    Lower->SetHiddenInSceneCapture(true);Lower->SetVisibleInRayTracing(false);
    Lower->bAffectDynamicIndirectLighting=false;
    // The world body is the sole pose authority. No copied-pose pelvis fitting,
    // independent leg IK or owner-only scaling can pull clothes off the torso.
    Lower->SetLeaderPoseComponent(Body);
    Lower->SetDisablePostProcessBlueprint(true);Lower->bUseAttachParentBound=true;
    Lower->SetVisibility(false);Lower->RegisterComponent();
    Lower->SetComponentTickEnabled(false);
    // ModularOutfit assembles the visible skin, torso, trousers and shoes in
    // one transaction. Hide this driver completely even before that load ends.
    if(const auto* Data=Mesh->GetResourceForRendering())
        for(int32 L=0;L<Data->LODRenderData.Num();++L)
            for(int32 S=0;S<Data->LODRenderData[L].RenderSections.Num();++S)
                Lower->ShowMaterialSection(Data->LODRenderData[L].RenderSections[S].MaterialIndex,S,false,L);
    FirstPersonLowerBody=Lower;
    UpdateFirstPersonLowerBodyVisibility();ApplyWorldBodyVisibility();
}

void UFPSPlayerBodyComponent::UpdateFirstPersonLowerBodyVisibility()
{
    if(!FirstPersonLowerBody)return;
    // Knockdown: the shared body plays the full-body fall, so the owner sees its legs. A body without that clip
    // still stands while the camera falls; hide the owner copy (and its outfits) then.
    const bool bShow=!bRideEyeOccluded&&ShouldShowFirstPersonLowerBody()&&!UPlayerKnockdownComponent::HidesOwnerLowerBody(GetOwner());
    bool bChanged=false;
    if(FirstPersonLowerBody->IsVisible()!=bShow){FirstPersonLowerBody->SetVisibility(bShow);bChanged=true;}
    if(FirstPersonLowerBody->bHiddenInGame==bShow){FirstPersonLowerBody->SetHiddenInGame(!bShow);bChanged=true;}
    if(bChanged)
        if(auto* Outfit=GetOwner()->FindComponentByClass<UFPSModularOutfitComponent>())
            Outfit->RefreshVisibilityForSource(FirstPersonLowerBody);
}

void UFPSPlayerBodyComponent::ApplyOwnerCameraOffset(FVector& Eye)
{
    OwnerCameraOffset=FVector::ZeroVector;
    if(UFPSFurnitureRestComponent::IsResting(Character.Get()))return;
    if(IsWorkstationIdle())return;
    if(!Character.IsValid()||!Character->FirstPersonCamera)return;
    if((!FirstPersonLowerBody||!ShouldShowFirstPersonLowerBody())&&!UHorseRiderComponent::IsRiding(Character.Get()))return;
    OwnerCameraOffset=CalculateAnatomicalCameraOffset(Eye);
    Eye+=OwnerCameraOffset;
}

FVector UFPSPlayerBodyComponent::GetGameplayCameraOffset(const FVector& Eye) const
{
    if(!Character.IsValid())return FVector::ZeroVector;
    if(Character->IsLocallyControlled())return OwnerCameraOffset;
    // Remote authority never runs the owner's visual camera update. Derive its
    // reach/melee eye from the same body configuration and collision sweep.
    if(!Character->FirstPersonCamera||UFPSFurnitureRestComponent::IsResting(Character.Get())
        ||IsWorkstationIdle()||DisplayState.Action==EFPSBodyAction::Dead||Character->IsTraversing())return FVector::ZeroVector;
    return CalculateAnatomicalCameraOffset(Eye);
}

FVector UFPSPlayerBodyComponent::CalculateAnatomicalCameraOffset(const FVector& Eye) const
{
    const TSharedPtr<FJsonObject>* Settings=nullptr;
    if(Configuration)Configuration->TryGetObjectField(TEXT("first_person_body"),Settings);
    const auto Read=[&](const TCHAR* Key,float Default)
    {double Value=Default;if(Settings)(*Settings)->TryGetNumberField(Key,Value);return float(Value);};
    const float Pitch=-FRotator::NormalizeAxis(Character->GetBaseAimRotation().Pitch);
    const float LookDown=FMath::SmoothStep(20.f,80.f,Pitch);
    FVector Offset(Character->bIsCrouched?Read(TEXT("camera_crouch_forward_cm"),OwnerCameraCrouchForward):Read(TEXT("camera_forward_cm"),OwnerCameraForward),
        0.f,-Read(TEXT("look_down_drop_cm"),OwnerCameraLookDownDrop)*LookDown);
    float Forward=Offset.X+Read(TEXT("look_down_forward_cm"),OwnerCameraLookDownForward)*LookDown;
    const float Clearance=Read(TEXT("torso_front_clearance_cm"),OwnerCameraTorsoClearance);
    const auto* Parent=Character->FirstPersonCamera->GetAttachParent();
    const FTransform ParentWorld=Parent?Parent->GetComponentTransform():Character->GetActorTransform();
    const auto* Ride=Character->FindComponentByClass<UHorseRiderComponent>();
    const bool bRiding=Ride&&Ride->Active();
    FVector Front=FVector::ForwardVector;
    if(bRiding)
    {
        const FRotator Aim=Character->GetControlRotation();
        Front=ParentWorld.InverseTransformVectorNoScale(FRotator(0,Aim.Yaw,0).Vector()).GetSafeNormal2D();
        Offset.Z+=Ride->EyeHeightOffset();
    }
    // Idle breathing belongs to the body, not the eye. Use an input-pitched
    // reference envelope while stationary; reading animated chest positions
    // here makes the first-person view chase every breath/weight shift.
    // Moving/actions retain their posed clearance and the existing camera
    // interpolation and collision sweep. Melee reuses this same eye offset.
    if(const auto* Body=GetBodyMesh())
    {
        const bool StableIdle=!bRiding&&DisplayState.Action==EFPSBodyAction::None&&DisplayState.Motion==EFPSBodyMotion::Ground
            &&(!BodyAnimation||!BodyAnimation->bFullBodyPoseActive)
            &&Character->GetVelocity().SizeSquared2D()<25.f&&Body->GetSkeletalMeshAsset();
        const auto ReferencePosition=[&](int32 BoneIndex)
        {
            const auto& Ref=Body->GetSkeletalMeshAsset()->GetRefSkeleton();
            FTransform Transform=Ref.GetRefBonePose()[BoneIndex];
            for(int32 ParentIndex=Ref.GetParentIndex(BoneIndex);ParentIndex>=0;ParentIndex=Ref.GetParentIndex(ParentIndex))
                Transform=Transform*Ref.GetRefBonePose()[ParentIndex];
            return Transform.GetLocation();
        };
        const int32 HipIndex=Body->GetBoneIndex(TEXT("pelvis"));
        const FVector ReferenceHip=StableIdle&&HipIndex!=INDEX_NONE?ReferencePosition(HipIndex):FVector::ZeroVector;
        const FQuat IdleLean(FVector::ForwardVector,FMath::DegreesToRadians(-FMath::Clamp(Pitch,-70.f,70.f)*.65f));
        static const FName TorsoBones[]={TEXT("pelvis"),TEXT("spine_01"),TEXT("spine_03"),TEXT("spine_05"),TEXT("neck_01")};
        for(const FName Bone:TorsoBones)
        {
            const int32 BoneIndex=Body->GetBoneIndex(Bone);
            if(BoneIndex==INDEX_NONE)continue;
            const FVector TorsoWorld=StableIdle
                ?Body->GetComponentTransform().TransformPosition(ReferenceHip+IdleLean.RotateVector(ReferencePosition(BoneIndex)-ReferenceHip))
                :Body->GetBoneLocation(Bone);
            const FVector PosedTorso=ParentWorld.InverseTransformPosition(TorsoWorld);
            Forward=FMath::Max(Forward,FVector::DotProduct(PosedTorso-Eye,Front)+Clearance);
        }
    }
    Offset=Front*Forward+FVector(0,0,Offset.Z);
    const FVector Start=ParentWorld.TransformPosition(Eye),Desired=ParentWorld.TransformPosition(Eye+Offset);
    FHitResult Hit;FCollisionQueryParams Params(SCENE_QUERY_STAT(OwnerBodyCamera),false,Character.Get());
    if(bRiding)Params.AddIgnoredActor(Ride->GetMount());
    if(GetWorld()->SweepSingleByChannel(Hit,Start,Desired,FQuat::Identity,ECC_Camera,FCollisionShape::MakeSphere(6.f),Params))
        Offset*=FMath::Max(0.f,Hit.Time-.02f);
    return Offset;
}
