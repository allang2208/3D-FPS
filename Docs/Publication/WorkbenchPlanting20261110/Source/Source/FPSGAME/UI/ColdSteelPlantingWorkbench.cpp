#include "ColdSteelWorkbenchWidget.h"
#include "ColdSteelHUDWidget.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelUIStyle.h"
#include "ColdSteelPlantingProgress.h"
#include "Components/NativeWidgetHost.h"
#include "Components/HorizontalBoxSlot.h"
#include "../Development/DevelopmentTuningSubsystem.h"
#include "Components/ComboBoxString.h"
#include "Framework/Application/SlateApplication.h"
#include "InputCoreTypes.h"
#include "../Building/ColdSteelPlantingSystem.h"
#include "../Building/ColdSteelPlantingLayout.h"
#include "../Building/VoxelBuildWorld.h"
#include "../Building/VoxelBuildPrefabActor.h"
#include "Blueprint/WidgetTree.h"
#include "Components/Border.h"
#include "Components/ButtonSlot.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/GridPanel.h"
#include "Components/GridSlot.h"
#include "Components/Image.h"
#include "Components/HorizontalBox.h"
#include "Components/ProgressBar.h"
#include "Components/ScaleBox.h"
#include "Components/ScrollBox.h"
#include "Components/SizeBox.h"
#include "Components/TextBlock.h"
#include "Components/UniformGridPanel.h"
#include "Components/UniformGridSlot.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "Engine/GameInstance.h"
#include "GameFramework/Pawn.h"

namespace
{
    void PlantingLabel(UTextBlock* Widget,const FString& Value)
    {if(Widget&&Widget->GetText().ToString()!=Value)Widget->SetText(FText::FromString(Value));}
    TArray<const FColdSteelCropPlant*> PlantingPositionPlants(const UColdSteelPlantingSystem* System,
        const AVoxelBuildWorld* World,FIntVector Cell,int32 Plot)
    {
        TArray<const FColdSteelCropPlant*> Result;
        if(!System||!ColdSteelPlantingLayout::IsPlot(Plot))return Result;
        const int32 Anchor=ColdSteelPlantingLayout::Anchor(Plot);
        for(int32 Offset:{0,1,4,5})if(const auto* Plant=System->Occupant(World,Cell,Anchor+Offset))Result.AddUnique(Plant);
        Result.Sort([](const FColdSteelCropPlant& A,const FColdSteelCropPlant& B){return A.Slot<B.Slot;});
        return Result;
    }
    const TCHAR* PlantingStageName(int32 Stage)
    {return Stage==3?TEXT("可收获"):Stage==2?TEXT("生长中"):TEXT("幼苗");}
}
void UColdSteelWorkbenchRowProxy::PlantingClicked()
{
    if(auto* Owner=Panel.Get())
    {if(Axis<0)Owner->SelectPlantingCrop(-Axis-1);else Owner->SelectPlantingSlot(Axis);}
}

void UColdSteelWorkbenchWidget::SetPlantingMode(bool Enabled)
{
    SetPlantingEffectsEnabled(false);CancelPlantingDrag();bPlantingMode=Enabled;PlantingSlot=INDEX_NONE;PlantingSelectedSlots.Reset();PlantingQuotedStage=-1;bDataDirty=true;
    PlantingBedContextId=Enabled&&World.IsValid()?World->PrefabInstanceIdentity(Cell):FGuid();
    if(!CraftingBodyContent)CraftingBodyContent=Body->GetContent();
    if(Enabled)
    {
        if(!PlantingBodyContent)BuildPlantingBody();
        Body->SetContent(PlantingBodyContent);BatchRow->SetVisibility(ESlateVisibility::Collapsed);
        PlantingLabel(PanelTitle,TEXT("种植 · 种植地"));
    }
    else
    {Body->SetContent(CraftingBodyContent);PlantingLabel(PanelTitle,TEXT("制作 · 工作台"));}
    UpdateScale();
}

