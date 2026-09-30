#include "ColdSteelGunAssemblyWidget.h"
#include "ColdSteelGunRecipeOptionWidget.h"
#include "ColdSteelForgeBoard.h"
#include "ColdSteelHUDWidget.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelUIStyle.h"
#include "ColdSteelItemTooltipData.h"
#include "../Weapons/GunsmithSystem.h"
#include "GunsmithUIStyle.h"
#include "../Building/GunAssemblySystem.h"
#include "../Building/CraftingSystem.h"
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
#include "Components/WidgetSwitcher.h"
#include "ImageUtils.h"
#include "Misc/Paths.h"
#include "Styling/SlateTypes.h"


namespace ColdSteelAssemblyPresentation
{
void SetText(UTextBlock* Widget,const FString& Value)
{if(Widget&&Widget->GetText().ToString()!=Value)Widget->SetText(FText::FromString(Value));}
}
void UColdSteelGunAssemblyWidget::OpenStation()
{Notice.Reset();AmmoNotice.Reset();bMaterialsDirty=true;bAmmoDirty=true;SelectedRecipe=System->Recipe().Id;if(!bAmmoPage)LoadMold();Refresh();}
void UColdSteelGunAssemblyWidget::SetInputReady(bool bReady)
{
    if(bInputReady==bReady)return;
    bInputReady=bReady;bAmmoDirty=true;
    AmmoPageButton->SetIsEnabled(bReady);GunPageButton->SetIsEnabled(bReady);Refresh();
}
void UColdSteelGunAssemblyWidget::LoadMold()
{
    if(!System||!Model)return;
    const FString Icon=ColdSteelInventory::Text(Model->CreateItem(System->Recipe().Output),TEXT("ue_icon"));
    if(Icon==LoadedMold)return;LoadedMold=Icon;
    MoldTexture=Icon.IsEmpty()?nullptr:FImageUtils::ImportFileAsTexture2D(FPaths::ProjectContentDir()/TEXT("ColdSteelData")/Icon);
    if(Board)Board->Configure(nullptr,MoldTexture);
}
void UColdSteelGunAssemblyWidget::Refresh()
{
    using ColdSteelAssemblyPresentation::SetText;
    if(bAmmoPage){RefreshAmmoCard();return;}
    if(!System||!Model||!ActionButton)return;
    const auto& R=System->Recipe();const auto& J=System->Job();const bool Paid=!J.Id.IsEmpty();
    if(SelectedRecipe!=R.Id){SelectedRecipe=R.Id;bMaterialsDirty=true;LoadMold();}
    if(bMaterialsDirty)
    {
        bMaterialsDirty=false;RefreshProductPreview();
        const int32 Index=System->Catalog().IndexOfByPredicate([&R](const auto& Row){return Row.Id==R.Id;});
        if(RecipeChoice->GetSelectedIndex()!=Index)RecipeChoice->SetSelectedIndex(Index);
        SetText(RecipeTitle,R.Id.IsNone()?TEXT("配方未就绪"):FString::Printf(TEXT("%d / %d · %s"),Index+1,System->Catalog().Num(),*System->ProductName()));
        TArray<FColdSteelCraftingInput> Inputs=R.Inputs;
        if(Paid){Inputs.Reset();TMap<FString,int64> PaidMaterials;System->GetPaidMaterials(PaidMaterials);for(const auto& Pair:PaidMaterials)Inputs.Add({Pair.Key,Pair.Value});Inputs.Sort([](const auto& A,const auto& B){return A.Item<B.Item;});}
        EnsureMaterialRows(Inputs.Num());
        SetText(MaterialQuantityHeader.Get(),Paid?TEXT("已投入"):TEXT("持有 / 需要"));
        SetText(MaterialSource.Get(),Paid?TEXT("本工件材料已支付 · 继续操作不重复扣除"):TEXT("材料来源 · 背包 + 主仓库"));
        for(int32 I=0;I<MaterialRows.Num();++I)
        {
            auto& Row=MaterialRows[I];const bool Visible=Inputs.IsValidIndex(I);
            for(UWidget* W:{static_cast<UWidget*>(Row.Name.Get()),static_cast<UWidget*>(Row.Amount.Get()),static_cast<UWidget*>(Row.State.Get())})W->SetVisibility(Visible?ESlateVisibility::HitTestInvisible:ESlateVisibility::Collapsed);
            if(!Visible)continue;
            const auto& Cost=Inputs[I];const int64 Owned=Paid?Cost.Count:Model->CountMaterial(Cost.Item);
            SetText(Row.Name.Get(),ColdSteelInventory::Text(Model->CreateItem(Cost.Item),TEXT("name")));
            SetText(Row.Owned.Get(),FString::Printf(TEXT("%lld"),Owned));SetText(Row.Required.Get(),FString::Printf(TEXT("%lld"),Cost.Count));
            Row.Owned->SetColorAndOpacity(Owned>=Cost.Count?ColdSteelUI::Success:ColdSteelUI::Danger);
            Row.Separator->SetVisibility(Paid?ESlateVisibility::Collapsed:ESlateVisibility::HitTestInvisible);
            Row.Required->SetVisibility(Paid?ESlateVisibility::Collapsed:ESlateVisibility::HitTestInvisible);
            SetText(Row.State.Get(),Paid?TEXT("已投入"):Owned>=Cost.Count?TEXT("充足"):TEXT("不足"));
        }
        TArray<FColdSteelCraftingInput> Refund;FString RefundReason;
        bCanDiscard=System->GetDiscardRefund(Refund,RefundReason);
        if(bCanDiscard)
        {
            TArray<FString> Returned;
            for(const auto& In:Refund)Returned.Add(FString::Printf(TEXT("%s × %lld"),*ColdSteelInventory::Text(Model->CreateItem(In.Item),TEXT("name")),In.Count));
            RefundReason=Returned.IsEmpty()?TEXT("废弃返还：无（各项材料折半不足 1 个）")
                :TEXT("废弃返还至背包：")+FString::Join(Returned,TEXT("、"));
        }
        SetText(RefundPreview,RefundReason);
    }
    const bool Active=HUD&&HUD->IsGunAssembly();
    RefundPreview->SetVisibility(Paid&&J.bFinished&&!Active?ESlateVisibility::HitTestInvisible:ESlateVisibility::Collapsed);
    const float Duration=Paid?J.CalibrationDuration:R.CalibrationDuration;
    SetText(Stage,J.bFinished?TEXT("组装完成 · ")+System->QualityName(J.Quality):!Paid?TEXT("准备组装"):System->Assembled()?TEXT("持稳校准"):TEXT("组件装配"));
    SetText(Stats,FString::Printf(TEXT("%d / %d    ·    %.1f / %.1f 秒    ·    %s"),System->InstalledCount(),R.Parts.Num(),J.CalibrationSeconds,Duration,
        J.bFinished?*FString::Printf(TEXT("%.0f 分"),J.Quality):TEXT("待完成")));
    FString Parts;
    for(int32 I=0;I<R.Parts.Num();++I){if(!Parts.IsEmpty())Parts+=TEXT("   ·   ");Parts+=(System->Installed(I)?TEXT("✓ "):TEXT("○ "))+R.Parts[I].Name;}
    SetText(PartsLabel,Parts);
    SetText(StatLegend,J.bFinished?System->BenefitText(J.Quality):TEXT("拖动对位 → 全部安装 → 持稳校准 → 领取成品"));
    Timer->SetPercent(J.bFinished?1.f:Paid?(System->InstalledCount()+J.CalibrationSeconds/FMath::Max(.01f,Duration))/FMath::Max(1,R.Parts.Num()+1):0.f);
    FString Why;const bool Can=J.bFinished||(HUD&&HUD->CanStartGunAssembly(Why)&&(Paid||System->CanStart(Why)));
    ActionButton->SetIsEnabled(bInputReady&&Can);
    DiscardButton->SetIsEnabled(bInputReady&&Paid&&J.bFinished&&!Active&&bCanDiscard);
    RecipeChoice->SetIsEnabled(bInputReady&&!Paid&&System->Catalog().Num()>1);
    SetText(ActionLabel,J.bFinished?TEXT("领取成品"):Paid?TEXT("继续组装"):TEXT("投入材料并开始"));
    SetText(Status,!Notice.IsEmpty()?Notice:!Can?Why:J.bFinished?TEXT("领取成品，或废弃返还一半材料；背包需有足够空间。"):Paid?TEXT("离开保留工件与进度 · 可随时继续"):TEXT("每轮制作一把 · 成品不附带弹药"));
}
void UColdSteelGunAssemblyWidget::HandleAction()
{
    if(!bInputReady||bAmmoPage||!System||!HUD)return;
    Notice.Reset();
    if(System->Job().bFinished)
    {if(System->Claim(Notice))HUD->SelectGunAssemblyRecipe(System->Recipe().Id);}
    else HUD->StartGunAssembly(Notice);
    bMaterialsDirty=true;Refresh();
}
void UColdSteelGunAssemblyWidget::HandleDiscard()
{
    if(!bInputReady||bAmmoPage||!System||!HUD||HUD->IsGunAssembly())return;
    const FName RecipeId=System->Recipe().Id;
    Notice.Reset();
    if(System->Discard(Notice))HUD->SelectGunAssemblyRecipe(RecipeId);
    bMaterialsDirty=true;SetKeyboardFocus();Refresh();
}
void UColdSteelGunAssemblyWidget::HandleClose(){if(HUD)HUD->CloseWorkbench();}
void UColdSteelGunAssemblyWidget::HandleRecipeSelected(FString Option,ESelectInfo::Type SelectionType)
{
    if(SelectionType==ESelectInfo::Direct||bAmmoPage||!System)return;
    const int32 Index=RecipeChoice->GetSelectedIndex();const auto& Recipes=System->Catalog();
    if(bInputReady&&Recipes.IsValidIndex(Index)&&HUD&&HUD->SelectGunAssemblyRecipe(Recipes[Index].Id))Notice.Reset();
    bMaterialsDirty=true;LoadMold();Refresh();
}
FReply UColdSteelGunAssemblyWidget::NativeOnMouseButtonDown(const FGeometry& Geometry,const FPointerEvent& Event)
{return FReply::Handled();}

