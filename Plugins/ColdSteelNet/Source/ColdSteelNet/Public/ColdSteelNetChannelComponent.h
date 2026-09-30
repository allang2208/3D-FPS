#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "UI/ColdSteelInventoryTypes.h"
#include "ColdSteelNetChannelComponent.generated.h"

class UColdSteelStatusModel;
class APlayerController;

/**
 * M2 档案桥：挂在 PlayerController 上（NetGameMode 在 PostLogin 为远端玩家装配）。
 *
 * 客户端（本机控制器）：每 0.8s 心跳上行本机档案快照（ServerSubmitProfile）——
 *   玩家在背包/装备/喝药等所有既有 UI 路径上的改动全部由此同步到服务端。
 * 服务端（权威）：为远端玩家维护影子档案（UColdSteelStatusModel::CreateShadowModel，
 *   目录状态复制自主机单例），应用到服务端 pawn（ApplyColdSteelProfile 全链路生效）；
 *   镜像 MirrorProfile 仅在服务端主动改档时下发（M3 伤害回程等），当前透传模式不回声；
 *   脏档案 20s 节流落盘主机（ColdSteelMP_<玩家键> 槽）。
 */
UCLASS(ClassGroup=(ColdSteelNet))
class COLDSTEELNET_API UColdSteelNetChannelComponent : public UActorComponent
{
    GENERATED_BODY()

public:
    UColdSteelNetChannelComponent();

    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
    virtual void BeginPlay() override;
    virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;

    /** 客户端→服务端：本机档案快照上行（心跳节流）。
     *  FColdSteelProfile 含 TMap 不能直接进 RPC，用与磁盘存档同口径的序列化字节块传输。 */
    UFUNCTION(Server, Reliable)
    void ServerSubmitProfile(const TArray<uint8>& ProfileBlob);

    /** 服务端→客户端：权威镜像（预留 M3 伤害/权威更正回程；透传模式不写）。 */
    UPROPERTY(ReplicatedUsing=OnRep_MirrorBlob)
    TArray<uint8> MirrorBlob;

    UFUNCTION()
    void OnRep_MirrorBlob();

    /** 服务端：影子档案（应用到服务端 pawn 的数据源；主机单例之外每远端玩家一份）。 */
    UPROPERTY(Transient)
    TObjectPtr<UColdSteelStatusModel> ShadowModel;

    /** 服务端：服务端初始化（PostLogin 时机调用）——登记槽名并尝试从主机磁盘载回老档案。 */
    void InitializeGuest(const FString& InSlotName);

private:
    /** 服务端：接收一份客人档案（上行 RPC 与磁盘载回共用）。 */
    void ApplyGuestProfile(const FColdSteelProfile& Profile);
    void ApplyShadowToServerPawn();
    void SaveShadowToHostDisk();

    FString SlotName;
    float ClientHeartbeat = 0.f;
    float ServerSaveTimer = 0.f;
    bool bServerDirty = false;
    /** 复用的序列化载体，避免每次心跳新建对象。 */
    UPROPERTY(Transient)
    TObjectPtr<UColdSteelProfileSave> ScratchSave;
};
