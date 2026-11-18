#include "ColdSteelSmeltingWidget.h"
#include "ColdSteelCampfirePanel.h"
#include "ColdSteelSmeltingPresentation.h"
#include "ColdSteelHUDWidget.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelInventoryTypes.h"
#include "ColdSteelUIStyle.h"
#include "GunsmithUIStyle.h"
#include "../Building/SmeltingSystem.h"
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
#include "Components/Overlay.h"
#include "Components/OverlaySlot.h"
#include "Components/ProgressBar.h"
#include "Components/ScrollBox.h"
#include "Components/SizeBox.h"
#include "Components/TextBlock.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "Components/WidgetSwitcher.h"
#include "Engine/Texture2D.h"
#include "ImageUtils.h"
#include "Misc/Paths.h"

#include "ColdSteelSmeltingLayoutPrivate.h"
using namespace ColdSteelSmeltingLayoutPrivate;

namespace
{
    using ColdSteelSmeltingPresentation::SmeltingProgressColor;
    using ColdSteelSmeltingPresentation::FuelFillColor;
    /**
     * 复刻原项目 game-dev `game-ui-manager.js:51-68` 的 `timelineProgressColor`：
     * 四个色标之间按进度线性插值。**方向按冶炼语义正向化**（规划文档第 2.2 节）：
     * 0%=红 → 1/3=黄 → 2/3=蓝 → 100%=绿；原项目为倒计时威胁语义（0 绿 1 红），常量在此不混用。
     */

    FString DefinitionName(UColdSteelStatusModel* Model,const FString& Definition)
    {
        if(!Model||Definition.IsEmpty())return Definition;
        const FString Name=ColdSteelInventory::Text(Model->CreateItem(Definition),TEXT("name"));
        return Name.IsEmpty()?Definition:Name;
    }

    /** 燃料条底色：按存料占比从暖橙 #F0BE71（Warning 档）渐变到亮黄 #F1C13F——
     *  越满越"有货"，与左侧进度条的四段色语义分开（燃料=存量、进度=时间）。 */

    /** 秒数 → 人类可读：≥60 秒折算"X 分 Y 秒"（整分省秒），否则原样。燃料每件 1 分钟，界面按分读。 */
    FString ReadableSeconds(double Seconds)
    {
        const int64 Total=FMath::RoundToInt64(Seconds);
        if(Total<60)return FString::Printf(TEXT("%lld 秒"),Total);
        const int64 M=Total/60,R=Total%60;
        return R>0?FString::Printf(TEXT("%lld 分 %lld 秒"),M,R):FString::Printf(TEXT("%lld 分钟"),M);
    }
}

void UColdSteelSmeltingRowProxy::Clicked()
{
    if(auto* Owner=Panel.Get())Owner->SelectRecipe(Recipe);
}

void UColdSteelSmeltingRowProxy::AxisClicked()
{
    if(auto* Owner=Panel.Get())Owner->SelectUpgradeAxis(Axis);
}


UTextBlock* UColdSteelSmeltingWidget::Text(const FString& Caption,float Pixels,const FLinearColor& Color,bool Numeric,bool Medium,bool bWrap)
{
    auto* Label=WidgetTree->ConstructWidget<UTextBlock>();
    Label->SetText(FText::FromString(Caption));Label->SetColorAndOpacity(Color);
    Label->SetFont(Numeric?GunsmithUI::NumberFont(Pixels/Scale,Medium):GunsmithUI::TextFont(Pixels/Scale,Medium));
    if(bWrap)Label->SetAutoWrapText(true);   // Slate 不裁剪不换行=文字画出玻璃框（正式规则 §3）。
    Label->SetVisibility(ESlateVisibility::HitTestInvisible);
    Labels.Add({Label,Pixels,Numeric,Medium});return Label;
}

UButton* UColdSteelSmeltingWidget::Action(const FString& Caption)
{
    auto* B=WidgetTree->ConstructWidget<UButton>();
    B->SetContent(Text(Caption,14,ColdSteelUI::TextPrimary));
    StyledButtons.Add(B);return B;
}

void UColdSteelSmeltingWidget::Configure(UColdSteelHUDWidget* Owner){HUD=Owner;}

void UColdSteelSmeltingWidget::SetFurnace(AVoxelBuildWorld* InWorld,FIntVector InCell)
{
    Campfire.Reset();
    if(StationPanels)StationPanels->SetActiveWidgetIndex(0);
    if(CampfirePanel)CampfirePanel->Configure(HUD,nullptr);
    // The shared campfire panel disables collection when empty or awaiting a receipt.
    // A different station must not inherit that button state.
    CollectButton->SetIsEnabled(true);
    World=InWorld;Cell=InCell;SelectedRecipe=NAME_None;
    bCampfire=InWorld&&InWorld->IsCampfireAt(Cell);
    RowsSignature.Reset();
    StationTitle->SetText(FText::FromString(bCampfire?TEXT("篝火 · 烧烤"):TEXT("冶炼")));
    ProgressTitle->SetText(FText::FromString(bCampfire?TEXT("烧烤进度"):TEXT("冶炼进度")));
    SectionTitle->SetText(FText::FromString(bCampfire?TEXT("可烧烤食材"):TEXT("可冶炼原料")));
    const bool bHasRecipes=System&&System->Catalog().ContainsByPredicate([](const auto& R){return R.bCampfire;});
    RowsEmpty->SetText(FText::FromString(bCampfire?(bHasRecipes?TEXT("背包与仓库中没有可烧烤的食材")
        :TEXT("暂无已接入的烧烤菜谱；仍可在下方添加木材取暖。")):TEXT("背包与仓库中没有可冶炼的原料")));
    StationFooter->SetText(FText::FromString(bCampfire
        ?TEXT("Esc / × 关闭 · 木材持续燃烧，离线也计时 · 燃烧时 5 米内饥饿与缺水自然消耗各减缓 50%，不叠加")
        :TEXT("Esc 或 × 关闭 · 存料持续燃烧（没矿也烧）· 有燃料才推进冶炼（关闭游戏也计入）")));
    bUpgradeOpen=false;   // 换炉上下文时收起升级弹层（等级是逐炉数据，别把上一座的弹层带过来）
    UpgSel=VoxelFurnaceAxisSpeed;   // 页签选择同样归零：新炉从默认轴看起
    CdLastBranch=-1;CdLastFuelSec=CdLastNeedSec=-1;   // 换炉后燃料行强制重绘一次
    FlyMotion=0.f;   // 换炉上下文时弹层瞬关（不播收回动画，防残影随面板滑入）
    if(UpgradeFlyout){UpgradeFlyout->SetVisibility(ESlateVisibility::Collapsed);UpgradeFlyout->SetRenderScale(FVector2D(1.f,1.f));}
    SetStatus(bCampfire&&InWorld->GetNetMode()!=NM_Standalone?TEXT("联机添柴与烧烤尚未接入"):FString());
    RefreshRows();RefreshJob();
}

void UColdSteelSmeltingWidget::SetLayoutWidth(float PixelsX)
{
    if(FMath::IsNearlyEqual(LayoutWidth,PixelsX,.5f))return;
    LayoutWidth=PixelsX;ApplyScreenLayout();RefreshJob();   // 弹层与面板同宽，宽度推送要同步重排（2026-09-24）
}

