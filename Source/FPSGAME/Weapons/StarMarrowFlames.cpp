#include "StarMarrowComponent.h"
#include "RuneSwordComponent.h"
#include "../FPSGAMECharacter.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "Components/PrimitiveComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Engine/World.h"
#include "Camera/PlayerCameraManager.h"
#include "GameFramework/PlayerController.h"
#include "NiagaraComponent.h"
#include "NiagaraSystem.h"

namespace
{
const FSoftObjectPath BlueFlame(TEXT("/Game/Weapons/FrostCrystalSword20260915/StarMarrowCharge20261103/NS_StarMarrowDenseBladeFire.NS_StarMarrowDenseBladeFire"));

FVector BladeWidthDirection(const USceneComponent& Source,const FVector& Axis)
{
    // Modular blades are Z-long and X-wide. The skeletal fallback uses the same weapon frame.
    const FTransform Frame = Source.DoesSocketExist(TEXT("WPN_root"))
        ? Source.GetSocketTransform(TEXT("WPN_root")) : Source.GetComponentTransform();
    return FRotationMatrix::MakeFromXZ(Axis,Frame.GetUnitAxis(EAxis::X)).GetUnitAxis(EAxis::Z);
}
}
void UStarMarrowComponent::LoadFlames()
{
    AddTickPrerequisiteActor(GetOwner());
    if(auto* Body=GetOwner()->FindComponentByClass<UFPSPlayerBodyComponent>())AddTickPrerequisiteComponent(Body);
    if(auto* Sword=GetOwner()->FindComponentByClass<URuneSwordComponent>())AddTickPrerequisiteComponent(Sword);
    if(GetNetMode()==NM_DedicatedServer||FlameSystem||FlameLoad)return;
    FlameLoad=UAssetManager::GetStreamableManager().RequestAsyncLoad(BlueFlame,FStreamableDelegate::CreateWeakLambda(this,[this]()
    {FlameSystem=Cast<UNiagaraSystem>(BlueFlame.ResolveObject());}));
}
void UStarMarrowComponent::StopFlames()
{
    for(auto& FX:FlameFX)if(FX){FX->DeactivateImmediate();FX->SetVisibility(false);}
    for(auto& History:FlameHistory)History.bValid=false;
}
void UStarMarrowComponent::UpdateFlames(float Delta)
{
    auto* Player=Cast<AFPSGAMECharacter>(GetOwner());
    if(GetNetMode()==NM_DedicatedServer||!Player||!FlameSystem)return;
    float Detail=1.f;
    if(!Player->IsLocallyControlled())if(const auto* PC=GetWorld()->GetFirstPlayerController();PC&&PC->PlayerCameraManager)
    {
        const double D=FVector::DistSquared(PC->PlayerCameraManager->GetCameraLocation(),Player->GetActorLocation());
        Detail=D<FMath::Square(1200.f)?1.f:D<FMath::Square(2500.f)?.6f:D<FMath::Square(5000.f)?.3f:0.f;
    }
    const auto* Body=Player->FindComponentByClass<UFPSPlayerBodyComponent>();
    const bool FirstPerson=Player->IsLocallyControlled()&&(!Body||!Body->IsThirdPersonViewEnabled());
    const auto* Sword=FirstPerson?Player->FindComponentByClass<URuneSwordComponent>():nullptr;
    const bool MatchingWeapon=FirstPerson ? Sword&&Sword->DisplayedSwordInstance()==ChargedInstance
                                         : Body&&Body->DisplayedWeaponInstance()==ChargedInstance;
    FFlameArmorAttachments Spans;
    if(Detail>0.f&&MatchingWeapon)FlameArmorAttachments::Gather(Player,Spans);
    static const FName StarMarrowBlade(TEXT("SM_FrostSword_Blade_star_marrow"));
    Spans.RemoveAll([](const FFlameArmorAttachment& S)
    {const auto* Mesh=S.Geometry.Get();return S.Section!=TEXT("SwordEdge")||!Mesh||Mesh->GetFName()!=StarMarrowBlade;});
    const float Fade=FMath::Min(FMath::Clamp((Duration-Remaining())/.18f,0.f,1.f),FMath::Clamp(Remaining()/.45f,0.f,1.f));
    for(int32 Index=0;Index<FlameArmorAttachments::MaxLayers;++Index)
    {
        auto& History=FlameHistory[Index];
        auto* FX=FlameFX.IsValidIndex(Index)?FlameFX[Index].Get():nullptr;
        if(!Spans.IsValidIndex(Index))
        {if(FX){FX->DeactivateImmediate();FX->SetVisibility(false);}History.bValid=false;continue;}
        const auto& Span=Spans[Index];
        if(!FX)
        {
            FX=NewObject<UNiagaraComponent>(Player,NAME_None,RF_Transient);Player->AddInstanceComponent(FX);
            FX->SetupAttachment(Player->GetRootComponent());FX->SetAutoActivate(false);FX->SetAsset(FlameSystem);
            FX->SetAbsolute(true,true,true);FX->SetCastShadow(false);FX->SetVisibleInRayTracing(false);FX->RegisterComponent();
            // Batched Niagara derives UsePrereqs from the attach parent, not
            // this late parameter producer. Simulate after the authored pose.
            FX->PrimaryComponentTick.TickGroup=TG_LastDemotable;
            FX->SetTickBehavior(ENiagaraTickBehavior::UseComponentTickGroup);
            FX->AddTickPrerequisiteComponent(this);
            if(FlameFX.Num()<=Index)FlameFX.SetNum(Index+1);FlameFX[Index]=FX;
        }
        const auto* Primitive=Cast<UPrimitiveComponent>(Span.Source.Get());
        FX->SetForceSolo(FirstPerson);
        const auto PrimitiveType=FirstPerson&&Primitive?Primitive->FirstPersonPrimitiveType:EFirstPersonPrimitiveType::None;
        if(FX->FirstPersonPrimitiveType!=PrimitiveType)FX->SetFirstPersonPrimitiveType(PrimitiveType);
        if(FX->bOnlyOwnerSee!=FirstPerson)FX->SetOnlyOwnerSee(FirstPerson);
        const bool Reset=!History.bValid||History.Source!=Span.Source||History.Geometry!=Span.Geometry
            ||History.EquipmentIdentity!=Span.EquipmentIdentity||FVector::DistSquared(History.Base,Span.Base)>FMath::Square(180.f)
            ||FVector::DistSquared(History.Tip,Span.Tip)>FMath::Square(240.f);
        if(Reset)
        {
            History.Base=Span.Base;History.Tip=Span.Tip;FX->DeactivateImmediate();
            // Change the cosmetic seed per charge/weapon, never per frame.
            FX->SetVariableFloat(TEXT("User.VariationSeed"),FMath::Fmod(float(ChargedUntil),1024.f)
                +float(Span.EquipmentIdentity%997)*.137f+Index*71.3f);
        }
        const FVector Axis=(Span.Tip-Span.Base).GetSafeNormal();
        if(Reset)
        {
            History.BaseFlow=History.TipFlow=FVector::ZeroVector;
        }
        else if(Delta>SMALL_NUMBER)
        {
            // About 95% settled after 0.18 s, independent of render frame rate.
            const double Blend=1.-FMath::Exp(-Delta/.060);
            const FVector Travel=Player->GetVelocity();
            const auto Follow=[Delta,Blend,&Travel](FVector& Filtered,const FVector& Step)
            {
                const FVector Target=(Step/Delta-Travel).GetClampedToMaxSize(1500.);
                Filtered=FMath::Lerp(Filtered,Target,Blend);
            };
            Follow(History.BaseFlow,Span.Base-History.Base);
            Follow(History.TipFlow,Span.Tip-History.Tip);
        }
        FX->SetWorldLocation(Span.Base);FX->SetVariableVec3(TEXT("User.WeaponEnd"),Span.Tip-Span.Base);
        FX->SetVariablePosition(TEXT("User.WeaponStartWorld"),Span.Base);FX->SetVariablePosition(TEXT("User.WeaponEndWorld"),Span.Tip);
        FX->SetVariablePosition(TEXT("User.PreviousStart"),History.Base);FX->SetVariablePosition(TEXT("User.PreviousEnd"),History.Tip);
        FX->SetVariableVec3(TEXT("User.BladeSide"),BladeWidthDirection(*Span.Source.Get(),Axis));
        FX->SetVariableVec3(TEXT("User.BaseFlow"),History.BaseFlow);
        FX->SetVariableVec3(TEXT("User.TipFlow"),History.TipFlow);
        FX->SetVariableFloat(TEXT("User.WeaponSize"),Span.Size);
        FX->SetVariableFloat(TEXT("User.Fade"),Fade*Span.Opacity);FX->SetVariableFloat(TEXT("User.Detail"),Detail);
        FX->SetVariableFloat(TEXT("User.Coverage"),FMath::Clamp(float(FVector::Distance(Span.Base,Span.Tip))/60.f,.3f,1.f));
        FX->SetVariableFloat(TEXT("User.MotionEnergy"),FMath::Clamp(FMath::Max(History.BaseFlow.Size(),History.TipFlow.Size())/900.,0.,1.));
        FX->SetVariableFloat(TEXT("User.FlameClock"),Duration-Remaining());
        FX->SetVisibility(true);if(Reset||!FX->IsActive())FX->Activate(true);
        History.Source=Span.Source;History.Geometry=Span.Geometry;History.EquipmentIdentity=Span.EquipmentIdentity;
        History.Base=Span.Base;History.Tip=Span.Tip;History.bValid=true;
    }
}
