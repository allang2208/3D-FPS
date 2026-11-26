#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "Engine/DataAsset.h"
#include "WeatherViewEffectsComponent.generated.h"

class UMaterialInterface;
class UMaterialInstanceDynamic;
class UMeshComponent;
struct FStreamableHandle;

/** Generated from existing licensed materials; holds cook-visible references. */
UCLASS(BlueprintType)
class FPSGAME_API UWeatherPresentationAssets : public UDataAsset
{
    GENERATED_BODY()
public:
    UPROPERTY(EditAnywhere) TMap<FString,TObjectPtr<UMaterialInterface>> WetMaterials;
    /** Runtime routing asset uses only soft references; legacy author catalogs
        retain WetMaterials for compatibility and never load during play. */
    UPROPERTY(EditAnywhere) TMap<FName,TSoftObjectPtr<UMaterialInterface>> WetMaterialPaths;
};

USTRUCT()
struct FWeatherLoadedMaterial
{
    GENERATED_BODY()
    UPROPERTY(Transient) TObjectPtr<UMaterialInterface> Material;
    double LastUsedAt=0.;
};

USTRUCT()
struct FWeatherViewMaterial
{
    GENERATED_BODY()
    UPROPERTY() TWeakObjectPtr<class AFPSGAMECharacter> Pawn;
    UPROPERTY() TWeakObjectPtr<class UWeaponWeatherStateComponent> State;
    UPROPERTY() TWeakObjectPtr<UMeshComponent> Mesh;
    UPROPERTY() TWeakObjectPtr<UObject> MeshAsset;
    UPROPERTY() TObjectPtr<UMaterialInterface> Original;
    UPROPERTY() TObjectPtr<UMaterialInstanceDynamic> Wet;
    int32 Slot=0;
    uint8 Hand=0;
    FString Instance;
    FSoftObjectPath TargetPath;
};

/** Immutable originals may share a MID only within the same player's hand. */
USTRUCT()
struct FSharedWetMaterial
{
    GENERATED_BODY()
    UPROPERTY(Transient) TWeakObjectPtr<class AFPSGAMECharacter> Pawn;
    uint8 Hand=0;
    UPROPERTY(Transient) TObjectPtr<const UMaterialInterface> Original;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> Wet;
};

/** Presents replicated per-item wetness for local and remote equipped weapons.
    Rain/screen visuals moved to Ultra Dynamic Weather; this component keeps the
    weapon wet-material swap driven by the manager's gameplay rain values. */
UCLASS()
class FPSGAME_API UWeatherViewEffectsComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UWeatherViewEffectsComponent();
    void Initialize();
    virtual void TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    float GetWeaponWetness() const { return ActiveWeaponWetness; }
    int32 GetWetMaterialCount() const { return Bindings.Num(); }
private:
    UPROPERTY(Transient) TObjectPtr<UWeatherPresentationAssets> Routing;
    UPROPERTY(Transient) TMap<FSoftObjectPath,FWeatherLoadedMaterial> Materials;
    UPROPERTY(Transient) TArray<FWeatherViewMaterial> Bindings;
    UPROPERTY(Transient) TArray<FSharedWetMaterial> SharedWet;
    TMap<TWeakObjectPtr<UMaterialInstanceDynamic>,float> LastPushed;
    float ActiveWeaponWetness=0.f,BindCountdown=0.f;
    bool bInitialized=false;
    TSet<FSoftObjectPath> WantedMaterials,FailedMaterials;
    TArray<FSoftObjectPath> LoadingMaterials;
    TSharedPtr<FStreamableHandle> RoutingLoad;
    TSharedPtr<FStreamableHandle> MaterialLoad;
    void FinishRoutingLoad();
    void StartMaterialLoad();
    void FinishMaterialLoad();
    UMaterialInterface* ResolveWet(UMaterialInterface* Original);
    UMaterialInstanceDynamic* AcquireWet(class AFPSGAMECharacter* Pawn,uint8 Hand,UMaterialInterface* Original,UMaterialInterface* Replacement);
    void BindWeapons(bool bScanAll);
    void RestoreMaterials();
};