void UColdSteelSmeltingWidget::SetPanelScreenX(float Px)
{
    if(FMath::IsNearlyEqual(PanelScreenPx,Px,.5f))return;
    PanelScreenPx=Px;ApplyScreenLayout();
}

void UColdSteelSmeltingWidget::SelectRecipe(FName Recipe)
{
    if(SelectedRecipe==Recipe)return;
    SelectedRecipe=Recipe;SetStatus(FString());RefreshSelection();RefreshJob();
}

void UColdSteelSmeltingWidget::NativeConstruct()
{
    Super::NativeConstruct();
    if(Model&&!ChangedHandle.IsValid())ChangedHandle=Model->OnChanged.AddUObject(this,&ThisClass::RefreshJob);
    RefreshRows();RefreshJob();
}

void UColdSteelSmeltingWidget::NativeDestruct()
{
    if(Model)Model->OnChanged.Remove(ChangedHandle);
    ChangedHandle.Reset();Super::NativeDestruct();
}

void UColdSteelSmeltingWidget::NativeTick(const FGeometry& MyGeometry,float InDeltaTime)
{
    Super::NativeTick(MyGeometry,InDeltaTime);
    if(!FMath::IsNearlyEqual(Scale,ColdSteelUI::PixelScale(this),.001f)){UpdateScale();return;}
    if(GetVisibility()==ESlateVisibility::Collapsed)return;
    if(bCampfire&&Campfire.IsValid())return; // Dedicated child owns the campfire clock and scrolling content.
    AnimateBars(InDeltaTime);   // 每帧：脉冲与火星读缓存值，不触发数据刷新
    PaintFuelLine();            // 每帧：燃料行挂钟外推；整数秒没变即返回（零分配零写入）
    // 升级弹层动画（2026-09-24 用户"作为一个独立的页面，以冶炼栏左边线条边界为基准，弹出和收回"）：
    // 右缘钉死在面板左缘那条缝上（枢轴右中），横向缩放 0→1 向左展开、1→0 向右收回，同款 4.0/s。
    // 不再从面板背后滑出——磨砂玻璃半透明，"藏"会漏成穿帮（上一版动画问题的根因）。
    FlyMotion=FMath::FInterpConstantTo(FlyMotion,bUpgradeOpen?1.f:0.f,InDeltaTime,4.0f);
    if(UpgradeFlyout)
    {
        UpgradeFlyout->SetVisibility(FlyMotion>KINDA_SMALL_NUMBER?ESlateVisibility::Visible:ESlateVisibility::Collapsed);
        UpgradeFlyout->SetRenderScale(FVector2D(FMath::Max(ColdSteelUI::EaseSmooth(FlyMotion),.02f),1.f));
    }
    LayoutUpgradeTab();   // v11：方片逐帧跟弹层左缘（与 RenderScale 同曲线）；静止时仅一次属性写，开销可忽略。
    RefreshAccum+=InDeltaTime;
    if(RefreshAccum<.1f)return;   // 进度与剩余时间按 0.1s 节流刷新（面板开着才计）。
    RefreshAccum=0.f;
    if(auto* W=World.Get())if(System)System->SettleFurnace(W,Cell);   // 面板开着的挂钟落账（写档脏标由 Settle 判定）
    RefreshJob();
}

void UColdSteelSmeltingWidget::RefreshRows()
{
    if(!RowsBox||!Model||!System)return;
    FString Signature=bCampfire?TEXT("campfire;"):TEXT("furnace;");
    for(const FColdSteelSmeltingRecipe& R:System->Catalog())
        if(R.bCampfire==bCampfire)Signature+=FString::Printf(TEXT("%s:%lld;"),*R.Id.ToString(),Model->CountMaterial(R.Input));
    if(Signature==RowsSignature)
    {
        // 持有量没变就不重建行（保住选择与滚动位置），但换炉子后的选中高亮仍要刷一次。
        if(Rows.IsEmpty())RowsEmpty->SetVisibility(ESlateVisibility::Visible);
        else RefreshSelection();
        return;
    }
    RowsSignature=Signature;
    RowsBox->ClearChildren();Rows.Reset();RowProxies.Reset();
    for(const FColdSteelSmeltingRecipe& R:System->Catalog())
    {
        if(R.bCampfire!=bCampfire)continue;
        const int64 Have=Model->CountMaterial(R.Input);
        if(Have<=0)continue;   // 未持有不生成卡片（与附魔卷轴同一口径），列表只报价可负担的配方。
        auto* Card=WidgetTree->ConstructWidget<UBorder>();
        Card->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::StatusCard,ColdSteelUI::CardRadius/Scale,ColdSteelUI::Border,1/Scale));
        Card->SetPadding(FMargin(12/Scale,10/Scale));   // 与炉内状态卡的 12px 内沿同一列
        RowsBox->AddChildToVerticalBox(Card)->SetPadding(FMargin(0,0,0,6/Scale));
        auto* Row=WidgetTree->ConstructWidget<UButton>();
        // 行按钮透明常态 + 语义色悬停：卡片底色与选中描边由外层 Border 负责（建造抽屉行卡先例）。
        Row->SetStyle(FButtonStyle()
            .SetNormal(ColdSteelUI::RoundedBrush(FLinearColor::Transparent,0,FLinearColor::Transparent,0))
            .SetHovered(ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonHover,ColdSteelUI::CardRadius/Scale,FLinearColor::Transparent,0))
            .SetPressed(ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonPressed,ColdSteelUI::CardRadius/Scale,FLinearColor::Transparent,0)));
        Card->SetContent(Row);
        auto* Content=WidgetTree->ConstructWidget<UHorizontalBox>();Row->SetContent(Content);
        // UButtonSlot 默认 HAlign_Center：行内容按 desired 收缩并居中，Fill 列撑不开、"持有"贴不到右缘，
        // 名称/产出被挤到换行（2026-09-23 截图审计实锤）。改为铺满按钮，行内左中右三段才成立。
        if(auto* RowSlot=Cast<UButtonSlot>(Content->Slot)){RowSlot->SetPadding(FMargin(0));
            RowSlot->SetHorizontalAlignment(HAlign_Fill);RowSlot->SetVerticalAlignment(VAlign_Center);}
        const FString InputName=DefinitionName(Model,R.Input);
        const FString OutputName=DefinitionName(Model,R.Output);
        if(const FSlateBrush* Brush=IconFor(R.Input))
        {
            auto* IconSize=WidgetTree->ConstructWidget<USizeBox>();
            IconSize->SetWidthOverride(28/Scale);IconSize->SetHeightOverride(28/Scale);
            Content->AddChildToHorizontalBox(IconSize)->SetVerticalAlignment(VAlign_Center);
            auto* Icon=WidgetTree->ConstructWidget<UImage>();Icon->SetBrush(*Brush);IconSize->SetContent(Icon);
        }
        // 行结构＝图标｜名称＋产出（Fill 撑开）｜持有数（右对齐卡边）。
        // 之前没有 Fill 列，整簇内容居中、"持有 N"悬在半空——不对称的主因。
        auto* Names=WidgetTree->ConstructWidget<UVerticalBox>();
        auto* NamesSlot=Content->AddChildToHorizontalBox(Names);
        NamesSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
        NamesSlot->SetPadding(FMargin(10/Scale,0,0,0));
        Names->AddChildToVerticalBox(Text(FString::Printf(TEXT("%s ×%lld"),*InputName,R.InputCount),14,ColdSteelUI::TextPrimary,false,false,true));
        Names->AddChildToVerticalBox(Text(FString::Printf(TEXT("→ %s ×%lld · %g 秒"),*OutputName,R.OutputCount,R.Seconds),12,ColdSteelUI::TextSecondary,false,false,true));
        auto* Held=Text(FString::Printf(TEXT("持有 %lld"),Have),12,ColdSteelUI::TextTertiary,true);
        auto* HeldSlot=Content->AddChildToHorizontalBox(Held);
        HeldSlot->SetVerticalAlignment(VAlign_Center);
        HeldSlot->SetPadding(FMargin(8/Scale,0,0,0));
        // UButton::OnClicked 是动态无参委托：按工程先例（UVoxelBuildCardProxy）用代理携带配方 id。
        auto* Proxy=NewObject<UColdSteelSmeltingRowProxy>(this);
        Proxy->Panel=this;Proxy->Recipe=R.Id;
        Row->OnClicked.AddDynamic(Proxy,&UColdSteelSmeltingRowProxy::Clicked);
        RowProxies.Add(Proxy);
        Rows.Add({Row,Card,R.Id});
    }
    // 空态行随重建挂回（ClearChildren 只摘不毁，但它需要重新入面板）。
    if(Rows.IsEmpty())RowsBox->AddChild(RowsEmpty);
    RefreshSelection();
}