void UColdSteelWorkbenchWidget::BuildPlantingBody()
{
    PlantingBodyContent=WidgetTree->ConstructWidget<UVerticalBox>();
    auto* System=GetGameInstance()->GetSubsystem<UColdSteelPlantingSystem>();
    auto* Selection=Card(PlantingBodyContent);
    Space(Selection->AddChildToVerticalBox(Text(TEXT("播种作物"),16,ColdSteelUI::TextPrimary,false,true)),FMargin(0,0,0,8));
    PlantingChoice=WidgetTree->ConstructWidget<UComboBoxString>();
    PlantingChoice->OnGenerateWidgetEvent.BindDynamic(this,&ThisClass::GenerateRecipeOption);
    if(System)for(const auto& Rule:System->Catalog())
    {
        PlantingChoice->AddOption(Rule.Name);
        IconFor(Rule.OutputItem); // Warm the bounded catalog once, never from drag input.
    }
    PlantingChoice->OnSelectionChanged.AddDynamic(this,&ThisClass::HandlePlantingCropSelected);
    PlantingChoice->SetToolTipText(FText::FromString(TEXT("每个种植位种植一株；选择作物后查看本次材料和收获预览。")));
    PlantingChoiceSize=WidgetTree->ConstructWidget<USizeBox>();PlantingChoiceSize->SetContent(PlantingChoice);ButtonSizes.Add(PlantingChoiceSize);
    Selection->AddChildToVerticalBox(PlantingChoiceSize);
    Space(Selection->AddChildToVerticalBox(Text(TEXT("单击选择种植位 · 拖动可批量选择空位 · 点击植株查看或收获"),12,ColdSteelUI::TextSecondary,false,false,true)),FMargin(0,8,0,0));
    if(System&&!System->Catalog().IsEmpty()&&!System->Find(PlantingCrop))PlantingCrop=System->Catalog()[0].Id;

    PlantingContentLayout=WidgetTree->ConstructWidget<UGridPanel>();
    Space(PlantingBodyContent->AddChildToVerticalBox(PlantingContentLayout),FMargin(0,0,0,8));
    auto* PlotColumn=WidgetTree->ConstructWidget<UVerticalBox>();
    auto* PlotSlot=PlantingContentLayout->AddChildToGrid(PlotColumn,0,0);PlotSlot->SetVerticalAlignment(VAlign_Fill);
    auto* PlotCard=Card(PlotColumn);
    Cast<UVerticalBoxSlot>(PlotCard->GetParent()->Slot)->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    Space(PlotCard->AddChildToVerticalBox(Text(TEXT("种植位置 · 2×2"),16,ColdSteelUI::TextPrimary,false,true)),FMargin(0,0,0,4));
    PlantingSummary=Text(TEXT(""),12,ColdSteelUI::TextSecondary,false,false,true);
    Space(PlotCard->AddChildToVerticalBox(PlantingSummary),FMargin(0,0,0,8));
    PlantingMapSize=WidgetTree->ConstructWidget<USizeBox>();
    PlotCard->AddChildToVerticalBox(PlantingMapSize)->SetHorizontalAlignment(HAlign_Center);
    auto* Map=WidgetTree->ConstructWidget<UCanvasPanel>();PlantingMapSize->SetContent(Map);
    for(int32 Index=0;Index<ColdSteelPlantingLayout::PlotCount;++Index)
    {
        // Render four planting positions; storage cells are never exposed as extra choices.
        auto* B=WidgetTree->ConstructWidget<UButton>();Buttons.Add(B);PlantingSlotButtons.Add(B);
        FPlantingTile Tile;Tile.Slot=Map->AddChildToCanvas(B);
        auto* TileCanvas=WidgetTree->ConstructWidget<UCanvasPanel>();B->SetContent(TileCanvas);TileCanvas->SetClipping(EWidgetClipping::ClipToBoundsAlways);
        auto* ButtonSlot=Cast<UButtonSlot>(TileCanvas->Slot);ButtonSlot->SetHorizontalAlignment(HAlign_Fill);ButtonSlot->SetVerticalAlignment(VAlign_Fill);ButtonSlot->SetPadding(0);
        auto* Info=WidgetTree->ConstructWidget<UBorder>();Info->SetBrushColor(FLinearColor::Transparent);Info->SetPadding(0);Info->SetVerticalAlignment(VAlign_Center);
        Info->SetVisibility(ESlateVisibility::HitTestInvisible);Info->SetClipping(EWidgetClipping::ClipToBoundsAlways);
        Tile.ContentSlot=TileCanvas->AddChildToCanvas(Info);Tile.ContentSlot->SetAnchors(FAnchors(0,0,1,1));
        auto* Column=WidgetTree->ConstructWidget<UVerticalBox>();Info->SetContent(Column);
        auto* IconSize=WidgetTree->ConstructWidget<USizeBox>();Tile.IconSize=IconSize;
        auto* Fit=WidgetTree->ConstructWidget<UScaleBox>();Fit->SetStretch(EStretch::ScaleToFit);IconSize->SetContent(Fit);
        auto* Icon=WidgetTree->ConstructWidget<UImage>();Tile.Icon=Icon;Fit->SetContent(Icon);
        Column->AddChildToVerticalBox(IconSize)->SetHorizontalAlignment(HAlign_Center);
        auto* Name=Text(TEXT(""),12,ColdSteelUI::TextPrimary,false,true);Name->SetJustification(ETextJustify::Center);Name->SetTextOverflowPolicy(ETextOverflowPolicy::Ellipsis);Tile.Name=Name;Column->AddChildToVerticalBox(Name);
        auto* State=Text(TEXT(""),12,ColdSteelUI::TextSecondary);State->SetJustification(ETextJustify::Center);State->SetTextOverflowPolicy(ETextOverflowPolicy::Ellipsis);Tile.State=State;Column->AddChildToVerticalBox(State);
        auto* BarSize=WidgetTree->ConstructWidget<USizeBox>();Tile.ProgressSize=BarSize;
        auto* Bar=WidgetTree->ConstructWidget<UNativeWidgetHost>();BarSize->SetContent(Bar);
        Tile.Progress=SNew(SColdSteelPlantingProgress);Bar->SetContent(Tile.Progress.ToSharedRef());
        BarSize->SetVisibility(ESlateVisibility::HitTestInvisible);BarSize->SetClipping(EWidgetClipping::ClipToBoundsAlways);
        Tile.ProgressSlot=TileCanvas->AddChildToCanvas(BarSize);Tile.ProgressSlot->SetAnchors(FAnchors(0,1,1,1));
        PlantingTiles.Add(Tile);
        auto* Proxy=NewObject<UColdSteelWorkbenchRowProxy>(this);Proxy->Panel=this;Proxy->Axis=Index;PlantingProxies.Add(Proxy);
        B->OnClicked.AddDynamic(Proxy,&UColdSteelWorkbenchRowProxy::PlantingClicked);
    }
    Space(PlotCard->AddChildToVerticalBox(Text(TEXT("每个位置 1 株，整块种植地最多 4 株。"),12,ColdSteelUI::TextTertiary,false,false,true)),FMargin(0,8,0,0));

    auto* DetailColumn=WidgetTree->ConstructWidget<UVerticalBox>();
    PlantingDetailsSlot=PlantingContentLayout->AddChildToGrid(DetailColumn,0,1);PlantingDetailsSlot->SetVerticalAlignment(VAlign_Fill);
    auto* Detail=Card(DetailColumn);
    Cast<UVerticalBoxSlot>(Detail->GetParent()->Slot)->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    PlantingDetailTitle=Text(TEXT("选中详情"),16,ColdSteelUI::TextPrimary,false,true);
    Space(Detail->AddChildToVerticalBox(PlantingDetailTitle),FMargin(0,0,0,8));
    PlantingPlotText=Text(TEXT("请选择地块"),14,ColdSteelUI::TextPrimary,false,false,true);
    Space(Detail->AddChildToVerticalBox(PlantingPlotText),FMargin(0,0,0,12));
    PlantingProductSize=WidgetTree->ConstructWidget<USizeBox>();
    auto* Fit=WidgetTree->ConstructWidget<UScaleBox>();Fit->SetStretch(EStretch::ScaleToFit);PlantingProductSize->SetContent(Fit);
    PlantingProductIcon=WidgetTree->ConstructWidget<UImage>();Fit->SetContent(PlantingProductIcon);Detail->AddChildToVerticalBox(PlantingProductSize);
    PlantingProductEmpty=Text(TEXT("暂无作物图像"),12,ColdSteelUI::TextTertiary);PlantingProductEmpty->SetJustification(ETextJustify::Center);Detail->AddChildToVerticalBox(PlantingProductEmpty);
    PlantingProductName=Text(TEXT(""),14,ColdSteelUI::TextPrimary,false,true);PlantingProductName->SetJustification(ETextJustify::Center);
    Space(Detail->AddChildToVerticalBox(PlantingProductName),FMargin(0,4,0,12));
    PlantingRuleText=Text(TEXT(""),14,ColdSteelUI::TextSecondary,false,false,true);Detail->AddChildToVerticalBox(PlantingRuleText);
    auto* Notes=Card(PlantingBodyContent);
    Space(Notes->AddChildToVerticalBox(Text(TEXT("种植概览"),16,ColdSteelUI::TextPrimary,false,true)),FMargin(0,0,0,8));
    PlantingOverview=Text(TEXT(""),14,ColdSteelUI::TextPrimary,false,false,true);
    Space(Notes->AddChildToVerticalBox(PlantingOverview),FMargin(0,0,0,10));
    PlantingCareNotice=Text(TEXT(""),12,ColdSteelUI::TextSecondary,false,false,true);
    Space(Notes->AddChildToVerticalBox(PlantingCareNotice),FMargin(0,10,0,0));
    Space(Notes->AddChildToVerticalBox(Text(TEXT("按实际时间生长，离线继续。拆除种植地会清除植株，不返还种植材料。"),12,ColdSteelUI::Warning,false,false,true)),FMargin(0,8,0,0));
    UpdatePlantingLayout();
}

