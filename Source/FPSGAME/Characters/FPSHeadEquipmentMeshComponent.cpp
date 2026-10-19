#include "FPSHeadEquipmentMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "Camera/PlayerCameraManager.h"
#include "GameFramework/PlayerController.h"

UFPSHeadEquipmentMeshComponent::UFPSHeadEquipmentMeshComponent()
{
    PrimaryComponentTick.bCanEverTick=true;
    PrimaryComponentTick.TickGroup=TG_PostPhysics;
    bComponentUseFixedSkelBounds=true;
    SetBoundsScale(1.15f);
}
void UFPSHeadEquipmentMeshComponent::ConfigureTip(const TArray<FName>& Bones,float MaxDegrees,float Frequency,float Damping)
{
    TipBones.Reset();RestPose.Reset();TipAxesX.Reset();TipAxesY.Reset();
    if(const auto* Mesh=Cast<USkeletalMesh>(GetSkinnedAsset()))
    {
        const auto& Ref=Mesh->GetRefSkeleton();RestPose=Ref.GetRefBonePose();TArray<FTransform> Frames=RestPose;
        for(int32 I=0;I<Frames.Num();++I)if(Ref.GetParentIndex(I)>=0)Frames[I]*=Frames[Ref.GetParentIndex(I)];
        for(FName Name:Bones)
        {
            const int32 I=Ref.FindBoneIndex(Name);
            if(I!=INDEX_NONE&&TipBones.Num()<4)
            {TipBones.Add(I);TipAxesX.Add(Frames[I].GetRotation().UnrotateVector(FVector::XAxisVector));TipAxesY.Add(Frames[I].GetRotation().UnrotateVector(FVector::YAxisVector));}
        }
    }
    Limit=FMath::DegreesToRadians(FMath::Clamp(MaxDegrees,0.f,15.f));
    Omega=2.f*PI*FMath::Clamp(Frequency,1.f,5.f);DampingRatio=FMath::Clamp(Damping,.4f,1.f);
    ResetTip();
}
void UFPSHeadEquipmentMeshComponent::ResetTip()
{Bend=Speed=FVector2D::ZeroVector;bSampled=false;ApplyTip();}
void UFPSHeadEquipmentMeshComponent::ApplyTip()
{
    if(RestPose.Num()!=BoneSpaceTransforms.Num())return;
    BoneSpaceTransforms=RestPose;
    const float Total=TipBones.Num()*(TipBones.Num()+1)*.5f;
    for(int32 J=0;J<TipBones.Num();++J)
    {
        const int32 Bone=TipBones[J];const float W=float(TipBones.Num()-J)/Total;
        const FQuat Rotation=FQuat(TipAxesX[J],Bend.X*W)*FQuat(TipAxesY[J],Bend.Y*W);
        BoneSpaceTransforms[Bone].SetRotation((RestPose[Bone].GetRotation()*Rotation).GetNormalized());
    }
    MarkRefreshTransformDirty();
}
void UFPSHeadEquipmentMeshComponent::SetDynamicsVisible(bool Visible)
{
    const bool Enabled=Visible&&!TipBones.IsEmpty();
    if(IsComponentTickEnabled()!=Enabled)
    {ResetTip();RefreshBoneTransforms();SetComponentTickEnabled(Enabled);}
}
void UFPSHeadEquipmentMeshComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick)
{
    const FVector Position=GetComponentLocation();const FQuat Rotation=GetComponentQuat();
    bool Near=false;
    if(const auto* World=GetWorld())if(const auto* PC=World->GetFirstPlayerController();PC&&PC->PlayerCameraManager)
        Near=FVector::DistSquared(Position,PC->PlayerCameraManager->GetCameraLocation())<FMath::Square(2200.f);
    if(!Near||Delta<=SMALL_NUMBER||Delta>.1f||!bSampled||FVector::DistSquared(Position,PreviousLocation)>FMath::Square(150.f))
    {
        ResetTip();PreviousVelocity=FVector::ZeroVector;
    }
    else
    {
        const FVector Velocity=(Position-PreviousLocation)/Delta;
        const FVector Acceleration=Rotation.UnrotateVector(((Velocity-PreviousVelocity)/Delta).GetClampedToMaxSize(2500.f));
        FQuat Change=Rotation*PreviousRotation.Inverse();if(Change.W<0)Change=Change*-1.f;
        FVector Axis;double Radians;Change.ToAxisAndAngle(Axis,Radians);
        const FVector Angular=Rotation.UnrotateVector(Axis*FMath::Min(Radians/double(Delta),12.));
        FVector2D Target(-Acceleration.Y*.000045-Angular.X*.018,Acceleration.X*.000045-Angular.Y*.018);
        Target=Target.GetClampedToMaxSize(Limit);
        const int32 Steps=FMath::Clamp(FMath::CeilToInt(Delta*120.f),1,12);const float H=Delta/Steps;
        for(int32 I=0;I<Steps;++I)
        {
            Speed+=(Omega*Omega*(Target-Bend)-2.f*DampingRatio*Omega*Speed)*H;Bend+=Speed*H;
            if(Bend.SizeSquared()>Limit*Limit){Bend=Bend.GetSafeNormal()*Limit;Speed*=.4f;}
        }
        PreviousVelocity=Velocity;ApplyTip();
    }
    PreviousLocation=Position;PreviousRotation=Rotation;bSampled=Near;
    Super::TickComponent(Delta,Type,Tick);
}
