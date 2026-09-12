#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "Engine/DataAsset.h"
#include "WeatherViewEffectsComponent.generated.h"

class UMaterialInterface;
class UMaterialInstanceDynamic;
class UMeshComponent;
class UPostProcessComponent;
class UNiagaraSystem;

/** Generated from existing licensed materials; holds cook-visible references. */
UCLASS(BlueprintType)
class FPSGAME_API UWeatherPresentationAssets : public UDataAsset
{
    GENERATED_BODY()
public:
    UPROPERTY(EditAnywhere) TObjectPtr<UMaterialInterface> ScreenMaterial;
    UPROPERTY(EditAnywhere) TMap<FString,TObjectPtr<UMaterialInterface>> WetMaterials;
    UPROPERTY(EditAnywhere) TMap<FString,TObjectPtr<UMaterialInterface>> SkyMaterials;
    UPROPERTY(EditAnywhere) TObjectPtr<UNiagaraSystem> Rain;
    UPROPERTY(EditAnywhere) TObjectPtr<UNiagaraSystem> Splashes;
    UPROPERTY(EditAnywhere) TObjectPtr<UNiagaraSystem> Mist;
    UPROPERTY(EditAnywhere) TObjectPtr<UNiagaraSystem> Drips;
    UPROPERTY(EditAnywhere) TObjectPtr<UMaterialInterface> Puddles;
};

USTRUCT()
struct FWeatherViewMaterial
{
    GENERATED_BODY()
    UPROPERTY() TWeakObjectPtr<UMeshComponent> Mesh;
    UPROPERTY() TWeakObjectPtr<UObject> MeshAsset;
    UPROPERTY() TObjectPtr<UMaterialInterface> Original;
    UPROPERTY() TObjectPtr<UMaterialInstanceDynamic> Wet;
    int32 Slot=0;
};

/** Camera water and per-inventory-instance weapon wetness, local presentation only. */
UCLASS()
class FPSGAME_API UWeatherViewEffectsComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UWeatherViewEffectsComponent();
    void Initialize(UWeatherPresentationAssets* InAssets);
    virtual void TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    float GetScreenWetness() const { return ScreenWetness; }
    float GetWeaponWetness() const { return ActiveWeaponWetness; }
    int32 GetWetMaterialCount() const { return Bindings.Num(); }
    UMaterialInstanceDynamic* GetLensMaterial() const { return LensMaterial; }
private:
    UPROPERTY(Transient) TObjectPtr<UWeatherPresentationAssets> Assets;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> LensMaterial;
    UPROPERTY(Transient) TObjectPtr<UPostProcessComponent> PostProcess;
    UPROPERTY(Transient) TArray<FWeatherViewMaterial> Bindings;
    UPROPERTY(Transient) TWeakObjectPtr<class AFPSGAMECharacter> BoundPawn;
    TMap<FString,float> WeaponWetness;
    float ScreenWetness=0.f,ActiveWeaponWetness=0.f,BindCountdown=0.f;
    void BindWeapon(class AFPSGAMECharacter* Pawn);
    void RestoreMaterials();
};
