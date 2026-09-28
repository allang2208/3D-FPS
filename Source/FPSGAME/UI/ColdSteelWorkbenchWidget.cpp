#include "ColdSteelWorkbenchWidget.h"
#include "ColdSteelGunRecipeOptionWidget.h"
#include "ColdSteelHUDWidget.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelInventoryTypes.h"
#include "ColdSteelUIStyle.h"
#include "ColdSteelItemTooltipData.h"
#include "GunsmithUIStyle.h"
#include "../Weapons/GunsmithSystem.h"
#include "../Building/CraftingSystem.h"
#include "../Building/VoxelBuildWorld.h"
#include "Blueprint/WidgetTree.h"
#include "Components/BackgroundBlur.h"
#include "Components/Border.h"
#include "Components/Button.h"
#include "Components/ButtonSlot.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/ComboBoxString.h"
#include "Components/GridPanel.h"
#include "Components/GridSlot.h"
#include "Components/HorizontalBox.h"
#include "Components/HorizontalBoxSlot.h"
#include "Components/Image.h"
#include "Components/ScaleBox.h"
#include "Components/ScrollBox.h"
#include "Components/SizeBox.h"
#include "Components/SizeBoxSlot.h"
#include "Components/TextBlock.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "Engine/Texture2D.h"
#include "ImageUtils.h"
#include "Misc/Paths.h"

// 占位轴名（同冶炼 AxisNames 口径的三页签结构）：工作台升级轴后续设计时只换这张表和
// RefreshUpgrade 里的 Lv/效果/材料三处读数，控件结构与动画一概不动。
// 命名带文件前缀：unity 批量编译会把本文件与冶炼 .cpp 并进同一翻译单元，匿名 namespace 拦不住重名（2026-09-24 构建 C2374 教训）。
namespace { const TCHAR* const WorkbenchAxisNames[3]={TEXT("升级轴一"),TEXT("升级轴二"),TEXT("升级轴三")}; }

void UColdSteelWorkbenchRowProxy::AxisClicked()
{
    if(auto* Owner=Panel.Get())Owner->SelectUpgradeAxis(Axis);
}

UTextBlock* UColdSteelWorkbenchWidget::Text(const FString& Caption,float Pixels,const FLinearColor& Color,bool Numeric,bool Medium,bool bWrap)
{
    auto* Label=WidgetTree->ConstructWidget<UTextBlock>();
    Label->SetText(FText::FromString(Caption));Label->SetColorAndOpacity(Color);
    Label->SetFont(Numeric?GunsmithUI::NumberFont(Pixels/Scale,Medium):GunsmithUI::TextFont(Pixels/Scale,Medium));
    if(bWrap)Label->SetAutoWrapText(true);   // Slate 不裁剪不换位＝文字画出玻璃框（正式规则 §3）。
    Label->SetVisibility(ESlateVisibility::HitTestInvisible);
    Labels.Add({Label,Pixels,Numeric,Medium});
    return Label;
}

UButton* UColdSteelWorkbenchWidget::Action(const FString& Caption)
{
    auto* B=WidgetTree->ConstructWidget<UButton>();
    B->SetContent(Text(Caption,14,ColdSteelUI::TextPrimary));
    StyledButtons.Add(B);return B;
}

// —— 打铁 ColdSteelForgingWidget 同款构件助手：按钮/卡片/行距/三列表，全部进缓存数组随 Scale 重排。——
UButton* UColdSteelWorkbenchWidget::Button(const FString& Caption,UTextBlock*& Label)
{
    auto* B=WidgetTree->ConstructWidget<UButton>();Label=Text(Caption,14,ColdSteelUI::TextPrimary,false,true);
    Label->SetJustification(ETextJustify::Center);Label->SetAutoWrapText(false);Label->SetWrapTextAt(0);
    B->SetContent(Label);
    auto* LabelSlot=Cast<UButtonSlot>(Label->Slot);LabelSlot->SetHorizontalAlignment(HAlign_Fill);LabelSlot->SetVerticalAlignment(VAlign_Center);
    Buttons.Add(B);return B;
}
UVerticalBox* UColdSteelWorkbenchWidget::Card(UVerticalBox* Parent)
{
    auto* Border=WidgetTree->ConstructWidget<UBorder>();Cards.Add(Border);
    Space(Parent->AddChildToVerticalBox(Border),FMargin(0,0,0,8));
    auto* Column=WidgetTree->ConstructWidget<UVerticalBox>();Border->SetContent(Column);return Column;
}
void UColdSteelWorkbenchWidget::Space(UVerticalBoxSlot* RowSlot,FMargin RowPadding)
{RowSpacings.Add({RowSlot,RowPadding});}
void UColdSteelWorkbenchWidget::AddMaterialCell(UWidget* Widget,int32 Row,int32 Column)
{
    auto* CellSlot=MaterialGrid->AddChildToGrid(Widget,Row,Column);
    CellSlot->SetHorizontalAlignment(Column==0?HAlign_Fill:HAlign_Right);
    CellSlot->SetVerticalAlignment(VAlign_Center);
    const float CellScale=Scale>0?Scale:1.f;
    CellSlot->SetPadding(FMargin(Column==0?0.f:12.f/CellScale,4.f/CellScale,0,4.f/CellScale));
    MaterialCellSlots.Add(CellSlot);
}
void UColdSteelWorkbenchWidget::EnsureMaterialRows(int32 Count)
{
    while(MaterialRows.Num()<Count)
    {
        FMaterialRow Row;
        auto* Name=Text(TEXT(""),14,ColdSteelUI::TextPrimary,false,false,true);Row.Name=Name;
        auto* Amount=WidgetTree->ConstructWidget<UHorizontalBox>();Row.Amount=Amount;
        auto* Owned=Text(TEXT(""),14,ColdSteelUI::TextPrimary,true);Row.Owned=Owned;
        auto* Separator=Text(TEXT(" / "),14,ColdSteelUI::TextSecondary,true);Row.Separator=Separator;
        auto* Required=Text(TEXT(""),14,ColdSteelUI::TextSecondary,true);Row.Required=Required;
        for(const auto& Number:{Owned,Separator,Required})
        {
            Number->SetAutoWrapText(false);Number->SetJustification(ETextJustify::Right);
            Amount->AddChildToHorizontalBox(Number)->SetVerticalAlignment(VAlign_Center);
        }
        auto* State=Text(TEXT(""),14,ColdSteelUI::TextPrimary);Row.State=State;
        State->SetAutoWrapText(false);State->SetJustification(ETextJustify::Right);
        const int32 GridRow=MaterialRows.Num()+1;
        AddMaterialCell(Name,GridRow,0);AddMaterialCell(Amount,GridRow,1);AddMaterialCell(State,GridRow,2);
        Name->SetVisibility(ESlateVisibility::Collapsed);Amount->SetVisibility(ESlateVisibility::Collapsed);State->SetVisibility(ESlateVisibility::Collapsed);
        MaterialRows.Add(Row);
    }
}

void UColdSteelWorkbenchWidget::Configure(UColdSteelHUDWidget* Owner)
{
    HUD=Owner;
}

