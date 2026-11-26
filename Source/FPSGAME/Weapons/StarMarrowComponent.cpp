#include "StarMarrowComponent.h"
#include "GunsmithSystem.h"
#include "RuneSwordComponent.h"
#include "StarMarrowChargeMotion.h"
#include "../FPSGAMECharacter.h"
#include "../FPSGAMEPlayerController.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Skills/NetCastUtils.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Monsters/BoundCongregateCaptureComponent.h"
#include "../Building/VoxelBuildComponent.h"
#include "GameFramework/GameStateBase.h"
#include "Engine/StreamableManager.h"
#include "Engine/AssetManager.h"
#include "Engine/Texture2D.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Engine/World.h"
#include "NiagaraComponent.h"
#include "Net/UnrealNetwork.h"
#include "Kismet/GameplayStatics.h"
#include "Components/AudioComponent.h"
#include "Sound/SoundBase.h"

UStarMarrowComponent::UStarMarrowComponent()
{
    SetIsReplicatedByDefault(true);PrimaryComponentTick.bCanEverTick=true;
    PrimaryComponentTick.bStartWithTickEnabled=false;PrimaryComponentTick.TickGroup=TG_PostUpdateWork;
}
bool UStarMarrowComponent::Equipped(const UColdSteelStatusModel* M)
{
    const auto* I=M&&!M->ActiveProductionTool()?M->Equipped():nullptr;
    const auto* G=M?M->GetGameInstance()->GetSubsystem<UGunsmithSystem>():nullptr;
    return I&&G&&I->Definition==TEXT("ue_frost_crystal_sword")&&G->Installed(*I).FindRef(TEXT("blade_1"))==TEXT("star_marrow");
}
void UStarMarrowComponent::Configure(const UColdSteelStatusModel* M)
{
    Profile=M;const FString Next=Equipped(M)?M->Equipped()->InstanceId:FString();
    if(Next!=EquippedInstance){Clear();HUDVisibleUntil=0.;}
    EquippedInstance=Next;EquippedData=Next.IsEmpty()?FString():M->Equipped()->Data;
    if(!Next.IsEmpty()){LoadFlames();LoadHUD();LoadChargeSound();}
    if(Remaining()>0.f)OnRep_State();
}
bool UStarMarrowComponent::IsEquipped() const
{
    const auto* M=Profile.Get();const auto* H=GetOwner()->FindComponentByClass<UFPSCombatHealthComponent>();
    const auto* Item=M&&!M->ActiveProductionTool()?M->Equipped():nullptr;
    return !EquippedInstance.IsEmpty()&&Item&&Item->InstanceId==EquippedInstance&&(Item->Data==EquippedData||Equipped(M))&&(!H||!H->IsDead());
}
double UStarMarrowComponent::Clock() const
{
    const auto* W=GetWorld();const auto* G=W?W->GetGameState():nullptr;
    return G?G->GetServerWorldTimeSeconds():W?W->GetTimeSeconds():0.;
}
float UStarMarrowComponent::Remaining() const
{
    if(const auto* H=GetOwner()->FindComponentByClass<UFPSCombatHealthComponent>();H&&H->IsDead())return 0.f;
    const auto* P=Cast<APawn>(GetOwner());
    if((GetOwner()->HasAuthority()||(P&&P->IsLocallyControlled()))&&(!IsEquipped()||ChargedInstance!=EquippedInstance))return 0.f;
    return FMath::Max(0.f,float(ChargedUntil-Clock()));
}
bool UStarMarrowComponent::ChargesDamage(const AActor* Source)
{
    if(!Source)return false;
    const auto* Pawn=Cast<APawn>(Source);if(!Pawn)Pawn=Source->GetInstigator();
    const auto* Core=Pawn?Pawn->FindComponentByClass<UStarMarrowComponent>():nullptr;
    return Core&&Core->Remaining()>0.f;
}
bool UStarMarrowComponent::CanActivate() const
{
    const auto* Player=Cast<AFPSGAMECharacter>(GetOwner());
    const auto* PC=Player?Cast<APlayerController>(Player->GetController()):nullptr;
    const auto* Build=PC?PC->FindComponentByClass<UVoxelBuildComponent>():nullptr;
    const auto* Sword=Player?Player->FindComponentByClass<URuneSwordComponent>():nullptr;
    if(Player&&Player->IsLocallyControlled()&&(!Sword||!Sword->IsStarMarrowChargeMotionReady()))return false;
    return Player&&IsEquipped()&&Remaining()<=0.f&&!Player->IsTraversing()&&!Player->IsLeftHandHeldForCast()
        &&!UBoundCongregateCaptureComponent::IsCaptured(Player)&&(!Sword||!Sword->IsBusy())
        &&(!PC||!PC->IsLocalController()||!AFPSGAMEPlayerController::BlocksOngoingActions(PC))&&(!Build||!Build->IsBuilding());
}
void UStarMarrowComponent::Trigger()
{
    const auto* Pawn=Cast<APawn>(GetOwner());
    if(!Pawn||!Pawn->IsLocallyControlled()||IsActivationPending()||!CanActivate())return;
    auto* M=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(GetOwner()->HasAuthority())
    {
        if(!ActivateCharge(M)){Feedback=TEXT("魔法不足");FeedbackUntil=Clock()+1.5;}
        return;
    }
    // Predict the gesture only. The authority mirror owns the balance even if rejection crosses a profile update.
    const float Cost=FMath::Max(0.f,M->Derived(TEXT("maxMp")))*ManaFraction;
    if(!M->CanSpendMana(Cost)){Feedback=TEXT("魔法不足");FeedbackUntil=Clock()+1.5;return;}
    auto* State=NetCast::StateFor(Pawn);
    if(!State)return;
    FColdSteelNetCastRequest Request;
    Request.SkillId=TEXT("starMarrowCharge");
    Request.WeaponInstance=EquippedInstance;
    PendingSequence=State->RequestCastSpell(Request);
    if(PendingSequence)
        if(auto* Sword=GetOwner()->FindComponentByClass<URuneSwordComponent>())bPredictedChargeMotion=Sword->BeginStarMarrowChargeMotion();
}
bool UStarMarrowComponent::ActivateCharge(UColdSteelStatusModel* M)
{
    if(!GetOwner()->HasAuthority()||!M)return false;
    Configure(M);
    if(!CanActivate()||!M->BeginStarMarrowCharge())return false;
    ChargedInstance=EquippedInstance;ChargedUntil=Clock()+Duration;
    GetOwner()->ForceNetUpdate();OnRep_State();return true;
}
void UStarMarrowComponent::NetCastResult(uint32 Sequence,uint8 Code)
{
    if(!PendingSequence||Sequence!=PendingSequence)return;
    if(Code)
    {
        if(bPredictedChargeMotion&&Remaining()<=0.f)
            if(auto* Sword=GetOwner()->FindComponentByClass<URuneSwordComponent>())Sword->CancelStarMarrowChargeMotion();
        bPredictedChargeMotion=false;
        Feedback=Code==6?TEXT("魔法不足或尚未就绪"):TEXT("充能未释放");FeedbackUntil=Clock()+1.5;
    }
    else if(Remaining()<=0.f)AcceptedRetryAfter=Clock()+StarMarrowChargeMotion::Duration;
    PendingSequence=0;
}
void UStarMarrowComponent::Clear()
{
    PendingSequence=0;
    AcceptedRetryAfter=0.;
    bPredictedChargeMotion=false;
    if(auto* Sword=GetOwner()->FindComponentByClass<URuneSwordComponent>())Sword->CancelStarMarrowChargeMotion();
    HUDVisibleUntil=FMath::Min(HUDVisibleUntil,Clock());
    if(GetOwner()->HasAuthority()&&ChargedUntil>0.){ChargedUntil=0.;ChargedInstance.Reset();GetOwner()->ForceNetUpdate();}
    StopFlames();StopChargeSound(.08f);SetComponentTickEnabled(false);
}
void UStarMarrowComponent::OnRep_State()
{
    if(Remaining()>0.f)
    {
        HUDVisibleUntil=ChargedUntil;LoadFlames();LoadHUD();LoadChargeSound();SetComponentTickEnabled(true);
        AcceptedRetryAfter=0.;
        PresentChargeMotion();
    }
    else if(ChargedUntil<=0.&&!PendingSequence)Clear();
    else {HUDVisibleUntil=FMath::Min(HUDVisibleUntil,Clock());StopFlames();StopChargeSound(.08f);SetComponentTickEnabled(false);}
}
void UStarMarrowComponent::PresentChargeMotion()
{
    const auto* Pawn=Cast<APawn>(GetOwner());
    if(!Pawn||!Pawn->IsLocallyControlled()||PresentedChargeUntil==ChargedUntil)return;
    const float Age=FMath::Max(0.f,Duration-Remaining());
    auto* Sword=Pawn->FindComponentByClass<URuneSwordComponent>();
    // Equip, the streamed clip and the charge can arrive in any order.
    if(bPredictedChargeMotion||Age>=StarMarrowChargeMotion::Duration||(Sword&&Sword->BeginStarMarrowChargeMotion(Age)))
    {
        PresentedChargeUntil=ChargedUntil;
        bPredictedChargeMotion=false;
        // Both the local prediction and the later authority confirmation land here; play once.
        PlayChargeSound();
    }
}
void UStarMarrowComponent::LoadChargeSound()
{
    // Loaded beside the flames: the charge can be triggered before the async
    // assets finish, so this is a streamed reference rather than a load on G.
    if(ChargeSound||GetNetMode()==NM_DedicatedServer)return;
    const FSoftObjectPath Path(TEXT("/Game/Weapons/FrostCrystalSword20260915/StarMarrowChargeAudio20261104/S_StarMarrow_Charge.S_StarMarrow_Charge"));
    UAssetManager::GetStreamableManager().RequestAsyncLoad(Path,FStreamableDelegate::CreateWeakLambda(this,[this,Path]()
    {ChargeSound=Cast<USoundBase>(Path.ResolveObject());}));
}
void UStarMarrowComponent::PlayChargeSound()
{
    if(bChargeSoundPlayed||GetNetMode()==NM_DedicatedServer)return;
    const auto* Pawn=Cast<APawn>(GetOwner());
    if(!Pawn||!Pawn->IsLocallyControlled())return;
    // The equip-time async load can still be in flight on the first charge; leave
    // the flag clear so the next tick plays it instead of silently skipping the cue.
    if(!ChargeSound){LoadChargeSound();return;}
    bChargeSoundPlayed=true;
    // Its own component so a cancelled charge can fade the remaining tail
    // instead of letting it ring over the next action.
    ChargeAudio=UGameplayStatics::CreateSound2D(this,ChargeSound,1.f,1.f,0.f,nullptr,false,true);
}
void UStarMarrowComponent::StopChargeSound(float FadeSeconds)
{
    if(IsValid(ChargeAudio))
    {
        if(FadeSeconds>0.f)ChargeAudio->FadeOut(FadeSeconds,0.f);
        else ChargeAudio->Stop();
    }
    ChargeAudio=nullptr;
    bChargeSoundPlayed=false;
}
void UStarMarrowComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Function)
{
    Super::TickComponent(Delta,Type,Function);
    if(Remaining()<=0.f){Clear();return;}
    PresentChargeMotion();
    // The motion may already be presented while the sound is still streaming; retry
    // here until it starts rather than losing the cue on the first G.
    if(PresentedChargeUntil!=0.&&!bChargeSoundPlayed)PlayChargeSound();
    UpdateFlames(Delta);
}
bool UStarMarrowComponent::HUDVisible() const
{const auto* P=Cast<APawn>(GetOwner());return P&&P->IsLocallyControlled()&&IsEquipped()&&(HUDAlpha()>0.f||IsActivationPending()||Clock()<FeedbackUntil);}
float UStarMarrowComponent::HUDAlpha() const
{
    if(HUDVisibleUntil<=0.||!IsEquipped())return 0.f;
    const double Now=Clock();
    const float In=FMath::Clamp(float((Now-HUDVisibleUntil+Duration)/.18),0.f,1.f);
    const float Out=FMath::Clamp(float(1.-(Now-HUDVisibleUntil)/.4),0.f,1.f);
    return In*Out;
}
namespace
{
const FSoftObjectPath ChargeShortcutIconPath(TEXT("/Game/Weapons/FrostCrystalSword20260915/StarMarrowCharge20261103/T_StarMarrowChargeIcon.T_StarMarrowChargeIcon"));
}
UTexture2D* UStarMarrowComponent::ShortcutIcon() const
{return Cast<UTexture2D>(ChargeShortcutIconPath.ResolveObject());}
void UStarMarrowComponent::LoadHUD()
{
    const auto* Pawn=Cast<APawn>(GetOwner());
    if(!Pawn||!Pawn->IsLocallyControlled()||GetNetMode()==NM_DedicatedServer)return;
    if((ChargeHUDMaterial&&ShortcutIcon())||(HUDLoad&&!HUDLoad->HasLoadCompleted()))return;
    const FSoftObjectPath Path(TEXT("/Game/Weapons/FrostCrystalSword20260915/StarMarrowChargeHUD20261103/M_StarMarrowChargeHUD.M_StarMarrowChargeHUD"));
    // The existing handle holds both resources; shortcut refresh only reads
    // the resolved texture and never imports a PNG or waits for streaming.
    HUDLoad=UAssetManager::GetStreamableManager().RequestAsyncLoad(TArray<FSoftObjectPath>{Path,ChargeShortcutIconPath},FStreamableDelegate::CreateWeakLambda(this,[this,Path]()
    {if(!ChargeHUDMaterial)if(auto* Parent=Cast<UMaterialInterface>(Path.ResolveObject()))ChargeHUDMaterial=UMaterialInstanceDynamic::Create(Parent,this);}));
}
FString UStarMarrowComponent::HUDLabel() const
{
    if(Remaining()>0.f)return FString::Printf(TEXT("[G] 充能  %.1f s  ·  伤害+30%% / 全魔法"),Remaining());
    if(IsActivationPending())return TEXT("[G] 充能  ·  释放中");
    if(Clock()<FeedbackUntil)return TEXT("[G] 充能  ·  ")+Feedback;
    return FString();
}
void UStarMarrowComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    StopChargeSound(0.f);ChargeSound=nullptr;
    if(FlameLoad)FlameLoad->CancelHandle();FlameLoad.Reset();
    if(HUDLoad)HUDLoad->CancelHandle();HUDLoad.Reset();ChargeHUDMaterial=nullptr;
    for(auto& FX:FlameFX)if(FX)FX->DestroyComponent();
    FlameFX.Reset();FlameSystem=nullptr;Super::EndPlay(Reason);
}
void UStarMarrowComponent::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{Super::GetLifetimeReplicatedProps(OutLifetimeProps);DOREPLIFETIME(UStarMarrowComponent,ChargedUntil);DOREPLIFETIME(UStarMarrowComponent,ChargedInstance);}

void UColdSteelStatusModel::ReconcileStarMarrowSpend(double Total)
{
    if(!FMath::IsFinite(Total)||Total<=Current.StarMarrowManaSpent)return;
    Current.MergeStarMarrowSpend(Total);
    bTrainingDirty=true;TrainingFlushAccumulator=0.f;OnChanged.Broadcast();
}

bool UColdSteelStatusModel::BeginStarMarrowCharge()
{
    if(!UStarMarrowComponent::Equipped(this))return false;
    SyncRuntime();const float Cost=FMath::Max(0.f,float(Derived(TEXT("maxMp"))))*UStarMarrowComponent::ManaFraction;
    if(!CanSpendMana(Cost))return false;
    auto State=Snapshot();if(!HasInfiniteMana())State.MergeStarMarrowSpend(State.StarMarrowManaSpent+Cost);
    return CommitState(MoveTemp(State));
}
