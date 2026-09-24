#include "ColdSteelHUDWidget.h"
#include "ColdSteelSkillPage.h"
#include "ColdSteelCodexPage.h"
#include "ColdSteelSmeltingWidget.h"
#include "ColdSteelWorkbenchWidget.h"
#include "ColdSteelUIStyle.h"
#include "GunsmithUIStyle.h"
#include "ColdSteelDetailRow.h"
#include "Blueprint/WidgetTree.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/TextBlock.h"
#include "Components/Border.h"
#include "Components/Button.h"
#include "Components/ButtonSlot.h"
#include "Components/SizeBox.h"
#include "Components/VerticalBoxSlot.h"

UTextBlock* UColdSteelHUDWidget::MakeInventoryText(const FString& Text,float Pixels,const FLinearColor& Color,bool Numeric,bool Medium)
{
    auto* Label=WidgetTree->ConstructWidget<UTextBlock>();Label->SetText(FText::FromString(Text));Label->SetColorAndOpacity(Color);
    const float Size=Pixels/ColdSteelUI::PixelScale(this);
    Label->SetFont(Numeric?GunsmithUI::NumberFont(Size,Medium):GunsmithUI::TextFont(Size,Medium));
    InventoryLabels.Add({Label,Pixels,Numeric,Medium});return Label;
}