void UColdSteelWorkbenchWidget::NativeOnInitialized()
{
    Super::NativeOnInitialized();SetIsFocusable(true);
    Scale=ColdSteelUI::PixelScale(this);
    Model=GetGameInstance()?GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr;
    Crafting=GetGameInstance()?GetGameInstance()->GetSubsystem<UColdSteelCraftingSystem>():nullptr;
    // 根＝Canvas：主题层把本 widget 槽位扩到屏幕左缘→面板右缘的全宽命中区（冶炼 §7.7 教训：
    // 挂在父边界外的负坐标子控件能绘制但收不到点击），Shell 用正偏移贴到面板位，
    // 页签/弹层坐标一律以屏幕像素折算、全部落在槽位内。
    RootCanvas=WidgetTree->ConstructWidget<UCanvasPanel>();WidgetTree->RootWidget=RootCanvas;
    // 本体/根画布均 SelfHitTestInvisible：透明区放行世界点击、子控件照常命中
    //（HitTestInvisible 会连子树屏蔽命中——冶炼 §7.8 已入档的根因）。
    SetVisibility(ESlateVisibility::SelfHitTestInvisible);
    RootCanvas->SetVisibility(ESlateVisibility::SelfHitTestInvisible);
    // 外壳三段式（与仓库/背包/冶炼同源）：描边 Border → 真实 UBackgroundBlur → 玻璃 Tint → 内容。
    auto* ShellOuter=WidgetTree->ConstructWidget<UBorder>();
    ShellOutline=ShellOuter;
    ShellOuter->SetBrush(ColdSteelUI::RoundedBrush(FLinearColor::Transparent,ColdSteelUI::PanelRadius/Scale,GunsmithUI::Edge,1/Scale));
    ShellOuter->SetPadding(FMargin(1/Scale));
    ShellSlot=RootCanvas->AddChildToCanvas(ShellOuter);
    ShellSlot->SetAnchors(FAnchors(0,0,1,1));ShellSlot->SetOffsets(FMargin(0));
    Blur=WidgetTree->ConstructWidget<UBackgroundBlur>();
    Blur->SetBlurStrength(ColdSteelUI::GlassBlurStrength);Blur->SetOverrideAutoRadiusCalculation(true);
    Blur->SetBlurRadius(ColdSteelUI::GlassBlurRadius);Blur->SetCornerRadius(FVector4(10,10,10,10));
    Blur->SetLowQualityFallbackBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::GlassFallback,ColdSteelUI::PanelRadius));
    ShellOuter->SetContent(Blur);
    auto* Tint=WidgetTree->ConstructWidget<UBorder>();
    Tint->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::GlassTint,ColdSteelUI::PanelRadius/Scale));
    Tint->SetPadding(FMargin(0));Blur->SetContent(Tint);
    Shell=Tint;
    auto* Stack=WidgetTree->ConstructWidget<UVerticalBox>();Tint->SetContent(Stack);

    HeaderSurface=WidgetTree->ConstructWidget<UBorder>();
    HeaderSurface->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::HeaderTint,ColdSteelUI::PanelRadius/Scale));
    Stack->AddChildToVerticalBox(HeaderSurface);
    HeaderSize=WidgetTree->ConstructWidget<USizeBox>();HeaderSurface->SetContent(HeaderSize);
    auto* Heading=WidgetTree->ConstructWidget<UHorizontalBox>();HeaderSize->SetContent(Heading);
    // 顶栏＝标题（20px Medium 档）＋ × 关闭（36px 方钮，打铁同款）：面板独立于背包，自带出口（Esc 同效）。
    PanelTitle=Text(TEXT("制作 · 工作台"),20,ColdSteelUI::TextPrimary,false,true);
    auto* TitleSlot=Heading->AddChildToHorizontalBox(PanelTitle);
    TitleSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));TitleSlot->SetVerticalAlignment(VAlign_Center);
    UTextBlock* CloseLabel=nullptr;auto* PanelClose=Button(TEXT("×"),CloseLabel);
    PanelClose->OnClicked.AddDynamic(this,&ThisClass::HandleClose);
    CloseSize=WidgetTree->ConstructWidget<USizeBox>();CloseSize->SetContent(PanelClose);ButtonSizes.Add(CloseSize);
    Heading->AddChildToHorizontalBox(CloseSize)->SetVerticalAlignment(VAlign_Center);

    // —— 中段＝Scroll→Body→卡列（打铁/装配同款）：StatusCard 卡面 12px 内沿、卡距 8px、滚动条 6px。——
    Scroll=WidgetTree->ConstructWidget<UScrollBox>();Scroll->SetConsumeMouseWheel(EConsumeMouseWheel::Always);
    BodySlot=Stack->AddChildToVerticalBox(Scroll);BodySlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    Body=WidgetTree->ConstructWidget<UBorder>();Body->SetBrushColor(FLinearColor::Transparent);Scroll->AddChild(Body);
    auto* CardColumn=WidgetTree->ConstructWidget<UVerticalBox>();Body->SetContent(CardColumn);

    // 配方卡：标题 16 Medium＋打铁同款 ComboBox（36px、列表最高 240）＋材料三列表（材料|持有/需要|状态）。
    auto* RecipeCard=Card(CardColumn);
    auto* RecipeCaption=Text(TEXT("配方 · 制作"),12,ColdSteelUI::TextTertiary);
    Space(RecipeCard->AddChildToVerticalBox(RecipeCaption),FMargin(0,0,0,4));
    RecipeTitle=Text(TEXT("—"),16,ColdSteelUI::TextPrimary,false,true);Space(RecipeCard->AddChildToVerticalBox(RecipeTitle),FMargin(0,0,0,8));
    RecipeChoice=WidgetTree->ConstructWidget<UComboBoxString>();
    RecipeChoice->OnGenerateWidgetEvent.BindDynamic(this,&ThisClass::GenerateRecipeOption);
    if(Crafting)for(const FColdSteelCraftingRecipe& Recipe:Crafting->Catalog())
        RecipeChoice->AddOption(FString::Printf(TEXT("%s ×%lld"),*DefinitionName(Recipe.Output),Recipe.OutputCount));
    RecipeChoice->OnSelectionChanged.AddDynamic(this,&ThisClass::HandleRecipeSelected);
    RecipeChoice->SetToolTipText(FText::FromString(TEXT("选择制作配方；材料取自背包与主仓库，制作即时结算。")));
    RecipeChoiceSize=WidgetTree->ConstructWidget<USizeBox>();RecipeChoiceSize->SetContent(RecipeChoice);ButtonSizes.Add(RecipeChoiceSize);
    Space(RecipeCard->AddChildToVerticalBox(RecipeChoiceSize),FMargin(0,0,0,8));
    Materials=Text(TEXT("所需材料"),14,ColdSteelUI::TextPrimary,false,true);Space(RecipeCard->AddChildToVerticalBox(Materials),FMargin(0,0,0,4));
    MaterialSource=Text(TEXT("材料来源 · 背包 + 主仓库"),12,ColdSteelUI::TextTertiary);Space(RecipeCard->AddChildToVerticalBox(MaterialSource),FMargin(0,0,0,4));
    MaterialGrid=WidgetTree->ConstructWidget<UGridPanel>();MaterialGrid->SetColumnFill(0,1.f);RecipeCard->AddChildToVerticalBox(MaterialGrid);
    auto* NameHeader=Text(TEXT("材料"),12,ColdSteelUI::TextSecondary);
    auto* QuantityHeader=Text(TEXT("持有 / 需要"),12,ColdSteelUI::TextSecondary);
    auto* StateHeader=Text(TEXT("状态"),12,ColdSteelUI::TextSecondary);
    MaterialQuantityHeader=QuantityHeader;
    for(auto* Label:{NameHeader,QuantityHeader,StateHeader})Label->SetAutoWrapText(false);
    AddMaterialCell(NameHeader,0,0);AddMaterialCell(QuantityHeader,0,1);AddMaterialCell(StateHeader,0,2);
    if(Crafting)
    {
        int32 MaterialRowCount=0;
        for(const FColdSteelCraftingRecipe& Recipe:Crafting->Catalog())MaterialRowCount=FMath::Max(MaterialRowCount,Recipe.Inputs.Num());
        EnsureMaterialRows(MaterialRowCount);
    }

    // The same status card hierarchy as forging, with values appropriate to instant crafting.
    auto* StateCard=Card(CardColumn);
    Stage=Text(TEXT("工作台空闲"),16,ColdSteelUI::TextTertiary,false,true);Space(StateCard->AddChildToVerticalBox(Stage),FMargin(0,0,0,8));
    auto* Summary=WidgetTree->ConstructWidget<UHorizontalBox>();
    Space(StateCard->AddChildToVerticalBox(Summary),FMargin(0,0,0,8));
    auto SummaryValue=[&](const TCHAR* Caption)
    {
        auto* Column=WidgetTree->ConstructWidget<UVerticalBox>();
        Summary->AddChildToHorizontalBox(Column)->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
        auto* Value=Text(TEXT("0"),16,ColdSteelUI::TextPrimary,true);
        Space(Column->AddChildToVerticalBox(Value),FMargin(0,0,0,4));
        Column->AddChildToVerticalBox(Text(Caption,12,ColdSteelUI::TextSecondary,false,false,true));
        return Value;
    };
    Stats=SummaryValue(TEXT("材料可制作 / 份"));BatchStat=SummaryValue(TEXT("本次制作 / 份"));OutputStat=SummaryValue(TEXT("本次产出 / 件"));
    StatLegend=Text(TEXT("材料可制作份数不含背包容量限制，单批最多 99 份。"),12,ColdSteelUI::TextTertiary,false,false,true);
    StateCard->AddChildToVerticalBox(StatLegend);

    // 成品预览：左产物图标（ScaleToFit 等比居中，不拉伸）｜右参数卡（浮窗摘要同口径两列表）。
    auto* PreviewCaption=Text(TEXT("成品预览 · 参数"),14,ColdSteelUI::TextPrimary,false,true);
    Space(CardColumn->AddChildToVerticalBox(PreviewCaption),FMargin(0,4,0,8));
    BoardSize=WidgetTree->ConstructWidget<USizeBox>();
    PreviewLayout=WidgetTree->ConstructWidget<UGridPanel>();BoardSize->SetContent(PreviewLayout);
    PreviewLayout->SetColumnFill(0,1.f);PreviewLayout->SetColumnFill(1,1.f);PreviewLayout->SetRowFill(0,1.f);
    Space(CardColumn->AddChildToVerticalBox(BoardSize),FMargin(0,0,0,8));
    auto* IconFrame=WidgetTree->ConstructWidget<UBorder>();IconFrameBorder=IconFrame;Cards.Add(IconFrame);
    PreviewIconSlot=PreviewLayout->AddChildToGrid(IconFrame,0,0);
    PreviewIconSlot->SetHorizontalAlignment(HAlign_Fill);PreviewIconSlot->SetVerticalAlignment(VAlign_Fill);
    IconFrameSize=WidgetTree->ConstructWidget<USizeBox>();IconFrame->SetContent(IconFrameSize);
    auto* IconContent=WidgetTree->ConstructWidget<UVerticalBox>();IconFrameSize->SetContent(IconContent);
    IconScale=WidgetTree->ConstructWidget<UScaleBox>();IconScale->SetStretch(EStretch::ScaleToFit);
    IconContent->AddChildToVerticalBox(IconScale)->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    PreviewIcon=WidgetTree->ConstructWidget<UImage>();PreviewIcon->SetVisibility(ESlateVisibility::Collapsed);IconScale->SetContent(PreviewIcon);
    PreviewEmpty=Text(TEXT("暂无物品图像"),12,ColdSteelUI::TextTertiary,false,false,true);
    PreviewEmpty->SetJustification(ETextJustify::Center);IconContent->AddChildToVerticalBox(PreviewEmpty);
    PreviewParameterCard=WidgetTree->ConstructWidget<UBorder>();Cards.Add(PreviewParameterCard);
    PreviewDetailsSlot=PreviewLayout->AddChildToGrid(PreviewParameterCard,0,1);
    PreviewDetailsSlot->SetHorizontalAlignment(HAlign_Fill);PreviewDetailsSlot->SetVerticalAlignment(VAlign_Fill);
    PreviewScroll=WidgetTree->ConstructWidget<UScrollBox>();PreviewParameterCard->SetContent(PreviewScroll);
    PreviewScroll->SetConsumeMouseWheel(EConsumeMouseWheel::WhenScrollingPossible);
    auto* ParameterContent=WidgetTree->ConstructWidget<UVerticalBox>();PreviewScroll->AddChild(ParameterContent);
    PreviewName=Text(TEXT("—"),16,ColdSteelUI::TextPrimary,false,true,true);Space(ParameterContent->AddChildToVerticalBox(PreviewName),FMargin(0,0,0,8));
    PreviewStage=Text(TEXT("全新成品 · 基础品质"),12,ColdSteelUI::TextSecondary,false,false,true);
    Space(ParameterContent->AddChildToVerticalBox(PreviewStage),FMargin(0,0,0,12));
    PreviewParameterGrid=WidgetTree->ConstructWidget<UGridPanel>();PreviewParameterGrid->SetColumnFill(0,1.f);
    ParameterContent->AddChildToVerticalBox(PreviewParameterGrid);
    PreviewScope=Text(TEXT(""),12,ColdSteelUI::TextTertiary,false,false,true);Space(ParameterContent->AddChildToVerticalBox(PreviewScope),FMargin(0,12,0,0));

    // 操作说明卡：说明 14＋规则 12＋附注 12（打铁"操作说明"卡同构）。
    auto* Instructions=Card(CardColumn);
    Space(Instructions->AddChildToVerticalBox(Text(TEXT("操作说明"),16,ColdSteelUI::TextPrimary,false,true)),FMargin(0,0,0,8));
    Space(Instructions->AddChildToVerticalBox(Text(TEXT("选择配方和制作份数，点击「直接制作」，成品立即放入背包。"),14,ColdSteelUI::TextPrimary,false,false,true)),FMargin(0,0,0,8));
    Space(Instructions->AddChildToVerticalBox(Text(TEXT("优先消耗背包材料，再使用主仓库。材料不足或背包放不下时不扣除材料。"),12,ColdSteelUI::TextSecondary,false,false,true)),FMargin(0,0,0,8));
    Instructions->AddChildToVerticalBox(Text(TEXT("Esc 或 × 关闭 · 工作台升级尚未开放"),12,ColdSteelUI::TextTertiary,false,false,true));

    // 页脚带（HeaderTint，打铁同款）：状态行＋居中批量步进＋整宽主操作，固定底部不随内容滚动。
    FooterBand=WidgetTree->ConstructWidget<UBorder>();FooterBand->SetBrushColor(ColdSteelUI::HeaderTint);
    Stack->AddChildToVerticalBox(FooterBand);
    auto* Foot=WidgetTree->ConstructWidget<UVerticalBox>();FooterBand->SetContent(Foot);
    StatusLine=Text(TEXT(""),14,ColdSteelUI::TextSecondary,false,false,true);
    Space(Foot->AddChildToVerticalBox(StatusLine),FMargin(0,0,0,8));
    StatusLine->SetVisibility(ESlateVisibility::Collapsed);
    CraftHint=Text(TEXT("选择配方后直接制作"),12,ColdSteelUI::TextSecondary,false,false,true);
    Space(Foot->AddChildToVerticalBox(CraftHint),FMargin(0,0,0,8));
    BatchRow=WidgetTree->ConstructWidget<UHorizontalBox>();
    BatchRowSlot=Foot->AddChildToVerticalBox(BatchRow);
    BatchRowSlot->SetPadding(FMargin(0,0,0,8/Scale));
    BatchRowSlot->SetHorizontalAlignment(HAlign_Center);
    auto Small=[&](const FString& Caption)->UButton*
    {
        UTextBlock* Label=nullptr;auto* B=Button(Caption,Label);
        auto* SZ=WidgetTree->ConstructWidget<USizeBox>();SZ->SetWidthOverride(ColdSteelUI::ActionHeight/Scale);ButtonSizes.Add(SZ);
        SZ->SetContent(B);
        BatchRow->AddChildToHorizontalBox(SZ)->SetVerticalAlignment(VAlign_Center);
        return B;
    };
    BatchMinus=Small(TEXT("−"));BatchMinus->OnClicked.AddDynamic(this,&ThisClass::HandleBatchMinus);
    BatchText=Text(TEXT("1 份"),14,ColdSteelUI::TextPrimary,true);
    auto* BatchTextSlot=BatchRow->AddChildToHorizontalBox(BatchText);
    BatchTextSlot->SetPadding(FMargin(8/Scale,0,8/Scale,0));
    BatchTextSlot->SetHorizontalAlignment(HAlign_Center);BatchTextSlot->SetVerticalAlignment(VAlign_Center);
    BatchPlus=Small(TEXT("+"));BatchPlus->OnClicked.AddDynamic(this,&ThisClass::HandleBatchPlus);
    BatchRow->SetVisibility(ESlateVisibility::Collapsed);   // 有工作台上下文且目录非空时由 RefreshJob 打开
    StartSize=WidgetTree->ConstructWidget<USizeBox>();StartSize->SetHeightOverride(ColdSteelUI::ActionHeight/Scale);
    Foot->AddChildToVerticalBox(StartSize);
    UTextBlock* StartLabel=nullptr;StartButton=Button(TEXT("直接制作"),StartLabel);StartSize->SetContent(StartButton);
    StartButton->SetIsEnabled(false);
    StartButton->OnClicked.AddDynamic(this,&ThisClass::HandleCraft);

    // —— 左缘「升级」页签（冶炼 v12b 同款）：36×60 方片，竖排两字逐行居中；无描边并入主体，
    //    颜色跟随所贴主体（收起=制作栏 GlassTint，展开=升级栏 Content），只圆左两角 8px；
    //    收起态右缘压面板左缘缝 1px，展开态随弹层左缘推到最左、文案换"收回"（点击＝关闭）。——
    UpgradeTab=WidgetTree->ConstructWidget<UBorder>();
    UpgradeTab->SetPadding(FMargin(0));   // v12：无描边并入主体，不再需要卡片内衬
    UpgradeTabBtn=WidgetTree->ConstructWidget<UButton>();
    UpgradeTabText=Text(TEXT("升\n级"),14,ColdSteelUI::TextPrimary,false,true);
    UpgradeTabText->SetJustification(ETextJustify::Center);   // 块内每行默认左对齐——居中修正（冶炼 v11c 根因）
    UpgradeTabText->SetLineHeightPercentage(.88f);   // 收紧两字行距，墨迹块更接近方片几何中心
    UpgradeTabBtn->SetContent(UpgradeTabText);
    // v12：不进 StyledButtons（共享样式带描边），外观由 ApplyUpgradeTabVisual 统一给无描边样式。
    UpgradeTabBtn->OnClicked.AddDynamic(this,&ThisClass::HandleUpgradeToggled);   // 收回态点击＝关闭升级栏（互斥翻转）
    UpgradeTab->SetContent(UpgradeTabBtn);
    ApplyUpgradeTabVisual();
    UpgradeTabSlot=RootCanvas->AddChildToCanvas(UpgradeTab);
    UpgradeTabSlot->SetAnchors(FAnchors(0,.5f));UpgradeTabSlot->SetAlignment(FVector2D(0,.5f));
    UpgradeTabSlot->SetSize(FVector2D(36/Scale,60/Scale));
    UpgradeTabSlot->SetPosition(FVector2D(8/Scale,0.f));
    UpgradeTabSlot->SetZOrder(1);
    UpgradeTab->SetVisibility(ESlateVisibility::Collapsed);   // 有工作台上下文时由 SetWorkbench 打开

    // —— 升级弹层（冶炼 v9/v10 同构）：与面板同尺寸的独立页面，右缘钉在面板左缘那条缝上；
    //    横向缩放 0→1 向左展开/收回（枢纽右中；不从磨砂玻璃背后滑出——半透明会漏穿帮）。
    //    版面＝头部底色条（20px 标题＋标准 ×）＋三页签卡列（整行可点）＋下方详情带＋垫底说明行。——
    UpgradeFlyout=WidgetTree->ConstructWidget<UBorder>();
    UpgradeFlyout->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::Content,10/Scale,GunsmithUI::Edge,1/Scale));
    UpgradeFlyout->SetPadding(FMargin(0));   // 版面结构照抄面板：头部底色＋内容各自带内边距
    UpgradeFlySlot=RootCanvas->AddChildToCanvas(UpgradeFlyout);
    UpgradeFlySlot->SetAnchors(FAnchors(0,0,1,1));UpgradeFlySlot->SetAlignment(FVector2D::ZeroVector);
    UpgradeFlySlot->SetOffsets(FMargin(8/Scale,0.f,0.f,0.f));
    UpgradeFlyout->SetRenderTransformPivot(FVector2D(1.f,.5f));
    auto* FlyStack=WidgetTree->ConstructWidget<UVerticalBox>();UpgradeFlyout->SetContent(FlyStack);
    FlyHeadSurf=WidgetTree->ConstructWidget<UBorder>();
    FlyHeadSurf->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::HeaderTint,ColdSteelUI::PanelRadius/Scale));
    FlyHeadSurf->SetPadding(FMargin(18/Scale,12/Scale));
    FlyStack->AddChildToVerticalBox(FlyHeadSurf);
    FlyHeadSize=WidgetTree->ConstructWidget<USizeBox>();FlyHeadSize->SetHeightOverride(36/Scale);FlyHeadSurf->SetContent(FlyHeadSize);
    auto* FlyHead=WidgetTree->ConstructWidget<UHorizontalBox>();FlyHeadSize->SetContent(FlyHead);
    if(auto* FTS=FlyHead->AddChildToHorizontalBox(Text(TEXT("工作台升级"),20,ColdSteelUI::TextPrimary,false,true)))
    {   FTS->SetSize(FSlateChildSize(ESlateSizeRule::Fill));FTS->SetVerticalAlignment(VAlign_Center);   }
    auto* FlyClose=Action(TEXT("×"));
    StyledButtons.Add(FlyClose);FlyClose->OnClicked.AddDynamic(this,&ThisClass::HandleUpgradeClose);
    if(auto* CS=FlyHead->AddChildToHorizontalBox(FlyClose))CS->SetVerticalAlignment(VAlign_Center);
    // 三页签（v10：整行可选，名称 14（选中 Medium）＋Lv 12；选中样式＝配方行同款 ButtonHover 底＋Accent 细边）
    auto* FlyBody=WidgetTree->ConstructWidget<UVerticalBox>();
    if(auto* BS=FlyStack->AddChildToVerticalBox(FlyBody))
    {   BS->SetSize(FSlateChildSize(ESlateSizeRule::Fill));BS->SetPadding(FMargin(12/Scale,10/Scale,12/Scale,0));   }
    for(int32 A=0;A<3;++A)
    {
        auto* Surf=WidgetTree->ConstructWidget<UBorder>();
        Surf->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::StatusCard,ColdSteelUI::CardRadius/Scale,ColdSteelUI::Border,1.f/Scale));
        Surf->SetPadding(FMargin(12/Scale,8/Scale));
        if(auto* KS=FlyBody->AddChildToVerticalBox(Surf))KS->SetPadding(FMargin(0,0,0,6/Scale));
        auto* Tab=WidgetTree->ConstructWidget<UButton>();
        Tab->SetStyle(FButtonStyle()
            .SetNormal(ColdSteelUI::RoundedBrush(FLinearColor::Transparent,0,FLinearColor::Transparent,0))
            .SetHovered(ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonHover,ColdSteelUI::CardRadius/Scale,FLinearColor::Transparent,0))
            .SetPressed(ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonPressed,ColdSteelUI::CardRadius/Scale,FLinearColor::Transparent,0)));
        Surf->SetContent(Tab);
        auto* Content=WidgetTree->ConstructWidget<UHorizontalBox>();Tab->SetContent(Content);
        if(auto* CBS=Cast<UButtonSlot>(Content->Slot))   // UButtonSlot 默认居中收缩（配方行 2026-09-23 的坑）：铺满才撑得开 Fill
            {CBS->SetPadding(FMargin(0));CBS->SetHorizontalAlignment(HAlign_Fill);CBS->SetVerticalAlignment(VAlign_Center);}
        UpgTabs.Add(Tab);UpgTabSurfs.Add(Surf);
        auto* Name=Text(WorkbenchAxisNames[A],14,ColdSteelUI::TextPrimary,false,A==UpgSel);
        if(auto* NS=Content->AddChildToHorizontalBox(Name))
        {   NS->SetSize(FSlateChildSize(ESlateSizeRule::Fill));NS->SetVerticalAlignment(VAlign_Center);   }
        UpgTabNames.Add(Name);
        auto* Lv=Text(TEXT("Lv.—"),12,ColdSteelUI::TextSecondary,false,true);   // 占位读数：升级轴上线后＝"Lv.N / Max"
        Content->AddChildToHorizontalBox(Lv)->SetVerticalAlignment(VAlign_Center);
        UpgTabLv.Add(Lv);
        auto* Proxy=NewObject<UColdSteelWorkbenchRowProxy>(this);   // 点击代理（v10c：专用数组常驻引用，与行缓存分家）
        Proxy->Panel=this;Proxy->Axis=A;
        Tab->OnClicked.AddDynamic(Proxy,&UColdSteelWorkbenchRowProxy::AxisClicked);
        UpgProxies.Add(Proxy);
    }
    // —— 详情带（v10）：字号吃正式规则 §4 四档——分区标题 16／正文 14／数值 16 NumberFont／辅助 12。——
    FlyDetail=WidgetTree->ConstructWidget<UBorder>();
    FlyDetail->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::StatusCard,ColdSteelUI::CardRadius/Scale,ColdSteelUI::Border,1.f/Scale));
    FlyDetail->SetPadding(FMargin(12/Scale));
    if(auto* DS=FlyStack->AddChildToVerticalBox(FlyDetail))DS->SetPadding(FMargin(12/Scale,2/Scale,12/Scale,0));
    auto* DCol=WidgetTree->ConstructWidget<UVerticalBox>();FlyDetail->SetContent(DCol);
    auto* DHead=WidgetTree->ConstructWidget<UHorizontalBox>();DCol->AddChildToVerticalBox(DHead);
    FlyDetailName=Text(WorkbenchAxisNames[0],16,ColdSteelUI::TextPrimary,false,true);
    DHead->AddChildToHorizontalBox(FlyDetailName)->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    FlyDetailLv=Text(TEXT("Lv.—"),12,ColdSteelUI::TextSecondary,false,true);
    DHead->AddChildToHorizontalBox(FlyDetailLv)->SetVerticalAlignment(VAlign_Center);
    FlyRuleSize=WidgetTree->ConstructWidget<USizeBox>();FlyRuleSize->SetHeightOverride(1.f/Scale);
    if(auto* RS=DCol->AddChildToVerticalBox(FlyRuleSize))RS->SetPadding(FMargin(0,8/Scale,0,6/Scale));
    auto* Rule=WidgetTree->ConstructWidget<UImage>();
    Rule->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::Border,0.f));FlyRuleSize->SetContent(Rule);   // §4 细线分区
    DCol->AddChildToVerticalBox(Text(TEXT("升级效果"),12,ColdSteelUI::TextTertiary));
    FlyFx=Text(TEXT("效果数值后续设计"),16,ColdSteelUI::TextSecondary,true,false);   // 上线后＝"30 分钟 → 40 分钟"类
    if(auto* XS=DCol->AddChildToVerticalBox(FlyFx))XS->SetPadding(FMargin(0,2/Scale,0,8/Scale));
    DCol->AddChildToVerticalBox(Text(TEXT("所需材料"),12,ColdSteelUI::TextTertiary));
    FlyMatRow=WidgetTree->ConstructWidget<UHorizontalBox>();
    if(auto* MS=DCol->AddChildToVerticalBox(FlyMatRow))MS->SetPadding(FMargin(0,2/Scale,0,0));
    FlyMatIconSize=WidgetTree->ConstructWidget<USizeBox>();
    FlyMatIconSize->SetWidthOverride(28/Scale);FlyMatIconSize->SetHeightOverride(28/Scale);
    FlyMatIcon=WidgetTree->ConstructWidget<UImage>();FlyMatIconSize->SetContent(FlyMatIcon);
    FlyMatIcon->SetVisibility(ESlateVisibility::Collapsed);
    FlyMatRow->AddChildToHorizontalBox(FlyMatIconSize)->SetVerticalAlignment(VAlign_Center);
    if(auto* NS=FlyMatRow->AddChildToHorizontalBox(Text(TEXT("材料"),14,ColdSteelUI::TextPrimary)))
        NS->SetPadding(FMargin(8/Scale,0,0,0));
    FlyMatValue=Text(TEXT("×—"),16,ColdSteelUI::TextPrimary,true,false);
    if(auto* VS=FlyMatRow->AddChildToHorizontalBox(FlyMatValue))
    {   VS->SetPadding(FMargin(8/Scale,0,0,0));VS->SetVerticalAlignment(VAlign_Center);   }
    FlyMatOwned=Text(TEXT(""),12,ColdSteelUI::TextSecondary,false,false,true);
    if(auto* OS=FlyMatRow->AddChildToHorizontalBox(FlyMatOwned))
    {   OS->SetSize(FSlateChildSize(ESlateSizeRule::Fill));OS->SetPadding(FMargin(8/Scale,0,0,0));OS->SetVerticalAlignment(VAlign_Center);   }
    FlyMatRow->SetVisibility(ESlateVisibility::Collapsed);   // 占位期材料行不显——上线后随选中轴数据开
    FlyNoMat=Text(TEXT("升级内容与消耗后续设计"),12,ColdSteelUI::TextTertiary);
    DCol->AddChildToVerticalBox(FlyNoMat);
    FlyBtnSize=WidgetTree->ConstructWidget<USizeBox>();FlyBtnSize->SetHeightOverride(ColdSteelUI::ActionHeight/Scale);
    if(auto* SS=DCol->AddChildToVerticalBox(FlyBtnSize))SS->SetPadding(FMargin(0,10/Scale,0,0));
    FlyBtn=Action(TEXT("升级"));FlyBtn->OnClicked.AddDynamic(this,&ThisClass::HandleUpgradeClicked);
    FlyBtnText=Cast<UTextBlock>(FlyBtn->GetContent());
    FlyBtn->SetIsEnabled(false);   // 工作台升级事务后续设计
    FlyBtnSize->SetContent(FlyBtn);
    if(auto* NS=FlyStack->AddChildToVerticalBox(Text(TEXT("升级只对这台工作台生效 · 升级轴与数值后续设计"),12,ColdSteelUI::TextTertiary,false,false,true)))
        NS->SetPadding(FMargin(12/Scale,0,12/Scale,10/Scale));   // Body 占 Fill，说明行自然垫底＝面板页脚同一位置语义
    UpgradeFlyout->SetVisibility(ESlateVisibility::Collapsed);
    UpdateScale();
}

