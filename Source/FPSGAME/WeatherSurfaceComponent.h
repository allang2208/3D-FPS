#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "WeatherSurfaceComponent.generated.h"
class UNiagaraSystem;
class UNiagaraComponent;
class UDecalComponent;
class UMaterialInterface;
class UMaterialInstanceDynamic;

USTRUCT()
struct FWeatherSurfacePatch
{
    GENERATED_BODY()
    UPROPERTY() TObjectPtr<UDecalComponent> Decal;
    UPROPERTY() TObjectPtr<UMaterialInstanceDynamic> Material;
    UPROPERTY() TObjectPtr<UNiagaraComponent> Splash;
    FIntPoint Cell = FIntPoint(MAX_int32,MAX_int32);
    FVector Contact = FVector::ZeroVector;
    bool bValid = false;
};

// One bounded local surface pool. All placements are world-space and rain-exposed.
UCLASS()
class FPSGAME_API UWeatherSurfaceComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UWeatherSurfaceComponent();
    void Initialize(UNiagaraSystem* Splashes, UNiagaraSystem* Drips, UMaterialInterface* Material);
    void SetRain(float Value) { Rain = Value; }
    float GetWetness() const { return Wetness; }
    int32 GetPatchCount() const { return Patches.Num(); }
    int32 GetValidPatchCount() const;
    int32 GetTraceCount() const { return LastTraceCount; }
    virtual void TickComponent(float DeltaTime,ELevelTick TickType,FActorComponentTickFunction* ThisTickFunction) override;
    static int32 GetQuality();
private:
    UPROPERTY(Transient) TArray<FWeatherSurfacePatch> Patches;
    UPROPERTY(Transient) TArray<TObjectPtr<UNiagaraComponent>> DripPool;
    UPROPERTY(Transient) TObjectPtr<UNiagaraSystem> SplashAsset;
    UPROPERTY(Transient) TObjectPtr<UMaterialInterface> SurfaceMaterial;
    float Rain = 0;
    float Wetness = 0;
    int32 Cursor = 0;
    int32 LastTraceCount = 0;
    FVector LastFootstep = FVector::ZeroVector;
    bool bHasFootstep = false;
    bool Trace(const FVector& Start,const FVector& End,FHitResult& Hit);
    void Place(FWeatherSurfacePatch& Patch,FIntPoint Cell,const FVector& Camera);
};
