#include "ColdSteelTypographyCheckCommandlet.h"
#if WITH_EDITOR
#include "../UI/ColdSteelTextToolTip.h"
#include "../UI/ColdSteelUIStyle.h"
#include "../UI/ColdSteelWorldText.h"
#include "../SceneTestPortal.h"
#include "../Props/FPSPracticeTarget.h"
#include "Materials/MaterialInterface.h"
#include "Components/TextBlock.h"
#include "Engine/Engine.h"
#include "Fonts/FontCache.h"
#include "Fonts/FontMeasure.h"
#include "Framework/Application/SlateApplication.h"
#include "Interfaces/ISlateRHIRendererModule.h"
#include "Modules/ModuleManager.h"
#include "Widgets/SToolTip.h"
#include "Widgets/Text/STextBlock.h"
#endif

int32 UColdSteelTypographyCheckCommandlet::Main(const FString& Params)
{
#if WITH_EDITOR
    if (!FSlateApplication::IsInitialized())
    {
        auto& Module = FModuleManager::LoadModuleChecked<ISlateRHIRendererModule>(TEXT("SlateRHIRenderer"));
        FSlateApplication::InitializeAsStandaloneApplication(Module.CreateSlateRHIRenderer());
    }
    if (FParse::Param(*Params,TEXT("InventoryPopups"))) return CheckInventoryPopups();
    const auto Renderer = FSlateApplication::Get().GetRenderer();
    const auto Cache = Renderer->GetFontCache();
    const auto Measure = Renderer->GetFontMeasureService();
    const auto Body = ColdSteelUI::TextFont(10.5f);
    int32 Failed = 0;
    auto Check = [&](bool OK, const TCHAR* Case)
    {
        UE_LOG(LogTemp, Display, TEXT("UI_TYPOGRAPHY %s %s"), OK ? TEXT("PASS") : TEXT("FAIL"), Case);
        if (!OK) ++Failed;
    };
    auto UsesFace = [&](const FSlateFontInfo& Font, UTF32CHAR Codepoint, const TCHAR* File)
    {
        float Scale = 1.f;
        return Cache->GetFontDataForCodepoint(Font, Codepoint, Scale).GetFontFilename().EndsWith(File);
    };
    if (FParse::Param(*Params,TEXT("WorldText")))
    {
        UFont* Font=LoadObject<UFont>(nullptr,ColdSteelWorldText::Asset);
        if (!Font || Font->FontCacheType!=EFontCacheType::Offline || Font->Textures.IsEmpty()) return 2;
        Check(Font->ImportOptions.bUseDistanceFieldAlpha,TEXT("world signs have a saved distance-field atlas"));
        const auto* Portal=GetDefault<ASceneTestPortal>()->FindComponentByClass<UTextRenderComponent>();
        const auto* Target=GetDefault<AFPSPracticeTarget>()->FindComponentByClass<UTextRenderComponent>();
        Check(Portal && Portal->Font==Font && Target && Target->Font==Font,TEXT("portal and target use the world font"));
        const FString Sample=TEXT("训练靶DPS总伤害命中林道村庄森林小径返回基地主神空间正在准备目的地…[Esc]取消加载失败[E]重试进入（2米内）掉落保存请0123456789.-");
        bool Glyphs=true;
        for (const TCHAR Ch : Sample)
        {
            const int32 Index=Font->RemapChar(Ch);
            Glyphs &= Font->CharRemap.Contains(Ch) && Font->Characters.IsValidIndex(Index)
                && Font->Characters[Index].USize>0 && Font->Textures.IsValidIndex(Font->Characters[Index].TextureIndex);
        }
        Check(Glyphs,TEXT("signs, thermometer and mixed-language controls have atlas glyphs"));
        auto* Material=LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/Building/PotionWorkbench20261015/ThermometerV9/M_AlchemyTemperatureText.M_AlchemyTemperatureText"));
        TArray<FMaterialParameterInfo> FontParams; TArray<FGuid> Ids;
        if (Material) Material->GetAllFontParameterInfo(FontParams,Ids);
        Check(!FontParams.IsEmpty(),TEXT("thermometer material accepts the component font and page"));
        auto CanvasUsesProjectFace = [&](UFont* Canvas, int32 Points)
        {
            if (!Canvas || Canvas->LegacyFontSize != Points ||
                !Canvas->GetPathName().StartsWith(TEXT("/Game/UI/GunsmithWorkbench/WorldText/F_ColdSteelCanvas"))) return false;
            const FSlateFontInfo Info = Canvas->GetLegacySlateFontInfo();
            return UsesFace(Info, 0x88C5, TEXT("NotoSansSC-Regular.otf")) && UsesFace(Info, '2', TEXT("NotoSansSC-Regular.otf"));
        };
        Check(CanvasUsesProjectFace(UEngine::GetTinyFont(), 8) && CanvasUsesProjectFace(UEngine::GetSmallFont(), 10)
            && CanvasUsesProjectFace(UEngine::GetMediumFont(), 10) && CanvasUsesProjectFace(UEngine::GetLargeFont(), 10)
            && CanvasUsesProjectFace(UEngine::GetSubtitleFont(), 10), TEXT("Canvas and subtitle defaults resolve Chinese and digits to the project face"));
        UE_LOG(LogTemp,Display,TEXT("WORLD_TYPOGRAPHY characters=%d pages=%d failures=%d"),Font->Characters.Num(),Font->Textures.Num(),Failed);
        return Failed ? 1 : 0;
    }
    for (auto Weight : {ColdSteelUI::ETextWeight::Regular, ColdSteelUI::ETextWeight::SemiBold, ColdSteelUI::ETextWeight::Bold})
    {
        const auto Font = ColdSteelUI::TextFont(12.f, Weight);
        const TCHAR* File = Weight == ColdSteelUI::ETextWeight::Regular ? TEXT("NotoSansSC-Regular.otf") :
            Weight == ColdSteelUI::ETextWeight::SemiBold ? TEXT("NotoSansSC-SemiBold.ttf") : TEXT("NotoSansSC-Bold.otf");
        Check(UsesFace(Font,0x88C5,File) && UsesFace(Font,'M',File) && UsesFace(Font,'2',File),TEXT("Chinese, Latin and digits resolve to the requested weight"));
        Check(UsesFace(Font,0x1F4A7,TEXT("NotoColorEmoji.ttf")) && UsesFace(Font,0x1F9B4,TEXT("NotoColorEmoji.ttf")),
            TEXT("water drop and bone resolve to a staged color font"));
        Check(UsesFace(Font,0x26E8,TEXT("NotoSansSymbols-VF.ttf")) && UsesFace(Font,0x2726,TEXT("NotoSansSymbols2-Regular.ttf"))
            && UsesFace(Font,0x27A4,TEXT("NotoSansSymbols2-Regular.ttf")),TEXT("shield, star and arrow resolve to their symbol faces"));
        Check(Measure->Measure(TEXT("111,111"),Font).X == Measure->Measure(TEXT("888,888"),Font).X,TEXT("same-length balances have equal widths"));
    }
    Check(UsesFace(ColdSteelUI::IconFont(22.5f),0x1F56F,TEXT("NotoColorEmoji.ttf")),TEXT("tribute candle uses the bundled color face"));
    const float DotWidth = Measure->Measure(TEXT("…"),Body).X;
    Check(ColdSteelUI::Ellipsize(TEXT("准备完成"),Body,DotWidth-.5f,*Measure).IsEmpty(),TEXT("narrow boxes do not paint an overflowing ellipsis"));
    const FString Combining(TEXT("Ae\u0301水滴💧完成"));
    const TArray<FString> Prefixes={TEXT("…"),TEXT("A…"),TEXT("Ae\u0301…"),TEXT("Ae\u0301水…"),TEXT("Ae\u0301水滴…"),TEXT("Ae\u0301水滴💧…"),TEXT("Ae\u0301水滴💧完…")};
    bool Safe = true;
    for (int32 W=1; W<=100; ++W)
    {
        const FString Fit = ColdSteelUI::Ellipsize(Combining,Body,W,*Measure);
        Safe &= (Fit.IsEmpty() || Fit==Combining || Prefixes.Contains(Fit)) && Measure->Measure(Fit,Body).X<=W;
    }
    Check(Safe,TEXT("truncation respects width, combining marks and supplementary characters"));

    // Verify the stock visualizer still sees live text after both Slate and UMG updates.
    FText Caption=FText::FromString(TEXT("未装备"));
    const auto MakeBound=ColdSteelToolTip::Make(TAttribute<FText>::CreateLambda([&Caption]{return Caption;}));
    if (!MakeBound.Get() || MakeBound.Get()->GetContentWidget()->GetType()!=TEXT("STextBlock")) return 2;
    const auto SlateLabel=StaticCastSharedRef<STextBlock>(MakeBound.Get()->GetContentWidget());
    Caption=FText::FromString(TEXT("已装备"));
    Check(SlateLabel->GetText().EqualTo(Caption) && SlateLabel->GetFont().CompositeFont==Body.CompositeFont,TEXT("deferred Slate tooltip updates with the shared font"));
    UTextBlock* Target=NewObject<UTextBlock>();
    ColdSteelToolTip::Set(*Target,Caption);
    const auto Owner=Target->TakeWidget();
    if (!Owner->GetToolTip() || Owner->GetToolTip()->GetContentWidget()->GetType()!=TEXT("SToolTip")) return 2;
    const auto Presenter=StaticCastSharedRef<SToolTip>(Owner->GetToolTip()->GetContentWidget());
    if (Presenter->GetContentWidget()->GetType()!=TEXT("STextBlock")) return 2;
    const auto Label=StaticCastSharedRef<STextBlock>(Presenter->GetContentWidget());
    const auto* Previous=Target->GetToolTip();
    ColdSteelToolTip::Set(*Target,FText::FromString(TEXT("数量 12")));
    Check(Target->GetToolTip()==Previous && Label->GetText().EqualTo(Target->GetToolTipText())
        && Label->GetFont().CompositeFont==Body.CompositeFont,TEXT("UMG tooltip survives TakeWidget and updates in place"));
    ColdSteelToolTip::Set(*Target,FText::GetEmpty());
    Check(!Owner->GetToolTip().IsValid() && !Target->GetToolTip(),TEXT("empty UMG hint clears the hover target"));
    return Failed ? 1 : 0;
#else
    return 1;
#endif
}
