#include "FPSCastingMeshComponent.h"
#include "FPSFireballComponent.h"
#include "Camera/CameraComponent.h"
#include "Engine/SkeletalMesh.h"
#include "TwoBoneIK.h"

namespace
{
FQuat LimbFrame(const FVector& Direction,const FVector& Plane)
{ return FRotationMatrix::MakeFromXZ(Direction,Plane).ToQuat(); }
}

void UFPSCastingMeshComponent::CacheCastSkeleton()
{
    PoseMesh=GetSkeletalMeshAsset();ReferencePose.Reset();LeftBones.Reset();EntryLocal.Reset();EntrySerial=0;
    CastClavicleIndex=GetBoneIndex(TEXT("clavicle_l"));CastUpperIndex=GetBoneIndex(TEXT("upperarm_l"));CastLowerIndex=GetBoneIndex(TEXT("lowerarm_l"));CastHandIndex=GetBoneIndex(TEXT("hand_l"));
    if(!PoseMesh.IsValid() || CastClavicleIndex==INDEX_NONE || CastUpperIndex==INDEX_NONE || CastLowerIndex==INDEX_NONE || CastHandIndex==INDEX_NONE)return;
    const auto& Ref=PoseMesh->GetRefSkeleton();ReferencePose=Ref.GetRefBonePose();
    for(int32 I=0;I<ReferencePose.Num();++I)
    {
        const int32 Parent=Ref.GetParentIndex(I);
        if(Parent>=0)ReferencePose[I]=ReferencePose[I]*ReferencePose[Parent];
        if((I==CastClavicleIndex || Ref.BoneIsChildOf(I,CastClavicleIndex)) && Ref.GetBoneName(I).ToString().EndsWith(TEXT("_l")))LeftBones.Add(I);
    }
    const int32 Index=GetBoneIndex(TEXT("index_01_l")),Middle=GetBoneIndex(TEXT("middle_01_l")),Pinky=GetBoneIndex(TEXT("pinky_01_l"));
    if(Index==INDEX_NONE || Middle==INDEX_NONE || Pinky==INDEX_NONE){LeftBones.Reset();return;}
    const FVector Origin=ReferencePose[CastHandIndex].GetLocation();
    const FVector Forward=ReferencePose[Middle].GetLocation()-Origin;
    // UE coordinates: index-to-pinky winding points out of the left palm.
    const FVector Normal=(ReferencePose[Index].GetLocation()-Origin)^(ReferencePose[Pinky].GetLocation()-Origin);
    ReferencePalm=FRotationMatrix::MakeFromXZ(Forward,Normal).ToQuat();
}

void UFPSCastingMeshComponent::FinalizeBoneTransform()
{
    if(auto* Magic=bApplyLeftHandCast && GetOwner()?GetOwner()->FindComponentByClass<UFPSFireballComponent>():nullptr)
    {
        if(Magic->IsOccupyingLeftHand() && IsVisible() && !bHiddenInGame)ApplyCastPose(Magic);
        else if(!Magic->IsOccupyingLeftHand()){EntrySerial=0;EntryLocal.Reset();}
    }
    Super::FinalizeBoneTransform();
}

