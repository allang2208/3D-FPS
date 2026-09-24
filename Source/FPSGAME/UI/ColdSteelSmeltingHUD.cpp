#include "ColdSteelHUDWidget.h"
#include "ColdSteelSmeltingWidget.h"
#include "ColdSteelUIStyle.h"
#include "../Building/VoxelBuildPrefabActor.h"
#include "../Building/VoxelBuildWorld.h"
#include "Blueprint/WidgetTree.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/Button.h"

void UColdSteelHUDWidget::BuildSmelting(UCanvasPanel* Root)
{
    // 与仓库侧板同一挂载方式，但锚在右缘：平时贴视口右缘，背包开着时让位贴到抽屉左侧（位置与宽度在 UpdateInventoryLayout 里算）。
    SmeltingWidget=CreateWidget<UColdSteelSmeltingWidget>(GetOwningPlayer());
    SmeltingWidget->Configure(this);
    SmeltingSlot=Root->AddChildToCanvas(SmeltingWidget);
    SmeltingSlot->SetAnchors(FAnchors(1,0,1,1));
    SmeltingSlot->SetAlignment(FVector2D(1,0));
    SmeltingSlot->SetOffsets(FMargin(0,ReferenceUnits(12),ReferenceUnits(360),ReferenceUnits(12)));
    SmeltingSlot->SetZOrder(42);
    SmeltingWidget->SetVisibility(ESlateVisibility::Collapsed);
}

void UColdSteelHUDWidget::OpenSmelting(AActor* Furnace)
{
    auto* Piece=Cast<AVoxelBuildPrefabActor>(Furnace);
    auto* World=Piece?Cast<AVoxelBuildWorld>(Piece->GetOwner()):nullptr;
    if(!Piece||!World||!World->HasPrefabAt(Piece->AnchorCell()))return;
    // 高炉 E＝背包＋面板一起开（2026-09-23 用户澄清）；但打开背包本身永远不带出面板——
    // 面板只在 bSmeltingOpen 时显示，而它只能由这里的 E 交互置真。
    if(bWorkbenchOpen)HideWorkbenchInstantly();   // 与工作台制作面板同贴位互斥：瞬收，避免两层叠画
    if(!bInventoryOpen){SetInventoryTab(false);SetInventoryOpen(true);}
    SmeltingWorld=World;SmeltingCell=Piece->AnchorCell();
    bSmeltingOpen=true;bSmeltRiding=false;   // 弹出相位：抽屉到位后面板从其左缘滑出
    if(SmeltingWidget)
    {
        SmeltingWidget->SetFurnace(World,SmeltingCell);
        // 可见性与滑动进度统一由 NativeTick 的 SmeltMotion 驱动（与背包抽屉同动画，2026-09-24）。
        SmeltingWidget->SetKeyboardFocus();
    }
}

void UColdSteelHUDWidget::CloseSmelting()
{
    if(!bSmeltingOpen)return;
    bSmeltingOpen=false;
    SmeltingWorld.Reset();
    // 关闭＝冶炼栏＋背包一个整体向右缩回（2026-09-24 用户定稿）：立即关抽屉，
    // 面板在 Tick 里与抽屉同一位移曲线刚体骑乘（抽屉行程加长面板宽）。
    if(bInventoryOpen){bSmeltRiding=true;SetInventoryOpen(false);}
    // 滑出动画由 NativeTick 的 SmeltMotion 播完再收起；面板内容挂在 widget 自己的上下文上，
    // 滑出期间保持完整（HUD 的 SmeltingWorld 只用于开炉期有效性校验）。
    if(bInventoryOpen&&CloseButton)CloseButton->SetKeyboardFocus();
}

void UColdSteelHUDWidget::HideSmeltingInstantly()
{
    // 互斥瞬收：不播骑乘动画，直接归位收起（与工作台制作面板共用同一贴位，开另一个前清场）。
    bSmeltingOpen=false;
    bSmeltRiding=false;
    SmeltMotion=0.f;
    SmeltingWorld.Reset();
    if(SmeltingWidget)
    {
        SmeltingWidget->SetVisibility(ESlateVisibility::Collapsed);
        SmeltingWidget->SetRenderTranslation(FVector2D::ZeroVector);
    }
    if(SmeltingSlot)SmeltingSlot->SetZOrder(42);
}
