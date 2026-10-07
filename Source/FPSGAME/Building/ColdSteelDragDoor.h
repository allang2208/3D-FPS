#pragma once

#include "CoreMinimal.h"
#include "ColdSteelDoor.h"
#include "ColdSteelDragDoor.generated.h"

/**
 * 拖拽门：按住 E 门就朝目标侧持续摆动，松手立刻停在当前角度（可停在任意开角）。
 * 语义取代 Fab 包的 BP_DragDoor（物理约束拖拽需要包角色的专用输入，本工程未接）：
 * 服务器权威——按 E 走门组件的 ToggleDoor 通道开始摆动，松开 E 经组件的
 * ServerReleaseDoor 在当前角度冻结；不自动关。停在半开也算“开”（bOpen 随目标方向）。
 */
UCLASS()
class FPSGAME_API AColdSteelDragDoor : public AColdSteelDoor
{
    GENERATED_BODY()
public:
    AColdSteelDragDoor();
    virtual void ToggleDoorFrom(const APawn* InstigatorPawn) override;
    virtual void ReleaseDoor() override;
};
