#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "ColdSteelDoorInteraction.generated.h"

class APawn;
class AActor;
class UFunction;

/**
 * 第三方门资产（Fab Door System，Content/DoorSystem）的接线层。
 *
 * 包里的门是自带逻辑的 Actor 蓝图：交互入口是蓝图接口 `BI_Interact` 的 `OnInteraction`，
 * 部分门另有 `AutoDoorActivated` / `OpenDoor` 之类的自定义事件。它们的参数写的是包自己的
 * 第三人称角色，所以本子系统在需要时生成一个隐藏的「玩家代理」并同步玩家的位置与朝向，
 * 用它充当参数——这样不必逐个改门的蓝图图，也不把包的角色带进玩法。
 */
UCLASS()
class FPSGAME_API UColdSteelDoorInteraction : public UWorldSubsystem
{
    GENERATED_BODY()
public:
    /** 准星命中的 Actor 是否是门：实现 BI_Interact，或带约定的交互入口函数。 */
    static bool IsDoor(const AActor* Target);
    /** 调用门的交互入口；返回是否真的调用了入口，OutMessage 供提示栏播报。 */
    bool TryInteract(AActor* Target, APawn* Player, FString& OutMessage);
private:
    UFunction* FindEntry(AActor* Target) const;
    UObject* ResolvePlayerArgument(UClass* Required, APawn* Player);
    /** 开发用：把一个门类上所有可调用函数名写进日志（每个类一次），便于补入口表。 */
    void LogDoorFunctions(const AActor* Target);
    UPROPERTY(Transient) TObjectPtr<AActor> PlayerProxy;
    /** 代理与日志集合都用原始类指针：UClass 由引擎常驻，不需要 GC 跟踪。 */
    UClass* PlayerProxyClass = nullptr;
    TSet<UClass*> LoggedClasses;
};
