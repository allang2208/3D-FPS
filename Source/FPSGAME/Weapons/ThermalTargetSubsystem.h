#pragma once
#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "ThermalTargetSubsystem.generated.h"

class UCameraComponent;
class UPrimitiveComponent;
class UMonsterCombatComponent;
class UMaterialInterface;
class UStaticMesh;
struct FStreamableHandle;

// Explicit source registration; no world actor enumeration or material guessing.
// Only local ADS creates depth-only proxies. They never replace source materials.
UCLASS()
class FPSGAME_API UThermalTargetSubsystem : public UWorldSubsystem
{
    GENERATED_BODY()
public:
    virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    virtual void Deinitialize() override;
    void RegisterMonster(UMonsterCombatComponent* Combat);
    static void RegisterFire(UPrimitiveComponent* Source, FVector Extent, FVector Offset=FVector::ZeroVector,float Duration=-1.f);
    void SetViewer(UCameraComponent* Camera,bool Active);
private:
    struct FTarget
    {
        TWeakObjectPtr<UPrimitiveComponent> Source;
        TWeakObjectPtr<UMonsterCombatComponent> Combat;
        TWeakObjectPtr<UPrimitiveComponent> Proxy;
        FVector Extent=FVector::ZeroVector,Offset=FVector::ZeroVector;
        bool Fire=false;
        double Expires=-1.;
    };
    TArray<FTarget> Targets;
    TSet<TWeakObjectPtr<UCameraComponent>> Viewers;
    TSharedPtr<FStreamableHandle> Resources;
    UPROPERTY(Transient) TObjectPtr<UStaticMesh> HeatMesh;
    UPROPERTY(Transient) TObjectPtr<UMaterialInterface> BodyMaterial;
    UPROPERTY(Transient) TObjectPtr<UMaterialInterface> FireMaterial;
    FTimerHandle RefreshTimer;
    void Refresh();
    void Release(FTarget& Target);
    void CreateProxy(FTarget& Target);
};
