#include "ColdSteelUIStyle.h"

#include "Brushes/SlateRoundedBoxBrush.h"
#include "Fonts/SlateFontInfo.h"
#include "Fonts/FontMeasure.h"
#include "Internationalization/BreakIterator.h"
#include "Styling/SlateTypes.h"
#include "Misc/Paths.h"
#include "Blueprint/WidgetLayoutLibrary.h"
#include "Engine/World.h"
#include "Engine/GameViewportClient.h"
#include "Framework/Application/SlateApplication.h"
#include "Widgets/SWindow.h"
#include "Engine/UserInterfaceSettings.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "UnrealClient.h"

namespace
{
    const FName RegularFace(TEXT("Regular"));
    const FName SemiBoldFace(TEXT("SemiBold"));
    const FName BoldFace(TEXT("Bold"));
    const FName IconFace(TEXT("Icon"));

    TSharedRef<FCompositeFont> MakeThemeFont()
    {
        auto Font = MakeShared<FCompositeFont>();
        const FString Directory = FPaths::ProjectContentDir() / TEXT("UI/GunsmithWorkbench/Fonts");
        auto& Faces = Font->DefaultTypeface.Fonts;
        Faces.Emplace(RegularFace, Directory / TEXT("NotoSansSC-Regular.otf"), EFontHinting::AutoLight, EFontLoadingPolicy::LazyLoad);
        Faces.Emplace(SemiBoldFace, Directory / TEXT("NotoSansSC-SemiBold.ttf"), EFontHinting::AutoLight, EFontLoadingPolicy::LazyLoad);
        Faces.Emplace(BoldFace, Directory / TEXT("NotoSansSC-Bold.otf"), EFontHinting::AutoLight, EFontLoadingPolicy::LazyLoad);
        const FString Emoji = Directory / TEXT("NotoColorEmoji.ttf");
        Faces.Emplace(IconFace, Emoji, EFontHinting::Default, EFontLoadingPolicy::LazyLoad);
        Font->FallbackTypeface.Typeface.Fonts.Emplace(RegularFace, Emoji, EFontHinting::Default, EFontLoadingPolicy::LazyLoad);

        // These catalogue symbols have text presentation and are absent from both SC and Color Emoji.
        auto& Shield = Font->SubTypefaces.AddDefaulted_GetRef();
        Shield.CharacterRanges.Emplace(0x26E8);
        Shield.Typeface.Fonts.Emplace(RegularFace, Directory / TEXT("NotoSansSymbols-VF.ttf"), EFontHinting::AutoLight, EFontLoadingPolicy::LazyLoad);
        auto& Marks = Font->SubTypefaces.AddDefaulted_GetRef();
        Marks.CharacterRanges.Emplace(0x2726);
        Marks.CharacterRanges.Emplace(0x27A4);
        Marks.Typeface.Fonts.Emplace(RegularFace, Directory / TEXT("NotoSansSymbols2-Regular.ttf"), EFontHinting::AutoLight, EFontLoadingPolicy::LazyLoad);
        return Font;
    }

    const TSharedRef<FCompositeFont>& ThemeFont()
    {
        static const auto Font = MakeThemeFont();
        return Font;
    }
}

FLinearColor ColdSteelUI::RarityColor(const FString& Rarity)
{
    // Code-backed override also updates editors whose static palette was already initialized.
    if(Rarity==TEXT("legendary"))return FLinearColor::FromSRGBColor(FColor(255,48,48));
    static const TMap<FString,FString> Colors={{TEXT("common"),TEXT("B9C2D5FF")},{TEXT("uncommon"),TEXT("8BC8ACFF")},{TEXT("rare"),TEXT("85B4E8FF")},{TEXT("epic"),TEXT("B695DEFF")},{TEXT("mythic"),TEXT("E3B278FF")}};
    const auto* Hex=Colors.Find(Rarity);return Hex?FLinearColor::FromSRGBColor(FColor::FromHex(*Hex)):TextSecondary;
}
FString ColdSteelUI::RarityLabel(const FString& Rarity)
{
    static const TMap<FString,FString> Names={{TEXT("common"),TEXT("普通")},{TEXT("uncommon"),TEXT("优秀")},{TEXT("rare"),TEXT("稀有")},{TEXT("epic"),TEXT("史诗")},{TEXT("mythic"),TEXT("神话")},{TEXT("legendary"),TEXT("传说")}};
    const auto* Name=Names.Find(Rarity);return Name?*Name:TEXT("");
}
FSlateBrush ColdSteelUI::RoundedBrush(const FLinearColor& Fill, float Radius, const FLinearColor& Outline, float OutlineWidth)
{
    return FSlateRoundedBoxBrush(Fill, Radius, Outline, OutlineWidth);
}

