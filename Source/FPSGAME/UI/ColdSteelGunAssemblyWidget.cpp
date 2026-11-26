#include "ColdSteelGunAssemblyWidget.h"
#include "ColdSteelTextToolTip.h"
#include "../Development/DevelopmentTuningSubsystem.h"
#include "ColdSteelGunRecipeOptionWidget.h"
#include "DevelopmentItemPicker.h"
#include "ColdSteelForgeBoard.h"
#include "ColdSteelHUDWidget.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelUIStyle.h"
#include "ColdSteelCraftingResultStyle.h"
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
#include "Components/WrapBox.h"
#include "ImageUtils.h"
#include "Misc/Paths.h"
#include "Styling/SlateTypes.h"


namespace ColdSteelAssemblyPresentation
{
void SetText(UTextBlock* Widget,const FString& Value)
{if(Widget&&Widget->GetText().ToString()!=Value)Widget->SetText(FText::FromString(Value));}
using ColdSteelCraftingResultStyle::SetBonus;
using ColdSteelCraftingResultStyle::ScoreColor;
}
void UColdSteelGunAssemblyWidget::OpenStation()
{
    Notice.Reset();AmmoNotice.Reset();bMaterialsDirty=true;bAmmoDirty=true;SelectedRecipe=System->Recipe().Id;
    if(System->Job().bFinished)
    {
        bAmmoPage=false;ManufacturingPages->SetActiveWidgetIndex(1);ManufacturingActions->SetActiveWidgetIndex(1);
        Scroll->ScrollToStart();UpdateManufacturingNavigation();
    }
    if(!bAmmoPage)LoadMold();Refresh();
}
bool UColdSteelGunAssemblyWidget::CanInteract() const
{return bInputReady&&Model&&!Model->IsCampfireInventoryPending();}
void UColdSteelGunAssemblyWidget::SetInputReady(bool bReady)
{
    if(bInputReady==bReady)return;
    bInputReady=bReady;bAmmoDirty=true;
    if(!bReady){RecipeChoice->CloseMenu();AmmoChoice->CloseMenu();}
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
    const bool Pending=Model&&Model->IsCampfireInventoryPending();
    if(Pending!=bTransactionPending)
    {
        bTransactionPending=Pending;bMaterialsDirty=bAmmoDirty=true;
        if(Pending){RecipeChoice->CloseMenu();AmmoChoice->CloseMenu();}
    }
    AmmoPageButton->SetIsEnabled(CanInteract());GunPageButton->SetIsEnabled(CanInteract());
    if(bAmmoPage){RefreshAmmoCard();return;}
    if(!System||!Model||!ActionButton)return;
    const auto& R=System->Recipe();const auto& J=System->Job();const bool Paid=!J.Id.IsEmpty();
    const bool Free=Paid?J.bMaterialsWaived:UDevelopmentTuningSubsystem::IsFreeCrafting(Model);
    if(SelectedRecipe!=R.Id){SelectedRecipe=R.Id;bMaterialsDirty=true;LoadMold();}
    if(bMaterialsDirty)
    {
        bMaterialsDirty=false;RefreshProductPreview();
        const int32 Index=System->Catalog().IndexOfByPredicate([&R](const auto& Row){return Row.Id==R.Id;});
        RecipeChoice->SetSelectedOption(R.Id.ToString());
        const int32 MetalIndex=System->Metals().IndexOfByPredicate([this](const auto& M){return M.Item==System->Metal();});
        if(MetalChoice->GetSelectedIndex()!=MetalIndex)MetalChoice->SetSelectedIndex(MetalIndex);
        SetText(RecipeTitle,R.Id.IsNone()?TEXT("旧工件 · ")+System->ProductName():FString::Printf(TEXT("%d / %d · %s"),Index+1,System->Catalog().Num(),*System->ProductName()));
        TArray<FColdSteelCraftingInput> Inputs;if(!Paid)System->InputsFor(Inputs);
        if(Paid){Inputs.Reset();TMap<FString,int64> PaidMaterials;System->GetPaidMaterials(PaidMaterials);for(const auto& Pair:PaidMaterials)Inputs.Add({Pair.Key,Pair.Value});Inputs.Sort([](const auto& A,const auto& B){return A.Item<B.Item;});}
        EnsureMaterialRows(Inputs.Num());
        SetText(Materials,Free?TEXT("免材料制作"):Paid?TEXT("本轮已投入材料"):TEXT("所需材料"));
        SetText(MaterialQuantityHeader.Get(),Paid?TEXT("已投入"):Free?TEXT("持有 / 本次消耗"):TEXT("持有 / 需要"));
        SetText(MaterialSource.Get(),Free?TEXT("本轮不扣材料 · 免费工件废弃不返料"):Paid?TEXT("本工件材料已支付 · 继续操作不重复扣除"):TEXT("材料来源 · 背包 + 主仓库"));
        for(int32 I=0;I<MaterialRows.Num();++I)
        {
            auto& Row=MaterialRows[I];const bool Visible=Inputs.IsValidIndex(I);
            for(UWidget* W:{static_cast<UWidget*>(Row.Name.Get()),static_cast<UWidget*>(Row.Amount.Get()),static_cast<UWidget*>(Row.State.Get())})W->SetVisibility(Visible?ESlateVisibility::HitTestInvisible:ESlateVisibility::Collapsed);
            if(!Visible)continue;
            const auto& Cost=Inputs[I];const int64 Owned=Paid?Cost.Count:Model->CountMaterial(Cost.Item);
            SetText(Row.Name.Get(),ColdSteelInventory::Text(Model->CreateItem(Cost.Item),TEXT("name")));
            SetText(Row.Owned.Get(),FString::Printf(TEXT("%lld"),Owned));SetText(Row.Required.Get(),FString::Printf(TEXT("%lld"),Free?int64(0):Cost.Count));
            Row.Owned->SetColorAndOpacity(Free||Owned>=Cost.Count?ColdSteelUI::Success:ColdSteelUI::Danger);
            Row.Separator->SetVisibility(Paid?ESlateVisibility::Collapsed:ESlateVisibility::HitTestInvisible);
            Row.Required->SetVisibility(Paid?ESlateVisibility::Collapsed:ESlateVisibility::HitTestInvisible);
            SetText(Row.State.Get(),Free?TEXT("免消耗"):Paid?TEXT("已投入"):Owned>=Cost.Count?TEXT("充足"):TEXT("不足"));
        }
        TArray<FColdSteelCraftingInput> Refund;FString RefundReason;
        bCanDiscard=System->GetDiscardRefund(Refund,RefundReason);
        if(bCanDiscard&&RefundReason.IsEmpty())
        {
            TArray<FString> Returned;
            for(const auto& In:Refund)Returned.Add(FString::Printf(TEXT("%s × %lld"),*ColdSteelInventory::Text(Model->CreateItem(In.Item),TEXT("name")),In.Count));
            RefundReason=J.bMaterialsWaived?TEXT("本轮免材料制作 · 废弃不返料"):Returned.IsEmpty()?TEXT("废弃返还：无（各项材料折半不足 1 个）")
                :TEXT("废弃返还至背包：")+FString::Join(Returned,TEXT("、"));
        }
        SetText(RefundPreview,RefundReason);
    }
    const bool Active=HUD&&HUD->IsGunAssembly();
    RefundPreview->SetVisibility(Paid&&!Active?ESlateVisibility::HitTestInvisible:ESlateVisibility::Collapsed);
    const float Duration=Paid?J.CalibrationDuration:R.CalibrationDuration;
    const float CalibrationProgress=J.CalibrationVersion>=GunAssemblyCalibration::FirstRoundsVersion?J.CalibrationTime:J.CalibrationSeconds;
    SetText(Stage,J.bFinished?TEXT("交付成品 · ")+System->QualityName(J.Quality):!Paid?TEXT("准备组装"):System->Assembled()?TEXT("五组跟随校准"):TEXT("组件装配"));
    SetText(Stats,FString::Printf(TEXT("%d / %d    ·    %.1f / %.1f 秒    ·    "),System->InstalledCount(),Paid?J.PartCount:R.Parts.Num(),CalibrationProgress,Duration));
    SetText(ScoreValue,J.bFinished?FString::Printf(TEXT("%.0f 分"),J.Quality):TEXT("待完成"));
    const FLinearColor QualityColor=ColdSteelAssemblyPresentation::ScoreColor(J.Quality);
    Stage->SetColorAndOpacity(J.bFinished?QualityColor:ColdSteelUI::TextPrimary);
    ScoreValue->SetColorAndOpacity(J.bFinished?QualityColor:ColdSteelUI::TextTertiary);
    FString Parts;
    for(int32 I=0;I<R.Parts.Num();++I){if(!Parts.IsEmpty())Parts+=TEXT("   ·   ");Parts+=(System->Installed(I)?TEXT("✓ "):TEXT("○ "))+R.Parts[I].Name;}
    SetText(PartsLabel,Parts);
    StatLegend->SetVisibility(Paid?ESlateVisibility::Collapsed:ESlateVisibility::HitTestInvisible);
    BonusBreakdownRow->SetVisibility(Paid?ESlateVisibility::HitTestInvisible:ESlateVisibility::Collapsed);
    if(Paid)
    {
        const double Material=System->MaterialBonus(),Assembly=ColdSteelAssemblyQuality::SkillBonus(System->Score());
        ColdSteelAssemblyPresentation::SetBonus(DamageBonusValue,TEXT("伤害"),Material+Assembly);
        ColdSteelAssemblyPresentation::SetBonus(MaterialBonusValue,TEXT("材质"),Material);
        ColdSteelAssemblyPresentation::SetBonus(AssemblyBonusValue,TEXT("装配"),Assembly);
    }
    else SetText(StatLegend,FString::Printf(TEXT("材质保底 +%.2f%% → 满分伤害 +%.2f%%"),System->MaterialBonus()*100,(System->MaterialBonus()+ColdSteelAssemblyQuality::MaxSkillBonus)*100));
    Timer->SetFillColorAndOpacity(J.bFinished?QualityColor:ColdSteelUI::Accent);
    Timer->SetPercent(J.bFinished?1.f:Paid?(System->InstalledCount()+CalibrationProgress/FMath::Max(.01f,Duration))/FMath::Max(1,J.PartCount+1):0.f);
    FString Why;const bool Can=J.bFinished||(HUD&&HUD->CanStartGunAssembly(Why)&&(Paid?System->CanResume(Why):System->CanStart(Why)));
    ActionButton->SetIsEnabled(CanInteract()&&Can);
    DiscardButton->SetIsEnabled(CanInteract()&&Paid&&!Active&&bCanDiscard);
    RecipeChoice->SetIsEnabled(CanInteract()&&!Paid&&System->Catalog().Num()>1);
    MetalChoice->SetIsEnabled(CanInteract()&&!Paid&&System->Metals().Num()>1);
    SetText(DiscardLabel,J.bFinished?TEXT("废弃成品"):TEXT("取消工件"));
    SetText(ActionLabel,J.bFinished?TEXT("领取成品"):Paid?TEXT("继续组装"):Free?TEXT("免材料开始组装"):TEXT("投入材料并开始"));
    SetText(Status,Pending?TEXT("等待服务器确认…"):!Notice.IsEmpty()?Notice:!Can?Why:J.bFinished?(Free?TEXT("可领取成品或直接废弃；本轮免材料，废弃不返料。"):TEXT("领取成品，或废弃返还一半材料；背包需有足够空间。")):Paid?TEXT("离开保留工件与进度 · 可随时继续或取消"):Free?TEXT("免材料制作 · 完成组装与校准后领取 · 成品不附带弹药"):TEXT("每轮制作一把 · 成品不附带弹药"));
}
void UColdSteelGunAssemblyWidget::HandleAction()
{
    if(!CanInteract()||bAmmoPage||!System||!HUD)return;
    Notice.Reset();
    if(System->Job().bFinished)
    {if(System->Claim(Notice))HUD->SelectGunAssemblyRecipe(System->Recipe().Id);}
    else HUD->StartGunAssembly(Notice);
    bMaterialsDirty=true;Refresh();
}
void UColdSteelGunAssemblyWidget::HandleDiscard()
{
    if(!CanInteract()||bAmmoPage||!System||!HUD||HUD->IsGunAssembly())return;
    Notice.Reset();
    if(System->Discard(Notice)&&GetWorld()->GetNetMode()!=NM_Client)HUD->SelectGunAssemblyRecipe(System->Recipe().Id);
    bMaterialsDirty=true;SetKeyboardFocus();Refresh();
}
void UColdSteelGunAssemblyWidget::HandleClose(){if(HUD)HUD->CloseWorkbench();}
void UColdSteelGunAssemblyWidget::HandleMetalSelected(FString Option,ESelectInfo::Type SelectionType)
{
    if(SelectionType==ESelectInfo::Direct||!System)return;
    const int32 Index=MetalChoice->GetSelectedIndex();
    if(CanInteract()&&!bAmmoPage&&System->Metals().IsValidIndex(Index)&&System->SelectMetal(System->Metals()[Index].Item))Notice.Reset();
    bMaterialsDirty=true;Refresh();SetKeyboardFocus();
}
void UColdSteelGunAssemblyWidget::HandleRecipeSelected(const FString& RecipeId)
{
    if(!System)return;
    if(CanInteract()&&!bAmmoPage&&HUD&&HUD->SelectGunAssemblyRecipe(FName(*RecipeId)))Notice.Reset();
    else RecipeChoice->SetSelectedOption(System->Recipe().Id.ToString());
    bMaterialsDirty=true;LoadMold();Refresh();
}
FReply UColdSteelGunAssemblyWidget::NativeOnMouseButtonDown(const FGeometry& Geometry,const FPointerEvent& Event)
{return FReply::Handled();}

