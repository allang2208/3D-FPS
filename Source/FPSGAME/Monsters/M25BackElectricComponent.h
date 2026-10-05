#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "M25BackElectricComponent.generated.h"

class UNiagaraComponent;
class UNiagaraSystem;
class USplineComponent;
class USkeletalMeshComponent;
class UPointLightComponent;
struct FStreamableHandle;

/** Cosmetic electrode discharges. Four reusable lanes; no targeting or damage. */
UCLASS(ClassGroup=(Monsters), meta=(BlueprintSpawnableComponent))
class FPSGAME_API UM25BackElectricComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UM25BackElectricComponent();
    void StopDischarges();
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M25|Electric") bool bElectricEnabled = true;
    UPROPERTY(EditDefaultsOnly, Category="M25|Electric") TSoftObjectPtr<UNiagaraSystem> ArcAsset;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M25|Electric", meta=(ClampMin="0.0", ClampMax="60.0")) float Brightness = 54.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M25|Electric", meta=(ClampMin="0.2", ClampMax="3.0")) float Width = 2.4f;
    UPROPERTY(EditAnywhere, Category="M25|Electric", meta=(ClampMin="500", Units="cm")) float MaxDrawDistance = 5500.f;
protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(EEndPlayReason::Type Reason) override;
    virtual void TickComponent(float Delta, ELevelTick Type, FActorComponentTickFunction* Tick) override;
private:
    static constexpr int32 LaneCount = 4;
    static constexpr int32 PointCount = 13;
    struct FLane
    {
        int32 From = 0, To = 1, Parent = 0;
        float Age = 0.f, Delay = 0.f, Hold = .3f, Fade = .3f, Seed = 0.f, Arch = 20.f, Alpha = 0.f;
        float BranchT = .55f;
        FVector BranchOffset = FVector::ZeroVector;
        FVector Noise[PointCount];
        bool Active = false;
    };
    FLane Lanes[LaneCount];
    FVector Tips[9];
    FName TipNames[9];
    UPROPERTY(Transient) TObjectPtr<USkeletalMeshComponent> Body;
    UPROPERTY(Transient) TObjectPtr<UNiagaraSystem> ArcSystem;
    UPROPERTY(Transient) TArray<TObjectPtr<USplineComponent>> Paths;
    UPROPERTY(Transient) TArray<TObjectPtr<UNiagaraComponent>> Arcs;
    UPROPERTY(Transient) TObjectPtr<UPointLightComponent> BackLight;
    TSharedPtr<FStreamableHandle> LoadHandle;
    FRandomStream Cosmetic;
    bool bVisible = false;
    void CreatePresentation();
    void StartLane(int32 Index, float Distance);
    void UpdatePath(int32 Index);
    void HidePresentation();
    float ViewDistance() const;
};
