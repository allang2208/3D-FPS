#include "FPSFireMagicComponent.h"
#include "../Monsters/BoundCongregateCaptureComponent.h"
#include "../Dungeons/WardBreakableGlass.h"
#include "FPSMeteorStrike.h"
#include "FPSFireballComponent.h"
#include "FireMagicArea.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Combat/CombatStatusFormula.h"
#include "../UI/StatusEffectsComponent.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Weapons/RuneSwordComponent.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "NiagaraComponent.h"
#include "NiagaraFunctionLibrary.h"
#include "NiagaraSystem.h"
#include "Sound/SoundBase.h"
#include "Net/UnrealNetwork.h"
#include "NetCastUtils.h"

UFPSFireMagicComponent::UFPSFireMagicComponent()
{
    PrimaryComponentTick.bCanEverTick=true;PrimaryComponentTick.TickGroup=TG_PostUpdateWork;
    SetIsReplicatedByDefault(true); // 焰甲激活态复制：远端副本演火环/武器火
}
void UFPSFireMagicComponent::BeginPlay()
{
    Super::BeginPlay();AddTickPrerequisiteActor(GetOwner());
    if(auto* Sword=GetOwner()->FindComponentByClass<URuneSwordComponent>())AddTickPrerequisiteComponent(Sword);
    AuraSystem=LoadObject<UNiagaraSystem>(nullptr,TEXT("/Game/Skills/FireMagic20260921/RealisticV5/NS_ArmorNaturalAura.NS_ArmorNaturalAura"));
    WeaponSystem=LoadObject<UNiagaraSystem>(nullptr,TEXT("/Game/Skills/FireMagic20260921/RealisticV5/NS_ArmorNaturalFire.NS_ArmorNaturalFire"));
    SparkSystem=LoadObject<UNiagaraSystem>(nullptr,TEXT("/Game/Skills/FireMagic20260921/NS_FireMagicSparks.NS_FireMagicSparks"));
    CastSound=LoadObject<USoundBase>(nullptr,TEXT("/Game/Skills/FireMagic20260921/S_FireMagicCast.S_FireMagicCast"));
    // Hold the meteor's authored dependencies before accepting a paid cast.
    bMeteorAssetsReady=true;
    const TCHAR* Assets[]={TEXT("/Game/Skills/FireMagic20260921/RealisticV3/SM_MeteorNaturalRock.SM_MeteorNaturalRock"),TEXT("/Game/Skills/FireMagic20260921/RealisticV3/MI_MeteorNaturalRock.MI_MeteorNaturalRock"),
        TEXT("/Game/Skills/FireMagic20260921/RealisticV5/NS_MeteorNaturalMantle.NS_MeteorNaturalMantle"),TEXT("/Game/Skills/FireMagic20260921/RealisticV5/NS_MeteorNaturalAfterfire.NS_MeteorNaturalAfterfire"),
        TEXT("/Game/Skills/FireMagic20260921/S_MeteorLand.S_MeteorLand"),TEXT("/Game/Skills/FireMagic20260921/S_MeteorBurn.S_MeteorBurn"),
        TEXT("/Game/Skills/FireMagic20260921/RealisticV5/NS_MeteorNaturalWake.NS_MeteorNaturalWake"),TEXT("/Game/Skills/FireMagic20260921/RealisticV5/NS_MeteorNaturalImpact.NS_MeteorNaturalImpact")};
    for(const TCHAR* Path:Assets){UObject* Asset=LoadObject<UObject>(nullptr,Path);bMeteorAssetsReady&=Asset!=nullptr;MeteorAssets.Add(Asset);}
}
UColdSteelStatusModel* UFPSFireMagicComponent::Model() const
{return GetWorld()&&GetWorld()->GetGameInstance()?GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr;}
UFPSFireballComponent* UFPSFireMagicComponent::Hands() const{return GetOwner()->FindComponentByClass<UFPSFireballComponent>();}
void UFPSFireMagicComponent::Feedback(FName Skill,const FString& Text){MessageSkill=Skill;Message=Text;MessageUntil=GetWorld()->GetTimeSeconds()+2;}
void UFPSFireMagicComponent::RejectHeldHand(FName Skill){QueuedSkill=NAME_None;NoticeSkill=Skill;HandNotice.Show(GetWorld()->GetTimeSeconds());}
bool UFPSFireMagicComponent::IsHandOccupiedNotice(FName Skill) const
{
    const auto* Player=Cast<AFPSGAMECharacter>(GetOwner());
    return Skill==NoticeSkill&&Player&&Player->IsSpellHandHeld()&&GetWorld()&&HandNotice.Active(GetWorld()->GetTimeSeconds());
}
float UFPSFireMagicComponent::HandNoticeAlpha() const{return GetWorld()?HandNotice.Alpha(GetWorld()->GetTimeSeconds()):0;}
float UFPSFireMagicComponent::HandNoticeRise() const{return GetWorld()?HandNotice.Rise(GetWorld()->GetTimeSeconds()):0;}
float UFPSFireMagicComponent::CooldownFraction(FName Skill) const
{const auto* M=Model();return M?FMath::Clamp(M->FireMagicCooldown(Skill)/FMath::Max(.1f,M->FireMagicCooldownDuration(Skill)),0.f,1.f):0;}
FString UFPSFireMagicComponent::StatusText(FName Skill) const
{
    if(IsHandOccupiedNotice(Skill))return TEXT("左手占用");
    if(Skill==MessageSkill&&GetWorld()->GetTimeSeconds()<MessageUntil)return Message;
    if(Skill==QueuedSkill)return TEXT("等待施法");if(Skill==CommittedSkill)return TEXT("施法");
    if(Skill==TEXT("flameArmor")&&ArmorTime>0)return FString::Printf(TEXT("焰甲 %.1fs"),ArmorTime);
    if(const auto* M=Model();M&&M->FireMagicCooldown(Skill)>0)return FString::Printf(TEXT("%.1f"),M->FireMagicCooldown(Skill));
    return TEXT("");
}
bool UFPSFireMagicComponent::Allowed(const FFireMagicCast& Spell,FString& Failure) const
{
    const auto* M=Model();if(!M)return false;
    if(Spell.bRequiresStaff&&!M->HasEquippedStaff())
    {Failure=TEXT("需要法杖");return false;}
    if(Spell.Skill==TEXT("flameArmor"))if(const auto* Status=GetOwner()->FindComponentByClass<UCombatStatusFormula>();Status&&Status->IsImmune())
    {Failure=TEXT("状态免疫");return false;}
    if(M->FireMagicCooldown(Spell.Skill)>0){Failure=TEXT("冷却");return false;}
    if(!M->CanSpendMana(Spell.ManaCost)){Failure=TEXT("缺蓝");return false;}
    return true;
}
bool UFPSFireMagicComponent::SelectGround(const FFireMagicCast& Spell,FVector& Point,FVector& Normal,FString& Failure) const
{
    const auto* Camera=GetOwner()->FindComponentByClass<UCameraComponent>();if(!Camera)return false;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(MeteorAim),true,GetOwner());FHitResult Hit;
    const FVector Eye=Camera->GetComponentLocation();
    if(!GetWorld()->LineTraceSingleByChannel(Hit,Eye,Eye+Camera->GetForwardVector()*(Spell.Range+250),ECC_Visibility,Query))
    {Failure=TEXT("准星未指向地面");return false;}
    // Aiming at a creature resolves its ground contact, not a hovering lava plane.
    if(Hit.GetActor()&&Hit.GetActor()->IsA<APawn>())
    {
        Query.AddIgnoredActor(Hit.GetActor());const FVector At=Hit.ImpactPoint;
        if(!FireMagic::TraceSurface(Cast<APawn>(GetOwner()),At+FVector(0,0,80),At-FVector(0,0,300),Hit))
        {Failure=TEXT("目标脚下无地面");return false;}
    }
    if(Hit.ImpactNormal.Z<.45f){Failure=TEXT("需要可落地表面");return false;}
    if(FVector::Dist2D(GetOwner()->GetActorLocation(),Hit.ImpactPoint)>Spell.Range)
    {Failure=TEXT("超出施法距离");return false;}
    Point=Hit.ImpactPoint;Normal=Hit.ImpactNormal;return true;
}
void UFPSFireMagicComponent::Trigger(FName Skill)
{
    if(UBoundCongregateCaptureComponent::IsCaptured(GetOwner()))return;
    auto* Player=Cast<AFPSGAMECharacter>(GetOwner());auto* M=Model();
    if(!FireMagic::IsSkill(Skill)||!Player||!M||!Player->IsLocallyControlled())return;
    if(const auto* Health=Player->FindComponentByClass<UFPSCombatHealthComponent>();Health&&Health->IsDead())return;
    if(!CommittedSkill.IsNone())return;
    if(const auto* H=Hands();H&&H->HasOtherPreparedSpell(this))
    {QueuedSkill=NAME_None;Feedback(Skill,TEXT("先释放已积蓄魔法"));return;}
    if(Player->IsSpellHandHeld()){RejectHeldHand(Skill);return;}
    if(!CastSound||(Skill==TEXT("meteor")?!bMeteorAssetsReady:(!AuraSystem||!WeaponSystem||!SparkSystem))){Feedback(Skill,TEXT("缺素材"));return;}
    const auto Spell=M->FireMagicStats(Skill);FString Failure;FVector Point,Normal;
    if(!Allowed(Spell,Failure)||(Skill==TEXT("meteor")&&!SelectGround(Spell,Point,Normal,Failure))){Feedback(Skill,Failure);return;}
    if(auto* Sword=Player->FindComponentByClass<URuneSwordComponent>();Sword&&Sword->IsGuarding())Sword->ReleaseGuard();
    QueuedSkill=Skill;MessageUntil=0;ServiceQueue();
}
void UFPSFireMagicComponent::ServiceQueue()
{
    if(QueuedSkill.IsNone())return;
    auto* Player=Cast<AFPSGAMECharacter>(GetOwner());auto* M=Model();auto* H=Hands();if(!Player||!M||!H)return;
    if(H->HasOtherPreparedSpell(this))
    {Feedback(QueuedSkill,TEXT("先释放已积蓄魔法"));QueuedSkill=NAME_None;return;}
    if(Player->IsSpellHandHeld()){RejectHeldHand(QueuedSkill);return;}
    const auto* PC=Cast<APlayerController>(Player->GetController());
    if(!PC||PC->IsLookInputIgnored()||PC->IsMoveInputIgnored()){QueuedSkill=NAME_None;return;}
    if(H->BlocksNewLeftHandAction()||Player->IsSpellHandBusy())return;
    const auto Spell=M->FireMagicStats(QueuedSkill);FString Failure;
    if(!Allowed(Spell,Failure)||(QueuedSkill==TEXT("meteor")&&!SelectGround(Spell,LockedPoint,LockedNormal,Failure)))
    {Feedback(QueuedSkill,Failure);QueuedSkill=NAME_None;return;}
    const bool bPushGesture=Spell.Skill!=TEXT("flameArmor");
    if(!H->TryBeginSpellGesture(this,bPushGesture,Spell.CastSpeed,FSimpleDelegate::CreateUObject(this,&ThisClass::ReleaseAtContact)))return;
    QueuedSkill=NAME_None;
    const float BeforeMana=M->Snapshot().Mana;
    if(!M->BeginFireMagicCast(Spell)){H->CancelSpellGesture(this);return;}
    H->RecordGesturePayment(BeforeMana,M->Snapshot().Mana,true);
    CastSnapshot=Spell;CommittedSkill=Spell.Skill;MessageUntil=0;
    if(auto* Status=Player->FindComponentByClass<UCombatStatusFormula>())Status->ConsumeChainSpell();
    // 联机客人：凝聚扣账上报；陨星落点/焰甲激活由服务端在释放相位结算。
    if(GetWorld()->GetNetMode()==NM_Client){bNetPaid=true;NetCast::Send(Player,Spell.Skill,0);}
}
void UFPSFireMagicComponent::ReleaseAtContact()
{
    if(CommittedSkill.IsNone())return;const FName Skill=CommittedSkill;CommittedSkill=NAME_None;
    auto* Player=Cast<AFPSGAMECharacter>(GetOwner());if(!Player)return;
    if(auto* M=Model();M&&CastSnapshot.bRequiresStaff&&!M->HasEquippedStaff())
    {M->RefundUnreleasedCast(Hands()?Hands()->TakeGesturePayment():0.f,Skill);Feedback(Skill,TEXT("需要法杖"));return;}
    if(Skill==TEXT("meteor"))
    {
        const auto* Camera=Player->FindComponentByClass<UCameraComponent>();FHitResult Block;
        const bool bBlocked=!Camera||FireMagic::TraceSurface(Player,Camera->GetComponentLocation(),LockedPoint+LockedNormal*12,Block);
        if(bBlocked||FVector::Dist2D(Player->GetActorLocation(),LockedPoint)>CastSnapshot.Range)
        {if(auto* M=Model())M->RefundUnreleasedCast(Hands()?Hands()->TakeGesturePayment():0.f,Skill);Feedback(Skill,TEXT("落点被遮挡或超距"));return;}
        // 联机客人：落点/法线上报服务端，权威陨星复制回来；本地收尾预扣账。
        if(GetWorld()->GetNetMode()==NM_Client)
        {
            NetCast::Send(Player,Skill,1,LockedPoint,LockedNormal);
            if(auto* M=Model())M->FinishFireMagicCast(Skill,FFireMagicRewards());
            bNetPaid=false;
            UGameplayStatics::PlaySoundAtLocation(this,CastSound,Player->GetActorLocation());
            if(auto* Status=UCombatStatusFormula::GetOrAdd(Player))
            {if(CastSnapshot.bGrantChain)Status->AddChainSpell();if(CastSnapshot.CastHasteStacks>0)Status->AddHaste(CastSnapshot.CastHasteStacks,CastSnapshot.CastHasteDuration);}
            return;
        }
        FActorSpawnParameters P;P.Owner=Player;P.Instigator=Player;P.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        auto* Strike=GetWorld()->SpawnActor<AFPSMeteorStrike>(LockedPoint,FRotator::ZeroRotator,P);
        if(!Strike||!Strike->InitializeStrike(Player,CastSnapshot,LockedPoint,LockedNormal))
        {if(auto* M=Model())M->RefundUnreleasedCast(Hands()?Hands()->TakeGesturePayment():0.f,Skill);Feedback(Skill,TEXT("陨星素材未就绪"));return;}
        Strikes.Add(Strike);
    }
    else
    {
        // 联机客人：焰甲激活上报——服务端跑权威灼烧，远端副本靠 bNetArmor 演火环。
        if(GetWorld()->GetNetMode()==NM_Client){NetCast::Send(Player,Skill,1);bNetPaid=false;}
        StartArmor();
    }
    UGameplayStatics::PlaySoundAtLocation(this,CastSound,Player->GetActorLocation());
    if(auto* Status=UCombatStatusFormula::GetOrAdd(Player))
    {if(CastSnapshot.bGrantChain)Status->AddChainSpell();if(CastSnapshot.CastHasteStacks>0)Status->AddHaste(CastSnapshot.CastHasteStacks,CastSnapshot.CastHasteDuration);}
}
void UFPSFireMagicComponent::StartArmor()
{
    EndArmor(true);ArmorSnapshot=CastSnapshot;ArmorTime=ArmorSnapshot.Duration;AuraTimer=0;
    SpawnArmorFX();
    TickArmor(0);
    if(AuraFX)AuraFX->Activate(true);if(WeaponFX)WeaponFX->Activate(true);
    // 旧 flame-armor-system：命中即刷 🔥 护盾卡片，duration 跟随技能面板。
    UStatusEffectsComponent::GetOrCreate(GetOwner())->SetTimed(TEXT("flameArmor"),ArmorSnapshot.Duration);
    if(GetOwner()->HasAuthority()){NetArmorCast=ArmorSnapshot;bNetArmor=true;} // 远端副本 OnRep 播同款火环
}
// 光环/武器火焰的 FX 壳——本地激活与远端 OnRep 共用。
void UFPSFireMagicComponent::SpawnArmorFX()
{
    AuraFX=UNiagaraFunctionLibrary::SpawnSystemAttached(AuraSystem,GetOwner()->GetRootComponent(),NAME_None,FVector::ZeroVector,FRotator::ZeroRotator,EAttachLocation::KeepRelativeOffset,false,false);
    WeaponFX=UNiagaraFunctionLibrary::SpawnSystemAttached(WeaponSystem,GetOwner()->GetRootComponent(),NAME_None,FVector::ZeroVector,FRotator::ZeroRotator,EAttachLocation::KeepRelativeOffset,false,false);
    if(AuraFX){AuraFX->SetAbsolute(false,true,true);AuraFX->SetVariableFloat(TEXT("User.Fade"),1);}
    if(WeaponFX)
    {
        WeaponFX->SetAbsolute(false,true,true);WeaponFX->SetVariableFloat(TEXT("User.Fade"),0);
        WeaponFX->AddTickPrerequisiteComponent(this);WeaponFX->SetTickBehavior(ENiagaraTickBehavior::UsePrereqs);
    }
    if(AuraFX)AuraFX->Activate(true);if(WeaponFX)WeaponFX->Activate(true);
}
void UFPSFireMagicComponent::OnRep_Armor()
{
    // 远端副本：焰甲激活——播 FX；伤害 tick 只在服务端跑（ApplyFireMagicHit 自带权威门）。
    const auto* OwnerPawn=Cast<APawn>(GetOwner());
    if(!bNetArmor||ArmorTime>0||!OwnerPawn||OwnerPawn->IsLocallyControlled())return;
    EndArmor(false);ArmorSnapshot=NetArmorCast;ArmorTime=ArmorSnapshot.Duration;AuraTimer=0;
    SpawnArmorFX();
}
void UFPSFireMagicComponent::Sparks(const FVector& Point)
{if(SparkSystem)UNiagaraFunctionLibrary::SpawnSystemAtLocation(this,SparkSystem,Point,FRotator::ZeroRotator,FVector(1),true,true,ENCPoolMethod::AutoRelease);}
void UFPSFireMagicComponent::OnWeaponHit(AActor* Target,const FVector& Point)
{
    if(ArmorTime<=0)return;
    auto* Player=Cast<APawn>(GetOwner());auto* M=NetCast::AuthorityModel(Player,GetWorld()?GetWorld()->GetGameInstance():nullptr);
    if(M&&M->ApplyFireMagicHit(Player,Target,ArmorSnapshot,ArmorSnapshot.Damage,ArmorRewards))Sparks(Point);
}
void UFPSFireMagicComponent::TickArmor(float Delta)
{
    if(ArmorTime<=0)return;
    auto* Player=Cast<AFPSGAMECharacter>(GetOwner());auto* M=NetCast::AuthorityModel(Player,GetWorld()?GetWorld()->GetGameInstance():nullptr);if(!Player||!M){EndArmor(false);return;}
    const float ActiveDelta=FMath::Min(Delta,ArmorTime);ArmorTime=FMath::Max(0.f,ArmorTime-Delta);AuraTimer+=ActiveDelta;
    const FVector Feet=Player->GetActorLocation()-FVector(0,0,Player->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()-5);
    while(AuraTimer+UE_KINDA_SMALL_NUMBER>=ArmorSnapshot.TickSeconds)
    {
        AuraTimer-=ArmorSnapshot.TickSeconds;int32 Hits=0;
        if(ArmorSnapshot.AuraDamage>0)UWardBreakableGlass::BreakInRadius(GetWorld(),Feet,ArmorSnapshot.AuraRadius,Player);
        for(AActor* Target:FireMagic::GroundTargets(Player,Feet,FVector::UpVector,ArmorSnapshot.AuraRadius))
        {
            const int32 Before=ArmorRewards.Hits;
            if(M->ApplyFireMagicHit(Player,Target,ArmorSnapshot,ArmorSnapshot.AuraDamage,ArmorRewards))Sparks(Target->GetActorLocation());
            Hits+=ArmorRewards.Hits-Before;
        }
        ArmorRewards.bMultiHit|=Hits>=2;
    }
    const float Onset=FMath::Clamp((ArmorSnapshot.Duration-ArmorTime)/.18f,0.f,1.f);
    const float Fade=FMath::Min(1.f,ArmorTime/.5f)*Onset*Onset*(3-2*Onset);
    if(AuraFX){AuraFX->SetWorldLocation(Feet);AuraFX->SetVariableFloat(TEXT("User.Radius"),Player->GetCapsuleComponent()->GetScaledCapsuleRadius()+16);AuraFX->SetVariableFloat(TEXT("User.Fade"),Fade);}
    if(WeaponFX)
    {
        FVector Base=FVector::ZeroVector,Tip=FVector::ZeroVector;bool bWeapon=false;
        if(auto* Sword=Player->FindComponentByClass<URuneSwordComponent>();Sword&&Sword->IsEquipped())bWeapon=Sword->GetFireMagicBladePoints(Base,Tip);
        else if(Player->HasInventoryWeapon()){Tip=Player->GetEffectiveMuzzleLocation();Base=Tip-Player->GetEffectiveMuzzleForward()*28;bWeapon=true;}
        WeaponFX->SetVisibility(bWeapon);
        if(bWeapon)
        {
            // Teleports / weapon swaps must not draw a streak across the previous weapon.
            if(!bWeaponSampleValid||FVector::DistSquared(Base,PreviousWeaponBase)>FMath::Square(180.f)||FVector::DistSquared(Tip,PreviousWeaponTip)>FMath::Square(240.f))
            {PreviousWeaponBase=Base;PreviousWeaponTip=Tip;}
            const FVector Velocity=Delta>0?((Base+Tip-PreviousWeaponBase-PreviousWeaponTip)*(.5f/Delta)).GetClampedToMaxSize(1400):FVector::ZeroVector;
            WeaponFX->SetWorldLocation(Base);WeaponFX->SetVariableVec3(TEXT("User.WeaponEnd"),Tip-Base);
            WeaponFX->SetVariablePosition(TEXT("User.WeaponStartWorld"),Base);WeaponFX->SetVariablePosition(TEXT("User.WeaponEndWorld"),Tip);
            WeaponFX->SetVariablePosition(TEXT("User.PreviousStart"),PreviousWeaponBase);WeaponFX->SetVariablePosition(TEXT("User.PreviousEnd"),PreviousWeaponTip);
            WeaponFX->SetVariableVec3(TEXT("User.WeaponVelocity"),Velocity);
            WeaponFX->SetVariableFloat(TEXT("User.WeaponSize"),FMath::Clamp(float(FVector::Distance(Base,Tip)/80.),.55f,1.f));
            WeaponFX->SetVariableFloat(TEXT("User.Fade"),Fade);PreviousWeaponBase=Base;PreviousWeaponTip=Tip;bWeaponSampleValid=true;
        }
        else{bWeaponSampleValid=false;WeaponFX->SetVariableFloat(TEXT("User.Fade"),0);}
    }
    if(ArmorTime<=0)EndArmor(true);
}
void UFPSFireMagicComponent::EndArmor(bool bTrain)
{
    if(bTrain)if(auto* M=NetCast::AuthorityModel(Cast<APawn>(GetOwner()),GetWorld()?GetWorld()->GetGameInstance():nullptr))M->FinishFireMagicCast(TEXT("flameArmor"),ArmorRewards);
    if(ArmorTime>0)UStatusEffectsComponent::GetOrCreate(GetOwner())->Remove(TEXT("flameArmor"));
    ArmorTime=0;AuraTimer=0;ArmorRewards={};bWeaponSampleValid=false;
    if(AuraFX){AuraFX->DestroyComponent();AuraFX=nullptr;}if(WeaponFX){WeaponFX->DestroyComponent();WeaponFX=nullptr;}
}
void UFPSFireMagicComponent::CancelPending()
{
    if(!CommittedSkill.IsNone())Feedback(CommittedSkill,TEXT("施法中断"));
    // 联机客人：凝聚期中断——服务端按 Phase2 退预留。
    if(GetWorld()&&GetWorld()->GetNetMode()==NM_Client&&bNetPaid&&!CommittedSkill.IsNone())NetCast::Send(GetOwner(),CommittedSkill,2);
    bNetPaid=false;
    QueuedSkill=NAME_None;CommittedSkill=NAME_None;if(auto* H=Hands())H->CancelSpellGesture(this);
}
void UFPSFireMagicComponent::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(UFPSFireMagicComponent,bNetArmor);
    DOREPLIFETIME(UFPSFireMagicComponent,NetArmorCast);
}
// ── 联机服务端入口：陨星定点生成（复制各端）/焰甲服务端权威激活 ──
bool UFPSFireMagicComponent::NetRelease(APawn* Caster,const FColdSteelNetCastRequest& Req,UColdSteelStatusModel* Shadow,const FFireMagicCast& Spell)
{
    CastSnapshot=Spell;
    if(Req.SkillId==TEXT("meteor"))
    {
        if(Req.AimNormal.Z<.45f)return false;
        if(FVector::Dist2D(Caster->GetActorLocation(),Req.AimPoint)>Spell.Range*1.15f)return false;
        FHitResult Block;
        if(FireMagic::TraceSurface(Caster,Caster->GetPawnViewLocation(),Req.AimPoint+Req.AimNormal*12,Block))return false;
        FActorSpawnParameters P;P.Owner=Caster;P.Instigator=Caster;P.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        auto* Strike=GetWorld()->SpawnActor<AFPSMeteorStrike>(Req.AimPoint,FRotator::ZeroRotator,P);
        if(!Strike||!Strike->InitializeStrike(Caster,Spell,Req.AimPoint,Req.AimNormal))
        {if(Strike)Strike->Destroy();return false;}
        Strikes.Add(Strike);
        if(auto* Status=UCombatStatusFormula::GetOrAdd(Caster))
        {if(Spell.bGrantChain)Status->AddChainSpell();if(Spell.CastHasteStacks>0)Status->AddHaste(Spell.CastHasteStacks,Spell.CastHasteDuration);}
        Shadow->FinishFireMagicCast(Req.SkillId,FFireMagicRewards()); // 陨星自治收尾：其内部 Rewards 空这里先结预扣，实际击杀经验由 Strike->Finish 再算？口径对齐单机：ReleaseAtContact 不 Finish——陨星 Finish 时才结。
        return true;
    }
    // flameArmor：服务端组件 TickArmor 走影子档案结算灼烧；bNetArmor 复制表现。
    StartArmor();
    if(CastSound)UGameplayStatics::PlaySoundAtLocation(this,CastSound,Caster->GetActorLocation());
    if(auto* Status=UCombatStatusFormula::GetOrAdd(Caster))
    {if(Spell.bGrantChain)Status->AddChainSpell();if(Spell.CastHasteStacks>0)Status->AddHaste(Spell.CastHasteStacks,Spell.CastHasteDuration);}
    return true;
}
void UFPSFireMagicComponent::NetCastRejected(uint8 /*Phase*/,uint8 /*Code*/)
{
    bNetPaid=false;
    if(!CommittedSkill.IsNone())
    {
        if(auto* M=Model())M->RefundUnreleasedCast(Hands()?Hands()->TakeGesturePayment():0.f,CommittedSkill);
        Feedback(CommittedSkill,TEXT("施法失败"));
    }
    QueuedSkill=NAME_None;CommittedSkill=NAME_None;if(auto* H=Hands())H->CancelSpellGesture(this);
}
void UFPSFireMagicComponent::NetCastCancelled(uint8 /*Phase*/)
{
    bNetPaid=false;
}
void UFPSFireMagicComponent::ClearEffects()
{CancelPending();EndArmor(false);for(auto& Strike:Strikes)if(Strike.IsValid())Strike->Destroy();Strikes.Reset();ImpactTime=-1;}
void UFPSFireMagicComponent::NotifyMeteorImpact(const FVector& Point)
{
    ImpactTime=GetWorld()->GetTimeSeconds();
    ImpactStrength=FMath::Clamp(1.f-FVector::Distance(GetOwner()->GetActorLocation(),Point)/1600.f,.15f,1.f);
}
void UFPSFireMagicComponent::GetCameraMotion(FVector& Location,FRotator& Rotation) const
{
    if(ImpactTime<0||!GetWorld())return;
    const float Age=GetWorld()->GetTimeSeconds()-ImpactTime;
    if(Age<0||Age>=.38f)return;
    const float Weight=ImpactStrength*FMath::Square(1-Age/.38f);
    Location+=FVector(0,FMath::Sin(Age*85)*.65f,-FMath::Cos(Age*67)*1.5f)*Weight;
    Rotation+=FRotator(FMath::Cos(Age*67)*.7f,FMath::Sin(Age*79)*.24f,FMath::Sin(Age*61)*.3f)*Weight;
}
void UFPSFireMagicComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick)
{
    Super::TickComponent(Delta,Type,Tick);
    if(const auto* Health=GetOwner()->FindComponentByClass<UFPSCombatHealthComponent>();Health&&Health->IsDead())
    {if(!CommittedSkill.IsNone())if(auto* M=Model())M->RefundUnreleasedCast(Hands()?Hands()->TakeGesturePayment():0.f,CommittedSkill);ClearEffects();return;}
    if(!CommittedSkill.IsNone()&&(!Hands()||!Hands()->IsSpellGesture(this)))CommittedSkill=NAME_None;
    if(!CommittedSkill.IsNone()||!QueuedSkill.IsNone())
    if(auto* M=Model();M&&!M->HasEquippedStaff())
    {
        const FName Pending=!CommittedSkill.IsNone()?CommittedSkill:QueuedSkill;
        if(!Pending.IsNone()&&M->FireMagicDefinition(Pending).FireMagic.bRequiresStaff)
        {
            if(!CommittedSkill.IsNone())M->RefundUnreleasedCast(Hands()?Hands()->TakeGesturePayment():0.f,CommittedSkill);
            CancelPending();Feedback(Pending,TEXT("需要法杖"));
        }
    }
    Strikes.RemoveAll([](const auto& A){return !A.IsValid();});TickArmor(Delta);ServiceQueue();
}
void UFPSFireMagicComponent::EndPlay(EEndPlayReason::Type Reason){ClearEffects();Super::EndPlay(Reason);}