void UColdSteelSmeltingWidget::RefreshSelection()
{
    for(const FRow& Row:Rows)
    {
        auto* Card=Row.Card.Get();if(!Card)continue;
        const bool bSelected=Row.Recipe==SelectedRecipe;
        Card->SetBrush(ColdSteelUI::RoundedBrush(bSelected?ColdSteelUI::ButtonHover:ColdSteelUI::StatusCard,
            ColdSteelUI::CardRadius/Scale,bSelected?ColdSteelUI::Accent:ColdSteelUI::Border,bSelected?2.f/Scale:1.f/Scale));
    }
}

void UColdSteelSmeltingWidget::RefreshJob()
{
    if(!JobTitle||!System)return;
    if(bCampfire&&Campfire.IsValid()){RefreshCampfireJob();return;}
    AVoxelBuildWorld* W=World.Get();
    const FVoxelSmeltingJob* Job=W?W->FindSmelting(Cell):nullptr;
    const FColdSteelSmeltingRecipe* Recipe=Job?System->Find(Job->Recipe):nullptr;
    const bool bFurnace=W&&W->IsFuelStationAt(Cell);
    const bool bCasting=bFurnace&&!bCampfire&&System->HasCastingStation(W,Cell);
    // 列表区只在炉内空闲时开放（规划文档第 6 节：空闲=选料，冶炼中=进度，完成=取出）；
    // 任务中同一区域交给炉况视觉区（A），分区标题随列表一起收起，不留空标题。
    const bool bShowRows=(!Job||bCasting)&&bFurnace&&GetVisibility()!=ESlateVisibility::Collapsed;
    RowsScroll->SetVisibility(bShowRows?ESlateVisibility::Visible:ESlateVisibility::Collapsed);
    SectionTitle->SetVisibility(bShowRows?ESlateVisibility::Visible:ESlateVisibility::Collapsed);
    Showcase->SetVisibility(Job&&bFurnace&&!bCasting?ESlateVisibility::Visible:ESlateVisibility::Collapsed);
    if(!Job||!bFurnace)bWasDone=false;   // 出炉/拆炉复位完成沿，下次转完成仍会闪光

    // —— 批量步进行（2026-09-24 批量冶炼；v9 起上限受"每次投料"升级轴约束）：
    // 只在空闲选料态显示，上限＝min(持有÷单份投料, 批量轴×5)，兜底封顶 99。——
    BatchRow->SetVisibility(bShowRows?ESlateVisibility::Visible:ESlateVisibility::Collapsed);
    int64 MaxBatch=1;
    if(bShowRows&&!SelectedRecipe.IsNone())
        if(const auto* R=System->Find(SelectedRecipe);R&&Model&&W)
            MaxBatch=FMath::Clamp<int64>(FMath::Min<int64>(Model->CountMaterial(R->Input)/R->InputCount,
                UColdSteelSmeltingSystem::BatchCapFor(bCampfire?1:W->FurnaceUpgradeLevel(Cell,VoxelFurnaceAxisBatch))),1,99);
    Batch=FMath::Clamp<int64>(Batch,1,FMath::Max<int64>(1,MaxBatch));
    BatchText->SetText(FText::FromString(FString::Printf(TEXT("批量 ×%lld（最多 %lld）"),Batch,MaxBatch)));
    BatchMinus->SetIsEnabled(Batch>1);BatchPlus->SetIsEnabled(Batch<MaxBatch);
    if(auto* Cap=Cast<UTextBlock>(StartButton->GetContent()))
        Cap->SetText(FText::FromString(bCampfire?FString::Printf(TEXT("开始烧烤 ×%lld"),Batch)
            :(Batch>1?FString::Printf(TEXT("开始冶炼 ×%lld"),Batch):TEXT("开始冶炼"))));

    // —— 升级页签/弹层：有炉子上下文才存在；弹层打开时数字跟着数据走（复用 10Hz 节拍，不加定时器）。——
    UpgradeTab->SetVisibility(bFurnace&&!bCampfire?ESlateVisibility::Visible:ESlateVisibility::Collapsed);
    if(!bFurnace||bCampfire)bUpgradeOpen=false;
    if(UpgradeTabText)   // v11（用户"打开升级栏后替换为收回二字，点击收回＝关闭"）：收回态点页签走的就是 HandleUpgradeToggled 的关闭分支。
    {   const FText Want=FText::FromString(bUpgradeOpen?TEXT("收回"):TEXT("升级"));   // 横排两字
        if(!UpgradeTabText->GetText().EqualTo(Want))UpgradeTabText->SetText(Want);
        if(bTabVisualOpen!=bUpgradeOpen){bTabVisualOpen=bUpgradeOpen;ApplyUpgradeTabVisual();}   // v12：换色跟随所贴主体
    }
    // 弹层可见性/滑位由 NativeTick 的 FlyMotion 统一驱动（复制冶炼面板的开合动画，2026-09-24）。
    if(bUpgradeOpen&&bFurnace&&W)
    {   // v10：页签只刷"名称字重＋Lv"，选中样式走配方行同款（ButtonHover 底＋Accent 2px 细边）；
        // 效果与材料集中在下方详情带，字号按 §4 分档，纯数值走 JetBrains Mono。
        const int64 Held=Model?Model->CountMaterial(TEXT("ironIngot")):0;
        UpgSel=FMath::Clamp(UpgSel,0,2);
        for(int32 A=0;A<3;++A)
        {
            const bool bSel=A==UpgSel;
            if(UpgTabSurfs.IsValidIndex(A)&&UpgTabSurfs[A])UpgTabSurfs[A]->SetBrush(ColdSteelUI::RoundedBrush(
                bSel?ColdSteelUI::ButtonHover:ColdSteelUI::StatusCard,ColdSteelUI::CardRadius/Scale,
                bSel?ColdSteelUI::Accent:ColdSteelUI::Border,bSel?2.f/Scale:1.f/Scale));
            if(UpgTabNames.IsValidIndex(A)&&UpgTabNames[A])
                UpgTabNames[A]->SetFont(GunsmithUI::TextFont(14/Scale,bSel));   // §4：Medium＝选中项
            if(UpgTabLv.IsValidIndex(A)&&UpgTabLv[A])UpgTabLv[A]->SetText(FText::FromString(
                FString::Printf(TEXT("Lv.%d / %d"),W->FurnaceUpgradeLevel(Cell,A),VoxelFurnaceAxisMax(A))));
        }
        const int32 Lvl=W->FurnaceUpgradeLevel(Cell,UpgSel);
        const int32 AxisMax=VoxelFurnaceAxisMax(UpgSel);
        const bool bMax=Lvl>=AxisMax;
        FString Cur,Next;
        AxisValueText(UpgSel,Lvl,Cur);AxisValueText(UpgSel,Lvl+1,Next);
        if(FlyDetailName)FlyDetailName->SetText(FText::FromString(AxisNames[UpgSel]));
        if(FlyDetailLv)FlyDetailLv->SetText(FText::FromString(FString::Printf(TEXT("Lv.%d / %d"),Lvl,AxisMax)));
        if(FlyFx)
        {   FlyFx->SetText(FText::FromString(bMax?FString::Printf(TEXT("已满级 · 当前 %s"),*Cur)
                :FString::Printf(TEXT("%s → %s"),*Cur,*Next)));
            FlyFx->SetColorAndOpacity(bMax?ColdSteelUI::TextSecondary:ColdSteelUI::Success);   }
        const int64 Cost=UColdSteelSmeltingSystem::UpgradeCostFor(Lvl);
        if(FlyMatRow)FlyMatRow->SetVisibility(bMax?ESlateVisibility::Collapsed:ESlateVisibility::Visible);
        if(FlyNoMat)FlyNoMat->SetVisibility(bMax?ESlateVisibility::Visible:ESlateVisibility::Collapsed);
        if(!bMax)
        {
            if(FlyMatValue)
            {   FlyMatValue->SetText(FText::FromString(FString::Printf(TEXT("×%lld"),Cost)));
                FlyMatValue->SetColorAndOpacity(Held>=Cost?ColdSteelUI::TextPrimary:ColdSteelUI::Warning);   }
            if(FlyMatOwned)
            {   FlyMatOwned->SetText(FText::FromString(Held>=Cost?FString::Printf(TEXT("持有 %lld"),Held)
                    :FString::Printf(TEXT("持有 %lld · 还差 %lld"),Held,Cost-Held)));
                FlyMatOwned->SetColorAndOpacity(Held>=Cost?ColdSteelUI::TextSecondary:ColdSteelUI::Warning);   }
            if(FlyMatIcon)
            {   if(const FSlateBrush* B=IconFor(TEXT("ironIngot"))){FlyMatIcon->SetBrush(*B);FlyMatIcon->SetVisibility(ESlateVisibility::HitTestInvisible);}
                else FlyMatIcon->SetVisibility(ESlateVisibility::Collapsed);   }
        }
        if(FlyBtn)FlyBtn->SetIsEnabled(!bMax&&Held>=Cost);
        if(FlyBtnText)FlyBtnText->SetText(FText::FromString(
            bMax?TEXT("已满级"):Held>=Cost?TEXT("升级"):TEXT("铁锭不足")));
    }
    // 上段进度条＋下段燃料卡：有炉子上下文就常显（燃料独立于任务——空炉也能先添燃料）。
    SmeltSection->SetVisibility(bFurnace?ESlateVisibility::Visible:ESlateVisibility::Collapsed);
    FuelCard->SetVisibility(bFurnace?ESlateVisibility::Visible:ESlateVisibility::Collapsed);
    // —— 燃料卡（面板下段）：剩余燃料 + 添加燃料（每炉存料口径，取出产物不清燃料）——
    const FColdSteelSmeltingFuel& FC=System->FuelConfig();
    if(!FuelIcon->GetBrush().GetResourceObject())   // 燃料图标一次挂上（定义表启动即定，不再变）
    {
        if(const FSlateBrush* B=IconFor(FC.Item)){FuelIcon->SetBrush(*B);FuelIcon->SetVisibility(ESlateVisibility::HitTestInvisible);}
        else FuelIcon->SetVisibility(ESlateVisibility::Collapsed);
    }
    const double Fuel=bFurnace?W->FuelAt(Cell):0.0;
    const double Cap=bFurnace?System->FurnaceCapacity(W,Cell):FC.Capacity;   // v9：容量随燃料仓轴升级
    AnimFuelRatio=Cap>0?FMath::Clamp(static_cast<float>(Fuel/Cap),0.f,1.f):0.f;
    bFuelAlive=bFurnace&&Fuel>0;
    // 用户 2026-09-24：燃料区也要看到剩余时间——任务中显示"存料 vs 还需烧"直接对比，
    // 存料不够烧完就转 Warning 橙（要不要添柴一眼可判）；空闲/完成态维持"存料 · 上限"。
    // 2026-09-24 实时化整改：这里只校准锚点，文案由 PaintFuelLine 每帧外推＋变化门控写一次。
    const bool bJobRunning=Job&&bFurnace&&!System->IsDone(W,Cell);
    bCdRunning=bJobRunning&&(!bCasting||!System->CastingBlocked(W,*Job));
    // v8 语义（2026-09-24 用户定稿）：炉内有存料就在烧——外推门按"有料"开，
    // 空闲态"存料 X"同样逐秒走；任务中"还需烧"仍只在有任务时参与。
    bCdBurning=bFurnace&&Fuel>0;
    CdFuel=Fuel;
    CdNeed=bJobRunning?System->RemainingSeconds(W,Cell):0.0;
    CdStamp=FPlatformTime::Seconds();
    PaintFuelLine();
    AddFuelButton->SetIsEnabled(System->CanAddFuel(W,Cell));
    if(auto* Caption=Cast<UTextBlock>(AddFuelButton->GetContent()))
        Caption->SetText(FText::FromString(FString::Printf(TEXT("添加燃料 +%s"),*ReadableSeconds(FC.SecondsPerUnit))));
    if(!Job)
    {
        JobTitle->SetText(FText::FromString(bCampfire?(Fuel>0?TEXT("篝火燃烧中"):TEXT("篝火已熄灭")):TEXT("炉内空闲")));
        JobTitle->SetColorAndOpacity(ColdSteelUI::TextTertiary);
        if(const auto* R=SelectedRecipe.IsNone()?nullptr:System->Find(SelectedRecipe))
        {   // 预览＝批量投料/产出与预计秒数（含这座炉的等级提速）。
            const double Mul=W&&bFurnace&&!bCampfire?UColdSteelSmeltingSystem::SpeedMultiplier(W->FurnaceLevel(Cell)):1.0;
            JobDetail->SetText(FText::FromString(FString::Printf(TEXT("%s ×%lld → %s ×%lld · %g 秒"),
                *DefinitionName(Model,R->Input),R->InputCount*Batch,*DefinitionName(Model,R->Output),R->OutputCount*Batch,
                R->Seconds*Batch/Mul)));
        }
        else JobDetail->SetText(FText::FromString(bCampfire?TEXT("添加木材取暖；有燃料才推进烧烤，无燃料时保留进度。")
            :TEXT("从下方选择原料投料")));
        JobDetail->SetColorAndOpacity(ColdSteelUI::TextTertiary);
        AnimSmeltT=0;bBurning=false;
        JobTime->SetText(FText::FromString(bCampfire?(Fuel>0?TEXT("5 米内减耗生效"):TEXT("添柴后点燃"))
            :(Fuel>0?TEXT("待投料起火"):TEXT("未起火"))));
        JobTime->SetColorAndOpacity(ColdSteelUI::TextTertiary);
        CollectButton->SetVisibility(ESlateVisibility::Collapsed);
        CollectGlow->SetVisibility(ESlateVisibility::Collapsed);
        StartButton->SetVisibility(ESlateVisibility::Visible);
        StartButton->SetIsEnabled(!SelectedRecipe.IsNone());
        // 炉况卡图标＝选中配方的输入矿（C 锚点）；没选中就收起。
        if(const auto* R=SelectedRecipe.IsNone()?nullptr:System->Find(SelectedRecipe);
            R&&IconFor(R->Input)){JobIcon->SetBrush(*IconFor(R->Input));JobIcon->SetVisibility(ESlateVisibility::Visible);}
        else JobIcon->SetVisibility(ESlateVisibility::Collapsed);
    }
    else
    {
        const bool bDone=System->IsDone(W,Cell);
        const bool bBurn=System->IsBurning(W,Cell);
        const float T=System->Progress(W,Cell);
        AnimSmeltT=T;bBurning=bBurn&&!bDone;
        // 三态：完成（Success）｜燃烧（TextPrimary＋脉冲）｜停炉（Warning，等添燃料）。
        JobTitle->SetText(FText::FromString(bDone?(bCampfire?TEXT("烧烤完成"):TEXT("冶炼完成"))
            :bBurn?(bCampfire?TEXT("烧烤中"):TEXT("冶炼中")):TEXT("燃料耗尽")));
        JobTitle->SetColorAndOpacity(bDone?ColdSteelUI::Success:bBurn?ColdSteelUI::TextPrimary:ColdSteelUI::Warning);
        JobDetail->SetText(FText::FromString(Recipe
            ?FString::Printf(TEXT("%s ×%lld → %s ×%lld · %g 秒"),
                *DefinitionName(Model,Recipe->Input),Recipe->InputCount*FMath::Max<int64>(1,Job->BatchCount),
                *DefinitionName(Model,Recipe->Output),Recipe->OutputCount*FMath::Max<int64>(1,Job->BatchCount),
                System->JobTotalSeconds(W,*Job,*Recipe))
            :FString(TEXT("配方已下架，炉内矿料无法结算"))));
        JobDetail->SetColorAndOpacity(ColdSteelUI::TextSecondary);
        JobTime->SetVisibility(ESlateVisibility::Visible);
        JobTime->SetText(FText::FromString(bDone?TEXT("等待取出")
            :bBurn?FString::Printf(TEXT("剩余 %.1f 秒"),System->RemainingSeconds(W,Cell))
            :FString::Printf(TEXT("已停炉 · 剩余 %.1f 秒"),System->RemainingSeconds(W,Cell))));
        JobTime->SetColorAndOpacity(bBurn?ColdSteelUI::TextSecondary:ColdSteelUI::TextTertiary);
        CollectButton->SetVisibility(bDone?ESlateVisibility::Visible:ESlateVisibility::Collapsed);
        CollectGlow->SetVisibility(bDone?ESlateVisibility::Visible:ESlateVisibility::Collapsed);
        StartButton->SetVisibility(ESlateVisibility::Collapsed);
        // 炉况卡图标＝在炼的原料（C 锚点）。
        if(Recipe&&IconFor(Recipe->Input)){JobIcon->SetBrush(*IconFor(Recipe->Input));JobIcon->SetVisibility(ESlateVisibility::Visible);}
        else JobIcon->SetVisibility(ESlateVisibility::Collapsed);
        // A 视觉区：投料图标→产物图标＋状态光环＋小字（缺图只隐不塌，布局稳定）。
        if(Recipe)
        {
            if(const FSlateBrush* B=IconFor(Recipe->Input)){ShowInIcon->SetBrush(*B);ShowInIcon->SetVisibility(ESlateVisibility::Visible);}
            else ShowInIcon->SetVisibility(ESlateVisibility::Hidden);
            if(const FSlateBrush* B=IconFor(Recipe->Output)){ShowOutIcon->SetBrush(*B);ShowOutIcon->SetVisibility(ESlateVisibility::Visible);}
            else ShowOutIcon->SetVisibility(ESlateVisibility::Hidden);
            ShowCaption->SetText(FText::FromString(FString::Printf(TEXT("%s ×%lld · %s"),
                *DefinitionName(Model,Recipe->Output),Recipe->OutputCount*FMath::Max<int64>(1,Job->BatchCount),
                bDone?TEXT("出炉待取"):bBurn?(bCampfire?TEXT("烧烤中"):TEXT("冶炼中")):TEXT("停炉待燃"))));
            ShowCaption->SetColorAndOpacity(bDone?ColdSteelUI::Success:bBurn?ColdSteelUI::TextSecondary:ColdSteelUI::Warning);
            ShowRing->SetBrush(ColdSteelUI::RoundedBrush(FLinearColor::Transparent,12.f/Scale,
                bDone?ColdSteelUI::Success:bBurn?ColdSteelUI::Warning:ColdSteelUI::Border,1.5f/Scale));
        }
        // B2：只在"转完成"那一拍起一次扫条闪光。
        if(bDone&&!bWasDone)FlashT=0.f;
        bWasDone=bDone;
    }
    if(bCasting)
    {
        const bool bBuffered=Job&&Job->bCasting;
        const int64 Stored=bBuffered?System->CastingStored(*Job):0;
        const int32 Queued=bBuffered?Job->Queue.Num():0;
        const bool bBlocked=bBuffered&&System->CastingBlocked(W,*Job);
        const bool bActive=Recipe!=nullptr;
        const FString State=bBlocked?(Stored>=System->CastingCapacity?TEXT("成品架已满 · 等待领取"):TEXT("铸造台缺失 · 已暂停"))
            :!bActive?TEXT("连续冶炼 · 待投料"):Fuel<=0?TEXT("燃料耗尽 · 队列暂停"):TEXT("连续冶炼中");
        JobTitle->SetText(FText::FromString(State));
        JobTitle->SetColorAndOpacity(bBlocked||(bActive&&Fuel<=0)?ColdSteelUI::Warning:ColdSteelUI::TextPrimary);
        FString Detail=FString::Printf(TEXT("成品架 %lld / 60 · 待冶炼 %d / 8"),Stored,Queued);
        if(bBuffered)
        {
            FString Products;
            for(const auto& Product:Job->Products)
                Products+=(Products.IsEmpty()?TEXT(""):TEXT(" · "))+DefinitionName(Model,Product.Item)+FString::Printf(TEXT(" ×%lld"),Product.Count);
            if(!Products.IsEmpty())Detail+=TEXT("\n")+Products;
            if(bActive)Detail+=FString::Printf(TEXT("\n当前：%s %lld / %lld"),*DefinitionName(Model,Recipe->Output),Job->ProducedBatches,Job->BatchCount);
            FString QueueLine;
            for(const auto& Order:Job->Queue)
                if(const auto* QueuedRecipe=System->Find(Order.Recipe))
                    QueueLine+=(QueueLine.IsEmpty()?TEXT(""):TEXT(" → "))+DefinitionName(Model,QueuedRecipe->Output)+FString::Printf(TEXT(" ×%lld"),Order.Batch);
            if(!QueueLine.IsEmpty())Detail+=TEXT("\n队列：")+QueueLine;
        }
        if(Stored==0&&!bActive&&Queued==0)Detail+=TEXT("\n按轮出料，领取后可手动存入储物箱");
        JobDetail->SetText(FText::FromString(Detail));
        JobDetail->SetColorAndOpacity(ColdSteelUI::TextSecondary);
        JobTime->SetText(FText::FromString(bActive?FString::Printf(TEXT("本项剩余 %.1f 秒%s"),System->RemainingSeconds(W,Cell),bBlocked?TEXT(" · 已暂停"):TEXT("")):TEXT("等待下一项投料")));
        bBurning=bActive&&!bBlocked&&Fuel>0;
        CollectButton->SetVisibility(Stored>0?ESlateVisibility::Visible:ESlateVisibility::Collapsed);
        CollectGlow->SetVisibility(Stored>0?ESlateVisibility::Visible:ESlateVisibility::Collapsed);
        if(auto* Caption=Cast<UTextBlock>(CollectButton->GetContent()))Caption->SetText(FText::FromString(TEXT("领取成品（按背包空间）")));
        StartButton->SetVisibility(ESlateVisibility::Visible);
        StartButton->SetIsEnabled(!SelectedRecipe.IsNone()&&Queued<System->CastingQueueCapacity&&Fuel>0);
        if(auto* Caption=Cast<UTextBlock>(StartButton->GetContent()))Caption->SetText(FText::FromString(
            Queued>=System->CastingQueueCapacity?TEXT("待冶炼队列已满"):FString::Printf(TEXT("加入队列 ×%lld"),Batch)));
    }
    else if(auto* Caption=Cast<UTextBlock>(CollectButton->GetContent()))
        Caption->SetText(FText::FromString(bCampfire?TEXT("领取菜品"):TEXT("取出矿锭")));
    ColdSteelSmeltingPresentation::RefreshProgressBars(SmeltBar,FuelBar,AnimSmeltT,AnimFuelRatio,bBurning,bFuelAlive);
}


