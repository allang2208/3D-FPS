#include "FPSFireMagicComponent.h"
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

FVector FlameProfile(FName Section)
{
    if(Section==TEXT("HammerLeft")||Section==TEXT("HammerRight")||Section==TEXT("HammerLeftBack")||Section==TEXT("HammerRightBack"))return FVector(1.4,1.05,.65);
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
        if(!FX)
        {
            FX=NewObject<UNiagaraComponent>(Player,NAME_None,RF_Transient);
            Player->AddInstanceComponent(FX);FX->SetupAttachment(Player->GetRootComponent());
            FX->SetAutoActivate(false);FX->SetAsset(WeaponSystem);FX->SetAbsolute(true,true,true);
            FX->SetCastShadow(false);FX->SetVisibleInRayTracing(false);FX->RegisterComponent();
            FX->AddTickPrerequisiteComponent(this);FX->SetTickBehavior(ENiagaraTickBehavior::UsePrereqs);
            if(WeaponFX.Num()<=Index)WeaponFX.SetNum(Index+1);WeaponFX[Index]=FX;
        }
        const auto* Primitive=Cast<UPrimitiveComponent>(Span.Source.Get());
        const EFirstPersonPrimitiveType PrimitiveType=FirstPerson&&Primitive?Primitive->FirstPersonPrimitiveType:EFirstPersonPrimitiveType::None;
        if(FX->FirstPersonPrimitiveType!=PrimitiveType)FX->SetFirstPersonPrimitiveType(PrimitiveType);
        if(FX->bOnlyOwnerSee!=FirstPerson)FX->SetOnlyOwnerSee(FirstPerson);
        const bool Reset=!History.bValid||History.Source!=Span.Source||History.Geometry!=Span.Geometry||History.Section!=Span.Section
            ||History.EquipmentIdentity!=Span.EquipmentIdentity||FVector::DistSquared(History.Base,Span.Base)>FMath::Square(180.f)
            ||FVector::DistSquared(History.Tip,Span.Tip)>FMath::Square(240.f);
        if(Reset){History.Base=Span.Base;History.Tip=Span.Tip;FX->DeactivateImmediate();}
        const FVector Velocity=Delta>SMALL_NUMBER?((Span.Base+Span.Tip-History.Base-History.Tip)*(.5f/Delta)).GetClampedToMaxSize(1400.f):FVector::ZeroVector;
        FX->SetWorldLocation(Span.Base);
        FX->SetVariableVec3(TEXT("User.WeaponEnd"),Span.Tip-Span.Base);
        FX->SetVariablePosition(TEXT("User.WeaponStartWorld"),Span.Base);FX->SetVariablePosition(TEXT("User.WeaponEndWorld"),Span.Tip);
        FX->SetVariablePosition(TEXT("User.PreviousStart"),History.Base);FX->SetVariablePosition(TEXT("User.PreviousEnd"),History.Tip);
        FX->SetVariableVec3(TEXT("User.WeaponVelocity"),Velocity);
        FX->SetVariableFloat(TEXT("User.WeaponSize"),Span.Size);FX->SetVariableFloat(TEXT("User.Fade"),Fade*Span.Opacity);
        FX->SetVariableFloat(TEXT("User.Detail"),Detail*(Spans.Num()>2?.85f:1.f));
        FX->SetVariableFloat(TEXT("User.Coverage"),FMath::Clamp(float(FVector::Distance(Span.Base,Span.Tip))/60.f,.3f,1.f));
        FX->SetVariableFloat(TEXT("User.MotionEnergy"),Reset?0.f:FMath::Clamp(float((Velocity-Player->GetVelocity()).Size())/750.f,0.f,1.f));
        FX->SetVariableVec3(TEXT("User.FlameProfile"),FlameProfile(Span.Section));
        if(!FX->IsVisible())FX->SetVisibility(true);
        if(Reset||!FX->IsActive())FX->Activate(true);
        History.Source=Span.Source;History.Geometry=Span.Geometry;History.Section=Span.Section;History.EquipmentIdentity=Span.EquipmentIdentity;
        History.Base=Span.Base;History.Tip=Span.Tip;History.bValid=true;
    }
}
