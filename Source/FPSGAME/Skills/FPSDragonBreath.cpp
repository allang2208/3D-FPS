#include "FPSFireMagicComponent.h"
#include "../Monsters/UnknownSpellCombat.h"
#include "DragonBreathAudioAssets.h"
#include "Components/AudioComponent.h"
#include "../Combat/RangedAttackQuery.h"
#include "FPSFireballComponent.h"
#include "FireMagicArea.h"
#include "MagicOcclusion.h"
#include "HolyLightTargets.h"
#include "NetCastUtils.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Monsters/BoundCongregateCaptureComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Engine/World.h"
#include "Engine/OverlapResult.h"
#include "GameFramework/GameStateBase.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "NiagaraComponent.h"
#include "NiagaraFunctionLibrary.h"
#include "NiagaraSystem.h"
#include "NiagaraSystemInstanceController.h"
#include "Materials/MaterialInterface.h"
#include "MaterialShared.h"
#include "SceneInterface.h"
#include "Scalability.h"

namespace
{
constexpr float DragonVisualTailSeconds=.65f;
constexpr float DragonBackgroundSimulationSeconds=.25f;
bool DragonRenderMaterialsReady(UNiagaraComponent* FX)
{
    if(!FX||!FX->GetSceneProxy())return false;
    // Query the actual dynamic material / static permutation, not its unused
    // base-material resource. Niagara/PSO readiness does not include this gate.
    TArray<UMaterialInterface*> UsedMaterials;FX->GetUsedMaterials(UsedMaterials);
    if(UsedMaterials.IsEmpty())return false;
    for(auto* Material:UsedMaterials)
    {
        const auto* Resource=Material?Material->GetMaterialResource(FX->GetWorld()->Scene->GetShaderPlatform()):nullptr;
        const auto* ShaderMap=Resource?Resource->GetGameThreadShaderMap():nullptr;
        if(!ShaderMap||!ShaderMap->IsValidForRendering())return false;
#if WITH_EDITOR
        if(!Resource->IsCompilationFinished())return false;
#endif
    }
    return !FX->IsPSOPrecaching();
}
FVector DragonFluidCenter(const FVector& Origin,const FQuat& Rotation,float Range)
{
    return Origin+Rotation.GetForwardVector()*(FMath::Max(Range,500.f)*.46f);
}
double DragonClock(UWorld* World)
{
    const auto* State=World?World->GetGameState<AGameStateBase>():nullptr;
    return State?State->GetServerWorldTimeSeconds():World?World->GetTimeSeconds():0.;
}
void ConfigureDragonVolume(UNiagaraComponent* FX,const APawn* Pawn,float Radius,float ArcDegrees)
{
    const float VisualRange=FMath::Max(Radius,500.f);
    const FVector Domain(VisualRange*1.2f+160.f,VisualRange*1.55f+160.f,VisualRange*.65f+200.f);
    static constexpr int32 Resolutions[]={80,96,128,160,160};
    const int32 Quality=FMath::Clamp(Scalability::GetQualityLevels().EffectsQuality,0,4);
    const int32 Resolution=Pawn&&Pawn->IsLocallyControlled()?Resolutions[Quality]:80;
    FX->SetVariableVec3(TEXT("User.WorldSpaceSize"),Domain);
    FX->SetVariableInt(TEXT("User.ResolutionMaxAxis"),Resolution);
    FX->SetVariableFloat(TEXT("User.CellSize"),float(Domain.GetMax())/Resolution);
    FX->SetVariableBool(TEXT("User.DrawBounds"),false);
    FX->SetVariableFloat(TEXT("User.Range"),Radius);
    FX->SetVariableFloat(TEXT("User.HalfAngle"),FMath::DegreesToRadians(ArcDegrees*.5f));
    const FVector Bounds=Domain*.5f+FVector(64.f);
    FX->SetSystemFixedBounds(FBox(-Bounds,Bounds));
}
}

