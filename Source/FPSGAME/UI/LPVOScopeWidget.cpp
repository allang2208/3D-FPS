#include "LPVOScopeWidget.h"
#include "../FPSGAMECharacter.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "PhysicalScopeScene.inl"

// The widget owns lifecycle only. All gun lenses, optical reticles and thermal
// images render on their original mesh surfaces; combat HUD draws normally.
void ULPVOScopeWidget::NativeConstruct()
{
    Super::NativeConstruct();
    if(!PhysicalScene&&GetOwningPlayer())PhysicalScene=MakeShared<FPhysicalScopeScene>(GetOwningPlayer());
}

void ULPVOScopeWidget::NativeDestruct()
{
    PhysicalScene.Reset();
    Super::NativeDestruct();
}
