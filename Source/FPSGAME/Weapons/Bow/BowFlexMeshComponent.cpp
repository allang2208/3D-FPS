#include "BowFlexMeshComponent.h"
#include "Engine/SkeletalMesh.h"

void UBowFlexMeshComponent::SetFlexMesh(USkeletalMesh* Mesh)
{
    SetSkeletalMesh(Mesh);SetComponentTickEnabled(false);SetBoundsScale(1.8f);
    bFlexReady=false;ReferenceCS.Reset();LastDistribution=-1.f;
    if(!Mesh)return;
    const auto& Ref=Mesh->GetRefSkeleton();ReferenceCS=Ref.GetRefBonePose();BoneSpaceTransforms=ReferenceCS;
    for(int32 I=0;I<ReferenceCS.Num();++I)
        if(const int32 Parent=Ref.GetParentIndex(I);Parent!=INDEX_NONE)ReferenceCS[I]*=ReferenceCS[Parent];
    bool Valid=true;
    for(int32 S=0;S<2;++S)for(int32 I=0;I<5;++I)
    {
        const FString Name=FString(S==0?TEXT("upper"):TEXT("lower"))+(I==4?TEXT("_tip"):FString::Printf(TEXT("_%02d"),I+1));
        Chain[S][I]=Ref.FindBoneIndex(FName(Name));Valid&=Chain[S][I]!=INDEX_NONE;
    }
    bFlexReady=Valid;MarkRefreshTransformDirty();RefreshBoneTransforms();
}
FVector UBowFlexMeshComponent::TipPosition(int32 Side,float Angle,float Distribution) const
{
    FVector Position=ReferenceCS[Chain[Side][0]].GetLocation();
    for(int32 I=1;I<5;++I)
    {
        const float Weight=FMath::Pow(float(I)/4.f,Distribution);
        const FQuat Bend(FVector::YAxisVector,Angle*(Side==0?-1.f:1.f)*Weight);
        Position+=Bend.RotateVector(ReferenceCS[Chain[Side][I]].GetLocation()-ReferenceCS[Chain[Side][I-1]].GetLocation());
    }
    return Position;
}
void UBowFlexMeshComponent::ApplyStringLoad(const FVector& NockCM,const FVector& BraceCM,float Distribution,float RingDegrees)
{
    if(!bFlexReady)return;
    Distribution=FMath::Clamp(Distribution,.5f,2.f);
    if(NockCM.Equals(LastNock,.0001)&&BraceCM.Equals(LastBrace,.0001)&&FMath::IsNearlyEqual(Distribution,LastDistribution)&&FMath::IsNearlyEqual(RingDegrees,LastRing))return;
    LastNock=NockCM;LastBrace=BraceCM;LastDistribution=Distribution;LastRing=RingDegrees;
    const double RestLength=FVector::Distance(ReferenceCS[Chain[0][4]].GetLocation(),BraceCM)+FVector::Distance(ReferenceCS[Chain[1][4]].GetLocation(),BraceCM);
    auto Length=[&](float A){return FVector::Distance(TipPosition(0,A,Distribution),NockCM)+FVector::Distance(TipPosition(1,A,Distribution),NockCM);};
    float Low=0.f,High=FMath::DegreesToRadians(38.f);
    if(Length(0.f)>RestLength+.0001)
    {
        // Bounded deterministic solve; bone segment lengths remain unchanged.
        for(int32 I=0;I<14;++I){const float Mid=(Low+High)*.5f;if(Length(Mid)>RestLength)Low=Mid;else High=Mid;}
    }
    else High=0.f;
    const float Angle=(Low+High)*.5f+FMath::DegreesToRadians(FMath::Clamp(RingDegrees,-1.5f,1.5f));
    TArray<FTransform,TInlineAllocator<16>> Pose;Pose.Append(ReferenceCS);
    for(int32 S=0;S<2;++S)
    {
        FVector Position=ReferenceCS[Chain[S][0]].GetLocation();
        for(int32 I=0;I<5;++I)
        {
            if(I>0)
            {
                const FQuat Previous(FVector::YAxisVector,Angle*(S==0?-1.f:1.f)*FMath::Pow(float(I)/4.f,Distribution));
                Position+=Previous.RotateVector(ReferenceCS[Chain[S][I]].GetLocation()-ReferenceCS[Chain[S][I-1]].GetLocation());
            }
            const FQuat Bend(FVector::YAxisVector,Angle*(S==0?-1.f:1.f)*FMath::Pow(float(FMath::Min(I+1,4))/4.f,Distribution));
            Pose[Chain[S][I]].SetLocation(Position);Pose[Chain[S][I]].SetRotation((Bend*ReferenceCS[Chain[S][I]].GetRotation()).GetNormalized());
        }
    }
    const auto& Ref=GetSkinnedAsset()->GetRefSkeleton();
    for(int32 I=0;I<Pose.Num();++I)
    {const int32 Parent=Ref.GetParentIndex(I);BoneSpaceTransforms[I]=Parent==INDEX_NONE?Pose[I]:Pose[I].GetRelativeTransform(Pose[Parent]);}
    MarkRefreshTransformDirty();RefreshBoneTransforms();
}
bool UBowFlexMeshComponent::Tips(FVector& Upper,FVector& Lower) const
{
    if(!bFlexReady)return false;
    const auto& Pose=GetComponentSpaceTransforms();
    if(!Pose.IsValidIndex(Chain[0][4])||!Pose.IsValidIndex(Chain[1][4]))return false;
    Upper=Pose[Chain[0][4]].GetLocation();Lower=Pose[Chain[1][4]].GetLocation();return true;
}