void UFPSFireMagicComponent::LoadDragonBreath()
{
    if(GetNetMode()==NM_DedicatedServer)return;
    const FSoftObjectPath Path(TEXT("/Game/Skills/DragonBreath20261013/Range2x20261019/NS_DragonVolume.NS_DragonVolume"));
    const TArray<FSoftObjectPath> Assets={Path,FSoftObjectPath(DragonBreathAudio::Start),
        FSoftObjectPath(DragonBreathAudio::Loop),FSoftObjectPath(DragonBreathAudio::Stop)};
    DragonLoad=UAssetManager::GetStreamableManager().RequestAsyncLoad(Assets,FSimpleDelegate::CreateWeakLambda(this,[this,Path]()
    {
        PrepareDragonBreathAudio();
        RefreshDragonBreathAudio(); // Restore only the current cast after async loading.
        DragonSystem=Cast<UNiagaraSystem>(Path.ResolveObject());
        if(!DragonSystem)
        {UE_LOG(LogTemp,Warning,TEXT("DragonBreath background load failed: %s"),*Path.ToString());return;}
#if WITH_EDITOR
        // Compile cold assets before first use, but do not invalidate a shared
        // ready system each time a player respawns or a remote pawn appears.
        if(!DragonSystem->IsReadyToRun()&&!DragonSystem->HasOutstandingCompilationRequests(true))
            DragonSystem->RequestCompile(false);
#endif
        PrepareDragonBreathVisuals();
    }));
}

bool UFPSFireMagicComponent::IsDragonBreathVisualReady() const
{
    if(GetNetMode()==NM_DedicatedServer)return true;
    if(!DragonSystem||!DragonFX||!DragonSystem->IsReadyToRun()||DragonFX->IsPSOPrecaching()||!DragonFX->IsActive())return false;
    const auto Instance=DragonFX->GetSystemInstanceController();
    // A loaded asset or active component alone does not mean the GPU grid has
    // initialized. Idle readiness is represented by the retained paused instance.
    return Instance&&Instance->GetAreDataInterfacesInitialized()&&!Instance->IsPendingSpawn()
        &&(DragonFX->IsPaused()||DragonVisualCastId!=0);
}

