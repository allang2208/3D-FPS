#include "ColdSteelMagicWheel.h"
#include "ColdSteelMagicQuickCast.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelHUDWidget.h"
#include "ColdSteelQuickDrag.h"
#include "ColdSteelUIStyle.h"
#include "ColdSteelUIAudio.h"
#include "Blueprint/WidgetTree.h"
#include "Components/Spacer.h"
#include "Engine/AssetManager.h"
#include "Engine/GameInstance.h"
#include "Engine/StreamableManager.h"
#include "Engine/Texture2D.h"
#include "Fonts/FontMeasure.h"
#include "Framework/Application/SlateApplication.h"
#include "HAL/IConsoleManager.h"
#include "Misc/Paths.h"
#include "Rendering/DrawElements.h"
#include "Rendering/SlateRenderer.h"
#include "Styling/CoreStyle.h"

namespace { constexpr float Hub=.30f;constexpr float Step=2.f*PI/ColdSteelMagicQuickCast::Count; }

void UColdSteelMagicWheel::NativeOnInitialized()
{
    Super::NativeOnInitialized();
    Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    WidgetTree->RootWidget=WidgetTree->ConstructWidget<USpacer>();
    SetVisibility(ESlateVisibility::HitTestInvisible);
}
void UColdSteelMagicWheel::Configure(UColdSteelHUDWidget* OwnerHUD)
{
    HUD=OwnerHUD;bConfiguration=OwnerHUD!=nullptr;
    SetVisibility(bConfiguration?ESlateVisibility::Visible:ESlateVisibility::HitTestInvisible);
    RefreshBindings();
}
void UColdSteelMagicWheel::NativeConstruct()
{
    Super::NativeConstruct();
    if(Model&&!ChangedHandle.IsValid())ChangedHandle=Model->OnChanged.AddUObject(this,&ThisClass::RefreshBindings);
    RefreshBindings();RequestIcons();
}
void UColdSteelMagicWheel::NativeDestruct()
{
    if(Model)Model->OnChanged.Remove(ChangedHandle);ChangedHandle.Reset();
    if(IconLoad)IconLoad->CancelHandle();IconLoad.Reset();
    Super::NativeDestruct();
}
void UColdSteelMagicWheel::Repaint()
{if(auto Slate=GetCachedWidget())Slate->Invalidate(EInvalidateWidgetReason::Paint);}
void UColdSteelMagicWheel::RefreshBindings()
{
    if(!Model)return;
    const bool Changed=Skills!=Model->MagicBindings();
    Skills=Model->MagicBindings();CurrentSlot=Model->SelectedMagicSlot();
    if(Changed)RequestIcons();
    Repaint();
}
void UColdSteelMagicWheel::RequestIcons()
{
    if(!Model)return;
    TArray<FSoftObjectPath> Pending;
    for(FName Skill:Skills)
    {
        if(Skill.IsNone()||Textures.Contains(Skill))continue;
        const auto* Definition=Model->QuickSkillDefinition(Skill);
        if(!Definition||Definition->Icon.IsEmpty())continue;
        const FString Package=TEXT("/Game/ColdSteelData/")+FPaths::GetPath(Definition->Icon)/FPaths::GetBaseFilename(Definition->Icon);
        const FSoftObjectPath Path(Package+TEXT(".")+FPaths::GetBaseFilename(Package));
        IconPaths.Add(Skill,Path);Pending.AddUnique(Path);
    }
    if(Pending.IsEmpty())return;
    if(IconLoad)IconLoad->CancelHandle();
    IconLoad=UAssetManager::GetStreamableManager().RequestAsyncLoad(Pending,FStreamableDelegate::CreateWeakLambda(this,[this]()
    {
        for(const auto& Entry:IconPaths)
            if(auto* Texture=Cast<UTexture2D>(Entry.Value.ResolveObject()))
            {
                Textures.Add(Entry.Key,Texture);FSlateBrush Brush;Brush.SetResourceObject(Texture);
                Brush.ImageSize=FVector2D(64);Brush.DrawAs=ESlateBrushDrawType::Image;Brushes.Add(Entry.Key,Brush);
            }
        Repaint();
    }));
}
UColdSteelMagicWheel::FLayout UColdSteelMagicWheel::Layout(const FGeometry& Geometry) const
{
    FLayout Result;Result.Scale=FMath::Max(.01f,ColdSteelUI::PixelScale(this));
    const FVector2D Size=Geometry.GetLocalSize();
    Result.Center=Size*.5;
    if(bConfiguration)
    {
        Result.Center.Y=FMath::Max(0.,(Size.Y-64.f/Result.Scale)*.5);
        Result.Radius=FMath::Max(1.f,FMath::Min(300.f/Result.Scale,float(FMath::Min(Size.X*.5-22.f/Result.Scale,Result.Center.Y-20.f/Result.Scale))));
    }
    else Result.Radius=FMath::Max(1.f,FMath::Min(300.f/Result.Scale,float(FMath::Min(Size.X*.44,Size.Y*.35))));
    return Result;
}
void UColdSteelMagicWheel::UpdateHover()
{
    const double Radius=Pointer.SizeSquared();
    Hover=Radius<Hub*Hub||Radius>1.+UE_DOUBLE_SMALL_NUMBER?INDEX_NONE:
        int32(FMath::FloorToDouble(FMath::Fmod(FMath::Atan2(Pointer.Y,Pointer.X)+HALF_PI+Step*.5+4.*PI,2.*PI)/Step))%ColdSteelMagicQuickCast::Count;
    Repaint();
}
void UColdSteelMagicWheel::MovePointer(FVector2D ScreenDelta)
{
    const auto* Sensitivity=IConsoleManager::Get().FindConsoleVariable(TEXT("fps.AmmoWheel.PixelsPerRadius"));
    Pointer+=ScreenDelta/FMath::Max(40.f,Sensitivity?Sensitivity->GetFloat():180.f);
    if(Pointer.SizeSquared()>1.)Pointer.Normalize();
    UpdateHover();
}
void UColdSteelMagicWheel::PointAt(const FGeometry& Geometry,FVector2D ScreenPosition)
{
    const auto Disc=Layout(Geometry);Pointer=(Geometry.AbsoluteToLocal(ScreenPosition)-Disc.Center)/Disc.Radius;UpdateHover();
}
int32 UColdSteelMagicWheel::SelectedSlot() const
{return Model&&Skills.IsValidIndex(Hover)&&Model->CanBindMagic(Skills[Hover])?Hover:INDEX_NONE;}
bool UColdSteelMagicWheel::ClearsSelection() const
{return Pointer.SizeSquared()<Hub*Hub||(Skills.IsValidIndex(Hover)&&Skills[Hover].IsNone());}
void UColdSteelMagicWheel::ClearHover()
{Hover=INDEX_NONE;Pointer=FVector2D::ZeroVector;bDragHover=false;bValidDrop=false;Repaint();}
FReply UColdSteelMagicWheel::NativeOnMouseMove(const FGeometry& Geometry,const FPointerEvent& Event)
{
    if(!bConfiguration)return Super::NativeOnMouseMove(Geometry,Event);
    PointAt(Geometry,Event.GetScreenSpacePosition());return FReply::Handled();
}
void UColdSteelMagicWheel::NativeOnMouseLeave(const FPointerEvent& Event)
{ClearHover();Super::NativeOnMouseLeave(Event);}
FReply UColdSteelMagicWheel::NativeOnMouseButtonDown(const FGeometry& Geometry,const FPointerEvent& Event)
{
    if(!bConfiguration||!Model)return FReply::Unhandled();
    PointAt(Geometry,Event.GetScreenSpacePosition());
    if(Event.GetEffectingButton()==EKeys::RightMouseButton&&Hover>=0){ColdSteelUIAudio::Play(this,ColdSteelUIAudio::ECue::Button);Model->ClearMagic(Hover);}
    else if(Event.GetEffectingButton()==EKeys::LeftMouseButton)
    {
        if(ClearsSelection()){ColdSteelUIAudio::Play(this,ColdSteelUIAudio::ECue::Slot);Model->SelectMagic(INDEX_NONE);}
        else if(SelectedSlot()>=0){ColdSteelUIAudio::Play(this,ColdSteelUIAudio::ECue::Slot);Model->SelectMagic(Hover);}
    }
    return FReply::Handled();
}
bool UColdSteelMagicWheel::NativeOnDragOver(const FGeometry& Geometry,const FDragDropEvent& Event,UDragDropOperation* Operation)
{
    auto* Drag=Cast<UColdSteelQuickDrag>(Operation);
    if(!bConfiguration||!Drag||!Model)return false;
    PointAt(Geometry,Event.GetScreenSpacePosition());bDragHover=true;
    const FName Skill=Drag->SourceSlot>=0?Model->QuickBinding(Drag->SourceSlot).Skill:Drag->Skill;
    bValidDrop=Hover>=0&&Drag->IsCurrent()&&Drag->MagicBindings==Model->MagicBindings()&&Model->CanBindMagic(Skill);
    Repaint();return true;
}
void UColdSteelMagicWheel::NativeOnDragLeave(const FDragDropEvent& Event,UDragDropOperation* Operation)
{ClearHover();Super::NativeOnDragLeave(Event,Operation);}
bool UColdSteelMagicWheel::NativeOnDrop(const FGeometry& Geometry,const FDragDropEvent& Event,UDragDropOperation* Operation)
{
    auto* Drag=Cast<UColdSteelQuickDrag>(Operation);
    if(!bConfiguration||!HUD.IsValid()||!Drag)return false;
    PointAt(Geometry,Event.GetScreenSpacePosition());
    const bool Handled=HUD->DropMagicDrag(Drag,Hover);if(Handled)ColdSteelUIAudio::Play(this,ColdSteelUIAudio::ECue::SlotDrop);ClearHover();return Handled;
}

