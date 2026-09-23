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
    /** Last value pushed to Wet, so unchanged weather does not touch the MID. */
    float LastPushed=-1.f;
};

/** One wet MID per distinct immutable original, reused across rebinding. */
USTRUCT()
struct FSharedWetMaterial
{
    GENERATED_BODY()
    UPROPERTY(Transient) TObjectPtr<const UMaterialInterface> Original;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> Wet;
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
    /** Wet MIDs are keyed by the original they were copied from, so re-binding a
        slot that uses the same material reuses the instance instead of leaking one. */
    UPROPERTY(Transient) TArray<FSharedWetMaterial> SharedWet;
    UPROPERTY(Transient) TWeakObjectPtr<class AFPSGAMECharacter> BoundPawn;
    TMap<FString,float> WeaponWetness;
    float ScreenWetness=0.f,ActiveWeaponWetness=0.f,BindCountdown=0.f;
    /** Path -> wet material, keyed by the original's object path, built once per pawn. */
    TMap<FName,UMaterialInterface*> WetByPath;
    /** Cached scalar parameter names; FName avoids per-frame string comparison work. */
    static const FName NameWetness;
    static const FName NameScreenWetness;
    static const FName NameStrength;
    static const FName NameAim;
    /** Last values pushed to the lens material, so unchanged weather does not touch it. */
    float LastScreenWetness=-1.f,LastStrength=-1.f,LastAim=-1.f;
    /** Rolling per-second material write counters (see TickComponent). */
    int32 PushedFrame=0,SkippedFrame=0;
    float CounterSeconds=0.f;
    UMaterialInstanceDynamic* AcquireWet(UMaterialInterface* Original,UMaterialInterface* Replacement);
    /** Prunes stale bindings; the full slot scan runs only when bScanAll is set
        (or when a prune invalidated one, to repair a gunsmith swap within a frame). */
    void BindWeapon(class AFPSGAMECharacter* Pawn,bool bScanAll);
    void RestoreMaterials();
};