void UColdSteelWorkbenchWidget::UpdateScale()
{
    Scale=ColdSteelUI::PixelScale(this);
    ShellOutline->SetBrush(ColdSteelUI::RoundedBrush(FLinearColor::Transparent,ColdSteelUI::PanelRadius/Scale,ColdSteelUI::Border,1/Scale));
    ShellOutline->SetPadding(1/Scale);
    Shell->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::GlassTint,ColdSteelUI::PanelRadius/Scale));
    HeaderSurface->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::HeaderTint,ColdSteelUI::PanelRadius/Scale));
    Blur->SetCornerRadius(FVector4(10,10,10,10)/Scale);
    Blur->SetLowQualityFallbackBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::GlassFallback,ColdSteelUI::PanelRadius/Scale));
    HeaderSurface->SetPadding(FMargin(18/Scale,12/Scale));HeaderSize->SetHeightOverride(36/Scale);
    CloseSize->SetWidthOverride(ColdSteelUI::ActionHeight/Scale);
    StartSize->SetHeightOverride(ColdSteelUI::ActionHeight/Scale);
    // 批量步进行（2026-09-25）：居中归属槽位、读数间隔与钮尺寸随 Scale 重算——与构建期同一口径。
    if(BatchRowSlot){BatchRowSlot->SetPadding(FMargin(0,0,0,8/Scale));BatchRowSlot->SetHorizontalAlignment(HAlign_Center);}
    if(auto* TS=Cast<UHorizontalBoxSlot>(BatchText->Slot))TS->SetPadding(FMargin(8/Scale,0,8/Scale,0));
    for(auto* B:{BatchMinus.Get(),BatchPlus.Get()})if(B)if(auto* SZ=Cast<USizeBox>(B->GetParent()))
        {SZ->SetWidthOverride(ColdSteelUI::ActionHeight/Scale);SZ->SetHeightOverride(ColdSteelUI::ActionHeight/Scale);}
    if(auto* TS=Cast<UCanvasPanelSlot>(UpgradeTabSlot))TS->SetSize(FVector2D(36/Scale,60/Scale));
    ApplyScreenLayout();   // Shell/页签/弹层按新 Scale 重排（坐标源＝主题层推送的屏幕像素）
    ApplyUpgradeTabVisual();   // v12：hover/pressed 圆角随 Scale 重建
    UpgradeFlyout->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::Content,10/Scale,GunsmithUI::Edge,1/Scale));
    UpgradeFlyout->SetPadding(FMargin(0));
    if(FlyHeadSurf)
    {   FlyHeadSurf->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::HeaderTint,ColdSteelUI::PanelRadius/Scale));
        FlyHeadSurf->SetPadding(FMargin(18/Scale,12/Scale));
        if(FlyHeadSize)FlyHeadSize->SetHeightOverride(36/Scale);   }
    for(int32 A=0;A<UpgTabSurfs.Num();++A)
    {   if(UpgTabSurfs[A])UpgTabSurfs[A]->SetPadding(FMargin(12/Scale,8/Scale));   // 卡面刷（含选中态）由 RefreshUpgrade 统一走
        if(UpgTabs.IsValidIndex(A)&&UpgTabs[A])UpgTabs[A]->SetStyle(FButtonStyle()
            .SetNormal(ColdSteelUI::RoundedBrush(FLinearColor::Transparent,0,FLinearColor::Transparent,0))
            .SetHovered(ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonHover,ColdSteelUI::CardRadius/Scale,FLinearColor::Transparent,0))
            .SetPressed(ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonPressed,ColdSteelUI::CardRadius/Scale,FLinearColor::Transparent,0)));   }
    if(FlyDetail)
    {   FlyDetail->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::StatusCard,ColdSteelUI::CardRadius/Scale,ColdSteelUI::Border,1.f/Scale));
        FlyDetail->SetPadding(FMargin(12/Scale));   }
    if(FlyRuleSize)FlyRuleSize->SetHeightOverride(1.f/Scale);
    if(FlyMatIconSize){FlyMatIconSize->SetWidthOverride(28/Scale);FlyMatIconSize->SetHeightOverride(28/Scale);}
    if(FlyBtnSize)FlyBtnSize->SetHeightOverride(ColdSteelUI::ActionHeight/Scale);
    // —— 打铁/装配同款重排：滚动条、卡面 12px 内沿、行距、双列缝、三列/参数表内距。——
    Scroll->SetScrollbarThickness(FVector2D(6/Scale,6/Scale));Scroll->SetScrollbarPadding(FMargin(4/Scale,0,0,0));
    PreviewScroll->SetScrollbarThickness(FVector2D(6/Scale,6/Scale));PreviewScroll->SetScrollbarPadding(FMargin(4/Scale,0,0,0));
    Body->SetPadding(12/Scale);
    FooterBand->SetPadding(12/Scale);
    for(const auto& Weak:Buttons)if(auto* B=Weak.Get())
    {   B->SetStyle(ColdSteelUI::ButtonStyle(Scale));
        if(auto* Content=B->GetContent())if(auto* ContentSlot=Cast<UButtonSlot>(Content->Slot))ContentSlot->SetPadding(FMargin(12/Scale,4/Scale));   }
    for(const auto& W:ButtonSizes)if(auto* S=W.Get())S->SetHeightOverride(ColdSteelUI::ActionHeight/Scale);
    for(const auto& C:Cards)if(auto* Border=C.Get())
    {   Border->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::StatusCard,ColdSteelUI::CardRadius/Scale,ColdSteelUI::Border,1/Scale));
        Border->SetPadding(12/Scale);   }
    for(const auto& Row:RowSpacings)if(auto* RowSlot=Row.Slot.Get())RowSlot->SetPadding(Row.Padding*(1.f/Scale));
    UpdatePreviewLayout();
    for(const auto& MaterialCell:MaterialCellSlots)if(auto* CellSlot=MaterialCell.Get())
        CellSlot->SetPadding(FMargin(CellSlot->GetColumn()==0?0.f:12.f/Scale,4.f/Scale,0,4.f/Scale));
    for(const auto& PreviewCell:PreviewCellSlots)if(auto* S=PreviewCell.Get())
        S->SetPadding(FMargin(S->GetColumn()==0?0.f:12.f/Scale,6.f/Scale,0,6.f/Scale));
    for(const auto& L:Labels)if(auto* Label=L.Widget.Get())
        Label->SetFont(L.Numeric?GunsmithUI::NumberFont(L.Pixels/Scale,L.Medium):GunsmithUI::TextFont(L.Pixels/Scale,L.Medium));
    for(const auto& Option:RecipeOptionWidgets)if(auto* Widget=Option.Get())Widget->SetPixelScale(Scale);
    auto ComboStyle=RecipeChoice->GetWidgetStyle();auto ComboButton=ComboStyle.ComboButtonStyle;
    ComboButton.SetButtonStyle(ColdSteelUI::ButtonStyle(Scale));
    ComboButton.SetMenuBorderBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::Gray(25,252),ColdSteelUI::CardRadius/Scale,ColdSteelUI::Border,1/Scale));
    ComboButton.DownArrowImage.ImageSize=FVector2D(8/Scale,8/Scale);
    ComboButton.SetDownArrowPadding(FMargin(4/Scale,0,0,0));ComboButton.SetShadowOffset(FVector2D::ZeroVector);
    ComboStyle.SetComboButtonStyle(ComboButton);RecipeChoice->SetWidgetStyle(ComboStyle);
    RecipeChoice->SetContentPadding(FMargin(22/Scale,4/Scale,10/Scale,4/Scale));RecipeChoice->SetMaxListHeight(240/Scale);
    auto ItemStyle=RecipeChoice->GetItemStyle();
    ItemStyle.SetEvenRowBackgroundBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::Content,ColdSteelUI::ButtonRadius/Scale));
    ItemStyle.SetOddRowBackgroundBrush(ItemStyle.EvenRowBackgroundBrush);
    ItemStyle.SetEvenRowBackgroundHoveredBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonHover,ColdSteelUI::ButtonRadius/Scale));
    ItemStyle.SetOddRowBackgroundHoveredBrush(ItemStyle.EvenRowBackgroundHoveredBrush);
    ItemStyle.SetActiveBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonHover,ColdSteelUI::ButtonRadius/Scale,ColdSteelUI::Accent,1/Scale));
    ItemStyle.SetInactiveBrush(ItemStyle.ActiveBrush);RecipeChoice->SetItemStyle(ItemStyle);
    const FButtonStyle Style=ColdSteelUI::ButtonStyle(Scale);
    for(const auto& Weak:StyledButtons)if(auto* B=Weak.Get())
    {
        B->SetStyle(Style);
        if(auto* Content=B->GetContent())if(auto* ContentSlot=Cast<UButtonSlot>(Content->Slot))ContentSlot->SetPadding(FMargin(10/Scale,8/Scale));
    }
    RefreshJob();
    RefreshUpgrade();   // 页签选中卡面/字号按新 Scale 复原（冶炼 UpdateScale 末尾同构）
}