UTextBlock* UColdSteelGunAssemblyWidget::Text(const FString& Caption,float Pixels,bool bNumeric,bool bMedium)
{
    auto* T=WidgetTree->ConstructWidget<UTextBlock>();T->SetText(FText::FromString(Caption));T->SetAutoWrapText(false);
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
    RecipeChoice=WidgetTree->ConstructWidget<UDevelopmentItemPicker>();
    RecipeChoice->SetPhysicalFontSizes(true);
    TArray<FColdSteelCatalogEntry> RecipeOptions;
    for(const auto& Recipe:System->Catalog())
    {
        const auto Item=Model->CreateItem(Recipe.Output);FColdSteelCatalogEntry Entry;
        Entry.Definition=Recipe.Id.ToString();Entry.Name=ColdSteelInventory::Text(Item,TEXT("name"));
        Entry.Group=ColdSteelInventory::Text(Item,TEXT("weaponTypeTag"));if(Entry.Group.IsEmpty())Entry.Group=TEXT("其他枪械");
        Entry.GroupOrder=Entry.Group==TEXT("手枪")?0:Entry.Group==TEXT("左轮手枪")?1:Entry.Group==TEXT("突击步枪")?2:
            Entry.Group==TEXT("霰弹枪")?3:Entry.Group==TEXT("狙击步枪")?4:Entry.Group==TEXT("轻机枪")?5:6;
        RecipeOptions.Add(MoveTemp(Entry));
    }
    RecipeOptions.StableSort([](const auto& A,const auto& B){return A.GroupOrder==B.GroupOrder?A.Group<B.Group:A.GroupOrder<B.GroupOrder;});
    RecipeChoice->SetOptions(RecipeOptions,System->Recipe().Id.ToString(),true);
    RecipeChoice->OnSelectionChanged.AddDynamic(this,&ThisClass::HandleRecipeSelected);
    ColdSteelToolTip::Set(*RecipeChoice, FText::FromString(TEXT("按枪械类别选择配方；当前工件领取或取消后可以更换。")));
    auto* ChoiceSize=WidgetTree->ConstructWidget<USizeBox>();ChoiceSize->SetContent(RecipeChoice);ButtonSizes.Add(ChoiceSize);
    Space(RecipeCard->AddChildToVerticalBox(ChoiceSize),FMargin(0,0,0,8));
    auto* MetalCaption=Text(TEXT("金属材质 · 决定伤害保底"),12);MetalCaption->SetColorAndOpacity(ColdSteelUI::TextTertiary);
    Space(RecipeCard->AddChildToVerticalBox(MetalCaption),FMargin(0,0,0,4));
    MetalChoice=WidgetTree->ConstructWidget<UComboBoxString>();
    MetalChoice->OnGenerateWidgetEvent.BindDynamic(this,&ThisClass::GenerateRecipeOption);
    for(const auto& Metal:System->Metals())MetalChoice->AddOption(FString::Printf(TEXT("%s · 保底 +%.0f%%"),
        *ColdSteelInventory::Text(Model->CreateItem(Metal.Item.ToString()),TEXT("name")),Metal.Bonus*100));
    MetalChoice->OnSelectionChanged.AddDynamic(this,&ThisClass::HandleMetalSelected);
    ColdSteelToolTip::Set(*MetalChoice, FText::FromString(TEXT("开始时锁定所选金属和保底；装配与校准最高再增加 15% 伤害。")));
    auto* MetalSize=WidgetTree->ConstructWidget<USizeBox>();MetalSize->SetContent(MetalChoice);ButtonSizes.Add(MetalSize);
    Space(RecipeCard->AddChildToVerticalBox(MetalSize),FMargin(0,0,0,8));
    Materials=Text(TEXT("所需材料"),14,false,true);Space(RecipeCard->AddChildToVerticalBox(Materials),FMargin(0,0,0,4));
    auto* Source=Text(TEXT("材料来源 · 背包 + 主仓库"),12);Source->SetColorAndOpacity(ColdSteelUI::TextTertiary);MaterialSource=Source;
    Space(RecipeCard->AddChildToVerticalBox(Source),FMargin(0,0,0,4));
    auto* Grid=WidgetTree->ConstructWidget<UGridPanel>();MaterialGrid=Grid;Grid->SetColumnFill(0,1.f);RecipeCard->AddChildToVerticalBox(Grid);
    auto* NameHeader=Text(TEXT("材料"),12);auto* QuantityHeader=Text(TEXT("持有 / 需要"),12);auto* StateHeader=Text(TEXT("状态"),12);
    MaterialQuantityHeader=QuantityHeader;
    for(auto* Label:{NameHeader,QuantityHeader,StateHeader}){Label->SetColorAndOpacity(ColdSteelUI::TextSecondary);Label->SetAutoWrapText(false);}
    AddMaterialCell(NameHeader,0,0);AddMaterialCell(QuantityHeader,0,1);AddMaterialCell(StateHeader,0,2);
    int32 MaterialRowCount=0;
    for(const auto& Recipe:System->Catalog())MaterialRowCount=FMath::Max(MaterialRowCount,Recipe.Inputs.Num()+1);
    EnsureMaterialRows(MaterialRowCount);
    auto* StateCard=Card(Content);
    Stage=Text(TEXT("准备组装"),16,false,true);Space(StateCard->AddChildToVerticalBox(Stage),FMargin(0,0,0,8));
    auto* StatsRow=WidgetTree->ConstructWidget<UHorizontalBox>();Space(StateCard->AddChildToVerticalBox(StatsRow),FMargin(0,0,0,4));
    Stats=Text(TEXT(""),16,true);StatsRow->AddChildToHorizontalBox(Stats)->SetVerticalAlignment(VAlign_Center);
    ScoreValue=Text(TEXT("待完成"),16,true);StatsRow->AddChildToHorizontalBox(ScoreValue)->SetVerticalAlignment(VAlign_Center);
    StatLegend=Text(TEXT("已装组件   /   校准进度   /   工艺评分"),12);StatLegend->SetColorAndOpacity(ColdSteelUI::TextTertiary);StateCard->AddChildToVerticalBox(StatLegend);
    BonusBreakdownRow=WidgetTree->ConstructWidget<UWrapBox>();StateCard->AddChildToVerticalBox(BonusBreakdownRow);
    DamageBonusValue=Text(TEXT(""),12);MaterialBonusValue=Text(TEXT(""),12);AssemblyBonusValue=Text(TEXT(""),12);
    for(UTextBlock* Value:{DamageBonusValue.Get(),MaterialBonusValue.Get(),AssemblyBonusValue.Get()})BonusBreakdownRow->AddChildToWrapBox(Value);
    PartsLabel=Text(TEXT(""),12);PartsLabel->SetAutoWrapText(true);PartsLabel->SetColorAndOpacity(ColdSteelUI::TextSecondary);Space(StateCard->AddChildToVerticalBox(PartsLabel),FMargin(0,8,0,0));
    RefundPreview=Text(TEXT(""),12);RefundPreview->SetAutoWrapText(true);RefundPreview->SetColorAndOpacity(ColdSteelUI::TextSecondary);Space(StateCard->AddChildToVerticalBox(RefundPreview),FMargin(0,8,0,0));
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
    PreviewScope=Text(TEXT(""),12);PreviewScope->SetAutoWrapText(true);PreviewScope->SetColorAndOpacity(ColdSteelUI::TextTertiary);
    Space(ParameterContent->AddChildToVerticalBox(PreviewScope),FMargin(0,12,0,0));
    auto* Instructions=Card(Content);Space(Instructions->AddChildToVerticalBox(Text(TEXT("操作说明"),16,false,true)),FMargin(0,0,0,8));
    auto* DragHelp=Text(TEXT("按住左键拿取组件，对准明亮安装圈；长按 Q / E 连续旋转，滚轮微调，松开左键安装。"),14);DragHelp->SetAutoWrapText(true);Space(Instructions->AddChildToVerticalBox(DragHelp),FMargin(0,0,0,8));
    auto* Help=Text(TEXT("Tab 选择下一件 · 长按 Q / E 旋转 · 滚轮微调 · 右键放回\n装好后校准 34 秒：准备 1 秒，5 组各跟随 5 秒，组间休息 2 秒。按住左键跟随变径圆圈；出圈或松开仍计时。结束自动进入交付，Esc 保存并返回。\n废弃返还一半实际材料，逐项向下取整；免材料工件不返料。"),12);Help->SetAutoWrapText(true);
    Help->SetColorAndOpacity(ColdSteelUI::TextSecondary);Instructions->AddChildToVerticalBox(Help);
    Footer=WidgetTree->ConstructWidget<UBorder>();Footer->SetBrushColor(ColdSteelUI::HeaderTint);Stack->AddChildToVerticalBox(Footer);
    ManufacturingActions=WidgetTree->ConstructWidget<UWidgetSwitcher>();Footer->SetContent(ManufacturingActions);
    auto* AmmoFoot=WidgetTree->ConstructWidget<UVerticalBox>();ManufacturingActions->AddChild(AmmoFoot);
    BuildAmmoCard(AmmoContent,AmmoFoot);
    auto* Foot=WidgetTree->ConstructWidget<UVerticalBox>();ManufacturingActions->AddChild(Foot);
    ManufacturingActions->SetActiveWidgetIndex(bAmmoPage?0:1);
    Status=Text(TEXT(""),14);Status->SetAutoWrapText(true);Status->SetColorAndOpacity(ColdSteelUI::TextSecondary);Space(Foot->AddChildToVerticalBox(Status),FMargin(0,0,0,8));
    auto* Actions=WidgetTree->ConstructWidget<UHorizontalBox>();Foot->AddChildToVerticalBox(Actions);
    UTextBlock* NewActionLabel=nullptr;ActionButton=Button(TEXT("开始组装"),NewActionLabel);ActionLabel=NewActionLabel;ActionButton->OnClicked.AddDynamic(this,&ThisClass::HandleAction);
    auto* ActionSize=WidgetTree->ConstructWidget<USizeBox>();ActionSize->SetContent(ActionButton);ButtonSizes.Add(ActionSize);Actions->AddChildToHorizontalBox(ActionSize)->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    UTextBlock* NewDiscardLabel=nullptr;DiscardButton=Button(TEXT("取消工件"),NewDiscardLabel);DiscardLabel=NewDiscardLabel;DiscardButton->OnClicked.AddDynamic(this,&ThisClass::HandleDiscard);
    ColdSteelToolTip::Set(*DiscardButton, FText::FromString(TEXT("取消工件或废弃未领取成品，按上方预览返还一半实际投入材料；免材料工件不返料。背包放不下返料时保留工件。")));
    auto* DiscardSize=WidgetTree->ConstructWidget<USizeBox>();DiscardSize->SetContent(DiscardButton);ButtonSizes.Add(DiscardSize);DiscardActionSlot=Actions->AddChildToHorizontalBox(DiscardSize);DiscardActionSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    UpdateScale();LoadMold();Refresh();
}