FString UColdSteelSmeltingWidget::DebugFuelLineText() const {return FuelTime?FuelTime->GetText().ToString():FString();}

void UColdSteelSmeltingWidget::PaintFuelLine()
{
    if(!FuelTime||!System)return;
    // 帧间纯挂钟外推：燃烧中存料与还需烧同步递减（1:1），停炉待燃/空闲就冻结在锚点。
    const double Now=FPlatformTime::Seconds();
    const double Elapsed=FMath::Max(0.0,Now-CdStamp);
    const double Fuel=bCdBurning?FMath::Max(0.0,CdFuel-Elapsed):CdFuel;
    const double Need=bCdBurning?FMath::Max(0.0,CdNeed-Elapsed):CdNeed;
    const int32 Branch=bCdRunning?1:0;
    const int32 FuelSec=FMath::CeilToInt32(Fuel),NeedSec=FMath::CeilToInt32(Need);
    if(Branch==CdLastBranch&&FuelSec==CdLastFuelSec&&(Branch==0||NeedSec==CdLastNeedSec))return;   // 显示没变：零写入
    CdLastBranch=Branch;CdLastFuelSec=FuelSec;CdLastNeedSec=NeedSec;
    if(bCdRunning)
    {
        FuelTime->SetText(FText::FromString(FString::Printf(TEXT("存料 %s · 还需烧 %s"),
            *ReadableSeconds(Fuel),*ReadableSeconds(Need))));
        FuelTime->SetColorAndOpacity(Fuel<Need?ColdSteelUI::Warning:ColdSteelUI::TextSecondary);
    }
    else
    {
        FuelTime->SetText(FText::FromString(FString::Printf(TEXT("%s · 上限 %s"),
            *ReadableSeconds(Fuel),*ReadableSeconds(bCampfire?System->FuelConfig().Capacity:System->FurnaceCapacity(World.Get(),Cell)))));   // v9：上限随燃料仓轴升级
        FuelTime->SetColorAndOpacity(Fuel>0?ColdSteelUI::TextSecondary:ColdSteelUI::TextTertiary);
    }
}

