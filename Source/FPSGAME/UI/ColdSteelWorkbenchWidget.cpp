#include "ColdSteelWorkbenchWidget.h"
#include "ColdSteelHUDWidget.h"
#include "ColdSteelUIStyle.h"
#include "GunsmithUIStyle.h"
#include "../Building/VoxelBuildWorld.h"
#include "Blueprint/WidgetTree.h"
#include "Components/BackgroundBlur.h"
#include "Components/Border.h"
#include "Components/Button.h"
#include "Components/ButtonSlot.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/HorizontalBox.h"
#include "Components/HorizontalBoxSlot.h"
#include "Components/Image.h"
#include "Components/ScrollBox.h"
#include "Components/SizeBox.h"
#include "Components/TextBlock.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"

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

void UColdSteelWorkbenchWidget::Configure(UColdSteelHUDWidget* Owner)
{
    HUD=Owner;
}

void UColdSteelWorkbenchWidget::NativeOnInitialized()
{
    Super::NativeOnInitialized();SetIsFocusable(true);
    Scale=ColdSteelUI::PixelScale(this);
    // 根＝Canvas：主题层把本 widget 槽位扩到屏幕左缘→面板右缘的全宽命中区（冶炼 §7.7 教训：
    // 挂在父边界外的负坐标子控件能绘制但收不到点击），Shell 用正偏移贴到面板位，
    // 页签/弹层坐标一律以屏幕像素折算、全部落在槽位内。
    RootCanvas=WidgetTree->ConstructWidget<UCanvasPanel>();WidgetTree->RootWidget=RootCanvas;
    // 本体/根画布均 SelfHitTestInvisible：透明区放行世界点击、子控件照常命中
    //（HitTestInvisible 会连子树一起屏蔽命中——冶炼 §7.8 已入档的根因）。
    SetVisibility(ESlateVisibility::SelfHitTestInvisible);
    RootCanvas->SetVisibility(ESlateVisibility::SelfHitTestInvisible);
    // 外壳三段式（与仓库/背包/冶炼同源）：描边 Border → 真实 UBackgroundBlur → 玻璃 Tint → 内容。
    auto* ShellOuter=WidgetTree->ConstructWidget<UBorder>();
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
    // 顶栏＝标题（20px Medium 档）＋ × 关闭：面板独立于背包，自带出口（Esc 同效）——冶炼同款。
    auto* TitleSlot=Heading->AddChildToHorizontalBox(Text(TEXT("制作"),20,ColdSteelUI::TextPrimary,false,true));
    TitleSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));TitleSlot->SetVerticalAlignment(VAlign_Center);
    auto* PanelClose=Action(TEXT("×"));
    PanelClose->OnClicked.AddDynamic(this,&ThisClass::HandleClose);
    Heading->AddChildToHorizontalBox(PanelClose)->SetVerticalAlignment(VAlign_Center);

    auto* Body=WidgetTree->ConstructWidget<UVerticalBox>();
    BodySlot=Stack->AddChildToVerticalBox(Body);BodySlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));

    // —— 工作台状态卡（与炉内状态卡同款 StatusCard 8px；进度/取出属冶炼内容，本卡只留外壳）——
    StatusCard=WidgetTree->ConstructWidget<UBorder>();
    StatusCard->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::StatusCard,ColdSteelUI::CardRadius/Scale,ColdSteelUI::Border,1/Scale));
    Body->AddChildToVerticalBox(StatusCard)->SetPadding(FMargin(0,0,0,10/Scale));
    auto* CardStack=WidgetTree->ConstructWidget<UVerticalBox>();StatusCard->SetContent(CardStack);
    auto* CardHeader=WidgetTree->ConstructWidget<UHorizontalBox>();
    CardStack->AddChildToVerticalBox(CardHeader)->SetPadding(FMargin(0,0,0,6/Scale));
    IconSize=WidgetTree->ConstructWidget<USizeBox>();
    IconSize->SetWidthOverride(28/Scale);IconSize->SetHeightOverride(28/Scale);
    CardHeader->AddChildToHorizontalBox(IconSize)->SetVerticalAlignment(VAlign_Center);
    IconImage=WidgetTree->ConstructWidget<UImage>();IconImage->SetVisibility(ESlateVisibility::Collapsed);   // 图标位预留（内容后续设计）
    IconSize->SetContent(IconImage);
    auto* CardTitle=Text(TEXT("工作台空闲"),16,ColdSteelUI::TextTertiary,false,true);
    auto* CardTitleSlot=CardHeader->AddChildToHorizontalBox(CardTitle);
    CardTitleSlot->SetPadding(FMargin(10/Scale,0,0,0));CardTitleSlot->SetVerticalAlignment(VAlign_Center);
    auto* CardDetail=Text(TEXT("制作配方与流程后续设计"),12,ColdSteelUI::TextTertiary,false,false,true);
    CardStack->AddChildToVerticalBox(CardDetail)->SetPadding(FMargin(0,0,0,8/Scale));

    // —— 可制作项目列表（与矿石列表同款：分区标题＋滚动行卡＋空态行；配方上线前恒空态）——
    auto* SectionTitle=Text(TEXT("可制作项目"),16,ColdSteelUI::TextPrimary,false,true);
    Body->AddChildToVerticalBox(SectionTitle)->SetPadding(FMargin(0,0,0,8/Scale));
    RowsScroll=WidgetTree->ConstructWidget<UScrollBox>();RowsScroll->SetAllowOverscroll(false);
    Body->AddChildToVerticalBox(RowsScroll)->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    auto* RowsBox=WidgetTree->ConstructWidget<UVerticalBox>();RowsScroll->AddChild(RowsBox);
    RowsEmpty=Text(TEXT("制作内容后续设计，敬请期待"),12,ColdSteelUI::TextTertiary,false,false,true);
    RowsBox->AddChildToVerticalBox(RowsEmpty);

    // —— 底部操作与状态行（主操作整宽＝「开始冶炼」同款行；配方与提交事务后续设计，先禁用）——
    StartSize=WidgetTree->ConstructWidget<USizeBox>();StartSize->SetHeightOverride(ColdSteelUI::ActionHeight/Scale);
    StartSlot=Stack->AddChildToVerticalBox(StartSize);
    StartButton=Action(TEXT("开始制作"));StartSize->SetContent(StartButton);
    StartButton->SetIsEnabled(false);
    StatusLine=Text(TEXT(""),12,ColdSteelUI::TextTertiary,false,false,true);
    StatusSlot=Stack->AddChildToVerticalBox(StatusLine);

    // 页脚快捷键/语义说明（12px 辅助档，可换行）——与冶炼页脚同一位置语义。
    Footer=Text(TEXT("Esc 或 × 关闭 · 制作配方与升级内容后续设计"),12,ColdSteelUI::TextTertiary,false,false,true);
    FooterSlot=Stack->AddChildToVerticalBox(Footer);

    // —— 左缘「升级」页签（冶炼 v11c 同款）：36×60 方片，竖排两字逐行居中；
    //    收起态右缘压面板左缘缝 2px，展开态随弹层左缘推到最左、文案换"收回"（点击＝关闭）———
    UpgradeTab=WidgetTree->ConstructWidget<UBorder>();
    UpgradeTab->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::GlassTint,8.f/Scale,GunsmithUI::Edge,1/Scale));
    UpgradeTab->SetPadding(FMargin(3/Scale));
    auto* TabInner=WidgetTree->ConstructWidget<UButton>();
    UpgradeTabText=Text(TEXT("升\n级"),14,ColdSteelUI::TextPrimary,false,true);
    UpgradeTabText->SetJustification(ETextJustify::Center);   // 块内每行默认左对齐——居中修正（冶炼 v11c 根因）
    TabInner->SetContent(UpgradeTabText);
    StyledButtons.Add(TabInner);
    TabInner->OnClicked.AddDynamic(this,&ThisClass::HandleUpgradeToggled);   // 收回态点击＝关闭升级栏（互斥翻转）
    UpgradeTab->SetContent(TabInner);
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
    UpgradeFlyout->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::Content,10.f/Scale,GunsmithUI::Edge,1/Scale));
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
    HeaderSurface->SetPadding(FMargin(18/Scale,12/Scale));HeaderSize->SetHeightOverride(36/Scale);
    StatusCard->SetPadding(FMargin(12/Scale));
    IconSize->SetWidthOverride(28/Scale);IconSize->SetHeightOverride(28/Scale);
    StartSize->SetHeightOverride(ColdSteelUI::ActionHeight/Scale);
    if(auto* TS=Cast<UCanvasPanelSlot>(UpgradeTabSlot))TS->SetSize(FVector2D(36/Scale,60/Scale));
    ApplyScreenLayout();   // Shell/页签/弹层按新 Scale 重排（坐标源＝主题层推送的屏幕像素）
    UpgradeTab->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::GlassTint,8.f/Scale,GunsmithUI::Edge,1/Scale));
    UpgradeTab->SetPadding(FMargin(3/Scale));
    UpgradeFlyout->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::Content,10.f/Scale,GunsmithUI::Edge,1/Scale));
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
    RowsScroll->SetScrollbarThickness(FVector2D(6/Scale));   // 正式规则 §3：中性灰线 6px 滚动条
    // 分区留白（§4"明度、细边、留白建立层级"）：与冶炼面板同一组 16px 边缘留白。
    BodySlot->SetPadding(FMargin(16/Scale,12/Scale,16/Scale,0));
    StartSlot->SetPadding(FMargin(16/Scale,2/Scale,16/Scale,4/Scale));
    StatusSlot->SetPadding(FMargin(16/Scale,2/Scale,16/Scale,2/Scale));
    FooterSlot->SetPadding(FMargin(16/Scale,0,16/Scale,8/Scale));
    for(const auto& L:Labels)if(auto* Label=L.Widget.Get())
        Label->SetFont(L.Numeric?GunsmithUI::NumberFont(L.Pixels/Scale,L.Medium):GunsmithUI::TextFont(L.Pixels/Scale,L.Medium));
    const FButtonStyle Style=ColdSteelUI::ButtonStyle(Scale);
    for(const auto& Weak:StyledButtons)if(auto* B=Weak.Get())
    {
        B->SetStyle(Style);
        if(auto* Content=B->GetContent())if(auto* ContentSlot=Cast<UButtonSlot>(Content->Slot))ContentSlot->SetPadding(FMargin(10/Scale,8/Scale));
    }
    RefreshUpgrade();   // 页签选中卡面/字号按新 Scale 复原（冶炼 UpdateScale 末尾同构）
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
    // 右缘压过接缝 2px（冶炼 v11c，两档"有间隙"反馈的定位）：方片与面板各带 1px 描边，边对边
    // 必夹一条可见缝，非整数 Scale 下还会再宽 1px；压 2px 后方片描边盖在面板描边之上，玻璃对玻璃无缝。
    // 展开态跟随：EaseSmooth(FlyMotion) 与弹层 RenderScale 同曲线同拍，方片右缘钉在弹层左缘上推到最左；
    // 屏幕边钳制：方片贴到 x=0 盖在弹层角上（ZOrder 1，可点收回）。
    const float X=FMath::Max(0.f,FMath::Lerp(P-TabW,L-TabW,ColdSteelUI::EaseSmooth(FlyMotion))+2.f/Scale);
    UpgradeTabSlot->SetPosition(FVector2D(X,0.f));
}

