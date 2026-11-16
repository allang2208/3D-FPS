#pragma once
#include "CoreMinimal.h"

namespace FPSBodyMeleeTiming
{
// Gameplay owns contact/recovery. Adapt a donor's markers to that clock on
// both player and AI bodies; rescaling the whole clip moves the visible hit.
inline float ContactSample(float Progress,float Contact,float Release,float Entry,float ContactPose,float ReleasePose)
{
    const float P=FMath::Clamp(Progress,0.f,1.f);
    const float Hit=FMath::Clamp(Contact,.01f,.98f);
    const float Out=FMath::Clamp(Release,Hit+.001f,.99f);
    const float In=FMath::Clamp(Entry,0.f,Hit-.001f);
    return P<=Hit?FMath::Lerp(0.f,ContactPose,FMath::Clamp((P-In)/(Hit-In),0.f,1.f)):
        P<=Out?FMath::Lerp(ContactPose,ReleasePose,(P-Hit)/(Out-Hit)):
        FMath::Lerp(ReleasePose,1.f,(P-Out)/(1.f-Out));
}
}
