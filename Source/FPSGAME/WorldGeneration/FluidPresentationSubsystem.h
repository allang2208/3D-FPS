#pragma once
#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "FluidPresentationSubsystem.generated.h"

class AFPSWeatherManager;
class ACharacter;
class UNiagaraComponent;
class ULevel;
class UNiagaraSystem;
class UPrimitiveComponent;
class AVoxelBuildPrefabActor;
struct FStreamableHandle;

/** Shared cosmetic scheduling. Never owns damage, projectile collision or hazard decals. */
UCLASS()
class FPSGAME_API UFluidPresentationSubsystem : public UTickableWorldSubsystem
{
    GENERATED_BODY()
public:
    virtual void OnWorldBeginPlay(UWorld& World) override;
    virtual void Deinitialize() override;
    virtual void Tick(float Delta) override;
    virtual bool IsTickable() const override { return bReady; }
    virtual TStatId GetStatId() const override;
    int32 AllocateDetail(const FVector& Position,int32 Requested,bool bImportant=false);
    FVector WindAt(const FVector& Position,float* OutShelter=nullptr);   // OutShelter＝屋檐遮蔽系数（阵风同系数缩放，防雨天下风向不一致）
    void ConfigureSmoke(UNiagaraComponent* FX,int32 Requested,bool bWet=false);
    bool ReserveGeometryQueries(int32 Count,bool bHazard=false);
    bool MoveMist(FVector& Position,FVector& Velocity,const FVector& Previous,float Radius);
    void EmitColdImpact(const FVector& Position,const FVector& Normal);
    void RegisterWaterBody(UPrimitiveComponent* Body);
protected:
    virtual bool DoesSupportWorldType(EWorldType::Type Type) const override;
private:
    struct FWalker
    {
        TWeakObjectPtr<ACharacter> Character;
        FVector Previous=FVector::ZeroVector;
        float Stride=0,Vertical=0;
        bool Initialized=false,Grounded=false,Wet=false;
    };
    struct FShelter { float Factor=0; double Time=-100; };
    struct FSmoke { TWeakObjectPtr<UNiagaraComponent> FX; double Expires=0; int32 Probe=0; bool bOwnWind=false; };
    struct FWaterBody { TWeakObjectPtr<UPrimitiveComponent> Body; FVector Previous=FVector::ZeroVector; double NextHit=0; bool Initialized=false; };
    /** 冶炼中的高炉烟囱黑烟：构件登记驱动，共享风/接触/细节预算；语义同枪口持续烟（Docs/Fluids/furnace-black-smoke-20260924.md）。 */
    struct FFurnaceSmoke
    {
        TWeakObjectPtr<AVoxelBuildPrefabActor> Piece;
        TWeakObjectPtr<UNiagaraComponent> FX;
        float Rate=0;
        double LastSeen=0,NextConfigure=0,LastFeed=-100;
    };
    TArray<FWalker> Walkers;
    TArray<FSmoke> Smoke;
    TArray<FWaterBody> WaterBodies;
    TMap<FIntVector,FShelter> Shelter;
    TWeakObjectPtr<AFPSWeatherManager> Weather;
    FDelegateHandle SpawnHandle,LevelHandle;
    FVector Eye=FVector::ZeroVector;
    float Tokens=72,UpdateClock=0,WindClock=0,DetailRemainder=0;
    double LastBudgetTime=0;
    int32 WalkerCursor=0,RoofQueries=0;
    uint64 RoofFrame=MAX_uint64;
    uint64 GeometryFrame=MAX_uint64;
    int32 CosmeticQueries=0,HazardQueries=0,BodyCursor=0,SmokeCursor=0;
    UPROPERTY() TSoftObjectPtr<UNiagaraSystem> ColdTemplate=TSoftObjectPtr<UNiagaraSystem>(
        FSoftObjectPath(TEXT("/Game/Fluids/FluidPolish20260924/NS_IceImpactMist.NS_IceImpactMist")));
    UPROPERTY(Transient) TArray<TObjectPtr<UNiagaraComponent>> ColdPool;
    TSharedPtr<FStreamableHandle> ColdLoad;
    /** 高炉黑烟（2026-09-24）：工作＝有在炼任务或炉内存料（同 VoxelBuildWorld 护炉谓词），烟从炉顶碗口出。 */
    TArray<FFurnaceSmoke> Furnaces;
    float FurnaceClock=0;
    double FurnaceScanAt=0;   // 1Hz 构件对账（SpawnActor 生成事件早于 Configure 写 Id，不可靠）
    UPROPERTY() TSoftObjectPtr<UNiagaraSystem> FurnaceTemplate=TSoftObjectPtr<UNiagaraSystem>(
        FSoftObjectPath(TEXT("/Game/Fluids/FurnaceSmoke20260924/NS_FurnaceBlackSmoke.NS_FurnaceBlackSmoke")));
    UPROPERTY(Transient) TObjectPtr<UNiagaraSystem> FurnaceAsset;
    TSharedPtr<FStreamableHandle> FurnaceLoad;
    bool bReady=false,bHasView=false;
    void RegisterActor(AActor* Actor);
    void RegisterLevel(ULevel* Level,UWorld* World);
    void UpdateWalker(FWalker& Walker);
    void UpdateSmokeGeometry(FSmoke& Entry,int32 Count);
    void PrepareColdPool();
    void UpdateWaterBody(FWaterBody& Entry);
    void UpdateFurnaceSmoke();
};
