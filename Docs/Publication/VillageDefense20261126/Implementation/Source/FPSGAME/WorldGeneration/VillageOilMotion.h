#pragma once
#include "CoreMinimal.h"

namespace VillageOilMotion
{
    constexpr double Raise=.41, Release=.36, Empty=.84, Finish=1.31;
    // Front edge of the actual hand-pot rim (author_oil.py, r=14 cm).
    inline const FVector Lip(11.58,-7.74,6.58);
    inline double Tip(double Age){return FMath::SmoothStep(.12,.58,Age)*(1.-FMath::SmoothStep(Empty,1.13,Age));}
    inline double Fill(double Age){return 1.-FMath::SmoothStep(Release,Empty,Age);}
}