void UColdSteelWorkbenchWidget::ApplyUpgradeTabVisual()
{
    if(!UpgradeTab)return;
    // v12（冶炼 §7.23 同款，用户"取消边界、做成主体一部分，保留功能"）：无描边填充，颜色跟随所贴主体——
    // 收起＝制作栏 GlassTint，展开＝升级栏 Content（ZOrder 1 盖在弹层缘上，同色即无缝）。
    // v12b：只圆左两角 8px、右两角直角——右侧是接缝，圆接缝侧会在面板/弹层边线上咬出背景缺口。
    const FLinearColor Fill=bTabVisualOpen?ColdSteelUI::Content:ColdSteelUI::GlassTint;
    const float R=8.f/Scale;
    UpgradeTab->SetBrush(ColdSteelUI::RoundedBrushCorners(Fill,FVector4(R,0.f,0.f,R)));
    if(UpgradeTabBtn)
    {   FButtonStyle S;   // 钮面透明（卡片感来源就是它这层描边底），只留 hover/pressed 的轻反馈
        S.SetNormal(ColdSteelUI::RoundedBrush(FLinearColor::Transparent,0.f,FLinearColor::Transparent,0.f));
        S.SetHovered(ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonHover,6.f/Scale,FLinearColor::Transparent,0.f));
        S.SetPressed(ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonPressed,6.f/Scale,FLinearColor::Transparent,0.f));
        S.SetDisabled(ColdSteelUI::RoundedBrush(FLinearColor::Transparent,0.f,FLinearColor::Transparent,0.f));
        UpgradeTabBtn->SetStyle(S);   }
}

