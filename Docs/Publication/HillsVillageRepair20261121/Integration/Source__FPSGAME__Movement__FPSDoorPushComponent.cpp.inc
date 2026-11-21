// Source/FPSGAME/Movement/FPSDoorPushComponent.cpp
// Merge each excerpt at the named target and scope. Line numbers locate the 2026-11-21 production source.

// Lines 2-3 | file scope
#include "../WorldGeneration/VillageDefenseSection.h"
#include "../WorldGeneration/HighVillageDefense.h"

// Lines 449-450 | bool UFPSDoorPushComponent::IsNativeDoor(AActor* Target)
        Cast<AColdSteelSlidingDoor>(Target)||Cast<AColdSteelRevolvingDoor>(Target)||Cast<AVillageDefenseGate>(Target)
        ||Cast<AHighVillageGate>(Target));

// Lines 479-480 | void UFPSDoorPushComponent::ServerToggleDoor_Implementation(AActor* Target)
    if(auto* Gate=Cast<AVillageDefenseGate>(Target)){Gate->ToggleDoor();return;}
    if(auto* Gate=Cast<AHighVillageGate>(Target)){Gate->ToggleDoor();return;}