void UColdSteelWorkbenchWidget::SelectPlantingCrop(int32 CropIndex)
{
    if(!bPlantingMode||!bInputReady)return;
    auto* System=GetGameInstance()->GetSubsystem<UColdSteelPlantingSystem>();
    if(!System||System->Pending()||!System->Catalog().IsValidIndex(CropIndex))return;
    PlantingCrop=System->Catalog()[CropIndex].Id;bDataDirty=true;SetStatus(FString());RefreshPlanting();SetKeyboardFocus();
}
void UColdSteelWorkbenchWidget::HandlePlantingCropSelected(FString Option,ESelectInfo::Type SelectionType)
{
    if(SelectionType==ESelectInfo::Direct)return;
    auto* System=GetGameInstance()->GetSubsystem<UColdSteelPlantingSystem>();
    if(!System||!PlantingChoice)return;
    if(!bInputReady||System->Pending())
    {PlantingChoice->SetSelectedIndex(System->Catalog().IndexOfByPredicate([this](const auto& R){return R.Id==PlantingCrop;}));return;}
    SelectPlantingCrop(PlantingChoice->GetSelectedIndex());
}
void UColdSteelWorkbenchWidget::SelectPlantingSlot(int32 SlotIndex)
{
    if(!bPlantingMode||!bInputReady||!ColdSteelPlantingLayout::IsPlot(SlotIndex))return;
    auto* System=GetGameInstance()->GetSubsystem<UColdSteelPlantingSystem>();if(!System||System->Pending())return;
    const auto Plants=PlantingPositionPlants(System,World.Get(),Cell,SlotIndex);
    const int32 Previous=PlantingSelectedSlots.IsEmpty()?Plants.IndexOfByPredicate([this](const auto* Plant){return Plant->Slot==PlantingSlot;}):INDEX_NONE;
    PlantingSelectedSlots.Reset();
    if(!Plants.IsEmpty())PlantingSlot=Plants[(Previous+1)%Plants.Num()]->Slot;
    else
    {
        ColdSteelPlantingLayout::AppendCells(SlotIndex,PlantingSelectedSlots);
        PlantingSlot=ColdSteelPlantingLayout::Anchor(SlotIndex);
    }
    PlantingQuotedStage=-1;bDataDirty=true;SetStatus(FString());RefreshPlanting();SetKeyboardFocus();
}