void UColdSteelHUDWidget::UpdateInventoryLayout(const FGeometry& Geometry)
{
    if(!InventoryPanelSlot)return;
    const float Scale=ColdSteelUI::PixelScale(this);const FVector2D Pixels=Geometry.GetLocalSize()*Scale;
    if(Pixels.X<100||Pixels.Y<100)return;
    const float RightInset=ColdSteelUI::NavigationDrawerInset;
    float Width=FMath::Min(float(Pixels.X)-RightInset-12.f,FMath::Clamp(float(Pixels.X)*.48f,720.f,1040.f));
    // Both drawers share their actual size; keep that layout until the left drawer finishes closing.
    if(bWarehouseOpen||WarehouseMotion>.001f)Width=FMath::Min(Width,(float(Pixels.X)-RightInset-24.f)*.5f);
    // 冶炼面板（2026-09-23 起独立于背包）：背包开着时**零缝拼接**贴抽屉左缘（2026-09-24 用户要求），
    // 背包关着时贴视口右缘（12px 边距）。宽＝背包实际宽的一半；仓库同开时再按剩余空间夹一次，
    // 低于最小可用宽就整块收起，不挤破视口。
    float Smelt=0.f,Dock=12.f;
    const bool bDrawerOut=bInventoryOpen||DrawerProgress>.001f;
    if(bSmeltingOpen)
    {
        Dock=bDrawerOut?Width:12.f;
        const float Leftover=float(Pixels.X)-RightInset-Dock-(bDrawerOut&&(bWarehouseOpen||WarehouseMotion>.001f)?Width+12.f:0.f)-24.f;
        Smelt=FMath::Max(0.f,FMath::Min(Width*.5f,Leftover));
        // 低于最小可用宽（12 内边距×2＋一列正文）就整块收起：细条面板里任何 12px 正文都会溢出方框。
        if(Smelt<240.f)Smelt=0.f;
    }
    // 工作台制作面板：与冶炼面板同贴位、同公式、互斥（HUD 开一瞬收另一，同一时刻至多一块占位）。
    float WB=0.f,WBDock=12.f;
    if(bWorkbenchOpen)
    {
        WBDock=bDrawerOut?Width:12.f;
        const float Leftover=float(Pixels.X)-RightInset-WBDock-(bDrawerOut&&(bWarehouseOpen||WarehouseMotion>.001f)?Width+12.f:0.f)-24.f;
        WB=FMath::Max(0.f,FMath::Min(Width*.5f,Leftover));
        if(WB<240.f)WB=0.f;
    }
    if(SkillPage)SkillPage->SetLayoutWidth(FMath::Max(1.f,Width-2.f));
    // 图鉴页用同一宽度决定网格／详情并排还是纵排。
    if(CodexPage)CodexPage->SetLayoutWidth(FMath::Max(1.f,Width-2.f));
    if(!Pixels.Equals(InventoryLayoutSize,.5f)||!FMath::IsNearlyEqual(Scale,InventoryLayoutScale,.001f)
        ||!FMath::IsNearlyEqual(Width,InventoryWidth,.5f)||!FMath::IsNearlyEqual(Smelt,SmeltWidth,.5f)
        ||!FMath::IsNearlyEqual(Dock,SmeltDock,.5f)
        ||!FMath::IsNearlyEqual(WB,WorkbenchWidth,.5f)||!FMath::IsNearlyEqual(WBDock,WorkbenchDock,.5f))
    {
        InventoryPanelSlot->SetOffsets(FMargin(-RightInset/Scale,12/Scale,Width/Scale,12/Scale));
        InventoryHeaderSurface->SetPadding(FMargin(18/Scale,12/Scale));InventoryHeaderSize->SetHeightOverride(36/Scale);
        for(auto& WeakSize:InventoryTabSizes)if(auto* Size=WeakSize.Get())Size->SetHeightOverride(40/Scale);
        InventoryFooterSlot->SetPadding(FMargin(18/Scale,8/Scale,18/Scale,10/Scale));
        Cast<UButtonSlot>(CloseButton->GetContent()->Slot)->SetPadding(FMargin(12/Scale,8/Scale));
        if(WarehouseSlot){WarehouseSlot->SetAnchors(FAnchors(0,0,0,1));WarehouseSlot->SetAlignment(FVector2D::ZeroVector);WarehouseSlot->SetOffsets(FMargin(12/Scale,12/Scale,Width/Scale,12/Scale));}
        if(SmeltingSlot)
        {
            // 槽位＝屏幕左缘→面板右缘的全宽命中区（2026-09-24 修复：挂在父边界外负坐标的子控件
            // 能绘制却收不到点击，"升级"页签被点穿、连带关掉背包与冶炼栏）。右缘仍由 Offset.Left
            // 贴住 Dock（背包开＝抽屉宽零缝拼接，关＝12px 边距）；宽度取满，面板本体在内部重排。
            SmeltingSlot->SetAnchors(FAnchors(1,0,1,1));SmeltingSlot->SetAlignment(FVector2D(1,0));
            SmeltingSlot->SetOffsets(FMargin(-Dock/Scale,12/Scale,(float(Pixels.X)-Dock)/Scale,12/Scale));
        }
        if(SmeltingWidget&&Smelt>1.f)
        {   SmeltingWidget->SetLayoutWidth(Smelt);
            // 面板左缘屏幕像素真值（Shell/页签/弹层重排的坐标源；Slate 缓存几何不可反推，见面板注释）。
            SmeltingWidget->SetPanelScreenX(float(Pixels.X)-Dock-Smelt);
        }
        if(WorkbenchSlot)
        {   // 工作台制作面板槽位＝屏幕左缘→面板右缘全宽命中区（与冶炼同一修复口径）。
            WorkbenchSlot->SetAnchors(FAnchors(1,0,1,1));WorkbenchSlot->SetAlignment(FVector2D(1,0));
            WorkbenchSlot->SetOffsets(FMargin(-WBDock/Scale,12/Scale,(float(Pixels.X)-WBDock)/Scale,12/Scale));
        }
        if(WorkbenchWidget&&WB>1.f)
        {   WorkbenchWidget->SetLayoutWidth(WB);
            WorkbenchWidget->SetPanelScreenX(float(Pixels.X)-WBDock-WB);
        }
        for(const auto& Entry:InventoryLabels)if(auto* Label=Entry.Widget.Get())
            Label->SetFont(Entry.Numeric?GunsmithUI::NumberFont(Entry.Pixels/Scale,Entry.Medium):GunsmithUI::TextFont(Entry.Pixels/Scale,Entry.Medium));
        for(const auto& Pair:CharacterRows)if(Pair.Value)Pair.Value->UpdateScale(Scale);
        InventoryLayoutSize=Pixels;InventoryLayoutScale=Scale;InventoryWidth=Width;SmeltWidth=Smelt;SmeltDock=Dock;
        WorkbenchWidth=WB;WorkbenchDock=WBDock;
        UE_LOG(LogTemp,Display,TEXT("INVENTORY_GLASS viewport=%.0fx%.0f drawer=%.0f scale=%.3f warehouse=%d smelting=%.0f workbench=%.0f"),Pixels.X,Pixels.Y,Width,Scale,bWarehouseOpen,Smelt,WB);
    }
}
