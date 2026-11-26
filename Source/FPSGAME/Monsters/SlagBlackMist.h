#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "SlagBlackMist.generated.h"

class USceneComponent;
class UNiagaraComponent;
class UMaterialInterface;

/** Body-born soot which rises in world space with a bounded exposure history. */
UCLASS()
class FPSGAME_API ASlagBlackMist : public AActor
{
    GENERATED_BODY()
public:
    ASlagBlackMist();
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void Tick(float DeltaSeconds) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& Out) const override;
    UPROPERTY(EditAnywhere, ReplicatedUsing=OnRep_Cloud, Category="Slag|Mist") float Radius = 260.f;
    UPROPERTY(EditAnywhere, Replicated, Category="Slag|Mist") float BlindSeconds = 2.f;
    /** Dense retention time before the final 1.5-second dissipation. */
    UPROPERTY(EditAnywhere, ReplicatedUsing=OnRep_Cloud, Category="Slag|Mist") float SmokeLifetime = 8.f;
    UFUNCTION() void OnRep_Cloud();
    void StopEmission();
    bool ContainsExposedEye(const FVector& Eye, const AActor* Player) const;
    static void Gather(UWorld* World, TArray<ASlagBlackMist*>& Out);
    UMaterialInterface* GetBlindViewOverride() const { return BlindViewOverride; }
protected:
    virtual void GetEmissionSources(FVector (&Origins)[4], FVector& Drift) const;
    virtual bool ShouldEmit() const;
    UNiagaraComponent* GetSmokeComponent() const { return Smoke; }
    virtual int32 GetEmissionSourceCount() const { return 3; }
    virtual float GetEmissionRate() const { return 8.f; }
    virtual void CapturePuffFloors(const FVector (&Origins)[4],float (&Floors)[4]) const;
    virtual FVector PuffCenter(const FVector& Origin,const FVector& Drift,float Age,float FloorZ) const;
    virtual float CoreRadiusFraction(float NormalizedAge) const;
protected:
    struct FWakePuff { FVector Origins[4], Drift; float Floors[4]{}; double Born; };
    TArray<FWakePuff, TInlineAllocator<32>> Trail;
    double NextWake = 0.;
    double NextEmissionBudgetUpdate = 0.;
    float CurrentFloors[4]{};
    virtual void UpdateWake();
    virtual double WakeClock() const;
    UPROPERTY(ReplicatedUsing=OnRep_Cloud) bool bEmitting = true;
    UPROPERTY(VisibleAnywhere) TObjectPtr<USceneComponent> Root;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UNiagaraComponent> Smoke;
protected:
    UPROPERTY(EditDefaultsOnly, Category="Slag|Mist") TObjectPtr<UMaterialInterface> BlindViewOverride;
    /** Radius growth clock only; retention, fading and buoyancy keep real age. */
    virtual float GetDiffusionSpeed() const { return 1.f; }
};