int32 UColdSteelWorkbenchWidget::PlantingHitSlot(FVector2D ScreenPosition,bool ClampToMap) const
{
    if(!PlantingMapSize||!PlantingMapSize->IsVisible())return INDEX_NONE;
    // The map may be clipped by the scrolling body; hidden cells must not steal footer clicks.
    if(!ClampToMap&&Scroll&&!Scroll->GetCachedGeometry().IsUnderLocation(ScreenPosition))return INDEX_NONE;
    const auto& Geometry=PlantingMapSize->GetCachedGeometry();const FVector2D Size=Geometry.GetLocalSize();
    if(Size.X<=0||Size.Y<=0||(!ClampToMap&&!Geometry.IsUnderLocation(ScreenPosition)))return INDEX_NONE;
    const FVector2D Position=Geometry.AbsoluteToLocal(ScreenPosition);
    constexpr int32 Columns=ColdSteelPlantingLayout::Columns;
    return FMath::Clamp(FMath::FloorToInt(Position.Y/Size.Y*Columns),0,Columns-1)*Columns
        +FMath::Clamp(FMath::FloorToInt(Position.X/Size.X*Columns),0,Columns-1);
}
void UColdSteelWorkbenchWidget::UpdatePlantingDrag(int32 SlotIndex)
{
    if(!bPlantingDragging||!ColdSteelPlantingLayout::IsPlot(SlotIndex)||SlotIndex==PlantingDragEnd)return;
    auto* System=GetGameInstance()->GetSubsystem<UColdSteelPlantingSystem>();
    if(!System||System->Pending()||!bInputReady){CancelPlantingDrag();return;}
    PlantingDragEnd=SlotIndex;PlantingSelectedSlots.Reset();
    constexpr int32 Columns=ColdSteelPlantingLayout::Columns;
    const int32 Top=FMath::Min(PlantingDragStart/Columns,SlotIndex/Columns),Bottom=FMath::Max(PlantingDragStart/Columns,SlotIndex/Columns);
    const int32 Left=FMath::Min(PlantingDragStart%Columns,SlotIndex%Columns),Right=FMath::Max(PlantingDragStart%Columns,SlotIndex%Columns);
    for(int32 Row=Top;Row<=Bottom;++Row)for(int32 Col=Left;Col<=Right;++Col)
    {
        const int32 Plot=Row*Columns+Col;
        if(PlantingPositionPlants(System,World.Get(),Cell,Plot).IsEmpty())ColdSteelPlantingLayout::AppendCells(Plot,PlantingSelectedSlots);
    }
    PlantingSlot=PlantingSelectedSlots.IsEmpty()?INDEX_NONE:PlantingSelectedSlots[0];
    PlantingQuotedStage=-1;bDataDirty=true;RefreshPlanting();
}
void UColdSteelWorkbenchWidget::CancelPlantingDrag()
{
    bPlantingDragging=false;PlantingDragStart=PlantingDragEnd=INDEX_NONE;
    if(FSlateApplication::IsInitialized())if(const auto Widget=GetCachedWidget();Widget.IsValid()&&Widget->HasMouseCapture())
        FSlateApplication::Get().ReleaseMouseCapture();
}
FReply UColdSteelWorkbenchWidget::NativeOnPreviewMouseButtonDown(const FGeometry& Geometry,const FPointerEvent& Event)
{
    if(bPlantingMode&&Event.GetEffectingButton()==EKeys::LeftMouseButton)
    {
        const int32 SlotIndex=PlantingHitSlot(Event.GetScreenSpacePosition());
        if(SlotIndex!=INDEX_NONE)
        {
            auto* System=GetGameInstance()->GetSubsystem<UColdSteelPlantingSystem>();
            if(!bInputReady||!System||System->Pending())return FReply::Handled();
            SelectPlantingSlot(SlotIndex);
            if(PlantingSelectedSlots.IsEmpty())return FReply::Handled();
            bPlantingDragging=true;PlantingDragStart=SlotIndex;PlantingDragEnd=SlotIndex;
            return FReply::Handled().CaptureMouse(TakeWidget());
        }
    }
    return Super::NativeOnPreviewMouseButtonDown(Geometry,Event);
}
FReply UColdSteelWorkbenchWidget::NativeOnMouseMove(const FGeometry& Geometry,const FPointerEvent& Event)
{
    if(bPlantingDragging)
    {
        if(!Event.IsMouseButtonDown(EKeys::LeftMouseButton)){CancelPlantingDrag();return FReply::Handled().ReleaseMouseCapture();}
        UpdatePlantingDrag(PlantingHitSlot(Event.GetScreenSpacePosition(),true));return FReply::Handled();
    }
    return Super::NativeOnMouseMove(Geometry,Event);
}
FReply UColdSteelWorkbenchWidget::NativeOnMouseButtonUp(const FGeometry& Geometry,const FPointerEvent& Event)
{
    if(bPlantingDragging&&Event.GetEffectingButton()==EKeys::LeftMouseButton)
    {
        UpdatePlantingDrag(PlantingHitSlot(Event.GetScreenSpacePosition(),true));
        bPlantingDragging=false;PlantingDragStart=PlantingDragEnd=INDEX_NONE;RefreshPlanting();
        return FReply::Handled().ReleaseMouseCapture();
    }
    return Super::NativeOnMouseButtonUp(Geometry,Event);
}
void UColdSteelWorkbenchWidget::NativeOnMouseCaptureLost(const FCaptureLostEvent& Event)
{
    bPlantingDragging=false;PlantingDragStart=PlantingDragEnd=INDEX_NONE;
    Super::NativeOnMouseCaptureLost(Event);
}