void UColdSteelSmeltingWidget::SetStatus(const FString& Line,bool bError)
{
    if(!StatusLine)return;
    StatusLine->SetText(FText::FromString(Line));
    StatusLine->SetColorAndOpacity(Line.IsEmpty()?ColdSteelUI::TextTertiary:bError?ColdSteelUI::Warning:ColdSteelUI::TextSecondary);
}

const FSlateBrush* UColdSteelSmeltingWidget::IconFor(const FString& Definition)
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
    Brush.ImageSize=FVector2D(256,256);Brush.DrawAs=ESlateBrushDrawType::Image;
    return &IconBrushes.Add(Definition,Brush);
}

void UColdSteelSmeltingWidget::HandleStart()
{
    if(bCampfire){SubmitCampfire(1);return;}
    if(SelectedRecipe.IsNone()||!World.IsValid()||!System)return;
    const FColdSteelSmeltingRecipe* R=System->Find(SelectedRecipe);
    if(!R){SetStatus(TEXT("该配方不存在"),true);return;}
    const FString InputName=DefinitionName(Model,R->Input);
    const double Mul=bCampfire?1.0:UColdSteelSmeltingSystem::SpeedMultiplier(World->FurnaceLevel(Cell));
    const double Seconds=R->Seconds*Batch/Mul;   // 与结算同一口径：批量÷等级速度
    const int64 SubmittedBatch=Batch;
    FString Reason;
    if(System->BeginSmelting(World.Get(),Cell,SelectedRecipe,Reason,Batch))
    {
        SelectedRecipe=NAME_None;
        RefreshRows();RefreshJob();
        SetStatus(System->HasCastingStation(World.Get(),Cell)
            ?FString::Printf(TEXT("已入队 %s ×%lld · 按顺序冶炼，满架时暂停"),*InputName,R->InputCount*SubmittedBatch)
            :FString::Printf(TEXT("已投料 %s ×%lld · 约 %g 秒后出炉"),*InputName,R->InputCount*SubmittedBatch,Seconds));
    }
    else SetStatus(Reason,true);
}

