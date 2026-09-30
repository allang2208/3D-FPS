#include "ColdSteelForgingWidget.h"
#include "ColdSteelForgeBoard.h"
#include "ColdSteelHUDWidget.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelUIStyle.h"
#include "ColdSteelItemTooltipData.h"
#include "../Weapons/GunsmithSystem.h"
#include "GunsmithUIStyle.h"
#include "../Building/ForgingSystem.h"
#include "../Building/VoxelBuildWorld.h"
#include "Engine/GameInstance.h"
#include "Engine/Texture2D.h"
#include "Blueprint/WidgetTree.h"
#include "Components/BackgroundBlur.h"
#include "Components/Border.h"
#include "Components/BorderSlot.h"
#include "Components/Button.h"
#include "Components/ButtonSlot.h"
#include "Components/GridPanel.h"
#include "Components/GridSlot.h"
#include "Components/HorizontalBox.h"
#include "Components/HorizontalBoxSlot.h"
#include "Components/Overlay.h"
#include "Components/OverlaySlot.h"
#include "Components/ProgressBar.h"
#include "Components/ScrollBox.h"
#include "Components/SizeBox.h"
#include "Components/SizeBoxSlot.h"
#include "Components/TextBlock.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "ImageUtils.h"
#include "Misc/Paths.h"
#include "Styling/SlateTypes.h"

