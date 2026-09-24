#pragma once
#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "Tickable.h"
#include "Styling/SlateBrush.h"
#include "ColdSteelMonsterPortraits.generated.h"

class UDevelopmentSpawnComponent;
class ACharacter;
class USceneCaptureComponent2D;
class UTexture2D;
class UTextureRenderTarget2D;
struct FDevelopmentMonsterEntry;
struct FStreamableHandle;
/** 立绘回读包：只由渲染命令与工作线程读写，游戏线程经原子状态同步。定义在 .cpp。 */
struct FColdSteelPortraitReadback;

DECLARE_MULTICAST_DELEGATE_OneParam(FColdSteelMonsterPortraitReady, const FString&);

/** 图鉴怪物立绘工作室：把怪物 Actor 生成在独立预览场景里，用**固定正交相机**渲染统一视角与朝向。
 *  与背包武器图标（UColdSteelWeaponIcons）同机制——共用异步队列、失败退避、按 Key 缓存与
 *  OnReady 通知，区别只是被摄体是 ACharacter 而非武器网格。
 *  只用于展示：不装备、不改存档、不改变运行中的怪物状态。 */
UCLASS()
class FPSGAME_API UColdSteelMonsterPortraits : public UGameInstanceSubsystem, public FTickableGameObject
{
    GENERATED_BODY()
public:
    virtual void Deinitialize() override;
    virtual void Tick(float DeltaTime) override;
    virtual bool IsTickable() const override { return !Queue.IsEmpty(); }
    virtual TStatId GetStatId() const override { RETURN_QUICK_DECLARE_CYCLE_STAT(UColdSteelMonsterPortraits, STATGROUP_Tickables); }
    virtual UWorld* GetTickableGameObjectWorld() const override { return GetWorld(); }

    /** 该身份是否有可渲染的骨骼网格（截图成功过一次才算可用由 Find 判断，这里只表达「值得排队」）。 */
    static bool Supports(const FDevelopmentMonsterEntry& Entry);
    /** 缓存键：身份 Id。同一身份只渲染一次。 */
    static FString Key(const FDevelopmentMonsterEntry& Entry);

    void Request(const FDevelopmentMonsterEntry& Entry);
    /** 玩家当前正在查看的项：插到队首优先拍，已有的排队项顺序不变。
     *  与 Request 分开，避免「预取」和「玩家要看」抢同一优先级。 */
    void RequestPriority(const FDevelopmentMonsterEntry& Entry);
    const FSlateBrush* Find(const FString& Key) const;
    FColdSteelMonsterPortraitReady OnReady;
    bool IsIdle() const { return Queue.IsEmpty(); }
    int32 RenderCount() const { return Completed; }
    /** 图鉴关闭时调用：停掉队列并释放工作室与渲染目标，空闲期不驻留预览场景。
     *  已缓存的小图保留（1.5MB/张，解耦于工作室），重开面板可立即命中。 */
    void ReleaseIdleResources();

private:
    struct FJob { FString Key; TSoftClassPtr<ACharacter> CharacterClass; double RequestedSeconds = 0.0; double RetryAfterSeconds = 0.0; int32 Attempts = 0; };
    struct FEntry { FSlateBrush Brush; uint64 Use = 0; };

    TArray<FJob> Queue;
    TSet<FString> Pending, Failed;
    mutable TMap<FString, FEntry> Cache;
    mutable uint64 Serial = 0;
    UPROPERTY(Transient) TMap<FString, TObjectPtr<UTexture2D>> Textures;

    /** 正在拍摄的作业下标；延后重试会把作业移到队尾，故不能假定恒为 Queue[0]。 */
    int32 ActiveIndex = 0;
    /** 当前作业正在拍摄的怪物 Actor；随作业切换而销毁重建。 */
    UPROPERTY(Transient) TObjectPtr<ACharacter> Subject;
    UPROPERTY(Transient) TObjectPtr<USceneCaptureComponent2D> Capture;
    UPROPERTY(Transient) TObjectPtr<UTextureRenderTarget2D> Target;
    UPROPERTY(Transient) TArray<TObjectPtr<UMaterialInterface>> CaptureMaterials;
    UPROPERTY(Transient) TArray<TObjectPtr<UTexture>> CaptureTextures;
    TUniquePtr<class FPreviewScene> Studio;
    TSharedPtr<FStreamableHandle> ResourceLoad;
    TArray<FSoftObjectPath> RequiredResources;
    /** 当前回读包；必须按实例持有，不能做成文件级静态，否则多 GameInstance 会互相覆盖。 */
    TSharedPtr<FColdSteelPortraitReadback, ESPMode::ThreadSafe> PendingReadback;
    /** 材质着色器是否编译完成：-2 待提交，-1 就绪，>=0 为第一个未就绪的索引。 */
    TSharedPtr<TAtomic<int32>, ESPMode::ThreadSafe> MaterialStatus;
    int32 ReadinessPolls = 0;
    double WaitStartSeconds = 0.0;

    /** 当前作业的阶段：0 空闲，1 建工作室，2 生成怪物，3 摆姿势取包围盒，4 已提交捕获等待回读。 */
    int32 Stage = 0;
    int32 Completed = 0;
    double AttemptStartSeconds = 0.0;
    /** 同一作业允许的尝试次数：超过才记永久失败。 */
    static constexpr int32 MaxAttempts = 3;
    /** 捕获宽高：立绘用竖构图，与详情卡左栏比例一致。 */
    static constexpr int32 PortraitWidth = 512;
    static constexpr int32 PortraitHeight = 768;

    bool EnsureStudio();
    /** 拆掉工作室／捕获／渲染目标，释放预览场景与 RT 显存。队列清空、被摄体销毁。 */
    void TeardownStudio();
    /** 异步预载怪物类（不阻塞游戏线程）；与武器图标工作室同一策略。
     *  仅登记到本分区的预览用类，不改变怪物资产本身。 */
    void BeginAsyncLoad();
    void ResetAsyncLoad();
    bool SpawnSubject();
    bool PoseAndFrame();
    /** 材质与贴图是否已就绪：未就绪时不能拍，否则会拍到灰模或糊图。返回 true 表示可以拍。 */
    bool SubmitReadiness();
    bool IsTextureReady(class UTexture* Texture) const;
    void BeginReadback();
    void PollReadback();
    void CancelReadback();
    void FinishJob(bool bSuccess);
    /** 首次失败不永久放弃：把队首作业延后重试（首次编译着色器／流送贴图常超过单次超时）。
     *  与武器图标工作室的 DeferCurrentJob/RetryAfterSeconds 同一策略；超过次数上限才记失败。 */
    void DeferCurrentJob(double Now);
    void ResetSubject();
    bool Publish(const FString& KeyValue, const TArray<FColor>& Pixels, int32 Width, int32 Height);
};