void UColdSteelGunAssemblyWidget::NativeConstruct()
{
    Super::NativeConstruct();if(Model&&!ChangedHandle.IsValid())ChangedHandle=Model->OnChanged.AddWeakLambda(this,[this]{bMaterialsDirty=true;bAmmoDirty=true;});
    if(System&&!AssemblyResultHandle.IsValid())AssemblyResultHandle=System->OnNetworkResult.AddWeakLambda(this,[this](const FString& Mode,bool Success,const FString& Reason)
    {
        Notice=Reason;bMaterialsDirty=bAmmoDirty=true;
        if(HUD&&(Mode==TEXT("assembly.start")||Mode==TEXT("assembly.resume")))HUD->GunAssemblyStartFinished(Success);
        if(Success&&HUD&&(Mode==TEXT("assembly.claim")||Mode==TEXT("assembly.discard")))HUD->SelectGunAssemblyRecipe(System->Recipe().Id);
        Refresh();
    });
    if(Crafting&&!AmmoResultHandle.IsValid())AmmoResultHandle=Crafting->OnNetworkResult.AddWeakLambda(this,[this](FName Recipe,bool Success,const FString& Reason)
    {
        if(!Crafting->IsAmmoRecipe(Recipe))return;
        AmmoNotice=Reason;bAmmoDirty=bMaterialsDirty=true;Refresh();
    });
}

