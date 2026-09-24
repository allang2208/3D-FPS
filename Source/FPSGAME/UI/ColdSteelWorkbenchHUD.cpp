#include "ColdSteelHUDWidget.h"
#include "ColdSteelWorkbenchWidget.h"
#include "ColdSteelUIStyle.h"
#include "../Building/VoxelBuildPrefabActor.h"
#include "../Building/VoxelBuildTypes.h"
#include "../Building/VoxelBuildWorld.h"
#include "Blueprint/WidgetTree.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/Button.h"

void UColdSteelHUDWidget::BuildWorkbench(UCanvasPanel* Root)
{
    // 与冶炼面板同一挂载（BuildSmelting）：锚右缘、上下 12px，位置与宽度在 UpdateInventoryLayout 里算；
    // 槽位＝屏幕左缘→面板右缘的全宽命中区，面板本体在内部按推送坐标重排。
    WorkbenchWidget=CreateWidget<UColdSteelWorkbenchWidget>(GetOwningPlayer());
    WorkbenchWidget->Configure(this);
    WorkbenchSlot=Root->AddChildToCanvas(WorkbenchWidget);
    WorkbenchSlot->SetAnchors(FAnchors(1,0,1,1));
    WorkbenchSlot->SetAlignment(FVector2D(1,0));
    WorkbenchSlot->SetOffsets(FMargin(0,ReferenceUnits(12),ReferenceUnits(360),ReferenceUnits(12)));
    WorkbenchSlot->SetZOrder(42);
    WorkbenchWidget->SetVisibility(ESlateVisibility::Collapsed);
}

void UColdSteelHUDWidget::OpenWorkbench(AActor* Workbench)
{
    auto* Piece=Cast<AVoxelBuildPrefabActor>(Workbench);
    auto* World=Piece?Cast<AVoxelBuildWorld>(Piece->GetOwner()):nullptr;
    if(!Piece||Piece->PrefabId()!=VoxelWorkbenchId||!World||!World->HasPrefabAt(Piece->AnchorCell()))return;
    // 工作台 E＝背包＋制作面板一起开（高炉同款生命周期）；打开背包本身永远不带出面板。
    if(bSmeltingOpen)HideSmeltingInstantly();   // 同贴位互斥：瞬收冶炼面板，避免两层叠画
    if(!bInventoryOpen){SetInventoryTab(false);SetInventoryOpen(true);}
    WorkbenchWorld=World;WorkbenchCell=Piece->AnchorCell();
    bWorkbenchOpen=true;bWorkbenchRiding=false;   // 弹出相位：抽屉到位后面板从其左缘滑出
    if(WorkbenchWidget)
    {
        WorkbenchWidget->SetWorkbench(World,WorkbenchCell);
        // 可见性与滑动进度统一由 NativeTick 的 WorkbenchMotion 驱动（与背包抽屉同动画）。
        WorkbenchWidget->SetKeyboardFocus();
    }
}

void UColdSteelHUDWidget::CloseWorkbench()
{
    if(!bWorkbenchOpen)return;
    bWorkbenchOpen=false;
    WorkbenchWorld.Reset();
    // 关闭＝制作栏＋背包一个整体向右缩回（冶炼定稿口径）：立即关抽屉，
    // 面板在 Tick 里与抽屉同一位移曲线刚体骑乘；背包本就开着时面板单独滑出。
    if(bInventoryOpen){bWorkbenchRiding=true;SetInventoryOpen(false);}
    if(bInventoryOpen&&CloseButton)CloseButton->SetKeyboardFocus();
}

void UColdSteelHUDWidget::HideWorkbenchInstantly()
{
    // 互斥瞬收：不播骑乘动画，直接归位收起（两面板共用同一贴位，开另一个前清场）。
    bWorkbenchOpen=false;
    bWorkbenchRiding=false;
    WorkbenchMotion=0.f;
    WorkbenchWorld.Reset();
    if(WorkbenchWidget)
    {
        WorkbenchWidget->SetVisibility(ESlateVisibility::Collapsed);
        WorkbenchWidget->SetRenderTranslation(FVector2D::ZeroVector);
    }
    if(WorkbenchSlot)WorkbenchSlot->SetZOrder(42);
}
