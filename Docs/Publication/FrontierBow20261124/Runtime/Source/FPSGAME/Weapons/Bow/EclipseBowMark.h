#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "EclipseBowMark.generated.h"

// Shared by the physical arrow and all secondary contacts from that release.
struct FEclipseBowShot
{
    static TSharedPtr<FEclipseBowShot> Capture(APawn* Shooter);
    TWeakObjectPtr<APawn> Shooter;
    TSet<TWeakObjectPtr<AActor>> MarkedTargets;
};

struct FEclipseBowImpact
{
    FEclipseBowImpact(FEclipseBowShot* Shot, AActor* Target);
    ~FEclipseBowImpact();
    void Confirm(float Damage);
    static void OnDeath(AActor* Victim);

private:
    static thread_local FEclipseBowImpact* Current;
    FEclipseBowImpact* Previous;
    FEclipseBowShot* Shot;
    AActor* Target;
};

USTRUCT()
struct FEclipseBowMarkState
{
    GENERATED_BODY()
    UPROPERTY() uint8 Layers = 0;
    UPROPERTY() double ExpiresAt = 0.;
};

UCLASS()
class FPSGAME_API UEclipseBowMark : public UActorComponent
{
    GENERATED_BODY()
public:
    UEclipseBowMark();
    static constexpr int32 MaxLayers = 10;
    static constexpr float Duration = 10.f;
    static constexpr float SpreadRadius = 1000.f;
    static double DamageMultiplier(const AActor* Target);
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;

private:
    friend struct FEclipseBowImpact;
    static bool CanMark(AActor* Target, APawn* Shooter);
    static void Add(AActor* Target, APawn* Shooter, int32 Count);
    int32 ActiveLayers() const;
    double Clock() const;
    void Clear();
    void StartGroundAura();
    void UpdateGroundAura();
    void StopGroundAura();
    UPROPERTY(Transient) TObjectPtr<class UMaterialInterface> AuraMaterial;
    UPROPERTY(Transient) TObjectPtr<class UDecalComponent> GroundAura;
    FTimerHandle AuraPlacementTimer;
    UFUNCTION() void OnRep_Mark();
    UPROPERTY(ReplicatedUsing=OnRep_Mark) FEclipseBowMarkState Mark;
    FTimerHandle ExpiryTimer;
    TWeakObjectPtr<APawn> LastShooter;
};