void UFPSFireMagicComponent::PrepareDragonBreathVisuals()
{
    if(GetNetMode()==NM_DedicatedServer||!DragonSystem)return;
    if(GetOwner()->IsActorBeingDestroyed()||GetWorld()->IsPaused())return;
    if(DragonVisualCastId!=0)return; // An actual cast / visual tail owns the simulation.
    if(DragonFX&&DragonFX->IsActive()&&DragonFX->IsPaused())return;
    const auto* Pawn=Cast<APawn>(GetOwner());
    if(!Pawn||(!Pawn->IsLocallyControlled()&&!IsDragonBreathActive()&&!DragonFX))return;
    if(Pawn->IsLocallyControlled()&&!IsDragonBreathActive()&&!DragonFX)
    {
        const auto* Profile=Model();
        if(!Profile||Profile->FireMagicProgress(TEXT("dragonBreath")).Level<=0)return;
    }
#if WITH_EDITOR
    // HasOutstandingCompilationRequests also includes NeedsRequestCompile: a
    // deferred request has not started yet. Submit it here, then poll without
    // waiting for the compile; false leaves cold/re-authored systems stuck.
    DragonSystem->PollForCompilationComplete(true);
    if(DragonSystem->HasOutstandingCompilationRequests(true))return;
#endif
    if(!DragonSystem->IsReadyToRun())return;
    if(!DragonFX)
    {
        DragonFX=NewObject<UNiagaraComponent>(GetOwner());
        GetOwner()->AddInstanceComponent(DragonFX);
        DragonFX->SetAutoActivate(false);DragonFX->SetAutoDestroy(false);
        DragonFX->SetAsset(DragonSystem);
        DragonFX->SetVariableFloat(TEXT("User.Strength"),0.f);
        DragonFX->SetVisibility(true);
        DragonFX->SetCastShadow(false);DragonFX->SetCanEverAffectNavigation(false);
        DragonFX->SetAllowScalability(false);
        DragonFX->RegisterComponent();
        DragonFX->AddTickPrerequisiteComponent(this);
        DragonFX->SetTickBehavior(ENiagaraTickBehavior::UsePrereqs);
        DragonFX->PrecachePSOs();
        DragonVisualCastId=0;DragonTailTime=0;
        return;
    }
    if(DragonFX->IsPSOPrecaching())return;
    if(DragonFX->IsPaused())return;
    if(!DragonFX->IsActive())
    {
        const auto* Profile=Model();
        if(!Profile&&!IsDragonBreathActive())return;
        const auto Spell=IsDragonBreathActive()?DragonView().Cast:Profile->FireMagicStats(TEXT("dragonBreath"));
        ConfigureDragonVolume(DragonFX,Pawn,FMath::Max(500.f,Spell.Radius),Spell.ArcDegrees);
        const FQuat Rotation=Pawn->GetBaseAimRotation().Quaternion();
        const FVector Origin=Pawn->GetPawnViewLocation();
        DragonFX->SetWorldLocationAndRotation(DragonFluidCenter(Origin,Rotation,Spell.Radius),Rotation);
        DragonFX->SetVariablePosition(TEXT("User.Origin"),Origin);
        DragonFX->SetVariableVec3(TEXT("User.Forward"),Rotation.GetForwardVector());
        DragonFX->SetVariableVec3(TEXT("User.Side"),Rotation.GetRightVector());
        DragonFX->SetVariableVec3(TEXT("User.Up"),Rotation.GetUpVector());
        DragonFX->SetVariableFloat(TEXT("User.Strength"),0.f);
        // Exercise both simulation and the volume renderer. Strength=0 zeros
        // emission/extinction, so this renders invisibly; hiding the component
        // would postpone material/permutation preparation until the first cast.
        DragonFX->SetVariableFloat(TEXT("User.EmissionScale"),.1f);
        DragonFX->SetAllowScalability(false);DragonFX->SetVisibility(true);
        DragonFX->Activate(false);
        if(DragonFX->IsActive())UE_LOG(LogTemp,Display,TEXT("DragonBreath background simulation started: %s"),*GetNameSafe(GetOwner()));
        return;
    }
    if(!DragonFX->IsVisible())DragonFX->SetVisibility(true);
    const auto Instance=DragonFX->GetSystemInstanceController();
    if(!Instance||Instance->IsPendingSpawn()||!Instance->GetAreDataInterfacesInitialized()
        ||Instance->GetAge()<DragonBackgroundSimulationSeconds)return;
    bool bHasEmission=false;
    if(DragonFX->GetVariableFloat(TEXT("User.EmissionScale"),bHasEmission)>0.f&&bHasEmission)
    {
        // Reset the hidden initialization pulse without destroying the GPU
        // interfaces, then run the empty grid before it can become cast-ready.
        DragonFX->SetVariableFloat(TEXT("User.EmissionScale"),0.f);
        DragonFX->ResetSystem();
        return;
    }
    // Keep this non-blocking and scoped to the dragon's actual materials.
    // A warm GPU grid alone can otherwise release a first cast with no pixels.
    if(!DragonRenderMaterialsReady(DragonFX))return;
    // Let normal world ticks submit GPU work across frames without gameplay,
    // damage or sound. DeactivateImmediate would destroy the data interfaces and
    // GPU compute proxy again; pausing retains them and stops idle simulation.
    DragonFX->SetPaused(true);
    DragonFX->SetVisibility(false);
    DragonLoad.Reset();
    UE_LOG(LogTemp,Display,TEXT("DragonBreath background simulation ready: %s age=%.3f (paused, GPU resources retained)"),
        *GetNameSafe(GetOwner()),Instance->GetAge());
    OnRep_DragonBreath(); // Re-apply current state only; never resurrect an old cast.
}

const FDragonBreathState& UFPSFireMagicComponent::DragonView() const
{
    const auto* Pawn=Cast<APawn>(GetOwner());
    return Pawn&&!Pawn->HasAuthority()&&Pawn->IsLocallyControlled()?DragonPrediction:DragonState;
}

bool UFPSFireMagicComponent::IsDragonBreathActive() const{return DragonView().bActive;}

FVector UFPSFireMagicComponent::CaptureDragonNozzle() const
{
    const auto* Pawn=Cast<APawn>(GetOwner());
    if(!Pawn)return FVector(95,17,4);
    FVector Tip;
    if(const auto* H=Hands();H&&H->TryStaffCastOrigin(Tip))
        return Pawn->GetBaseAimRotation().UnrotateVector(Tip-Pawn->GetPawnViewLocation());
    return FVector(95,17,4);
}