void UColdSteelSmeltingWidget::HandleBatchMinus()
{
    if(Batch>1){--Batch;RefreshJob();}
}

void UColdSteelSmeltingWidget::HandleBatchPlus()
{
    if(Batch<99){++Batch;RefreshJob();}   // RefreshJob 再按持有量夹一次，超了自动回弹
}

void UColdSteelSmeltingWidget::HandleUpgradeToggled()
{
    bUpgradeOpen=!bUpgradeOpen;RefreshJob();
}

void UColdSteelSmeltingWidget::HandleUpgradeClose()
{
    bUpgradeOpen=false;RefreshJob();
}

void UColdSteelSmeltingWidget::HandleUpgradeClicked()        {UpgradeAxis(UpgSel);}   // 详情带升级钮：升当前选中轴
void UColdSteelSmeltingWidget::HandleUpgradeFuelClicked()    {SelectUpgradeAxis(VoxelFurnaceAxisFuelCapacity);UpgradeAxis(VoxelFurnaceAxisFuelCapacity);}
void UColdSteelSmeltingWidget::HandleUpgradeBatchClicked()   {SelectUpgradeAxis(VoxelFurnaceAxisBatch);UpgradeAxis(VoxelFurnaceAxisBatch);}

void UColdSteelSmeltingWidget::SelectUpgradeAxis(int32 Axis)
{
    // 点击立即换详情，不等下一拍刷新。
    UpgSel=FMath::Clamp(Axis,0,2);RefreshJob();
}

