#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "CampfireSharedTypes.h"
#include "ColdSteelCampfire.generated.h"

class APawn;
class UNiagaraComponent;
class UNiagaraSystem;
class UPointLightComponent;
class USphereComponent;
class UStaticMeshComponent;
class AVoxelBuildWorld;
class APlayerController;

/** Buildable campfire. Warmth is queried by the authoritative survival clock, never saved as a buff. */
UCLASS()
class FPSGAME_API AColdSteelCampfire : public AActor
{
    GENERATED_BODY()
public:
    AColdSteelCampfire();
    static constexpr float WarmthRadiusCm=500.f;
    static constexpr float ConsumptionMultiplier=.5f;
    static float ConsumptionMultiplierAt(const APawn* Player);
    bool IsProvidingWarmth() const;
    bool HasPresentation() const { return Flame!=nullptr; }
    /** Shared fluid scheduler owns distance and world instance budgets. */
    void SetPresentationActive(bool bActive);
    void Extinguish();
    /** Fuel is owned by the existing building save; only on/off is replicated for presentation. */
    void SetFuelSeconds(double Seconds);
    bool ResolveStation(AVoxelBuildWorld*& World,FIntVector& Cell) const;
    bool CanOperate(const APlayerController* Player) const;
    bool IsAvailable() const { return !bExtinguished&&!IsActorBeingDestroyed(); }
    void PublishSharedState(bool Force=false);
    const FCampfireSharedState& SharedState() const { return Shared; }
    double DisplayFuel() const;
    double DisplayProgress() const;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    UPROPERTY(Replicated) FCampfireSharedState Shared;
    double LastSharedPublish=-100;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> Body;
    UPROPERTY() TObjectPtr<USphereComponent> WarmthQuery;
    UPROPERTY() TObjectPtr<UNiagaraSystem> FlameSystem;
    UPROPERTY(Transient) TObjectPtr<UNiagaraComponent> Flame;
    UPROPERTY(Transient) TObjectPtr<UPointLightComponent> FireLight;
    UPROPERTY(ReplicatedUsing=OnRep_Extinguished) bool bExtinguished=false;
    int64 FuelUntilTicks=0;
    UPROPERTY(ReplicatedUsing=OnRep_Fuel) bool bFuelBurning=false;
    UFUNCTION() void OnRep_Fuel();
    UFUNCTION() void OnRep_Extinguished();
};
