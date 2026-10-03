#include "MonsterRecoveryGroundNode.h"
#include "NurseZombie.h"
#include "HumanoidKnockdownComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "PhysicsEngine/PhysicsAsset.h"
#include "PhysicsEngine/SkeletalBodySetup.h"

void FMonsterRecoveryGroundNode::Prepare(const ANurseZombie* Monster)
{
    Alpha=0.f;
    FVector Point,Normal;
    if(!Monster||!Monster->Knockdown||!Monster->Knockdown->GetRecoverySupport(Point,Normal))return;
    auto* Mesh=Monster->GetMesh();auto* Asset=Mesh->GetSkeletalMeshAsset();auto* Physics=Mesh->GetPhysicsAsset();
    if(!Asset||!Physics)return;
    if(PreparedMesh.Get()!=Asset||PreparedPhysics.Get()!=Physics)
    {
        PreparedMesh=Asset;PreparedPhysics=Physics;Samples.Reset();
        const auto& Ref=Asset->GetRefSkeleton();
        for(const auto& Pointer:Physics->SkeletalBodySetups)
        {
            const auto* Body=Pointer.Get();if(!Body)continue;
            const FString Name=Body->BoneName.ToString().ToLower();
            if(!(Name.Contains(TEXT("pelvis"))||Name==TEXT("hips")||Name.Contains(TEXT("spine"))||
                Name.Contains(TEXT("head"))||Name.Contains(TEXT("leg"))||Name.Contains(TEXT("calf"))||
                Name.Contains(TEXT("thigh"))||Name.Contains(TEXT("foot"))||Name.Contains(TEXT("toe"))||
                Name.Contains(TEXT("arm"))||Name.Contains(TEXT("hand"))))continue;
            const int32 Bone=Ref.FindBoneIndex(Body->BoneName);if(Bone==INDEX_NONE)continue;
            auto Add=[&](const FTransform& Frame,const FVector& Local){Samples.Add({Bone,Frame.TransformPosition(Local)});};
            for(const auto& Box:Body->AggGeom.BoxElems)
                for(int32 X:{-1,1})for(int32 Y:{-1,1})for(int32 Z:{-1,1})
                    Add(Box.GetTransform(),FVector(Box.X*X,Box.Y*Y,Box.Z*Z)*.5f);
            for(const auto& Sphere:Body->AggGeom.SphereElems)
                for(int32 Axis=0;Axis<3;++Axis)for(int32 Sign:{-1,1})
                {FVector Direction=FVector::ZeroVector;Direction[Axis]=Sphere.Radius*Sign;Add(Sphere.GetTransform(),Direction);}
            for(const auto& Capsule:Body->AggGeom.SphylElems)
                for(int32 End:{-1,1})for(int32 Axis=0;Axis<3;++Axis)for(int32 Sign:{-1,1})
                {FVector Local(0,0,Capsule.Length*.5f*End);Local[Axis]+=Capsule.Radius*Sign;Add(Capsule.GetTransform(),Local);}
            for(const auto& Convex:Body->AggGeom.ConvexElems)
            {
                const int32 Step=FMath::Max(1,FMath::DivideAndRoundUp(Convex.VertexData.Num(),32));
                for(int32 I=0;I<Convex.VertexData.Num();I+=Step)Add(Convex.GetTransform(),Convex.VertexData[I]);
            }
        }
    }
    const FTransform Frame=Mesh->GetComponentTransform();
    FloorPoint=Frame.InverseTransformPosition(Point);
    FloorNormal=(Frame.InverseTransformVectorNoScale(Normal)*Frame.GetScale3D()).GetSafeNormal();
    WorldUp=Frame.InverseTransformVectorNoScale(FVector::UpVector).GetSafeNormal();
    Scale=FMath::Max(.01f,float(Frame.GetScale3D().GetAbsMax()));
    Alpha=1.f;
}

void FMonsterRecoveryGroundNode::EvaluateSkeletalControl_AnyThread(FComponentSpacePoseContext& Output,TArray<FBoneTransform>& Out)
{
    const auto& Bones=Output.Pose.GetPose().GetBoneContainer();
    double Gap=TNumericLimits<double>::Max();
    for(const auto& Sample:Samples)
    {
        const auto Bone=Bones.MakeCompactPoseIndex(FMeshPoseBoneIndex(Sample.Bone));
        if(Bone==INDEX_NONE)continue;
        const FVector Point=Output.Pose.GetComponentSpaceTransform(Bone).TransformPosition(Sample.Point);
        Gap=FMath::Min(Gap,FVector::DotProduct(Point-FloorPoint,FloorNormal)-.5/Scale);
    }
    if(Gap==TNumericLimits<double>::Max())return;
    // Preserve every limb rotation and the snapshot blend. Only the final
    // body's vertical support moves; no foot locks, traces or UObject reads.
    FTransform Root=Output.Pose.GetComponentSpaceTransform(FCompactPoseBoneIndex(0));
    Root.AddToTranslation(WorldUp*FMath::Clamp(-Gap/FMath::Max(.2,FVector::DotProduct(WorldUp,FloorNormal)),
        -45./Scale,15./Scale));
    Out.Emplace(FCompactPoseBoneIndex(0),Root);
}