void UColdSteelWorkbenchWidget::ApplyScreenLayout()
{
    if(PanelScreenPx<0.f||Scale<=0.f)return;
    // 槽位原点＝屏幕 x=0（主题层把 widget 扩为全宽命中区），偏移/Scale 即屏幕像素，无需任何几何反推。
    const float P=PanelScreenPx/Scale;
    if(ShellSlot)ShellSlot->SetOffsets(FMargin(P,0.f,0.f,0.f));
    if(UpgradeTabSlot)LayoutUpgradeTab();   // v11：摆位收敛到一个函数（收起贴缝/展开随弹层，见下）
    if(UpgradeFlySlot)
    {   // 弹层＝面板的左右镜像：同宽（LayoutWidth）、同高（画布全高）、右缘＝面板左缘零缝。
        // 纯推送值，不依赖缓存几何（冶炼 §7.12 教训：首帧未测量回落全画布宽＝大小完全错误）。
        const float W=FMath::Max(1.f,LayoutWidth)/Scale;
        const float L=FMath::Max(8.f/Scale,P-W);
        UpgradeFlySlot->SetOffsets(FMargin(L,0.f,W,0.f));   // 右留白＝W：rect 右缘＝P 钉在缝上
    }
}

void UColdSteelWorkbenchWidget::LayoutUpgradeTab()
{
    if(!UpgradeTabSlot||PanelScreenPx<0.f||Scale<=0.f)return;
    const float P=PanelScreenPx/Scale;                      // 面板左缘（单位系）
    const float W=FMath::Max(1.f,LayoutWidth)/Scale;
    const float L=FMath::Max(8.f/Scale,P-W);                // 弹层全开左缘（与 ApplyScreenLayout 同式）
    const float TabW=36.f/Scale;
    // v12（冶炼 §7.23 同款）：方片已无自身描边（并入主体），右缘压线 1px 只为消掉抗锯齿发丝缝。
    // 展开态跟随：EaseSmooth(FlyMotion) 与弹层 RenderScale 同曲线同拍，方片右缘钉在弹层左缘上推到最左；
    // 屏幕边钳制：方片贴到 x=0 盖在弹层角上（ZOrder 1，可点收回）。
    const float X=FMath::Max(0.f,FMath::Lerp(P-TabW,L-TabW,ColdSteelUI::EaseSmooth(FlyMotion))+1.f/Scale);
    UpgradeTabSlot->SetPosition(FVector2D(X,0.f));
}

