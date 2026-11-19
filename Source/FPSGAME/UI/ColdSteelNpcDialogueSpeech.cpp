#include "ColdSteelNpcDialogueSpeech.h"
#include "ColdSteelUIStyle.h"
#include "Framework/Application/SlateApplication.h"
#include "Internationalization/BreakIterator.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/SNullWidget.h"
#include "Widgets/SOverlay.h"
#include "Widgets/Text/STextBlock.h"

namespace
{
constexpr double SecondsPerCharacter = .040;

bool EndsSentence(TCHAR Ch)
{
    return FCString::Strchr(TEXT("。！？!?；;"), Ch) != nullptr;
}

bool EndsQuotation(TCHAR Ch)
{
    return FCString::Strchr(TEXT("”’」』）)】"), Ch) != nullptr;
}
}

void SColdSteelNpcSpeech::Construct(const FArguments& Args)
{
    Passages = Args._Passages;
    OnFinished = Args._OnFinished;
    for (int32 Section = 0; Section < Passages.Num(); ++Section)
    {
        const FString& Source = Passages[Section].Text;
        int32 Begin = 0;
        for (int32 Index = 0; Index < Source.Len(); ++Index)
        {
            const TCHAR Ch = Source[Index];
            const bool bPeriod = Ch == TEXT('.') && !(Index + 1 < Source.Len() && FChar::IsDigit(Source[Index + 1]));
            if (!EndsSentence(Ch) && !bPeriod && Ch != TEXT('\n') && Index + 1 < Source.Len()) continue;
            while (Index + 1 < Source.Len() && (EndsQuotation(Source[Index + 1]) || EndsSentence(Source[Index + 1])))
                ++Index;
            FString Sentence = Source.Mid(Begin, Index + 1 - Begin).TrimStartAndEnd();
            if (!Sentence.IsEmpty()) Lines.Add({MoveTemp(Sentence), Section});
            Begin = Index + 1;
        }
    }
    using namespace ColdSteelUI;
    const FSlateFontInfo SpeechFont = TextFont(15);
    constexpr float SpeechLineHeight = 1.35f;
    ChildSlot[SNew(SVerticalBox)
        + SVerticalBox::Slot().AutoHeight()
        [SAssignNew(Heading, STextBlock).Font(TextFont(12, true)).ColorAndOpacity(HUDGoldLight)]
        + SVerticalBox::Slot().AutoHeight().Padding(0, 4, 0, 0)
        [SNew(SBox).MaxDesiredWidth(1040)
            [SNew(SOverlay)
                // The full sentence supplies the wrapped height and screen-reader text throughout the reveal.
                + SOverlay::Slot()
                [SAssignNew(FullSentence, STextBlock).Visibility(EVisibility::HitTestInvisible).RenderOpacity(0.f)
                    .Font(SpeechFont).AutoWrapText(true).LineHeightPercentage(SpeechLineHeight)]
                + SOverlay::Slot()
                [SAssignNew(SpokenText, STextBlock)
                    .Font(SpeechFont).AutoWrapText(true).LineHeightPercentage(SpeechLineHeight)
                    .ColorAndOpacity(TextPrimary)
                    .AccessibleParams(FAccessibleWidgetData(EAccessibleBehavior::NotAccessible, EAccessibleBehavior::NotAccessible, false))]]]
        + SVerticalBox::Slot().AutoHeight()[SAssignNew(Illustration, SBox)]];
    if (Lines.IsEmpty()) return;
    StartLine(0, FSlateApplication::Get().GetCurrentTime());
    if (HasMore())
        Playback = RegisterActiveTimer(.025f, FWidgetActiveTimerDelegate::CreateSP(this, &SColdSteelNpcSpeech::TickPlayback));
}

void SColdSteelNpcSpeech::StartLine(int32 Index, double Now)
{
    const int32 OldPassage = Lines.IsValidIndex(Line) ? Lines[Line].Passage : INDEX_NONE;
    Line = Index;
    const FLine& Current = Lines[Line];
    if (OldPassage != Current.Passage)
    {
        const FColdSteelSpokenPassage& Passage = Passages[Current.Passage];
        Heading->SetText(FText::FromString(Passage.Heading));
        Heading->SetVisibility(Passage.Heading.IsEmpty() ? EVisibility::Collapsed : EVisibility::HitTestInvisible);
        Illustration->SetContent(Passage.Illustration ? Passage.Illustration.ToSharedRef() : SNullWidget::NullWidget);
        Illustration->SetVisibility(Passage.Illustration ? EVisibility::HitTestInvisible : EVisibility::Collapsed);
    }
    CharacterEnds.Reset();
    const auto Characters = FBreakIterator::GetCharacterBoundaryIterator();
    Characters->SetStringRef(Current.Text);
    Characters->ResetToBeginning();
    for (int32 End = Characters->MoveToNext(); End != INDEX_NONE; End = Characters->MoveToNext())
        CharacterEnds.Add(End);
    Characters->ClearString();
    StartedAt = Now;
    VisibleCharacters = 0;
    FullSentence->SetText(FText::FromString(Current.Text));
    Reveal(1, Now);
}

void SColdSteelNpcSpeech::Reveal(int32 Count, double Now)
{
    VisibleCharacters = FMath::Min(Count, CharacterEnds.Num());
    const FString& Text = Lines[Line].Text;
    if (IsRevealing())
    {
        SpokenText->SetText(FText::FromString(Text.Left(CharacterEnds[VisibleCharacters - 1])));
        return;
    }
    SpokenText->SetText(FText::FromString(Text));
    if (Lines.IsValidIndex(Line + 1))
    {
        NextLineAt = Now + FMath::Clamp(.65 + CharacterEnds.Num() * .075, 1.15, 7.);
    }
    else
    {
        OnFinished.ExecuteIfBound();
    }
}

bool SColdSteelNpcSpeech::RevealOrAdvance()
{
    const double Now = FSlateApplication::Get().GetCurrentTime();
    if (IsRevealing()) Reveal(CharacterEnds.Num(), Now);
    else if (Lines.IsValidIndex(Line + 1)) StartLine(Line + 1, Now);
    else return false;
    return true;
}

EActiveTimerReturnType SColdSteelNpcSpeech::TickPlayback(double Now, float)
{
    if (IsRevealing())
    {
        const int32 Count = 1 + FMath::FloorToInt((Now - StartedAt) / SecondsPerCharacter);
        if (Count > VisibleCharacters) Reveal(Count, Now);
    }
    else if (Lines.IsValidIndex(Line + 1) && Now >= NextLineAt)
        StartLine(Line + 1, Now);

    if (HasMore()) return EActiveTimerReturnType::Continue;
    Playback.Reset();
    return EActiveTimerReturnType::Stop;
}

void SColdSteelNpcSpeech::Stop()
{
    if (const auto Handle = Playback.Pin()) UnRegisterActiveTimer(Handle.ToSharedRef());
    Playback.Reset();
    OnFinished.Unbind();
}
