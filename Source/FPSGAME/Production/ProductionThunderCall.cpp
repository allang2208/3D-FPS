#include "ProductionToolComponent.h"
#include "ThunderHammerTuning.h"
#include "../FPSGAMECharacter.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Components/DecalComponent.h"
#include "Components/AudioComponent.h"
#include "Sound/SoundBase.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Engine/World.h"

float UProductionToolComponent::ThunderCallChargeProgress() const
{
    if(!bThunderCallCharging)return 0.f;
    const auto* Pawn=Character.Get();
    if(Pawn&&Pawn->IsLocallyControlled())return HeavyChargeFraction();
    return FMath::Clamp(float(RuneboundClock()-ThunderCallVisualStartedAt)/FMath::Max(.01f,ThunderCallVisualSeconds),0.f,1.f);
}

void UProductionToolComponent::StopThunderCallAudio()
{
    if(bThunderCallAudioActive&&ThunderCallChargeAudio)ThunderCallChargeAudio->FadeOut(.08f,0.f);
    bThunderCallAudioActive=false;
}

void UProductionToolComponent::TickThunderCallAudio()
{
    auto* Pawn=Character.Get();
    if(GetNetMode()==NM_DedicatedServer||!Pawn)return;
    if(!bThunderCallCharging){StopThunderCallAudio();return;}
    if(!ThunderCallChargeSound)return; // Preloaded with the equipped hammer.
    if(!ThunderCallChargeAudio)
    {
        auto* Audio=NewObject<UAudioComponent>(Pawn,TEXT("JiLeiElectromagneticCharge"));
        Pawn->AddInstanceComponent(Audio);Audio->bAutoActivate=false;Audio->bAutoDestroy=false;Audio->bStopWhenOwnerDestroyed=true;
        Audio->SetupAttachment(Pawn->GetRootComponent());Audio->SetSound(ThunderCallChargeSound);
        Audio->bAllowSpatialization=!Pawn->IsLocallyControlled();Audio->bOverrideAttenuation=true;
        Audio->AttenuationOverrides.bAttenuate=!Pawn->IsLocallyControlled();
        Audio->AttenuationOverrides.AttenuationShapeExtents=FVector(250.f,0.f,0.f);
        Audio->AttenuationOverrides.FalloffDistance=1800.f;
        Audio->RegisterComponent();Audio->SetLowPassFilterEnabled(true);ThunderCallChargeAudio=Audio;
    }
    const float Charge=ThunderCallChargeProgress(),Energy=FMath::SmoothStep(0.f,1.f,Charge);
    // A low magnetic hum grows into a denser electrical rasp. Use the same
    // charge clock as the arm and lightning, including remote observers.
    const float Volume=FMath::Lerp(.055f,.70f,Energy);
    ThunderCallChargeAudio->SetVolumeMultiplier(Volume);
    ThunderCallChargeAudio->SetPitchMultiplier(FMath::Lerp(.72f,1.18f,Energy));
    ThunderCallChargeAudio->SetLowPassFilterFrequency(FMath::Lerp(520.f,3600.f,Energy*Energy));
    if(!bThunderCallAudioActive)
    {
        ThunderCallChargeAudio->FadeIn(.06f,1.f);bThunderCallAudioActive=true;
    }
}

void UProductionToolComponent::ClearThunderCallVisual()
{
    ThunderCallPreviewWait=0.f;
    if(ThunderCallDecal)ThunderCallDecal->SetHiddenInGame(true);
    if(!bThunderCallCharging)StopThunderCallAudio();
}