void UColdSteelGunAssemblyWidget::NativeDestruct()
{
    if(Model&&ChangedHandle.IsValid()){Model->OnChanged.Remove(ChangedHandle);ChangedHandle.Reset();}
    if(System&&AssemblyResultHandle.IsValid()){System->OnNetworkResult.Remove(AssemblyResultHandle);AssemblyResultHandle.Reset();}
    if(Crafting&&AmmoResultHandle.IsValid()){Crafting->OnNetworkResult.Remove(AmmoResultHandle);AmmoResultHandle.Reset();}
    if(RecipeChoice)RecipeChoice->CloseMenu();if(AmmoChoice)AmmoChoice->CloseMenu();
    Super::NativeDestruct();
}

void UColdSteelGunAssemblyWidget::RefreshProductPreview()
{
    using ColdSteelAssemblyPresentation::SetText;
    const auto* Recipe=&System->Recipe();
    const auto& Job=System->Job();
    const bool HasJob=!Job.Id.IsEmpty();
    FColdSteelItem Item=HasJob?Job.Item:Recipe?Model->CreateItem(Recipe->Output):FColdSteelItem{};
    if(HasJob)ColdSteelAssemblyQuality::Apply(Item,Job);
    else if(const auto* Metal=System->FindMetal(System->Metal()))
    {
        FColdSteelGunAssemblyJob Preview;Preview.QualityVersion=ColdSteelAssemblyQuality::Version;
        Preview.Metal=Metal->Item;Preview.MaterialBonus=Metal->Bonus;
        Preview.MaterialName=ColdSteelInventory::Text(Model->CreateItem(Metal->Item.ToString()),TEXT("name"));
        ColdSteelAssemblyQuality::Apply(Item,Preview);
    }
    const auto Data=Item.Data.IsEmpty()?FColdSteelTooltipContent{}:
        BuildColdSteelItemTooltip(Item,Model,GetGameInstance()->GetSubsystem<UGunsmithSystem>());
    SetText(PreviewName,Data.Name.IsEmpty()?TEXT("暂无成品参数"):Data.Name);
    SetText(PreviewStage,HasJob?(Job.bFinished?TEXT("成品实际参数 · 已计工艺伤害"):TEXT("当前工件参数 · 已计工艺伤害")):TEXT("材质保底参数 · 未计装配提升"));
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
    BonusBreakdownRow->SetInnerSlotPadding(FVector2D(12/Scale,4/Scale));
    for(const auto& L:Labels)if(auto* T=L.Widget.Get())T->SetFont(L.Numeric?GunsmithUI::NumberFont(L.Pixels/Scale,L.Medium):GunsmithUI::TextFont(L.Pixels/Scale,L.Medium));
    for(const auto& Option:RecipeOptionWidgets)if(auto* Widget=Option.Get())Widget->SetPixelScale(Scale);
    for(const auto& W:Buttons)if(auto* B=W.Get()){B->SetStyle(ColdSteelUI::ButtonStyle(Scale));if(auto* ButtonSlot=Cast<UButtonSlot>(B->GetContent()->Slot))ButtonSlot->SetPadding(FMargin(12/Scale,4/Scale));}
    for(const auto& W:ButtonSizes)if(auto* S=W.Get())S->SetHeightOverride(ColdSteelUI::ActionHeight/Scale);
    CloseSize->SetWidthOverride(ColdSteelUI::ActionHeight/Scale);
    DiscardActionSlot->SetPadding(FMargin(ColdSteelUI::ActionGap/Scale,0,0,0));
    RecipeChoice->SetPixelScale(Scale);AmmoChoice->SetPixelScale(Scale);
    auto ComboStyle=MetalChoice->GetWidgetStyle();auto ComboButton=ComboStyle.ComboButtonStyle;
    ComboButton.SetButtonStyle(ColdSteelUI::ButtonStyle(Scale));
    ComboButton.SetMenuBorderBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::Gray(25,252),ColdSteelUI::CardRadius/Scale,ColdSteelUI::Border,1/Scale));
    ComboButton.DownArrowImage.ImageSize=FVector2D(8/Scale,8/Scale);
    ComboButton.SetDownArrowPadding(FMargin(4/Scale,0,0,0));ComboButton.SetShadowOffset(FVector2D::ZeroVector);
    ComboStyle.SetComboButtonStyle(ComboButton);
    auto ItemStyle=MetalChoice->GetItemStyle();
    ItemStyle.SetEvenRowBackgroundBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::Content,ColdSteelUI::ButtonRadius/Scale));
    ItemStyle.SetOddRowBackgroundBrush(ItemStyle.EvenRowBackgroundBrush);
    ItemStyle.SetEvenRowBackgroundHoveredBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonHover,ColdSteelUI::ButtonRadius/Scale));
    ItemStyle.SetOddRowBackgroundHoveredBrush(ItemStyle.EvenRowBackgroundHoveredBrush);
    ItemStyle.SetActiveBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonHover,ColdSteelUI::ButtonRadius/Scale,ColdSteelUI::Accent,1/Scale));
    ItemStyle.SetInactiveBrush(ItemStyle.ActiveBrush);
    for(auto* Choice:{MetalChoice.Get()})if(Choice)
    {
        Choice->SetWidgetStyle(ComboStyle);Choice->SetItemStyle(ItemStyle);
        Choice->SetContentPadding(FMargin(22/Scale,4/Scale,10/Scale,4/Scale));Choice->SetMaxListHeight(240/Scale);
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
