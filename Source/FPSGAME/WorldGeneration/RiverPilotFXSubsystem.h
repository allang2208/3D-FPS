#pragma once
#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "TemperateHillsRiver.h"
#include "RiverPilotFXSubsystem.generated.h"

class ATemperateHillsWorld;
class UMaterialInterface;
class UMaterialInstanceDynamic;
class UNiagaraSystem;
class UNiagaraComponent;
class UStaticMeshComponent;
class ULevel;
struct FStreamableHandle;
struct FWaterImpactFootprint;

struct FRegisteredWaterSurface
{
    TWeakObjectPtr<UStaticMeshComponent> Component;
    TWeakObjectPtr<UMaterialInstanceDynamic> Material;
    const FWaterImpactFootprint* Footprint=nullptr;
};

struct FFluidWaterContact
{
    FVector Position=FVector::ZeroVector,Normal=FVector::UpVector;
    TWeakObjectPtr<UMaterialInstanceDynamic> Material;
    float Scale=1,Depth=0;
    bool Static=false;
};

/** Water presentation shared by the full river, fountain basins and dungeon puddles.
 * Legacy class/asset names remain for serialized references. No gameplay collision. */
UCLASS()
class FPSGAME_API URiverPilotFXSubsystem : public UWorldSubsystem
{
    GENERATED_BODY()
public:
    void BindRiver(ATemperateHillsWorld* River,TemperateRiver::FPlanPtr Plan,
        UMaterialInterface* Material,UNiagaraSystem* Splash);
    void UnbindRiver(ATemperateHillsWorld* River);
    UMaterialInterface* GetRiverMaterial() const;
    bool TryBulletCrossing(const FVector& Start,const FVector& End,float SpeedCM);
    bool FindWaterCrossing(const FVector& Start,const FVector& End,FFluidWaterContact& Contact) const;
    bool SampleWater(const FVector& Feet,float MaxDepth,FFluidWaterContact& Contact) const;
    void CharacterWater(const FFluidWaterContact& Contact,const FVector& Velocity,float LandingSpeed,bool bPlayer);
    bool TryFireCrossing(const FVector& Start,const FVector& End,float Radius,bool bMeteor);
    void UpdateWake(AActor* Owner,const FFluidWaterContact& Contact,const FVector& Velocity,float Width);
    bool BodyWater(const FVector& Previous,const FVector& Position,const FVector& Velocity,const FVector& Extent,float Mass);
    bool IsSubmergedRiverbed(const FHitResult& Hit) const;
    void RegisterWaterSurface(UStaticMeshComponent* Component);
    void UnregisterWaterSurface(UStaticMeshComponent* Component);
    /** True when the component is an active water surface. RegisterWaterSurface returns
     *  void and silently refuses components with no impact footprint, so a caller that
     *  must know whether interaction is live needs to ask. */
    bool IsWaterSurfaceRegistered(const UStaticMeshComponent* Component) const;
    virtual void OnWorldBeginPlay(UWorld& InWorld) override;
    virtual void Deinitialize() override;
protected:
    virtual bool DoesSupportWorldType(EWorldType::Type Type) const override;
private:
    static constexpr int32 SplashSlots=12;
    static constexpr int32 RippleSlots=8;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> WaterMID;
    UPROPERTY(Transient) TArray<TObjectPtr<UNiagaraComponent>> SplashPool;
    UPROPERTY(Transient) TArray<TObjectPtr<UNiagaraComponent>> SteamPool;
    UPROPERTY() TSoftObjectPtr<UNiagaraSystem> SteamTemplate=TSoftObjectPtr<UNiagaraSystem>(
        FSoftObjectPath(TEXT("/Game/Fluids/FluidInteractions20260924/NS_WaterImpactSteam.NS_WaterImpactSteam")));
    TSharedPtr<FStreamableHandle> SteamLoad;
    TWeakObjectPtr<ATemperateHillsWorld> OwnerRiver;
    TemperateRiver::FPlanPtr RiverPlan;
    UPROPERTY() TSoftObjectPtr<UNiagaraSystem> ImpactTemplate = TSoftObjectPtr<UNiagaraSystem>(
        FSoftObjectPath(TEXT("/Game/Fluids/RiverPilot20260923/NS_RiverBulletSplash.NS_RiverBulletSplash")));
    TSharedPtr<FStreamableHandle> SplashLoad;
    TArray<FRegisteredWaterSurface> StaticSurfaces;
    TWeakObjectPtr<UMaterialInstanceDynamic> RippleOwners[RippleSlots];
    FDelegateHandle LevelAddedHandle;
    struct FWakeSlot { TWeakObjectPtr<AActor> Owner; TWeakObjectPtr<UMaterialInstanceDynamic> Material; double Time=-100; };
    FWakeSlot Wakes[4];
    void RegisterLevelWater(ULevel* Level,UWorld* World);
    void PrepareSplashPool(UNiagaraSystem* Splash);
    void PrepareSteamPool();
    void EmitWater(const FFluidWaterContact& Contact,float Strength,const FVector& Flow,bool bImportant,float Spread=1.f);
    bool FindStaticCrossing(const FVector& Start,const FVector& End,FVector& Position,
        FVector& Normal,UMaterialInstanceDynamic*& Material,float& Scale) const;
    double LastBudgetTime=0;
    float Tokens=6;
    int32 RippleCursor=0;
};
