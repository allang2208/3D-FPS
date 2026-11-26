#include "FPSFireMagicComponent.h"
#include "HammerFireSurfaces.h"
#include "../FPSGAMECharacter.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "../WorldGeneration/FluidPresentationSubsystem.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "GameFramework/PlayerController.h"
#include "Engine/World.h"
#include "NiagaraComponent.h"
#include "NiagaraSystem.h"

namespace
{
float ArmorDetail(const AFPSGAMECharacter* Player)
{
    if(Player->IsLocallyControlled())return 1.f;
    if(const auto* PC=Player->GetWorld()->GetFirstPlayerController();PC&&PC->PlayerCameraManager)
    {
        const double Distance=FVector::DistSquared(PC->PlayerCameraManager->GetCameraLocation(),Player->GetActorLocation());
        return Distance<FMath::Square(1200.f)?1.f:Distance<FMath::Square(2500.f)?.6f:Distance<FMath::Square(5000.f)?.3f:0.f;
    }
    return .3f;
}

bool IsHammerFlame(FName Section)
{
    return Section==TEXT("HammerSurface")||Section==TEXT("HammerLeft")||Section==TEXT("HammerRight")||Section==TEXT("HammerLeftBack")||Section==TEXT("HammerRightBack");
}

FVector FlameProfile(FName Section)
{
    if(IsHammerFlame(Section))return FVector(1.4,1.05,.65);
    if(Section==TEXT("hand_r")||Section==TEXT("hand_l"))return FVector(1,.7,.15);
    if(Section==TEXT("BowUpper")||Section==TEXT("BowLower"))return FVector(.7,.85,.22);
    if(Section==TEXT("NockedArrow"))return FVector(.72,.7,.3);
    if(Section==TEXT("StaffShaft"))return FVector(.8,.9,.3);
    if(Section==TEXT("StaffCrown"))return FVector(1.2,1.15,.35);
    if(Section==TEXT("GunBarrel"))return FVector(.85,.65,.12);
    if(Section==TEXT("ToolEdge"))return FVector(1.15,.85,.55);
    return FVector(1,1.05,1);
}
}

void UFPSFireMagicComponent::UpdateArmorBodyFX(float Fade,const FVector& Feet)
{
    auto* Player=Cast<AFPSGAMECharacter>(GetOwner());if(!Player||!AuraFX)return;
    const float Detail=ArmorDetail(Player);
    if(Detail<=0.f||Fade<=0.f)
    {
        AuraFX->DeactivateImmediate();AuraFX->SetVisibility(false);bArmorFeetValid=false;return;
    }
    const float Height=Player->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()*2.f;
    const float Radius=Player->GetCapsuleComponent()->GetScaledCapsuleRadius();
    if(!bArmorFeetValid||FVector::DistSquared(PreviousArmorFeet,Feet)>FMath::Square(220.f))AuraFX->DeactivateImmediate();
    AuraFX->SetWorldLocation(Feet);
    AuraFX->SetVariablePosition(TEXT("User.BodyOrigin"),Feet);
    AuraFX->SetVariableVec3(TEXT("User.BodyVelocity"),Player->GetVelocity());
    const auto* World=GetWorld();
    auto* Fluids=World->GetSubsystem<UFluidPresentationSubsystem>();
    AuraFX->SetVariableVec3(TEXT("User.Wind"),Fluids?Fluids->WindAt(Feet):FVector::ZeroVector);
    AuraFX->SetVariableFloat(TEXT("User.Clock"),World->GetTimeSeconds());
    AuraFX->SetVariableFloat(TEXT("User.Radius"),Radius+10.f);
    AuraFX->SetVariableFloat(TEXT("User.BodyHeight"),Height);
    AuraFX->SetVariableFloat(TEXT("User.UpperVisibility"),0.f);
    AuraFX->SetVariableFloat(TEXT("User.Detail"),Detail);
    AuraFX->SetVariableFloat(TEXT("User.Fade"),Fade);
    AuraFX->SetVisibility(true);
    if(!AuraFX->IsActive())AuraFX->Activate(true);
    PreviousArmorFeet=Feet;bArmorFeetValid=true;
}