void UColdSteelWorkbenchWidget::RefreshPlanting()
{
    if(!bPlantingMode||!PlantingBodyContent||!World.IsValid())return;
    auto* System=GetGameInstance()->GetSubsystem<UColdSteelPlantingSystem>();
    auto* Piece=Cast<AVoxelBuildPrefabActor>(World->PrefabActorAt(Cell));
    if(!System||!Model)return;
    if(!Piece||Piece->IsFalling()||!World->HasPrefabAt(Cell)||World->PrefabInstanceIdentity(Cell)!=PlantingBedContextId||!GetOwningPlayerPawn()
        ||FVector::DistSquared(Piece->GetActorLocation(),GetOwningPlayerPawn()->GetActorLocation())>FMath::Square(350.f))
    {if(HUD&&HUD->IsWorkbenchOpen())HUD->CloseWorkbench();return;}
    const bool Pending=System->Pending();const bool Ready=bInputReady&&HUD&&HUD->IsWorkbenchOpen()&&!Pending;
    if(bPlantingWasPending&&!Pending&&!System->NetworkFailed())
    {PlantingSelectedSlots.Reset();PlantingSlot=INDEX_NONE;bDataDirty=true;}
    TArray<const FColdSteelCropPlant*> PositionPlants[ColdSteelPlantingLayout::PlotCount];
    for(int32 Plot=0;Plot<ColdSteelPlantingLayout::PlotCount;++Plot)
    {
        PositionPlants[Plot]=PlantingPositionPlants(System,World.Get(),Cell,Plot);
        if(!PositionPlants[Plot].IsEmpty()&&!PlantingSelectedSlots.IsEmpty())
        {
            const int32 Removed=PlantingSelectedSlots.RemoveAll([Plot](int32 PhysicalSlot){return ColdSteelPlantingLayout::PlotForSlot(PhysicalSlot)==Plot;});
            if(Removed){PlantingSlot=PlantingSelectedSlots.IsEmpty()?INDEX_NONE:PlantingSelectedSlots[0];bDataDirty=true;}
        }
    }
    const bool Free=UDevelopmentTuningSubsystem::IsFreePlanting(Model);
    const auto* Rule=System->Find(PlantingCrop);
    const auto* Plant=PlantingSelectedSlots.IsEmpty()?System->Occupant(World.Get(),Cell,PlantingSlot):nullptr;
    if(Plant&&PlantingSlot!=Plant->Slot){PlantingSlot=Plant->Slot;bDataDirty=true;}
    const int64 Now=System->NowTicks(World.Get());const int32 StageNow=Plant?Plant->Stage(Now):0;
    const bool Changed=bDataDirty||PlantingQuotedSerial!=System->StateSerial()||PlantingQuotedStage!=StageNow
        ||bPlantingWasPending!=Pending||bPlantingFreeQuoted!=Free||CraftReason==TEXT("正在准备作物模型");
    if(Changed)
    {
        bDataDirty=false;PlantingQuotedStage=StageNow;PlantingQuotedSerial=System->StateSerial();bPlantingWasPending=Pending;
        if(GetWorld()->GetNetMode()!=NM_Standalone&&!System->NetworkNotice().IsEmpty())SetStatus(System->NetworkNotice(),System->NetworkFailed());
        bPlantingFreeQuoted=Free;PlantingBatchCount=0;
        bCanCraft=Plant?System->CanAct(World.Get(),Cell,PlantingSlot,PlantingCrop,CraftReason)
            :System->CanPlantSelection(World.Get(),Cell,PlantingSelectedSlots,PlantingCrop,PlantingBatchCount,CraftReason);
        if(PlantingChoice)PlantingChoice->SetSelectedIndex(System->Catalog().IndexOfByPredicate([this](const auto& R){return R.Id==PlantingCrop;}));
        const auto* DisplayRule=Plant?System->Find(Plant->Crop):Rule;
        const FString Output=Plant?Plant->OutputItem:Rule?Rule->OutputItem:FString();
        const auto* Brush=IconBrushes.Find(Output);
        if(Brush){PlantingProductIcon->SetBrush(*Brush);PlantingProductIcon->SetVisibility(ESlateVisibility::HitTestInvisible);}
        else PlantingProductIcon->SetVisibility(ESlateVisibility::Collapsed);
        PlantingProductEmpty->SetVisibility(Brush?ESlateVisibility::Collapsed:ESlateVisibility::HitTestInvisible);
        PlantingProductSize->SetVisibility(Brush?ESlateVisibility::HitTestInvisible:ESlateVisibility::Collapsed);
        PlantingLabel(PlantingProductName,Output.IsEmpty()?TEXT("暂无作物"):DefinitionName(Output));
        PlantingLabel(PlantingDetailTitle,Plant?TEXT("植株详情"):TEXT("播种预览"));
        if(Plant)
            PlantingLabel(PlantingRuleText,FString::Printf(TEXT("成熟时间 · %.0f 分钟\n收获 · %s ×%lld\n收获后放入背包"),
                Plant->GrowthSeconds/60.,*DefinitionName(Plant->OutputItem),Plant->OutputCount));
        else if(DisplayRule)
        {
            const FString Cost=Free?FString(TEXT("开发模式 · 本次无需种子"))
                :FString::Printf(TEXT("每株材料 · %s ×%lld\n持有 · %lld\n本次消耗 · %lld"),*DefinitionName(DisplayRule->InputItem),
                    DisplayRule->InputCount,Model->CountMaterial(DisplayRule->InputItem),DisplayRule->InputCount*PlantingBatchCount);
            PlantingLabel(PlantingRuleText,FString::Printf(TEXT("%s\n本次播种 · %d 株\n成熟时间 · %.0f 分钟\n每株收获 · %s ×%lld"),
                *Cost,PlantingBatchCount,DisplayRule->GrowthSeconds/60.,*DefinitionName(DisplayRule->OutputItem),DisplayRule->OutputCount));
        }
        else PlantingLabel(PlantingRuleText,TEXT("当前暂无可种植作物"));
    }
    int32 Empty=0,Growing=0,Mature=0;
    bool LegacyMultiple=false;
    TArray<const FColdSteelCropPlant*> CountedPlants;
    for(int32 Index=0;Index<PlantingSlotButtons.Num();++Index)
    {
        auto* B=PlantingSlotButtons[Index].Get();auto& Tile=PlantingTiles[Index];const auto& Plants=PositionPlants[Index];
        const auto* At=Plant&&Plants.Contains(Plant)?Plant:Plants.IsEmpty()?nullptr:Plants[0];
        if(Plants.IsEmpty())++Empty;
        LegacyMultiple|=Plants.Num()>1;
        for(const auto* Existing:Plants)if(!CountedPlants.Contains(Existing))
        {CountedPlants.Add(Existing);if(Existing->Stage(Now)==3)++Mature;else ++Growing;}
        B->SetVisibility(ESlateVisibility::Visible);
        const int32 TileStage=At?At->Stage(Now):0;const auto* CropRule=At?System->Find(At->Crop):nullptr;
        const bool Selected=Plant?Plants.Contains(Plant):PlantingSelectedSlots.Contains(ColdSteelPlantingLayout::Anchor(Index));
        if(Changed)
        {
            constexpr int32 Columns=ColdSteelPlantingLayout::Columns;
            Tile.Slot->SetAnchors(FAnchors(float(Index%Columns)/Columns,float(Index/Columns)/Columns,
                float(Index%Columns+1)/Columns,float(Index/Columns+1)/Columns));
            Tile.Slot->SetOffsets(FMargin(3/Scale));
            auto Style=ColdSteelUI::ButtonStyle(Scale);
            if(Selected)Style.SetNormal(ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonHover,ColdSteelUI::ButtonRadius/Scale,
                !Plant&&!bCanCraft?ColdSteelUI::Warning:ColdSteelUI::Accent,2.f/Scale));
            B->SetStyle(Style);
            const auto* Brush=At?IconBrushes.Find(At->OutputItem):nullptr;
            if(Brush)Tile.Icon->SetBrush(*Brush);
            const float TilePixels=PlantingMapSize->GetHeightOverride()*Scale/Columns;
            Tile.IconSize->SetVisibility(Brush&&TilePixels>=110.f?ESlateVisibility::HitTestInvisible:ESlateVisibility::Collapsed);
            Tile.ProgressSize->SetVisibility(At?ESlateVisibility::HitTestInvisible:ESlateVisibility::Collapsed);
            Tile.Name->SetVisibility(ESlateVisibility::HitTestInvisible);
            Tile.State->SetVisibility(ESlateVisibility::HitTestInvisible);
            PlantingLabel(Tile.Name.Get(),At?FString::Printf(TEXT("%d · %s"),Index+1,CropRule?*CropRule->Name:TEXT("植株")):
                FString::Printf(TEXT("%d 号种植位"),Index+1));
            const FString Hint=Plants.Num()>1?FString::Printf(TEXT("旧档保留 %d 株，重复点击切换查看和收获"),Plants.Num()):At?TEXT("点击查看植株，成熟后可收获"):TEXT("选择此位置播种一株，可拖动选择多个空位");
            B->SetToolTipText(FText::FromString(FString::Printf(TEXT("%d 号种植位 · %s"),Index+1,*Hint)));
        }
        const float Progress=At?float(FMath::Clamp(At->AgeSeconds(Now)/FMath::Max(1.,At->GrowthSeconds),0.,1.)):0.f;
        const int32 Seconds=At?FMath::Max(0,FMath::CeilToInt(At->GrowthSeconds-At->AgeSeconds(Now))):0;
        PlantingLabel(Tile.State.Get(),Plants.Num()>1?FString::Printf(TEXT("旧档 %d 株 · 点击切换"),Plants.Num()):
            At?(TileStage==3?FString(TEXT("可收获")):FString::Printf(TEXT("%02d:%02d 后成熟"),Seconds/60,Seconds%60)):Selected?TEXT("已选择 · 待播种"):TEXT("空闲 · 可播种"));
        Tile.State->SetColorAndOpacity(TileStage==3?ColdSteelUI::Success:ColdSteelUI::TextSecondary);
        Tile.Progress->SetPlant(At?At->PlantId:FGuid(),Progress,bInputReady&&HUD&&HUD->IsWorkbenchOpen());
        if(B->GetIsEnabled()!=Ready)B->SetIsEnabled(Ready);
    }
    const int32 SelectedCount=PlantingSelectedSlots.Num()/ColdSteelPlantingLayout::CellsPerPlot;
    PlantingLabel(PlantingSummary,FString::Printf(TEXT("已选 %d 个空位 · 本次播种 %d 株"),SelectedCount,PlantingBatchCount));
    PlantingLabel(PlantingOverview,FString::Printf(TEXT("空闲 %d 位 · 生长中 %d 株 · 可收获 %d 株"),Empty,Growing,Mature));
    PlantingLabel(PlantingCareNotice,LegacyMultiple||CountedPlants.Num()>ColdSteelPlantingLayout::PlotCount?
        TEXT("旧档植株全部保留；同一位置重复点击可切换收获，清空后每位种植一株。"):
        Mature>0?TEXT("成熟植株会保留；背包放不下时不会清除，腾出空间后可继续收获。"):
        Free?TEXT("开发模式已开启：无需种子，生长时间和收获数量保持不变。"):
        TEXT("种植材料取自背包、夹层与主仓库；每个位置种植一株。"));
    if(PlantingChoice)PlantingChoice->SetIsEnabled(Ready&&!bPlantingDragging);
    int32 Remaining=0;
    if(Plant)
    {
        const auto* CurrentRule=System->Find(Plant->Crop);Remaining=FMath::Max(0,FMath::CeilToInt(Plant->GrowthSeconds-Plant->AgeSeconds(Now)));
        const int32 Percent=FMath::Clamp(FMath::FloorToInt(Plant->AgeSeconds(Now)/FMath::Max(1.,Plant->GrowthSeconds)*100.),0,100);
        PlantingLabel(PlantingPlotText,FString::Printf(TEXT("%d 号种植位 · %s\n%s%s"),ColdSteelPlantingLayout::PlotForSlot(Plant->Slot)+1,CurrentRule?*CurrentRule->Name:TEXT("植株"),PlantingStageName(StageNow),
            StageNow==3?TEXT(" · 等待收获"):*FString::Printf(TEXT(" · %d%%\n距离成熟 %02d:%02d"),Percent,Remaining/60,Remaining%60)));
    }
    else PlantingLabel(PlantingPlotText,PlantingSelectedSlots.IsEmpty()?TEXT("请选择空闲种植位"):
        FString::Printf(TEXT("已选择 %d 个种植位\n%s"),SelectedCount,Rule?*FString::Printf(TEXT("准备播种 · %s"),*Rule->Name):TEXT("请选择作物")));
    const FString Action=Pending?TEXT("正在提交…"):Plant?(StageNow==3?FString(TEXT("收获植株")):FString::Printf(TEXT("生长中 · %02d:%02d"),Remaining/60,Remaining%60)):FString::Printf(TEXT("播种 · %d 株"),PlantingBatchCount);
    PlantingLabel(Cast<UTextBlock>(StartButton->GetContent()),Action);
    StartButton->SetIsEnabled(Ready&&!bPlantingDragging&&bCanCraft&&FPlatformTime::Seconds()>=PlantingNextActionTime);
    StartButton->SetToolTipText(FText::FromString(bCanCraft?(Plant?TEXT("收入背包并移除当前植株"):Free?TEXT("开发模式：无需种子，每个所选位置播种一株"):TEXT("一次扣除本批材料并播种；任一地块不可用则不提交")):CraftReason));
    PlantingLabel(CraftHint,Pending?TEXT("正在等待服务端种植结果…"):bCanCraft?(Plant?TEXT("已成熟 · 点击收获到背包"):Free?TEXT("无需种子已开启 · 点击播种"):TEXT("材料与所选位置可用 · 点击播种")):CraftReason);
    CraftHint->SetColorAndOpacity(bCanCraft||Pending||(Plant&&StageNow<3)?ColdSteelUI::TextSecondary:ColdSteelUI::Warning);
}

