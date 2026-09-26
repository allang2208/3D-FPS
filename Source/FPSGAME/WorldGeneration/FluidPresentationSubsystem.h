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
class UStaticMeshComponent;
class AVoxelBuildPrefabActor;
class AVoxelBuildWorld;
struct FVoxelSmeltingJob;
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
    /** 冶炼中的高炉烟囱黑烟：构件登记驱动，共享风/接触/细节预算；语义同枪口持续烟（Docs/Fluids/furnace-black-smoke-20260924.md）。
     *  v5（2026-09-25）加连续火力 Heat 与整批完成脉冲的上一拍进度记忆（Docs/Fluids/furnace-smoke-optimization-plan-20260925.md §2）。
     *  2026-09-25 出铁口熔融金属流与凝固锭（Docs/Fluids/furnace-tap-metal-20260925.md）：
     *  同一 5Hz 拍内做完成上升沿判定（复用既有 Job/LiveProgress/JobTotalSeconds 口径，只读）、
     *  金流 NS 组件、锭展示组件，全部走有界池；不新增遍历、不新增容器分配、不写任何玩法状态。 */
    struct FFurnaceSmoke
    {
        TWeakObjectPtr<AVoxelBuildPrefabActor> Piece;
        TWeakObjectPtr<UNiagaraComponent> FX;
        float Rate=0;
        double LastSeen=0,NextConfigure=0,LastFeed=-100;
        /** 上一拍任务累计进度（秒）；-1＝还没有有效读数。跨越整批边界时写 User.Puff，无新事件系统。 */
        double LastProgress=-1;
        /** 整批完成脉冲的起始时刻（GetTimeSeconds）；0／已过期＝无脉冲。 */
        double PuffAt=0;
        /** 上一拍写入的连续火力档（0..1）；降档用，避免每拍重算插值。 */
        float Heat=0;
        // —— 出铁口熔融金属流与凝固锭（2026-09-25，同上案）——
        /** 上一拍「任务在炉且已完成」（UColdSteelSmeltingSystem::IsDone 口径）；上升沿才放出铁。 */
        bool bWasDone=false;
        /** 本次出铁的起始时刻（GetTimeSeconds）；0＝未出铁。t≥1.6s 才展示凝固锭。 */
        double TapAt=0;
        /** 金流 NS 组件（池位，最多 4 座炉同时出铁）；随 Body 变换，注入即衰减，不被动销毁。 */
        TWeakObjectPtr<UNiagaraComponent> TapFX;
        /** 凝固锭展示组件（池位，默认隐藏；展示到任务被取出）。 */
        TWeakObjectPtr<UStaticMeshComponent> Ingot;
        /** 借用的锭池桶位：每炉一个固定桶，避免三个炉子抢同一个池。 */
        int32 IngotSlot=-1;
        /** 上一拍展示的锭定义（MI_<def> 用；bDone 变 false 即清空）。 */
        FString IngotDef;
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
    /** 出铁锭池展示桶位：每炉一个固定桶（0..2，与产出锭模一一对应），-1＝未占用。 */
    int32 IngotSlots[3]={-1,-1,-1};
    UPROPERTY() TSoftObjectPtr<UNiagaraSystem> FurnaceTemplate=TSoftObjectPtr<UNiagaraSystem>(
        FSoftObjectPath(TEXT("/Game/Fluids/FurnaceSmoke20260924/NS_FurnaceBlackSmoke.NS_FurnaceBlackSmoke")));
    UPROPERTY(Transient) TObjectPtr<UNiagaraSystem> FurnaceAsset;
    TSharedPtr<FStreamableHandle> FurnaceLoad;
    /** 出铁口熔融金属流（2026-09-25）：软引用异步预载，未就绪时静默跳过（无同步 Load）。
     *  定名 NS_FurnaceMoltenTap（弃 NS_FurnaceTapMetal）：资产名是发射器名 FurnaceTapMetalFlow
     *  的前缀时，Niagara 编译可复现地出现幻影 SystemUpdateScript Custom Hlsl 报错（valid=0），
     *  逐字节相同内容换名即过；复现探针 Tools/Fluids/probe_tap_name_cache.py。 */
    UPROPERTY() TSoftObjectPtr<UNiagaraSystem> TapTemplate=TSoftObjectPtr<UNiagaraSystem>(
        FSoftObjectPath(TEXT("/Game/Fluids/FurnaceTapMetal20260925/NS_FurnaceMoltenTap.NS_FurnaceMoltenTap")));
    UPROPERTY(Transient) TObjectPtr<UNiagaraSystem> TapAsset;
    TSharedPtr<FStreamableHandle> TapLoad;
    /** 有界池：≤4 座炉同时出铁（设计定稿并发上限），池位不够时本炉这次不出铁。 */
    UPROPERTY(Transient) TArray<TObjectPtr<UNiagaraComponent>> TapPool;
    /** 凝固锭展示组件池：三炉各一个固定桶位（SM_Ingot＋MI_<def>），默认隐藏、无碰撞无物理。 */
    UPROPERTY(Transient) TArray<TObjectPtr<UStaticMeshComponent>> IngotPool;
    /** 四个 MI_<def>Ingot 与 SM_Ingot 的异步批量预载句柄（与 NS 同一次请求）。 */
    TSharedPtr<FStreamableHandle> TapMeshLoad;
    bool bReady=false,bHasView=false;
    void RegisterActor(AActor* Actor);
    void RegisterLevel(ULevel* Level,UWorld* World);
    void UpdateWalker(FWalker& Walker);
    void UpdateSmokeGeometry(FSmoke& Entry,int32 Count);
    void PrepareColdPool();
    void UpdateWaterBody(FWaterBody& Entry);
    void UpdateFurnaceSmoke();
    /** 出铁口熔融金属流与凝固锭（2026-09-25）：完成上升沿触发，全部在既有 5Hz 拍内，只读玩法数据。 */
    void UpdateFurnaceTap(FFurnaceSmoke& Entry,AVoxelBuildWorld* Build,const FVoxelSmeltingJob* Job,
        const UStaticMeshComponent* Body,const FVector& Mouth,bool bDone,double Now);
};
