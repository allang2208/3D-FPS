#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "ColdSteelWarehouseChest.generated.h"
class APawn;
class UWorld;
/**
 * 武器仓库宝箱。2026-09-24 起不再携带模型上方的世界空间名牌：
 * 交互提示统一走准星下小浮窗（ColdSteelWorldInteraction::ResolveInteractionHint）。
 */
UCLASS()
class FPSGAME_API AColdSteelWarehouseChest : public AActor
{
    GENERATED_BODY()
public:
    AColdSteelWarehouseChest();
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;
    bool CanInteract(const APawn* Pawn) const;
    bool IsWithinReach(const APawn* Pawn) const;
    void SetOpen(bool Open);
    bool IsOpen()const{return bIsOpen;}
    bool IsAnimating()const{return bAnimating;}
    /** ---- 储物会话接口：本 Actor 交互时面板绑定的存储容器 ----
     *  默认（空键）＝档案主仓库，既有语义不变；储物箱子类覆写为独立容器键、
     *  容量页数与档位标题，与主仓库共用同一套面板、规则与开合动画逻辑。 */
    virtual FString GetStorageKey()const{return FString();}
    virtual int32 GetStoragePages()const{return 0;}
    virtual FString GetStorageCaption()const{return FString();}
    /** 准星小浮窗正文（无 "E · " 前缀，E 徽标由浮窗自绘）；储物箱子类按档位覆写。 */
    virtual FString GetPromptLabel()const{return FString(TEXT("武器仓库 · 打开仓库面板"));}
    /**
     * 固定生成解算：锚点优先取地图 PlayerStart（与 GameMode 出生规则同一数据源），
     * 位置由关卡与 Content/ColdSteelData/warehouse_assets.json 的 spawn 段决定，
     * 不读取玩家当前站位/视角，因此每次进入游戏落点一致。
     * 没有 PlayerStart 时才退回玩家当前位置（旧口径），并写入 OutSource 说明来源。
     */
    static bool ResolveFixedSpawn(UWorld* World,const APawn* FallbackPawn,FVector& OutLocation,FRotator& OutRotation,FString& OutSource);
    UPROPERTY(EditAnywhere,Category="Warehouse") float InteractionRadius=240;
    UPROPERTY(EditAnywhere,Category="Warehouse") TObjectPtr<class USkeletalMesh> ChestAsset;
    UPROPERTY(EditAnywhere,Category="Warehouse") TObjectPtr<class UAnimSequence> OpenClip;
    UPROPERTY(EditAnywhere,Category="Warehouse") TObjectPtr<class UAnimSequence> CloseClip;
    UPROPERTY(VisibleAnywhere,Category="Warehouse") TObjectPtr<class USkeletalMeshComponent> Mesh;
protected:
    UPROPERTY() TObjectPtr<class UBoxComponent> Collision; // 子类按自身外形调整交互碰撞体
private:
    bool bDesiredOpen=false,bIsOpen=false,bAnimating=false,bPlayingOpen=false;
    float Elapsed=0;
};
