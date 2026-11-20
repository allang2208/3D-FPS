#pragma once
#include "CoreMinimal.h"
#include "PotionUseMotion.h"

namespace PotionEquipmentHandoff
{
inline constexpr float LowerSeconds=.36f;
inline constexpr float RaiseSeconds=.26f;
inline float Weight(float SourceAge,float UseDuration)
{
    return FPotionUseMotion::Ease((SourceAge+LowerSeconds)/LowerSeconds)*
        (1.f-FPotionUseMotion::Ease((SourceAge-UseDuration)/RaiseSeconds));
}
}
