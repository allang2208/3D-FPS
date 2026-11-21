#include "VillageDefenseRepairTargets.h"
#include "VillageDefenseSection.h"
#include "VillageDefenseStairs.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"

void UVillageDefenseRepairTargets::Remove(AVillageDefenseSection& Section)
{
    Breaches.Remove(&Section);
}

void UVillageDefenseRepairTargets::Update(AVillageDefenseSection& Section)
{
    if (Section.GetHealth() > 0.f)
    {
        Remove(Section);
        return;
    }

    FBreach Breach;
    const auto* Gate = Cast<AVillageDefenseGate>(&Section);
    auto AddPiece = [&](const UStaticMeshComponent* Part)
    {
        if (!Part || !Part->GetStaticMesh()) return;
        FTransform Local = Part->GetRelativeTransform();
        if (Gate) Local.SetRotation(FQuat::Identity);
        const FBox Bounds = Part->GetStaticMesh()->GetBoundingBox();
        Breach.Pieces.Add({Bounds, Local});
        Breach.LocalBounds += Bounds.TransformBy(Local);
    };
    if(const auto* Stairs=Cast<AVillageDefenseStairs>(&Section))
    {
        TArray<FBox> Treads;
        Stairs->GetRepairBounds(Treads);
        const FTransform& Placement=Stairs->GetMasonry()->GetRelativeTransform();
        for(const FBox& Tread:Treads)
        {
            Breach.Pieces.Add({Tread,Placement});
            Breach.LocalBounds+=Tread.TransformBy(Placement);
        }
    }
    else AddPiece(Section.GetMasonry());
    if (Gate) AddPiece(Gate->GetRightLeaf());
    if (!Breach.Pieces.IsEmpty()) Breaches.Add(&Section, MoveTemp(Breach));
}

AVillageDefenseSection* UVillageDefenseRepairTargets::Trace(const APawn& Pawn, const FVector& Eye,
    const FVector& RayEnd, AVillageDefenseSection** Nearby) const
{
    AVillageDefenseSection* Aimed = nullptr;
    AVillageDefenseSection* Closest = nullptr;
    float BestHit = 1.f;
    double ClosestSq = FMath::Square(Reach);
    const FCollisionQueryParams Sight(SCENE_QUERY_STAT(VillageDefenseRepairSight), false, &Pawn);
    for (const auto& Entry : Breaches)
    {
        auto* Section = Entry.Key.Get();
        const FBreach& Breach = Entry.Value;
        if (!Section || Section->IsActorBeingDestroyed() || Section->ActorHasTag(TEXT("VoxelDetached"))) continue;
        // A replicated prefab carrier can acquire its final location after its broken health arrives.
        const FTransform& SectionPose=Section->GetActorTransform();
        const FVector LocalEye=SectionPose.InverseTransformPosition(Eye);
        const FVector Nearest=SectionPose.TransformPosition(Breach.LocalBounds.GetClosestPointTo(LocalEye));
        if (FVector::DistSquared(Nearest,Eye)>FMath::Square(Reach)) continue;
        for (const FPiece& Piece : Breach.Pieces)
        {
            const FTransform Placement=Piece.RelativePose*SectionPose;
            const FVector Start = Placement.InverseTransformPosition(Eye);
            FVector Hit, Normal;
            float Time = 0.f;
            if (Piece.Bounds.IsInsideOrOn(Start) || FMath::LineExtentBoxIntersection(Piece.Bounds, Start,
                Placement.InverseTransformPosition(RayEnd), FVector::ZeroVector, Hit, Normal, Time))
            {
                // Adjacent bays can share an edge. Use their persistent ids to
                // break a tie identically on the server and the viewing client.
                if ((Time < BestHit && !FMath::IsNearlyEqual(Time,BestHit)) ||
                    (Aimed && FMath::IsNearlyEqual(Time,BestHit) && Section->GetSectionId()<Aimed->GetSectionId()))
                {
                    BestHit = Time;
                    Aimed = Section;
                }
            }
            if (!Nearby || Aimed) continue;
            const FVector Point = Placement.TransformPosition(Piece.Bounds.GetClosestPointTo(Start));
            const double DistSq = FVector::DistSquared(Point, Eye);
            if (DistSq < ClosestSq && !GetWorld()->LineTraceTestByChannel(Eye, Point, ECC_Visibility, Sight))
            {
                Closest = Section;
                ClosestSq = DistSq;
            }
        }
    }
    if (Nearby) *Nearby = Aimed ? Aimed : Closest;
    return Aimed;
}