void UFPSFireMagicComponent::DragonBreathFrame(FVector& Origin,FQuat& Rotation) const
{
    auto* Pawn=Cast<APawn>(GetOwner());
    Rotation=Pawn?Pawn->GetBaseAimRotation().Quaternion():GetOwner()->GetActorQuat();
    const FVector Eye=Pawn?Pawn->GetPawnViewLocation():GetOwner()->GetActorLocation();
    Origin=Eye+Rotation.RotateVector(DragonView().NozzleOffset);
    FHitResult Wall;
    // Do not let a staff protruding through a wall become an origin behind it.
    if(FireMagic::TraceSurface(Pawn,Eye,Origin,Wall,true))Origin=Eye;
}

bool UFPSFireMagicComponent::StartDragonBreath(const FFireMagicCast& Spell,bool bPredict,uint32 CastId,const FVector& NozzleOffset,FString* Failure)
{
    const auto Reject=[&](const TCHAR* Reason)
    {
        if(Failure)*Failure=Reason;
        UE_LOG(LogTemp,Warning,TEXT("DragonBreath release rejected: %s; pawn=%s mode=%d predict=%d cast=%u nozzle=%s"),
            Reason,*GetNameSafe(GetOwner()),int32(GetNetMode()),bPredict,CastId,*NozzleOffset.ToString());
        return false;
    };
    if(IsDragonBreathActive())return Reject(TEXT("龙息喷吐中"));
    auto* Pawn=Cast<APawn>(GetOwner());
    auto* Profile=bPredict?Model():NetCast::AuthorityModel(Pawn,GetWorld()->GetGameInstance());
    if(!Pawn||!Profile)return Reject(TEXT("角色数据未就绪"));
    if(Pawn->IsPlayerControlled()&&Pawn->IsLocallyControlled()&&!IsDragonBreathVisualReady())return Reject(TEXT("龙息火焰准备中"));
    if(!Profile->HasEquippedStaff())return Reject(TEXT("需要法杖"));
    if(const auto* HP=Pawn->FindComponentByClass<UFPSCombatHealthComponent>();HP&&HP->IsDead())return Reject(TEXT("死亡无法施法"));
    if(UBoundCongregateCaptureComponent::IsCaptured(Pawn))return Reject(TEXT("被捕获无法施法"));
    if(const auto* Status=Pawn->FindComponentByClass<UCombatStatusFormula>();Status&&Status->BlocksMovement())return Reject(TEXT("受控无法施法"));
    // NozzleOffset starts at the capsule eye, whereas the authored staff starts
    // at the first-person camera. That camera advances 56 cm standing / 62 cm
    // crouched, plus look-down/torso clearance (FPSPlayerFirstPersonBody).
    // Include its bounded displacement in every aim-space axis: looking up or
    // down rotates the horizontal camera advance into the vertical offset.
    // Keep the transmitted tip unchanged so authority and FX share the real
    // origin; DragonBreathFrame still checks the entire eye-to-tip wall segment.
    constexpr float CameraDisplacementAllowance=100.f;
    if(NozzleOffset.ContainsNaN()||NozzleOffset.X<0||NozzleOffset.X>140+CameraDisplacementAllowance||
        FMath::Abs(NozzleOffset.Y)>65+CameraDisplacementAllowance||FMath::Abs(NozzleOffset.Z)>85+CameraDisplacementAllowance||
        NozzleOffset.SizeSquared()>FMath::Square(170.f+CameraDisplacementAllowance))return Reject(TEXT("龙息喷口位置异常"));
    if(bPredict&&!CastId)return Reject(TEXT("联机施法未就绪"));
    if(!bPredict&&!UnknownSpell::IsCaster(Pawn))
    {
        if(!Profile->Snapshot().bDragonBreathReserved)return Reject(TEXT("龙息施法预扣已取消"));
        if(!Profile->CommitDragonBreathRelease())
        {
            UE_LOG(LogTemp,Warning,TEXT("DragonBreath profile commit failed: %s"),*Profile->ResultMessage());
            return Reject(TEXT("龙息施法提交失败"));
        }
    }
    if(!CastId){CastId=++DragonAuthoritySerial;if(!CastId)CastId=++DragonAuthoritySerial;}
    DragonRewards=FFireMagicRewards();DragonNextDamage=0;DragonProbeClock=0;
    auto& State=bPredict?DragonPrediction:DragonState;
    State.Cast=Spell;State.StartedAt=DragonClock(GetWorld());State.CastId=CastId;
    State.NozzleOffset=NozzleOffset;State.bActive=true;
    if(!bPredict)DragonRewardModel=Profile;
    bDragonGestureHeld=Pawn->IsLocallyControlled();PresentDragonBreath();
    if(Pawn->IsLocallyControlled())if(auto* H=Hands())H->ContinueSpellRelease(this,Spell.Duration,false);
    if(GetOwner()->HasAuthority())GetOwner()->ForceNetUpdate();
    return true;
}