void UColdSteelWorkbenchWidget::HandlePlantingAction()
{
    if(!bInputReady||bPlantingDragging||!HUD||!HUD->IsWorkbenchOpen()||!World.IsValid())return;
    if(FPlatformTime::Seconds()<PlantingNextActionTime)return;
    PlantingNextActionTime=FPlatformTime::Seconds()+.35;
    auto* System=GetGameInstance()->GetSubsystem<UColdSteelPlantingSystem>();if(!System)return;
    if(System->Pending())return;
    const auto* Existing=PlantingSelectedSlots.IsEmpty()?System->Occupant(World.Get(),Cell,PlantingSlot):nullptr;
    const bool Harvest=Existing!=nullptr;const FGuid Expected=Existing?Existing->PlantId:FGuid();
    FString Reason;
    const bool Success=Harvest?System->Act(World.Get(),Cell,PlantingSlot,PlantingCrop,Reason,Expected)
        :System->PlantSelection(World.Get(),Cell,PlantingSelectedSlots,PlantingCrop,Reason);
    if(Success)
    {
        SetStatus(GetWorld()->GetNetMode()==NM_Standalone?(Harvest?TEXT("已收获 · 物品已放入背包"):TEXT("所选地块已全部播种 · 等待植株成熟")):System->NetworkNotice(),System->NetworkFailed());
        if(GetWorld()->GetNetMode()==NM_Standalone||(!System->Pending()&&!System->NetworkFailed())){PlantingSelectedSlots.Reset();PlantingSlot=INDEX_NONE;}
    }
    else SetStatus(Reason,true);
    bDataDirty=true;PlantingQuotedStage=-1;RefreshPlanting();SetKeyboardFocus();
}

