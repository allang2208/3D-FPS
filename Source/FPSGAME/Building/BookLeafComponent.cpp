#include "BookLeafComponent.h"
#include "Engine/SkeletalMesh.h"

UBookLeafComponent::UBookLeafComponent()
{
    PrimaryComponentTick.bCanEverTick=false;
    SetCollisionEnabled(ECollisionEnabled::NoCollision);
    SetGenerateOverlapEvents(false);
    SetCanEverAffectNavigation(false);
    SetMobility(EComponentMobility::Movable);
    // The same reference sheet crosses the spine and rises above the binding.
    bComponentUseFixedSkelBounds=true;
    SetBoundsScale(2.f);
}

bool UBookLeafComponent::InitializeTemplate(USkeletalMesh* Mesh)
{
    if(!Mesh)return false;
    SetSkinnedAssetAndUpdate(Mesh);
    const FReferenceSkeleton& Skeleton=Mesh->GetRefSkeleton();
    ReferenceComponentPose=Skeleton.GetRefBonePose();
    for(int32 I=1;I<ReferenceComponentPose.Num();++I)
        ReferenceComponentPose[I]*=ReferenceComponentPose[Skeleton.GetParentIndex(I)];
    Chain.Reset();
    for(int32 I=0;I<ReferenceComponentPose.Num();++I)
        if(Skeleton.GetBoneName(I).ToString().StartsWith(TEXT("Page_")))Chain.Add(I);
    WorkingComponentPose=ReferenceComponentPose;
    return Chain.Num()>2;
}

void UBookLeafComponent::SetPagePose(float Turn,float CurlDirection,float CornerLift)
{
    if(Chain.Num()<3||BoneSpaceTransforms.Num()!=ReferenceComponentPose.Num())return;
    const FReferenceSkeleton& Skeleton=GetSkinnedAsset()->GetRefSkeleton();
    const float T=FMath::Clamp(Turn,0.f,1.f),Phase=PI*T;
    const float Wave=FMath::Sin(Phase),RestSide=FMath::Cos(Phase);
    const float Width=FMath::Max(PaperWidth,1.f);
    auto Angle=[&](float X)
    {
        const float U=FMath::Clamp(X/Width,0.f,1.f);
        const float Slope=RestArch*PI/Width*FMath::Cos(PI*U)+.045f/.7f*FMath::Exp(-X/.7f);
        return Phase+RestSide*FMath::Atan(Slope)+CurlDirection*TurnBend*Wave*(.65f-1.3f*U);
    };
    FVector Center(0,0,-.045f);
    float PreviousX=0;
    for(int32 Index:Chain)
    {
        const FTransform& Ref=ReferenceComponentPose[Index];
        const float X=Ref.GetLocation().X;
        const float A=Angle((PreviousX+X)*.5f);
        // Integrate a constant-length strip: changing curvature never scales UVs.
        Center+=FVector(FMath::Cos(A),0,FMath::Sin(A))*(X-PreviousX);
        const float U=FMath::Clamp(X/Width,0.f,1.f);
        const float Twist=CornerLift/FMath::Max(PaperHeight*.5f,1.f)*U*U*Wave;
        const FQuat Bend=FQuat(FVector::YAxisVector,-Angle(X))*FQuat(FVector::XAxisVector,Twist);
        WorkingComponentPose[Index]=FTransform(Bend*Ref.GetRotation(),Center,Ref.GetScale3D());
        const int32 Parent=Skeleton.GetParentIndex(Index);
        BoneSpaceTransforms[Index]=Parent==INDEX_NONE?WorkingComponentPose[Index]:
            WorkingComponentPose[Index].GetRelativeTransform(WorkingComponentPose[Parent]);
        PreviousX=X;
    }
    // The private reader world does not tick skeletal components. Submit once
    // after the whole chain is posed, also updating skinned normals/tangents.
    RefreshBoneTransforms(nullptr);
}
