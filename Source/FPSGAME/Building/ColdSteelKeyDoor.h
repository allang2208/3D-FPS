#pragma once

#include "CoreMinimal.h"
#include "ColdSteelDoor.h"
#include "ColdSteelKeyDoor.generated.h"

class USoundBase;

/**
 * 键门：上锁的原生门。E 键开门时校验操作者身上的门钥匙环（AFPSGAMECharacter::HasDoorKey）：
 * 有钥匙 → 解锁（本次会话内保持解锁）并照常开门；无钥匙 → 拒绝，门保持锁住。
 * 解锁状态随门的开合复制通道一起复制（远端玩家看到同一把锁）。
 * 锁着的键门在撞门链路里同样拒绝（OpenDoorFrom 统一闸口），准星提示会显示“上锁”。
 */
UCLASS()
class FPSGAME_API AColdSteelKeyDoor : public AColdSteelDoor
{
    GENERATED_BODY()
public:
    AColdSteelKeyDoor();
    virtual bool OpenDoorFrom(const APawn* InstigatorPawn) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
    UFUNCTION(BlueprintPure, Category="Door|Key") bool IsLocked() const { return !bUnlocked; }
    UFUNCTION(BlueprintPure, Category="Door|Key") FName GetKeyId() const { return KeyId; }
protected:
    UFUNCTION() void OnRep_Unlocked();
    /** 上锁拒绝的把手晃动声 / 解锁声（服务器组播）。 */
    UFUNCTION(NetMulticast, Reliable)
    void MulticastKeySound(bool bUnlock);
    UPROPERTY(EditAnywhere, Category="Door|Key") TObjectPtr<USoundBase> UnlockSound;
    UPROPERTY(EditAnywhere, Category="Door|Key") TObjectPtr<USoundBase> LockedSound;
    /** 解锁所需钥匙；与 AColdSteelKeyPickup 发放的钥匙按同一个 FName 匹配。 */
    UPROPERTY(EditAnywhere, Category="Door|Key") FName KeyId = TEXT("door_key");
    /** 解锁后本次会话内不再上锁（门自动关闭仍照常）。 */
    UPROPERTY(ReplicatedUsing=OnRep_Unlocked) bool bUnlocked = false;
};
