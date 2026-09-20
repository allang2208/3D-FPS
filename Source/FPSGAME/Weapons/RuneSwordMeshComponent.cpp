#include "RuneSwordMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "TwoBoneIK.h"

void URuneSwordMeshComponent::CaptureWhirlwindEntry()
{
    EntryMesh=GetSkeletalMeshAsset();
    EntryPose=GetComponentSpaceTransforms();
    EntryTime=0.f;
}

void URuneSwordMeshComponent::SetWhirlwindEntryTime(float Seconds)
{
    EntryTime=FMath::Max(0.f,Seconds);
    if(EntryTime>=EntrySeconds)ClearWhirlwindEntry();
}

void URuneSwordMeshComponent::ClearWhirlwindEntry()
{
    EntryPose.Reset();EntryMesh.Reset();EntryTime=0.f;
}

void URuneSwordMeshComponent::FinalizeBoneTransform()
{
    if(!EntryPose.IsEmpty())ApplyWhirlwindEntry();
    Super::FinalizeBoneTransform();
}

void URuneSwordMeshComponent::ApplyWhirlwindEntry()
{
    auto* Mesh=GetSkeletalMeshAsset();
    auto& Pose=GetEditableComponentSpaceTransforms();
    if(!Mesh||EntryMesh.Get()!=Mesh||EntryPose.Num()!=Pose.Num())
    {ClearWhirlwindEntry();return;}
    // The first sample must keep exactly the pose the player was already seeing.
    if(EntryTime<=0.f){Pose=EntryPose;return;}
    const auto& Ref=Mesh->GetRefSkeleton();
    const float T=FMath::Clamp(EntryTime/EntrySeconds,0.f,1.f);
    const float Alpha=T*T*T*(T*(T*6.f-15.f)+10.f);
    const TArray<FTransform> Incoming=Pose;
    // Blend in parent space so the upper arm and forearm do not shorten along
    // the interpolation chord. The WPN_root uses this same blend and clock.
    for(int32 I=0;I<Pose.Num();++I)
    {
        const int32 Parent=Ref.GetParentIndex(I);
        const FTransform A=Parent==INDEX_NONE?EntryPose[I]:EntryPose[I].GetRelativeTransform(EntryPose[Parent]);
        const FTransform B=Parent==INDEX_NONE?Incoming[I]:Incoming[I].GetRelativeTransform(Incoming[Parent]);
        FTransform Local;Local.Blend(A,B,Alpha);
        Pose[I]=Parent==INDEX_NONE?Local:Local*Pose[Parent];
    }
    const int32 Weapon=GetBoneIndex(TEXT("WPN_root"));
    if(Weapon==INDEX_NONE)return;
    const TArray<FTransform> Blended=Pose;
    for(const TCHAR* Side:{TEXT("l"),TEXT("r")})
    {
        const auto Bone=[&](const TCHAR* Stem){return GetBoneIndex(FName(*(FString(Stem)+TEXT("_")+Side)));};
        const int32 C=Bone(TEXT("clavicle")),U=Bone(TEXT("upperarm")),L=Bone(TEXT("lowerarm")),H=Bone(TEXT("hand"));
        if(C==INDEX_NONE||U==INDEX_NONE||L==INDEX_NONE||H==INDEX_NONE)continue;
        FTransform Grip;
        Grip.Blend(EntryPose[H].GetRelativeTransform(EntryPose[Weapon]),
            Incoming[H].GetRelativeTransform(Incoming[Weapon]),Alpha);
        const FTransform Target=Grip*Pose[Weapon];
        const FVector OldA=Blended[U].GetLocation(),OldE=Blended[L].GetLocation(),OldH=Blended[H].GetLocation();
        const double UpperLength=(OldE-OldA).Size(),LowerLength=(OldH-OldE).Size();
        const FVector Reach=Target.GetLocation()-OldA;
        const double SupportedReach=FMath::Max(0.,UpperLength+LowerLength-.01);
        const FVector ShoulderShift=Reach.GetSafeNormal()*FMath::Max(0.,Reach.Size()-SupportedReach);
        const FVector A=OldA+ShoulderShift;
        FVector E,Hand;
        AnimationCore::SolveTwoBoneIK(A,OldE+ShoulderShift,OldH+ShoulderShift,
            OldE+ShoulderShift,Target.GetLocation(),E,Hand,UpperLength,LowerLength,false,1.,1.);
        FTransform Upper=Blended[U],Lower=Blended[L],Wrist=Blended[H];
        Upper.SetLocation(A);
        Upper.SetRotation((FQuat::FindBetweenNormals((OldE-OldA).GetSafeNormal(),(E-A).GetSafeNormal())*Upper.GetRotation()).GetNormalized());
        Lower.SetLocation(E);
        Lower.SetRotation((FQuat::FindBetweenNormals((OldH-OldE).GetSafeNormal(),(Hand-E).GetSafeNormal())*Lower.GetRotation()).GetNormalized());
        Wrist.SetLocation(Hand);Wrist.SetRotation(Target.GetRotation());
        // Rebuild helpers and fingers from their blended local transforms.
        // Both wrists follow the shared weapon grip, not independent lerps.
        for(int32 I=C;I<Pose.Num();++I)
        {
            // The weapon is the constraint driver even on rigs parenting it
            // under a hand. Do not carry it a second time with that arm's IK.
            if(I==Weapon||Ref.BoneIsChildOf(I,Weapon))continue;
            if(I==C)Pose[I].AddToTranslation(ShoulderShift);
            else if(I==U)Pose[I]=Upper;
            else if(I==L)Pose[I]=Lower;
            else if(I==H)Pose[I]=Wrist;
            else if(Ref.BoneIsChildOf(I,C))
            {
                const int32 Parent=Ref.GetParentIndex(I);
                Pose[I]=Blended[I].GetRelativeTransform(Blended[Parent])*Pose[Parent];
            }
        }
    }
}
