#include "MonsterGroundSupport.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/Volume.h"

FMonsterGroundProbe::FMonsterGroundProbe(const AActor* Owner)
    : Query(SCENE_QUERY_STAT(MonsterTerrainSupport), true, Owner)
{
    Objects.AddObjectTypesToQuery(ECC_WorldStatic);
    Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
    Objects.AddObjectTypesToQuery(ECC_PhysicsBody);
}

bool FMonsterGroundProbe::Trace(UWorld* World, const FVector& Start, const FVector& End,
    const FVector& Up, float MinimumNormalDot, FHitResult& Hit)
{
    // Object multi-traces retain the floor behind rejected units/soft corpses.
    // Complex collision follows the actual treads instead of a movement ramp.
    Hits.Reset();
    World->LineTraceMultiByObjectType(Hits, Start, End, Objects, Query);
    const FHitResult* Best = nullptr;
    for (const FHitResult& Candidate : Hits)
    {
        const auto* Component = Candidate.GetComponent();
        if (!Candidate.bBlockingHit || Candidate.bStartPenetrating || !Component ||
            Cast<APawn>(Candidate.GetActor()) || Cast<AVolume>(Candidate.GetActor()) ||
            Cast<USkinnedMeshComponent>(Component) ||
            Component->GetCollisionResponseToChannel(ECC_Pawn) != ECR_Block ||
            FVector::DotProduct(Candidate.ImpactNormal, Up) < MinimumNormalDot) continue;
        if (!Best || Candidate.Time < Best->Time) Best = &Candidate;
    }
    if (!Best) return false;
    Hit = *Best;
    return true;
}

float MonsterGroundSupport::QueryInterval(const USkeletalMeshComponent* Mesh, float VisibleInterval)
{
    return Mesh && (Mesh->WasRecentlyRendered(.3f) || Mesh->GetNetMode() == NM_DedicatedServer)
        ? VisibleInterval : FMath::Max(.15f, VisibleInterval * 3.f);
}

bool MonsterGroundSupport::FitPlane(TConstArrayView<FVector> Points, const FVector& Pivot,
    float TiltDegrees, float& Height, FQuat& Tilt)
{
    Height = 0.f; Tilt = FQuat::Identity;
    if (Points.IsEmpty()) return false;
    FVector Mean = FVector::ZeroVector;
    for (const FVector& P : Points) Mean += P;
    Mean /= Points.Num();
    if (Points.Num() >= 3 && TiltDegrees > 0.f)
    {
        double XX=0, YY=0, XY=0, XZ=0, YZ=0;
        for (const FVector& P : Points)
        {
            const FVector D=P-Mean;
            XX+=D.X*D.X; YY+=D.Y*D.Y; XY+=D.X*D.Y; XZ+=D.X*D.Z; YZ+=D.Y*D.Z;
        }
        const double Det=XX*YY-XY*XY;
        if (Det > 1.)
        {
            const FVector Normal=FVector(-(XZ*YY-YZ*XY)/Det, -(YZ*XX-XZ*XY)/Det, 1.).GetSafeNormal();
            Tilt=FQuat::FindBetweenNormals(FVector::UpVector, Normal);
            const double Angle=Tilt.GetAngle(), Limit=FMath::DegreesToRadians(TiltDegrees);
            if (Angle>Limit) Tilt=FQuat::Slerp(FQuat::Identity,Tilt,Limit/Angle).GetNormalized();
        }
    }
    const FVector Normal=Tilt.RotateVector(FVector::UpVector);
    Height=Mean.Z-(Normal.X*(Pivot.X-Mean.X)+Normal.Y*(Pivot.Y-Mean.Y))/Normal.Z-Pivot.Z;
    return true;
}
