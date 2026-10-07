#pragma once

#include "CoreMinimal.h"
#include "ColdSteelDoor.h"
#include "ColdSteelContactDoor.generated.h"

class UBoxComponent;

/**
 * 铁门（撞开）：身体走到门口就开门的原生门。
 *
 * 取代调色板旧条目 door_physics 挂的 Fab 物理门（BP_PhysicsDoor）：
 *  1. 透缝——物理门沿用包自带 SM_Door/SM_DoorFrame（框宽 113.99 vs 占格 120），与本工程 120 cm
 *     补缝口径不一致；本类沿用原生门的补缝网格（SM_SingleDoorFrame_D40 族），透缝随之消除；
 *  2. 联机——包物理门不复制；本类继承 AColdSteelDoor 的开合复制与服务器权威开关，远端玩家可见。
 *
 * 接触判定：门口的薄触发盒在**服务器**上检测玩家 Pawn 走入（含远端玩家），视为“撞门”；
 * 只对玩家生效——怪物撞门不开（守家口径，2026-10-04）。E 键照常可开关（继承原生门入口）。
 * 开门仍走 OpenDoorFrom：两侧摆动空间都被实体挡住时拒绝开门（与所有原生门同一口径）。
 */
UCLASS()
class FPSGAME_API AColdSteelContactDoor : public AColdSteelDoor
{
    GENERATED_BODY()
public:
    AColdSteelContactDoor();
protected:
    virtual void BeginPlay() override;
private:
    UFUNCTION()
    void HandleContact(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor,
        UPrimitiveComponent* OtherComp, int32 OtherBodyIndex, bool bFromSweep, const FHitResult& SweepResult);
    /** 门口接触触发区：比门洞略宽略深，玩家贴到门板就触发。 */
    UPROPERTY(VisibleAnywhere, Category="Door") TObjectPtr<UBoxComponent> ContactZone;
};