void UFPSFireMagicComponent::OnRep_DragonBreath()
{
    const auto* Pawn=Cast<APawn>(GetOwner());
    if(Pawn&&!Pawn->HasAuthority()&&Pawn->IsLocallyControlled())
    {
        // A newer spell must not consume this cast's receipt; a cancelled or
        // older cast must not recreate the predicted flame/gesture either.
        if(!DragonState.CastId||DragonState.CastId!=DragonLocalCastId)return;
        ConfirmDragonRelease(DragonState.CastId);
        if(DragonCancelledCastId==DragonState.CastId)return;
        DragonPrediction=DragonState;
    }
    PresentDragonBreath();
}

void UFPSFireMagicComponent::PresentDragonBreath()
{
    const auto& State=DragonView();
    if(!State.bActive)
    {
        StopDragonBreathAudio();
        // Stop fuel births immediately. The bounded fluid grid fades out;
        // this residual heat is purely cosmetic and never causes damage.
        if(DragonFX&&DragonVisualCastId!=0&&DragonTailTime<=0)
        {
            DragonFX->SetVariableFloat(TEXT("User.EmissionScale"),0.f);
            DragonTailTime=DragonVisualTailSeconds;
        }
        if(bDragonGestureHeld)if(auto* H=Hands())H->CancelSpellGesture(this);
        bDragonGestureHeld=false;
        return;
    }
    RefreshDragonBreathAudio();
    if(GetWorld()->GetNetMode()==NM_DedicatedServer||!IsDragonBreathVisualReady()||DragonVisualCastId==State.CastId)return;
    // A rapid recast resets particles but keeps the live GPU interfaces. The
    // first cast resumes the empty, already initialized background instance.
    if(DragonVisualCastId!=0)DragonFX->ResetSystem();
    DragonTailTime=0;
    FVector Origin;FQuat Rotation;DragonBreathFrame(Origin,Rotation);
    DragonFX->SetWorldLocationAndRotation(DragonFluidCenter(Origin,Rotation,State.Cast.Radius),Rotation);
    DragonFX->SetVisibility(true);
    DragonVisualCastId=State.CastId;
    // One bounded volume per caster; remote casts use a smaller grid. Resolution
    // is selected at creation so turning or changing view cannot reallocate it.
    ConfigureDragonVolume(DragonFX,Cast<APawn>(GetOwner()),State.Cast.Radius,State.Cast.ArcDegrees);
    DragonFX->SetVariableFloat(TEXT("User.Strength"),1.f);
    DragonFX->SetVariableFloat(TEXT("User.EmissionScale"),1.f);
    DragonFX->SetVariablePosition(TEXT("User.Origin"),Origin);
    DragonFX->SetVariableVec3(TEXT("User.Forward"),Rotation.GetForwardVector());
    DragonFX->SetVariableVec3(TEXT("User.Side"),Rotation.GetRightVector());
    DragonFX->SetVariableVec3(TEXT("User.Up"),Rotation.GetUpVector());
    // Publish wall distances before the first particles spawn, including casts
    // started directly next to a wall.
    UpdateDragonBreathOcclusion(Origin,Rotation);
    DragonProbeClock=.10f;
    if(const auto Instance=DragonFX->GetSystemInstanceController())Instance->SetLastRenderTime(GetWorld()->GetTimeSeconds());
    DragonFX->SetAllowScalability(true);
    DragonFX->SetPaused(false);
}

