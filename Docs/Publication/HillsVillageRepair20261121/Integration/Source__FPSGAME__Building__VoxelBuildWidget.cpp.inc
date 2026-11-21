// Source/FPSGAME/Building/VoxelBuildWidget.cpp
// Merge each excerpt at the named target and scope. Line numbers locate the 2026-11-21 production source.

// Lines 4-4 | file scope
#include "VillageBuildDefense.h"

// Lines 255-260 | void UVoxelBuildWidget::SetVillageConstructionUnlocked(bool bUnlocked)
void UVoxelBuildWidget::SetVillageConstructionUnlocked(bool bUnlocked)
{
    if(bVillageConstructionUnlocked==bUnlocked)return;
    bVillageConstructionUnlocked=bUnlocked;
    if(Category==ECategory::Village)bCardsDirty=true;
}

// Lines 313-313 | void UVoxelBuildWidget::ShowVillageCategory(){if(Category!=ECategory::Village){Category=ECategory::Village;bCardsDirty=true;}}
void UVoxelBuildWidget::ShowVillageCategory(){if(Category!=ECategory::Village){Category=ECategory::Village;bCardsDirty=true;}}

// Lines 408-408 | void UVoxelBuildWidget::RefreshCategory()
    if(VillageTab)VillageTab->SetStyle(Category==ECategory::Village?Selected:Normal);

// Lines 415-415 | void UVoxelBuildWidget::RefreshCategory()
    ApplyTabFont(VillageTabLabel.Get(),Category==ECategory::Village,Scale);

// Lines 456-456 | void UVoxelBuildWidget::RefreshLayout()
    for(UButton* TabButton:{MaterialTab.Get(),VillageTab.Get(),ComponentTab.Get()})if(TabButton)

// Lines 532-534 | void UVoxelBuildWidget::ShowState(const FString& Headline,const FString& Brush,const FString& Message,bool bValid,bool bSnapEnabled,
    const TCHAR* Snap=VillageWallStairs::CanDock(SelectedComponent)
        ? (bSnapEnabled?TEXT("地面每格 1° · 吸附时滚轮换接法 · F 关闭吸附"):TEXT("地面每格 1° · R 转 90° · F 开启吸附"))
        : VillageBuildDefense::IsBasicWallOrGate(SelectedComponent)

// Lines 536-536 | void UVoxelBuildWidget::ShowState(const FString& Headline,const FString& Brush,const FString& Message,bool bValid,bool bSnapEnabled,
        : (bSnapEnabled?TEXT("体素吸附已开启 · F 自由放置"):TEXT("自由位置 · F 开启体素吸附"));