void UColdSteelSmeltingWidget::DebugClickUpgradeTab(int32 Axis)
{
    if(UpgTabs.IsValidIndex(Axis)&&UpgTabs[Axis])UpgTabs[Axis]->OnClicked.Broadcast();
}

void UColdSteelSmeltingWidget::AxisValueText(int32 Axis,int32 Level,FString& Out) const
{
    if(!System){Out.Reset();return;}
    switch(Axis)
    {   case VoxelFurnaceAxisFuelCapacity:
            Out=FString::Printf(TEXT("%d 分钟"),FMath::RoundToInt32(System->FuelConfig().Capacity*FMath::Clamp(Level,1,VoxelFurnaceAxisMax(Axis))/60.0));break;
        case VoxelFurnaceAxisBatch:
            Out=FString::Printf(TEXT("×%lld"),UColdSteelSmeltingSystem::BatchCapFor(Level));break;
        default:
            Out=FString::Printf(TEXT("+%d%%"),FMath::RoundToInt32((UColdSteelSmeltingSystem::SpeedMultiplier(Level)-1)*100));break;   }
}

void UColdSteelSmeltingWidget::UpgradeAxis(int32 Axis)
{
    if(!World.IsValid()||!System)return;
    FString Reason;
    if(System->UpgradeFurnace(World.Get(),Cell,Reason,Axis))
    {   static const TCHAR* const AxisDone[3]={TEXT("冶炼提速了"),TEXT("燃料仓扩容了"),TEXT("每次投料上限提高了")};
        SetStatus(FString::Printf(TEXT("升级成功 · %s"),Axis>=0&&Axis<3?AxisDone[Axis]:AxisDone[0]),false);RefreshJob();   }
    else SetStatus(Reason,true);
}

void UColdSteelSmeltingWidget::HandleCollect()
{
    if(bCampfire){SubmitCampfire(2);return;}
    if(!World.IsValid()||!System)return;
    const FVoxelSmeltingJob* Job=World->FindSmelting(Cell);
    const FColdSteelSmeltingRecipe* R=Job?System->Find(Job->Recipe):nullptr;
    const FString OutputName=R?DefinitionName(Model,R->Output):FString();
    const int64 OutputCount=R&&Job?R->OutputCount*FMath::Max<int64>(1,Job->BatchCount):0;
    const bool bCasting=Job&&Job->bCasting;
    FString Reason;
    if(System->CollectSmelting(World.Get(),Cell,Reason))
    {
        RefreshRows();RefreshJob();
        SetStatus(bCasting?Reason:FString::Printf(TEXT("已取出 %s ×%lld"),*OutputName,OutputCount));
    }
    else SetStatus(Reason,true);
}

void UColdSteelSmeltingWidget::HandleAddFuel()
{
    if(bCampfire){SubmitCampfire(0);return;}
    if(!World.IsValid()||!System)return;
    FString Reason;
    if(System->AddFuel(World.Get(),Cell,Reason))
    {
        RefreshJob();
        SetStatus(FString::Printf(TEXT("已添加燃料 +%s"),*ReadableSeconds(System->FuelConfig().SecondsPerUnit)));
    }
    else SetStatus(Reason,true);
}

void UColdSteelSmeltingWidget::HandleClose()
{
    // 面板独立于背包：× 与 Esc 走同一个出口（HUD 的 CloseSmelting 幂等，重复调用安全）。
    if(HUD)HUD->CloseSmelting();
}

