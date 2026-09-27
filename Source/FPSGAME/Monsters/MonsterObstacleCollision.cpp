#include "MonsterObstacleCollision.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/World.h"
#include "GameFramework/Character.h"
#include "PhysicsEngine/PhysicsAsset.h"
#include "PhysicsEngine/SkeletalBodySetup.h"

namespace MonsterObstacleCollision
{
static FCollisionResponseParams SceneResponses()
{
    FCollisionResponseContainer Responses(ECR_Ignore);
    Responses.SetResponse(ECC_WorldStatic,ECR_Block);
    Responses.SetResponse(ECC_WorldDynamic,ECR_Block);
    return FCollisionResponseParams(Responses);
}

void BuildProbes(const USkeletalMeshComponent* Mesh,TArray<FMonsterObstacleProbe>& Out)
{
    Out.Reset();
    const auto* Asset=Mesh?Mesh->GetPhysicsAsset():nullptr;
    if (!Asset) return;
    for (const USkeletalBodySetup* Body:Asset->SkeletalBodySetups)
    {
        if (!Body || Mesh->GetBoneIndex(Body->BoneName)==INDEX_NONE ||
            Body->BoneName==TEXT("FatZombieRoot") || Body->BoneName==TEXT("Mutant3Root")) continue;
        for (const auto& Sphere:Body->AggGeom.SphereElems)
            Out.Add({Body->BoneName,Sphere.Center,Sphere.Radius});
        for (const auto& Capsule:Body->AggGeom.SphylElems)
        {
            // Three overlapping spheres cover the cylinder as well as its caps.
            const float Radius=FMath::Sqrt(FMath::Square(Capsule.Radius)+FMath::Square(Capsule.Length*.25f));
            for (int32 I=-1;I<=1;++I)
                Out.Add({Body->BoneName,Capsule.Center+Capsule.Rotation.RotateVector(FVector(0,0,I*Capsule.Length*.5f)),Radius});
        }
        for (const auto& Box:Body->AggGeom.BoxElems)
            Out.Add({Body->BoneName,Box.Center,static_cast<float>(FVector(Box.X,Box.Y,Box.Z).Size()*.5f)});
    }
}

FMonsterObstacleSphere TransformProbe(const FMonsterObstacleProbe& Probe,const FTransform& Bone)
{
    return {Bone.TransformPosition(Probe.Center),static_cast<float>(Probe.Radius*Bone.GetScale3D().GetAbsMax())};
}

void WorldPose(const USkeletalMeshComponent* Mesh,const TArray<FMonsterObstacleProbe>& Probes,FMonsterObstaclePose& Out)
{
    Out.Reset(Probes.Num());
    for (const auto& Probe:Probes) Out.Add(TransformProbe(Probe,Mesh->GetSocketTransform(Probe.Bone)));
}

static FVector AboveSupport(const FMonsterObstacleSphere& Sphere,float FloorZ)
{
    // A conservative body envelope must not mistake ordinary floor contact for
    // a wall. Probe above support, retaining the full horizontal body footprint.
    FVector Center=Sphere.Center;
    Center.Z=FMath::Max(Center.Z,double(FloorZ+Sphere.Radius+2.f));
    return Center;
}

bool PoseFits(const ACharacter* Owner,const FMonsterObstaclePose& Pose,float FloorZ)
{
    const FCollisionQueryParams Query(SCENE_QUERY_STAT(MonsterPoseClearance),false,Owner);
    const auto Responses=SceneResponses();
    for (const auto& Sphere:Pose)
        if (Owner->GetWorld()->OverlapBlockingTestByChannel(AboveSupport(Sphere,FloorZ),FQuat::Identity,ECC_Pawn,
            FCollisionShape::MakeSphere(FMath::Max(1.f,Sphere.Radius-1.f)),Query,Responses)) return false;
    return true;
}

bool PathFits(const ACharacter* Owner,const FMonsterObstaclePose& From,const FMonsterObstaclePose& To,float FloorZ)
{
    if (From.Num()!=To.Num()) return false;
    const FCollisionQueryParams Query(SCENE_QUERY_STAT(MonsterPoseSweep),false,Owner);
    const auto Responses=SceneResponses();
    for (int32 I=0;I<From.Num();++I)
    {
        FHitResult Hit;
        const FVector Start=AboveSupport(From[I],FloorZ),End=AboveSupport(To[I],FloorZ);
        if (Owner->GetWorld()->SweepSingleByChannel(Hit,Start,End,FQuat::Identity,ECC_Pawn,
            FCollisionShape::MakeSphere(FMath::Max(1.f,FMath::Max(From[I].Radius,To[I].Radius)-1.f)),Query,Responses) &&
            !(Hit.bStartPenetrating && FVector::DotProduct(End-Start,Hit.Normal)>0.f)) return false;
    }
    return true;
}

float LimitPush(const ACharacter* Owner,const FVector& Delta)
{
    const auto* Mesh=Owner->GetMesh();
    if (!Mesh || Delta.IsNearlyZero()) return 1.f;
    TArray<FMonsterObstacleProbe> Probes;
    BuildProbes(Mesh,Probes);
    const float FloorZ=Owner->GetActorLocation().Z-Owner->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
    const FCollisionQueryParams Query(SCENE_QUERY_STAT(MonsterPushBodySweep),false,Owner);
    const auto Responses=SceneResponses();
    float Fraction=1.f;
    for (const auto& Probe:Probes)
    {
        const auto Sphere=TransformProbe(Probe,Mesh->GetSocketTransform(Probe.Bone));
        const FVector Start=AboveSupport(Sphere,FloorZ);
        FHitResult Hit;
        if (!Owner->GetWorld()->SweepSingleByChannel(Hit,Start,Start+Delta,FQuat::Identity,ECC_Pawn,
            FCollisionShape::MakeSphere(FMath::Max(1.f,Sphere.Radius-1.f)),Query,Responses)) continue;
        // Permit motion out of an existing contact; never drive farther into it.
        if (Hit.bStartPenetrating && FVector::DotProduct(Delta,Hit.Normal)>0.f) continue;
        Fraction=FMath::Min(Fraction,FMath::Max(0.f,Hit.Time-2.f/float(Delta.Size())));
    }
    return Fraction;
}
}
