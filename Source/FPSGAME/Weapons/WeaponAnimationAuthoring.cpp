#include "WeaponAnimationAuthoring.h"
#include "Animation/AnimSequence.h"
#include "Animation/Skeleton.h"

bool UWeaponAnimationAuthoring::RebindNativeAnimation(UAnimSequence* Sequence, USkeleton* TargetSkeleton)
{
#if WITH_EDITOR
    if (!Sequence || !TargetSkeleton) return false;
    if (Sequence->GetSkeleton() == TargetSkeleton) return true;
    Sequence->Modify();
    // Shared native arms have the same rest pose. Space conversion would rewrite
    // the accepted PKM arm curves; only the skeleton association needs changing.
    const bool Rebound = Sequence->ReplaceSkeleton(TargetSkeleton, false);
    if (Rebound) Sequence->MarkPackageDirty();
    return Rebound;
#else
    return false;
#endif
}
