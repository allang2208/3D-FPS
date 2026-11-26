#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "StableMarketShowcaseSubsystem.generated.h"

class AActor;
class AFPSWeatherManager;
class AStableRidingHorse;
class UAnimSequence;

/**
 * Displays today's daily market horses inside the East-Gate Stable barn stalls and
 * roaming freely inside the entrance forecourt, using deterministic per-day random
 * allocation, exact walkable ground snapping, and summon fade-in / fade-out transitions.
 */
UCLASS()
class FPSGAME_API UStableMarketShowcaseSubsystem : public UTickableWorldSubsystem
{
    GENERATED_BODY()
public:
    virtual bool ShouldCreateSubsystem(UObject* Outer) const override;
    virtual void Deinitialize() override;
    virtual void Tick(float DeltaTime) override;
    virtual TStatId GetStatId() const override;

    /** Force a showcase refresh (optional debug day override >= 0). */
    void RefreshShowcase(bool bFadeTransition, int32 InDebugDayOverride = INDEX_NONE);

private:
    struct FShowcaseSpot
    {
        FVector LocalFeet = FVector::ZeroVector;
        float LocalYaw = 0.f;
        bool bStall = false;
        bool bFeedingCrib = false;
    };

    bool ResolveStableFrame();
    bool FindWalkableGroundZ(const FVector& WorldRef, bool bStall, double& OutGroundZ) const;
    void LoadClipsIfNeeded();
    void ClearAllShowcase(bool bFadeOut);
    void SetShowcaseSleeping(bool bSleep);
    void ReconcileStock(const FGuid& ProfileId, int32 Day, const TArray<struct FStableHorseOffer>& Offers,
                        const struct FStableMountRoster& Roster, bool bFadeTransition);
    AStableRidingHorse* SpawnShowcaseHorse(const struct FStableHorseOffer& Offer, const FShowcaseSpot& Spot,
                                           FRandomStream& Rng, bool bFadeIn);

    TWeakObjectPtr<AActor> StableAnchor;
    TWeakObjectPtr<AFPSWeatherManager> CachedWeather;
    FTransform VillageToWorld = FTransform::Identity;
    bool bHasStableFrame = false;
    bool bShowcaseSleeping = false;

    FGuid ActiveProfile;
    int32 ActiveDay = INDEX_NONE;
    int32 DebugDayOverride = INDEX_NONE;
    int64 ActiveRosterRevision = -1;
    bool bHasInitializedOnce = false;
    double NextScanTime = 0.;

    UPROPERTY(Transient) TMap<FGuid, TWeakObjectPtr<AStableRidingHorse>> LiveDisplay;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> ClipIdle;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> ClipFeed;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> ClipQIdle;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> ClipQIdleLook;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> ClipQHeadLow;
};
