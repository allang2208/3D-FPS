#include "RuneSwordMeshComponent.h"
#include "RuneSwordComponent.h"
#include "Engine/SkeletalMesh.h"
#include "TwoBoneIK.h"

namespace
{
void RaiseQuickCombatWindup(URuneSwordMeshComponent& Mesh)
{
    using namespace RuneSwordPommelRhythm;
    // Read the sampled animation clock, not the component's previous-frame
    // elapsed time. The 0.20 s windup and the contact pose stay in sync.
    const float Time=Mesh.GetPosition();
    const float Weight=Time<=ContactStart
        ? RecoveryEase((Time-TurnEnd*.5f)/(RaiseEnd-TurnEnd*.5f))
        : 1.f-RecoveryEase((Time-ContactStart)/(ExtensionEnd-ContactStart));
    if(Weight<=0.f)return;
    const int32 Weapon=Mesh.GetBoneIndex(TEXT("WPN_root"));
    auto* Asset=Mesh.GetSkeletalMeshAsset();
    if(!Asset||Weapon==INDEX_NONE)return;
    const auto& Ref=Asset->GetRefSkeleton();
    auto& Pose=Mesh.GetEditableComponentSpaceTransforms();
    const TArray<FTransform> Source=Pose;
    // The mesh has only a yaw mounting rotation: local +Z is camera-up.
    // Lift the actual grip group by 10 cm, retaining both hands' grip frames.
    const FVector Lift(0.,0.,10.*Weight);
    for(int32 I=0;I<Pose.Num();++I)
        if(I==Weapon||Ref.BoneIsChildOf(I,Weapon))Pose[I].AddToTranslation(Lift);
    for(const TCHAR* Side:{TEXT("l"),TEXT("r")})
    {
        const auto Bone=[&](const TCHAR* Stem){return Mesh.GetBoneIndex(FName(*(FString(Stem)+TEXT("_")+Side)));};
        const int32 C=Bone(TEXT("clavicle")),U=Bone(TEXT("upperarm")),L=Bone(TEXT("lowerarm")),H=Bone(TEXT("hand"));
        if(C==INDEX_NONE||U==INDEX_NONE||L==INDEX_NONE||H==INDEX_NONE)continue;
        const FVector OldA=Source[U].GetLocation(),OldE=Source[L].GetLocation(),OldH=Source[H].GetLocation();
        const FVector Target=OldH+Lift;
        const double UpperLength=(OldE-OldA).Size(),LowerLength=(OldH-OldE).Size();
        // A small shoulder rise supports the higher grip; retain some elbow
        // bend even at maximum reach rather than stretching either bone.
        FVector ShoulderShift=Lift*.16;
        const FVector Reach=Target-OldA-ShoulderShift;
        ShoulderShift+=Reach.GetSafeNormal()*FMath::Max(0.,Reach.Size()-(UpperLength+LowerLength)*.98);
        const FVector A=OldA+ShoulderShift;
        FVector E,Hand;
        AnimationCore::SolveTwoBoneIK(A,OldE+ShoulderShift,OldH+ShoulderShift,
            OldE+Lift*.5,Target,E,Hand,UpperLength,LowerLength,false,1.,1.);
        const FQuat LowerDelta=FQuat::FindBetweenNormals((OldH-OldE).GetSafeNormal(),(Hand-E).GetSafeNormal());
        // Transport the forearm frame through the upper arm too. Independent
        // shortest-swing rotations can concentrate an axial twist at the elbow.
        const FQuat UpperDelta=FQuat::FindBetweenNormals(
            LowerDelta.RotateVector((OldE-OldA).GetSafeNormal()),(E-A).GetSafeNormal())*LowerDelta;
        FTransform Upper=Source[U],Lower=Source[L],Wrist=Source[H];
        Upper.SetLocation(A);Upper.SetRotation((UpperDelta*Upper.GetRotation()).GetNormalized());
        Lower.SetLocation(E);Lower.SetRotation((LowerDelta*Lower.GetRotation()).GetNormalized());
        Wrist.SetLocation(Hand);
        for(int32 I=C;I<Pose.Num();++I)
        {
            // WPN_root and modular attachments already moved with the grip.
            if(I==Weapon||Ref.BoneIsChildOf(I,Weapon))continue;
            if(I==C)Pose[I].AddToTranslation(ShoulderShift);
            else if(I==U)Pose[I]=Upper;
            else if(I==L)Pose[I]=Lower;
            else if(I==H)Pose[I]=Wrist;
            else if(Ref.BoneIsChildOf(I,C))
            {
                const int32 Parent=Ref.GetParentIndex(I);
                Pose[I]=Source[I].GetRelativeTransform(Source[Parent])*Pose[Parent];
            }
        }
    }
}
}

void URuneSwordMeshComponent::CaptureWhirlwindEntry()
{
    EntryMesh=GetSkeletalMeshAsset();
    EntryPose=GetComponentSpaceTransforms();
    EntryTime=0.f;EntryDuration=EntrySeconds;
}

void URuneSwordMeshComponent::SetWhirlwindEntryTime(float Seconds)
{
    EntryTime=FMath::Max(0.f,Seconds);
    if(EntryTime>=EntryDuration)ClearWhirlwindEntry();
}

void URuneSwordMeshComponent::ClearWhirlwindEntry()
{
    EntryPose.Reset();EntryMesh.Reset();EntryTime=0.f;
}

