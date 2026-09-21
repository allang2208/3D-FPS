#include "ColdSteelHUDWidget.h"
#include "ColdSteelStatusModel.h"
#include "../FPSGAMECharacter.h"
#include "Engine/GameInstance.h"

void UColdSteelHUDWidget::OpenAmmoPouch()
{SetInventoryPage(3);SetInventoryOpen(true);}
void UColdSteelHUDWidget::RequestAmmoChange(const FString& WeaponId,const FString& Target)
{
    auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!Model||!Model->CanSwitchAmmo(WeaponId,Target))return;
    SetInventoryOpen(false);
    if(auto* Pawn=GetOwningPlayerPawn<AFPSGAMECharacter>())
        if(!Pawn->StartAmmoSwitch(WeaponId,Target))Model->PostNotice(TEXT("暂时无法切换弹种"),TEXT("请等待当前动作结束"));
}
