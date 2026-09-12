#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "StormCloudComponent.generated.h"

class UVolumetricCloudComponent;
class UMaterialInterface;
class UMaterialInstanceDynamic;
class UMeshComponent;
class ULightComponentBase;

USTRUCT()
struct FStormSkyMesh
{
    GENERATED_BODY()
    UPROPERTY() TWeakObjectPtr<UMeshComponent> Mesh;
    UPROPERTY() TObjectPtr<UMaterialInterface> Original;
    UPROPERTY() TObjectPtr<UMaterialInstanceDynamic> Dynamic;
    float Brightness = 1;
};

// Single-player presentation owned by the weather actor. Reuses one cloud layer;
// all overrides are transient and applied after the existing day/night controller.
UCLASS()
class FPSGAME_API UStormCloudComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UStormCloudComponent();
    virtual void BeginPlay() override;
    virtual void TickComponent(float Delta, ELevelTick Type, FActorComponentTickFunction* Tick) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    float GetStormBlend() const { return Blend; }
    UVolumetricCloudComponent* GetCloud() const { return Cloud.Get(); }
    UPROPERTY(EditDefaultsOnly, Category="Weather|Clouds")
    TSoftObjectPtr<UMaterialInterface> FallbackCloudMaterial;
private:
    UPROPERTY(Transient) TWeakObjectPtr<UVolumetricCloudComponent> Cloud;
    UPROPERTY(Transient) TObjectPtr<UMaterialInterface> OriginalMaterial;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> CloudMaterial;
    UPROPERTY(Transient) TArray<FStormSkyMesh> SkyMeshes;
    struct FLightState
    {
        float Base=0, Applied=-1;
        FLinearColor Disk=FLinearColor::White;
    };
    TMap<TWeakObjectPtr<ULightComponentBase>, FLightState> Lights;
    float Blend=0, DiscoveryTime=0;
    float OriginalBottom=2, OriginalHeight=2, OriginalOcclusion=0;
    float Coverage=0, Density=0, Storm=0;
    FLinearColor Albedo=FLinearColor::White;
    FLinearColor WindControls=FLinearColor(1.f,.32f,.12f,.333333f);
    FLinearColor LayoutPlacement=FLinearColor::Black;
    FVector2D WindOffset=FVector2D::ZeroVector;
    bool bOriginalVisible=false, bCreatedCloud=false, bOverride=false;
    void Discover();
    void Restore();
};
