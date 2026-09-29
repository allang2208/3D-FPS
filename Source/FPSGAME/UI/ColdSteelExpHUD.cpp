#include "ColdSteelHUDWidget.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelUIStyle.h"
#include "Blueprint/UserWidget.h"
#include "Blueprint/WidgetTree.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/ProgressBar.h"
#include "Styling/SlateTypes.h"

// 底部经验条（2026-09-29 用户需求）：形式取原项目 game-dev 的贴底全宽 6px 金色经验条
// （src/ui/panels/hud-panels-misc.js + game-style.css .exp-bar-container/.exp-bar-fill：
// 轨道半透明黑、金色填充、贴屏幕底缘）。冷钢化：填充色走 HUDGold 语义色（HUD 装饰金，
// 设计系统 §2），轨道保持原版的 rgba(0,0,0,.5)；高度按 PixelScale 反算 6 物理像素。
// 数据与人物状态页同源：StatusModel->Experience()/MaxExperience()（升级消耗制，条内为
// 当前等级内进度）。RefreshStatus 每次刷新同步，杀怪到账在 HUD 上直接可见。
void UColdSteelHUDWidget::BuildExpBar(UCanvasPanel* Root)
{
    if (!Root) return;
    ExperienceBar = WidgetTree->ConstructWidget<UProgressBar>(UProgressBar::StaticClass(), TEXT("BottomExpBar"));
    ExperienceBar->SetVisibility(ESlateVisibility::HitTestInvisible);
    ExperienceBar->SetFillColorAndOpacity(ColdSteelUI::HUDGold);
    // 轨道走样式画刷（UE5.8 的 UProgressBar 无 SetBackgroundColor）：半透明黑，对齐原版。
    FProgressBarStyle BarStyle;
    BarStyle.BackgroundImage = FSlateColorBrush(FLinearColor(0.f, 0.f, 0.f, .5f));
    BarStyle.FillImage = FSlateColorBrush(FLinearColor::White);
    ExperienceBar->SetWidgetStyle(BarStyle);
    ExperienceBar->SetPercent(0.f);
    UCanvasPanelSlot* ExpSlot = Root->AddChildToCanvas(ExperienceBar);
    // UMG 画布槽语义（SConstraintCanvas：锚点同侧不拉伸时尺寸=Offset.Right/Bottom）：
    // 底部条 = 锚点 (0,1)-(1,1) + offsets (0,−H, 0, +H)：Top 定位到屏幕底缘上方 H，Bottom 即高度。
    const float BarHeight = 6.f / ColdSteelUI::PixelScale(this);
    ExpSlot->SetAnchors(FAnchors(0.f, 1.f, 1.f, 1.f));
    ExpSlot->SetOffsets(FMargin(0.f, -BarHeight, 0.f, BarHeight));
    ExpSlot->SetZOrder(1);
    RefreshExpBar();
}

void UColdSteelHUDWidget::RefreshExpBar()
{
    if (!ExperienceBar) return;
    if (!StatusModel) return;
    const int64 Need = StatusModel->MaxExperience();
    const int64 Have = StatusModel->Experience();
    const float Percent = Need > 0
        ? FMath::Clamp(static_cast<float>(static_cast<double>(Have) / static_cast<double>(Need)), 0.f, 1.f)
        : 0.f;
    // 低频 Tick 每次都进来：值没变不写 SetPercent，避免无谓的布局失效。
    if (!FMath::IsNearlyEqual(Percent, ExperienceBar->GetPercent()))
        ExperienceBar->SetPercent(Percent);
}
