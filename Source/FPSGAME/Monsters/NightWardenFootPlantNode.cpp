#include "NightWardenFootPlantNode.h"
#include "NightWardenMonster.h"
#include "MonsterGroundSupport.h"
#include "MonsterCombatComponent.h"
#include "Animation/AnimSequence.h"
#include "Components/SkeletalMeshComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "TwoBoneIK.h"

FNightWardenFootPlantNode::FNightWardenFootPlantNode()
{
    Alpha=1.f;
    Legs[0].Hip.BoneName=TEXT("Bone_010");Legs[0].Knee.BoneName=TEXT("Bone_009");Legs[0].Foot.BoneName=TEXT("Bone_008");
    Legs[1].Hip.BoneName=TEXT("Bone_015");Legs[1].Knee.BoneName=TEXT("Bone_014");Legs[1].Foot.BoneName=TEXT("Bone_013");
}
void FNightWardenFootPlantNode::InitializeBoneReferences(const FBoneContainer& Bones)
{
    for(auto& L:Legs)
    {
        L.Hip.Initialize(Bones);L.Knee.Initialize(Bones);L.Foot.Initialize(Bones);L.Locked=L.Released=false;
        if(!L.Foot.IsValidToEvaluate(Bones))continue;
        auto Index=L.Foot.GetCompactPoseIndex(Bones);FTransform Ref=Bones.GetRefPoseTransform(Index);
        for(auto P=Bones.GetParentBoneIndex(Index);P!=INDEX_NONE;P=Bones.GetParentBoneIndex(P))Ref*=Bones.GetRefPoseTransform(P);
        // V14 barefoot geometry and V18 stance are authored on the z=.3 cm sole plane.
        L.Sole=Ref.InverseTransformPosition(FVector(Ref.GetLocation().X,Ref.GetLocation().Y,.3));
    }
    WasEnabled=false;
}
bool FNightWardenFootPlantNode::IsValidToEvaluate(const USkeleton*,const FBoneContainer& Bones)
{
    for(const auto& L:Legs)if(!L.Hip.IsValidToEvaluate(Bones)||!L.Knee.IsValidToEvaluate(Bones)||!L.Foot.IsValidToEvaluate(Bones))return false;
    return true;
}
void FNightWardenFootPlantNode::Prepare(const ANightWardenMonster* M,float Time,float Weight,float Dt)
{
    if(!M){Enabled=false;return;}
    const auto* Clip=M->WalkClip.Get();auto* Mesh=M->GetMesh();const auto* Move=M->GetCharacterMovement();
    static const FName Curves[]={TEXT("NW_Plant_L"),TEXT("NW_Plant_R")};
    Enabled=Clip&&Weight>.01f&&!M->IsAttacking()&&(!M->Combat||!M->Combat->IsDead())&&!Mesh->IsSimulatingPhysics()&&Move->IsMovingOnGround()&&
        Clip->HasCurveData(Curves[0],false)&&Clip->HasCurveData(Curves[1],false);
    Frame=Mesh->GetComponentTransform();
    if(!Enabled){TraceAge=1.f;return;}
    for(int32 I=0;I<2;++I)Legs[I].Weight=FMath::Clamp(Clip->EvaluateCurveData(Curves[I],FAnimExtractContext(Time,false))*Weight,0.f,1.f);
    TraceAge+=Dt;
    if(TraceAge<MonsterGroundSupport::QueryInterval(Mesh,.05f))return;
    TraceAge=0.f;FMonsterGroundProbe Probe(M);
    for(auto& L:Legs)
    {
        const int32 Bone=Mesh->GetBoneIndex(L.Foot.BoneName);L.Ground=false;if(Bone==INDEX_NONE)continue;
        const FVector Sole=Mesh->GetBoneTransform(Bone).TransformPosition(L.Sole);FHitResult Hit;
        L.Ground=Probe.Trace(M->GetWorld(),Sole+FVector(0,0,35),Sole-FVector(0,0,55),FVector::UpVector,Move->GetWalkableFloorZ(),Hit);
        if(L.Ground){L.Point=Hit.ImpactPoint;L.Normal=Hit.ImpactNormal;}
    }
}
void FNightWardenFootPlantNode::EvaluateSkeletalControl_AnyThread(FComponentSpacePoseContext& Output,TArray<FBoneTransform>& Out)
{
    const bool Reset=!WasEnabled||FVector::DistSquared(Frame.GetLocation(),PreviousFrame.GetLocation())>FMath::Square(80.)||
        Frame.GetRotation().AngularDistance(PreviousFrame.GetRotation())>FMath::DegreesToRadians(45.f);
    PreviousFrame=Frame;WasEnabled=Enabled;
    if(!Enabled||Reset)for(auto& L:Legs){L.Locked=L.Released=false;}
    if(!Enabled)return;
    const auto& Bones=Output.Pose.GetPose().GetBoneContainer();
    for(auto& L:Legs)
    {
        if(!L.Ground||L.Weight<.01f){L.Locked=L.Released=false;continue;}
        // The left stance crosses the loop boundary; only its contact curve
        // releases the anchor, never a global animation-time wrap.
        const auto H=L.Hip.GetCompactPoseIndex(Bones),K=L.Knee.GetCompactPoseIndex(Bones),F=L.Foot.GetCompactPoseIndex(Bones);
        FTransform Hip=Output.Pose.GetComponentSpaceTransform(H),Knee=Output.Pose.GetComponentSpaceTransform(K),Foot=Output.Pose.GetComponentSpaceTransform(F);
        const FTransform WorldFoot=Foot*Frame;const FVector Animated=WorldFoot.TransformPosition(L.Sole);
        if(!L.Locked&&!L.Released)
        {
            L.Anchor=Animated-L.Normal*FVector::DotProduct(Animated-L.Point,L.Normal)+L.Normal*.3;
            L.Rotation=(FQuat::FindBetweenNormals(Frame.GetUnitAxis(EAxis::Z),L.Normal)*WorldFoot.GetRotation()).GetNormalized();
            L.Locked=true;
        }
        if(!L.Locked)continue;
        const FVector SoleGoal=FMath::Lerp(Animated,L.Anchor,L.Weight);
        const FQuat WorldRotation=FQuat::Slerp(WorldFoot.GetRotation(),L.Rotation,L.Weight).GetNormalized();
        const FVector AnkleWorld=SoleGoal-WorldRotation.RotateVector(L.Sole*WorldFoot.GetScale3D());
        const FVector Target=Frame.InverseTransformPosition(AnkleWorld);
        const double Reach=FVector::Distance(Hip.GetLocation(),Knee.GetLocation())+FVector::Distance(Knee.GetLocation(),Foot.GetLocation());
        if(FVector::Distance(Target,Hip.GetLocation())>.985*Reach||WorldFoot.GetRotation().AngularDistance(WorldRotation)>FMath::DegreesToRadians(35.f))
        {L.Locked=false;L.Released=true;continue;}
        const FVector Direction=(Target-Hip.GetLocation()).GetSafeNormal();
        FVector Bend=Knee.GetLocation()-Hip.GetLocation();Bend-=Direction*FVector::DotProduct(Bend,Direction);
        if(Bend.SizeSquared()<.01){Bend=FVector::ForwardVector-Direction*Direction.X;}
        AnimationCore::SolveTwoBoneIK(Hip,Knee,Foot,Hip.GetLocation()+Bend.GetSafeNormal()*Reach,Target,false,1.f,1.f);
        Foot.SetRotation((Frame.GetRotation().Inverse()*WorldRotation).GetNormalized());
        Out.Emplace(H,Hip);Out.Emplace(K,Knee);Out.Emplace(F,Foot);
    }
    Out.Sort([](const FBoneTransform& A,const FBoneTransform& B){return A.BoneIndex.GetInt()<B.BoneIndex.GetInt();});
}
