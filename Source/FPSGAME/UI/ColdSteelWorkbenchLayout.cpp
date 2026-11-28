#include "ColdSteelWorkbenchWidget.h"
#include "ColdSteelTextToolTip.h"
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
#include "../Building/VoxelBuildPrefabActor.h"
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
#include "ColdSteelScrollBar.h"
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
    Scroll=WidgetTree->ConstructWidget<UColdSteelScrollBox>();Scroll->SetConsumeMouseWheel(EConsumeMouseWheel::Always);ColdSteelUI::ConfigureGoldScrollBox(Scroll,6/Scale);
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
    ColdSteelToolTip::Set(*RecipeChoice, FText::FromString(TEXT("选择制作配方；材料取自背包与主仓库，制作即时结算。")));
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
    PreviewScroll=WidgetTree->ConstructWidget<UColdSteelScrollBox>();ColdSteelUI::ConfigureGoldScrollBox(PreviewScroll,6/Scale);PreviewParameterCard->SetContent(PreviewScroll);
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
    UpgradeTabText=Text(TEXT("升级"),14,ColdSteelUI::TextPrimary,false,true);
    UpgradeTabText->SetJustification(ETextJustify::Center);   // 块内每行默认左对齐——居中修正（冶炼 v11c 根因）
    UpgradeTabText->SetAutoWrapText(false);UpgradeTabText->SetWrapTextAt(0); // 横向单行页签。
    UpgradeTabBtn->SetContent(UpgradeTabText);
    // v12：不进 StyledButtons（共享样式带描边），外观由 ApplyUpgradeTabVisual 统一给无描边样式。
    UpgradeTabBtn->OnClicked.AddDynamic(this,&ThisClass::HandleUpgradeToggled);   // 收回态点击＝关闭升级栏（互斥翻转）
    UpgradeTab->SetContent(UpgradeTabBtn);
    ApplyUpgradeTabVisual();
    UpgradeTabSlot=RootCanvas->AddChildToCanvas(UpgradeTab);
    UpgradeTabSlot->SetAnchors(FAnchors(0,.5f));UpgradeTabSlot->SetAlignment(FVector2D(0,.5f));
    UpgradeTabSlot->SetSize(FVector2D(64/Scale,36/Scale));
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

