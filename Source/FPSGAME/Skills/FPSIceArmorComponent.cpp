#include "FPSIceArmorComponent.h"
#include "FPSFireballComponent.h"
#include "PlayerSkillPreparation.h"
#include "NetCastUtils.h"
#include "FireMagicArea.h"
#include "EnemyAttackDamage.h"
#include "HolyLightTargets.h"
#include "../FPSGAMECharacter.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/StatusEffectsComponent.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Combat/CombatFormulaRuntime.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Monsters/BoundCongregateCaptureComponent.h"
#include "CorrosivePusDamage.h"
#include "Components/CapsuleComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "GameFramework/GameStateBase.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"
#include "Engine/StaticMesh.h"
#include "Engine/SkeletalMesh.h"
#include "NiagaraSystem.h"
#include "Materials/MaterialInterface.h"
#include "Net/UnrealNetwork.h"

UFPSIceArmorComponent::UFPSIceArmorComponent()
{PrimaryComponentTick.bCanEverTick=true;PrimaryComponentTick.TickGroup=TG_PostUpdateWork;SetIsReplicatedByDefault(true);}
UColdSteelStatusModel* UFPSIceArmorComponent::Model() const
{return GetWorld()&&GetWorld()->GetGameInstance()?GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr;}
UFPSFireballComponent* UFPSIceArmorComponent::Hands() const{return GetOwner()->FindComponentByClass<UFPSFireballComponent>();}
double UFPSIceArmorComponent::Clock() const
{return GetWorld()->GetGameState()?GetWorld()->GetGameState()->GetServerWorldTimeSeconds():GetWorld()->GetTimeSeconds();}
const FIceArmorState& UFPSIceArmorComponent::View() const{return bAwaiting?Prediction:State;}
float UFPSIceArmorComponent::Remaining() const
{const auto& S=View();return S.bActive?FMath::Max(0.,S.StartedAt+S.Cast.Duration-Clock()):0.f;}
float UFPSIceArmorComponent::DefenseBonus(bool Magic) const
{
    if(Remaining()<=0)return 0;
    if(const auto* S=GetOwner()->FindComponentByClass<UCombatStatusFormula>();S&&S->IsImmune())return 0;
    return Magic?View().Cast.MagicDefense:View().Cast.PhysicalDefense;
}
void UFPSIceArmorComponent::Feedback(const TCHAR* Text){Message=Text;MessageUntil=Clock()+2.;}
bool UFPSIceArmorComponent::IsHandOccupiedNotice() const
{const auto* P=Cast<AFPSGAMECharacter>(GetOwner());return P&&P->IsSpellHandHeld()&&HandNotice.Active(GetWorld()->GetTimeSeconds());}
float UFPSIceArmorComponent::HandNoticeAlpha() const{return HandNotice.Alpha(GetWorld()->GetTimeSeconds());}
float UFPSIceArmorComponent::HandNoticeRise() const{return HandNotice.Rise(GetWorld()->GetTimeSeconds());}
FString UFPSIceArmorComponent::StatusText() const
{
    if(IsHandOccupiedNotice())return TEXT("左手占用");if(Clock()<MessageUntil)return Message;
    if(bQueued)return TEXT("等待动作");if(bCommitted)return TEXT("凝结");
    if(Remaining()>0)return FString::Printf(TEXT("冰甲 %.1fs"),Remaining());
    if(const auto* M=Model();M&&M->IceArmorCooldown()>0)return FString::Printf(TEXT("%.1f"),M->IceArmorCooldown());return FString();
}
float UFPSIceArmorComponent::CooldownFraction() const
{const auto* M=Model();return M?FMath::Clamp(M->IceArmorCooldown()/FMath::Max(.1f,M->IceArmorCooldownDuration()),0.f,1.f):0.f;}
void UFPSIceArmorComponent::BeginPlay()
{
    Super::BeginPlay();AddTickPrerequisiteActor(GetOwner());
    if(auto* Body=GetOwner()->FindComponentByClass<UFPSPlayerBodyComponent>())AddTickPrerequisiteComponent(Body);
    if(GetNetMode()==NM_DedicatedServer)return;
    PlayerSkillAssets::Defer(GetOwner(),TEXT("iceArmor"),FSimpleDelegate::CreateWeakLambda(this,[this]()
    {
        ShellMeshes.Reset();for(const TCHAR* Path:IceArmorAssets::Shells)ShellMeshes.Add(PlayerSkillAssets::Resolve<USkeletalMesh>(Path));
        ChipMesh=PlayerSkillAssets::Resolve<UStaticMesh>(IceArmorAssets::Chip);ChipMaterial=PlayerSkillAssets::Resolve<UMaterialInterface>(IceArmorAssets::ChipMaterial);
        MistSystem=PlayerSkillAssets::Resolve<UNiagaraSystem>(IceArmorAssets::Mist);LensMesh=PlayerSkillAssets::Resolve<UStaticMesh>(IceArmorAssets::Lens);
        ArmorMaterial=PlayerSkillAssets::Resolve<UMaterialInterface>(IceArmorAssets::Material);LensMaterial=PlayerSkillAssets::Resolve<UMaterialInterface>(IceArmorAssets::LensMaterial);
        CastSound=PlayerSkillAssets::Resolve<USoundBase>(IceArmorAssets::CastSound);UpdateVisuals();
    }));
}
void UFPSIceArmorComponent::Trigger()
{
    auto* P=Cast<AFPSGAMECharacter>(GetOwner());if(!P||!P->IsLocallyControlled()||bCommitted)return;
    if(P->IsSpellHandHeld()){HandNotice.Show(GetWorld()->GetTimeSeconds());bQueued=false;return;}
    bQueued=true;ServiceQueue();
}
void UFPSIceArmorComponent::ServiceQueue()
{
    if(!bQueued)return;auto* P=Cast<AFPSGAMECharacter>(GetOwner());auto* M=Model();auto* H=Hands();if(!P||!M||!H)return;
    const auto* PC=Cast<APlayerController>(P->GetController());if(!PC||PC->IsLookInputIgnored()||PC->IsMoveInputIgnored()){bQueued=false;return;}
    if(P->IsSpellHandHeld()){HandNotice.Show(GetWorld()->GetTimeSeconds());bQueued=false;return;}
    if(H->HasOtherPreparedSpell(this)){Feedback(TEXT("先释放已积蓄魔法"));bQueued=false;return;}
    if(H->BlocksNewLeftHandAction()||P->IsSpellHandBusy())return;
    if(UBoundCongregateCaptureComponent::IsCaptured(P)){Feedback(TEXT("受控"));bQueued=false;return;}
    if(const auto* S=P->FindComponentByClass<UCombatStatusFormula>();S&&S->IsImmune()){Feedback(TEXT("状态免疫"));bQueued=false;return;}
    Pending=M->IceArmorStats();
    if(M->IceArmorCooldown()>0||!M->CanSpendMana(Pending.ManaCost)){Feedback(M->IceArmorCooldown()>0?TEXT("冷却"):TEXT("缺蓝"));bQueued=false;return;}
    if(!H->TryBeginSpellGesture(this,false,Pending.CastSpeed,FSimpleDelegate::CreateUObject(this,&ThisClass::Release)))return;
    bQueued=false;const float Before=M->Snapshot().Mana;
    if(!M->BeginIceArmorCast(Pending)){H->CancelSpellGesture(this);return;}
    H->RecordGesturePayment(Before,M->Snapshot().Mana,true);bCommitted=true;PendingRefund=0;
    if(GetNetMode()==NM_Client){LocalCastId=NetCast::Send(P,TEXT("iceArmor"),0);if(!LocalCastId){Cancel();Feedback(TEXT("联机施法未就绪"));}}
}
void UFPSIceArmorComponent::Release()
{
    if(!bCommitted)return;
    if(const auto* S=GetOwner()->FindComponentByClass<UCombatStatusFormula>();S&&S->IsImmune()){Cancel();Feedback(TEXT("状态免疫"));return;}
    if(UBoundCongregateCaptureComponent::IsCaptured(GetOwner())){Cancel();return;}
    bCommitted=false;auto* P=Cast<APawn>(GetOwner());PendingRefund=Hands()?Hands()->TakeGesturePayment():0.f;
    if(GetNetMode()==NM_Client)
    {
        NetCast::Send(P,TEXT("iceArmor"),1,FVector::ZeroVector,FVector::UpVector,0,nullptr,0,FVector::ForwardVector,LocalCastId);
        Start(Pending,LocalCastId,nullptr);
    }
    else {PendingRefund=0;Start(Pending,0,NetCast::AuthorityModel(P,GetWorld()->GetGameInstance()));}
}
void UFPSIceArmorComponent::Cancel()
{
    bQueued=false;if(!bCommitted)return;
    if(auto* M=Model())M->RefundUnreleasedCast(Hands()?Hands()->TakeGesturePayment():0.f,TEXT("iceArmor"));
    if(GetNetMode()==NM_Client&&LocalCastId)NetCast::Send(GetOwner(),TEXT("iceArmor"),2,FVector::ZeroVector,FVector::UpVector,0,nullptr,0,FVector::ForwardVector,LocalCastId);
    bCommitted=false;if(auto* H=Hands())H->CancelSpellGesture(this);Feedback(TEXT("施法中断"));
}
void UFPSIceArmorComponent::Start(const FIceArmorCast& Spell,uint32 CastId,UColdSteelStatusModel* OwnerModel)
{
    End(true);ClearVisuals();PulseClock=0;TrainingSources.Reset();Experience=Spell.CastExperience;
    if(GetOwner()->HasAuthority())
    {
        RewardModel=OwnerModel;State.Cast=Spell;State.CastId=CastId;++State.Serial;State.StartedAt=Clock();State.bActive=true;GetOwner()->ForceNetUpdate();
    }
    else {Prediction.Cast=Spell;Prediction.CastId=CastId;Prediction.StartedAt=Clock();Prediction.bActive=true;bAwaiting=true;}
    RefreshStatus();UpdateVisuals();if(CastSound&&GetNetMode()!=NM_DedicatedServer)UGameplayStatics::PlaySoundAtLocation(this,CastSound,GetOwner()->GetActorLocation(),.65f,1.1f);
}
bool UFPSIceArmorComponent::NetRelease(APawn* Caster,const FColdSteelNetCastRequest& Req,UColdSteelStatusModel* OwnerModel,const FIceArmorCast& Spell)
{
    if(Caster!=GetOwner()||!Caster->HasAuthority()||!OwnerModel||!Req.CastId||Req.SkillId!=TEXT("iceArmor"))return false;
    if(const auto* S=Caster->FindComponentByClass<UCombatStatusFormula>();S&&S->IsImmune())return false;
    Start(Spell,Req.CastId,OwnerModel);return true;
}
void UFPSIceArmorComponent::NetCastResult(uint8 Phase,uint8 Code,uint32 CastId)
{
    if(!CastId||CastId!=LocalCastId)return;
    if(!Code){if(Phase==1){ConfirmedCastId=CastId;PendingRefund=0;}return;}
    if(Phase>1||ConfirmedCastId==CastId||RejectedCastId==CastId)return;RejectedCastId=CastId;
    const float Refund=bCommitted&&Hands()?Hands()->TakeGesturePayment():PendingRefund;PendingRefund=0;
    if(auto* M=Model())M->RefundUnreleasedCast(Refund,TEXT("iceArmor"));
    if(bCommitted){bCommitted=false;if(auto* H=Hands())H->CancelSpellGesture(this);}bQueued=false;
    if(bAwaiting)End(false);OnRep_State();Feedback(TEXT("施法失败"));
}
void UFPSIceArmorComponent::OnRep_State()
{
    if(bAwaiting&&State.CastId!=LocalCastId)return;
    if(State.CastId&&State.CastId==LocalCastId){ConfirmedCastId=State.CastId;PendingRefund=0;}
    bAwaiting=false;Prediction.bActive=false;
    if(const auto* H=GetOwner()->FindComponentByClass<UFPSCombatHealthComponent>();H&&H->IsDead()){End(false);return;}
    RefreshStatus();UpdateVisuals();
    const auto* P=Cast<APawn>(GetOwner());
    if(State.bActive&&Remaining()>0&&Clock()-State.StartedAt<.75&&SoundSerial!=State.Serial&&P&&!P->IsLocallyControlled()&&CastSound)
        UGameplayStatics::PlaySoundAtLocation(this,CastSound,GetOwner()->GetActorLocation(),.65f,1.1f);
    SoundSerial=State.Serial;
}
void UFPSIceArmorComponent::RefreshStatus()
{
    auto* S=UStatusEffectsComponent::GetOrCreate(GetOwner());S->Remove(TEXT("iceArmor"));
    if(Remaining()>0)S->SetTimed(TEXT("iceArmor"),Remaining());
    if(auto* M=Model();M&&Cast<APawn>(GetOwner())&&Cast<APawn>(GetOwner())->IsLocallyControlled())M->OnChanged.Broadcast();
}
void UFPSIceArmorComponent::Pulse()
{
    auto* P=Cast<AFPSGAMECharacter>(GetOwner());if(!P||!P->HasAuthority())return;
    const auto& C=State.Cast;const FVector Feet=P->GetActorLocation()-FVector(0,0,P->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()-5);
    for(AActor* Target:FireMagic::GroundTargets(P,Feet,FVector::UpVector,C.Radius))
        UCombatStatusFormula::GetOrAdd(Target)->AddChill(1,C.ChillSeconds,C.SlowPerStack,true);
}
void UFPSIceArmorComponent::ObserveAcceptedDamage(AActor* Source,const UDamageType* Type,float Damage)
{
    if(!GetOwner()->HasAuthority()||Remaining()<=0||Damage<=0||!IsValid(Source)||Source==GetOwner()||!Type)return;
    auto* Combat=Source->FindComponentByClass<UMonsterCombatComponent>();if(!Combat||HolyLightTargets::IsFriendly(Source))return;
    const bool Melee=Type->IsA<UEnemyMeleeDamage>();
    const bool Ranged=Type->IsA<UEnemyRangedDamage>()||(CombatFormulaRuntime::IsMagic(Type)&&!Type->IsA<UStatusMagicDamage>()&&!Type->IsA<UCorrosivePusDamage>());
    if(!Melee&&!Ranged)return;const auto& C=State.Cast;
    if(Clock()-Impact.At>=.08||Impact.CastSerial!=State.Serial)
    {
        ++Impact.Serial;Impact.CastSerial=State.Serial;Impact.At=Clock();
        const FVector Direction=(Source->GetActorLocation()-GetOwner()->GetActorLocation()).GetSafeNormal(UE_SMALL_NUMBER,GetOwner()->GetActorForwardVector());
        Impact.LocalDirection=GetOwner()->GetActorTransform().InverseTransformVectorNoScale(Direction);
        OnRep_Impact();GetOwner()->ForceNetUpdate();
    }
    if(Melee&&!Combat->IsDead())UCombatStatusFormula::GetOrAdd(Source)->AddChill(1,C.ChillSeconds,C.SlowPerStack,true);
    if(Source->ActorHasTag(TEXT("Summoned"))||Source->ActorHasTag(TEXT("NoSkillTraining"))||Experience>=C.ExperienceCap)return;
    const double Now=Clock();const TWeakObjectPtr<AActor> Key=Source;
    if(const auto* Last=TrainingSources.Find(Key);Last&&Now-*Last<C.TrainingSourceInterval)return;
    if(TrainingSources.Num()>=32)TrainingSources.Reset();TrainingSources.Add(Key,Now);
    Experience=FMath::Min(C.ExperienceCap,Experience+(Melee?C.MeleeExperience:C.RangedExperience));
}
void UFPSIceArmorComponent::End(bool bTrain)
{
    const bool Had=State.bActive||Prediction.bActive||RewardModel.IsValid();auto* M=RewardModel.Get();const int32 XP=Experience;
    RewardModel.Reset();Experience=0;TrainingSources.Reset();PulseClock=0;bAwaiting=false;Prediction.bActive=false;
    if(GetOwner()->HasAuthority()&&State.bActive){State.bActive=false;GetOwner()->ForceNetUpdate();}
    if(!bTrain)ClearVisuals();if(auto* S=GetOwner()->FindComponentByClass<UStatusEffectsComponent>())S->Remove(TEXT("iceArmor"));
    if(bTrain&&GetOwner()->HasAuthority()&&M)M->FinishIceArmorTraining(XP);
    if(Had)if(auto* Local=Model();Local&&Cast<APawn>(GetOwner())&&Cast<APawn>(GetOwner())->IsLocallyControlled())Local->OnChanged.Broadcast();
}
void UFPSIceArmorComponent::FinishForRemoval(){Cancel();End(true);ClearVisuals();}
void UFPSIceArmorComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick)
{
    Super::TickComponent(Delta,Type,Tick);
    if(const auto* H=GetOwner()->FindComponentByClass<UFPSCombatHealthComponent>();H&&H->IsDead()){Cancel();if(Remaining()>0||RewardModel.IsValid())End(true);ClearVisuals();return;}
    if(bCommitted&&(!Hands()||!Hands()->IsSpellGesture(this)))Cancel();ServiceQueue();
    if(const auto* S=GetOwner()->FindComponentByClass<UCombatStatusFormula>();S&&S->IsImmune()){if(Remaining()>0)End(true);ClearVisuals();return;}
    if(Remaining()<=0){if(RewardModel.IsValid()||bAwaiting)End(true);UpdateVisuals(Delta);return;}
    if(GetOwner()->HasAuthority())
    {
        PulseClock+=Delta;const float Step=FMath::Max(.1f,State.Cast.PulseSeconds);
        // No catch-up burst of cold stacks after a stalled server frame.
        if(PulseClock>=Step){PulseClock=FMath::Fmod(PulseClock,Step);Pulse();}
    }
    OnRep_Impact();UpdateVisuals(Delta);
}
void UFPSIceArmorComponent::EndPlay(EEndPlayReason::Type Reason){FinishForRemoval();Super::EndPlay(Reason);}
void UFPSIceArmorComponent::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{Super::GetLifetimeReplicatedProps(OutLifetimeProps);DOREPLIFETIME(UFPSIceArmorComponent,State);DOREPLIFETIME(UFPSIceArmorComponent,Impact);}