void UFPSFireMagicComponent::UpdateArmorWeaponFX(float Delta,float Fade)
{
    if(GetNetMode()==NM_DedicatedServer||!WeaponSystem)return;
    auto* Player=Cast<AFPSGAMECharacter>(GetOwner());if(!Player)return;
    FFlameArmorAttachments Spans;
    const float Detail=ArmorDetail(Player);
    if(Detail>0.f)FlameArmorAttachments::Gather(Player,Spans);
    const auto* Body=Player->FindComponentByClass<UFPSPlayerBodyComponent>();
    const bool FirstPerson=Player->IsLocallyControlled()&&(!Body||!Body->IsThirdPersonViewEnabled());
    for(int32 Index=0;Index<FlameArmorAttachments::MaxLayers;++Index)
    {
        auto& History=WeaponHistory[Index];
        UNiagaraComponent* FX=WeaponFX.IsValidIndex(Index)?WeaponFX[Index].Get():nullptr;
        if(!Spans.IsValidIndex(Index)||Fade<=0.f)
        {
            if(FX&&FX->IsActive()){FX->SetVariableFloat(TEXT("User.Fade"),0.f);FX->DeactivateImmediate();FX->SetVisibility(false);}
            History.bValid=false;continue;
        }
        const auto& Span=Spans[Index];
        const bool Hammer=IsHammerFlame(Span.Section);
        const bool Sword=Span.bSword&&SwordSystem;
        UNiagaraSystem* DesiredSystem=Sword?SwordSystem.Get():(Hammer&&HammerSystem?HammerSystem.Get():WeaponSystem.Get());
        if(!FX)
        {
            FX=NewObject<UNiagaraComponent>(Player,NAME_None,RF_Transient);
            Player->AddInstanceComponent(FX);FX->SetupAttachment(Player->GetRootComponent());
            FX->SetAutoActivate(false);FX->SetAsset(DesiredSystem);FX->SetAbsolute(false,false,true);
            // Use current-frame parameters after camera, animation and armor
            // presentation. UsePrereqs alone only examines the attach parent
            // for batched Niagara and can simulate before this component.
            FX->PrimaryComponentTick.TickGroup=TG_LastDemotable;
            FX->SetTickBehavior(ENiagaraTickBehavior::UseComponentTickGroup);
            FX->SetForceSolo(FirstPerson);
            FX->SetCastShadow(false);FX->SetVisibleInRayTracing(false);FX->RegisterComponent();
            FX->AddTickPrerequisiteComponent(this);
            if(WeaponFX.Num()<=Index)WeaponFX.SetNum(Index+1);WeaponFX[Index]=FX;
        }
        const auto* Primitive=Cast<UPrimitiveComponent>(Span.Source.Get());
        const EFirstPersonPrimitiveType PrimitiveType=FirstPerson&&Primitive?Primitive->FirstPersonPrimitiveType:EFirstPersonPrimitiveType::None;
        if(FX->FirstPersonPrimitiveType!=PrimitiveType)FX->SetFirstPersonPrimitiveType(PrimitiveType);
        if(FX->bOnlyOwnerSee!=FirstPerson)FX->SetOnlyOwnerSee(FirstPerson);
        // Only the local viewmodel needs an individual ordered tick. Other
        // players retain Niagara batching in the final frame tick group.
        FX->SetForceSolo(FirstPerson);
        const bool SystemChanged=FX->GetAsset()!=DesiredSystem;
        if(SystemChanged){FX->DeactivateImmediate();FX->SetAsset(DesiredSystem);}
        const bool AttachmentChanged=FX->GetAttachParent()!=Span.Source.Get()||FX->GetAttachSocketName()!=Span.Socket;
        const FVector SurfaceScale=Span.Source->GetComponentScale();
        const bool Reset=AttachmentChanged||SystemChanged||!History.bValid||History.Source!=Span.Source||History.Geometry!=Span.Geometry||History.Section!=Span.Section
            ||(Span.HammerSurface&&!History.SurfaceScale.Equals(SurfaceScale,.0001))
            ||History.EquipmentIdentity!=Span.EquipmentIdentity||FVector::DistSquared(History.Base,Span.Base)>FMath::Square(180.f)
            ||FVector::DistSquared(History.Tip,Span.Tip)>FMath::Square(240.f);
        if(Reset){History.Base=Span.Base;History.Tip=Span.Tip;FX->DeactivateImmediate();}
        if(AttachmentChanged)
        {
            if(auto* Previous=FX->GetAttachParent())FX->RemoveTickPrerequisiteComponent(Previous);
            FX->AttachToComponent(Span.Source.Get(),FAttachmentTransformRules::KeepWorldTransform,Span.Socket);
            FX->AddTickPrerequisiteComponent(Span.Source.Get());
        }
        // Roots inherit the actual weapon (or weapon bone), including late
        // parent transforms. Keep centimetre dimensions despite mesh scale.
        const FQuat Frame=Span.Source->GetSocketQuaternion(Span.Socket);
        FX->SetWorldLocationAndRotation(Span.Base,Frame);
        FX->SetWorldScale3D(FVector::OneVector);
        if(Reset&&Span.HammerSurface)HammerFireSurfaces::Configure(FX,*Span.HammerSurface,SurfaceScale);
        const FVector Velocity=Delta>SMALL_NUMBER?((Span.Base+Span.Tip-History.Base-History.Tip)*(.5f/Delta)).GetClampedToMaxSize(1400.f):FVector::ZeroVector;
        // A short, frame-rate independent inertia response keeps flame tips
        // bending through a swing reversal, without dragging the surface roots.
        if(Hammer)
        {
            History.FlameFlow=Reset?FVector::ZeroVector:FMath::Lerp(History.FlameFlow,Velocity,1.f-FMath::Exp(-FMath::Max(Delta,0.f)/.055f));
            FX->SetVariableVec3(TEXT("User.HammerFlow"),Frame.UnrotateVector(History.FlameFlow));
        }
        // All weapon families now use the restored charge flame's separate
        // base/tip flow inputs. Position itself is never filtered.
        {
            // Match StarMarrow charge's separate base/tip inertia and subtract
            // player travel so walking does not bend every tongue backwards.
            if(Reset)History.SwordBaseFlow=History.SwordTipFlow=FVector::ZeroVector;
            else if(Delta>SMALL_NUMBER)
            {
                const double Blend=1.-FMath::Exp(-Delta/.060);
                const FVector Travel=Player->GetVelocity();
                History.SwordBaseFlow=FMath::Lerp(History.SwordBaseFlow,((Span.Base-History.Base)/Delta-Travel).GetClampedToMaxSize(1500.),Blend);
                History.SwordTipFlow=FMath::Lerp(History.SwordTipFlow,((Span.Tip-History.Tip)/Delta-Travel).GetClampedToMaxSize(1500.),Blend);
            }
            FVector Side=Span.Side;
            if(Span.Section==TEXT("SwordEdge")&&Span.Source->DoesSocketExist(TEXT("WPN_root")))
                Side=FRotationMatrix::MakeFromXZ((Span.Tip-Span.Base).GetSafeNormal(),Span.Source->GetSocketTransform(TEXT("WPN_root")).GetUnitAxis(EAxis::X)).GetUnitAxis(EAxis::Z);
            FX->SetVariableVec3(TEXT("User.BladeSide"),Frame.UnrotateVector(Side));
            FX->SetVariableVec3(TEXT("User.BaseFlow"),Frame.UnrotateVector(History.SwordBaseFlow));
            FX->SetVariableVec3(TEXT("User.TipFlow"),Frame.UnrotateVector(History.SwordTipFlow));
        }
        FX->SetVariableVec3(TEXT("User.WeaponEnd"),Frame.UnrotateVector(Span.Tip-Span.Base));
        FX->SetVariableVec3(TEXT("User.WeaponSide"),Frame.UnrotateVector(Span.Side));
        FX->SetVariableVec3(TEXT("User.WeaponNormal"),Frame.UnrotateVector(Span.Normal));
        FX->SetVariableVec3(TEXT("User.FlameUp"),Frame.UnrotateVector(FVector::UpVector));
        // Hammer systems use their mesh triangles; other families retain the
        // existing cross-section fitting parameters.
        const bool BladeRim=Span.Section==TEXT("BladeSurface")||Span.Section==TEXT("ToolEdge");
        FX->SetVariableFloat(TEXT("User.SurfaceMode"),Hammer?1.f:BladeRim?2.f:0.f);
        static const FName SurfaceNames[]={TEXT("User.Surface0"),TEXT("User.Surface1"),TEXT("User.Surface2"),TEXT("User.Surface3"),
            TEXT("User.Surface4"),TEXT("User.Surface5"),TEXT("User.Surface6"),TEXT("User.Surface7")};
        for(int32 Station=0;Station<8;++Station)FX->SetVariableVec4(SurfaceNames[Station],Span.Surface[Station]);
        const uint32 Seed=HashCombineFast(HashCombineFast(GetTypeHash(Span.Source.Get()),GetTypeHash(Span.Section)),NetArmor.CastId);
        FX->SetVariableFloat(TEXT("User.VariationSeed"),float(Seed&0xffff)*.015625f);
        FX->SetVariableFloat(TEXT("User.FlameClock"),GetWorld()->GetTimeSeconds());
        FX->SetVariablePosition(TEXT("User.WeaponStartWorld"),Span.Base);FX->SetVariablePosition(TEXT("User.WeaponEndWorld"),Span.Tip);
        FX->SetVariablePosition(TEXT("User.PreviousStart"),History.Base);FX->SetVariablePosition(TEXT("User.PreviousEnd"),History.Tip);
        FX->SetVariableVec3(TEXT("User.WeaponVelocity"),Frame.UnrotateVector(Velocity));
        FX->SetVariableFloat(TEXT("User.WeaponSize"),Span.Size);FX->SetVariableFloat(TEXT("User.Fade"),Fade*Span.Opacity);
        FX->SetVariableFloat(TEXT("User.Detail"),Detail*(Spans.Num()>2?.85f:1.f));
        FX->SetVariableFloat(TEXT("User.Coverage"),FMath::Clamp(float(FVector::Distance(Span.Base,Span.Tip))/60.f,.3f,1.f));
        const float MotionEnergy=float(FMath::Max(History.SwordBaseFlow.Size(),History.SwordTipFlow.Size())/900.);
        FX->SetVariableFloat(TEXT("User.MotionEnergy"),Reset?0.f:FMath::Clamp(MotionEnergy,0.f,1.f));
        FX->SetVariableVec3(TEXT("User.FlameProfile"),FlameProfile(Span.Section));
        if(!FX->IsVisible())FX->SetVisibility(true);
        // The copied persistent core bursts only at emitter age zero. A soft
        // activation after an equipment change can retain the old burst state
        // and leave the new weapon with no core. Recreate simulation state only
        // at these discontinuities, after the new surface parameters are set.
        if(Reset)FX->ReinitializeSystem();
        else if(!FX->IsActive())FX->Activate(true);
        History.Source=Span.Source;History.Geometry=Span.Geometry;History.Section=Span.Section;History.EquipmentIdentity=Span.EquipmentIdentity;
        History.Base=Span.Base;History.Tip=Span.Tip;History.SurfaceScale=SurfaceScale;History.bValid=true;
    }
}
