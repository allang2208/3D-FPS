#pragma once
#include "CoreMinimal.h"
#include "GameFramework/SaveGame.h"
#include "../FPSWeatherManager.h"
#include "HillsNightRaidSave.generated.h"

USTRUCT()
struct FHillsSavedRaider
{
    GENERATED_BODY()
    UPROPERTY() FName Kind=TEXT("nurse");
    UPROPERTY() FTransform Transform;
    UPROPERTY() float Health=0.f;
};

/** Separate WorldId-keyed sidecar: never rewrites terrain, seed or construction saves. */
UCLASS()
class UHillsNightRaidSave : public USaveGame
{
    GENERATED_BODY()
public:
    UPROPERTY() int32 Version=1;
    UPROPERTY() FGuid WorldId;
    UPROPERTY() int32 Seed=0;
    UPROPERTY() FFPSWeatherNetworkState Weather;
    UPROPERTY() bool Night=false;
    UPROPERTY() int32 NightSerial=MIN_int32;
    UPROPERTY() int32 Spawned=0;
    UPROPERTY() int32 WaveRemaining=0;
    UPROPERTY() int32 RandomSeed=0;
    UPROPERTY() float ShrineHealth=1800.f;
    UPROPERTY() float ShrineMaximum=1800.f;
    UPROPERTY() bool PortalActive=false;
    UPROPERTY() bool SiteChosen=false;
    UPROPERTY() FVector PortalSite=FVector::ZeroVector;
    UPROPERTY() FRotator PortalFacing=FRotator::ZeroRotator;
    UPROPERTY() double PortalAge=0.;
    UPROPERTY() double SpawnDelay=0.;
    UPROPERTY() double WaveDelay=0.;
    UPROPERTY() double PortalDelay=0.;
    UPROPERTY() TArray<FHillsSavedRaider> Raiders;
};
