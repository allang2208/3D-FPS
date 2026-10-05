#include "LurkerM08Monster.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/World.h"

bool ALurkerM08Monster::HasHuntingSight(const APawn* Victim) const
{
    if (!IsValid(Victim) || !GetWorld()) return false;
    float Radius, HalfHeight;
    Victim->GetSimpleCollisionCylinder(Radius, HalfHeight);
    const FVector Targets[] = {Victim->GetActorLocation(),
        Victim->GetActorLocation() + FVector::UpVector * HalfHeight * .55f};
    // Use actual anatomy on floors and walls. The low capsule centre alone
    // loses a standing player behind steps/railings and ignores the tall arch.
    const FVector Origins[] = {GetMesh()->GetSocketLocation(TEXT("head")),
        GetMesh()->GetSocketLocation(TEXT("arch_crown")) - GetActorUpVector() * 12.f};
    FCollisionQueryParams Query(SCENE_QUERY_STAT(M08HuntingSight), false, this);
    Query.AddIgnoredActor(Victim);
    for (const FVector Origin : Origins)
        for (const FVector SightPoint : Targets)
        {
            FHitResult Hit;
            if (!GetWorld()->LineTraceSingleByChannel(Hit, Origin, SightPoint, ECC_Visibility, Query)) return true;
        }
    return false;
}
