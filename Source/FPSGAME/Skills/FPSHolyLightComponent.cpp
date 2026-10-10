#include "FPSHolyLightComponent.h"
#include "../Monsters/BoundCongregateCaptureComponent.h"
#include "../Dungeons/WardBreakableGlass.h"
#include "FPSHolyLightEffect.h"
#include "HolyLightTargets.h"
#include "FPSFireballComponent.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Weapons/RuneSwordComponent.h"
#include "Camera/CameraComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "NiagaraSystem.h"
#include "Sound/SoundBase.h"
#include "NetCastUtils.h"

UFPSHolyLightComponent::UFPSHolyLightComponent(){PrimaryComponentTick.bCanEverTick=true;}
void UFPSHolyLightComponent::BeginPlay()
{
    Super::BeginPlay();AddTickPrerequisiteActor(GetOwner());
    MoteSystem=LoadObject<UNiagaraSystem>(nullptr,TEXT("/Game/Skills/HolyLight/NS_HolyLightMotes.NS_HolyLightMotes"));
    CastSounds.Add(LoadObject<USoundBase>(nullptr,TEXT("/Game/Skills/HolyLight/S_HolyLightCast.S_HolyLightCast")));
}
UColdSteelStatusModel* UFPSHolyLightComponent::Model() const
{return GetWorld()&&GetWorld()->GetGameInstance()?GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr;}
UFPSFireballComponent* UFPSHolyLightComponent::Hands() const{return GetOwner()->FindComponentByClass<UFPSFireballComponent>();}
bool UFPSHolyLightComponent::IsTarget(AActor* Target) const
{
    if(UWardBreakableGlass::IntactPane(Target))return true;
    return HolyLightTargets::IsAlive(Target)&&(HolyLightTargets::IsFriendly(Target)||Target->FindComponentByClass<UMonsterCombatComponent>());
}
bool UFPSHolyLightComponent::VisibleFrom(AActor* Origin,AActor* Target,const FVector& Start) const
{
    FCollisionQueryParams Query(SCENE_QUERY_STAT(HolyLightSight),true,Origin);Query.AddIgnoredActor(GetOwner());
    const auto* Pane=UWardBreakableGlass::IntactPane(Target);if(!Pane)Query.AddIgnoredActor(Target);
    FHitResult Hit;return !GetWorld()->LineTraceSingleByChannel(Hit,Start,UWardBreakableGlass::TargetPoint(Target),ECC_Visibility,Query) || (Pane && Hit.GetComponent()==Pane);
}
AActor* UFPSHolyLightComponent::SelectTarget(const FHolyLightCast& Spell,FString& Failure) const
{
    const auto* Camera=GetOwner()->FindComponentByClass<UCameraComponent>();if(!Camera)return nullptr;
    const FVector Eye=Camera->GetComponentLocation(),Forward=Camera->GetForwardVector();
    FHitResult AimHit;FCollisionQueryParams AimQuery(SCENE_QUERY_STAT(HolyLightGlassAim),false,GetOwner());
    if(GetWorld()->LineTraceSingleByChannel(AimHit,Eye,Eye+Forward*Spell.Range,ECC_Visibility,AimQuery)
        && Cast<UWardBreakableGlass>(AimHit.GetComponent())){Failure.Empty();return AimHit.GetActor();}
    AActor* Best=nullptr;double Score=DBL_MAX;bool NearAim=false,InRange=false;
    for(TActorIterator<AActor> It(GetWorld());It;++It)
    {
        AActor* Target=*It;if(Target==GetOwner()||!IsTarget(Target)||UWardBreakableGlass::IntactPane(Target))continue;
        const FVector Offset=Target->GetActorLocation()-Eye;const double Along=FVector::DotProduct(Offset,Forward);
        if(Along<=0)continue;
        const double Perpendicular=(Offset-Forward*Along).Size();if(Perpendicular>Spell.AimRadius)continue;
        NearAim=true;if(FVector::Dist(GetOwner()->GetActorLocation(),Target->GetActorLocation())>Spell.Range)continue;
        InRange=true;if(!VisibleFrom(GetOwner(),Target,Eye))continue;
        const double CandidateScore=Perpendicular/FMath::Max(1.,Along);
        if(CandidateScore<Score){Score=CandidateScore;Best=Target;}
    }
    Failure=Best?TEXT(""):!NearAim?TEXT("准星附近无目标"):!InRange?TEXT("超出施法距离"):TEXT("目标被遮挡");return Best;
}
void UFPSHolyLightComponent::Feedback(const FString& Text){Message=Text;MessageUntil=GetWorld()->GetTimeSeconds()+2;}
void UFPSHolyLightComponent::RejectHeldHand(){bQueued=false;HandNotice.Show(GetWorld()->GetTimeSeconds());}
bool UFPSHolyLightComponent::IsHandOccupiedNotice() const
{
    const auto* Player=Cast<AFPSGAMECharacter>(GetOwner());
    return Player&&Player->IsSpellHandHeld()&&GetWorld()&&HandNotice.Active(GetWorld()->GetTimeSeconds());
}
float UFPSHolyLightComponent::HandNoticeAlpha() const{return GetWorld()?HandNotice.Alpha(GetWorld()->GetTimeSeconds()):0;}
float UFPSHolyLightComponent::HandNoticeRise() const{return GetWorld()?HandNotice.Rise(GetWorld()->GetTimeSeconds()):0;}
FString UFPSHolyLightComponent::StatusText() const
{
    if(IsHandOccupiedNotice())return TEXT("左手占用");
    if(GetWorld()&&GetWorld()->GetTimeSeconds()<MessageUntil)return Message;
    if(bQueued)return TEXT("等待施法");if(bCommitted)return TEXT("施法");
    if(auto* M=Model();M&&M->HolyLightCooldown()>0)return FString::Printf(TEXT("%.1f"),M->HolyLightCooldown());return TEXT("");
}
float UFPSHolyLightComponent::CooldownFraction() const
{const auto* M=Model();return M?FMath::Clamp(M->HolyLightCooldown()/FMath::Max(.1f,M->HolyLightCooldownDuration()),0.f,1.f):0;}
void UFPSHolyLightComponent::Trigger(bool bSelf)
{
    if(UBoundCongregateCaptureComponent::IsCaptured(GetOwner()))return;
    auto* Player=Cast<AFPSGAMECharacter>(GetOwner());auto* M=Model();
    if(!Player||!M||!Player->IsLocallyControlled())return;
    if(const auto* Health=Player->FindComponentByClass<UFPSCombatHealthComponent>();Health&&Health->IsDead())return;
    if(bCommitted)return;
    if(const auto* H=Hands();H&&H->HasOtherPreparedSpell(this))
    {bQueued=false;Feedback(TEXT("先释放已积蓄魔法"));return;}
    if(Player->IsSpellHandHeld()){RejectHeldHand();return;}
    if(M->HolyLightCooldown()>0){Feedback(TEXT("冷却"));return;}
    if(!MoteSystem||CastSounds.Num()!=1||CastSounds.Contains(nullptr)){Feedback(TEXT("缺素材"));return;}
    const auto Spell=M->HolyLightStats();FString Failure;
    if(!bSelf&&!SelectTarget(Spell,Failure)){Feedback(Failure);return;}
    if(!M->CanSpendMana(Spell.ManaCost)){Feedback(TEXT("缺蓝"));return;}
    if(auto* Sword=Player->FindComponentByClass<URuneSwordComponent>();Sword&&Sword->IsGuarding())Sword->ReleaseGuard();
    bQueuedSelf=bSelf;bQueued=true;MessageUntil=0;ServiceQueue();
}
void UFPSHolyLightComponent::ServiceQueue()
{
    if(!bQueued)return;
    auto* Player=Cast<AFPSGAMECharacter>(GetOwner());auto* M=Model();auto* H=Hands();if(!Player||!M||!H)return;
    if(H->HasOtherPreparedSpell(this)){bQueued=false;Feedback(TEXT("先释放已积蓄魔法"));return;}
    if(Player->IsSpellHandHeld()){RejectHeldHand();return;}
    const auto* PC=Cast<APlayerController>(Player->GetController());
    if(!PC||PC->IsLookInputIgnored()||PC->IsMoveInputIgnored()){bQueued=false;return;}
    if(H->BlocksNewLeftHandAction()||Player->IsSpellHandBusy())return;
    const auto Spell=M->HolyLightStats();FString Failure;AActor* Target=bQueuedSelf?Player:SelectTarget(Spell,Failure);
    if(!Target){bQueued=false;Feedback(Failure);return;}
    if(M->HolyLightCooldown()>0||!M->CanSpendMana(Spell.ManaCost)){bQueued=false;Feedback(TEXT("未就绪"));return;}
    // Freeze the gesture choice with the actual committed target, including
    // queued Alt self-casts. Other targets keep the shared outward palm push.
    if(!H->TryBeginSpellGesture(this,true,Spell.CastSpeed,FSimpleDelegate::CreateUObject(this,&ThisClass::ReleaseAtContact),Target==Player))return;
    bQueued=false;
    const float BeforeMana=M->Snapshot().Mana;
    if(!M->BeginHolyLightCast(Spell)){H->CancelSpellGesture(this);return;}
    H->RecordGesturePayment(BeforeMana,M->Snapshot().Mana,true);
    CastSnapshot=Spell;LockedTarget=Target;bCommitted=true;MessageUntil=0;
    if(auto* Status=Player->FindComponentByClass<UCombatStatusFormula>())Status->ConsumeChainSpell();
    // 联机客人：凝聚即扣账上报；治疗/伤害由服务端在释放相位结算。
    if(GetWorld()->GetNetMode()==NM_Client){bNetPaid=true;NetCast::Send(Player,TEXT("holyLight"),0,FVector::ZeroVector,FVector::UpVector,Target==Player?1:0);}
}
void UFPSHolyLightComponent::ReleaseAtContact()
{
    if(!bCommitted)return;bCommitted=false;
    auto* Player=Cast<AFPSGAMECharacter>(GetOwner());auto* M=Model();const auto* Camera=GetOwner()->FindComponentByClass<UCameraComponent>();
    AActor* Target=LockedTarget.Get();LockedTarget.Reset();
    if(!Player||!M||!Camera||!IsTarget(Target)||(Target!=Player&&(FVector::Dist(Player->GetActorLocation(),UWardBreakableGlass::TargetPoint(Target))>CastSnapshot.Range||!VisibleFrom(Player,Target,Camera->GetComponentLocation()))))
    {if(M)M->RefundUnreleasedCast(Hands()?Hands()->TakeGesturePayment():0.f,TEXT("holyLight"));Feedback(TEXT("目标已失效或被遮挡"));return;}
    // 联机客人：目标引用上行，服务端权威结算治疗/伤害并生成复制光柱；本地收尾预扣账。
    if(GetWorld()->GetNetMode()==NM_Client)
    {
        NetCast::Send(Player,TEXT("holyLight"),1,Target->GetActorLocation(),FVector::UpVector,Target==Player?1:0,Target);
        if(M)M->FinishHolyLightCast(FHolyLightRewards());
        bNetPaid=false;
        for(const auto& Sound:CastSounds)if(Sound)UGameplayStatics::PlaySoundAtLocation(this,Sound.Get(),Target->GetActorLocation());
        if(auto* Status=UCombatStatusFormula::GetOrAdd(Player))
        {if(CastSnapshot.bGrantChain)Status->AddChainSpell();if(CastSnapshot.CastHasteStacks>0)Status->AddHaste(CastSnapshot.CastHasteStacks,CastSnapshot.CastHasteDuration);}
        return;
    }
    for(const auto& Sound:CastSounds)if(Sound)UGameplayStatics::PlaySoundAtLocation(this,Sound.Get(),Target->GetActorLocation());
    FHolyLightRewards Rewards;
    if(HolyLightTargets::IsFriendly(Target))
    {M->ApplyHolyLightHealing(Target,CastSnapshot,Rewards);Feedback(TEXT("圣光治疗"));}
    else M->ApplyHolyLightHit(Player,Target,Camera->GetComponentLocation(),CastSnapshot,CastSnapshot.Damage,Rewards);
    FActorSpawnParameters P;P.Owner=Player;P.Instigator=Player;P.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    if(auto* Effect=GetWorld()->SpawnActor<AFPSHolyLightEffect>(Target->GetActorLocation(),FRotator::ZeroRotator,P))
    {Effect->InitializeLight(Target,MoteSystem,CastSnapshot);Effects.Add(Effect);}
    M->FinishHolyLightCast(Rewards);
    if(auto* Status=UCombatStatusFormula::GetOrAdd(Player))
    {if(CastSnapshot.bGrantChain)Status->AddChainSpell();if(CastSnapshot.CastHasteStacks>0)Status->AddHaste(CastSnapshot.CastHasteStacks,CastSnapshot.CastHasteDuration);}
}
void UFPSHolyLightComponent::Cancel()
{
    bQueued=false;bCommitted=false;LockedTarget.Reset();
    if(auto* H=Hands())H->CancelSpellGesture(this);
    for(auto& Arc:Effects)if(Arc.IsValid())Arc->Destroy();Effects.Reset();
    // 联机客人：已扣账未释放的凝聚取消——上报服务端退预留。
    if(GetWorld()&&GetWorld()->GetNetMode()==NM_Client&&bNetPaid)NetCast::Send(GetOwner(),TEXT("holyLight"),2);
    bNetPaid=false;
}
void UFPSHolyLightComponent::InterruptPending()
{
    if(bCommitted)Feedback(TEXT("施法中断"));
    // 联机客人：中断视同凝聚取消——Phase2 退款。
    if(GetWorld()&&GetWorld()->GetNetMode()==NM_Client&&bCommitted&&bNetPaid)NetCast::Send(GetOwner(),TEXT("holyLight"),2);
    bNetPaid=false;
    bQueued=bCommitted=false;LockedTarget.Reset();
    // Healing/damage and an already released light keep their own lifetime.
}
// ── 联机服务端入口：验证上报目标→权威治疗/伤害→生成复制光柱 ──
bool UFPSHolyLightComponent::NetRelease(APawn* Caster,const FColdSteelNetCastRequest& Req,UColdSteelStatusModel* Shadow,const FHolyLightCast& Spell)
{
    AActor* Target=(Req.Variant&1)?static_cast<AActor*>(Caster):Req.Target.Get();
    if(!Target||!IsValid(Target))return false;
    const bool bSelf=Target==Caster;
    if(!bSelf)
    {
        if(!IsTarget(Target))return false;
        const FVector Eye=Caster->GetPawnViewLocation();
        if(FVector::Dist(Caster->GetActorLocation(),UWardBreakableGlass::TargetPoint(Target))>Spell.Range*1.15f)return false;
        if(!VisibleFrom(Caster,Target,Eye))return false;
    }
    FHolyLightRewards Rewards;
    if(HolyLightTargets::IsFriendly(Target)||bSelf)
        Shadow->ApplyHolyLightHealing(Target,Spell,Rewards);
    else
        Shadow->ApplyHolyLightHit(Caster,Target,Caster->GetPawnViewLocation(),Spell,Spell.Damage,Rewards);
    Shadow->FinishHolyLightCast(Rewards);
    FActorSpawnParameters P;P.Owner=Caster;P.Instigator=Caster;P.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    if(auto* Effect=GetWorld()->SpawnActor<AFPSHolyLightEffect>(Target->GetActorLocation(),FRotator::ZeroRotator,P))
    {Effect->InitializeLight(Target,MoteSystem,Spell);Effects.Add(Effect);}
    for(const auto& Sound:CastSounds)if(Sound)UGameplayStatics::PlaySoundAtLocation(this,Sound.Get(),Target->GetActorLocation());
    if(auto* Status=UCombatStatusFormula::GetOrAdd(Caster))
    {if(Spell.bGrantChain)Status->AddChainSpell();if(Spell.CastHasteStacks>0)Status->AddHaste(Spell.CastHasteStacks,Spell.CastHasteDuration);}
    return true;
}
void UFPSHolyLightComponent::NetCastRejected(uint8 /*Phase*/,uint8 /*Code*/)
{
    bNetPaid=false;
    if(bCommitted){bCommitted=false;LockedTarget.Reset();if(auto* M=Model())M->RefundUnreleasedCast(Hands()?Hands()->TakeGesturePayment():0.f,TEXT("holyLight"));}
    if(auto* H=Hands())H->CancelSpellGesture(this);
    Feedback(TEXT("施法失败"));
}
void UFPSHolyLightComponent::NetCastCancelled(uint8 /*Phase*/)
{
    bNetPaid=false;
}
void UFPSHolyLightComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick)
{
    Super::TickComponent(Delta,Type,Tick);
    if(const auto* Health=GetOwner()->FindComponentByClass<UFPSCombatHealthComponent>();Health&&Health->IsDead())
    {if(bCommitted)if(auto* M=Model())M->RefundUnreleasedCast(Hands()?Hands()->TakeGesturePayment():0.f,TEXT("holyLight"));Cancel();return;}
    if(bCommitted&&(!Hands()||!Hands()->IsSpellGesture(this))){bCommitted=false;LockedTarget.Reset();}
    Effects.RemoveAll([](const auto& A){return !A.IsValid();});ServiceQueue();
}
void UFPSHolyLightComponent::EndPlay(EEndPlayReason::Type Reason){Cancel();Super::EndPlay(Reason);}