UTextBlock* UColdSteelGunAssemblyWidget::Text(const FString& Caption,float Pixels,bool bNumeric,bool bMedium)
{
    auto* T=WidgetTree->ConstructWidget<UTextBlock>();T->SetText(FText::FromString(Caption));T->SetAutoWrapText(true);
    const float FontScale=Scale>0?Scale:1.f;
    T->SetFont(bNumeric?GunsmithUI::NumberFont(Pixels/FontScale,bMedium):GunsmithUI::TextFont(Pixels/FontScale,bMedium));
    T->SetColorAndOpacity(ColdSteelUI::TextPrimary);Labels.Add({T,Pixels,bNumeric,bMedium});return T;
}

UButton* UColdSteelGunAssemblyWidget::Button(const FString& Caption,UTextBlock*& Label)
{
    auto* B=WidgetTree->ConstructWidget<UButton>();Label=Text(Caption,14,false,true);Label->SetJustification(ETextJustify::Center);
    Label->SetAutoWrapText(false);Label->SetWrapTextAt(0);
    B->SetContent(Label);
    auto* LabelSlot=Cast<UButtonSlot>(Label->Slot);LabelSlot->SetHorizontalAlignment(HAlign_Fill);LabelSlot->SetVerticalAlignment(VAlign_Center);
    Buttons.Add(B);return B;
}