void UProductionToolComponent::TickThunderCall(float Delta)
{
    auto* Pawn=Character.Get();if(!Pawn)return;
    auto* Profile=ColdSteelAuthority::ForPawn(Pawn);
    if(!IsThunderCalling()&&bThunderCallResourcesDirty)FinishThunderCallResources();
    if(IsThunderCalling()&&Profile&&!Profile->HasInfiniteMana()&&Profile->Mana()<=0.f)
    {CancelHeavyCharge();return;}
    TickThunderCallAudio();
    if(!Pawn->IsLocallyControlled())return;
    if(!bThunderCallSeat||!bBluntCharging||HeavyChargeFraction()<1.f-UE_SMALL_NUMBER||!CanUse(true))
    {ClearThunderCallVisual();return;}
    // Position follows the local camera each frame, independently of FX clocks.
    FHitResult Ground;
    if(!ThunderHammerCall::SelectGround(Pawn,Ground))
    {if(ThunderCallDecal)ThunderCallDecal->SetHiddenInGame(true);return;}
    if(!ThunderCallDecal)
    {
        auto* Material=Cast<UMaterialInterface>(FSoftObjectPath(TEXT("/Game/Weapons/ThunderGodHammer20261028/JiLeiSeatV1/M_JiLeiAim.M_JiLeiAim")).ResolveObject());
        if(!Material)return;
        ThunderCallDecal=NewObject<UDecalComponent>(Pawn,TEXT("JiLeiAreaPreview"));Pawn->AddInstanceComponent(ThunderCallDecal);
        ThunderCallDecal->SetDecalMaterial(Material);ThunderCallDecal->DecalSize=FVector(104.f,ThunderHammerCall::RadiusCM+16.f,ThunderHammerCall::RadiusCM+16.f);
        ThunderCallDecal->SetFadeScreenSize(0.f);ThunderCallDecal->RegisterComponent();ThunderCallAimMID=ThunderCallDecal->CreateDynamicMaterialInstance();
        ThunderCallAimMID->SetScalarParameterValue(TEXT("ImpactRadius"),ThunderHammerCall::RadiusCM);
        ThunderCallAimMID->SetScalarParameterValue(TEXT("FieldRadius"),ThunderHammerCall::RadiusCM);
    }
    ThunderCallDecal->SetWorldLocationAndRotation(Ground.ImpactPoint+Ground.ImpactNormal*4.f,FRotationMatrix::MakeFromX(-Ground.ImpactNormal).Rotator());
    ThunderCallAimMID->SetVectorParameterValue(TEXT("Center"),FLinearColor(Ground.ImpactPoint));
    ThunderCallAimMID->SetVectorParameterValue(TEXT("SurfaceNormal"),FLinearColor(Ground.ImpactNormal));
    ThunderCallDecal->SetHiddenInGame(false);
}

void UProductionToolComponent::ReleaseThunderCall()
{
    if(!ThunderCallDecal||ThunderCallDecal->bHiddenInGame)
    {CancelHeavyCharge();return;}
    // Authority commits the displayed ground request. The hammer stays held;
    // recovery has no physical melee contact or projectile detachment event.
    ThunderCallReleaseAge=0.f;
    const FVector Normal=-ThunderCallDecal->GetForwardVector();
    ServerReleaseThunderCall(BluntAttackId,ThunderCallDecal->GetComponentLocation()-Normal*4.f);
    bBluntCharging=bBluntHeavy=bThunderCallCharging=false;NextBluntStage=0;
    ClearThunderCallVisual();
}

void UProductionToolComponent::ClientThunderCallResult_Implementation(uint32 AttackId,bool Accepted)
{
    if(AttackId!=BluntAttackId||Accepted)return;
    if(bBluntCharging)CancelHeavyCharge();
    else {ThunderCallReleaseAge=-1.f;HandOffBluntPose();}
}

void UProductionToolComponent::FinishThunderCallResources()
{
    auto* Pawn=Character.Get();if(!Pawn||!Pawn->HasAuthority()||!bThunderCallResourcesDirty)return;
    auto* Profile=ColdSteelAuthority::ForPawn(Pawn);if(!Profile)return;
    const auto* PS=!Pawn->IsLocallyControlled()?Pawn->GetPlayerState<AColdSteelPlayerState>():nullptr;
    if(!Profile->CommitCampfireState(Profile->Snapshot(),TEXT("JiLeiCharge"),PS?PS->CampfireGuestSlot():FString()))return;
    bThunderCallResourcesDirty=false;const auto State=Profile->Snapshot();
    ClientThunderCallResources(State.CampfireInventoryRevision,State.Mana,State.Stamina,State.StaminaRecoveryDelay,State.bSprintExhausted);
}

void UProductionToolComponent::ClientThunderCallResources_Implementation(int64 Revision,float Mana,float Stamina,float RecoveryDelay,bool Exhausted)
{
    auto* Pawn=Character.Get();auto* Profile=ColdSteelAuthority::ForPawn(Pawn);
    if(!Pawn||Pawn->HasAuthority()||!Pawn->IsLocallyControlled()||!Profile||Revision<=ThunderCallResourceRevision)return;
    auto State=Profile->Snapshot();if(Revision<State.CampfireInventoryRevision)return;
    ThunderCallResourceRevision=Revision;State.CampfireInventoryRevision=Revision;State.CampfireWorldReceipts.FindOrAdd(TEXT("JiLeiCharge"))=Revision;
    State.Mana=FMath::Clamp(Mana,0.f,float(Profile->Derived(TEXT("maxMp"))));State.Stamina=FMath::Clamp(Stamina,0.f,Profile->MaxStamina());
    State.StaminaRecoveryDelay=RecoveryDelay;State.bSprintExhausted=Exhausted;
    Profile->AdoptNetMirror(State,true);Profile->OnChanged.Broadcast();Profile->SaveNow();
}
