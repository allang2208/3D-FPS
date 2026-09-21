#include "ColdSteelAmmoWheel.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelUIStyle.h"
#include "Blueprint/WidgetTree.h"
#include "Components/Spacer.h"
#include "Engine/GameInstance.h"
#include "Framework/Application/SlateApplication.h"
#include "Fonts/FontMeasure.h"
#include "Rendering/DrawElements.h"
#include "Rendering/SlateRenderer.h"
#include "Styling/CoreStyle.h"

void UColdSteelAmmoWheel::NativeOnInitialized()
{
    Super::NativeOnInitialized();
    Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    WidgetTree->RootWidget=WidgetTree->ConstructWidget<USpacer>();
    SetVisibility(ESlateVisibility::HitTestInvisible);
}
void UColdSteelAmmoWheel::NativeConstruct()
{Super::NativeConstruct();if(Model&&!ChangedHandle.IsValid())ChangedHandle=Model->OnChanged.AddUObject(this,&ThisClass::RefreshCounts);}
void UColdSteelAmmoWheel::NativeDestruct()
{if(Model)Model->OnChanged.Remove(ChangedHandle);ChangedHandle.Reset();Super::NativeDestruct();}
void UColdSteelAmmoWheel::OpenForWeapon(const FString& Id,int32 Hand)
{
    Instance=Id;bDualHand=Hand>=0;Pointer=FVector2D::ZeroVector;Hover=INDEX_NONE;Choices.Reset();
    if(Model)if(const auto* Gun=Model->FindItem(Id))
    {
        Choices=Model->CompatibleAmmo(*Gun);Caption=ColdSteelInventory::Text(*Gun,TEXT("name"));
        for(const auto& Choice:Choices)Model->AmmoIcon(Choice.Id);
        if(const auto* Type=Model->AmmoType(Model->AmmoDefinitionFor(*Gun)))Caption+=TEXT(" · ")+Type->GroupName;
        if(Hand>=0)Caption+=(Hand?TEXT(" · 副手"):TEXT(" · 主手"));
    }
}
void UColdSteelAmmoWheel::RefreshCounts()
{
    if(!Model)return;const auto* Gun=Model->FindItem(Instance);
    // Keep segment positions stable until this opening ends.
    for(auto& Choice:Choices){Choice.Count=Model->PouchCount(Choice.Id);Choice.Current=Gun&&Model->AmmoDefinitionFor(*Gun)==Choice.Id;}
    if(auto Slate=GetCachedWidget())Slate->Invalidate(EInvalidateWidgetReason::Paint);
}
void UColdSteelAmmoWheel::MovePointer(FVector2D Delta)
{
    Pointer=(Pointer+Delta/200.).GetClampedToMaxSize(.96);
    const int32 Count=Choices.Num();
    if(Count==0||Pointer.SizeSquared()<.30*.30)Hover=INDEX_NONE;
    else
    {
        // Segment zero is centered at twelve o'clock. Drawing and hit selection
        // use the same 2PI/N step, with no fixed three/six segment limit.
        const double Step=2.*PI/Count;
        const double Angle=FMath::Atan2(Pointer.Y,Pointer.X)+HALF_PI;
        const int32 Next=int32(FMath::FloorToDouble(FMath::Fmod(Angle+Step*.5+4.*PI,2.*PI)/Step))%Count;
        const double Distance=Hover>=0?FMath::Abs(FMath::UnwindRadians(Angle-Hover*Step)):PI;
        if(Hover<0||Next==Hover||Distance>Step*.5+FMath::Min(FMath::DegreesToRadians(4.),Step*.10))Hover=Next;
    }
    if(auto Slate=GetCachedWidget())Slate->Invalidate(EInvalidateWidgetReason::Paint);
}
FString UColdSteelAmmoWheel::SelectedAmmo() const
{return Choices.IsValidIndex(Hover)&&Choices[Hover].Count>0&&!Choices[Hover].Current?Choices[Hover].Id:FString();}
int32 UColdSteelAmmoWheel::NativePaint(const FPaintArgs& Args,const FGeometry& G,const FSlateRect& Cull,FSlateWindowElementList& Out,int32 Layer,const FWidgetStyle& Style,bool Enabled) const
{
    Layer=Super::NativePaint(Args,G,Cull,Out,Layer,Style,Enabled);
    if(Choices.IsEmpty())return Layer;
    const float Scale=ColdSteelUI::PixelScale(this);
    const FVector2f Center(G.GetLocalSize()*.5);
    const float R=FMath::Min(FMath::Clamp(220.f+Choices.Num()*5.f,240.f,340.f)/Scale,
        float(FMath::Min(G.GetLocalSize().X*.44,G.GetLocalSize().Y*.35)));
    const float Inner=R*.30f;
    const auto Resource=FSlateApplication::Get().GetRenderer()->GetResourceHandle(*FCoreStyle::Get().GetBrush("WhiteBrush"));
    const float Step=2*PI/Choices.Num(),Gap=FMath::Min(.016f,Step*.04f);
    auto TextAt=[&](const FString& Text,FVector2f At,float Pixels,const FLinearColor& Color,bool Numeric=false)
    {
        const auto Font=Numeric?ColdSteelUI::NumberFont(Pixels*.75f/Scale):ColdSteelUI::TextFont(Pixels*.75f/Scale);
        const FVector2D Size=FSlateApplication::Get().GetRenderer()->GetFontMeasureService()->Measure(Text,Font);
        FSlateDrawElement::MakeText(Out,Layer+3,G.ToPaintGeometry(Size,FSlateLayoutTransform(FVector2D(At)-Size*.5)),Text,Font,ESlateDrawEffect::None,Color);
    };
    for(int32 I=0;I<Choices.Num();++I)
    {
        const auto& Choice=Choices[I];const bool Selected=I==Hover;
        const float Middle=-HALF_PI+I*Step,Start=Middle-Step*.5f+Gap,End=Middle+Step*.5f-Gap;
        const auto* Type=Model->AmmoType(Choice.Id);
        const auto Tier=Type?Type->TierColor:FLinearColor::Transparent;
        const auto Fill=Tier.A>0?FMath::Lerp(ColdSteelUI::GlassTint,Tier,Selected?.27f:.12f):Selected?ColdSteelUI::Gray(65,248):ColdSteelUI::GlassTint;
        TArray<FSlateVertex> Verts;TArray<SlateIndex> Indices;TArray<FVector2f> Edge;
        const int32 Steps=FMath::Max(3,FMath::CeilToInt(96.f/Choices.Num()));
        for(int32 J=0;J<=Steps;++J)
        {
            const float Angle=FMath::Lerp(Start,End,float(J)/Steps);const FVector2f Direction(FMath::Cos(Angle),FMath::Sin(Angle));
            for(const float Radius:{Inner,R})Verts.Add(FSlateVertex::Make<ESlateVertexRounding::Disabled>(G.GetAccumulatedRenderTransform(),Center+Direction*Radius,FVector2f(.5f),Fill.ToFColor(true)));
            Edge.Add(Center+Direction*R);
            if(J){const SlateIndex K=SlateIndex(J*2);Indices.Append({SlateIndex(K-2),SlateIndex(K-1),K,SlateIndex(K-1),SlateIndex(K+1),K});}
        }
        FSlateDrawElement::MakeCustomVerts(Out,Layer+1,Resource,Verts,Indices,nullptr,0,0);
        FSlateDrawElement::MakeLines(Out,Layer+2,G.ToPaintGeometry(),Edge,ESlateDrawEffect::None,Selected?ColdSteelUI::Accent:Tier.A>0?Tier:ColdSteelUI::Border,true,(Selected?2.f:1.f)/Scale);
        const FVector2f At=Center+FVector2f(FMath::Cos(Middle),FMath::Sin(Middle))*R*.67f;
        const auto Color=Choice.Count==0?ColdSteelUI::TextTertiary:ColdSteelUI::TextPrimary;
        if(Choices.Num()<=8)
        {
            const auto* Icon=Choices.Num()<=6?Model->AmmoIcon(Choice.Id):nullptr;
            if(Icon)
            {
                const float Side=FMath::Min(80/Scale,R*.34f);
                FSlateDrawElement::MakeBox(Out,Layer+3,G.ToPaintGeometry(FVector2D(Side),
                    FSlateLayoutTransform(FVector2D(At)-FVector2D(Side*.5,Side*.5+24/Scale))),Icon,
                    ESlateDrawEffect::None,Choice.Count==0?FLinearColor(.55f,.55f,.55f,1):FLinearColor::White);
            }
            TextAt(Choice.Name,At+FVector2f(0,(Icon?26.f:-21.f)/Scale),16,Color);
            TextAt(FString::Printf(TEXT("%lld"),Choice.Count),At+FVector2f(0,(Icon?49.f:2.f)/Scale),24,Color,true);
            TextAt(Choice.Current?TEXT("当前装填"):Choice.Count==0?TEXT("已用尽"):Selected?TEXT("待切换"):TEXT(""),At+FVector2f(0,(Icon?73.f:26.f)/Scale),12,ColdSteelUI::TextSecondary);
        }
        else if(Choices.Num()<=24)TextAt(FString::FromInt(I+1),At,14,Color,true);
        // Dense wheels still split equally; full hovered names/counts live in the
        // hub, rather than shrinking or overlapping sector text.
    }
    const auto Disc=ColdSteelUI::RoundedBrush(FLinearColor::White,Inner,ColdSteelUI::Border,1/Scale);
    FSlateDrawElement::MakeBox(Out,Layer+2,G.ToPaintGeometry(FVector2D(Inner*2),FSlateLayoutTransform(FVector2D(Center)-FVector2D(Inner))),&Disc,ESlateDrawEffect::None,ColdSteelUI::GlassTint);
    const auto* Selected=Choices.IsValidIndex(Hover)?&Choices[Hover]:nullptr;
    TextAt(Selected?Selected->Name:TEXT("切换弹种"),Center-FVector2f(0,18/Scale),16,ColdSteelUI::TextPrimary);
    TextAt(Selected?FString::Printf(TEXT("%lld 发"),Selected->Count):TEXT("移动鼠标选择"),Center+FVector2f(0,5/Scale),12,ColdSteelUI::TextSecondary);
    TextAt(Selected&&Selected->Count>0&&!Selected->Current?TEXT("松开 R 换弹"):TEXT("松开 R 取消"),Center+FVector2f(0,26/Scale),12,ColdSteelUI::TextSecondary);
    TextAt(Caption,Center-FVector2f(0,R+47/Scale),16,ColdSteelUI::TextPrimary);
    const FString EffectId=Selected?Selected->Id:Model->AmmoDefinition();
    TextAt(Model->AmmoEffectSummary(EffectId),Center-FVector2f(0,R+24/Scale),12,ColdSteelUI::TextSecondary);
    TextAt(TEXT("移动鼠标选择 · 松开 R 换弹"),Center+FVector2f(0,R+24/Scale),14,ColdSteelUI::TextPrimary);
    TextAt(TEXT("移回中心取消 · Esc 取消"),Center+FVector2f(0,R+46/Scale),12,ColdSteelUI::TextSecondary);
    if(bDualHand)TextAt(TEXT("左键选择主手 · 右键选择副手"),Center+FVector2f(0,R+66/Scale),12,ColdSteelUI::TextSecondary);
    const FVector2f Point=Center+FVector2f(Pointer)*R;
    const auto Dot=ColdSteelUI::RoundedBrush(FLinearColor::White,4/Scale,FLinearColor::Black,1/Scale);
    FSlateDrawElement::MakeBox(Out,Layer+4,G.ToPaintGeometry(FVector2D(8/Scale),FSlateLayoutTransform(FVector2D(Point)-FVector2D(4/Scale))),&Dot,ESlateDrawEffect::None,ColdSteelUI::TextPrimary);
    return Layer+4;
}