void UColdSteelGunAssemblyWidget::Space(UVerticalBoxSlot* RowSlot,FMargin RowPadding)
{RowSpacings.Add({RowSlot,RowPadding});}

UVerticalBox* UColdSteelGunAssemblyWidget::Card(UVerticalBox* Parent)
{
    auto* Border=WidgetTree->ConstructWidget<UBorder>();Cards.Add(Border);
    Space(Parent->AddChildToVerticalBox(Border),FMargin(0,0,0,8));
    auto* Column=WidgetTree->ConstructWidget<UVerticalBox>();Border->SetContent(Column);return Column;
}

void UColdSteelGunAssemblyWidget::AddMaterialCell(UWidget* Widget,int32 Row,int32 Column)
{
    auto* CellSlot=MaterialGrid->AddChildToGrid(Widget,Row,Column);
    CellSlot->SetHorizontalAlignment(Column==0?HAlign_Fill:HAlign_Right);
    CellSlot->SetVerticalAlignment(VAlign_Center);
    const float CellScale=Scale>0?Scale:1.f;
    CellSlot->SetPadding(FMargin(Column==0?0.f:12.f/CellScale,4.f/CellScale,0,4.f/CellScale));
    MaterialCellSlots.Add(CellSlot);
}

void UColdSteelGunAssemblyWidget::EnsureMaterialRows(int32 Count)
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