void UFPSCastingMeshComponent::ApplyCastPose(UFPSFireballComponent* Magic)
{
    if(PoseMesh.Get()!=GetSkeletalMeshAsset())CacheCastSkeleton();
    if(LeftBones.IsEmpty())return;
    auto& Pose=GetEditableComponentSpaceTransforms();
    if(Pose.Num()!=ReferencePose.Num())return;
    const auto* Camera=GetOwner()->FindComponentByClass<UCameraComponent>();if(!Camera)return;
    const auto& Ref=PoseMesh->GetRefSkeleton();
    const FTransform MeshWorld=GetComponentTransform(),CameraWorld=Camera->GetComponentTransform();
    const auto ToCamera=[&](const FTransform& Bone){return (Bone*MeshWorld).GetRelativeTransform(CameraWorld);};
    const auto ToMesh=[&](const FVector& Point){return MeshWorld.InverseTransformPosition(CameraWorld.TransformPosition(Point));};
    const FQuat CameraToMesh=MeshWorld.GetRotation().Inverse()*CameraWorld.GetRotation();
    SourcePose=Pose;
    if(EntrySerial!=Magic->GetCastSerial() || EntryLocal.Num()!=Pose.Num())
    {
        EntrySerial=Magic->GetCastSerial();EntryLocal=SourcePose;
        for(int32 I:LeftBones)EntryLocal[I]=SourcePose[I].GetRelativeTransform(SourcePose[Ref.GetParentIndex(I)]);
        Magic->CaptureHandEntry(ToCamera(SourcePose[CastHandIndex]),ToCamera(SourcePose[CastClavicleIndex]),ToCamera(SourcePose[CastUpperIndex]).GetLocation(),ToCamera(SourcePose[CastLowerIndex]).GetLocation());
    }
    const auto& Settings=Magic->HandPose();
    const auto Phase=Magic->GetHandPhase();const float T=Magic->HandPhaseFraction();
    // Bone orientation is reconstructed from palm semantics for each loaded rig.
    const FQuat HandCorrection=ReferencePalm.Inverse()*ReferencePose[CastHandIndex].GetRotation();
    const FTransform CurrentHand=ToCamera(SourcePose[CastHandIndex]);
    const FVector EntryShoulder=Magic->HandEntryShoulder();
    FFireballArmMotion Current;
    Current.Wrist=CurrentHand.GetLocation();Current.Rotation=CurrentHand.GetRotation();
    Current.Shoulder=ToCamera(SourcePose[CastUpperIndex]).GetLocation();Current.Pole=ToCamera(SourcePose[CastLowerIndex]).GetLocation();
    const FFireballArmMotion Motion=Magic->SampleHandMotion(HandCorrection,Current);
    const FVector Wrist=Motion.Wrist,Shoulder=Motion.Shoulder,Pole=Motion.Pole;
    const FQuat HandRotation=Motion.Rotation;
    const float Release=Motion.Palm;
    FVector A=ToMesh(Shoulder);
    const FVector Target=ToMesh(Wrist);
    const FVector RefA=ReferencePose[CastUpperIndex].GetLocation(),RefE=ReferencePose[CastLowerIndex].GetLocation(),RefH=ReferencePose[CastHandIndex].GetLocation();
    const FVector RU=RefE-RefA,RL=RefH-RefE;
    // Translate the shoulder girdle towards an out-of-reach target instead of
    // locking/lengthening the arm. Keep elbow bend on each equipped skeleton.
    const FVector Reach=Target-A;
    const float SupportedReach=(RU.Size()+RL.Size())*.93f;
    if(Reach.Size()>SupportedReach)A+=Reach.GetSafeNormal()*(Reach.Size()-SupportedReach);
    FVector E,H;
    // Constant bone lengths: the elbow follows an outward/downward pole; no scale/stretch.
    AnimationCore::SolveTwoBoneIK(A,A+RU,A+RU+RL,ToMesh(Pole),Target,E,H,RU.Size(),RL.Size(),false,1.,1.);
    const FVector UD=(E-A).GetSafeNormal(),LD=(H-E).GetSafeNormal();
    FVector Plane=(UD^LD).GetSafeNormal();
    if(Plane.IsNearlyZero())Plane=(UD^(ToMesh(Pole)-A)).GetSafeNormal();
    const FVector RefPlane=(RU^RL).GetSafeNormal();
    FTransform UpperPose=ReferencePose[CastUpperIndex],LowerPose=ReferencePose[CastLowerIndex],HandPose=ReferencePose[CastHandIndex];
    UpperPose.SetLocation(A);UpperPose.SetRotation(LimbFrame(UD,Plane)*LimbFrame(RU,RefPlane).Inverse()*ReferencePose[CastUpperIndex].GetRotation());
    LowerPose.SetLocation(E);
    HandPose.SetLocation(H);HandPose.SetRotation(CameraToMesh*HandRotation);
    // Use the same closed forearm solution as RuneSword's supported grasp:
    // inherit palm roll, then swing its forearm axis onto the solved segment.
    // No accumulated +/-180-degree scalar is applied to skinning helpers.
    const FQuat HandDeform=HandPose.GetRotation()*ReferencePose[CastHandIndex].GetRotation().Inverse();
    const FVector AlignedForearm=HandDeform.RotateVector(RL.GetSafeNormal());
    const FQuat ForearmDeform=FQuat::FindBetweenNormals(AlignedForearm,LD)*HandDeform;
    LowerPose.SetRotation((ForearmDeform*ReferencePose[CastLowerIndex].GetRotation()).GetNormalized());
    GoalPose=SourcePose;
    const float LayerBlend=Motion.Layer;
    const FQuat DesiredPalm=HandPose.GetRotation()*ReferencePose[CastHandIndex].GetRotation().Inverse()*ReferencePalm;
    for(int32 I:LeftBones)
    {
        const int32 Parent=Ref.GetParentIndex(I);const FString Name=Ref.GetBoneName(I).ToString();
        const FTransform RestLocal=Ref.GetRefBonePose()[I];
        if(I==CastClavicleIndex)
        {
            const auto& EntryClavicle=Magic->HandEntryClavicle();
            GoalPose[I]=EntryClavicle*CameraWorld;GoalPose[I]=GoalPose[I].GetRelativeTransform(MeshWorld);
            GoalPose[I].SetLocation(A+ToMesh(EntryClavicle.GetLocation())-ToMesh(EntryShoulder));
        }
        else if(I==CastUpperIndex)GoalPose[I]=UpperPose;
        else if(I==CastLowerIndex)GoalPose[I]=LowerPose;
        else if(I==CastHandIndex)GoalPose[I]=HandPose;
        else
        {
            GoalPose[I]=RestLocal*GoalPose[Parent];
            // Both upper/lower-arm helpers retain their complete rest-local
            // transform and follow their segment as a rigid group. Fractional
            // roll against a fully rolled parent pinched this mesh during cast.
            for(const auto& Digit:Settings.Digits)
            {
                if(!Name.StartsWith(Digit.Key.ToString()+TEXT("_")) || Name.Contains(TEXT("metacarpal")))continue;
                const int32 Segment=FCString::Atoi(*Name.Mid(Digit.Key.ToString().Len()+1,2))-1;
                if(Segment<0 || Segment>2)break;
                const int32 Next=GetBoneIndex(FName(*FString::Printf(TEXT("%s_%02d_l"),*Digit.Key.ToString(),Segment+2)));
                FVector RefDirection;
                if(Next!=INDEX_NONE)RefDirection=ReferencePose[Next].GetLocation()-ReferencePose[I].GetLocation();
                else
                {
                    const FVector ParentAxis=ReferencePose[Parent].GetRotation().UnrotateVector(ReferencePose[I].GetLocation()-ReferencePose[Parent].GetLocation());
                    RefDirection=ReferencePose[I].GetRotation().RotateVector(ParentAxis);
                }
                const float Spread=FMath::DegreesToRadians(Digit.Value.Spread[Segment]);
                const float Flex=FMath::DegreesToRadians(FMath::Lerp(Digit.Value.GatherFlex[Segment],Digit.Value.ReleaseFlex[Segment],Release));
                const FVector Direction=DesiredPalm.RotateVector(FVector(FMath::Cos(Flex)*FMath::Cos(Spread),FMath::Cos(Flex)*FMath::Sin(Spread),FMath::Sin(Flex)));
                const FQuat OpenRotation=LimbFrame(Direction,DesiredPalm.GetAxisZ())*LimbFrame(RefDirection,ReferencePalm.GetAxisZ()).Inverse()*ReferencePose[I].GetRotation();
                const FQuat OpenLocal=GoalPose[Parent].GetRotation().Inverse()*OpenRotation;
                const float FingerBlend=FireballCastMotion::FingerWeight(Motion.Fingers,Digit.Key,Segment);
                const FQuat Local=FQuat::Slerp(EntryLocal[I].GetRotation(),OpenLocal,FingerBlend);
                GoalPose[I].SetRotation(GoalPose[Parent].GetRotation()*Local);
                break;
            }
        }
    }
    // Blend in local space so intermediate arm/finger segments retain their lengths.
    for(int32 I:LeftBones)
    {
        const int32 Parent=Ref.GetParentIndex(I);
        FTransform Local=EntryLocal[I];
        if(Phase==EFireballHandPhase::Recovering)
            Local.BlendWith(SourcePose[I].GetRelativeTransform(SourcePose[Parent]),FireballCastMotion::Ease(T));
        const FTransform DesiredLocal=GoalPose[I].GetRelativeTransform(GoalPose[Parent]);
        Local.BlendWith(DesiredLocal,LayerBlend);Pose[I]=Local*Pose[Parent];
    }
}