void UColdSteelWorkbenchWidget::SetWorkbench(AVoxelBuildWorld* InWorld,FIntVector InCell)
{
    World=InWorld;Cell=InCell;
    bInputReady=false;bDataDirty=true;bPreviewDirty=true;PreviewRecipe.Reset();
    SelectedRecipe=NAME_None;Batch=1;   // 换台清选择与批量（逐台上下文，别把上一台的选中带过来）
    SetStatus(FString());
    bUpgradeOpen=false;   // 换台上下文时收起升级弹层（升级数据是逐台的，别把上一台的弹层带过来）
    UpgSel=0;             // 页签选择同样归零：新工作台从默认轴看起（冶炼换炉同款）
    FlyMotion=0.f;        // 瞬关不播收回动画（防残影随面板滑入，冶炼同款处理）
    if(UpgradeFlyout){UpgradeFlyout->SetVisibility(ESlateVisibility::Collapsed);UpgradeFlyout->SetRenderScale(FVector2D(1.f,1.f));}
    if(UpgradeTab)UpgradeTab->SetVisibility(ESlateVisibility::Visible);
    RefreshJob();RefreshUpgrade();
}

void UColdSteelWorkbenchWidget::SetLayoutWidth(float PixelsX)
{
    if(FMath::IsNearlyEqual(LayoutWidth,PixelsX,.5f))return;
    LayoutWidth=PixelsX;ApplyScreenLayout();UpdatePreviewLayout();
}

void UColdSteelWorkbenchWidget::SetPanelScreenX(float Px)
{
    if(FMath::IsNearlyEqual(PanelScreenPx,Px,.5f))return;
    PanelScreenPx=Px;ApplyScreenLayout();
}

void UColdSteelWorkbenchWidget::NativeConstruct()
{
    Super::NativeConstruct();
    if(Model&&!ChangedHandle.IsValid())ChangedHandle=Model->OnChanged.AddUObject(this,&ThisClass::RefreshDataChanged);
    RefreshDataChanged();
    RefreshJob();
}

void UColdSteelWorkbenchWidget::NativeDestruct()
{
    if(Model)Model->OnChanged.Remove(ChangedHandle);
    ChangedHandle.Reset();Super::NativeDestruct();
}

void UColdSteelWorkbenchWidget::NativeTick(const FGeometry& MyGeometry,float InDeltaTime)
{
    Super::NativeTick(MyGeometry,InDeltaTime);
    if(!FMath::IsNearlyEqual(Scale,ColdSteelUI::PixelScale(this),.001f)){UpdateScale();return;}
    if(GetVisibility()==ESlateVisibility::Collapsed)return;
    const float Height=bPreviewStacked
        ?FMath::Clamp(float(MyGeometry.GetLocalSize().Y)*Scale-430.f,360.f,480.f)/Scale
        :FMath::Clamp(float(MyGeometry.GetLocalSize().Y)*Scale-520.f,220.f,420.f)/Scale;
    if(!FMath::IsNearlyEqual(Height,BoardHeight,.5f)){BoardHeight=Height;BoardSize->SetHeightOverride(Height);}
    // 升级弹层动画（冶炼 §7.12 同款）：右缘钉死在面板左缘那条缝上（枢纽右中），
    // 横向缩放 0→1 向左展开/1→0 向右收回，4.0/s＋EaseSmooth。
    FlyMotion=FMath::FInterpConstantTo(FlyMotion,bUpgradeOpen?1.f:0.f,InDeltaTime,4.0f);
    if(UpgradeFlyout)
    {
        UpgradeFlyout->SetVisibility(FlyMotion>KINDA_SMALL_NUMBER?ESlateVisibility::Visible:ESlateVisibility::Collapsed);
        UpgradeFlyout->SetRenderScale(FVector2D(FMath::Max(ColdSteelUI::EaseSmooth(FlyMotion),.02f),1.f));
    }
    LayoutUpgradeTab();   // v11：方片逐帧跟弹层左缘（与 RenderScale 同曲线）；静止时仅一次属性写，开销可忽略。
    RefreshAccum+=InDeltaTime;
    if(RefreshAccum<.1f)return;   // 数据侧 0.1s 节流、动画每帧——与冶炼"刷新与动画解耦"同一构建（§7.13）。
    RefreshAccum=0.f;
    RefreshJob();
}

void UColdSteelWorkbenchWidget::RefreshDataChanged()
{bDataDirty=true;bPreviewDirty=true;}

void UColdSteelWorkbenchWidget::SetInputReady(bool bReady)
{
    if(bInputReady==bReady)return;
    bInputReady=bReady;
    if(bReady){bDataDirty=true;RefreshJob();}else RefreshActions();
}

FReply UColdSteelWorkbenchWidget::NativeOnMouseButtonDown(const FGeometry& Geometry,const FPointerEvent& Event)
{
    // The root canvas includes the empty area to the left of the panel for the upgrade flyout.
    const FVector2D Position=Event.GetScreenSpacePosition();
    for(UWidget* Widget:{static_cast<UWidget*>(Shell.Get()),static_cast<UWidget*>(UpgradeTab.Get()),static_cast<UWidget*>(UpgradeFlyout.Get())})
        if(Widget&&Widget->IsVisible()&&Widget->GetCachedGeometry().IsUnderLocation(Position))return FReply::Handled();
    return Super::NativeOnMouseButtonDown(Geometry,Event);
}

void UColdSteelWorkbenchWidget::UpdatePreviewLayout()
{
    if(!PreviewLayout)return;
    bPreviewStacked=LayoutWidth>0&&LayoutWidth<560.f;
    PreviewLayout->SetColumnFill(1,bPreviewStacked?0.f:1.f);
    PreviewLayout->SetRowFill(0,bPreviewStacked?0.f:1.f);PreviewLayout->SetRowFill(1,bPreviewStacked?1.f:0.f);
    PreviewDetailsSlot->SetRow(bPreviewStacked?1:0);PreviewDetailsSlot->SetColumn(bPreviewStacked?0:1);
    PreviewIconSlot->SetPadding(bPreviewStacked?FMargin(0,0,0,8/Scale):FMargin(0,0,4/Scale,0));
    PreviewDetailsSlot->SetPadding(bPreviewStacked?FMargin(0):FMargin(4/Scale,0,0,0));
    if(bPreviewStacked)IconFrameSize->SetHeightOverride(140/Scale);else IconFrameSize->ClearHeightOverride();
}