int32 UColdSteelMagicWheel::NativePaint(const FPaintArgs& Args,const FGeometry& Geometry,const FSlateRect& Cull,FSlateWindowElementList& Out,int32 Layer,const FWidgetStyle& Style,bool Enabled) const
{
    Layer=Super::NativePaint(Args,Geometry,Cull,Out,Layer,Style,Enabled);
    const auto Disc=Layout(Geometry);const float Scale=Disc.Scale,R=Disc.Radius,Inner=R*Hub;
    const FVector2f Center(Disc.Center);const auto Transform=Geometry.GetAccumulatedRenderTransform();
    const auto Renderer=FSlateApplication::Get().GetRenderer();
    const auto Resource=Renderer->GetResourceHandle(*FCoreStyle::Get().GetBrush("WhiteBrush"));
    const FLinearColor Tint=Style.GetColorAndOpacityTint();
    auto TextAt=[&](FString Text,FVector2D At,float Pixels,FLinearColor Color,float MaxWidth=0.f)
    {
        const auto Font=ColdSteelUI::TextFont(Pixels*.75f/Scale);
        const auto Measure=Renderer->GetFontMeasureService();FVector2D Size=Measure->Measure(Text,Font);
        if(MaxWidth>0&&Size.X>MaxWidth)
        {
            while(Text.Len()>1&&Measure->Measure(Text+TEXT("…"),Font).X>MaxWidth)Text.LeftChopInline(1);
            Text+=TEXT("…");Size=Measure->Measure(Text,Font);
        }
        FSlateDrawElement::MakeText(Out,Layer+6,Geometry.ToPaintGeometry(Size,FSlateLayoutTransform(At-Size*.5)),Text,Font,ESlateDrawEffect::None,Color*Tint);
    };
    auto Band=[&](float Start,float End,float Low,float High,FLinearColor LowColor,FLinearColor HighColor,int32 DrawLayer)
    {
        const int32 Segments=FMath::Max(8,FMath::CeilToInt((End-Start)*48.f));
        TArray<FSlateVertex> Vertices;TArray<SlateIndex> Indices;Vertices.Reserve((Segments+1)*2);Indices.Reserve(Segments*6);
        for(int32 I=0;I<=Segments;++I)
        {
            const float Angle=FMath::Lerp(Start,End,float(I)/Segments);const FVector2f Direction(FMath::Cos(Angle),FMath::Sin(Angle));
            Vertices.Add(FSlateVertex::Make<ESlateVertexRounding::Disabled>(Transform,Center+Direction*Low,FVector2f(.5f),(LowColor*Tint).ToFColor(true)));
            Vertices.Add(FSlateVertex::Make<ESlateVertexRounding::Disabled>(Transform,Center+Direction*High,FVector2f(.5f),(HighColor*Tint).ToFColor(true)));
            if(I){const SlateIndex J=SlateIndex(I*2);Indices.Append({SlateIndex(J-2),J,SlateIndex(J+1),SlateIndex(J-2),SlateIndex(J+1),SlateIndex(J-1)});}
        }
        FSlateDrawElement::MakeCustomVerts(Out,DrawLayer,Resource,Vertices,Indices,nullptr,0,0);
    };
    Band(0,2*PI,R,R*1.04f,FLinearColor(0,0,0,.35f),FLinearColor::Transparent,Layer+1);
    Band(0,2*PI,0,Inner,ColdSteelUI::Content,ColdSteelUI::GlassTint,Layer+1);
    const float IconSide=FMath::Min(64.f/Scale,R*.23f);
    for(int32 Index=0;Index<ColdSteelMagicQuickCast::Count;++Index)
    {
        const FName Skill=Skills.IsValidIndex(Index)?Skills[Index]:NAME_None;
        const bool Available=Model&&Model->CanBindMagic(Skill),Hot=Index==Hover,Selected=Index==CurrentSlot;
        const float Angle=-HALF_PI+Index*Step,Start=Angle-Step*.5f+.0045f,End=Angle+Step*.5f-.0045f;
        FLinearColor Fill=Hot?ColdSteelUI::ButtonHover:ColdSteelUI::Content;
        FLinearColor Edge=Selected?ColdSteelUI::HUDGold:Hot?ColdSteelUI::Accent:ColdSteelUI::Border;
        if(Hot&&bDragHover)Edge=bValidDrop?ColdSteelUI::Success:ColdSteelUI::Danger;
        Band(Start,End,Inner,R,Fill,ColdSteelUI::GlassTint,Layer+2);
        Band(Start,End,R-(Selected||Hot?2.f:1.f)/Scale,R,Edge,Edge,Layer+3);
        if(Selected)Band(Start,End,Inner,Inner+3.f/Scale,Edge,Edge,Layer+3);
        const FVector2D Direction(FMath::Cos(Angle),FMath::Sin(Angle));
        const FVector2D Cell=Disc.Center+Direction*(R*.68f);
        TextAt(FString::FromInt(Index+1),Disc.Center+Direction*(R*.90f),12,Selected?ColdSteelUI::HUDGoldLight:ColdSteelUI::TextTertiary);
        if(const auto* Brush=Brushes.Find(Skill))
        {
            const FVector2D IconAt=Cell-FVector2D(IconSide*.5,IconSide*.5+8.f/Scale);
            FSlateDrawElement::MakeBox(Out,Layer+4,Geometry.ToPaintGeometry(FVector2D(IconSide),FSlateLayoutTransform(IconAt)),Brush,ESlateDrawEffect::None,FLinearColor(1,1,1,Available?1.f:.35f)*Tint);
        }
        const auto* Definition=Model?Model->QuickSkillDefinition(Skill):nullptr;
        TextAt(Definition?Definition->Name:TEXT("未配置"),Cell+FVector2D(0,Skill.IsNone()?0:IconSide*.5+3.f/Scale),13,
            Available?ColdSteelUI::TextPrimary:ColdSteelUI::TextTertiary,R*.43f);
    }
    const int32 Display=Hover>=0?Hover:bConfiguration?CurrentSlot:INDEX_NONE;
    const FName DisplaySkill=Skills.IsValidIndex(Display)?Skills[Display]:NAME_None;
    const auto* Definition=Model?Model->QuickSkillDefinition(DisplaySkill):nullptr;
    TextAt(Hover>=0?FString::Printf(TEXT("法术 %02d"),Hover+1):TEXT("当前魔法"),Disc.Center-FVector2D(0,23.f/Scale),13,ColdSteelUI::TextTertiary,Inner*1.8f);
    TextAt(Definition?Definition->Name:TEXT("未选择魔法"),Disc.Center,17,ColdSteelUI::TextPrimary,Inner*1.8f);
    TextAt(bConfiguration?TEXT("点击中心取消选择"):TEXT("松开 R 确认"),Disc.Center+FVector2D(0,24.f/Scale),11,ColdSteelUI::TextSecondary,Inner*1.8f);
    const float FooterY=bConfiguration?float(Geometry.GetLocalSize().Y)-46.f/Scale:float(Disc.Center.Y)+R+36.f/Scale;
    TextAt(bConfiguration?TEXT("拖入已学魔法 · 点击选择 · 右键清空"):TEXT("中心 / 空槽恢复挥杖 · Esc 取消切换"),FVector2D(Disc.Center.X,FooterY),14,ColdSteelUI::TextSecondary,float(Geometry.GetLocalSize().X)-24.f/Scale);
    if(bConfiguration)TextAt(TEXT("中心 / 空槽取消选择 · 未选择时左键挥杖"),FVector2D(Disc.Center.X,FooterY+25.f/Scale),13,ColdSteelUI::TextTertiary,float(Geometry.GetLocalSize().X)-24.f/Scale);
    else
    {
        const FVector2D WheelPointerPoint=Disc.Center+Pointer*R;
        const auto CursorBrush=ColdSteelUI::RoundedBrush(ColdSteelUI::TextPrimary,3.f/Scale,FLinearColor::Transparent,0);
        FSlateDrawElement::MakeBox(Out,Layer+7,Geometry.ToPaintGeometry(FVector2D(6.f/Scale),FSlateLayoutTransform(WheelPointerPoint-FVector2D(3.f/Scale))),&CursorBrush,ESlateDrawEffect::None,Tint);
    }
    return Layer+7;
}