void UFPSFireMagicComponent::DragonBreathHit()
{
    auto* Pawn=Cast<APawn>(GetOwner());
    auto* Profile=NetCast::AuthorityModel(Pawn,GetWorld()->GetGameInstance());
    if(!Pawn||!Pawn->HasAuthority()||!Profile)return;
    FVector Origin;FQuat Rotation;DragonBreathFrame(Origin,Rotation);
    const auto& C=DragonState.Cast;
    FCollisionObjectQueryParams Objects;Objects.AddObjectTypesToQuery(ECC_Pawn);Objects.AddObjectTypesToQuery(ECC_WorldDynamic);Objects.AddObjectTypesToQuery(ECC_PhysicsBody);
    FCollisionQueryParams Query(SCENE_QUERY_STAT(DragonBreathArea),false,Pawn);
    TArray<FOverlapResult> Overlaps;
    GetWorld()->OverlapMultiByObjectType(Overlaps,Origin,FQuat::Identity,Objects,FCollisionShape::MakeSphere(C.Radius+100),Query);
    TSet<AActor*> Seen;int32 Hits=0;
    const float Slope=FMath::Tan(FMath::DegreesToRadians(C.ArcDegrees*.5f));
    for(const auto& Overlap:Overlaps)
    {
        AActor* Target=Overlap.GetActor();if(!IsValid(Target)||Target==Pawn||Seen.Contains(Target))continue;Seen.Add(Target);
        const auto* Combat=Target->FindComponentByClass<UMonsterCombatComponent>();
        if(UnknownSpell::IsCaster(Pawn)?!UnknownSpell::IsTarget(Pawn,Target):(!Combat||Combat->IsDead()||RangedAttackQuery::IsFriendlyUnit(Pawn,Target)))continue;
        MagicOcclusion::FBodySamples Samples;MagicOcclusion::BodySamples(Target,Origin,Samples);
        bool Exposed=false;
        for(const FVector& Point:Samples)
        {
            const FVector Local=Rotation.UnrotateVector(Point-Origin);
            if(Local.X<0||Local.X*Local.X+Local.Y*Local.Y>FMath::Square(C.Radius)||
                FMath::Abs(Local.Y)>Local.X*Slope||FMath::Abs(Local.Z)>80.f+Local.X*.28f)continue;
            FHitResult Block;if(!FireMagic::TraceSurface(Pawn,Origin,Point,Block,true)){Exposed=true;break;}
        }
        if(!Exposed)continue;
        const int32 Before=DragonRewards.Hits;
        Profile->ApplyFireMagicHit(Pawn,Target,C,C.Damage,DragonRewards);
        Hits+=DragonRewards.Hits-Before;
    }
    DragonRewards.bMultiHit|=Hits>=2;
}

