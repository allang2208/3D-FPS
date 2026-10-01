#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "SlagBlackMist.generated.h"

class USceneComponent;
class UNiagaraComponent;

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
private:
    struct FWakePuff { FVector Origins[3], Drift; double Born; };
    TArray<FWakePuff, TInlineAllocator<32>> Trail;
    double NextWake = 0.;
    void UpdateWake();
    UPROPERTY(ReplicatedUsing=OnRep_Cloud) bool bEmitting = true;
    UPROPERTY(VisibleAnywhere) TObjectPtr<USceneComponent> Root;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UNiagaraComponent> Smoke;
};
