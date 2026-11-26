#include "FPSQuickCombatComponent.h"
#include "ColdSteelSkillRules.h"
#include "../Dungeons/WardBreakableGlass.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../FPSGAMECharacter.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Monsters/BoundCongregateCaptureComponent.h"
#include "FPSCastingMeshComponent.h"
#include "../Weapons/FPSGunplayAnimInstance.h"
#include "../Weapons/MeleeSmallTargetQuery.h"
#include "../Weapons/PistolDualWieldComponent.h"
#include "../Weapons/Bow/BowWeaponComponent.h"
#include "../Weapons/Bow/BowQuickCombatMotion.h"
#include "../Weapons/FPSImpactFXSubsystem.h"
#include "../Weapons/WoodenTorchItem.h"
#include "../Weapons/WoodenTorchComponent.h"
#include "../Weapons/Staff/StaffWeaponComponent.h"
#include "../Weapons/Staff/StaffQuickCombatMotion.h"
#include "../Weapons/Spellbook/SpellbookComponent.h"
#include "../Weapons/Spellbook/SpellbookAuthoredStrike.h"
#include "../Weapons/Unarmed/FPSUnarmedIdleComponent.h"
#include "../Weapons/Unarmed/UnarmedPunchTuning.h"
#include "Engine/World.h"
#include "Components/StaticMeshComponent.h"
#include "GameFramework/Pawn.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"

void UFPSQuickCombatComponent::ConfirmTorchContact(const FVector& Point)
{
    if(Style!=EQuickCombatStyle::TorchStrike||!IsOccupyingLeftHand())return;
    ImpactAge=0.f;ImpactStrength=1.f;
    if(auto* Player=Cast<AFPSGAMECharacter>(GetOwner()))Player->RefreshQuickCombatCamera();
    if(ImpactSound)UGameplayStatics::PlaySoundAtLocation(this,ImpactSound,Point,.9f,.9f);
    if(SwingSound)UGameplayStatics::PlaySound2D(this,SwingSound,.8f,1.f);
}