void UColdSteelGunAssemblyWidget::NativeOnInitialized()
{
    Super::NativeOnInitialized();SetIsFocusable(true);
    Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();System=GetGameInstance()->GetSubsystem<UGunAssemblySystem>();
    Crafting=GetGameInstance()->GetSubsystem<UColdSteelCraftingSystem>();
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
    auto* Title=Text(TEXT("制作 · 枪械工作台"),20,false,true);auto* TitleSlot=Head->AddChildToHorizontalBox(Title);TitleSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));TitleSlot->SetVerticalAlignment(VAlign_Center);
    UTextBlock* CloseLabel=nullptr;auto* Close=Button(TEXT("×"),CloseLabel);Close->OnClicked.AddDynamic(this,&ThisClass::HandleClose);
    CloseSize=WidgetTree->ConstructWidget<USizeBox>();CloseSize->SetContent(Close);ButtonSizes.Add(CloseSize);Head->AddChildToHorizontalBox(CloseSize)->SetVerticalAlignment(VAlign_Center);
    BuildManufacturingNavigation(Stack);
    Scroll=WidgetTree->ConstructWidget<UScrollBox>();Scroll->SetConsumeMouseWheel(EConsumeMouseWheel::Always);Stack->AddChildToVerticalBox(Scroll)->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    Body=WidgetTree->ConstructWidget<UBorder>();Body->SetBrushColor(FLinearColor::Transparent);Scroll->AddChild(Body);
    ManufacturingPages=WidgetTree->ConstructWidget<UWidgetSwitcher>();Body->SetContent(ManufacturingPages);
    auto* AmmoContent=WidgetTree->ConstructWidget<UVerticalBox>();ManufacturingPages->AddChild(AmmoContent);
    auto* Content=WidgetTree->ConstructWidget<UVerticalBox>();ManufacturingPages->AddChild(Content);
    ManufacturingPages->SetActiveWidgetIndex(bAmmoPage?0:1);
    auto* RecipeCard=Card(Content);
    auto* RecipeCaption=Text(TEXT("配方 · 工件"),12);RecipeCaption->SetColorAndOpacity(ColdSteelUI::TextTertiary);Space(RecipeCard->AddChildToVerticalBox(RecipeCaption),FMargin(0,0,0,4));
    RecipeTitle=Text(TEXT("—"),16,false,true);Space(RecipeCard->AddChildToVerticalBox(RecipeTitle),FMargin(0,0,0,8));
    RecipeChoice=WidgetTree->ConstructWidget<UComboBoxString>();
    RecipeChoice->OnGenerateWidgetEvent.BindDynamic(this,&ThisClass::GenerateRecipeOption);
    for(const auto& Recipe:System->Catalog())
        RecipeChoice->AddOption(ColdSteelInventory::Text(Model->CreateItem(Recipe.Output),TEXT("name")));
    RecipeChoice->OnSelectionChanged.AddDynamic(this,&ThisClass::HandleRecipeSelected);
    RecipeChoice->SetToolTipText(FText::FromString(TEXT("选择枪械配方；当前工件领取后可以更换。")));
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
    Stage=Text(TEXT("准备组装"),16,false,true);Space(StateCard->AddChildToVerticalBox(Stage),FMargin(0,0,0,8));
    Stats=Text(TEXT(""),16,true);Space(StateCard->AddChildToVerticalBox(Stats),FMargin(0,0,0,4));
    StatLegend=Text(TEXT("已装组件   /   持稳校准   /   工艺评分"),12);StatLegend->SetColorAndOpacity(ColdSteelUI::TextTertiary);StateCard->AddChildToVerticalBox(StatLegend);
    PartsLabel=Text(TEXT(""),12);PartsLabel->SetColorAndOpacity(ColdSteelUI::TextSecondary);Space(StateCard->AddChildToVerticalBox(PartsLabel),FMargin(0,8,0,0));
    RefundPreview=Text(TEXT(""),12);RefundPreview->SetColorAndOpacity(ColdSteelUI::TextSecondary);Space(StateCard->AddChildToVerticalBox(RefundPreview),FMargin(0,8,0,0));
    Timer=WidgetTree->ConstructWidget<UProgressBar>();Timer->SetFillColorAndOpacity(ColdSteelUI::Accent);
    TimerSize=WidgetTree->ConstructWidget<USizeBox>();TimerSize->SetContent(Timer);Space(StateCard->AddChildToVerticalBox(TimerSize),FMargin(0,8,0,0));
    auto* PreviewCaption=Text(TEXT("成品预览 · 枪械参数"),14,false,true);Space(Content->AddChildToVerticalBox(PreviewCaption),FMargin(0,4,0,8));
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
    PreviewStage=Text(TEXT("配方基础参数 · 未计装配品质"),12);PreviewStage->SetColorAndOpacity(ColdSteelUI::TextSecondary);
    Space(ParameterContent->AddChildToVerticalBox(PreviewStage),FMargin(0,0,0,12));
    PreviewParameterGrid=WidgetTree->ConstructWidget<UGridPanel>();PreviewParameterGrid->SetColumnFill(0,1.f);
    ParameterContent->AddChildToVerticalBox(PreviewParameterGrid);
    PreviewScope=Text(TEXT(""),12);PreviewScope->SetColorAndOpacity(ColdSteelUI::TextTertiary);
    Space(ParameterContent->AddChildToVerticalBox(PreviewScope),FMargin(0,12,0,0));
    auto* Instructions=Card(Content);Space(Instructions->AddChildToVerticalBox(Text(TEXT("操作说明"),16,false,true)),FMargin(0,0,0,8));
    Space(Instructions->AddChildToVerticalBox(Text(TEXT("按住左键拿取组件，拖到枪身轮廓；滚轮或 Q / R 调整朝向，松开左键安装。"),14)),FMargin(0,0,0,8));
    auto* Help=Text(TEXT("Tab 选择下一件 · 右键放回 · 全部装好后按住左键持稳校准 · Esc 保存并返回\n成品可领取或直接废弃。废弃返还一半投入材料至背包，每种材料的零头向下取整。"),12);
    Help->SetColorAndOpacity(ColdSteelUI::TextSecondary);Instructions->AddChildToVerticalBox(Help);
    Footer=WidgetTree->ConstructWidget<UBorder>();Footer->SetBrushColor(ColdSteelUI::HeaderTint);Stack->AddChildToVerticalBox(Footer);
    ManufacturingActions=WidgetTree->ConstructWidget<UWidgetSwitcher>();Footer->SetContent(ManufacturingActions);
    auto* AmmoFoot=WidgetTree->ConstructWidget<UVerticalBox>();ManufacturingActions->AddChild(AmmoFoot);
    BuildAmmoCard(AmmoContent,AmmoFoot);
    auto* Foot=WidgetTree->ConstructWidget<UVerticalBox>();ManufacturingActions->AddChild(Foot);
    ManufacturingActions->SetActiveWidgetIndex(bAmmoPage?0:1);
    Status=Text(TEXT(""),14);Status->SetColorAndOpacity(ColdSteelUI::TextSecondary);Space(Foot->AddChildToVerticalBox(Status),FMargin(0,0,0,8));
    auto* Actions=WidgetTree->ConstructWidget<UHorizontalBox>();Foot->AddChildToVerticalBox(Actions);
    UTextBlock* NewActionLabel=nullptr;ActionButton=Button(TEXT("开始组装"),NewActionLabel);ActionLabel=NewActionLabel;ActionButton->OnClicked.AddDynamic(this,&ThisClass::HandleAction);
    auto* ActionSize=WidgetTree->ConstructWidget<USizeBox>();ActionSize->SetContent(ActionButton);ButtonSizes.Add(ActionSize);Actions->AddChildToHorizontalBox(ActionSize)->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    UTextBlock* DiscardLabel=nullptr;DiscardButton=Button(TEXT("废弃 · 返还一半"),DiscardLabel);DiscardButton->OnClicked.AddDynamic(this,&ThisClass::HandleDiscard);
    DiscardButton->SetToolTipText(FText::FromString(TEXT("直接废弃未领取的成品，返还一半投入材料至背包（逐项向下取整）。背包空间不足时保留成品。")));
    auto* DiscardSize=WidgetTree->ConstructWidget<USizeBox>();DiscardSize->SetContent(DiscardButton);ButtonSizes.Add(DiscardSize);DiscardActionSlot=Actions->AddChildToHorizontalBox(DiscardSize);DiscardActionSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    UpdateScale();LoadMold();Refresh();
}

