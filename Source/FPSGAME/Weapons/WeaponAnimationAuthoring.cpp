#include "WeaponAnimationAuthoring.h"
#include "Animation/AnimSequence.h"
#include "Animation/Skeleton.h"
#if WITH_EDITOR
#include "Animation/AnimData/IAnimationDataController.h"
#include "Animation/IAnimationSequenceCompiler.h"
#endif

bool UWeaponAnimationAuthoring::FinalizeAuthoredAnimation(UAnimSequence* Sequence)
{
#if WITH_EDITOR
    if(!Sequence)return false;
    UAnimSequence* Sequences[]={Sequence};
    // Duplicating a sequence can leave compression in flight. Complete that
    // request before repopulating, then finish the new authored data before a
    // commandlet saves the package or releases it during shutdown.
    UE::Anim::IAnimSequenceCompilingManager::FinishCompilation(Sequences);
    Sequence->Modify();
    // SetFrameRate changes source keys only. Populated also synchronizes
    // PlatformTargetFrameRate, otherwise compression silently stays at 30 Hz.
    Sequence->GetController().NotifyPopulated();
    UE::Anim::IAnimSequenceCompilingManager::FinishCompilation(Sequences);
    Sequence->MarkPackageDirty();
    return true;
#else
    return false;
#endif
}

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
