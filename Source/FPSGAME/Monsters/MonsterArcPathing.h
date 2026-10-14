#pragma once

#include "CoreMinimal.h"
#include "Navigation/APS_MoveToInterface.h"
#include "MonsterArcPathing.generated.h"

class APawn;
class UWorld;

/** Per-monster APS path shaping; sign and magnitude are split per spawned instance. */
USTRUCT(BlueprintType)
struct FMonsterArcPathingTuning
{
    GENERATED_BODY()
    // |strength| > .1 with midpoints > 0 enables the APS arc warp; 0 keeps the stock straight corridor.
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float ArcStrength = .55f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, meta=(ClampMin="0", ClampMax="8")) int32 ArcMidPoints = 3;
    // |offset| >= 180 cm additionally lets APS inject corridor side routes; keep the pilot below that gate.
    UPROPERTY(EditAnywhere, BlueprintReadWrite, meta=(Units="cm")) float LaneOffset = 110.f;
};

namespace MonsterArcPathing
{
    // Applies the deterministic per-instance left/right split from the pawn's spawn id.
    void FillMoveParameters(const APawn* Pawn, const FMonsterArcPathingTuning& Tuning,
        float& ArcStrength, int32& NumMidPoints, EAPSArcMidpointMode& MidpointMode, float& LaneOffset);
    // The pilot reuses engine paths only; reports "no custom path" to the APS override hook.
    void IgnoreCustomPath(FVector const& StartLocation, FVector const& EndLocation, TArray<FVector>& OutPath,
        float ArcStrength, UWorld* World, bool& bUseCustomPath, bool& bFound);
}
