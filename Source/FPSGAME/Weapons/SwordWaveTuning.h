#pragma once
#include "CoreMinimal.h"
class UColdSteelEnhancementSystem;
struct FColdSteelItem;

namespace SwordWaveTuning
{
    struct FFlight {float RangeCM=1200.f,SpeedCM=1800.f;};
    // Rift reads the catalog and installed-item overrides. Pan Chi inherits
    // this range, deriving its own rise speed from the requested effect duration.
    FFlight RiftFlight(const UColdSteelEnhancementSystem* Enchant,const FColdSteelItem* Item);
}
