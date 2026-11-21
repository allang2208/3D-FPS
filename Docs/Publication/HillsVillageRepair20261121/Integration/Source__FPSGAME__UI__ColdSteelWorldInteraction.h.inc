// Source/FPSGAME/UI/ColdSteelWorldInteraction.h
// Merge each excerpt at the named target and scope. Line numbers locate the 2026-11-21 production source.

// Lines 7-7 | class AVillageDefenseSection;
class AVillageDefenseSection;

// Lines 20-20 | class UWorld;
    FUseTargets TraceUseTargets(const APlayerController* Controller,float Reach=250.f,bool bFindNearbyBreach=false);

// Lines 58-60 | class UWorld;
        FString Title;
    };
    FInteractionHint ResolveInteractionHint(const AActor* Target,APawn* Viewer);
