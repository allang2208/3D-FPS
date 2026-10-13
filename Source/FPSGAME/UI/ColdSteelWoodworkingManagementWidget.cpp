#include "ColdSteelWoodworkingManagementWidget.h"
#include "ColdSteelForgeBoard.h"
#include "../Building/WoodworkingQuality.h"
#include "ColdSteelGunRecipeOptionWidget.h"
#include "ColdSteelWoodworkingWidget.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelUIStyle.h"
#include "ColdSteelItemTooltipData.h"
#include "../Weapons/GunsmithSystem.h"
#include "GunsmithUIStyle.h"
#include "../Building/WoodworkingSystem.h"
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

namespace ColdSteelWoodManagementPresentation
{
void SetText(UTextBlock* Widget,const FString& Value)
{if(Widget&&Widget->GetText().ToString()!=Value)Widget->SetText(FText::FromString(Value));}
}
void UColdSteelWoodworkingManagementWidget::Configure(UColdSteelWoodworkingWidget* Owner)
{OwnerWidget=Owner;bMaterialsDirty=true;Refresh();}
bool UColdSteelWoodworkingManagementWidget::IsRecipeMenuOpen() const {return RecipeChoice&&RecipeChoice->IsOpen();}
const FColdSteelCraftingRecipe* UColdSteelWoodworkingManagementWidget::Recipe() const
{
    const auto* Pattern=System?System->Pattern():nullptr;
    auto* Craft=GetGameInstance()->GetSubsystem<UColdSteelCraftingSystem>();
    return Pattern&&Craft?Craft->Find(Pattern->CraftRecipe):nullptr;
}
void UColdSteelWoodworkingManagementWidget::CacheProductImages()
{
    // At most the two catalog products plus an older pending job. Import only during initialization.
    auto Cache=[this](const FColdSteelItem& Item)
    {
        const FString Path=ColdSteelInventory::Text(Item,TEXT("ue_icon"));
        if(!Path.IsEmpty()&&!ProductImages.Contains(Path))
            ProductImages.Add(Path,FImageUtils::ImportFileAsTexture2D(FPaths::ProjectContentDir()/TEXT("ColdSteelData")/Path));
    };
    auto* Craft=GetGameInstance()->GetSubsystem<UColdSteelCraftingSystem>();
    for(const auto& Pattern:System->Patterns())if(const auto* Entry=Craft->Find(Pattern.CraftRecipe))Cache(Model->CreateItem(Entry->Output));
    if(System->HasPendingJob())Cache(System->Job().Item);
}
UTextBlock* UColdSteelWoodworkingManagementWidget::Text(const FString& Caption,float Pixels,bool bNumeric,bool bMedium)
{
    auto* T=WidgetTree->ConstructWidget<UTextBlock>();T->SetText(FText::FromString(Caption));T->SetAutoWrapText(false);
    const float FontScale=Scale>0?Scale:1.f;
    T->SetFont(bNumeric?GunsmithUI::NumberFont(Pixels/FontScale,bMedium):GunsmithUI::TextFont(Pixels/FontScale,bMedium));
    T->SetColorAndOpacity(ColdSteelUI::TextPrimary);Labels.Add({T,Pixels,bNumeric,bMedium});return T;
}
UButton* UColdSteelWoodworkingManagementWidget::Button(const FString& Caption,UTextBlock*& Label)
{
    auto* B=WidgetTree->ConstructWidget<UButton>();Label=Text(Caption,14,false,true);Label->SetJustification(ETextJustify::Center);
    Label->SetAutoWrapText(false);Label->SetWrapTextAt(0);
    B->SetContent(Label);
    auto* LabelSlot=Cast<UButtonSlot>(Label->Slot);LabelSlot->SetHorizontalAlignment(HAlign_Fill);LabelSlot->SetVerticalAlignment(VAlign_Center);
    Buttons.Add(B);return B;
}
void UColdSteelWoodworkingManagementWidget::Space(UVerticalBoxSlot* RowSlot,FMargin RowPadding)
{RowSpacings.Add({RowSlot,RowPadding});}
UVerticalBox* UColdSteelWoodworkingManagementWidget::Card(UVerticalBox* Parent)
{
    auto* Border=WidgetTree->ConstructWidget<UBorder>();Cards.Add(Border);
    Space(Parent->AddChildToVerticalBox(Border),FMargin(0,0,0,8));
    auto* Column=WidgetTree->ConstructWidget<UVerticalBox>();Border->SetContent(Column);return Column;
}
void UColdSteelWoodworkingManagementWidget::AddMaterialCell(UWidget* Widget,int32 Row,int32 Column)
{
    auto* CellSlot=MaterialGrid->AddChildToGrid(Widget,Row,Column);
    CellSlot->SetHorizontalAlignment(Column==0?HAlign_Fill:HAlign_Right);
    CellSlot->SetVerticalAlignment(VAlign_Center);
    const float CellScale=Scale>0?Scale:1.f;
    CellSlot->SetPadding(FMargin(Column==0?0.f:12.f/CellScale,4.f/CellScale,0,4.f/CellScale));
    MaterialCellSlots.Add(CellSlot);
}
void UColdSteelWoodworkingManagementWidget::EnsureMaterialRows(int32 Count)
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
void UColdSteelWoodworkingManagementWidget::NativeOnInitialized()
{
    Super::NativeOnInitialized();SetIsFocusable(true);
    Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();System=GetGameInstance()->GetSubsystem<UWoodworkingSystem>();
    CacheProductImages();
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
    auto* Title=Text(TEXT("木工 · 工作台"),20,false,true);auto* TitleSlot=Head->AddChildToHorizontalBox(Title);TitleSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));TitleSlot->SetVerticalAlignment(VAlign_Center);
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
    auto* Craft=GetGameInstance()->GetSubsystem<UColdSteelCraftingSystem>();
    for(const auto& Pattern:System->Patterns())
    {
        const auto* Entry=Craft->Find(Pattern.CraftRecipe);
        RecipeChoice->AddOption(Entry?ColdSteelInventory::Text(Model->CreateItem(Entry->Output),TEXT("name")):Pattern.Name);
    }
    RecipeChoice->OnSelectionChanged.AddDynamic(this,&ThisClass::HandleRecipeSelected);
    RecipeChoice->SetToolTipText(FText::FromString(TEXT("选择木工配方；当前工件需领取或废弃后才能更换。")));
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
    for(const auto& Pattern:System->Patterns())if(const auto* Entry=Craft->Find(Pattern.CraftRecipe))MaterialRowCount=FMath::Max(MaterialRowCount,Entry->Inputs.Num());
    EnsureMaterialRows(MaterialRowCount);
    auto* StateCard=Card(Content);
    Stage=Text(TEXT("准备加工"),16,false,true);Space(StateCard->AddChildToVerticalBox(Stage),FMargin(0,0,0,8));
    Stats=Text(TEXT(""),16,true);Space(StateCard->AddChildToVerticalBox(Stats),FMargin(0,0,0,4));
    StatLegend=Text(TEXT("切割时限   /   废料清除   /   主体损伤"),12);StatLegend->SetColorAndOpacity(ColdSteelUI::TextTertiary);StateCard->AddChildToVerticalBox(StatLegend);
    RefundPreview=Text(TEXT(""),12);RefundPreview->SetAutoWrapText(true);RefundPreview->SetColorAndOpacity(ColdSteelUI::TextSecondary);Space(StateCard->AddChildToVerticalBox(RefundPreview),FMargin(0,8,0,0));
    Timer=WidgetTree->ConstructWidget<UProgressBar>();Timer->SetFillColorAndOpacity(ColdSteelUI::Accent);
    TimerSize=WidgetTree->ConstructWidget<USizeBox>();TimerSize->SetContent(Timer);Space(StateCard->AddChildToVerticalBox(TimerSize),FMargin(0,8,0,0));
    auto* PreviewCaption=Text(TEXT("成品预览 · 完整装备"),14,false,true);Space(Content->AddChildToVerticalBox(PreviewCaption),FMargin(0,4,0,8));
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
    PreviewStage=Text(TEXT("配方基础参数 · 装备原始属性"),12);PreviewStage->SetColorAndOpacity(ColdSteelUI::TextSecondary);
    Space(ParameterContent->AddChildToVerticalBox(PreviewStage),FMargin(0,0,0,12));
    PreviewParameterGrid=WidgetTree->ConstructWidget<UGridPanel>();PreviewParameterGrid->SetColumnFill(0,1.f);
    ParameterContent->AddChildToVerticalBox(PreviewParameterGrid);
    PreviewScope=Text(TEXT(""),12);PreviewScope->SetAutoWrapText(true);PreviewScope->SetColorAndOpacity(ColdSteelUI::TextTertiary);
    Space(ParameterContent->AddChildToVerticalBox(PreviewScope),FMargin(0,12,0,0));
    auto* Instructions=Card(Content);Space(Instructions->AddChildToVerticalBox(Text(TEXT("操作说明"),16,false,true)),FMargin(0,0,0,8));
    auto* Help=Text(TEXT("浅色轮廓是保留主体，轮廓外的木料是废料。按空格切换调整与切割，鼠标左键拖动木板进料。"),14);Help->SetAutoWrapText(true);Space(Instructions->AddChildToVerticalBox(Help),FMargin(0,0,0,8));
    RulesText=Text(TEXT(""),12);RulesText->SetAutoWrapText(true);RulesText->SetColorAndOpacity(ColdSteelUI::TextSecondary);Space(Instructions->AddChildToVerticalBox(RulesText),FMargin(0,0,0,8));
    auto* Exit=Text(TEXT("开始时扣除材料。中途返回按当前切割结果结算；达标后可领取成品，未达标工件可废弃。废弃返还一半材料至背包，每种材料的零头向下取整。"),12);Exit->SetAutoWrapText(true);Exit->SetColorAndOpacity(ColdSteelUI::TextTertiary);Instructions->AddChildToVerticalBox(Exit);
    Footer=WidgetTree->ConstructWidget<UBorder>();Footer->SetBrushColor(ColdSteelUI::HeaderTint);Stack->AddChildToVerticalBox(Footer);
    auto* Foot=WidgetTree->ConstructWidget<UVerticalBox>();Footer->SetContent(Foot);
    Status=Text(TEXT(""),14);Status->SetAutoWrapText(true);Status->SetColorAndOpacity(ColdSteelUI::TextSecondary);Space(Foot->AddChildToVerticalBox(Status),FMargin(0,0,0,8));
    auto* Actions=WidgetTree->ConstructWidget<UHorizontalBox>();Foot->AddChildToVerticalBox(Actions);
    UTextBlock* NewActionLabel=nullptr;ActionButton=Button(TEXT("开始加工"),NewActionLabel);ActionLabel=NewActionLabel;ActionButton->OnClicked.AddDynamic(this,&ThisClass::HandleAction);
    auto* ActionSize=WidgetTree->ConstructWidget<USizeBox>();ActionSize->SetContent(ActionButton);ButtonSizes.Add(ActionSize);Actions->AddChildToHorizontalBox(ActionSize)->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    UTextBlock* DiscardLabel=nullptr;DiscardButton=Button(TEXT("废弃 · 返还一半"),DiscardLabel);DiscardButton->OnClicked.AddDynamic(this,&ThisClass::HandleDiscard);
    DiscardButton->SetToolTipText(FText::FromString(TEXT("直接废弃未领取的成品，返还一半投入材料至背包（逐项向下取整）。背包空间不足时保留成品。")));
    auto* DiscardSize=WidgetTree->ConstructWidget<USizeBox>();DiscardSize->SetContent(DiscardButton);ButtonSizes.Add(DiscardSize);DiscardActionSlot=Actions->AddChildToHorizontalBox(DiscardSize);DiscardActionSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    UpdateScale();Refresh();
}
void UColdSteelWoodworkingManagementWidget::NativeConstruct()
{
    Super::NativeConstruct();bMaterialsDirty=true;if(Model&&!ChangedHandle.IsValid())ChangedHandle=Model->OnChanged.AddWeakLambda(this,[this]{bMaterialsDirty=true;});
}
void UColdSteelWoodworkingManagementWidget::NativeDestruct()
{
    if(Model&&ChangedHandle.IsValid()){Model->OnChanged.Remove(ChangedHandle);ChangedHandle.Reset();}
    Super::NativeDestruct();
}
void UColdSteelWoodworkingManagementWidget::RefreshProductPreview()
{
    using ColdSteelWoodManagementPresentation::SetText;
    const auto* Recipe=this->Recipe();
    const auto& Job=System->Job();
    const bool HasJob=!Job.Id.IsEmpty();
    FColdSteelItem Item=HasJob?Job.Item:Recipe?Model->CreateItem(Recipe->Output):FColdSteelItem{};
    // Older unclaimed jobs use the same saved score that Claim applies on authority.
    if(HasJob&&Job.bFinished&&Job.bPassed)ColdSteelWoodQuality::Apply(Item,Job.Quality);
    Board->Configure(nullptr,ProductImages.FindRef(ColdSteelInventory::Text(Item,TEXT("ue_icon"))));
    const auto Data=Item.Data.IsEmpty()?FColdSteelTooltipContent{}:
        BuildColdSteelItemTooltip(Item,Model,GetGameInstance()->GetSubsystem<UGunsmithSystem>());
    SetText(PreviewName,Data.Name.IsEmpty()?TEXT("暂无成品参数"):Data.Name);
    SetText(PreviewStage,HasJob&&Job.bFinished&&Job.bPassed?TEXT("成品实际参数 · 已计入木工品质修正"):TEXT("配方基础参数 · 尚未计入木工品质"));
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
void UColdSteelWoodworkingManagementWidget::UpdateScale()
{
    const float NewScale=ColdSteelUI::PixelScale(this);if(FMath::IsNearlyEqual(Scale,NewScale,.001f))return;Scale=FMath::Max(.1f,NewScale);
    for(const auto& L:Labels)if(auto* T=L.Widget.Get())T->SetFont(L.Numeric?GunsmithUI::NumberFont(L.Pixels/Scale,L.Medium):GunsmithUI::TextFont(L.Pixels/Scale,L.Medium));
    RecipeOptionWidgets.RemoveAll([](const auto& Entry){return !Entry.IsValid();});
    for(const auto& Option:RecipeOptionWidgets)if(auto* Widget=Option.Get())Widget->SetPixelScale(Scale);
    for(const auto& W:Buttons)if(auto* B=W.Get()){B->SetStyle(ColdSteelUI::ButtonStyle(Scale));if(auto* ButtonSlot=Cast<UButtonSlot>(B->GetContent()->Slot))ButtonSlot->SetPadding(FMargin(12/Scale,4/Scale));}
    for(const auto& W:ButtonSizes)if(auto* S=W.Get())S->SetHeightOverride(ColdSteelUI::ActionHeight/Scale);
    CloseSize->SetWidthOverride(ColdSteelUI::ActionHeight/Scale);
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
void UColdSteelWoodworkingManagementWidget::NativeTick(const FGeometry& Geometry,float DeltaTime)
{
    Super::NativeTick(Geometry,DeltaTime);UpdateScale();
    const float Height=FMath::Clamp(float(Geometry.GetLocalSize().Y)*Scale-520.f,200.f,420.f)/Scale;
    if(!FMath::IsNearlyEqual(Height,BoardHeight,.5f)){BoardHeight=Height;BoardSize->SetHeightOverride(Height);}
    RefreshClock+=DeltaTime;
    if(RefreshClock>=.05f){RefreshClock=0;Refresh();}
}
void UColdSteelWoodworkingManagementWidget::Refresh()
{
    using ColdSteelWoodManagementPresentation::SetText;
    auto* Owner=OwnerWidget.Get();if(!System||!Model||!ActionButton||!Owner)return;
    const auto& Job=System->Job();const bool Pending=System->HasPendingJob();
    const auto* Pattern=System->Pattern();const auto* Recipe=this->Recipe();
    const FName PatternId=Pattern?Pattern->Id:NAME_None;
    const bool Preparing=Owner->IsPreparingProject(),Busy=System->TransactionPending(),InputReady=Owner->ManagementInputReady();
    const bool NeedsSettlement=Pending&&!Job.bFinished&&(System->State()==EWoodworkingPhase::Complete||System->State()==EWoodworkingPhase::Failed);
    if(ObservedPattern!=PatternId||ObservedJobId!=Job.Id||bObservedFinished!=Job.bFinished||bObservedBusy!=Busy||ObservedPhase!=uint8(System->State()))
    {ObservedPattern=PatternId;ObservedJobId=Job.Id;bObservedFinished=Job.bFinished;bObservedBusy=Busy;ObservedPhase=uint8(System->State());bMaterialsDirty=true;}
    if(bMaterialsDirty)
    {
        RefreshProductPreview();
        const int32 Index=System->Patterns().IndexOfByPredicate([PatternId](const auto& P){return P.Id==PatternId;});
        if(RecipeChoice->GetSelectedIndex()!=Index)RecipeChoice->SetSelectedIndex(Index);
        const FString ProductName=ColdSteelInventory::Text(Pending?Job.Item:Recipe?Model->CreateItem(Recipe->Output):FColdSteelItem{},TEXT("name"));
        SetText(RecipeTitle,Pending?Job.Name:Recipe?FString::Printf(TEXT("%d / %d · %s"),Index+1,System->Patterns().Num(),*ProductName):TEXT("配方未就绪"));
        TArray<FColdSteelCraftingInput> DisplayInputs;
        if(Pending)
        {
            auto Paid=Job.PaidMaterials;
            if(Recipe)for(const auto& Input:Recipe->Inputs)if(const auto* Count=Paid.Find(Input.Item))
            {DisplayInputs.Add({Input.Item,*Count});Paid.Remove(Input.Item);}
            TArray<FString> Definitions;Paid.GetKeys(Definitions);Definitions.Sort();
            for(const auto& Definition:Definitions)DisplayInputs.Add({Definition,Paid.FindRef(Definition)});
        }
        else if(Recipe)DisplayInputs=Recipe->Inputs;
        SetText(Materials,Pending?TEXT("本轮已投入材料"):TEXT("所需材料"));
        SetText(MaterialSource.Get(),Pending?TEXT("本轮材料已扣除"):Recipe?TEXT("材料来源 · 背包 + 主仓库"):TEXT("暂无可用配方"));
        SetText(MaterialQuantityHeader.Get(),Pending?TEXT("已投入数量"):TEXT("持有 / 需要"));
        EnsureMaterialRows(DisplayInputs.Num());
        for(int32 MaterialIndex=0;MaterialIndex<MaterialRows.Num();++MaterialIndex)
        {
            const auto& Row=MaterialRows[MaterialIndex];const bool Visible=DisplayInputs.IsValidIndex(MaterialIndex);
            const auto RowVisibility=Visible?ESlateVisibility::HitTestInvisible:ESlateVisibility::Collapsed;
            Row.Name->SetVisibility(RowVisibility);Row.Amount->SetVisibility(RowVisibility);Row.State->SetVisibility(RowVisibility);
            if(!Visible)continue;
            const auto& Input=DisplayInputs[MaterialIndex];const int64 Owned=Pending?Input.Count:Model->CountMaterial(Input.Item);
            SetText(Row.Name.Get(),ColdSteelInventory::Text(Model->CreateItem(Input.Item),TEXT("name")));
            SetText(Row.Owned.Get(),FString::Printf(TEXT("%lld"),Owned));
            SetText(Row.Required.Get(),FString::Printf(TEXT("%lld"),Input.Count));
            Row.Separator->SetVisibility(Pending?ESlateVisibility::Collapsed:ESlateVisibility::HitTestInvisible);
            Row.Required->SetVisibility(Pending?ESlateVisibility::Collapsed:ESlateVisibility::HitTestInvisible);
            const bool Enough=Owned>=Input.Count;
            const FLinearColor Color=Pending?ColdSteelUI::TextPrimary:Enough?ColdSteelUI::Success:ColdSteelUI::Danger;
            Row.Owned->SetColorAndOpacity(Color);
            SetText(Row.State.Get(),Pending?TEXT("已投入"):Enough?TEXT("已满足"):FString::Printf(TEXT("缺 %lld"),Input.Count-Owned));
            Row.State->SetColorAndOpacity(Pending?ColdSteelUI::TextSecondary:Color);
        }
        bCanStart=System->CanStart(false,StartReason);
        TArray<FColdSteelCraftingInput> Refund;FString Reason;bCanDiscard=System->GetDiscardRefund(Refund,Reason);
        if(bCanDiscard)
        {
            TArray<FString> Returned;
            for(const auto& Input:Refund)Returned.Add(FString::Printf(TEXT("%s × %lld"),*ColdSteelInventory::Text(Model->CreateItem(Input.Item),TEXT("name")),Input.Count));
            Reason=Returned.IsEmpty()?TEXT("废弃返还：无（各项材料折半不足 1 个）"):TEXT("废弃返还至背包：")+FString::Join(Returned,TEXT("、"));
        }
        SetText(RefundPreview,Pending?Job.Result+TEXT("\n")+Reason:TEXT(""));
        SetText(RulesText,Pattern?Pattern->Instructions+FString::Printf(TEXT("\nQ / E 每次 1° · Shift + Q / E 每次 0.25° · Ctrl + Z 撤销，最多 %d 次\n调整时暂停计时，关键连接必须完整；达到清除目标且损伤不超限才能领取成品。\n评分决定成品修正：50 分不变，100 分 +25%%，最低 -25%%；弓修正物理伤害，法杖修正本件魔法攻击。\nEsc 或“暂停并返回”保留进度；“结束并返回”按当前进度结算。"),System->Settings().UndoLimit):TEXT("暂无加工说明"));
        bMaterialsDirty=false;
    }
    RefundPreview->SetVisibility(Pending?ESlateVisibility::HitTestInvisible:ESlateVisibility::Collapsed);
    SetText(Stage,Preparing?TEXT("准备台面与木板"):NeedsSettlement?TEXT("加工已结束 · 等待保存结果"):Pending?(Job.bFinished?(Job.bPassed?TEXT("加工完成 · 已达标"):TEXT("加工结束 · 未达标")):TEXT("加工已暂停 · 进度保留")):TEXT("选择工件 · 准备加工"));
    SetText(Stats,Pending?FString::Printf(TEXT("%.1f 分   |   %.1f%%   |   %.1f%%"),Job.Quality,Job.Clearance*100,(1-Job.Integrity)*100):
        Pattern?FString::Printf(TEXT("%.0f s   |   ≥%.1f%%   |   ≤%.1f%%"),Pattern->Seconds,Pattern->RequiredClearance*100,Pattern->MaximumDamage*100):TEXT("—"));
    SetText(StatLegend,Pending?TEXT("工艺评分   /   废料清除   /   主体损伤"):TEXT("切割时限   /   废料清除   /   主体损伤"));
    Stats->SetColorAndOpacity(!Pending||!Job.bFinished?ColdSteelUI::TextSecondary:Job.bPassed?ColdSteelUI::Success:ColdSteelUI::Danger);
    Timer->SetPercent(Pending?FMath::Clamp(float(Job.Clearance),0.f,1.f):0.f);
    SetText(ActionLabel,Preparing?TEXT("准备加工中"):NeedsSettlement?TEXT("重试结算"):Pending?(Job.bFinished?TEXT("领取成品"):TEXT("继续加工")):TEXT("开始加工"));
    ActionButton->SetIsEnabled(InputReady&&!Preparing&&!Busy&&(Pending?(Job.bFinished?Job.bPassed:(NeedsSettlement||System->CanResume())):(bCanStart&&Owner->CanConfirmProject())));
    RecipeChoice->SetIsEnabled(InputReady&&!Preparing&&!Busy&&System->CanSelect()&&System->Patterns().Num()>1);
    DiscardButton->SetIsEnabled(InputReady&&!Preparing&&!Busy&&Pending&&bCanDiscard);
    FString Reason;
    if(Preparing)Reason=Owner->PresentationStatus().IsEmpty()?TEXT("正在准备台面与木板，准备完成后投入材料。"):Owner->PresentationStatus();
    else if(Busy)Reason=TEXT("正在等待服务器结算…");
    else if(Pending)Reason=System->Message();
    else Reason=!Owner->PresentationStatus().IsEmpty()?Owner->PresentationStatus():StartReason;
    SetText(Status,Reason);
}
void UColdSteelWoodworkingManagementWidget::HandleAction()
{
    auto* Owner=OwnerWidget.Get();if(!Owner||!System||!Owner->ManagementInputReady()||Owner->IsPreparingProject()||System->TransactionPending()||!Owner->EnsureStation())return;
    if(System->HasPendingJob())
    {
        if(System->Job().bFinished)System->Claim();
        else if(System->State()==EWoodworkingPhase::Complete||System->State()==EWoodworkingPhase::Failed)System->Settle();
        else Owner->ConfirmProject();
    }
    else Owner->ConfirmProject();
    bMaterialsDirty=true;Refresh();
}
void UColdSteelWoodworkingManagementWidget::HandleClose(){if(auto* Owner=OwnerWidget.Get())if(Owner->ManagementInputReady())Owner->CloseConfirmed();}
void UColdSteelWoodworkingManagementWidget::HandleDiscard()
{
    auto* Owner=OwnerWidget.Get();if(!Owner||!System||!Owner->ManagementInputReady()||Owner->IsPreparingProject()||System->TransactionPending()||!Owner->EnsureStation())return;
    System->Discard();bMaterialsDirty=true;Refresh();SetKeyboardFocus();
}
UWidget* UColdSteelWoodworkingManagementWidget::GenerateRecipeOption(FString Option)
{
    // ComboBoxString retains TakeWidget(), not a detached UMG subtree.
    // SObjectWidget keeps the text and its StrikeBrush alive for selected content and menu rows.
    auto* Widget=CreateWidget<UColdSteelGunRecipeOptionWidget>(this);
    if(!Widget)return nullptr;
    Widget->Configure(Option,ColdSteelUI::PixelScale(this));
    RecipeOptionWidgets.RemoveAll([](const auto& Entry){return !Entry.IsValid();});
    RecipeOptionWidgets.Add(Widget);
    return Widget;
}
void UColdSteelWoodworkingManagementWidget::HandleRecipeSelected(FString Option,ESelectInfo::Type SelectionType)
{
    if(SelectionType==ESelectInfo::Direct||!System)return;
    auto* Owner=OwnerWidget.Get();if(!Owner)return;
    const auto& Catalog=System->Patterns();const int32 Index=RecipeChoice->GetSelectedIndex();
    if(!Owner->ManagementInputReady()||Owner->IsPreparingProject()||!System->CanSelect()||!Catalog.IsValidIndex(Index))
    {bMaterialsDirty=true;Refresh();return;}
    Owner->SelectProject(Catalog[Index].Id);bMaterialsDirty=true;Refresh();SetKeyboardFocus();
}
FReply UColdSteelWoodworkingManagementWidget::NativeOnMouseButtonDown(const FGeometry&,const FPointerEvent&){return FReply::Handled();}
