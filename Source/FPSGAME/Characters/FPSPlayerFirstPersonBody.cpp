#include "FPSPlayerBodyComponent.h"
#include "../FPSGAMECharacter.h"
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
        &&DisplayState.Action!=EFPSBodyAction::Dead&&!Character->IsTraversing();
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
    auto* Lower=NewObject<USkeletalMeshComponent>(GetOwner(),TEXT("FirstPersonSharedBody"),RF_Transient);
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
    const bool bShow=ShouldShowFirstPersonLowerBody();
    if(FirstPersonLowerBody->IsVisible()!=bShow)FirstPersonLowerBody->SetVisibility(bShow);
    if(FirstPersonLowerBody->bHiddenInGame==bShow)FirstPersonLowerBody->SetHiddenInGame(!bShow);
}

void UFPSPlayerBodyComponent::ApplyOwnerCameraOffset(FVector& Eye)
{
    OwnerCameraOffset=FVector::ZeroVector;
    if(!FirstPersonLowerBody||!ShouldShowFirstPersonLowerBody()||!Character->FirstPersonCamera)return;
    const float Pitch=-FRotator::NormalizeAxis(Character->GetBaseAimRotation().Pitch);
    const float LookDown=FMath::SmoothStep(20.f,80.f,Pitch);
    FVector Offset(Character->bIsCrouched?OwnerCameraCrouchForward:OwnerCameraForward,0.f,-OwnerCameraLookDownDrop*LookDown);
    Offset.X+=OwnerCameraLookDownForward*LookDown;
    const auto* Parent=Character->FirstPersonCamera->GetAttachParent();
    const FTransform ParentWorld=Parent?Parent->GetComponentTransform():Character->GetActorTransform();
    // The shared world pose pitches the chest forward when looking down.
    // Keep the eye ahead of that posed torso, not merely ahead of the capsule.
    // Native shirt depth is covered by the clearance; no vertex scans or extra
    // pose evaluation are needed. The camera's existing interpolation remains
    // the sole smoothing stage, and melee reuses the resulting stable offset.
    if(const auto* Body=GetBodyMesh())
    {
        static const FName TorsoBones[]={TEXT("pelvis"),TEXT("spine_01"),TEXT("spine_03"),TEXT("spine_05"),TEXT("neck_01")};
        for(const FName Bone:TorsoBones)
        {
            if(Body->GetBoneIndex(Bone)==INDEX_NONE)continue;
            const FVector PosedTorso=ParentWorld.InverseTransformPosition(Body->GetBoneLocation(Bone));
            Offset.X=FMath::Max(Offset.X,PosedTorso.X-Eye.X+OwnerCameraTorsoClearance);
        }
    }
    const FVector Start=ParentWorld.TransformPosition(Eye),Desired=ParentWorld.TransformPosition(Eye+Offset);
    FHitResult Hit;FCollisionQueryParams Params(SCENE_QUERY_STAT(OwnerBodyCamera),false,Character.Get());
    if(GetWorld()->SweepSingleByChannel(Hit,Start,Desired,FQuat::Identity,ECC_Camera,FCollisionShape::MakeSphere(6.f),Params))
        Offset*=FMath::Max(0.f,Hit.Time-.02f);
    OwnerCameraOffset=Offset;
    Eye+=Offset;
}
