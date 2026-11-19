#pragma once
#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "SColdSteelSkillTreeCanvas.h"
#include "ColdSteelTreePanel.h"
#include "ColdSteelSkillTreeScreen.generated.h"
class UColdSteelStatusModel;
class UColdSteelHUDWidget;
class UTexture2D;
class SBox;
class SScrollBox;
class SVerticalBox;

/** Full-screen skill tree opened with P (2026-11-15). Plan: Docs/UI/skill-tree-plan-20261115.md.
    Grid + routing follow game-dev's technology tree; learning is free once requirements are met;
    specialization pages (fireball, elemental arrow) use the same grid. */
UCLASS()
class FPSGAME_API UColdSteelSkillTreeScreen : public UUserWidget
{
    GENERATED_BODY()
public:
    void SetHUD(UColdSteelHUDWidget* Owner);
    void Select(FName Skill);
protected:
    virtual TSharedRef<SWidget> RebuildWidget() override;
    virtual void ReleaseSlateResources(bool bReleaseChildren) override;
    virtual void NativeConstruct() override;
    virtual void NativeDestruct() override;
    /** Rebuilds the detail column when DetailWidth() changes (window resize while the tree is open). */
    virtual void NativeTick(const FGeometry& Geometry, float Delta) override;
    virtual FReply NativeOnKeyDown(const FGeometry& Geometry, const FKeyEvent& Event) override;
    virtual FReply NativeOnPreviewMouseButtonDown(const FGeometry& Geometry, const FPointerEvent& Event) override;
    virtual FReply NativeOnMouseButtonUp(const FGeometry& Geometry, const FPointerEvent& Event) override;
    virtual void NativeOnDragDetected(const FGeometry& Geometry, const FPointerEvent& Event, UDragDropOperation*& Out) override;
    virtual bool NativeOnDrop(const FGeometry& Geometry, const FDragDropEvent& Event, UDragDropOperation* Operation) override;
private:
    TWeakObjectPtr<UColdSteelHUDWidget> HUD;
    UPROPERTY(Transient) TObjectPtr<UColdSteelStatusModel> Model;
    /** Top notices (learn / unlock / spec) drawn above this screen; the HUD copy is collapsed meanwhile. */
    UPROPERTY(Transient) TObjectPtr<class UColdSteelProgressNotification> Notices;
    UPROPERTY(Transient) TMap<FString, TObjectPtr<UTexture2D>> IconTextures;
    /** Quickbar strip (same UColdSteelQuickSlot as the HUD hotbar) and the staff magic-wheel configuration. */
    UPROPERTY(Transient) TArray<TObjectPtr<class UColdSteelQuickSlot>> StripSlots;
    UPROPERTY(Transient) TObjectPtr<class UColdSteelMagicWheel> WheelConfig;
    /** Former skill page in embedded mode: per-skill description, 技能收益 current/next values, 修炼方式. */
    UPROPERTY(Transient) TObjectPtr<class UColdSteelSkillPage> DetailPage;
    TSharedPtr<SWidget> WheelPanel;
    FName PendingDrag;
    bool bWheelOpen = false;
    TMap<FString, TSharedPtr<FSlateBrush>> IconBrushes;
    TSharedPtr<SColdSteelSkillTreeCanvas> TreeCanvas, SpecCanvas;
    TSharedPtr<SBox> TreePage, SpecPage, DetailHost, SpecPreview;
    FName Group = NAME_None, Selected = TEXT("fireball"), SpecSkill, SpecNode;
    FString Query;
    bool bSpec = false;
    /** Why the last 免费习得 / 投入 click failed (model message); shown in the footer until the selection changes. */
    FString ActionError;
    /** DetailWidth() the current detail column was built for. */
    float BuiltDetailWidth = 0.f;
    FDelegateHandle ChangedHandle;
    ColdSteelTreePanel::FStyle TreeStyle;
    FSlateBrush SlotBrush, KeyChip, KeyChipOn, KeyChipEmpty, GoldDot;

    // layout & data (ColdSteelSkillTreeSources.cpp)
    TArray<ColdSteelSkillTreeLayout::FRow> TreeRows() const;
    TArray<ColdSteelSkillTreeLayout::FRow> SpecRows(FName Skill) const;
    SColdSteelSkillTreeCanvas::FSource TreeSource() const;
    SColdSteelSkillTreeCanvas::FSource SpecSource() const;
    SColdSteelSkillTreeCanvas::EStatus SkillStatus(FName Id) const;
    TSet<FName> TreePath(FName Id) const;
    FString SkillName(FName Id) const;
    FString RequirementText(const ColdSteelSkillTree::FRequirement& R, bool bSpecPage) const;
    const FSlateBrush* Icon(const FString& Path);
    FLinearColor ToneColor(const FString& Tone) const;

    // detail column (ColdSteelSkillTreeDetail.cpp)
    /** Raw-pixel width of the right column: 40% of the viewport, 480–760 px (2026-11-17 doubled from 380). */
    float DetailWidth() const;
    TSharedRef<SWidget> BuildSkillDetail();
    TSharedRef<SWidget> BuildSpecDetail();
    TSharedRef<SWidget> BuildSpecPreview();
    void ShowDetail();
    TSharedRef<SWidget> Section(const FString& Title, const FString& Count, TSharedRef<SWidget> Body) const;
    TSharedRef<SWidget> Requirement(const ColdSteelSkillTree::FRequirement& R, bool bSpecPage);
    TSharedRef<SWidget> Label(const FString& Text, float Px, const FLinearColor& Color, bool bMedium = false, bool bWrap = false) const;

    // shell (ColdSteelSkillTreeScreen.cpp)
    TSharedRef<SWidget> BuildHeader();
    TSharedRef<SWidget> BuildLegend();
    TSharedRef<SWidget> BuildSpecPage();
    TSharedRef<SWidget> BuildQuickStrip();
    TSharedRef<SWidget> BuildWheelPanel();
    void ToggleWheel(bool bOpen);
    void Relayout();
    void RefreshAll();
    void OpenSpec(FName Skill);
    void CloseSpec();
    void SelectSpecNode(FName Node);
    void Close();
};