void UColdSteelWorkbenchWidget::RefreshJob()
{
    if(!bDataDirty||!Crafting||!Model||!RecipeChoice)return;
    bDataDirty=false;
    const TArray<FColdSteelCraftingRecipe>& Catalog=Crafting->Catalog();
    // 选中同步：换台/无选择时默认第一项（打铁同款"选中即可点"手感）。
    int32 Index=INDEX_NONE;
    for(int32 I=0;I<Catalog.Num();++I)if(Catalog[I].Id==SelectedRecipe){Index=I;break;}
    if(Index==INDEX_NONE&&!Catalog.IsEmpty()){SelectedRecipe=Catalog[0].Id;Index=0;}
    if(RecipeChoice->GetSelectedIndex()!=Index)RecipeChoice->SetSelectedIndex(Index);
    const bool bCtx=World.IsValid()&&World->HasPrefabAt(Cell);
    const FColdSteelCraftingRecipe* Sel=Index!=INDEX_NONE?&Catalog[Index]:nullptr;
    // Clamp first: the material rows, summary, quote and eventual submission share this batch.
    MaxBatch=Sel?Crafting->MaxCraftable(Model,*Sel):0;
    Batch=FMath::Clamp<int64>(Batch,1,FMath::Max<int64>(1,MaxBatch));
    RecipeTitle->SetText(FText::FromString(Sel?FString::Printf(TEXT("%d / %d · %s"),Index+1,Catalog.Num(),*DefinitionName(Sel->Output)):TEXT("暂无制作配方")));
    RecipeTitle->SetAutoWrapText(true);
    // —— 材料三列表（打铁同款）：需求＝单份×批量；持有不足标红并报差额。——
    EnsureMaterialRows(Sel?Sel->Inputs.Num():0);
    for(int32 I=0;I<MaterialRows.Num();++I)
    {
        FMaterialRow& Row=MaterialRows[I];
        const bool bHasInput=Sel&&I<Sel->Inputs.Num();
        const auto RowVisibility=bHasInput?ESlateVisibility::HitTestInvisible:ESlateVisibility::Collapsed;
        Row.Name->SetVisibility(RowVisibility);Row.Amount->SetVisibility(RowVisibility);Row.State->SetVisibility(RowVisibility);
        if(!bHasInput)continue;
        const auto& Input=Sel->Inputs[I];
        const int64 Owned=Model->CountMaterial(Input.Item),Required=Input.Count*FMath::Max<int64>(1,Batch);
        const bool bEnough=Owned>=Required;
        auto Set=[&](UTextBlock* Widget,const FString& Value){if(Widget&&Widget->GetText().ToString()!=Value)Widget->SetText(FText::FromString(Value));};
        Set(Row.Name.Get(),DefinitionName(Input.Item));
        Set(Row.Owned.Get(),FString::Printf(TEXT("%lld"),Owned));
        Set(Row.Required.Get(),FString::Printf(TEXT("%lld"),Required));
        Set(Row.State.Get(),bEnough?TEXT("充足"):FString::Printf(TEXT("缺 %lld"),Required-Owned));
        Row.Owned->SetColorAndOpacity(bEnough?ColdSteelUI::Success:ColdSteelUI::Danger);
        Row.State->SetColorAndOpacity(bEnough?ColdSteelUI::TextSecondary:ColdSteelUI::Danger);
    }
    if(Materials)
    {
        const FString Want=Sel&&Batch>1?FString::Printf(TEXT("所需材料 · 按批量 ×%lld"),Batch):FString(TEXT("所需材料"));
        if(Materials->GetText().ToString()!=Want)Materials->SetText(FText::FromString(Want));
    }
    // —— 批量步进与主操作（提交走 UColdSteelCraftingSystem 单事务）。——
    BatchRow->SetVisibility(Sel?ESlateVisibility::Visible:ESlateVisibility::Collapsed);
    if(BatchText)
    {
        const FString Want=FString::Printf(TEXT("%lld 份"),Batch);
        if(BatchText->GetText().ToString()!=Want)BatchText->SetText(FText::FromString(Want));
    }
    if(auto* Cap=Cast<UTextBlock>(StartButton->GetContent()))
        Cap->SetText(FText::FromString(Batch>1?FString::Printf(TEXT("直接制作 · %lld 份"),Batch):TEXT("直接制作")));
    bCanCraft=false;CraftReason.Reset();
    if(!bCtx)CraftReason=TEXT("工作台不可用，请重新交互");
    else if(!Sel)CraftReason=TEXT("暂无制作配方");
    else bCanCraft=Crafting->CanCraft(*Sel,Batch,CraftReason);
    StartButton->SetToolTipText(FText::FromString(bCanCraft?FString::Printf(TEXT("消耗当前材料，制作 %s ×%lld 并放入背包"),*DefinitionName(Sel->Output),Sel->OutputCount*Batch):CraftReason));
    CraftHint->SetText(FText::FromString(bCanCraft?TEXT("材料与背包空间充足 · 点击后立即制作"):CraftReason));
    CraftHint->SetColorAndOpacity(bCanCraft?ColdSteelUI::TextSecondary:ColdSteelUI::Warning);
    // —— 状态卡：选中＝就绪/材料不足＋三段读数；未选＝空闲态。制作即时结算，无进度条。——
    if(Sel)
    {
        Stage->SetText(FText::FromString(bCanCraft?TEXT("准备就绪 · 直接制作"):MaxBatch==0?TEXT("材料不足"):TEXT("暂不可制作")));
        Stage->SetColorAndOpacity(bCanCraft?ColdSteelUI::TextPrimary:ColdSteelUI::Warning);
        Stats->SetText(FText::AsNumber(MaxBatch));BatchStat->SetText(FText::AsNumber(Batch));OutputStat->SetText(FText::AsNumber(Sel->OutputCount*Batch));
        Stats->SetColorAndOpacity(MaxBatch>0?ColdSteelUI::TextPrimary:ColdSteelUI::Danger);
    }
    else
    {
        Stage->SetText(FText::FromString(TEXT("工作台空闲")));
        Stage->SetColorAndOpacity(ColdSteelUI::TextTertiary);
        Stats->SetText(FText::FromString(TEXT("0")));BatchStat->SetText(FText::FromString(TEXT("—")));OutputStat->SetText(FText::FromString(TEXT("—")));
    }
    RefreshPreview(Sel);RefreshActions();
}

void UColdSteelWorkbenchWidget::RefreshActions()
{
    const bool Ready=bInputReady&&World.IsValid()&&HUD&&HUD->IsWorkbenchOpen();
    if(RecipeChoice)RecipeChoice->SetIsEnabled(Ready&&Crafting&&Crafting->Catalog().Num()>1);
    if(StartButton)StartButton->SetIsEnabled(Ready&&bCanCraft);
    if(BatchMinus)BatchMinus->SetIsEnabled(Ready&&Batch>1);
    if(BatchPlus)BatchPlus->SetIsEnabled(Ready&&Batch<MaxBatch);
    if(UpgradeTabBtn)UpgradeTabBtn->SetIsEnabled(Ready);
}

void UColdSteelWorkbenchWidget::RefreshPreview(const FColdSteelCraftingRecipe* Recipe)
{
    const FString Key=Recipe?Recipe->Id.ToString():FString();
    if(Key==PreviewRecipe&&!bPreviewDirty)return;
    const bool bRecipeChanged=Key!=PreviewRecipe;
    PreviewRecipe=Key;bPreviewDirty=false;
    if(bRecipeChanged)PreviewScroll->ScrollToStart();
    auto Set=[](UTextBlock* Widget,const FString& Value){if(Widget&&Widget->GetText().ToString()!=Value)Widget->SetText(FText::FromString(Value));};
    if(!Recipe)
    {
        Set(PreviewName,TEXT("—"));Set(PreviewScope,FString());
        PreviewIcon->SetVisibility(ESlateVisibility::Collapsed);
        PreviewEmpty->SetText(FText::FromString(TEXT("暂无成品预览")));PreviewEmpty->SetVisibility(ESlateVisibility::HitTestInvisible);
        Set(PreviewStage,FString());
        for(const auto& Row:PreviewRows)
        {Row.Name->SetVisibility(ESlateVisibility::Collapsed);Row.Value->SetVisibility(ESlateVisibility::Collapsed);}
        return;
    }
    // 参数读浮窗摘要同口径：物品提示、本预览与实战读同一份评估（打铁 RefreshProductPreview 同构）。
    const FColdSteelItem Item=Model->CreateItem(Recipe->Output);
    const auto Data=BuildColdSteelItemTooltip(Item,Model,GetGameInstance()->GetSubsystem<UGunsmithSystem>());
    Set(PreviewName,Data.Name.IsEmpty()?DefinitionName(Recipe->Output):Data.Name);
    Set(PreviewStage,TEXT("全新成品 · 基础品质"));
    Set(PreviewScope,Data.ValueScope);
    while(PreviewRows.Num()<Data.Summary.Num())
    {
        const int32 RowIndex=PreviewRows.Num();
        auto* Name=Text(TEXT(""),14,ColdSteelUI::TextSecondary,false,false,true);
        auto* Value=Text(TEXT(""),14,ColdSteelUI::TextPrimary,true);
        Value->SetJustification(ETextJustify::Right);Value->SetAutoWrapText(false);
        for(int32 Column=0;Column<2;++Column)
        {
            auto* CellSlot=PreviewParameterGrid->AddChildToGrid(Column==0?static_cast<UWidget*>(Name):static_cast<UWidget*>(Value),RowIndex,Column);
            CellSlot->SetVerticalAlignment(VAlign_Center);CellSlot->SetHorizontalAlignment(HAlign_Fill);
            CellSlot->SetPadding(FMargin(Column==0?0.f:12.f/Scale,6.f/Scale,0,6.f/Scale));
            PreviewCellSlots.Add(CellSlot);
        }
        PreviewRows.Add({Name,Value});
    }
    for(int32 I=0;I<PreviewRows.Num();++I)
    {
        auto& Row=PreviewRows[I];const bool Visible=Data.Summary.IsValidIndex(I);
        Row.Name->SetVisibility(Visible?ESlateVisibility::HitTestInvisible:ESlateVisibility::Collapsed);
        Row.Value->SetVisibility(Visible?ESlateVisibility::HitTestInvisible:ESlateVisibility::Collapsed);
        if(Visible){Set(Row.Name.Get(),Data.Summary[I].Label);Set(Row.Value.Get(),Data.Summary[I].Value);}
    }
    if(const FSlateBrush* Brush=IconFor(Recipe->Output))
    {PreviewIcon->SetBrush(*Brush);PreviewIcon->SetVisibility(ESlateVisibility::HitTestInvisible);PreviewEmpty->SetVisibility(ESlateVisibility::Collapsed);}
    else
    {PreviewIcon->SetVisibility(ESlateVisibility::Collapsed);PreviewEmpty->SetText(FText::FromString(TEXT("暂无物品图像")));PreviewEmpty->SetVisibility(ESlateVisibility::HitTestInvisible);}
}