void UColdSteelWorkbenchWidget::UpdatePlantingLayout()
{
    if(!PlantingContentLayout)return;
    // Reflow the details, not the 2x2 position map. Header and action stay in the existing fixed shell.
    const float Available=FMath::Max(160.f,(LayoutWidth>0.f?LayoutWidth:600.f)-42.f);
    const bool Stacked=Available<560.f;
    const float MapPixels=FMath::Max(96.f,FMath::Min(288.f,Stacked?Available-24.f:Available*.52f-24.f));
    PlantingContentLayout->SetColumnFill(0,Stacked?1.f:.52f);PlantingContentLayout->SetColumnFill(1,Stacked?0.f:.48f);
    PlantingDetailsSlot->SetRow(Stacked?1:0);PlantingDetailsSlot->SetColumn(Stacked?0:1);
    PlantingDetailsSlot->SetPadding(Stacked?FMargin(0):FMargin(12/Scale,0,0,0));
    PlantingMapSize->SetWidthOverride(MapPixels/Scale);PlantingMapSize->SetHeightOverride(MapPixels/Scale);
    PlantingProductSize->SetHeightOverride(80.f/Scale);
    for(int32 I=0;I<PlantingTiles.Num();++I)
    {
        auto& Tile=PlantingTiles[I];Tile.Slot->SetOffsets(FMargin(3/Scale));
        Tile.IconSize->SetWidthOverride(40/Scale);Tile.IconSize->SetHeightOverride(40/Scale);Tile.ProgressSize->SetHeightOverride(8/Scale);
        Tile.ContentSlot->SetOffsets(FMargin(6/Scale,6/Scale,6/Scale,18/Scale));
        Tile.ProgressSlot->SetOffsets(FMargin(6/Scale,-12/Scale,6/Scale,8/Scale));Tile.Progress->SetPixelScale(Scale);
        if(auto* ContentSlot=Cast<UButtonSlot>(PlantingSlotButtons[I]->GetContent()->Slot))ContentSlot->SetPadding(FMargin(0));
    }
    bDataDirty=true;
}
void UColdSteelWorkbenchWidget::SetPlantingEffectsEnabled(bool Enabled)
{for(auto& Tile:PlantingTiles)if(Tile.Progress)Tile.Progress->SetEffectsEnabled(Enabled);}
