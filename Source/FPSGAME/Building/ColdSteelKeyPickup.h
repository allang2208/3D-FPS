#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "ColdSteelKeyPickup.generated.h"

class UBoxComponent;
class UStaticMeshComponent;

/**
 * 门钥匙拾取物：玩家走入触发范围即在角色钥匙环上登记钥匙（会话内有效）并消失。
 * 与 AColdSteelKeyDoor 按 KeyId 匹配；作为建造调色板的逻辑构件放置（存档重进世界会重新生成，
 * 与键门“本次会话内解锁”的口径一致——钥匙与门都不跨运行记状态）。
 * 外观为引擎基本体拼的小钥匙（本工程暂无钥匙网格），悬空慢转便于在环境里辨认。
 */
UCLASS()
class FPSGAME_API AColdSteelKeyPickup : public AActor
{
    GENERATED_BODY()
public:
    AColdSteelKeyPickup();
    virtual void Tick(float DeltaSeconds) override;
    UFUNCTION(BlueprintPure, Category="Key") bool IsTaken() const { return bTaken; }
protected:
    virtual void BeginPlay() override;
private:
    UFUNCTION()
    void HandleContact(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor,
        UPrimitiveComponent* OtherComp, int32 OtherBodyIndex, bool bFromSweep, const FHitResult& SweepResult);
    /** 用基本体拼一把小钥匙：柄头 + 柄杆 + 两个齿。 */
    UStaticMeshComponent* MakeKeyPart(FName Name, const FVector& Extent, const FVector& Location) const;
    UPROPERTY(VisibleAnywhere) TObjectPtr<USceneComponent> KeyRoot;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UBoxComponent> ContactZone;
    UPROPERTY(EditAnywhere, Category="Key") FName KeyId = TEXT("door_key");
    bool bTaken = false;
};