void UColdSteelSmeltingWidget::AnimateBars(float DeltaSeconds)
{
    if(!SmeltBar||!FuelBar)return;
    AnimTime+=FMath::Clamp(DeltaSeconds,0.f,.25f);   // 挂起/切窗口回来不跳相位
    const float Pulse=.5f+.5f*FMath::Sin(AnimTime*2.f*PI/1.1f);   // 脉冲周期 1.1s
    // 亮头/火星参照宽＝条控件缓存几何（单位系），与 percent 同源 → 永远贴在条内。
    const float SmeltBarW=FMath::Max(1.f,BarSize->GetCachedGeometry().GetLocalSize().X);
    SmeltFillPx=SmeltBarW*FMath::Clamp(AnimSmeltT,0.f,1.f);
    FuelFillPx=FMath::Max(1.f,FuelBarSize->GetCachedGeometry().GetLocalSize().X)*FMath::Clamp(bFuelAlive?AnimFuelRatio:0.f,0.f,1.f);
    // 冶炼条脉冲：燃烧时填充亮度在 0.90~1.24 间起伏（提亮封顶靠 sRGB 钳位），前沿亮头同步呼吸。
    if(bBurning)
    {
        const FLinearColor Base=SmeltingProgressColor(AnimSmeltT);
        const float Bright=.90f+.34f*Pulse;
        SmeltBar->SetFillColorAndOpacity(FLinearColor(Base.R*Bright,Base.G*Bright,Base.B*Bright));
        SmeltBar->SetPercent(FMath::Clamp(AnimSmeltT,0.f,1.f));   // 燃烧中每帧跟手（占比小步长肉眼无跳变）
    }
    if(Head)
    {
        const bool bShowHead=bBurning&&SmeltFillPx>1.f;
        Head->SetVisibility(bShowHead?ESlateVisibility::HitTestInvisible:ESlateVisibility::Collapsed);
        if(bShowHead)
        {
            Head->SetColorAndOpacity(FLinearColor(1.f,1.f,1.f,.22f+.5f*Pulse));
            const float HeadX=FMath::Max(0.f,SmeltFillPx-4.f/Scale);
            if(auto* HeadSlot=Cast<UCanvasPanelSlot>(Head->Slot))
            {
                HeadSlot->SetSize(FVector2D(7.f/Scale,12.f/Scale));
                HeadSlot->SetPosition(FVector2D(HeadX,0.f));
            }
            // B3 辉光：16px 软带垫在亮头后（左偏 4.5px），α 随同一脉冲。
            if(HeadGlow)
            {
                HeadGlow->SetVisibility(ESlateVisibility::HitTestInvisible);
                HeadGlow->SetColorAndOpacity(FLinearColor(1.f,1.f,1.f,.08f+.14f*Pulse));
                if(auto* GS=Cast<UCanvasPanelSlot>(HeadGlow->Slot))
                {GS->SetSize(FVector2D(16.f/Scale,12.f/Scale));GS->SetPosition(FVector2D(FMath::Max(0.f,HeadX-4.5f/Scale),0.f));}
            }
        }
        else if(HeadGlow)HeadGlow->SetVisibility(ESlateVisibility::Collapsed);
        // B4 刻度：每帧按条宽重摆（面板宽度会随抽屉变化，刻线必须跟着 25/50/75% 走）。
        for(int32 i=0;i<BarTicks.Num();++i)if(auto* T=BarTicks[i].Get())
            if(auto* S=Cast<UCanvasPanelSlot>(T->Slot))
            {S->SetSize(FVector2D(1.f/Scale,12.f/Scale));S->SetPosition(FVector2D((i+1)*.25f*SmeltBarW-.5f/Scale,0.f));}
    }
    // 燃料条火星：沿填充区从左向右漂的小暖粒，上下轻摆＋闪烁，流向头部逐渐冷却；
    // 只在有存料时激活——停燃不画粒子，与"没油不推进"的语义一致。
    const bool bSparks=bFuelAlive&&FuelFillPx>2.f&&EmberImages.Num()==Embers.Num();
    const FLinearColor Amber=FLinearColor::FromSRGBColor(FColor(0xF1,0xC1,0x3F));
    for(int32 i=0;i<EmberImages.Num();++i)
    {
        UImage* Spark=EmberImages[i];if(!Spark)continue;
        if(!bSparks){Spark->SetColorAndOpacity(FLinearColor(1,1,1,0));continue;}
        FEmber& E=Embers[i];
        E.Phase+=E.Speed*DeltaSeconds;
        if(E.Phase>1.f){E.Phase-=1.f;E.Seed=FMath::FRand();}   // 回到尾部时换一颗新"火星"
        const float Sz=E.Size/Scale;
        const float Jitter=(2.4f/Scale)*FMath::Sin(2.f*PI*(E.Phase*1.7f+E.Seed));
        const float Flicker=.5f+.5f*FMath::Sin(3.f*(AnimTime*(2.2f+E.Speed*5.f)+E.Seed*9.f));
        const float Fade=1.f-.55f*E.Phase;
        const float Hot=.5f+.5f*FMath::Sin(E.Seed*17.f);       // 每颗固定的琥珀↔白偏色
        const FLinearColor Base=Amber*(1.f-.5f*Hot)+FLinearColor::White*(.5f*Hot);
        Spark->SetColorAndOpacity(FLinearColor(Base.R,Base.G,Base.B,(.18f+.62f*Flicker)*Fade));
        if(auto* SparkSlot=Cast<UCanvasPanelSlot>(Spark->Slot))
        {
            SparkSlot->SetSize(FVector2D(Sz,Sz));
            SparkSlot->SetPosition(FVector2D(E.Phase*FuelFillPx,(12.f/Scale-Sz)*.5f+Jitter));
        }
    }
    // B1 流动高光：燃烧时 8/20/8 三段亮带在填充区内往返（2.2s 一往返），位置数学钳制不越条。
    const float BandW=8.f/Scale,MainW=20.f/Scale,TotalW=2.f*BandW+MainW;
    const bool bSweep=bBurning&&SmeltFillPx>TotalW+2.f;
    float SweepX=0.f;
    if(bSweep)
    {   const float Ph=FMath::Frac(AnimTime/2.2f);
        const float Tri=Ph<.5f?Ph*2.f:(1.f-Ph)*2.f;
        SweepX=FMath::Lerp(0.f,SmeltFillPx-TotalW,Tri);}
    auto PlaceBand=[&](UImage* B,float OffX,float W)
    {
        if(!B)return;
        if(!bSweep){B->SetVisibility(ESlateVisibility::Collapsed);return;}
        B->SetVisibility(ESlateVisibility::HitTestInvisible);
        if(auto* S=Cast<UCanvasPanelSlot>(B->Slot)){S->SetSize(FVector2D(W,12.f/Scale));S->SetPosition(FVector2D(SweepX+OffX,0.f));}
    };
    PlaceBand(SweepA,0.f,BandW);PlaceBand(SweepB,BandW,MainW);PlaceBand(SweepC,BandW+MainW,BandW);
    // B2 完成闪光：一条宽带 0.55s 扫满条并淡出（一次性，扫完自动收起）。
    if(FlashT>=0.f)
    {
        FlashT+=FMath::Clamp(DeltaSeconds,0.f,.25f)/0.55f;
        const float W=26.f/Scale;
        if(FlashT<1.f&&SmeltFillPx>W)
        {
            FlashBand->SetVisibility(ESlateVisibility::HitTestInvisible);
            FlashBand->SetColorAndOpacity(FLinearColor(1,1,1,(1.f-FlashT)*.5f));
            const float X=FMath::Clamp(FlashT*(SmeltFillPx+W)-W,0.f,SmeltFillPx-W);
            if(auto* S=Cast<UCanvasPanelSlot>(FlashBand->Slot)){S->SetSize(FVector2D(W,12.f/Scale));S->SetPosition(FVector2D(X,0.f));}
        }
        else FlashBand->SetVisibility(ESlateVisibility::Collapsed);
        if(FlashT>=1.f)FlashT=-1.f;
    }
    // A/C 呼吸：光环完成态 1.8s 慢呼吸（栏目脉冲先例）、燃烧与条脉冲同步 1.1s、停炉静止低亮；
    // 取出按钮描边随完成态绿色呼吸。都只改 tint，不重绘数据。
    if(ShowRing&&ShowRing->GetVisibility()!=ESlateVisibility::Collapsed)
    {
        const float Breath=.5f+.5f*FMath::Sin(AnimTime*2.f*PI/(bWasDone?1.8f:1.1f));
        ShowRing->SetBrushColor(FLinearColor(1,1,1,bWasDone?.45f+.55f*Breath:bBurning?.3f+.6f*Breath:.35f));
    }
    if(CollectGlow&&CollectGlow->GetVisibility()!=ESlateVisibility::Collapsed)
        CollectGlow->SetBrushColor(FLinearColor(1,1,1,.4f+.6f*(.5f+.5f*FMath::Sin(AnimTime*2.f*PI/1.8f))));
}