void UColdSteelWorkbenchWidget::HandleRecipeSelected(FString Option,ESelectInfo::Type SelectionType)
{
    if(SelectionType==ESelectInfo::Direct||!Crafting||!Model)return;
    const TArray<FColdSteelCraftingRecipe>& Catalog=Crafting->Catalog();
    const int32 Index=RecipeChoice->GetSelectedIndex();
    if(!bInputReady||!World.IsValid()||!Catalog.IsValidIndex(Index))
    {   // 无效切换（无台上下文/越界）回滚到当前选中（打铁 HandleRecipeSelected 同款守卫）。
        RecipeChoice->SetSelectedIndex(Catalog.IndexOfByPredicate([this](const FColdSteelCraftingRecipe& R){return R.Id==SelectedRecipe;}));
        return;
    }
    if(SelectedRecipe==Catalog[Index].Id)return;
    SelectedRecipe=Catalog[Index].Id;Batch=1;   // 换配方清批量（可作份数变了）
    SetStatus(FString());RefreshDataChanged();RefreshJob();SetKeyboardFocus();
}

UWidget* UColdSteelWorkbenchWidget::GenerateRecipeOption(FString Option)
{
    auto* Widget=CreateWidget<UColdSteelGunRecipeOptionWidget>(this);
    if(!Widget)return nullptr;
    Widget->Configure(Option,ColdSteelUI::PixelScale(this));
    RecipeOptionWidgets.RemoveAll([](const auto& Entry){return !Entry.IsValid();});RecipeOptionWidgets.Add(Widget);
    return Widget;
}

FString UColdSteelWorkbenchWidget::InputsText(const FColdSteelCraftingRecipe& R,int64 InBatch) const
{
    const int64 Mul=FMath::Max<int64>(1,InBatch);
    FString S;
    for(const auto& In:R.Inputs)
    {
        if(!S.IsEmpty())S+=TEXT(" · ");
        S+=FString::Printf(TEXT("%s ×%lld"),*DefinitionName(In.Item),In.Count*Mul);
    }
    return S;
}

void UColdSteelWorkbenchWidget::HandleCraft()
{
    if(!bInputReady||!HUD||!HUD->IsWorkbenchOpen()||!World.IsValid()||!World->HasPrefabAt(Cell)||SelectedRecipe.IsNone()||!Crafting)return;
    const FColdSteelCraftingRecipe* R=Crafting->Find(SelectedRecipe);
    if(!R){SetStatus(TEXT("该配方不存在"),true);return;}
    const FString OutName=DefinitionName(R->Output);
    const FString Cost=InputsText(*R,Batch);
    const int64 N=Batch;
    FString Reason;
    if(Crafting->Craft(SelectedRecipe,N,Reason))
    {
        SetStatus(FString::Printf(TEXT("已制作 %s ×%lld · 消耗 %s"),*OutName,R->OutputCount*N,*Cost));
    }
    else SetStatus(Reason,true);
    RefreshDataChanged();RefreshJob();SetKeyboardFocus();
}

void UColdSteelWorkbenchWidget::HandleBatchMinus()
{
    if(bInputReady&&Batch>1){--Batch;SetStatus(FString());bDataDirty=true;RefreshJob();SetKeyboardFocus();}
}

void UColdSteelWorkbenchWidget::HandleBatchPlus()
{
    if(bInputReady&&Batch<MaxBatch){++Batch;SetStatus(FString());bDataDirty=true;RefreshJob();SetKeyboardFocus();}
}

void UColdSteelWorkbenchWidget::SetStatus(const FString& Line,bool bError)
{
    if(!StatusLine)return;
    StatusLine->SetText(FText::FromString(Line));
    StatusLine->SetVisibility(Line.IsEmpty()?ESlateVisibility::Collapsed:ESlateVisibility::HitTestInvisible);
    StatusLine->SetColorAndOpacity(Line.IsEmpty()?ColdSteelUI::TextTertiary:bError?ColdSteelUI::Warning:ColdSteelUI::TextSecondary);
}

const FSlateBrush* UColdSteelWorkbenchWidget::IconFor(const FString& Definition)
{
    if(!Model||Definition.IsEmpty())return nullptr;
    if(const auto* Found=IconBrushes.Find(Definition))return Found;
    if(FailedIcons.Contains(Definition))return nullptr;
    const FString File=ColdSteelInventory::Text(Model->CreateItem(Definition),TEXT("ue_icon"));
    if(File.IsEmpty()){FailedIcons.Add(Definition);return nullptr;}
    auto* Texture=FImageUtils::ImportFileAsTexture2D(FPaths::ProjectContentDir()/TEXT("ColdSteelData")/File);
    if(!Texture){FailedIcons.Add(Definition);return nullptr;}   // 失败要记住：源文件缺失，别每次刷新都重试。
    IconTextures.Add(Texture);
    FSlateBrush Brush;Brush.SetResourceObject(Texture);
    Brush.ImageSize=FVector2D(Texture->GetSizeX(),Texture->GetSizeY());Brush.DrawAs=ESlateBrushDrawType::Image;
    return &IconBrushes.Add(Definition,Brush);
}

FString UColdSteelWorkbenchWidget::DefinitionName(const FString& Definition) const
{
    if(!Model||Definition.IsEmpty())return Definition;
    const FString Name=ColdSteelInventory::Text(Model->CreateItem(Definition),TEXT("name"));
    return Name.IsEmpty()?Definition:Name;
}

void UColdSteelWorkbenchWidget::RefreshUpgrade()
{
    if(UpgradeTabText)   // v11：展开态文案换"收回"，点击收回＝关闭升级栏（同一页签互斥翻转）
    {   const FText Want=FText::FromString(bUpgradeOpen?TEXT("收\n回"):TEXT("升\n级"));
        if(!UpgradeTabText->GetText().EqualTo(Want))UpgradeTabText->SetText(Want);   }
    if(bTabVisualOpen!=bUpgradeOpen){bTabVisualOpen=bUpgradeOpen;ApplyUpgradeTabVisual();}   // v12：换色跟随所贴主体
    if(!bUpgradeOpen)return;   // 弹层收回时不刷内容（冶炼同款：数据只在展开期跟随刷）
    // —— 页签高亮（v10 配方行同款选中样式）；Lv/效果/材料读数等升级轴数据上线后在此接入 ——
    UpgSel=FMath::Clamp(UpgSel,0,FMath::Max(0,UpgTabs.Num()-1));
    for(int32 A=0;A<UpgTabs.Num();++A)
    {
        const bool bSel=A==UpgSel;
        if(UpgTabSurfs.IsValidIndex(A)&&UpgTabSurfs[A])UpgTabSurfs[A]->SetBrush(ColdSteelUI::RoundedBrush(
            bSel?ColdSteelUI::ButtonHover:ColdSteelUI::StatusCard,ColdSteelUI::CardRadius/Scale,
            bSel?ColdSteelUI::Accent:ColdSteelUI::Border,bSel?2.f/Scale:1.f/Scale));
        if(UpgTabNames.IsValidIndex(A)&&UpgTabNames[A])
            UpgTabNames[A]->SetFont(GunsmithUI::TextFont(14/Scale,bSel));   // §4：Medium＝选中页
    }
    if(FlyDetailName&&UpgTabNames.IsValidIndex(UpgSel)&&UpgTabNames[UpgSel])
        FlyDetailName->SetText(UpgTabNames[UpgSel]->GetText());   // 详情带轴名随选中页签（占位名同步切换）
}

void UColdSteelWorkbenchWidget::SelectUpgradeAxis(int32 Axis)
{
    // 点击立即换详情，不等下一拍刷新（冶炼同款）。
    UpgSel=FMath::Clamp(Axis,0,FMath::Max(0,UpgTabs.Num()-1));RefreshUpgrade();
}

void UColdSteelWorkbenchWidget::DebugClickUpgradeTab(int32 Axis)
{
    if(UpgTabs.IsValidIndex(Axis)&&UpgTabs[Axis])UpgTabs[Axis]->OnClicked.Broadcast();
}

void UColdSteelWorkbenchWidget::HandleUpgradeToggled()
{
    if(!bInputReady)return;
    bUpgradeOpen=!bUpgradeOpen;RefreshUpgrade();   // 展开/收回动画由 NativeTick 的 FlyMotion 驱动
}

void UColdSteelWorkbenchWidget::HandleUpgradeClose()
{
    bUpgradeOpen=false;RefreshUpgrade();
}

void UColdSteelWorkbenchWidget::HandleUpgradeClicked()
{
    // 占位：工作台升级事务后续设计（冶炼对应 UpgradeAxis→System->UpgradeFurnace）。
}

void UColdSteelWorkbenchWidget::HandleClose()
{
    // 面板独立于背包：× 与 Esc 走同一个出口（HUD 的 CloseWorkbench 幂等，重复调用安全）。
    if(HUD)HUD->CloseWorkbench();
}