void UColdSteelWorkbenchWidget::SetWorkbench(AVoxelBuildWorld* InWorld,FIntVector InCell)
{
    World=InWorld;Cell=InCell;
    bUpgradeOpen=false;   // 换台上下文时收起升级弹层（升级数据是逐台的，别把上一台的弹层带过来）
    UpgSel=0;             // 页签选择同样归零：新工作台从默认轴看起（冶炼换炉同款）
    FlyMotion=0.f;        // 瞬关不播收回动画（防残影随面板滑入，冶炼同款处理）
    if(UpgradeFlyout){UpgradeFlyout->SetVisibility(ESlateVisibility::Collapsed);UpgradeFlyout->SetRenderScale(FVector2D(1.f,1.f));}
    if(UpgradeTab)UpgradeTab->SetVisibility(ESlateVisibility::HitTestInvisible);   // 面板只在有效上下文打开，页签常驻
    RefreshUpgrade();
}

void UColdSteelWorkbenchWidget::SetLayoutWidth(float PixelsX)
{
    if(FMath::IsNearlyEqual(LayoutWidth,PixelsX,.5f))return;
    LayoutWidth=PixelsX;ApplyScreenLayout();   // 弹层与面板同宽，宽度推送要同步重排
}

void UColdSteelWorkbenchWidget::SetPanelScreenX(float Px)
{
    if(FMath::IsNearlyEqual(PanelScreenPx,Px,.5f))return;
    PanelScreenPx=Px;ApplyScreenLayout();
}

void UColdSteelWorkbenchWidget::NativeTick(const FGeometry& MyGeometry,float InDeltaTime)
{
    Super::NativeTick(MyGeometry,InDeltaTime);
    if(!FMath::IsNearlyEqual(Scale,ColdSteelUI::PixelScale(this),.001f)){UpdateScale();return;}
    if(GetVisibility()==ESlateVisibility::Collapsed)return;
    // 升级弹层动画（冶炼 §7.12 同款）：右缘钉死在面板左缘那条缝上（枢纽右中），
    // 横向缩放 0→1 向左展开、1→0 向右收回，4.0/s＋EaseSmooth。
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
    RefreshUpgrade();
}

void UColdSteelWorkbenchWidget::RefreshUpgrade()
{
    if(UpgradeTabText)   // v11：展开态文案换"收回"，点击收回＝关闭升级栏（同一页签互斥翻转）
    {   const FText Want=FText::FromString(bUpgradeOpen?TEXT("收\n回"):TEXT("升\n级"));
        if(!UpgradeTabText->GetText().EqualTo(Want))UpgradeTabText->SetText(Want);   }
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
