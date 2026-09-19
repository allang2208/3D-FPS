#include "AKMAnimationAuditLibrary.h"
#include "Animation/AnimSequence.h"

void UAKMAnimationAuditLibrary::FinishAnimationCompression(UAnimSequence* Animation)
{
#if WITH_EDITOR
    if(Animation){Animation->CacheDerivedDataForCurrentPlatform();Animation->WaitOnExistingCompression(true);}
#endif
}