void UFPSQuickCombatComponent::ContactHit()
{
    auto* Player=Cast<AFPSGAMECharacter>(GetOwner());auto* Profile=Model();
    if(!Player||!Profile||!GetWorld())return;
    if(Style==EQuickCombatStyle::Warhammer){ContactWarhammer(Player,Profile);return;}
    auto Stats=Profile->QuickCombatStats();
    const bool bUnarmed=Style==EQuickCombatStyle::UnarmedPunch;
    // Bare hands use the same authored contact when struggling out of a coil.
    {
        auto* Capture=Player->FindComponentByClass<UBoundCongregateCaptureComponent>();
        if(Capture&&Capture->HitRestraintWithQuickMelee())
        {
            // The F contact strikes the coil around us, instead of also sweeping
            // through a second target in front. Keep the held weapon's hit feel.
            ImpactAge=0.f;ImpactStrength=1.f;Player->RefreshQuickCombatCamera();
            const bool BowContact=Style==EQuickCombatStyle::Bow;
            if(ImpactSound)UGameplayStatics::PlaySound2D(this,ImpactSound,BowContact?1.1f:.9f,BowContact?.84f:.9f);
            if(SwingSound)UGameplayStatics::PlaySound2D(this,SwingSound,BowContact?.32f:.8f,1.f);
            return;
        }
    }
    if(bUnarmed){Stats.Damage=UnarmedPunch::Damage(Profile);Stats.RangeCM=UnarmedPunch::ReachCM;Stats.KnockbackCM=0.f;}
    // 打击射线：起点用握把底（与作者源 clip 的接触位置一致），方向用玩家瞄准
    // （与其它武器/技能同一合同）；不再从眼位沿视线前扫，也不再取实时姿态方向。
    const auto Aim=Player->GetMeleeAimTransform();
    const FVector Direction=Aim.GetUnitAxis(EAxis::X);
    FVector Start=Aim.GetLocation();
    FVector ProbeOrigin=FVector::ZeroVector;
    auto* Viewmodel=Player->FindComponentByClass<UFPSCastingMeshComponent>();
    if((Player->IsM24Weapon()||Player->bUseASH12||Player->IsM870Weapon()||SVCHWeaponAssets::Matches(Viewmodel))&&Viewmodel&&IsRifleStyle())
    {
        // Evaluate the exact contact pose once before the sweep. The faster
        // entry must not trace from the previous frame's wind-up position.
        if(auto* Animation=Cast<UFPSGunplayAnimInstance>(Viewmodel->GetAnimInstance());Animation&&Animation->ActionClip)
        {
            Animation->ActionTime=ContactTime;
            Animation->ActionAlpha=1.f;
            Viewmodel->TickAnimation(0.f,false);
            Viewmodel->RefreshBoneTransforms();
        }
    }
    // 手枪：握把底（手骨 + 相机空间偏移）；步枪：枪身前段（枪口沿枪轴回撤，跟随实际挥击姿态）。
    const bool bBow=Style==EQuickCombatStyle::Bow;
    const bool bBook=Style==EQuickCombatStyle::SpellbookPush;
    const bool bPunch=Style==EQuickCombatStyle::StaffPunch||bUnarmed;
    const bool bTorch=Style==EQuickCombatStyle::TorchStrike;
    const auto* TorchItem=bTorch?ColdSteelInventory::QuickTorch(Profile->Equipped(),Profile->Equipped(Profile->ActiveOffhandSlot())):nullptr;
    if(bTorch&&!TorchItem)return;
    FVector TorchGrip=FVector::ZeroVector;
    const bool bOffhand=Style==EQuickCombatStyle::StaffOffhandPistol;
    const bool bRifle=IsRifleStyle();
    auto* Dual=Player->FindComponentByClass<UPistolDualWieldComponent>();
    auto* Bow=Player->FindComponentByClass<UBowWeaponComponent>();
    auto* Staff=Player->FindComponentByClass<UStaffWeaponComponent>();
    auto* Hands=Player->FindComponentByClass<UFPSUnarmedIdleComponent>();
    auto* Book=Player->FindComponentByClass<USpellbookComponent>();
    const bool bProbe=bTorch?(Staff&&Staff->GetTorchQuickContact(TorchGrip,ProbeOrigin)):bBook
        ?(Book&&Book->GetQuickCombatStrikeProbe(ProbeOrigin))
        :bUnarmed
        ?(Hands&&Hands->GetStrikeProbe(ProbeOrigin))
        :bPunch
        ?(Staff&&Staff->GetQuickCombatStrikeProbe(ProbeOrigin,ContactTime))
        :bBow
        ?(Bow&&Bow->GetQuickCombatStrikeProbe(ProbeOrigin,ContactTime))
        :(Style==EQuickCombatStyle::DualPistol||bOffhand)
        ?(Dual&&Dual->GetQuickCombatStrikeProbe(ProbeOrigin,ContactTime))
        :(bRifle
            ?(Viewmodel&&Viewmodel->GetRifleStockMeleeProbe(ProbeOrigin,Style==EQuickCombatStyle::M4ReferenceRifle))
            :(Viewmodel&&Viewmodel->GetQuickCombatStrikeProbe(ProbeOrigin)));
    if((bBook||bTorch)&&!bProbe)return;
    if(bProbe)Start=ProbeOrigin;
    FHitResult Hit;
    // 单目标：实际接触优先；小手低位范围补充共用同一次伤害结算。
    const float Radius=bBook?SpellbookAuthoredStrike::QueryRadiusCM:(bPunch||bTorch)?StaffQuickCombatMotion::QueryRadiusCM:bBow?BowQuickCombatMotion::QueryRadiusCM
        :bRifle?QuickCombatRifleMotion::QueryRadiusCM:QuickCombatPistolMotion::QueryRadiusCM;
    const bool bHit=MeleeSmallTargets::QueryQuickContact(GetWorld(),Player,Aim,Start,Stats.RangeCM,Radius,Hit);
    // Other quick-melee styles retain their query-frame impulse. Bow collision
    // feedback is gated by physical contact or damage, never by a free swing.
    ImpactAge=0.f;
    Player->RefreshQuickCombatCamera();
    AActor* Target=bHit?Hit.GetActor():nullptr;
    const FString TargetName=Target?Target->GetName():FString(TEXT("无"));
    // R0 诊断：一次动作只打一行，标出射线来源、起点与命中对象，方便对实机反馈。
    UE_LOG(LogTemp,Log,TEXT("[QuickCombat] 接触 武器=%s 射线=%s 起点=%s 方向=%s 距离=%.0f 目标=%s"),
        bTorch?TEXT("火把敲击"):bBook?TEXT("魔法书前击"):bUnarmed?TEXT("空手拳击"):bPunch?TEXT("法杖左拳"):bOffhand?TEXT("法杖副手枪"):bBow?TEXT("弓"):bRifle?TEXT("步枪"):TEXT("手枪"),
        bProbe?(bTorch?TEXT("火把头"):bBook?TEXT("书页外沿"):bUnarmed?(Hands->GetPunchSide()==1?TEXT("右拳指节"):TEXT("左拳指节")):bPunch?TEXT("左拳指节"):bOffhand?TEXT("左手持枪拳"):bBow?TEXT("弓身下段"):bRifle?(Style==EQuickCombatStyle::M4ReferenceRifle?TEXT("M4枪托"):TEXT("枪身前段")):TEXT("握把底")):TEXT("眼位回退"),
        *Start.ToCompactString(),*Direction.ToCompactString(),Stats.RangeCM,*TargetName);
    if(TorchItem)
    {
        auto* Torch=Player->FindComponentByClass<UWoodenTorchComponent>();
        if(Torch&&bHit&&Hit.bBlockingHit&&Target&&!Cast<APawn>(Target)&&!Target->FindComponentByClass<UMonsterCombatComponent>())
            Torch->SurfaceContact(Hit);
        else if(Torch&&!bHit&&bProbe)
        {
            // Thin scenery can block visibility while ignoring the punch's Pawn channel.
            // Sample only the held shaft at contact and keep this query cosmetic.
            FHitResult Surface;
            if(MeleeSmallTargets::BladeScenery(GetWorld(),Player,TorchGrip,ProbeOrigin,Surface))
                Torch->SurfaceContact(Surface);
        }
    }
    if(bHit && UWardBreakableGlass::BreakHit(Hit,Direction))
    {ImpactAge=0.f;ImpactStrength=1.f;Player->RefreshQuickCombatCamera();return;}
    auto* Combat=Target?Target->FindComponentByClass<UMonsterCombatComponent>():nullptr;
    const bool bM24Stock=Player->IsM24Weapon()&&IsRifleStyle();
    if((bBow||bM24Stock)&&bHit&&Hit.bBlockingHit&&!Combat&&!Cast<APawn>(Target))
    {
        // A blocked shove has local resistance but no invented damage,
        // training credit or bullet hole. The existing pooled surface effect
        // provides its material sound and a few wood/stone chips or sparks.
        ImpactAge=0.f;ImpactStrength=.8f;
        Player->RefreshQuickCombatCamera();
        if(bBow)
            if(auto* FX=GetWorld()->GetSubsystem<UFPSImpactFXSubsystem>())
                FX->SpawnImpact(Hit,Player->FirstPersonCamera,true,false);
        return;
    }
    if(!Combat||Combat->IsDead())return;
    // Bow resistance is a physical-contact prediction. Client ApplyHit only
    // forwards to authority and returns zero; waiting on that return suppressed
    // the owner's hit stop, recoil and contact audio in multiplayer. Damage,
    // knockback, training and hit markers still require the authoritative result.
    if(bBow){ImpactAge=0.f;ImpactStrength=1.f;Player->RefreshQuickCombatCamera();}
    const bool Eligible=!Target->ActorHasTag(TEXT("Summoned"))&&!Target->ActorHasTag(TEXT("NoSkillTraining"));
    FColdSteelSkillShot Shot;
    if(bPunch||bTorch)
    {
        // A bare fist must not inherit the held staff's rune/ammo/mastery effects.
        Shot=ColdSteelSkills::StaffQuickStrike(*Profile,TorchItem);
        if(bTorch)Shot.ToughnessDamageMultiplier=Stats.ToughnessMultiplier;
    }
    else Shot=ColdSteelSkills::Snapshot(Player,bBook?Profile->Equipped(Profile->Snapshot().ActiveWeaponSlot==6?8:11)
        :bOffhand&&Dual?&Dual->Hand(1).Item:bBow?Profile->ActiveBow():Profile->Equipped(),false);
    // 步枪版走 rifleMastery 修炼（与枪械命中同一口径），手枪版走 pistolMastery。
    Shot.bRifle=bRifle;Shot.bPistol=IsPistolStyle();Shot.WeakpointPercent=0;
    // 握把底/枪身砸击是钝器动作，按钝器折算削韧；同时标记为手持枪械发动的近战打击，
    // 使其不受「枪械默认不硬直」闸门约束。
    Shot.AttackForm=EMonsterAttackForm::Blunt;Shot.bMeleeStrike=true;
    Shot.AttackMeta=bUnarmed?UnarmedPunch::AttackMeta:uint8(Shot.AttackMeta|0x80);
    if(bUnarmed)Shot.GenericMeleeSerial=GenericMeleeSerial;
    FWeaponDamageResult DamageResult;
    const float Applied=ColdSteelSkills::ApplyHit(Player,Hit,Stats.Damage,Direction,Shot,&DamageResult);
    const bool bKilled=Combat->IsDead();
    // 命中确认通道：与剑/火球/冰锥一致——准星命中标记、钝器确认音、怪物血条反馈。
    // bFirearmHit=false ⇒ 走近战/技能确认（枪械命中的落点是另一条通道）。
    if(Applied>0.f||bKilled)Player->NotifyConfirmedWeaponHit(Target,Applied,&DamageResult,false);
    // Pure push: ReceiveStun would still interrupt attacks even with zero seconds.
    if(Applied>0.f||bKilled)Combat->ReceiveMeleeKnockback(Player,Stats.KnockbackCM);
    if(bTorch)
    {
        if(Player->HasAuthority()&&(Applied>0.f||bKilled))ConfirmTorchContact(Hit.ImpactPoint);
        if(Eligible&&bKilled)bKillPending=true;
        return;
    }
    // ASH uses confirmed damage; bow resistance was already predicted from contact.
    if(Applied>0.f||bKilled){ImpactAge=0.f;ImpactStrength=1.f;Player->RefreshQuickCombatCamera();}
    if(!bUnarmed&&Eligible&&bKilled)bKillPending=true;
    if((bBow||Applied>0.f||bKilled)&&ImpactSound)
    {
        UGameplayStatics::PlaySoundAtLocation(this,ImpactSound,Hit.ImpactPoint,bBow?1.1f:.9f,bBow?.84f:.9f);
        UE_LOG(LogTemp,Log,TEXT("[QuickCombat] 命中音播放=%s 目标=%s 伤害=%.1f 位置=%s"),
            *ImpactSound->GetName(),*TargetName,Applied,*Hit.ImpactPoint.ToCompactString());
    }
    // 用户 2026-09-19：这枚挥击音从「松握即播」改到伤害确认时刻——挥空整段不出声，
    // Bow uses physical contact, including the owner's pending network hit;
    // other styles keep their damage-confirmed gate. Misses remain silent.
    if((bBow||Applied>0.f||bKilled)&&SwingSound)
        UGameplayStatics::PlaySound2D(this,SwingSound,bBow?.32f:.8f,1.f);
}