namespace ColdSteelForgePresentation
{
void SetText(UTextBlock* Widget,const FString& Value)
{if(Widget&&Widget->GetText().ToString()!=Value)Widget->SetText(FText::FromString(Value));}
}
void UColdSteelForgingWidget::Configure(UColdSteelHUDWidget* Owner){HUD=Owner;}
UTextBlock* UColdSteelForgingWidget::Text(const FString& Caption,float Pixels,bool bNumeric,bool bMedium)
{
    auto* T=WidgetTree->ConstructWidget<UTextBlock>();T->SetText(FText::FromString(Caption));T->SetAutoWrapText(true);
    const float FontScale=Scale>0?Scale:1.f;
    T->SetFont(bNumeric?GunsmithUI::NumberFont(Pixels/FontScale,bMedium):GunsmithUI::TextFont(Pixels/FontScale,bMedium));
    T->SetColorAndOpacity(ColdSteelUI::TextPrimary);Labels.Add({T,Pixels,bNumeric,bMedium});return T;
}
UButton* UColdSteelForgingWidget::Button(const FString& Caption,UTextBlock*& Label)
{
    auto* B=WidgetTree->ConstructWidget<UButton>();Label=Text(Caption,14,false,true);Label->SetJustification(ETextJustify::Center);
    Label->SetAutoWrapText(false);Label->SetWrapTextAt(0);
    B->SetContent(Label);
    auto* LabelSlot=Cast<UButtonSlot>(Label->Slot);LabelSlot->SetHorizontalAlignment(HAlign_Fill);LabelSlot->SetVerticalAlignment(VAlign_Center);
    Buttons.Add(B);return B;
}
void UColdSteelForgingWidget::Space(UVerticalBoxSlot* RowSlot,FMargin RowPadding)
{RowSpacings.Add({RowSlot,RowPadding});}
UVerticalBox* UColdSteelForgingWidget::Card(UVerticalBox* Parent)
{
    auto* Border=WidgetTree->ConstructWidget<UBorder>();Cards.Add(Border);
    Space(Parent->AddChildToVerticalBox(Border),FMargin(0,0,0,8));
    auto* Column=WidgetTree->ConstructWidget<UVerticalBox>();Border->SetContent(Column);return Column;
}
void UColdSteelForgingWidget::AddMaterialCell(UWidget* Widget,int32 Row,int32 Column)
{
    auto* CellSlot=MaterialGrid->AddChildToGrid(Widget,Row,Column);
    CellSlot->SetHorizontalAlignment(Column==0?HAlign_Fill:HAlign_Right);
    CellSlot->SetVerticalAlignment(VAlign_Center);
    const float CellScale=Scale>0?Scale:1.f;
    CellSlot->SetPadding(FMargin(Column==0?0.f:12.f/CellScale,4.f/CellScale,0,4.f/CellScale));
    MaterialCellSlots.Add(CellSlot);
}
void UColdSteelForgingWidget::EnsureMaterialRows(int32 Count)
{
    while(MaterialRows.Num()<Count)
    {
        FMaterialRow Row;
        auto* Name=Text(TEXT(""),14);Row.Name=Name;
        auto* Amount=WidgetTree->ConstructWidget<UHorizontalBox>();Row.Amount=Amount;
        auto* Owned=Text(TEXT(""),14,true);Row.Owned=Owned;
        auto* Separator=Text(TEXT(" / "),14,true);Row.Separator=Separator;
        auto* Required=Text(TEXT(""),14,true);Row.Required=Required;
        Separator->SetColorAndOpacity(ColdSteelUI::TextSecondary);
        Required->SetColorAndOpacity(ColdSteelUI::TextSecondary);
        for(auto* Number:{Owned,Separator,Required})
        {
            Number->SetAutoWrapText(false);Number->SetJustification(ETextJustify::Right);
            Amount->AddChildToHorizontalBox(Number)->SetVerticalAlignment(VAlign_Center);
        }
        auto* State=Text(TEXT(""),14);Row.State=State;
        State->SetAutoWrapText(false);State->SetJustification(ETextJustify::Right);
        const int32 GridRow=MaterialRows.Num()+1;
        AddMaterialCell(Name,GridRow,0);AddMaterialCell(Amount,GridRow,1);AddMaterialCell(State,GridRow,2);
        Name->SetVisibility(ESlateVisibility::Collapsed);Amount->SetVisibility(ESlateVisibility::Collapsed);State->SetVisibility(ESlateVisibility::Collapsed);
        MaterialRows.Add(Row);
    }
}
void UColdSteelForgingWidget::NativeOnInitialized()
{
    Super::NativeOnInitialized();SetIsFocusable(true);
    Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();System=GetGameInstance()->GetSubsystem<UColdSteelForgingSystem>();
    if(!System->Catalog().IsEmpty())SelectedRecipe=System->Catalog()[0].Id;
    Shell=WidgetTree->ConstructWidget<UBorder>();Shell->SetHorizontalAlignment(HAlign_Fill);Shell->SetVerticalAlignment(VAlign_Fill);WidgetTree->RootWidget=Shell;
    auto* Layers=WidgetTree->ConstructWidget<UOverlay>();Shell->SetContent(Layers);
    Blur=WidgetTree->ConstructWidget<UBackgroundBlur>();auto* BlurSlot=Layers->AddChildToOverlay(Blur);BlurSlot->SetHorizontalAlignment(HAlign_Fill);BlurSlot->SetVerticalAlignment(VAlign_Fill);
    Blur->SetVisibility(ESlateVisibility::HitTestInvisible);
    auto* Tint=WidgetTree->ConstructWidget<UBorder>();Tint->SetBrushColor(ColdSteelUI::GlassTint);Tint->SetPadding(0);
    Tint->SetHorizontalAlignment(HAlign_Fill);Tint->SetVerticalAlignment(VAlign_Fill);
    auto* TintSlot=Layers->AddChildToOverlay(Tint);TintSlot->SetHorizontalAlignment(HAlign_Fill);TintSlot->SetVerticalAlignment(VAlign_Fill);
    auto* Stack=WidgetTree->ConstructWidget<UVerticalBox>();Tint->SetContent(Stack);
    Header=WidgetTree->ConstructWidget<UBorder>();Header->SetBrushColor(ColdSteelUI::HeaderTint);Stack->AddChildToVerticalBox(Header);
    auto* Head=WidgetTree->ConstructWidget<UHorizontalBox>();Header->SetContent(Head);
    auto* Title=Text(TEXT("锻造 · 铸造台"),20,false,true);auto* TitleSlot=Head->AddChildToHorizontalBox(Title);TitleSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));TitleSlot->SetVerticalAlignment(VAlign_Center);
    UTextBlock* CloseLabel=nullptr;auto* Close=Button(TEXT("×"),CloseLabel);Close->OnClicked.AddDynamic(this,&ThisClass::HandleClose);
    CloseSize=WidgetTree->ConstructWidget<USizeBox>();CloseSize->SetContent(Close);ButtonSizes.Add(CloseSize);Head->AddChildToHorizontalBox(CloseSize)->SetVerticalAlignment(VAlign_Center);
    Scroll=WidgetTree->ConstructWidget<UScrollBox>();Scroll->SetConsumeMouseWheel(EConsumeMouseWheel::Always);Stack->AddChildToVerticalBox(Scroll)->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    Body=WidgetTree->ConstructWidget<UBorder>();Body->SetBrushColor(FLinearColor::Transparent);Scroll->AddChild(Body);
    auto* Content=WidgetTree->ConstructWidget<UVerticalBox>();Body->SetContent(Content);
    auto* RecipeCard=Card(Content);
    auto* RecipeCaption=Text(TEXT("配方 · 工件"),12);RecipeCaption->SetColorAndOpacity(ColdSteelUI::TextTertiary);Space(RecipeCard->AddChildToVerticalBox(RecipeCaption),FMargin(0,0,0,4));
    RecipeTitle=Text(TEXT("—"),16,false,true);Space(RecipeCard->AddChildToVerticalBox(RecipeTitle),FMargin(0,0,0,8));
    RecipeChoice=WidgetTree->ConstructWidget<UComboBoxString>();
    RecipeChoice->OnGenerateWidgetEvent.BindDynamic(this,&ThisClass::GenerateRecipeOption);
    for(const auto& Recipe:System->Catalog())
        RecipeChoice->AddOption(ColdSteelInventory::Text(Model->CreateItem(Recipe.Output),TEXT("name")));
    RecipeChoice->OnSelectionChanged.AddDynamic(this,&ThisClass::HandleRecipeSelected);
    RecipeChoice->SetToolTipText(FText::FromString(TEXT("选择锻造配方；当前工件需领取或废弃后才能更换。")));
    auto* ChoiceSize=WidgetTree->ConstructWidget<USizeBox>();ChoiceSize->SetContent(RecipeChoice);ButtonSizes.Add(ChoiceSize);
    Space(RecipeCard->AddChildToVerticalBox(ChoiceSize),FMargin(0,0,0,8));
    Materials=Text(TEXT("所需材料"),14,false,true);Space(RecipeCard->AddChildToVerticalBox(Materials),FMargin(0,0,0,4));
    auto* Source=Text(TEXT("材料来源 · 背包 + 主仓库"),12);Source->SetColorAndOpacity(ColdSteelUI::TextTertiary);MaterialSource=Source;
    Space(RecipeCard->AddChildToVerticalBox(Source),FMargin(0,0,0,4));
    auto* Grid=WidgetTree->ConstructWidget<UGridPanel>();MaterialGrid=Grid;Grid->SetColumnFill(0,1.f);RecipeCard->AddChildToVerticalBox(Grid);
    auto* NameHeader=Text(TEXT("材料"),12);auto* QuantityHeader=Text(TEXT("持有 / 需要"),12);auto* StateHeader=Text(TEXT("状态"),12);
    MaterialQuantityHeader=QuantityHeader;
    for(auto* Label:{NameHeader,QuantityHeader,StateHeader}){Label->SetColorAndOpacity(ColdSteelUI::TextSecondary);Label->SetAutoWrapText(false);}
    AddMaterialCell(NameHeader,0,0);AddMaterialCell(QuantityHeader,0,1);AddMaterialCell(StateHeader,0,2);
    int32 MaterialRowCount=0;
    for(const auto& Recipe:System->Catalog())MaterialRowCount=FMath::Max(MaterialRowCount,Recipe.Inputs.Num());
    EnsureMaterialRows(MaterialRowCount);
    auto* StateCard=Card(Content);
    Stage=Text(TEXT("准备锻造"),16,false,true);Space(StateCard->AddChildToVerticalBox(Stage),FMargin(0,0,0,8));
    Stats=Text(TEXT(""),16,true);Space(StateCard->AddChildToVerticalBox(Stats),FMargin(0,0,0,4));
    StatLegend=Text(TEXT("剩余时间   /   有效命中   /   工艺伤害"),12);StatLegend->SetColorAndOpacity(ColdSteelUI::TextTertiary);StateCard->AddChildToVerticalBox(StatLegend);
    RefundPreview=Text(TEXT(""),12);RefundPreview->SetColorAndOpacity(ColdSteelUI::TextSecondary);Space(StateCard->AddChildToVerticalBox(RefundPreview),FMargin(0,8,0,0));
    Timer=WidgetTree->ConstructWidget<UProgressBar>();Timer->SetFillColorAndOpacity(ColdSteelUI::Accent);
    TimerSize=WidgetTree->ConstructWidget<USizeBox>();TimerSize->SetContent(Timer);Space(StateCard->AddChildToVerticalBox(TimerSize),FMargin(0,8,0,0));
    auto* PreviewCaption=Text(TEXT("成品预览 · 剑类共用剑胚"),14,false,true);Space(Content->AddChildToVerticalBox(PreviewCaption),FMargin(0,4,0,8));
    BoardSize=WidgetTree->ConstructWidget<USizeBox>();
    auto* PreviewColumns=WidgetTree->ConstructWidget<UHorizontalBox>();BoardSize->SetContent(PreviewColumns);
    Space(Content->AddChildToVerticalBox(BoardSize),FMargin(0,0,0,8));
    Board=WidgetTree->ConstructWidget<UColdSteelForgeBoard>();
    PreviewColumns->AddChildToHorizontalBox(Board)->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    auto* Parameters=WidgetTree->ConstructWidget<UBorder>();Cards.Add(Parameters);
    PreviewParameterSlot=PreviewColumns->AddChildToHorizontalBox(Parameters);
    PreviewParameterSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    auto* ParameterScroll=WidgetTree->ConstructWidget<UScrollBox>();Parameters->SetContent(ParameterScroll);
    auto* ParameterContent=WidgetTree->ConstructWidget<UVerticalBox>();ParameterScroll->AddChild(ParameterContent);
    PreviewName=Text(TEXT("—"),16,false,true);Space(ParameterContent->AddChildToVerticalBox(PreviewName),FMargin(0,0,0,8));
    PreviewStage=Text(TEXT("配方基础参数 · 未计锻造品质"),12);PreviewStage->SetColorAndOpacity(ColdSteelUI::TextSecondary);
    Space(ParameterContent->AddChildToVerticalBox(PreviewStage),FMargin(0,0,0,12));
    PreviewParameterGrid=WidgetTree->ConstructWidget<UGridPanel>();PreviewParameterGrid->SetColumnFill(0,1.f);
    ParameterContent->AddChildToVerticalBox(PreviewParameterGrid);
    PreviewScope=Text(TEXT(""),12);PreviewScope->SetColorAndOpacity(ColdSteelUI::TextTertiary);
    Space(ParameterContent->AddChildToVerticalBox(PreviewScope),FMargin(0,12,0,0));
    auto* Instructions=Card(Content);Space(Instructions->AddChildToVerticalBox(Text(TEXT("操作说明"),16,false,true)),FMargin(0,0,0,8));
    auto* Help=Text(TEXT("光圈与命中范围随时间缩小，直到消失。移动鼠标对准后左键落锤，出锤时锁定大小，锤头接触时判定。"),14);Space(Instructions->AddChildToVerticalBox(Help),FMargin(0,0,0,8));
    auto* Rule=Text(FString::Printf(TEXT("每轮 20 处光圈 · 单处随机停留 %.1f～%.1f 秒，出锤后锁定至接触\n落锤后随机间隔 %.2f～%.2f 秒，且等待回锤完成 · 10 次命中为基础品质\n伤害浮动 −25%% ～ ＋25%%"),System->HitWindowMin,System->HitWindowMax,System->TargetGapMin,System->TargetGapMax),12);Rule->SetColorAndOpacity(ColdSteelUI::TextSecondary);Space(Instructions->AddChildToVerticalBox(Rule),FMargin(0,0,0,8));
    auto* Exit=Text(TEXT("开始时扣除材料。中途返回按当前命中数结算；成品可领取或直接废弃。废弃返还一半材料至背包，每种材料的零头向下取整。"),12);Exit->SetColorAndOpacity(ColdSteelUI::TextTertiary);Instructions->AddChildToVerticalBox(Exit);
    Footer=WidgetTree->ConstructWidget<UBorder>();Footer->SetBrushColor(ColdSteelUI::HeaderTint);Stack->AddChildToVerticalBox(Footer);
    auto* Foot=WidgetTree->ConstructWidget<UVerticalBox>();Footer->SetContent(Foot);
    Status=Text(TEXT(""),14);Status->SetColorAndOpacity(ColdSteelUI::TextSecondary);Space(Foot->AddChildToVerticalBox(Status),FMargin(0,0,0,8));
    auto* Actions=WidgetTree->ConstructWidget<UHorizontalBox>();Foot->AddChildToVerticalBox(Actions);
    UTextBlock* NewActionLabel=nullptr;ActionButton=Button(TEXT("开始锻造"),NewActionLabel);ActionLabel=NewActionLabel;ActionButton->OnClicked.AddDynamic(this,&ThisClass::HandleAction);
    auto* ActionSize=WidgetTree->ConstructWidget<USizeBox>();ActionSize->SetContent(ActionButton);ButtonSizes.Add(ActionSize);Actions->AddChildToHorizontalBox(ActionSize)->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    UTextBlock* DiscardLabel=nullptr;DiscardButton=Button(TEXT("废弃 · 返还一半"),DiscardLabel);DiscardButton->OnClicked.AddDynamic(this,&ThisClass::HandleDiscard);
    DiscardButton->SetToolTipText(FText::FromString(TEXT("直接废弃未领取的成品，返还一半投入材料至背包（逐项向下取整）。背包空间不足时保留成品。")));
    auto* DiscardSize=WidgetTree->ConstructWidget<USizeBox>();DiscardSize->SetContent(DiscardButton);ButtonSizes.Add(DiscardSize);DiscardActionSlot=Actions->AddChildToHorizontalBox(DiscardSize);DiscardActionSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    UTextBlock* SmeltLabel=nullptr;SmeltingButton=Button(TEXT("冶炼队列 / 领锭"),SmeltLabel);SmeltingButton->OnClicked.AddDynamic(this,&ThisClass::HandleSmelting);
    auto* SmeltSize=WidgetTree->ConstructWidget<USizeBox>();SmeltSize->SetContent(SmeltingButton);ButtonSizes.Add(SmeltSize);SecondaryActionSlot=Actions->AddChildToHorizontalBox(SmeltSize);SecondaryActionSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    UpdateScale();LoadMold();Refresh();
}
void UColdSteelForgingWidget::NativeConstruct()
{
    Super::NativeConstruct();if(Model&&!ChangedHandle.IsValid())ChangedHandle=Model->OnChanged.AddWeakLambda(this,[this]{bMaterialsDirty=true;});
}
void UColdSteelForgingWidget::NativeDestruct()
{
    if(Model&&ChangedHandle.IsValid()){Model->OnChanged.Remove(ChangedHandle);ChangedHandle.Reset();}
    Super::NativeDestruct();
}
void UColdSteelForgingWidget::SetStation(AVoxelBuildWorld* InWorld,FIntVector InCell)
{
    World=InWorld;Cell=InCell;Notice.Reset();bMaterialsDirty=true;
    if(System&&!System->Active()&&!System->Job().Id.IsEmpty()&&!System->Job().bFinished)System->Finish(Notice);
    if(System&&!System->Job().Id.IsEmpty())SelectedRecipe=System->Job().Recipe;
    LoadMold();Refresh();
}
void UColdSteelForgingWidget::SetInputReady(bool bReady)
{
    if(bInputReady==bReady)return;bInputReady=bReady;if(Board)Board->SetIsEnabled(bReady);Refresh();
}
void UColdSteelForgingWidget::LoadMold()
{
    const auto* Recipe=System?System->Find(SelectedRecipe):nullptr;if(!Recipe||LoadedMold==Recipe->Mold)return;
    LoadedMold=Recipe->Mold;MoldTexture=FImageUtils::ImportFileAsTexture2D(FPaths::ProjectContentDir()/TEXT("ColdSteelData")/Recipe->Mold);
    if(Board)Board->Configure(nullptr,MoldTexture); // Recipe reference only; world contact owns scoring.
}
void UColdSteelForgingWidget::RefreshProductPreview()
{
    using ColdSteelForgePresentation::SetText;
    const auto* Recipe=System->Find(SelectedRecipe);
    const auto& Job=System->Job();
    const bool HasJob=!Job.Id.IsEmpty();
    const FColdSteelItem Item=HasJob?Job.Item:Recipe?Model->CreateItem(Recipe->Output):FColdSteelItem{};
    const auto Data=Item.Data.IsEmpty()?FColdSteelTooltipContent{}:
        BuildColdSteelItemTooltip(Item,Model,GetGameInstance()->GetSubsystem<UGunsmithSystem>());
    SetText(PreviewName,Data.Name.IsEmpty()?TEXT("暂无成品参数"):Data.Name);
    SetText(PreviewStage,HasJob&&Job.bFinished?TEXT("成品实际参数 · 已计锻造品质"):TEXT("配方基础参数 · 未计锻造品质"));
    SetText(PreviewScope,Data.ValueScope);
    while(PreviewRows.Num()<Data.Summary.Num())
    {
        const int32 Index=PreviewRows.Num();
        auto* Name=Text(TEXT(""),14);Name->SetColorAndOpacity(ColdSteelUI::TextSecondary);
        auto* Value=Text(TEXT(""),14,true);Value->SetJustification(ETextJustify::Right);
        const float S=FMath::Max(.1f,Scale);
        for(int32 Column=0;Column<2;++Column)
        {
            auto* ParameterCellSlot=PreviewParameterGrid->AddChildToGrid(Column==0?Name:Value,Index,Column);
            ParameterCellSlot->SetVerticalAlignment(VAlign_Center);ParameterCellSlot->SetHorizontalAlignment(HAlign_Fill);
            ParameterCellSlot->SetPadding(FMargin(Column==0?0.f:12.f/S,6.f/S,0,6.f/S));PreviewCellSlots.Add(ParameterCellSlot);
        }
        PreviewRows.Add({Name,Value});
    }
    for(int32 Index=0;Index<PreviewRows.Num();++Index)
    {
        const auto& Row=PreviewRows[Index];const bool Visible=Data.Summary.IsValidIndex(Index);
        Row.Name->SetVisibility(Visible?ESlateVisibility::HitTestInvisible:ESlateVisibility::Collapsed);
        Row.Value->SetVisibility(Visible?ESlateVisibility::HitTestInvisible:ESlateVisibility::Collapsed);
        if(Visible){SetText(Row.Name.Get(),Data.Summary[Index].Label);SetText(Row.Value.Get(),Data.Summary[Index].Value);}
    }
}
void UColdSteelForgingWidget::UpdateScale()
{
    const float NewScale=ColdSteelUI::PixelScale(this);if(FMath::IsNearlyEqual(Scale,NewScale,.001f))return;Scale=FMath::Max(.1f,NewScale);
    for(const auto& L:Labels)if(auto* T=L.Widget.Get())T->SetFont(L.Numeric?GunsmithUI::NumberFont(L.Pixels/Scale,L.Medium):GunsmithUI::TextFont(L.Pixels/Scale,L.Medium));
    for(const auto& W:Buttons)if(auto* B=W.Get()){B->SetStyle(ColdSteelUI::ButtonStyle(Scale));if(auto* ButtonSlot=Cast<UButtonSlot>(B->GetContent()->Slot))ButtonSlot->SetPadding(FMargin(12/Scale,4/Scale));}
    for(const auto& W:ButtonSizes)if(auto* S=W.Get())S->SetHeightOverride(ColdSteelUI::ActionHeight/Scale);
    CloseSize->SetWidthOverride(ColdSteelUI::ActionHeight/Scale);SecondaryActionSlot->SetPadding(FMargin(ColdSteelUI::ActionGap/Scale,0,0,0));
    DiscardActionSlot->SetPadding(FMargin(ColdSteelUI::ActionGap/Scale,0,0,0));
    auto ComboStyle=RecipeChoice->GetWidgetStyle();auto ComboButton=ComboStyle.ComboButtonStyle;
    ComboButton.SetButtonStyle(ColdSteelUI::ButtonStyle(Scale));
    ComboButton.SetMenuBorderBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::Gray(25,252),ColdSteelUI::CardRadius/Scale,ColdSteelUI::Border,1/Scale));
    ComboButton.DownArrowImage.ImageSize=FVector2D(8/Scale,8/Scale);
    ComboButton.SetDownArrowPadding(FMargin(4/Scale,0,0,0));ComboButton.SetShadowOffset(FVector2D::ZeroVector);
    ComboStyle.SetComboButtonStyle(ComboButton);RecipeChoice->SetWidgetStyle(ComboStyle);
    RecipeChoice->SetContentPadding(FMargin(22/Scale,4/Scale,10/Scale,4/Scale));
    RecipeChoice->SetMaxListHeight(240/Scale);
    auto ItemStyle=RecipeChoice->GetItemStyle();
    ItemStyle.SetEvenRowBackgroundBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::Content,ColdSteelUI::ButtonRadius/Scale));
    ItemStyle.SetOddRowBackgroundBrush(ItemStyle.EvenRowBackgroundBrush);
    ItemStyle.SetEvenRowBackgroundHoveredBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonHover,ColdSteelUI::ButtonRadius/Scale));
    ItemStyle.SetOddRowBackgroundHoveredBrush(ItemStyle.EvenRowBackgroundHoveredBrush);
    ItemStyle.SetActiveBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonHover,ColdSteelUI::ButtonRadius/Scale,ColdSteelUI::Accent,1/Scale));
    ItemStyle.SetInactiveBrush(ItemStyle.ActiveBrush);RecipeChoice->SetItemStyle(ItemStyle);
    // Symmetric padding keeps the two visible halves equally wide.
    if(auto* LeftSlot=Cast<UHorizontalBoxSlot>(Board->Slot))LeftSlot->SetPadding(FMargin(0,0,4/Scale,0));
    PreviewParameterSlot->SetPadding(FMargin(4/Scale,0,0,0));
    for(const auto& PreviewCell:PreviewCellSlots)if(auto* S=PreviewCell.Get())
        S->SetPadding(FMargin(S->GetColumn()==0?0.f:12.f/Scale,6.f/Scale,0,6.f/Scale));
    for(const auto& C:Cards)if(auto* Border=C.Get()){Border->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::StatusCard,ColdSteelUI::CardRadius/Scale,ColdSteelUI::Border,1/Scale));Border->SetPadding(12/Scale);}
    for(const auto& Row:RowSpacings)if(auto* RowSlot=Row.Slot.Get())RowSlot->SetPadding(Row.Padding*(1.f/Scale));
    for(const auto& MaterialCell:MaterialCellSlots)if(auto* CellSlot=MaterialCell.Get())
        CellSlot->SetPadding(FMargin(CellSlot->GetColumn()==0?0.f:12.f/Scale,4.f/Scale,0,4.f/Scale));
    Scroll->SetScrollbarThickness(FVector2D(6/Scale,6/Scale));Scroll->SetScrollbarPadding(FMargin(4/Scale,0,0,0));
    TimerSize->SetHeightOverride(3/Scale);
    FProgressBarStyle Progress;Progress.SetBackgroundImage(ColdSteelUI::RoundedBrush(ColdSteelUI::Gray(45),1.5f/Scale,FLinearColor::Transparent,0));
    Progress.SetFillImage(ColdSteelUI::RoundedBrush(FLinearColor::White,1.5f/Scale,FLinearColor::Transparent,0));Timer->SetWidgetStyle(Progress);
    Shell->SetBrush(ColdSteelUI::RoundedBrush(FLinearColor::Transparent,ColdSteelUI::PanelRadius/Scale,ColdSteelUI::Border,1/Scale));Shell->SetPadding(1/Scale);
    Blur->SetBlurStrength(ColdSteelUI::GlassBlurStrength);Blur->SetBlurRadius(ColdSteelUI::GlassBlurRadius);Blur->SetCornerRadius(FVector4(10,10,10,10)/Scale);
    Blur->SetLowQualityFallbackBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::GlassFallback,10/Scale));
    Header->SetPadding(FMargin(18/Scale,12/Scale));Body->SetPadding(12/Scale);Footer->SetPadding(12/Scale);
}
void UColdSteelForgingWidget::NativeTick(const FGeometry& Geometry,float DeltaTime)
{
    Super::NativeTick(Geometry,DeltaTime);UpdateScale();
    const float Height=FMath::Clamp(float(Geometry.GetLocalSize().Y)*Scale-520.f,200.f,420.f)/Scale;
    if(!FMath::IsNearlyEqual(Height,BoardHeight,.5f)){BoardHeight=Height;BoardSize->SetHeightOverride(Height);}
    RefreshClock+=DeltaTime;
    if(RefreshClock>=.05f){RefreshClock=0;Refresh();}
}
void UColdSteelForgingWidget::Refresh()
{
    using ColdSteelForgePresentation::SetText;
    if(!System||!Model||!ActionButton)return;
    const auto& Job=System->Job();const bool Pending=!Job.Id.IsEmpty(),Active=System->Active();
    if(Pending&&SelectedRecipe!=Job.Recipe)
    {SelectedRecipe=Job.Recipe;bMaterialsDirty=true;LoadMold();}
    const auto* Recipe=System->Find(SelectedRecipe);
    if(bMaterialsDirty)
    {
        RefreshProductPreview();
        const int32 Index=System->Catalog().IndexOfByPredicate([this](const auto& R){return R.Id==SelectedRecipe;});
        if(RecipeChoice->GetSelectedIndex()!=Index)RecipeChoice->SetSelectedIndex(Index);
        SetText(RecipeTitle,Recipe?FString::Printf(TEXT("%d / %d · %s"),Index+1,System->Catalog().Num(),
            *ColdSteelInventory::Text(Model->CreateItem(Recipe->Output),TEXT("name"))):TEXT("配方未就绪"));
        TArray<FColdSteelCraftingInput> DisplayInputs;
        bool bPaidAvailable=true;
        if(Pending)
        {
            TMap<FString,int64> Paid;bPaidAvailable=System->GetPaidMaterials(Paid);
            // Preserve recipe order, then show any paid materials from an older recipe.
            if(Recipe)for(const auto& Input:Recipe->Inputs)if(const auto* Count=Paid.Find(Input.Item))
            {DisplayInputs.Add({Input.Item,*Count});Paid.Remove(Input.Item);}
            TArray<FString> Definitions;Paid.GetKeys(Definitions);Definitions.Sort();
            for(const auto& Definition:Definitions)DisplayInputs.Add({Definition,Paid[Definition]});
        }
        else if(Recipe)DisplayInputs=Recipe->Inputs;
        SetText(Materials,Pending?TEXT("本轮已投入材料"):TEXT("所需材料"));
        SetText(MaterialSource.Get(),Pending?(bPaidAvailable?TEXT("本轮材料已扣除"):TEXT("投入材料记录不可用"))
            :Recipe?TEXT("材料来源 · 背包 + 主仓库"):TEXT("暂无可用配方"));
        SetText(MaterialQuantityHeader.Get(),Pending?TEXT("已投入数量"):TEXT("持有 / 需要"));
        EnsureMaterialRows(DisplayInputs.Num());
        for(int32 MaterialIndex=0;MaterialIndex<MaterialRows.Num();++MaterialIndex)
        {
            const auto& Row=MaterialRows[MaterialIndex];
            const bool bHasInput=DisplayInputs.IsValidIndex(MaterialIndex);
            const auto RowVisibility=bHasInput?ESlateVisibility::HitTestInvisible:ESlateVisibility::Collapsed;
            Row.Name->SetVisibility(RowVisibility);Row.Amount->SetVisibility(RowVisibility);Row.State->SetVisibility(RowVisibility);
            if(!bHasInput)continue;
            const auto& Input=DisplayInputs[MaterialIndex];const int64 Owned=Pending?Input.Count:Model->CountMaterial(Input.Item);
            SetText(Row.Name.Get(),ColdSteelInventory::Text(Model->CreateItem(Input.Item),TEXT("name")));
            SetText(Row.Owned.Get(),FString::Printf(TEXT("%lld"),Owned));
            SetText(Row.Required.Get(),FString::Printf(TEXT("%lld"),Input.Count));
            Row.Separator->SetVisibility(Pending?ESlateVisibility::Collapsed:ESlateVisibility::HitTestInvisible);
            Row.Required->SetVisibility(Pending?ESlateVisibility::Collapsed:ESlateVisibility::HitTestInvisible);
            const bool bEnough=Owned>=Input.Count;
            const FLinearColor QuantityColor=Pending?ColdSteelUI::TextPrimary:bEnough?ColdSteelUI::Success:ColdSteelUI::Danger;
            Row.Owned->SetColorAndOpacity(QuantityColor);
            SetText(Row.State.Get(),Pending?TEXT("已投入"):bEnough?TEXT("已满足"):FString::Printf(TEXT("缺 %lld"),Input.Count-Owned));
            Row.State->SetColorAndOpacity(Pending?ColdSteelUI::TextSecondary:QuantityColor);
        }
        bCanStart=System->CanStart(SelectedRecipe,StartReason);
        TArray<FColdSteelCraftingInput> Refund;FString RefundReason;
        bCanDiscard=System->GetDiscardRefund(Refund,RefundReason);
        if(bCanDiscard)
        {
            TArray<FString> Returned;
            for(const auto& In:Refund)Returned.Add(FString::Printf(TEXT("%s × %lld"),*ColdSteelInventory::Text(Model->CreateItem(In.Item),TEXT("name")),In.Count));
            RefundReason=Returned.IsEmpty()?TEXT("废弃返还：无（各项材料折半不足 1 个）")
                :TEXT("废弃返还至背包：")+FString::Join(Returned,TEXT("、"));
        }
        SetText(RefundPreview,RefundReason);bMaterialsDirty=false;
    }
    RefundPreview->SetVisibility(Pending&&Job.bFinished&&!Active?ESlateVisibility::HitTestInvisible:ESlateVisibility::Collapsed);
    const int32 Hits=Pending?Job.Hits:0;const double Percent=(System->Multiplier(Hits)-1)*100;
    if(Active)
    {
        const double T=System->Elapsed();SetText(Stage,T<0?FString::Printf(TEXT("准备 · %d"),FMath::CeilToInt(-T)):TEXT("锻打中"));
        SetText(Stats,FString::Printf(TEXT("%02d / 20   |   %02d / 20   |   %+.1f%%"),System->ResolvedTargets(),Hits,Percent));
        Timer->SetPercent(float(System->ResolvedTargets())/System->TargetCount);
    }
    else
    {
        SetText(Stage,Pending?(Job.bFinished?TEXT("锻造完成 · ")+System->Quality(Hits):TEXT("工件待结算")):TEXT("选择工件 · 准备锻造"));
        SetText(Stats,Pending?FString::Printf(TEXT("%02d / 20   |   %+.1f%%"),Hits,Percent):TEXT("2.5 s   |   20 处   |   −25% ～ ＋25%"));Timer->SetPercent(Pending?float(Hits)/20.f:0.f);
    }
    SetText(StatLegend,Active?TEXT("已处理光圈   /   有效命中   /   工艺伤害"):Pending?TEXT("有效命中   /   工艺伤害"):TEXT("单点停留   /   光圈总数   /   伤害范围"));
    Stats->SetColorAndOpacity(!Pending?ColdSteelUI::TextSecondary:Percent>0?ColdSteelUI::Success:Percent<0?ColdSteelUI::Danger:ColdSteelUI::TextPrimary);
    SetText(ActionLabel,Active?TEXT("锻打进行中"):Pending?(Job.bFinished?TEXT("领取成品"):TEXT("重试结算")):TEXT("开始锻造"));
    FString Reason;bool Can=false;
    if(!Active&&!Pending){Can=bCanStart;Reason=StartReason;FString ReadyReason;if(!HUD||!HUD->CanStartWorldForging(ReadyReason)){Can=false;Reason=ReadyReason;}}
    else if(Pending&&!Active){Can=true;Reason=Job.bFinished?TEXT("领取成品，或废弃返还一半材料；背包需有足够空间。"):TEXT("工件尚未结算，请重试结算。");}
    else Reason=TEXT("锤头接触热区时计分；每次命中增加 2.5% 工艺伤害。");
    ActionButton->SetIsEnabled(bInputReady&&Can);
    const bool bCanChoose=bInputReady&&!Active&&!Pending&&System->Catalog().Num()>1;
    RecipeChoice->SetIsEnabled(bCanChoose);
    DiscardButton->SetIsEnabled(bInputReady&&Pending&&Job.bFinished&&!Active&&bCanDiscard);
    FIntVector Furnace;const bool Linked=World.IsValid()&&World->FindCastingFurnace(Cell,Furnace);
    SmeltingButton->SetIsEnabled(bInputReady&&Linked&&!Active);
    SetText(Status,!System->Error().IsEmpty()?System->Error():!Notice.IsEmpty()?Notice:Reason);
}
void UColdSteelForgingWidget::HandleAction()
{
    if(!bInputReady||!System||System->Active())return;
    Notice.Reset();
    if(!System->Job().Id.IsEmpty()){if(System->Job().bFinished)System->Claim(Notice);else System->Finish(Notice);}
    else if(HUD&&HUD->StartWorldForging(SelectedRecipe,Notice)){Notice.Reset();bMaterialsDirty=true;Refresh();return;}
    bMaterialsDirty=true;SetKeyboardFocus();Refresh();
}
void UColdSteelForgingWidget::HandleClose(){if(HUD)HUD->CloseForging();}
void UColdSteelForgingWidget::HandleDiscard()
{
    if(!bInputReady||!System||System->Active())return;
    Notice.Reset();System->Discard(Notice);
    bMaterialsDirty=true;SetKeyboardFocus();Refresh();
}
void UColdSteelForgingWidget::HandleSmelting(){if(HUD&&!System->Active())HUD->OpenForgingSmelting();}
UWidget* UColdSteelForgingWidget::GenerateRecipeOption(FString Option)
{
    auto* Label=Text(Option,14,false,true);Label->SetJustification(ETextJustify::Center);
    auto* OptionBox=WidgetTree->ConstructWidget<USizeBox>();OptionBox->SetMinDesiredHeight(ColdSteelUI::ActionHeight/FMath::Max(.1f,ColdSteelUI::PixelScale(this)));
    OptionBox->SetContent(Label);Cast<USizeBoxSlot>(Label->Slot)->SetVerticalAlignment(VAlign_Center);
    return OptionBox;
}
void UColdSteelForgingWidget::HandleRecipeSelected(FString Option,ESelectInfo::Type SelectionType)
{
    if(SelectionType==ESelectInfo::Direct||!System)return;
    const auto& Catalog=System->Catalog();
    const int32 Index=RecipeChoice->GetSelectedIndex();
    if(!bInputReady||System->Active()||!System->Job().Id.IsEmpty()||!Catalog.IsValidIndex(Index))
    {
        RecipeChoice->SetSelectedIndex(Catalog.IndexOfByPredicate([this](const auto& R){return R.Id==SelectedRecipe;}));return;
    }
    if(SelectedRecipe==Catalog[Index].Id)return;
    SelectedRecipe=Catalog[Index].Id;Notice.Reset();bMaterialsDirty=true;
    LoadMold();Refresh();SetKeyboardFocus();
}
FReply UColdSteelForgingWidget::NativeOnMouseButtonDown(const FGeometry&,const FPointerEvent&){return FReply::Handled();}
