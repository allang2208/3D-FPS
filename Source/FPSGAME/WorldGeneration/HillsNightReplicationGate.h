#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "HillsNightReplicationGate.generated.h"

/** Owner-only readiness acknowledgement; no save state or monster authority. */
UCLASS(NotBlueprintable,Transient)
class FPSGAME_API AHillsNightReplicationGate : public AActor
{
    GENERATED_BODY()
public:
    AHillsNightReplicationGate();
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;
    bool IsPrepared() const {return bPrepared;}
private:
    UFUNCTION(Server,Reliable) void ServerAssetsPrepared();
    bool bPrepared=false;
};
