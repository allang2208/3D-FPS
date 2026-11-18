#pragma once
#include "Components/ScrollBox.h"
#include "Components/WrapBox.h"
#include "Components/VerticalBoxSlot.h"
namespace VoxelBuildWidgetLayoutPrivate
{
    inline constexpr float HeaderHeight=36.f,CardHeight=44.f,CardGap=4.f;
    // 指针离浮窗边缘在这个屏幕像素余量内就保持浮窗打开（含指针从卡片移向关闭按钮的路径）。
    inline constexpr float TooltipKeepMarginPixels=44.f;
    // 浮窗显示后跟随鼠标这么久就钉住位置：跟随阶段浮窗永远在光标外 10px，关闭按钮够不到；
    // 钉住后玩家能移到浮窗上点 ×（2026-09-19 审计）。
    inline constexpr float TooltipFollowSeconds=.7f;
    // Material rows carry the 其他构造 disclosure; its submenu rows are indented underneath.
    inline constexpr float ChildIndent=14.f,DisclosureWidth=96.f,DisclosureHeight=26.f;
    // 其他构造 grid: one identical card per construction, equal gaps, wrapping when a row is full.
    inline constexpr float GridGap=8.f,GridCardWidth=116.f,GridCardMinHeight=170.f,GridIconPixels=104.f;
    inline constexpr float GridCardPadding=5.f,GridNameInset=2.f;
    inline constexpr float GridNameWidth=GridCardWidth-2.f*(GridCardPadding+GridNameInset);
    /** 材质行左侧缩略图；DPI/视口变化时按此重算，不跟网格卡的 104px 混用。 */
    inline constexpr float MaterialThumbPixels=28.f;
    inline constexpr float DrawerViewportFraction=.48f,DrawerMinWidth=720.f,DrawerMaxWidth=1040.f,DrawerEdgeInset=12.f;
    inline constexpr float DrawerBorderInset=1.f,BuildScrollLeft=18.f,BuildScrollRight=12.f,BuildScrollbarWidth=6.f;

    inline void ConfigureBuildScroll(UScrollBox* ScrollBox,float Scale)
    {
        // Reserve the same gutter before and after a material expansion needs scrolling.
        ScrollBox->SetAlwaysShowScrollbar(true);
        ScrollBox->SetScrollbarPadding(FMargin(0));
        ScrollBox->SetScrollbarThickness(FVector2D(BuildScrollbarWidth/Scale));
        FScrollBoxStyle ScrollStyle=ScrollBox->GetWidgetStyle();
        ScrollStyle.SetVerticalScrolledContentPadding(FMargin(0));
        ScrollBox->SetWidgetStyle(ScrollStyle);
        // The track brushes also contribute desired width; thickness alone does not constrain them.
        FScrollBarStyle BarStyle=ScrollBox->GetWidgetBarStyle();
        BarStyle.VerticalTopSlotImage.SetImageSize(FVector2D(BuildScrollbarWidth/Scale,BarStyle.VerticalTopSlotImage.GetImageSize().Y));
        BarStyle.VerticalBottomSlotImage.SetImageSize(FVector2D(BuildScrollbarWidth/Scale,BarStyle.VerticalBottomSlotImage.GetImageSize().Y));
        ScrollBox->SetWidgetBarStyle(BarStyle);
    }

    inline void ConfigureBuildGrid(UWrapBox* Grid,float DrawerWidth,float Scale,bool bIndented)
    {
        const float Indent=bIndented?ChildIndent:0.f;
        const float AvailableWidth=DrawerWidth-(2.f*DrawerBorderInset+BuildScrollLeft+BuildScrollRight+BuildScrollbarWidth+Indent)/Scale;
        // Recreated grids must not start from UWrapBox's default 500-unit preferred width.
        Grid->SetExplicitWrapSize(true);
        Grid->SetWrapSize(FMath::Max(GridCardWidth/Scale,AvailableWidth));
        Grid->SetInnerSlotPadding(FVector2D(GridGap/Scale,GridGap/Scale));
        if(auto* GridSlot=Cast<UVerticalBoxSlot>(Grid->Slot))
            GridSlot->SetPadding(FMargin(Indent/Scale,bIndented?0.f:2.f/Scale,0,GridGap/Scale));
    }
}
