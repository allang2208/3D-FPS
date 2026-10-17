#include "Super90SupportArmNode.h"
#include "Super90WeaponAssets.h"
#include "TubeShotgunAssets.h"
#include "Animation/AnimInstanceProxy.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Math/RotationMatrix.h"

namespace Super90SupportArm
{
FTransform ComponentPose(const FCompactPose& Pose,FCompactPoseBoneIndex Index)
{
    FTransform Result=Pose[Index];
    for(auto Parent=Pose.GetParentBoneIndex(Index);Parent.GetInt()!=INDEX_NONE;Parent=Pose.GetParentBoneIndex(Parent))
        Result=Result*Pose[Parent];
    return Result;
}
FQuat Basis(const FVector& Axis,const FVector& Side)
{
    return FRotationMatrix::MakeFromXY(Axis,Side).ToQuat();
}
}

FSuper90SupportArmNode::FSuper90SupportArmNode()
{
    static const FName Names[]={TEXT("clavicle_l"),TEXT("upperarm_l"),TEXT("lowerarm_l"),
        TEXT("lowerarm_aux_l"),TEXT("lowerarm_twist_02_l"),TEXT("lowerarm_twist_01_l"),
        TEXT("hand_l"),TEXT("index_01_l"),TEXT("pinky_01_l")};
    for(int32 I=0;I<Count;++I)Bones[I].BoneName=Names[I];
}

void FSuper90SupportArmNode::Configure(const USkeletalMeshComponent& Mesh)
{
    USkeletalMesh* Asset=Mesh.GetSkeletalMeshAsset();
    if(CachedMesh.Get()==Asset)return;
    CachedMesh=Asset;
    bEnabled=Asset && TubeShotgunAssets::MatchesMesh(Asset->GetPathName());
}

void FSuper90SupportArmNode::CacheBones_AnyThread(const FAnimationCacheBonesContext& Context)
{
    Source.CacheBones(Context);bReady=false;
    const auto& Required=Context.AnimInstanceProxy->GetRequiredBones();
    const auto& Ref=Required.GetReferenceSkeleton();
    for(int32 I=0;I<Count;++I)
    {
        const int32 Index=Ref.FindBoneIndex(Bones[I].BoneName);
        if(Index==INDEX_NONE)return;
        Bones[I].Initialize(Required);
        if(!Bones[I].IsValidToEvaluate(Required))return;
        Rest[I]=Ref.GetRefBonePose()[Index];
        for(int32 Parent=Ref.GetParentIndex(Index);Parent!=INDEX_NONE;Parent=Ref.GetParentIndex(Parent))
            Rest[I]=Rest[I]*Ref.GetRefBonePose()[Parent];
    }
    RestUpper=Rest[Lower].GetLocation()-Rest[Upper].GetLocation();
    RestFore=Rest[Hand].GetLocation()-Rest[Lower].GetLocation();
    RestWidth=Rest[Index].GetLocation()-Rest[Pinky].GetLocation();
    if(RestUpper.IsNearlyZero()||RestFore.IsNearlyZero()||FVector::CrossProduct(RestFore,RestWidth).IsNearlyZero())return;
    LengthRatio=RestFore.Size()/RestUpper.Size();
    RestForeBasis=Super90SupportArm::Basis(RestFore,RestWidth);
    bReady=true;
}

