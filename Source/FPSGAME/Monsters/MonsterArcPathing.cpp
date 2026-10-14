#include "MonsterArcPathing.h"
#include "GameFramework/Pawn.h"

void MonsterArcPathing::FillMoveParameters(const APawn* Pawn, const FMonsterArcPathingTuning& Tuning,
    float& ArcStrength, int32& NumMidPoints, EAPSArcMidpointMode& MidpointMode, float& LaneOffset)
{
    MidpointMode = EAPSArcMidpointMode::SmoothCurve;
    NumMidPoints = FMath::Max(Tuning.ArcMidPoints, 0);
    if (!Pawn || FMath::Abs(Tuning.ArcStrength) <= .1f || NumMidPoints <= 0)
    {
        ArcStrength = 0.f;
        NumMidPoints = 0;
        LaneOffset = 0.f;
        return;
    }
    const uint32 Id = Pawn->GetUniqueID();
    const float Sign = (Id & 1) ? 1.f : -1.f;
    const float Jitter = .85f + .3f * FMath::Frac(Id * .6180339f);
    ArcStrength = Sign * Tuning.ArcStrength * Jitter;
    LaneOffset = Sign * Tuning.LaneOffset * Jitter;
}

void MonsterArcPathing::IgnoreCustomPath(FVector const& StartLocation, FVector const& EndLocation,
    TArray<FVector>& OutPath, float ArcStrength, UWorld* World, bool& bUseCustomPath, bool& bFound)
{
    bUseCustomPath = false;
    bFound = false;
}
