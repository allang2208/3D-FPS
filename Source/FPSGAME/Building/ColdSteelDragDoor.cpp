#include "ColdSteelDragDoor.h"

AColdSteelDragDoor::AColdSteelDragDoor()
{
    // 拖拽门不自动关：停在什么角度就保持什么角度。
    AutoCloseSeconds = 0.f;
}

void AColdSteelDragDoor::ToggleDoorFrom(const APawn* InstigatorPawn)
{
    // 按 E（按下）开始摆动：闭着→朝操作者反侧全开；开着（含停在半开）→朝关闭方向回摆。
    // 摆动过程可随时松手（ReleaseDoor 在当前角度冻结），不是一次性开关。
    if(!HasAuthority())return;
    const bool bSwingOut=!bOpen||FMath::IsNearlyEqual(TargetAngle,0.f,.5f);
    if(bSwingOut)
    {
        if(!OpenDoorFrom(InstigatorPawn))return;
    }
    else
    {
        bOpen=false;
        TargetAngle=0.f;
        AutoCloseRemaining=0.f;
        PublishSwing();
        MulticastDoorSound(false);
    }
}

void AColdSteelDragDoor::ReleaseDoor()
{
    // 松手：在当前角度停住（从当前位置重发布开合通道，远端按同钟重放到这里）。
    if(!HasAuthority())return;
    if(FMath::IsNearlyEqual(CurrentAngle,TargetAngle,.5f))return;
    TargetAngle=CurrentAngle;
    PublishSwing();
    UE_LOG(LogTemp,Display,TEXT("ColdSteelDragDoor %s 松手停在 %.1f°"),*GetName(),CurrentAngle);
}
