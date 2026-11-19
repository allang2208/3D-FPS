#pragma once
#include "CoreMinimal.h"
#include "Styling/SlateTypes.h"
#include "Widgets/SWidget.h"

class UUserWidget;
class SColdSteelSkillTreeCanvas;

/** The skill screen and village tree use the same Slate chrome and detail controls. */
namespace ColdSteelTreePanel
{
    struct FStyle
    {
        FSlateBrush GlassBrush, FallbackBrush, BarBrush, CardBrush, RowBrush, RowMetBrush, ChipBrush, GlyphBrush, TabLine;
        FButtonStyle Quiet, Muted, Primary;
        void Initialize();
    };
    struct FTab { FName Id; FString Caption; };
    struct FHeader
    {
        FString Title, SearchHint, CloseKey;
        TAttribute<FText> Breadcrumb, Summary;
        TFunction<void(const FText&)> OnSearch;
        TFunction<void()> OnClose;
    };
    float DetailWidth(const UUserWidget* Owner);
    TSharedRef<SWidget> Label(const FString& Text, float Px, const FLinearColor& Color, bool Medium = false, bool Wrap = false);
    TSharedRef<SWidget> Section(const FString& Title, const FString& Count, TSharedRef<SWidget> Body);
    TSharedRef<SWidget> Frame(UUserWidget* Owner, const FStyle& Style, TSharedRef<SWidget> Header, TSharedRef<SWidget> Main, TSharedRef<SWidget> Detail);
    TSharedRef<SWidget> Tabs(const FStyle& Style, const TArray<FTab>& Items, TAttribute<FName> Selected, TAttribute<bool> ShowLine, TFunction<void(FName)> OnSelect);
    TSharedRef<SWidget> Header(const FStyle& Style, const FHeader& Data, TSharedRef<SWidget> Tabs, TSharedRef<SWidget> Extra);
    TSharedRef<SWidget> Legend(const FStyle& Style, TWeakPtr<SColdSteelSkillTreeCanvas> Canvas, const FString& ItemName);
    TSharedRef<SWidget> DetailHead(const FStyle& Style, TSharedRef<SWidget> Icon, const FString& Breadcrumb, const FString& Title, const FString& Tag);
    TSharedRef<SWidget> Progress(const FStyle& Style, const FString& State, const FString& Value, const FString& Note, float Fill, const FLinearColor& StateColor, const FLinearColor& FillColor);
    TSharedRef<SWidget> Action(const FString& Caption, const FButtonStyle* Style, bool Enabled, TFunction<void()> OnClick, const FLinearColor& Color, bool Medium);
    TSharedRef<SWidget> DetailPage(TSharedRef<SWidget> Body, TSharedRef<SWidget> Actions, TSharedRef<SWidget> Note, float NoteGap = 8.f);
}