void URuneSwordMeshComponent::CaptureLocomotionEntry()
{
    // Share the grip-constrained solver across locomotion and action handoffs.
    CaptureWhirlwindEntry();
}

void URuneSwordMeshComponent::LimitLocomotionEntry(float Seconds)
{
    // A resumed windup can have less than 100 ms before contact. Finish the
    // visual handoff within that time so sweeps use the authored strike pose.
    EntryDuration=FMath::Min(EntryDuration,FMath::Max(0.f,Seconds));
    if(EntryTime>=EntryDuration)ClearWhirlwindEntry();
}

void URuneSwordMeshComponent::AdvanceLocomotionEntry(float Delta)
{
    if(!EntryPose.IsEmpty())SetWhirlwindEntryTime(EntryTime+FMath::Max(0.f,Delta));
}

void URuneSwordMeshComponent::FinalizeBoneTransform()
{
    if(bCaptureRecoveryIdle)
    {
        // Capture the sampled idle before any action/casting overlay is applied.
        RecoveryMesh=GetSkeletalMeshAsset();
        RecoveryIdlePose=GetEditableComponentSpaceTransforms();
        bCaptureRecoveryIdle=false;
    }
    // Build the raised target before entry blending so the entering frame
    // still matches the currently displayed pose. Ordinary combo #4 shares
    // this animation but does not receive the quick-combat-only lift.
    const auto* Sword=GetOwner()?GetOwner()->FindComponentByClass<URuneSwordComponent>():nullptr;
    if(Sword&&Sword->IsQuickCombatActive())RaiseQuickCombatWindup(*this);
    if(!EntryPose.IsEmpty())ApplyWhirlwindEntry();
    if(RecoveryWeight>0.f)ApplyQuickCombatRecovery();
    Super::FinalizeBoneTransform();
}

void URuneSwordMeshComponent::CacheQuickCombatIdlePose()
{
    // Equipment changes request a capture on the next idle evaluation.
    RecoveryMesh.Reset();
    RecoveryIdlePose.Reset();
    RecoveryWeight=0.f;
    bCaptureRecoveryIdle=true;
}

void URuneSwordMeshComponent::SetQuickCombatRecoveryWeight(float Weight)
{
    RecoveryWeight=FMath::Clamp(Weight,0.f,1.f);
}

void URuneSwordMeshComponent::ApplyQuickCombatRecovery()
{
    auto* Mesh=GetSkeletalMeshAsset();
    auto& Pose=GetEditableComponentSpaceTransforms();
    if(!Mesh||RecoveryMesh.Get()!=Mesh||RecoveryIdlePose.Num()!=Pose.Num())return;
    if(RecoveryWeight>=1.f){Pose=RecoveryIdlePose;return;}
    const TArray<FTransform> Incoming=Pose;
    BlendSupportedPoses(Incoming,RecoveryIdlePose,RecoveryWeight,true);
}

void URuneSwordMeshComponent::ApplyWhirlwindEntry()
{
    auto* Mesh=GetSkeletalMeshAsset();
    auto& Pose=GetEditableComponentSpaceTransforms();
    if(!Mesh||EntryMesh.Get()!=Mesh||EntryPose.Num()!=Pose.Num())
    {ClearWhirlwindEntry();return;}
    // The first sample must keep exactly the pose the player was already seeing.
    if(EntryTime<=0.f){Pose=EntryPose;return;}
    const float T=FMath::Clamp(EntryTime/EntryDuration,0.f,1.f);
    const float Alpha=T*T*T*(T*(T*6.f-15.f)+10.f);
    const TArray<FTransform> Incoming=Pose;
    BlendSupportedPoses(EntryPose,Incoming,Alpha,false);
}

void URuneSwordMeshComponent::BlendSupportedPoses(const TArray<FTransform>& From,
    const TArray<FTransform>& To,float Alpha,bool bPreserveBoneLengths)
{
    auto& Pose=GetEditableComponentSpaceTransforms();
    const auto& Ref=GetSkeletalMeshAsset()->GetRefSkeleton();
    // Blend in parent space so the upper arm and forearm do not shorten along
    // the interpolation chord. The WPN_root uses this same blend and clock.
    for(int32 I=0;I<Pose.Num();++I)
    {
        const int32 Parent=Ref.GetParentIndex(I);
        const FTransform A=Parent==INDEX_NONE?From[I]:From[I].GetRelativeTransform(From[Parent]);
        const FTransform B=Parent==INDEX_NONE?To[I]:To[I].GetRelativeTransform(To[Parent]);
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
        Grip.Blend(From[H].GetRelativeTransform(From[Weapon]),
            To[H].GetRelativeTransform(To[Weapon]),Alpha);
        const FTransform Target=Grip*Pose[Weapon];
        const FVector OldA=Blended[U].GetLocation(),OldE=Blended[L].GetLocation(),OldH=Blended[H].GetLocation();
        // Recovery must not shorten the arm to meet an interpolated wrist.
        // Read lengths from the two source poses, before blending positions.
        const double UpperLength=bPreserveBoneLengths
            ? FMath::Lerp((From[L].GetLocation()-From[U].GetLocation()).Size(),
                (To[L].GetLocation()-To[U].GetLocation()).Size(),double(Alpha)):(OldE-OldA).Size();
        const double LowerLength=bPreserveBoneLengths
            ? FMath::Lerp((From[H].GetLocation()-From[L].GetLocation()).Size(),
                (To[H].GetLocation()-To[L].GetLocation()).Size(),double(Alpha)):(OldH-OldE).Size();
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