void UColdSteelGunAssemblyWidget::NativeConstruct()
{
    Super::NativeConstruct();if(Model&&!ChangedHandle.IsValid())ChangedHandle=Model->OnChanged.AddWeakLambda(this,[this]{bMaterialsDirty=true;bAmmoDirty=true;});
}

void UColdSteelGunAssemblyWidget::NativeDestruct()
{
    if(Model&&ChangedHandle.IsValid()){Model->OnChanged.Remove(ChangedHandle);ChangedHandle.Reset();}
    Super::NativeDestruct();
}

void UColdSteelGunAssemblyWidget::RefreshProductPreview()
{
    using ColdSteelAssemblyPresentation::SetText;
    const auto* Recipe=&System->Recipe();
    const auto& Job=System->Job();
    const bool HasJob=!Job.Id.IsEmpty();
    const FColdSteelItem Item=HasJob?Job.Item:Recipe?Model->CreateItem(Recipe->Output):FColdSteelItem{};
    const auto Data=Item.Data.IsEmpty()?FColdSteelTooltipContent{}:
        BuildColdSteelItemTooltip(Item,Model,GetGameInstance()->GetSubsystem<UGunsmithSystem>());
    SetText(PreviewName,Data.Name.IsEmpty()?TEXT("暂无成品参数"):Data.Name);
    SetText(PreviewStage,HasJob&&Job.bFinished?TEXT("成品实际参数 · 已计装配品质"):TEXT("配方基础参数 · 未计装配品质"));
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

void UColdSteelGunAssemblyWidget::UpdateScale()
{
    const float NewScale=ColdSteelUI::PixelScale(this);if(FMath::IsNearlyEqual(Scale,NewScale,.001f))return;Scale=FMath::Max(.1f,NewScale);
    for(const auto& L:Labels)if(auto* T=L.Widget.Get())T->SetFont(L.Numeric?GunsmithUI::NumberFont(L.Pixels/Scale,L.Medium):GunsmithUI::TextFont(L.Pixels/Scale,L.Medium));
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
    if(AmmoChoice)
    {
        AmmoChoice->SetWidgetStyle(ComboStyle);AmmoChoice->SetItemStyle(ItemStyle);
        AmmoChoice->SetContentPadding(FMargin(22/Scale,4/Scale,10/Scale,4/Scale));AmmoChoice->SetMaxListHeight(240/Scale);
    }
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
    UpdateManufacturingNavigation();
}

void UColdSteelGunAssemblyWidget::NativeTick(const FGeometry& Geometry,float DeltaTime)
{
    Super::NativeTick(Geometry,DeltaTime);UpdateScale();
    if(!bAmmoPage)
    {
        const float Height=FMath::Clamp(float(Geometry.GetLocalSize().Y)*Scale-600.f,200.f,420.f)/Scale;
        if(!FMath::IsNearlyEqual(Height,BoardHeight,.5f)){BoardHeight=Height;BoardSize->SetHeightOverride(Height);}
    }
    RefreshClock+=DeltaTime;
    if(RefreshClock>=.05f){RefreshClock=0;Refresh();}
}

UWidget* UColdSteelGunAssemblyWidget::GenerateRecipeOption(FString Option)
{
    // UComboBoxString retains only TakeWidget(), not the generated UObject.
    // A UUserWidget supplies SObjectWidget's GC reference for both selected content and menu rows.
    auto* Widget=CreateWidget<UColdSteelGunRecipeOptionWidget>(this);
    if(!Widget)return nullptr;
    Widget->Configure(Option,ColdSteelUI::PixelScale(this));
    RecipeOptionWidgets.RemoveAll([](const auto& Entry){return !Entry.IsValid();});
    RecipeOptionWidgets.Add(Widget);
    return Widget;
}
