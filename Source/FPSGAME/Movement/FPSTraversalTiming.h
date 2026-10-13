#pragma once
#include "CoreMinimal.h"

namespace FPSTraversalTiming
{
// Both the native FPS rig and the retargeted body sample these same three
// phases. Runtime duration may compress recovery without freezing either rig.
inline float Sample(float Progress,float ContactFraction,float ReleaseFraction,
    float SourceContact,float SourceRelease,float SourceEnd)
{
    const float P=FMath::Clamp(Progress,0.f,1.f);
    const float Hit=FMath::Clamp(ContactFraction,.01f,.98f);
    const float LetGo=FMath::Clamp(ReleaseFraction,Hit+.001f,.99f);
    return P<Hit?FMath::Lerp(0.f,SourceContact,P/Hit):P<LetGo?
        FMath::Lerp(SourceContact,SourceRelease,(P-Hit)/(LetGo-Hit)):
        FMath::Lerp(SourceRelease,SourceEnd,(P-LetGo)/(1.f-LetGo));
}
}
