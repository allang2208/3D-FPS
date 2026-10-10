#include "FPSIceSpikeComponent.h"
#include "../Monsters/BoundCongregateCaptureComponent.h"
#include "FPSIceSpikeVolley.h"
#include "FPSFireballComponent.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Weapons/RuneSwordComponent.h"
#include "Camera/CameraComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInterface.h"
#include "Particles/ParticleSystem.h"
#include "Sound/SoundBase.h"
#include "NiagaraSystem.h"
#include "NetCastUtils.h"
#include "FPSMagicPreview.h"

UFPSIceSpikeComponent::UFPSIceSpikeComponent(){PrimaryComponentTick.bCanEverTick=true;}
void UFPSIceSpikeComponent::BeginPlay()
{
    Super::BeginPlay();AddTickPrerequisiteActor(GetOwner());
    for(int32 I=1;I<=3;++I)
    {
        const FString Path=FString::Printf(TEXT("/Game/Skills/IceSpike/FrostV2/SM_IceSpike_%02d.SM_IceSpike_%02d"),I,I);
        SpikeMeshes.Add(LoadObject<UStaticMesh>(nullptr,*Path));
    }
    ShardMesh=LoadObject<UStaticMesh>(nullptr,TEXT("/Game/Skills/IceSpike/SM_IceShard.SM_IceShard"));
    IceMaterial=LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/Skills/IceSpike/FrostV2/M_IceHeart.M_IceHeart"));
    IceShellMaterial=LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/Skills/IceSpike/FrostV2/M_IceShell.M_IceShell"));
    ImpactFX=LoadObject<UParticleSystem>(nullptr,TEXT("/Game/Skills/IceSpike/P_IceSpikeImpact.P_IceSpikeImpact"));
    ImpactSound=LoadObject<USoundBase>(nullptr,TEXT("/Game/Skills/IceSpike/S_IceImpact.S_IceImpact"));
    Motes=LoadObject<UNiagaraSystem>(nullptr,TEXT("/Game/Skills/IceSpike/FrostV2/NS_FrostCrystals.NS_FrostCrystals"));
    ColdMist=LoadObject<UNiagaraSystem>(nullptr,TEXT("/Game/Skills/IceSpike/FrostV2/NS_ColdMist.NS_ColdMist"));
}
UColdSteelStatusModel* UFPSIceSpikeComponent::Model() const
{return GetWorld()&&GetWorld()->GetGameInstance()?GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr;}
UFPSFireballComponent* UFPSIceSpikeComponent::Hands() const {return GetOwner()->FindComponentByClass<UFPSFireballComponent>();}
bool UFPSIceSpikeComponent::IsPrepared() const {return (Active.IsValid()&&!Active->IsFlying())||bNetExpect;}
int32 UFPSIceSpikeComponent::ActiveCount() const {return Active.IsValid()?Active->RemainingCount():0;}
void UFPSIceSpikeComponent::Feedback(const FString& Text){Message=Text;MessageUntil=GetWorld()->GetTimeSeconds()+1.5;}
void UFPSIceSpikeComponent::RejectHeldLeftHand()
{
    // Shared with the fireball: a held left hand is released by a loadout change,
    // not by waiting, so the queued gather/release is dropped with the notice.
    bQueuedGather=bQueuedRelease=false;
    if(GetWorld())HandNotice.Show(float(GetWorld()->GetTimeSeconds()));
}
bool UFPSIceSpikeComponent::IsHandOccupiedNotice() const
{
    const auto* Player=Cast<AFPSGAMECharacter>(GetOwner());
    return Player&&Player->IsSpellHandHeld()&&GetWorld()&&HandNotice.Active(float(GetWorld()->GetTimeSeconds()));
}
float UFPSIceSpikeComponent::HandNoticeAlpha() const
{ return GetWorld()?HandNotice.Alpha(float(GetWorld()->GetTimeSeconds())):0.f; }
float UFPSIceSpikeComponent::HandNoticeRise() const
{ return GetWorld()?HandNotice.Rise(float(GetWorld()->GetTimeSeconds())):0.f; }
FString UFPSIceSpikeComponent::StatusText() const
{
    if(IsHandOccupiedNotice())return TEXT("左手占用");
    if(GetWorld()&&GetWorld()->GetTimeSeconds()<MessageUntil)return Message;
    if(bQueuedGather||bQueuedRelease)return TEXT("等待施法");
    if(const auto* H=Hands();H&&H->IsSpellGesture(this))
    {
        if(H->GetHandPhase()==EFireballHandPhase::Raising)return TEXT("凝聚");
        if(H->GetHandPhase()==EFireballHandPhase::ReadyingRelease||H->GetHandPhase()==EFireballHandPhase::Releasing)return TEXT("齐射");
    }
    if(IsPrepared())return TEXT("齐射");if(Active.IsValid())return TEXT("飞行");
    if(auto* M=Model();M&&M->IceSpikeCooldown()>0)return FString::Printf(TEXT("%.1f"),M->IceSpikeCooldown());return TEXT("");
}
float UFPSIceSpikeComponent::CooldownFraction() const
{auto* M=Model();return M&&!Active.IsValid()?FMath::Clamp(M->IceSpikeCooldown()/FMath::Max(.1f,M->IceSpikeCooldownDuration()),0.f,1.f):0.f;}
void UFPSIceSpikeComponent::Trigger()
{
    if(UBoundCongregateCaptureComponent::IsCaptured(GetOwner()))return;
    auto* Player=Cast<AFPSGAMECharacter>(GetOwner());auto* M=Model();
    if(!Player||!M||!Player->IsLocallyControlled())return;
    if(auto* H=Player->FindComponentByClass<UFPSCombatHealthComponent>();H&&H->IsDead())return;
    if(const auto* H=Hands();H&&H->HasOtherPreparedSpell(this))
    {bQueuedGather=bQueuedRelease=false;Feedback(TEXT("先释放已积蓄魔法"));return;}
    if(auto* Sword=Player->FindComponentByClass<URuneSwordComponent>();Sword&&Sword->IsGuarding())Sword->ReleaseGuard();
    // Share the fireball's selected casting hand, including right-hand staff.
    if(Player->IsSpellHandHeld()){RejectHeldLeftHand();return;}
    if(Active.IsValid()||bNetExpect)
    {
        if(IsPrepared()&&!(Hands()&&Hands()->IsSpellGesture(this)&&(Hands()->GetHandPhase()==EFireballHandPhase::ReadyingRelease||Hands()->GetHandPhase()==EFireballHandPhase::Releasing)))bQueuedRelease=true;
    }
    else
    {
        if(M->IceSpikeCooldown()>0){Feedback(TEXT("冷却"));return;}
        if(!M->CanSpendMana(M->IceSpikeStats().ManaCost)){Feedback(TEXT("缺蓝"));return;}
        if(SpikeMeshes.Num()!=3||SpikeMeshes.Contains(nullptr)||!ShardMesh||!IceMaterial||!IceShellMaterial||!ImpactFX||!ColdMist){Feedback(TEXT("缺素材"));return;}
        bQueuedGather=true;
    }
    ServiceQueue();
}
void UFPSIceSpikeComponent::ServiceQueue()
{
    auto* M=Model();auto* H=Hands();auto* Player=Cast<APawn>(GetOwner());if(!M||!H||!Player)return;
    if((bQueuedGather||bQueuedRelease)&&H->HasOtherPreparedSpell(this))
    {bQueuedGather=bQueuedRelease=false;Feedback(TEXT("先释放已积蓄魔法"));return;}
    // A loadout change while queued drops the request instead of holding it.
    if((bQueuedGather||bQueuedRelease)&&Cast<AFPSGAMECharacter>(Player)&&Cast<AFPSGAMECharacter>(Player)->IsSpellHandHeld())
    {RejectHeldLeftHand();return;}
    if(bQueuedGather)
    {
        const auto Snapshot=M->IceSpikeStats();
        if(M->IceSpikeCooldown()>0||!M->CanSpendMana(Snapshot.ManaCost)){bQueuedGather=false;Feedback(TEXT("未就绪"));return;}
        if(!H->TryBeginSpellGesture(this,false,Snapshot.CastSpeed,FSimpleDelegate()))return;
        bQueuedGather=false;
        // 联机客人：手势+本地扣账照常，权威齐射由服务端生成后复制回来认领。
        if(GetWorld()->GetNetMode()==NM_Client)
        {
            const float BeforeNet=M->Snapshot().Mana;
            if(!M->BeginIceSpikeCast(Snapshot)){H->CancelSpellGesture(this);return;}
            H->RecordGesturePayment(BeforeNet,M->Snapshot().Mana);
            if(auto* Status=Player->FindComponentByClass<UCombatStatusFormula>())Status->ConsumeChainSpell();
            bNetExpect=true;NetExpectAt=GetWorld()->GetTimeSeconds();
            NetCast::Send(Player,TEXT("iceSpike"),0);
            MessageUntil=0;return;
        }
        FActorSpawnParameters Params;Params.Owner=Player;Params.Instigator=Player;Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        auto* Volley=GetWorld()->SpawnActor<AFPSIceSpikeVolley>(Player->GetActorLocation(),FRotator::ZeroRotator,Params);
        if(!Volley){H->CancelSpellGesture(this);return;}
        const float BeforeMana=M->Snapshot().Mana;
        if(!M->BeginIceSpikeCast(Snapshot)){Volley->Destroy();H->CancelSpellGesture(this);return;}
        H->RecordGesturePayment(BeforeMana,M->Snapshot().Mana);
        if(auto* Status=Player->FindComponentByClass<UCombatStatusFormula>())Status->ConsumeChainSpell();
        Active=Volley;Volley->Prepare(this,Player,Snapshot,SpikeMeshes,ShardMesh,IceMaterial,IceShellMaterial,ImpactFX,ImpactSound,Motes,ColdMist);
        MessageUntil=0;return;
    }
    if(bQueuedRelease)
    {
        if(!IsPrepared()){bQueuedRelease=false;return;}
        const float Speed=Active.IsValid()?Active->CastSpeed():M->IceSpikeStats().CastSpeed;
        if(H->TryBeginSpellGesture(this,true,Speed,FSimpleDelegate::CreateUObject(this,&ThisClass::LaunchAtContact)))
        {bQueuedRelease=false;MessageUntil=0;}
    }
}
void UFPSIceSpikeComponent::LaunchAtContact()
{
    if(!IsPrepared())return;
    auto* Camera=GetOwner()->FindComponentByClass<UCameraComponent>();if(!Camera)return;
    // 联机客人：发射意图上报——服务端权威齐射按上报瞄准点起飞，本地不驱动弹道。
    if(GetWorld()->GetNetMode()==NM_Client)
    {
        NetCast::Send(GetOwner(),TEXT("iceSpike"),1,FPSMagicPreview::AimPoint(Cast<APawn>(GetOwner()),Active.Get()));
        return;
    }
    Active->Launch();
}
void UFPSIceSpikeComponent::VolleyFinished(AFPSIceSpikeVolley* Volley)
{if(Active.Get()!=Volley)return;Active.Reset();bQueuedRelease=false;bAimPreview=false;if(auto* H=Hands())H->CancelSpellGesture(this);}
void UFPSIceSpikeComponent::SetAimPreview(bool bActive)
{
    // Only a hovering, fully gathered group previews; during the gather the press keeps its
    // old meaning (queue the release) so the first press is never swallowed.
    const auto* H=Hands();
    const bool bCastInProgress=H&&H->IsSpellGesture(this)&&(H->GetHandPhase()==EFireballHandPhase::Raising
        ||H->GetHandPhase()==EFireballHandPhase::ReadyingRelease||H->GetHandPhase()==EFireballHandPhase::Releasing);
    if(bActive&&(!IsPrepared()||bQueuedRelease||bCastInProgress))return;
    bAimPreview=bActive;
    if(auto* V=Active.Get())V->SetAimPreviewActive(bAimPreview);
}
void UFPSIceSpikeComponent::ReleaseAimPreview()
{
    if(!bAimPreview||!IsPrepared())return;
    Active->CommitAimPreview();bAimPreview=false;
    Trigger();
    const auto* H=Hands();
    const bool bReleasing=H&&H->IsSpellGesture(this)&&H->GetHandPhase()==EFireballHandPhase::ReadyingRelease;
    if(!bQueuedRelease&&!bReleasing)
        if(auto* V=Active.Get())V->SetAimPreviewActive(false);
}
void UFPSIceSpikeComponent::Cancel()
{
    bQueuedGather=bQueuedRelease=false;bAimPreview=false;
    // 联机客人：凝聚期取消退蓝（Phase2）；已凝聚弃置只清占用（Phase3，与单机 Destroy 不退蓝同口径）。
    if(GetWorld()&&GetWorld()->GetNetMode()==NM_Client)
    {
        if(bNetExpect)NetCast::Send(GetOwner(),TEXT("iceSpike"),2);
        else if(Active.IsValid()&&!Active->IsFlying())NetCast::Send(GetOwner(),TEXT("iceSpike"),3);
        if(Active.IsValid()&&!Active->HasAuthority())Active->Destroy(); // 本地副本即时消隐；权威壳由服务端销毁复制同步
    }
    else if(Active.IsValid())Active->Destroy();
    Active.Reset();bNetExpect=false;if(auto* H=Hands())H->CancelSpellGesture(this);
}
void UFPSIceSpikeComponent::InterruptPending(bool bCancelPrepared)
{
    bQueuedGather=bQueuedRelease=false;SetAimPreview(false);
    if(bCancelPrepared && IsPrepared())
    {
        if(GetWorld()&&GetWorld()->GetNetMode()==NM_Client)
        {NetCast::Send(GetOwner(),TEXT("iceSpike"),bNetExpect?2:3);bNetExpect=false;}
        if(Active.IsValid()&&!Active->HasAuthority())Active->Destroy();Active.Reset();
        Feedback(TEXT("施法中断"));
    }
}
void UFPSIceSpikeComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick)
{
    Super::TickComponent(Delta,Type,Tick);
    if(auto* H=GetOwner()->FindComponentByClass<UFPSCombatHealthComponent>();H&&H->IsDead()){Cancel();return;}
    // 联机：凝聚已上报但服务端齐射迟迟未达——超时本地收尾退款。
    if(bNetExpect&&!Active.IsValid()&&GetWorld()&&GetWorld()->GetTimeSeconds()-NetExpectAt>2.5)
    {
        bNetExpect=false;
        if(auto* M=Model())M->RefundUnreleasedCast(Hands()?Hands()->TakeGesturePayment():0.f,TEXT("iceSpike"));
        if(auto* H=Hands())H->CancelSpellGesture(this);
        Feedback(TEXT("施法超时"));
    }
    ServiceQueue();
}
AFPSIceSpikeVolley* UFPSIceSpikeComponent::SpawnVolleyForCast(APawn* Caster,const FIceSpikeCast& Snapshot)
{
    // 服务端入口：组件资产在服务端副本上同样已载，Prepare 时一并写复制态。
    if(SpikeMeshes.Num()!=3||SpikeMeshes.Contains(nullptr)||!ShardMesh||!IceMaterial||!IceShellMaterial||!ImpactFX||!ColdMist)return nullptr;
    FActorSpawnParameters Params;Params.Owner=Caster;Params.Instigator=Caster;Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    auto* Volley=GetWorld()->SpawnActor<AFPSIceSpikeVolley>(Caster->GetActorLocation(),FRotator::ZeroRotator,Params);
    if(!Volley)return nullptr;
    Active=Volley;Volley->Prepare(this,Caster,Snapshot,SpikeMeshes,ShardMesh,IceMaterial,IceShellMaterial,ImpactFX,ImpactSound,Motes,ColdMist);
    return Volley;
}
void UFPSIceSpikeComponent::AdoptNetVolley(AFPSIceSpikeVolley* Volley)
{
    if(!Volley||Volley->IsFlying())return;
    Active=Volley;bNetExpect=false;
    if(bAimPreview)Volley->SetAimPreviewActive(true);
}
void UFPSIceSpikeComponent::NetCastPrepared(uint8 /*Phase*/)
{
    // 服务端 Begin 成功回执——本地姿势/预留早已就位，无需动作。
}
void UFPSIceSpikeComponent::NetCastRejected(uint8 Phase,uint8 /*Code*/)
{
    bQueuedGather=bQueuedRelease=false;bNetExpect=false;
    if(auto* M=Model())M->RefundUnreleasedCast(Hands()?Hands()->TakeGesturePayment():0.f,TEXT("iceSpike"));
    if(auto* H=Hands())H->CancelSpellGesture(this);
    Feedback(TEXT("施法失败"));
}
void UFPSIceSpikeComponent::NetCastCancelled(uint8 Phase)
{
    bNetExpect=false;
    if(Phase==2){if(auto* M=Model())M->RefundUnreleasedCast(Hands()?Hands()->TakeGesturePayment():0.f,TEXT("iceSpike"));}
    if(Active.IsValid()&&!Active->HasAuthority())Active->Destroy();Active.Reset();
}
void UFPSIceSpikeComponent::EndPlay(EEndPlayReason::Type Reason){Cancel();Super::EndPlay(Reason);}
