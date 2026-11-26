#pragma once

#include "CoreMinimal.h"

class AActor;
class UNiagaraComponent;
class UNiagaraSystem;
class UStaticMesh;
class UStaticMeshComponent;
class UMaterialInterface;
class UMaterialInstanceDynamic;
class FJsonObject;

/** Authored local-space cosmetic sites. Never participates in encounters/navigation. */
struct FFacilityAtmosphereSite
{
    FTransform Transform;
    FVector Extent = FVector(120, 60, 18);
    FLinearColor Tint = FLinearColor(.64f, .69f, .72f);
    TWeakObjectPtr<UNiagaraSystem> System;
    TWeakObjectPtr<UStaticMesh> FogMesh;
    TWeakObjectPtr<UMaterialInterface> FogMaterial;
    int32 Module = INDEX_NONE, Kind = 0, Seed = 0;
    float Density = .2f, Rate = 3.f, Distance = 2200.f;
    static FFacilityAtmosphereSite FromJson(const TSharedPtr<FJsonObject>& Spec,
        const FTransform& Room, int32 ModuleIndex, UNiagaraSystem* Asset,
        UStaticMesh* Mesh = nullptr, UMaterialInterface* Material = nullptr);
    bool HasAsset() const { return Kind==0 ? FogMesh.IsValid()&&FogMaterial.IsValid() : System.IsValid(); }
};

/** Eight reusable components per peer: 4 hills-derived fog volumes, 2 steam, 2 dust. */
struct FFacilityAtmosphere
{
    void Install(AActor* Owner, TArray<FFacilityAtmosphereSite>&& InSites);
    void Update(AActor* Owner, const TArray<bool>& WantedRooms, double Now, float Delta);
    void Reset();
private:
    struct FSlot
    {
        TWeakObjectPtr<UNiagaraComponent> FX;
        TWeakObjectPtr<UStaticMeshComponent> Fog;
        TWeakObjectPtr<UMaterialInstanceDynamic> FogMID;
        int32 Site = INDEX_NONE, Kind = 0;
        float Alpha = 0.f, Detail = 0.f;
        double NextBudget = 0;
    };
    TArray<FFacilityAtmosphereSite> Sites;
    TArray<FSlot> Slots;
};