void UFPSFireMagicComponent::TickDragonBreath(float Delta)
{
    PrepareDragonBreathVisuals();
    if(!IsDragonBreathActive())
    {
        StopDragonBreathAudio();
        if(DragonFX&&DragonTailTime>0)
        {
            DragonTailTime=FMath::Max(0.f,DragonTailTime-Delta);
            DragonFX->SetVariableFloat(TEXT("User.Strength"),DragonTailTime/DragonVisualTailSeconds);
            if(DragonTailTime<=0)
            {
                DragonFX->SetVariableFloat(TEXT("User.Strength"),0.f);
                DragonFX->SetVariableFloat(TEXT("User.EmissionScale"),0.f);
                DragonFX->SetVisibility(false);DragonFX->SetAllowScalability(false);
                DragonVisualCastId=0;
                // Clear old heat, then let the background path pause the empty
                // grid after ordinary ticks; do not tear down its GPU resources.
                DragonFX->ResetSystem();
            }
        }
        return;
    }
    auto* Pawn=Cast<APawn>(GetOwner());if(!Pawn){StopDragonBreath(false);return;}
    const auto& State=DragonView();
    const double Age=DragonClock(GetWorld())-State.StartedAt;
    const auto& C=State.Cast;
    if(Pawn->HasAuthority()||Pawn->IsLocallyControlled())
    {
        const auto* Profile=Pawn->HasAuthority()?NetCast::AuthorityModel(Pawn,GetWorld()->GetGameInstance()):Model();
        const auto* HP=Pawn->FindComponentByClass<UFPSCombatHealthComponent>();
        const auto* Status=Pawn->FindComponentByClass<UCombatStatusFormula>();
        const bool Dead=HP&&HP->IsDead();
        const bool Interrupted=!Profile||!Profile->HasEquippedStaff()||Dead||UBoundCongregateCaptureComponent::IsCaptured(Pawn)||
            (Status&&Status->BlocksMovement())||(Pawn->IsPlayerControlled()&&Pawn->IsLocallyControlled()&&(!Hands()||!Hands()->IsSpellGesture(this)));
        if(Interrupted)
        {
            if(Pawn->IsPlayerControlled()&&Pawn->IsLocallyControlled())RequestDragonStop();
            else StopDragonBreath(!Dead);
            return;
        }
    }
    if(Pawn->HasAuthority())
        while(DragonNextDamage<C.Duration-UE_KINDA_SMALL_NUMBER&&DragonNextDamage<=Age)
        {DragonBreathHit();DragonNextDamage+=C.TickSeconds;}
    if(Age>=C.Duration){StopDragonBreath(true);return;}
    if(Pawn->IsPlayerControlled()&&Pawn->IsLocallyControlled()&&Hands())Hands()->ContinueSpellRelease(this,.10f,false);
    FVector Origin;FQuat Rotation;DragonBreathFrame(Origin,Rotation);
    RefreshDragonBreathAudio();
    for(auto* Voice:{DragonStartAudio.Get(),DragonLoopAudio.Get(),DragonStopAudio.Get()})
        if(Voice)Voice->SetWorldLocation(Origin);
    if(!DragonFX||DragonVisualCastId!=State.CastId)
    {PresentDragonBreath();if(!DragonFX||DragonVisualCastId!=State.CastId)return;}
    // A valid component pointer is not proof that activation survived an async
    // compile/reinitialization. Retry the live cast once readiness comes back.
    if(!DragonFX->IsActive()&&DragonSystem&&DragonSystem->IsReadyToRun()&&!DragonFX->IsPSOPrecaching())DragonFX->Activate(true);
    // The template compensates the previous grid transform during advection.
    // Moving/turning the staff changes the source without rigidly dragging fire.
    DragonFX->SetWorldLocationAndRotation(DragonFluidCenter(Origin,Rotation,C.Radius),Rotation);
    DragonFX->SetVariablePosition(TEXT("User.Origin"),Origin);
    DragonFX->SetVariableVec3(TEXT("User.Forward"),Rotation.GetForwardVector());
    DragonFX->SetVariableVec3(TEXT("User.Side"),Rotation.GetRightVector());
    DragonFX->SetVariableVec3(TEXT("User.Up"),Rotation.GetUpVector());
    DragonFX->SetVariableFloat(TEXT("User.Strength"),1.f);
    DragonFX->SetVariableFloat(TEXT("User.EmissionScale"),FMath::Min(FMath::Clamp(float(Age)/.08f,0.f,1.f),FMath::Clamp(float(C.Duration-Age)/.12f,0.f,1.f)));
    DragonProbeClock-=Delta;
    if(DragonProbeClock<=0)
    {
        DragonProbeClock=.10f;
        UpdateDragonBreathOcclusion(Origin,Rotation);
    }
}

void UFPSFireMagicComponent::UpdateDragonBreathOcclusion(const FVector& Origin,const FQuat& Rotation)
{
    if(!DragonFX)return;
    auto* Pawn=Cast<APawn>(GetOwner());
    const auto& C=DragonView().Cast;
    static const FName RayNames[]={TEXT("User.Ray0"),TEXT("User.Ray1"),TEXT("User.Ray2"),TEXT("User.Ray3"),TEXT("User.Ray4"),TEXT("User.Ray5"),TEXT("User.Ray6"),TEXT("User.Ray7"),TEXT("User.Ray8")};
    static const FName NormalNames[]={TEXT("User.HitNormal0"),TEXT("User.HitNormal1"),TEXT("User.HitNormal2"),TEXT("User.HitNormal3"),TEXT("User.HitNormal4"),TEXT("User.HitNormal5"),TEXT("User.HitNormal6"),TEXT("User.HitNormal7"),TEXT("User.HitNormal8")};
    for(int32 I=0;I<9;++I)
    {
        const float Angle=FMath::DegreesToRadians(FMath::Lerp(-C.ArcDegrees*.5f,C.ArcDegrees*.5f,I/8.f));
        const FVector Direction=Rotation.RotateVector(FVector(FMath::Cos(Angle),FMath::Sin(Angle),0));
        FHitResult Hit;
        const bool bBlocked=FireMagic::TraceSurface(Pawn,Origin,Origin+Direction*C.Radius,Hit,true);
        DragonFX->SetVariableFloat(RayNames[I],bBlocked?FMath::Max(0.f,Hit.Distance-12.f):C.Radius);
        DragonFX->SetVariableVec3(NormalNames[I],bBlocked?Hit.ImpactNormal.GetSafeNormal():-Direction);
    }
}

