#pragma once
class USkeletalMeshComponent;
struct FHitResult;

namespace M66CorpseSurface
{
// One surface fit for the animated corpse fallback; never alters a simulated corpse.
bool GroundAnimated(USkeletalMeshComponent* Mesh);
// Confirm contact against the actual convex surface when its rotated AABB misses a tread.
bool FindPhysicalSupport(const USkeletalMeshComponent* Mesh,FHitResult& Out);
}
