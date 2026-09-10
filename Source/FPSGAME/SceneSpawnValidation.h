#pragma once
#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "Subsystems/WorldSubsystem.h"
#include "SceneSpawnValidation.generated.h"

UCLASS()
class FPSGAME_API USceneSpawnValidation : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()
public:
    // Uses the same simple Pawn collision that supports the character capsule.
    UFUNCTION(BlueprintCallable, Category="Scene Tests", meta=(WorldContext="WorldContextObject"))
    static bool FindSafeSpawn(UObject* WorldContextObject, FVector NearLocation, FVector& SafeLocation);
    UFUNCTION(BlueprintCallable, Category="Scene Tests", meta=(WorldContext="WorldContextObject"))
    static bool InternalizeTestActors(UObject* WorldContextObject);
};

// Opt-in, headless runtime acceptance; completely inert during normal play.
UCLASS()
class FPSGAME_API USceneSpawnAuditSubsystem : public UWorldSubsystem
{
    GENERATED_BODY()
public:
    virtual void OnWorldBeginPlay(UWorld& World) override;
    virtual void Deinitialize() override;
private:
    void CheckLanding();
    FTimerHandle AuditTimer;
    int32 Samples = 0;
    int32 GroundedSamples = 0;
    bool SawRising = false;
    bool SawFalling = false;
    FVector InitialPosition = FVector::ZeroVector;
};