void UFPSFireMagicComponent::StopDragonBreath(bool bTrain)
{
    const auto* Pawn=Cast<APawn>(GetOwner());
    auto& State=Pawn&&!Pawn->HasAuthority()&&Pawn->IsLocallyControlled()?DragonPrediction:DragonState;
    const bool WasActive=State.bActive;State.bActive=false;PresentDragonBreath();
    if(!WasActive)return;
    if(GetOwner()->HasAuthority())
    {
        GetOwner()->ForceNetUpdate();
        if(const auto* HP=GetOwner()->FindComponentByClass<UFPSCombatHealthComponent>();HP&&HP->IsDead())bTrain=false;
        if(bTrain)if(auto* M=DragonRewardModel.Get())M->FinishFireMagicCast(TEXT("dragonBreath"),DragonRewards);
    }
    DragonRewards=FFireMagicRewards();
    DragonRewardModel.Reset();
}

void UFPSFireMagicComponent::RequestDragonStop()
{
    if(GetNetMode()==NM_Client&&DragonLocalCastId&&DragonCancelledCastId!=DragonLocalCastId)
    {
        DragonCancelledCastId=DragonLocalCastId;
        NetCast::Send(GetOwner(),TEXT("dragonBreath"),4,FVector::ZeroVector,FVector::UpVector,0,nullptr,0,FVector::ForwardVector,DragonLocalCastId);
    }
    bDragonAwaitingRelease=false;
    StopDragonBreath(true);
}

void UFPSFireMagicComponent::NetStopDragonBreath(uint32 CastId)
{
    if(GetOwner()->HasAuthority()&&CastId&&DragonState.CastId==CastId)StopDragonBreath(true);
}

void UFPSFireMagicComponent::FinishDragonBreathForRemoval()
{
    if(GetOwner()->HasAuthority())StopDragonBreath(true);
}

void UFPSFireMagicComponent::ConfirmDragonRelease(uint32 CastId)
{
    if(!CastId||CastId!=DragonLocalCastId||DragonConfirmedCastId==CastId)return;
    DragonConfirmedCastId=CastId;bDragonAwaitingRelease=false;
    if(auto* M=Model())M->CommitDragonBreathRelease();
    // A delayed receipt must not consume a newer meteor/armor gesture payment.
    if(CommittedSkill.IsNone()&&IsDragonBreathActive())
        if(auto* H=Hands();H&&H->IsSpellGesture(this))H->TakeGesturePayment();
}

void UFPSFireMagicComponent::NetDragonCastResult(uint8 Phase,uint8 Code,uint32 CastId)
{
    if(!CastId||CastId!=DragonLocalCastId)return;
    if(Code==0)
    {
        if(Phase==1)ConfirmDragonRelease(CastId);
        return;
    }
    if(Phase>1||DragonConfirmedCastId==CastId)return;
    const bool Pending=CommittedSkill==TEXT("dragonBreath");
    const bool Cancelled=DragonCancelledCastId==CastId;
    if(auto* M=Model())M->RefundUnreleasedCast(Pending&&Hands()?Hands()->TakeGesturePayment():0.f,TEXT("dragonBreath"));
    bDragonAwaitingRelease=false;DragonCancelledCastId=CastId;
    StopDragonBreath(false);
    if(Pending){CommittedSkill=NAME_None;bNetPaid=false;if(auto* H=Hands())H->CancelSpellGesture(this);}
    if(QueuedSkill==TEXT("dragonBreath"))QueuedSkill=NAME_None;
    if(!Cancelled)Feedback(TEXT("dragonBreath"),TEXT("施法失败"));
}