FSlateBrush ColdSteelUI::RoundedBrushCorners(const FLinearColor& Fill, const FVector4& CornerRadii, const FLinearColor& Outline, float OutlineWidth)
{
    return FSlateRoundedBoxBrush(Fill, CornerRadii, Outline, OutlineWidth);
}

FButtonStyle ColdSteelUI::ButtonStyle(float Scale)
{
    return FButtonStyle().SetNormal(RoundedBrush(ButtonNormal,ButtonRadius/Scale,Border,1/Scale))
        .SetHovered(RoundedBrush(ButtonHover,ButtonRadius/Scale,Accent,1/Scale))
        .SetPressed(RoundedBrush(ButtonPressed,ButtonRadius/Scale,Border,1/Scale))
        .SetDisabled(RoundedBrush(ButtonDisabled,ButtonRadius/Scale,Border,1/Scale));
}

FSlateFontInfo ColdSteelUI::TextFont(float Size, ETextWeight Weight)
{
    const auto& Font = ThemeFont();
    switch (Weight)
    {
    case ETextWeight::SemiBold: return FSlateFontInfo(Font, Size, SemiBoldFace);
    case ETextWeight::Bold: return FSlateFontInfo(Font, Size, BoldFace);
    default: return FSlateFontInfo(Font, Size, RegularFace);
    }
}

FSlateFontInfo ColdSteelUI::TextFont(float Size, bool bEmphasized)
{
    return TextFont(Size, bEmphasized ? ETextWeight::Bold : ETextWeight::Regular);
}

FSlateFontInfo ColdSteelUI::NumberFont(float Size, bool bBold)
{
    // The family's lining digits have equal advances at each weight.
    return TextFont(Size, bBold);
}

FSlateFontInfo ColdSteelUI::IconFont(float Size)
{
    return FSlateFontInfo(ThemeFont(), Size, IconFace);
}

FString ColdSteelUI::Ellipsize(const FString& Text, const FSlateFontInfo& Font, float Width, const FSlateFontMeasure& Measure)
{
    if (Width <= 0.f || Text.IsEmpty()) return {};
    if (Measure.Measure(Text, Font).X <= Width) return Text;
    const FString Ellipsis(TEXT("…"));
    if (Measure.Measure(Ellipsis, Font).X > Width) return {};

    // Search complete graphemes so emoji, combining marks and surrogate pairs stay together.
    TArray<int32, TInlineAllocator<64>> Ends;
    Ends.Add(0);
    auto Breaks = FBreakIterator::GetCharacterBoundaryIterator();
    Breaks->SetStringRef(Text);
    Breaks->ResetToBeginning();
    for (int32 End = Breaks->MoveToNext(); End != INDEX_NONE && End < Text.Len(); End = Breaks->MoveToNext())
        Ends.Add(End);
    Breaks->ClearString();
    int32 Low = 0, High = Ends.Num() - 1;
    while (Low < High)
    {
        const int32 Mid = (Low + High + 1) / 2;
        if (Measure.Measure(Text.Left(Ends[Mid]) + Ellipsis, Font).X <= Width) Low = Mid;
        else High = Mid - 1;
    }
    return Text.Left(Ends[Low]) + Ellipsis;
}

float ColdSteelUI::PixelScale(const UObject* Context)
{
    FVector2D Size = UWidgetLayoutLibrary::GetViewportSize(Context);
    // Widgets can initialize before the viewport RHI has its requested size.
    // The default zero-size DPI curve must never be baked into font sizes/padding.
    if (Size.X < 100 || Size.Y < 100)
    {
        int32 X = GSystemResolution.ResX, Y = GSystemResolution.ResY;
        FParse::Value(FCommandLine::Get(), TEXT("ResX="), X);
        FParse::Value(FCommandLine::Get(), TEXT("ResY="), Y);
        Size = FVector2D(FMath::Max(960, X), FMath::Max(540, Y));
    }
    return FMath::Max(.01f, GetDefault<UUserInterfaceSettings>()->GetDPIScaleBasedOnSize(FIntPoint(Size.X, Size.Y)));
}
