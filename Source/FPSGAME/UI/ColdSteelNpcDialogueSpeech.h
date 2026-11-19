#pragma once

#include "CoreMinimal.h"
#include "Widgets/DeclarativeSyntaxSupport.h"
#include "Widgets/SCompoundWidget.h"

class SBox;
class STextBlock;

struct FColdSteelSpokenPassage
{
    FString Text;
    FString Heading;
    TSharedPtr<SWidget> Illustration;
};

/** Plays the authored passages in order, keeping one spoken sentence on screen. */
class SColdSteelNpcSpeech : public SCompoundWidget
{
public:
    SLATE_BEGIN_ARGS(SColdSteelNpcSpeech) {}
        SLATE_ARGUMENT(TArray<FColdSteelSpokenPassage>, Passages)
        SLATE_EVENT(FSimpleDelegate, OnFinished)
    SLATE_END_ARGS()

    void Construct(const FArguments& Args);
    bool IsRevealing() const { return VisibleCharacters < CharacterEnds.Num(); }
    bool HasMore() const { return IsRevealing() || Lines.IsValidIndex(Line + 1); }
    bool RevealOrAdvance();
    void Stop();

private:
    struct FLine
    {
        FString Text;
        int32 Passage;
    };
    TArray<FColdSteelSpokenPassage> Passages;
    TArray<FLine> Lines;
    TArray<int32> CharacterEnds;
    int32 Line = INDEX_NONE;
    int32 VisibleCharacters = 0;
    double StartedAt = 0., NextLineAt = 0.;
    TSharedPtr<STextBlock> Heading, FullSentence, SpokenText;
    TSharedPtr<SBox> Illustration;
    TWeakPtr<FActiveTimerHandle> Playback;
    FSimpleDelegate OnFinished;

    void StartLine(int32 Index, double Now);
    void Reveal(int32 Count, double Now);
    EActiveTimerReturnType TickPlayback(double Now, float Delta);
};
