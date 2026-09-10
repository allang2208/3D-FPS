#include "ColdSteelUIStyle.h"

#include "Brushes/SlateRoundedBoxBrush.h"
#include "Fonts/SlateFontInfo.h"
#include "HAL/FileManager.h"
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
    FString ExistingFontOrFallback(const FString& Preferred, const FString& Fallback)
    {
        return IFileManager::Get().FileExists(*Preferred) ? Preferred : Fallback;
    }
}

FLinearColor ColdSteelUI::RarityColor(const FString& Rarity)
{
    static const TMap<FString,FString> Colors={{TEXT("common"),TEXT("B9C2D5FF")},{TEXT("uncommon"),TEXT("8BC8ACFF")},{TEXT("rare"),TEXT("85B4E8FF")},{TEXT("epic"),TEXT("B695DEFF")},{TEXT("mythic"),TEXT("E3B278FF")},{TEXT("legendary"),TEXT("E78B9FFF")}};
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

FSlateFontInfo ColdSteelUI::TextFont(float Size)
{
    const FString Fallback = FPaths::EngineContentDir() / TEXT("Slate/Fonts/Roboto-Regular.ttf");
    const FString LocalFont = FPaths::ProjectSavedDir() / TEXT("UIFonts/SimSun-ColdSteel-0p5.ttf");
    static TSharedPtr<FCompositeFont> Font = MakeShared<FCompositeFont>(TEXT("Regular"),
        ExistingFontOrFallback(LocalFont, ExistingFontOrFallback(TEXT("C:/Windows/Fonts/simsun.ttc"), Fallback)), EFontHinting::AutoLight, EFontLoadingPolicy::LazyLoad);
    return FSlateFontInfo(Font, Size);
}

FSlateFontInfo ColdSteelUI::NumberFont(float Size, bool bBold)
{
    const FString Fallback = FPaths::EngineContentDir() / TEXT("Slate/Fonts/RobotoMono-Regular.ttf");
    auto MakeNumeric = [&Fallback](const TCHAR* Path)
    {
        auto Font = MakeShared<FCompositeFont>(TEXT("Regular"), ExistingFontOrFallback(Path, Fallback), EFontHinting::AutoLight, EFontLoadingPolicy::LazyLoad);
        Font->FallbackTypeface.Typeface.Fonts.Add(FTypefaceEntry(TEXT("Chinese"),
            ExistingFontOrFallback(FPaths::ProjectSavedDir() / TEXT("UIFonts/SimSun-ColdSteel-0p5.ttf"), TEXT("C:/Windows/Fonts/simsun.ttc")), EFontHinting::AutoLight, EFontLoadingPolicy::LazyLoad));
        return Font;
    };
    static TSharedPtr<FCompositeFont> Regular = MakeNumeric(TEXT("C:/Windows/Fonts/consola.ttf"));
    static TSharedPtr<FCompositeFont> Bold = MakeNumeric(TEXT("C:/Windows/Fonts/consolab.ttf"));
    return FSlateFontInfo(bBold ? Bold : Regular, Size);
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