void FSuper90SupportArmNode::Evaluate_AnyThread(FPoseContext& Output)
{
    Source.Evaluate(Output);
    if(!bEnabled||!bReady)return;
    // Quick melee owns its lowered elbow and skin hinge in the authored clip.
    // This curve is blended with ActionAlpha by the existing pose graph: entry,
    // recovery and interruption all hand back to the ordinary support smoothly.
    // Re-solving a full-weight melee with the palm-width reload rule rolls its
    // upper arm back towards the camera and destroys the authored elbow bend.
    static const FName MeleeOwnershipCurve(TEXT("Super90MeleeArmAuthored"));
    const float MeleeOwnership=FMath::Clamp(Output.Curve.Get(MeleeOwnershipCurve),0.f,1.f);
    if(MeleeOwnership>=1.f-UE_SMALL_NUMBER)return;
    const auto& Required=Output.Pose.GetBoneContainer();
    FTransform Old[Count], Wanted[Count];
    FCompactPoseBoneIndex Indices[Count];
    for(int32 I=0;I<Count;++I)
    {
        Indices[I]=Bones[I].GetCompactPoseIndex(Required);
        Old[I]=Super90SupportArm::ComponentPose(Output.Pose,Indices[I]);Wanted[I]=Old[I];
    }
    const FVector OriginalShoulder=Old[Upper].GetLocation();
    const FVector OriginalElbow=Old[Lower].GetLocation(), Wrist=Old[Hand].GetLocation();
    FVector Axis=Wrist-OriginalShoulder;
    const float Distance=Axis.Size(), UpperLength=(OriginalElbow-OriginalShoulder).Size();
    const float ForeLength=UpperLength*LengthRatio, Total=UpperLength+ForeLength;
    if(Distance<UE_SMALL_NUMBER||UpperLength<UE_SMALL_NUMBER||Distance>=Total-UE_SMALL_NUMBER)return;
    Axis/=Distance;
    FVector Pole=OriginalElbow-OriginalShoulder;
    Pole-=Axis*FVector::DotProduct(Pole,Axis);
    if(!Pole.Normalize())return;

    // The old push folds the elbow to ~155 degrees. Translate the shoulder
    // behind the fixed contact, keeping both bone lengths and some elbow bend.
    // The same smooth support applies to idle, ADS, reload and their blends.
    const float Short=FMath::Max(0.f,.935f*Total-Distance);
    const FVector ShoulderShift=-Axis*(Short*Short/(Short+.0142f*Total));
    const FVector Shoulder=OriginalShoulder+ShoulderShift;
    const float Reach=(Wrist-Shoulder).Size();
    const FQuat HandDeform=(Old[Hand].GetRotation()*Rest[Hand].GetRotation().Inverse()).GetNormalized();
    FVector DesiredPole=-HandDeform.RotateVector(RestFore.GetSafeNormal());
    DesiredPole-=Axis*FVector::DotProduct(DesiredPole,Axis);
    if(DesiredPole.Normalize())
    {
        const float Angle=FMath::Atan2(FVector::DotProduct(Axis,FVector::CrossProduct(Pole,DesiredPole)),
            FVector::DotProduct(Pole,DesiredPole));
        Pole=FQuat(Axis,FMath::Clamp(Angle,-FMath::DegreesToRadians(32.f),FMath::DegreesToRadians(32.f))).RotateVector(Pole);
    }
    const float Along=(UpperLength*UpperLength-ForeLength*ForeLength+Reach*Reach)/(2.f*Reach);
    const float Radius=FMath::Sqrt(FMath::Max(0.f,UpperLength*UpperLength-Along*Along));
    const FVector Elbow=Shoulder+Axis*Along+Pole*Radius;
    const FVector ForeDirection=Wrist-Elbow, PalmWidth=HandDeform.RotateVector(RestWidth);
    if(FVector::CrossProduct(ForeDirection,PalmWidth).IsNearlyZero())return;
    const FQuat ForeDeform=(Super90SupportArm::Basis(ForeDirection,PalmWidth)*RestForeBasis.Inverse()).GetNormalized();
    const FQuat UpperDeform=(FQuat::FindBetweenNormals(ForeDeform.RotateVector(RestUpper.GetSafeNormal()),
        (Elbow-Shoulder).GetSafeNormal())*ForeDeform).GetNormalized();
    Wanted[Clavicle].AddToTranslation(ShoulderShift);
    Wanted[Upper].SetLocation(Shoulder);
    Wanted[Upper].SetRotation((UpperDeform*Rest[Upper].GetRotation()).GetNormalized());
    const float Scale=UpperLength/RestUpper.Size();
    for(int32 I=Lower;I<=Twist01;++I)
    {
        Wanted[I].SetLocation(Elbow+ForeDeform.RotateVector(Rest[I].GetLocation()-Rest[Lower].GetLocation())*Scale);
        // Real V7 weights: aux spans the elbow, twist_02 the mid forearm and
        // twist_01 the wrist. The unweighted main bone carries the full frame.
        const float Mix=I==Aux?.5f:I==Twist02?.88f:1.f;
        const FQuat Driver=FQuat::Slerp(UpperDeform,ForeDeform,Mix).GetNormalized();
        Wanted[I].SetRotation((Driver*Rest[I].GetRotation()).GetNormalized());
    }
    if(MeleeOwnership>UE_SMALL_NUMBER)
    {
        for(int32 I=Clavicle;I<Hand;++I)
        {
            Wanted[I].SetLocation(FMath::Lerp(Wanted[I].GetLocation(),Old[I].GetLocation(),MeleeOwnership));
            Wanted[I].SetRotation(FQuat::Slerp(Wanted[I].GetRotation(),Old[I].GetRotation(),MeleeOwnership).GetNormalized());
        }
    }
    // Rebuild locals from final component poses. The hand and its fingers stay
    // exactly at the authored contact; gun, loader and right arm are untouched.
    for(int32 I=Clavicle;I<=Hand;++I)
    {
        const auto Parent=Output.Pose.GetParentBoneIndex(Indices[I]);
        FTransform ParentPose=Parent.GetInt()==INDEX_NONE?FTransform::Identity:Super90SupportArm::ComponentPose(Output.Pose,Parent);
        for(int32 J=Clavicle;J<=Hand;++J)if(Indices[J]==Parent){ParentPose=Wanted[J];break;}
        Output.Pose[Indices[I]]=Wanted[I].GetRelativeTransform(ParentPose);
        Output.Pose[Indices[I]].NormalizeRotation();
    }
}
