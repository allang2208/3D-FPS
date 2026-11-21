// Source/FPSGAME/Building/VoxelBuildWidgetLayout.cpp
// Merge each excerpt at the named target and scope. Line numbers locate the 2026-11-21 production source.

// Lines 5-5 | file scope
#include "VillageBuildDefense.h"

// Lines 78-80 | void UVoxelBuildWidget::NativeOnInitialized()
    auto* HintFit=WidgetTree->ConstructWidget<UScaleBox>();
    HintFit->SetStretch(EStretch::ScaleToFit);
    HintFit->SetStretchDirection(EStretchDirection::DownOnly);

// Lines 82-84 | void UVoxelBuildWidget::NativeOnInitialized()
    HeaderHints=WidgetTree->ConstructWidget<UHorizontalBox>();
    HintFit->SetContent(HeaderHints);
    CastChecked<UScaleBoxSlot>(HeaderHints->Slot)->SetHorizontalAlignment(HAlign_Left);

// Lines 90-90 | void UVoxelBuildWidget::NativeOnInitialized()
        HeaderHints->AddChildToHorizontalBox(Label)->SetVerticalAlignment(VAlign_Center);

// Lines 100-101 | void UVoxelBuildWidget::NativeOnInitialized()
    Selection=Text(TEXT(""),14);Selection->SetAutoWrapText(false);
    Selection->SetTextOverflowPolicy(ETextOverflowPolicy::Ellipsis);

// Lines 115-115 | void UVoxelBuildWidget::NativeOnInitialized()
    MaterialTab=Tab(TEXT("材质"));VillageTab=Tab(TEXT("村庄建筑"));ComponentTab=Tab(TEXT("其他"));

// Lines 117-117 | void UVoxelBuildWidget::NativeOnInitialized()
    VillageTab->OnClicked.AddDynamic(this,&ThisClass::ShowVillageCategory);

// Lines 122-123 | void UVoxelBuildWidget::NativeOnInitialized()
    VillageTabLabel=Cast<UTextBlock>(VillageTab->GetContent());
    for(UButton* Entry:{MaterialTab.Get(),VillageTab.Get(),ComponentTab.Get()})

// Lines 178-178 | void UVoxelBuildWidget::AddGridCard(UWrapBox* Grid,const FVoxelBuildPanelCard& Entry,FName MaterialId,bool bChild,
    const bool bLocked=VillageBuildDefense::IsVillageRecipe(Entry.Id)&&!bVillageConstructionUnlocked;

// Lines 392-395 | void UVoxelBuildWidget::RebuildCards()
    const bool bVillage=Category==ECategory::Village;
    if(bVillage&&!bVillageConstructionUnlocked)
    {
        auto* Hint=Text(TEXT("前往丘陵村庄，在修女处解锁「村庄修建」后可建造。"),14);

// Lines 402-402 | void UVoxelBuildWidget::RebuildCards()
        if(bVillage==VillageBuildDefense::IsVillageRecipe(Entry.Id)&&(bVillage||Entry.MaterialId.IsNone()))

// Lines 406-406 | void UVoxelBuildWidget::RebuildCards()
        auto* Empty=Text(bVillage?TEXT("暂无可用村庄构件"):TEXT("暂无其他构件 · 已分类构件可在对应材质的「其他构造」中选择"),14);
