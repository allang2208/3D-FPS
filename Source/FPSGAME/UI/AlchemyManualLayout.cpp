#include "AlchemyManualLayout.h"
#include "Framework/Text/PlainTextLayoutMarshaller.h"
#include "Framework/Text/SlateTextLayout.h"
#include "Misc/Paths.h"
#include "Widgets/Layout/SBox.h"

namespace AlchemyManualLayout
{
FSlateFontInfo Font(float Pixels,bool Strong)
{
    // Filename-backed fonts require LazyLoad or Stream; Inline is only valid
    // for embedded Font Face asset data and asserts in FFontData's constructor.
    const auto Make=[](const TCHAR* Name){return MakeShared<FCompositeFont>(TEXT("Regular"),FPaths::ProjectContentDir()/TEXT("UI/AlchemyManual/Fonts")/Name,EFontHinting::AutoLight,EFontLoadingPolicy::LazyLoad);};
    static auto Regular=Make(TEXT("FolioSerif-Regular.ttf"));
    static auto Semibold=Make(TEXT("FolioSerif-Semibold.ttf"));
    return FSlateFontInfo(Strong?Semibold:Regular,Pixels*.75f);
}
static float TextHeight(const FString& Text,float Pixels,bool Strong,float Width)
{
    FTextBlockStyle Style;Style.SetFont(Font(Pixels,Strong));
    // FSlateTextLayout's FChildren requires a live owner even for measurement.
    // Keep this off-screen owner alive until the local layout is destroyed.
    const TSharedRef<SBox> MeasureOwner=SNew(SBox);
    auto Layout=FSlateTextLayout::Create(&MeasureOwner.Get(),Style);Layout->SetWrappingWidth(Width);Layout->SetLineHeightPercentage(1.24f);
    FPlainTextLayoutMarshaller::Create()->SetText(Text,*Layout);Layout->UpdateIfNeeded();return Layout->GetSize().Y;
}
FString Action(const FString& Name)
{
    if(Name==TEXT("pour"))return TEXT("投料");if(Name==TEXT("grind"))return TEXT("研磨");
    if(Name==TEXT("heat"))return TEXT("温养");if(Name==TEXT("stir"))return TEXT("调和");
    if(Name==TEXT("cool"))return TEXT("冷却");return TEXT("炼制");
}
TArray<FParameter> Parameters(const FAlchemyRecipe& R,const FAlchemyStep& S)
{
    TArray<FParameter> Out;
    const FString Range=FString::Printf(TEXT("%.0f–%.0f °C"),S.MinHeat,S.MaxHeat);
    if(S.Action==TEXT("heat"))
    {
        Out.Add({TEXT("温度"),Range,Heat});
        Out.Add({R.FreeBrewing?TEXT("参考时间"):TEXT("保持时间"),FString::Printf(TEXT("%.0f 秒"),S.Amount),Time});
    }
    else if(S.Action==TEXT("stir"))
    {
        Out.Add({TEXT("调和"),FString::Printf(TEXT("%s · %.0f 圈"),S.Direction==0?TEXT("方向不限"):S.Direction>0?TEXT("顺时针"):TEXT("逆时针"),S.Amount),Stir});
        Out.Add({TEXT("温度"),Range,Heat});
    }
    else if(S.Action==TEXT("grind"))Out.Add({TEXT("研磨时间"),FString::Printf(TEXT("%.0f 秒"),S.Amount),Time});
    else if(S.Action==TEXT("pour"))
    {
        Out.Add({TEXT("投料数量"),FString::Printf(TEXT("%.0f 份"),S.Amount),Material});
        Out.Add({TEXT("温度"),Range,Heat});
    }
    else if(S.Action==TEXT("cool"))Out.Add({TEXT("目标温度"),Range,Heat});
    return Out;
}
static float FragmentHeight(const FAlchemyRecipe& R,const FAlchemyManualStepFragment& F)
{
    return 46.f+TextHeight(F.Text,34,false,StepWidth)+12.f+(F.bParameters?Parameters(R,R.Steps[F.Step]).Num()*52.f:0.f)+26.f;
}
const TArray<FAlchemyManualLeaf>& Leaves(const FAlchemyRecipe& R)
{
    // The bounded print plan is shared by page count, page content and contents
    // folios. Measuring and parsing never occur while dragging the paper.
    static TMap<FString,TArray<FAlchemyManualLeaf>> Cache;
    const FString Key=R.Raw.IsEmpty()?R.Id.ToString()+R.Name:R.Raw;
    if(const auto* Found=Cache.Find(Key))return *Found;
    if(Cache.Num()>=32)Cache.Reset();
    TArray<FAlchemyManualLeaf> Pages;FAlchemyManualLeaf Intro;Intro.bOverview=true;Pages.Add(Intro);
    FAlchemyManualLeaf Current;
    const auto Flush=[&](){if(!Current.Steps.IsEmpty()||Current.bNotes){Pages.Add(MoveTemp(Current));Current=FAlchemyManualLeaf();}};
    for(int32 Index=0;Index<R.Steps.Num();++Index)
    {
        FString Remaining=R.Steps[Index].Text;bool Continued=false;
        do
        {
            FAlchemyManualStepFragment F{Index,Remaining,Continued,true};
            float Height=FragmentHeight(R,F);
            if(Height>BodyHeight)
            {
                // Split a single long instruction at a natural break. Its
                // parameters remain attached to its final continuation only.
                int32 Low=1,High=FMath::Max(1,Remaining.Len()-1);
                while(Low<High)
                {
                    const int32 Mid=(Low+High+1)/2;F.Text=Remaining.Left(Mid);F.bParameters=false;
                    if(FragmentHeight(R,F)<=BodyHeight-8.f)Low=Mid;else High=Mid-1;
                }
                int32 Cut=Low;
                for(int32 J=Low-1;J>Low/2;--J)
                    if(Remaining[J]==TEXT('。')||Remaining[J]==TEXT('；')||Remaining[J]==TEXT('，')||Remaining[J]==TEXT(' ')){Cut=J+1;break;}
                F.Text=Remaining.Left(Cut);F.bParameters=false;Remaining=Remaining.Mid(Cut);Height=FragmentHeight(R,F);
            }
            else Remaining.Empty();
            if(Current.UsedHeight+Height>BodyHeight)Flush();
            Current.Steps.Add(F);Current.UsedHeight+=Height;Continued=true;
        } while(!Remaining.IsEmpty());
    }
    Flush();
    const float NotesHeight=250.f;
    if(!Pages.Last().bOverview&&Pages.Last().UsedHeight+NotesHeight<=BodyHeight)
    {Pages.Last().bNotes=true;Pages.Last().UsedHeight+=NotesHeight;}
    else
    {FAlchemyManualLeaf Finish;Finish.bFinish=true;Finish.bNotes=true;Pages.Add(Finish);}
    if(Pages.Num()%2)
    {
        // A final spread has a product record on one face and notes on the
        // other; never strip notes from an otherwise empty face.
        const bool AlreadyFinish=Pages.Last().bFinish;
        Pages.Last().bNotes=false;
        FAlchemyManualLeaf Finish;Finish.bFinish=!AlreadyFinish;Finish.bNotes=true;Pages.Add(Finish);
    }
    return Cache.Add(Key,MoveTemp(Pages));
}
}
