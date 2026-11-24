#include "ColdSteelBowResonance.h"
#include "../Weapons/Bow/BowWeaponComponent.h"
#include "../Weapons/Bow/BowScopeOptics.h"
#include "../Weapons/Bow/BowMountainEchoComponent.h"
#include "../Weapons/Bow/MountainEchoString.h"
#include "../Weapons/Bow/BowCadenceComponent.h"
#include "../Weapons/Bow/CadenceString.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "GameFramework/Actor.h"
#include "Layout/Geometry.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Rendering/DrawElements.h"
#include "Styling/SlateBrush.h"
#include "Styling/WidgetStyle.h"

int32 ColdSteelBowResonance::Paint(const UBowWeaponComponent& Bow,const FGeometry& Geometry,
    FSlateWindowElementList& Elements,int32 Layer,const FWidgetStyle& Style,float PixelToLocal)
{
    const auto* Owner=Bow.GetOwner();
    auto* Resonance=Owner?Owner->FindComponentByClass<UBowMountainEchoComponent>():nullptr;
    auto* Cadence=Owner?Owner->FindComponentByClass<UBowCadenceComponent>():nullptr;
    const bool IsCadence=Cadence&&Cadence->IsEquippedFor(Bow.EquippedInstance());
    if(!IsCadence&&(!Resonance||!Resonance->IsEquippedFor(Bow.EquippedInstance())))return Layer;
    if(const auto* Health=Owner->FindComponentByClass<UFPSCombatHealthComponent>();Health&&Health->IsDead())return Layer;

    const int32 Maximum=IsCadence?CadenceString::MaximumStacks:MountainEchoString::MaximumStacks;
    const int32 Count=FMath::Clamp(IsCadence?Cadence->Charges():Resonance->ChargesFor(Bow.EquippedInstance()),0,Maximum);
    const bool Ready=Count==Maximum;
    const float GainAge=FMath::Max(0.f,IsCadence?Cadence->GainAge():Resonance->GainAge());
    const float T=FMath::Clamp(GainAge/.38f,0.f,1.f);
    const float Reveal=1.f-FMath::Pow(1.f-T,3.f);
    const float Fraction=Count>0?(float(Count-1)+Reveal)/Maximum:0.f;
    const float PulseAge=IsCadence?Cadence->PulseAge():GainAge;
    const float Gain=Count>0?FMath::Square(1.f-FMath::Clamp(PulseAge/.60f,0.f,1.f)):0.f;
    const float ReadyAge=IsCadence?Cadence->ReadyAge():Resonance->ReadyAge();
    const float Breath=Ready?.5f+.5f*FMath::Sin(ReadyAge*2.f*PI*.65f):0.f;
    const float CrownAge=IsCadence?PulseAge:ReadyAge-.38f;
    const float CrownPulse=Ready&&CrownAge>=0.f?
        FMath::Square(1.f-FMath::Clamp(CrownAge/.72f,0.f,1.f)):0.f;
    const auto& Layout=IsCadence?CadenceLayout:LightPillarLayout;
    const FVector2D Center=Geometry.GetLocalSize()*.5f;
    const float Scale=Layout.Scale(Center,PixelToLocal);
    if(Scale<=0.f)return Layer;
    auto* Material=IsCadence?Cadence->HUDMaterial():Resonance->ResonanceHUDMaterial();
    if(!Material)return Layer;
    static const FName StateParameter(TEXT("ResonanceState"));
    Material->SetVectorParameterValue(StateParameter,FLinearColor(Fraction,Gain,Breath,CrownPulse));
    const FVector2D Size(Layout.Width,Layout.Height());
    const FVector2D ScopeOffset=Bow.ScopeOptics()?Bow.ScopeOptics()->CueOffset(Geometry,Scale):FVector2D::ZeroVector;
    const FVector2D Position=Center+ScopeOffset+FVector2D(-Size.X*.5f,Layout.Top)*Scale;
    FSlateBrush Brush;
    Brush.DrawAs=ESlateBrushDrawType::Image;
    Brush.ImageSize=Size;
    Brush.SetResourceObject(Material);
    FSlateDrawElement::MakeBox(Elements,Layer+1,
        Geometry.ToPaintGeometry(Size*Scale,FSlateLayoutTransform(Position)),
        &Brush,ESlateDrawEffect::None,Style.GetColorAndOpacityTint());
    return Layer+1;
}
