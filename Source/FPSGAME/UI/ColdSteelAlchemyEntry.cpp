#include "ColdSteelAlchemyWidget.h"
#include "ColdSteelForgeBoard.h"
#include "ColdSteelUIStyle.h"
#include "Blueprint/WidgetTree.h"
#include "Components/BackgroundBlur.h"
#include "Components/Border.h"
#include "Components/Button.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/GridPanel.h"
#include "Components/GridSlot.h"
#include "Components/HorizontalBox.h"
#include "Components/HorizontalBoxSlot.h"
#include "Components/Overlay.h"
#include "Components/OverlaySlot.h"
#include "Components/ProgressBar.h"
#include "Components/ScrollBox.h"
#include "Components/SizeBox.h"
#include "Components/TextBlock.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"

void UColdSteelAlchemyWidget::EntrySpace(UVerticalBoxSlot* RowSlot,FMargin RowPadding)
{EntrySpacings.Add({RowSlot,RowPadding});}
UVerticalBox* UColdSteelAlchemyWidget::EntryCard(UVerticalBox* Parent)
{
    auto* Border=WidgetTree->ConstructWidget<UBorder>();EntryCards.Add(Border);
    EntrySpace(Parent->AddChildToVerticalBox(Border),FMargin(0,0,0,8));
    auto* Column=WidgetTree->ConstructWidget<UVerticalBox>();Border->SetContent(Column);return Column;
}
void UColdSteelAlchemyWidget::AddEntryMaterialCell(UWidget* Widget,int32 Row,int32 Column)
{
    auto* CellSlot=EntryMaterialGrid->AddChildToGrid(Widget,Row,Column);
    CellSlot->SetHorizontalAlignment(Column==0?HAlign_Fill:HAlign_Right);CellSlot->SetVerticalAlignment(VAlign_Center);
    CellSlot->SetPadding(FMargin(Column==0?0.f:12.f/Scale,4.f/Scale,0,4.f/Scale));EntryMaterialSlots.Add(CellSlot);
}
void UColdSteelAlchemyWidget::EnsureEntryMaterialRows(int32 Count)
{
    while(EntryMaterialRows.Num()<Count)
    {
        FEntryMaterialRow Row;
        auto* Name=Text(TEXT(""),14);Row.Name=Name;
        auto* Amount=WidgetTree->ConstructWidget<UHorizontalBox>();Row.Amount=Amount;
        auto* Owned=Text(TEXT(""),14,false,true);Row.Owned=Owned;
        auto* Separator=Text(TEXT(" / "),14,false,true);Row.Separator=Separator;
        auto* Required=Text(TEXT(""),14,false,true);Row.Required=Required;
        Separator->SetColorAndOpacity(ColdSteelUI::TextSecondary);Required->SetColorAndOpacity(ColdSteelUI::TextSecondary);
        for(auto* Number:{Owned,Separator,Required})
        {Number->SetJustification(ETextJustify::Right);Amount->AddChildToHorizontalBox(Number)->SetVerticalAlignment(VAlign_Center);}
        auto* State=Text(TEXT(""),14);State->SetJustification(ETextJustify::Right);Row.State=State;
        const int32 Index=EntryMaterialRows.Num()+1;
        AddEntryMaterialCell(Name,Index,0);AddEntryMaterialCell(Amount,Index,1);AddEntryMaterialCell(State,Index,2);
        EntryMaterialRows.Add(Row);
    }
}
void UColdSteelAlchemyWidget::BuildEntry()
{
    // Mirror ColdSteelForgingWidget's entry tree and spacing. Only its business
    // labels/data/actions change; the preview below is the very same widget.
    Management=WidgetTree->ConstructWidget<UBorder>();Management->SetHorizontalAlignment(HAlign_Fill);Management->SetVerticalAlignment(VAlign_Fill);
    ManagementSlot=Canvas->AddChildToCanvas(Management);
    auto* Layers=WidgetTree->ConstructWidget<UOverlay>();Management->SetContent(Layers);
    EntryBlur=WidgetTree->ConstructWidget<UBackgroundBlur>();auto* BlurSlot=Layers->AddChildToOverlay(EntryBlur);
    BlurSlot->SetHorizontalAlignment(HAlign_Fill);BlurSlot->SetVerticalAlignment(VAlign_Fill);EntryBlur->SetVisibility(ESlateVisibility::HitTestInvisible);
    auto* Tint=WidgetTree->ConstructWidget<UBorder>();Tint->SetBrushColor(ColdSteelUI::GlassTint);Tint->SetPadding(0);
    Tint->SetHorizontalAlignment(HAlign_Fill);Tint->SetVerticalAlignment(VAlign_Fill);
    auto* TintSlot=Layers->AddChildToOverlay(Tint);TintSlot->SetHorizontalAlignment(HAlign_Fill);TintSlot->SetVerticalAlignment(VAlign_Fill);
    auto* Stack=WidgetTree->ConstructWidget<UVerticalBox>();Tint->SetContent(Stack);
    EntryHeader=WidgetTree->ConstructWidget<UBorder>();EntryHeader->SetBrushColor(ColdSteelUI::HeaderTint);Stack->AddChildToVerticalBox(EntryHeader);
    auto* Head=WidgetTree->ConstructWidget<UHorizontalBox>();EntryHeader->SetContent(Head);
    auto* Title=Text(TEXT("炼药 · 药水工作台"),20,false,false,true);
    auto* TitleSlot=Head->AddChildToHorizontalBox(Title);TitleSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));TitleSlot->SetVerticalAlignment(VAlign_Center);
    EntryCloseSize=WidgetTree->ConstructWidget<USizeBox>();EntryCloseSize->SetContent(Button(TEXT("×"),1));ButtonSizes.Add(EntryCloseSize);
    Head->AddChildToHorizontalBox(EntryCloseSize)->SetVerticalAlignment(VAlign_Center);
    EntryScroll=WidgetTree->ConstructWidget<UScrollBox>();EntryScroll->SetConsumeMouseWheel(EConsumeMouseWheel::Always);
    Stack->AddChildToVerticalBox(EntryScroll)->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    EntryBody=WidgetTree->ConstructWidget<UBorder>();EntryBody->SetBrushColor(FLinearColor::Transparent);EntryScroll->AddChild(EntryBody);
    auto* Content=WidgetTree->ConstructWidget<UVerticalBox>();EntryBody->SetContent(Content);
    auto* RecipeCard=EntryCard(Content);
    auto* Caption=Text(TEXT("配方 · 药水"),12);Caption->SetColorAndOpacity(ColdSteelUI::TextTertiary);
    EntrySpace(RecipeCard->AddChildToVerticalBox(Caption),FMargin(0,0,0,4));
    EntryRecipeTitle=Text(TEXT("—"),16,false,false,true);EntrySpace(RecipeCard->AddChildToVerticalBox(EntryRecipeTitle),FMargin(0,0,0,8));
    Choice=WidgetTree->ConstructWidget<UComboBoxString>();Choice->OnGenerateWidgetEvent.BindDynamic(this,&ThisClass::Option);
    Choice->OnSelectionChanged.AddDynamic(this,&ThisClass::Select);
    Choice->SetToolTipText(FText::FromString(TEXT("选择炼药配方；当前批次需领取或作废后才能更换。")));
    auto* ChoiceSize=WidgetTree->ConstructWidget<USizeBox>();ChoiceSize->SetContent(Choice);ButtonSizes.Add(ChoiceSize);
    EntrySpace(RecipeCard->AddChildToVerticalBox(ChoiceSize),FMargin(0,0,0,8));
    Materials=Text(TEXT("所需材料"),14,false,false,true);EntrySpace(RecipeCard->AddChildToVerticalBox(Materials),FMargin(0,0,0,4));
    EntryMaterialSource=Text(TEXT("材料来源 · 背包 + 主仓库"),12);EntryMaterialSource->SetColorAndOpacity(ColdSteelUI::TextTertiary);
    EntrySpace(RecipeCard->AddChildToVerticalBox(EntryMaterialSource),FMargin(0,0,0,4));
    EntryMaterialGrid=WidgetTree->ConstructWidget<UGridPanel>();EntryMaterialGrid->SetColumnFill(0,1.f);RecipeCard->AddChildToVerticalBox(EntryMaterialGrid);
    auto* NameHeader=Text(TEXT("材料"),12);EntryQuantityHeader=Text(TEXT("持有 / 需要"),12);auto* StateHeader=Text(TEXT("状态"),12);
    for(auto* Label:{NameHeader,EntryQuantityHeader.Get(),StateHeader})Label->SetColorAndOpacity(ColdSteelUI::TextSecondary);
    AddEntryMaterialCell(NameHeader,0,0);AddEntryMaterialCell(EntryQuantityHeader,0,1);AddEntryMaterialCell(StateHeader,0,2);
    auto* StateCard=EntryCard(Content);
    EntryStage=Text(TEXT("选择配方 · 准备炼药"),16,false,false,true);EntrySpace(StateCard->AddChildToVerticalBox(EntryStage),FMargin(0,0,0,8));
    EntryStats=Text(TEXT(""),16,false,true);EntrySpace(StateCard->AddChildToVerticalBox(EntryStats),FMargin(0,0,0,4));
    EntryLegend=Text(TEXT("基础产量   /   精制加成   /   装瓶上限"),12);EntryLegend->SetColorAndOpacity(ColdSteelUI::TextTertiary);StateCard->AddChildToVerticalBox(EntryLegend);
    Refund=Text(TEXT(""),12,true);Refund->SetColorAndOpacity(ColdSteelUI::TextSecondary);EntrySpace(StateCard->AddChildToVerticalBox(Refund),FMargin(0,8,0,0));
    EntryTimer=WidgetTree->ConstructWidget<UProgressBar>();EntryTimer->SetFillColorAndOpacity(ColdSteelUI::Accent);
    EntryTimerSize=WidgetTree->ConstructWidget<USizeBox>();EntryTimerSize->SetContent(EntryTimer);EntrySpace(StateCard->AddChildToVerticalBox(EntryTimerSize),FMargin(0,8,0,0));
    auto* PreviewCaption=Text(TEXT("成品预览 · 按配方显示药水"),14,false,false,true);EntrySpace(Content->AddChildToVerticalBox(PreviewCaption),FMargin(0,4,0,8));
    EntryBoardSize=WidgetTree->ConstructWidget<USizeBox>();auto* Columns=WidgetTree->ConstructWidget<UHorizontalBox>();EntryBoardSize->SetContent(Columns);
    EntrySpace(Content->AddChildToVerticalBox(EntryBoardSize),FMargin(0,0,0,8));
    EntryPreview=WidgetTree->ConstructWidget<UColdSteelForgeBoard>();EntryPreview->SetVisibility(ESlateVisibility::HitTestInvisible);
    Columns->AddChildToHorizontalBox(EntryPreview)->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    auto* Parameters=WidgetTree->ConstructWidget<UBorder>();EntryCards.Add(Parameters);
    EntryParameterSlot=Columns->AddChildToHorizontalBox(Parameters);EntryParameterSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    auto* ParameterScroll=WidgetTree->ConstructWidget<UScrollBox>();Parameters->SetContent(ParameterScroll);
    auto* ParameterContent=WidgetTree->ConstructWidget<UVerticalBox>();ParameterScroll->AddChild(ParameterContent);
    EntryPreviewName=Text(TEXT("—"),16,false,false,true);EntrySpace(ParameterContent->AddChildToVerticalBox(EntryPreviewName),FMargin(0,0,0,8));
    EntryPreviewStage=Text(TEXT("配方基础参数"),12);EntryPreviewStage->SetColorAndOpacity(ColdSteelUI::TextSecondary);
    EntrySpace(ParameterContent->AddChildToVerticalBox(EntryPreviewStage),FMargin(0,0,0,12));
    EntryParameterGrid=WidgetTree->ConstructWidget<UGridPanel>();EntryParameterGrid->SetColumnFill(0,1.f);ParameterContent->AddChildToVerticalBox(EntryParameterGrid);
    ProductInfo=Text(TEXT(""),12,true);ProductInfo->SetColorAndOpacity(ColdSteelUI::TextTertiary);EntrySpace(ParameterContent->AddChildToVerticalBox(ProductInfo),FMargin(0,12,0,0));
    auto* Instructions=EntryCard(Content);EntrySpace(Instructions->AddChildToVerticalBox(Text(TEXT("操作说明"),16,false,false,true)),FMargin(0,0,0,8));
    auto* Help=Text(TEXT("进入台面后直接点击材料与器具。按住搅拌棒绕锅心拖动，火候旋钮左键升档、右键降档。"),14,true);
    EntrySpace(Instructions->AddChildToVerticalBox(Help),FMargin(0,0,0,8));
    auto* Rule=Text(TEXT("翻阅配方手册决定用料、火候与搅拌，观察药液和温度计判断时机。点击量瓶舀取并装瓶。"),12,true);
    Rule->SetColorAndOpacity(ColdSteelUI::TextSecondary);EntrySpace(Instructions->AddChildToVerticalBox(Rule),FMargin(0,0,0,8));
    auto* Exit=Text(TEXT("开炉时扣除材料。离台收火暂存，可继续本炉；未完成时作废退还未开封材料，完成后作废返还一半材料（逐项向下取整）。"),12,true);
    Exit->SetColorAndOpacity(ColdSteelUI::TextTertiary);Instructions->AddChildToVerticalBox(Exit);
    EntryFooter=WidgetTree->ConstructWidget<UBorder>();EntryFooter->SetBrushColor(ColdSteelUI::HeaderTint);Stack->AddChildToVerticalBox(EntryFooter);
    auto* Foot=WidgetTree->ConstructWidget<UVerticalBox>();EntryFooter->SetContent(Foot);
    Status=Text(TEXT(""),14,true);Status->SetColorAndOpacity(ColdSteelUI::TextSecondary);EntrySpace(Foot->AddChildToVerticalBox(Status),FMargin(0,0,0,8));
    auto* ActionsRow=WidgetTree->ConstructWidget<UHorizontalBox>();Foot->AddChildToVerticalBox(ActionsRow);
    auto AddAction=[&](const TCHAR* Label,int32 Id)
    {
        auto* Size=WidgetTree->ConstructWidget<USizeBox>();Size->SetContent(Button(Label,Id));ButtonSizes.Add(Size);
        auto* ActionSlot=ActionsRow->AddChildToHorizontalBox(Size);ActionSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));return ActionSlot;
    };
    AddAction(TEXT("备料开炉"),10);EntryDiscardSlot=AddAction(TEXT("作废退料"),12);EntryManualSlot=AddAction(TEXT("配方手册"),11);
    ScaleEntry();
}
bool UColdSteelAlchemyWidget::ContainsManagement(FVector2D ScreenPosition) const
{return Management&&Management->IsVisible()&&Management->GetCachedGeometry().IsUnderLocation(ScreenPosition);}
