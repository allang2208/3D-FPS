#include "FPSFireMagicComponent.h"
#include "../Monsters/UnknownSpellCombat.h"
#include "BlizzardEnvironment.h"
#include "MeteorGround.h"
#include "FlameArmorAssets.h"
#include "MeteorAssets.h"
#include "PlayerSkillPreparation.h"
#include "GameFramework/GameStateBase.h"
#include "MagicOcclusion.h"
#include "../Monsters/BoundCongregateCaptureComponent.h"
#include "../Weapons/ThermalTargetSubsystem.h"
#include "../Dungeons/WardBreakableGlass.h"
#include "FPSMeteorStrike.h"
#include "FPSFireballComponent.h"
#include "FireMagicArea.h"
#include "../FPSGAMECharacter.h"
#include "../FPSGAMEPlayerController.h"
#include "../Building/VoxelBuildComponent.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Combat/CombatStatusFormula.h"
#include "../UI/StatusEffectsComponent.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Weapons/RuneSwordComponent.h"
#include "../Weapons/Bow/BowWeaponComponent.h"
#include "../Weapons/Staff/StaffWeaponComponent.h"
#include "../Weapons/Staff/StaffOffhandMeleeComponent.h"
#include "../Weapons/Kukri/KukriWeaponComponent.h"
#include "../Weapons/Kukri/OffhandKukriComponent.h"
#include "../Weapons/Unarmed/FPSUnarmedIdleComponent.h"
#include "../Production/ProductionToolComponent.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/DecalComponent.h"
#include "Materials/MaterialInterface.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Engine/AssetManager.h"
#include "Engine/GameInstance.h"
#include "Engine/StreamableManager.h"
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
    if(auto* Body=GetOwner()->FindComponentByClass<UFPSPlayerBodyComponent>())AddTickPrerequisiteComponent(Body);
    if(auto* Bow=GetOwner()->FindComponentByClass<UBowWeaponComponent>())AddTickPrerequisiteComponent(Bow);
    if(auto* Staff=GetOwner()->FindComponentByClass<UStaffWeaponComponent>())AddTickPrerequisiteComponent(Staff);
    if(auto* Knife=GetOwner()->FindComponentByClass<UKukriWeaponComponent>())AddTickPrerequisiteComponent(Knife);
    if(auto* Knife=GetOwner()->FindComponentByClass<UOffhandKukriComponent>())AddTickPrerequisiteComponent(Knife);
    if(auto* Pair=GetOwner()->FindComponentByClass<UStaffOffhandMeleeComponent>())AddTickPrerequisiteComponent(Pair);
    if(auto* Tool=GetOwner()->FindComponentByClass<UProductionToolComponent>())AddTickPrerequisiteComponent(Tool);
    if(auto* Empty=GetOwner()->FindComponentByClass<UFPSUnarmedIdleComponent>())AddTickPrerequisiteComponent(Empty);
    if(GetNetMode()==NM_DedicatedServer)return;
    PlayerSkillAssets::Defer(GetOwner(),TEXT("flameArmor"),FSimpleDelegate::CreateWeakLambda(this,[this]()
    {
        AuraSystem=PlayerSkillAssets::Resolve<UNiagaraSystem>(FlameArmorAssets::Body);
        WeaponSystem=PlayerSkillAssets::Resolve<UNiagaraSystem>(FlameArmorAssets::Weapon);
        HammerSystem=PlayerSkillAssets::Resolve<UNiagaraSystem>(FlameArmorAssets::Hammer);
        SwordSystem=PlayerSkillAssets::Resolve<UNiagaraSystem>(FlameArmorAssets::Sword);
        ArrowSystem=PlayerSkillAssets::Resolve<UNiagaraSystem>(FlameArmorAssets::Arrow);
        SparkSystem=PlayerSkillAssets::Resolve<UNiagaraSystem>(TEXT("/Game/Skills/FireMagic20260921/NS_FireMagicSparks.NS_FireMagicSparks"));
        CastSound=PlayerSkillAssets::Resolve<USoundBase>(TEXT("/Game/Skills/FireMagic20260921/S_FireMagicCast.S_FireMagicCast"));
        // Remote armor may already be active when its presentation arrives.
        RefreshArmorVisuals();
    }));
    PlayerSkillAssets::Defer(GetOwner(),TEXT("meteor"),FSimpleDelegate::CreateUObject(this,&ThisClass::ResolveMeteorAssets));
    PlayerSkillAssets::Defer(GetOwner(),TEXT("dragonBreath"),FSimpleDelegate::CreateWeakLambda(this,[this]()
    {
        CastSound=PlayerSkillAssets::Resolve<USoundBase>(TEXT("/Game/Skills/FireMagic20260921/S_FireMagicCast.S_FireMagicCast"));
        LoadDragonBreath();
    }));
}
void UFPSFireMagicComponent::ResolveMeteorAssets()
{
    CastSound=PlayerSkillAssets::Resolve<USoundBase>(MeteorSpellAssets::CastSound);
    bMeteorAssetsReady=true;MeteorAssets.Reset();
    for(const TCHAR* Path:MeteorSpellAssets::Visuals)
    {
        UObject* Asset=PlayerSkillAssets::Resolve<UObject>(Path);
        bMeteorAssetsReady&=Asset!=nullptr;MeteorAssets.Add(Asset);
        if(!Asset)UE_LOG(LogTemp,Warning,TEXT("Meteor preparation missing asset: %s"),Path);
    }
    MeteorAimMaterial=PlayerSkillAssets::Resolve<UMaterialInterface>(MeteorSpellAssets::Preview);
}
UColdSteelStatusModel* UFPSFireMagicComponent::Model() const
{return NetCast::LocalModel(*this);}
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
    if(Skill==TEXT("meteor")&&bMeteorAimPreview)return bMeteorPreviewValid?TEXT("选择落点"):MeteorPreviewFailure;
    if(Skill==TEXT("dragonBreath")&&Skill==QueuedSkill&&!IsDragonBreathVisualReady())return TEXT("火焰准备中");
    if(Skill==QueuedSkill)return TEXT("等待施法");if(Skill==CommittedSkill)return TEXT("施法");
    if(Skill==TEXT("dragonBreath")&&IsDragonBreathActive())return TEXT("喷吐中");
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
    FVector Axis=Camera->GetRightVector();
    return BlizzardEnvironment::Select(Cast<APawn>(GetOwner()),Spell.Range,Camera->GetComponentLocation(),
        Camera->GetForwardVector(),Point,Normal,Axis,Failure);
}
void UFPSFireMagicComponent::Trigger(FName Skill)
{
    SetMeteorAimPreview(false);
    QueueCast(Skill,false);
}
bool UFPSFireMagicComponent::PrepareCastRequest(FName Skill,FFireMagicCast& Spell,bool bRequireCastAssets)
{
    if(UBoundCongregateCaptureComponent::IsCaptured(GetOwner()))return false;
    auto* Player=Cast<AFPSGAMECharacter>(GetOwner());auto* M=Model();
    if(!FireMagic::IsSkill(Skill)||!Player||!M||!Player->IsLocallyControlled())return false;
    if(const auto* Health=Player->FindComponentByClass<UFPSCombatHealthComponent>();Health&&Health->IsDead())return false;
    if(!CommittedSkill.IsNone())return false;
    if(Skill==TEXT("meteor")&&bMeteorAwaitingResult){Feedback(Skill,TEXT("等待施法确认"));return false;}
    if(IsDragonBreathActive()||bDragonAwaitingRelease){Feedback(Skill,TEXT("龙息喷吐中"));return false;}
    if(const auto* H=Hands();H&&H->HasOtherPreparedSpell(this))
    {QueuedSkill=NAME_None;Feedback(Skill,TEXT("先释放已积蓄魔法"));return false;}
    if(Player->IsSpellHandHeld()){RejectHeldHand(Skill);return false;}
    if(bRequireCastAssets&&Skill==TEXT("dragonBreath")&&!IsDragonBreathVisualReady()){Feedback(Skill,TEXT("火焰准备中"));return false;}
    if(bRequireCastAssets&&(!CastSound||(Skill!=TEXT("dragonBreath")&&(Skill==TEXT("meteor")?!bMeteorAssetsReady:(!AuraSystem||!WeaponSystem||!SparkSystem))))){Feedback(Skill,TEXT("素材准备中"));return false;}
    Spell=M->FireMagicStats(Skill);FString Failure;
    if(!Allowed(Spell,Failure)){Feedback(Skill,Failure);return false;}
    return true;
}
void UFPSFireMagicComponent::QueueCast(FName Skill,bool bUsePreviewTarget)
{
    FFireMagicCast Spell;if(!PrepareCastRequest(Skill,Spell))return;
    if(Skill==TEXT("meteor"))
    {
        FString Failure;
        if(!bUsePreviewTarget&&!SelectGround(Spell,LockedPoint,LockedNormal,Failure))
        {Feedback(Skill,Failure);return;}
        if(FVector::Dist2D(GetOwner()->GetActorLocation(),LockedPoint)>Spell.Range)
        {Feedback(Skill,TEXT("超出施法距离"));return;}
    }
    auto* Player=Cast<AFPSGAMECharacter>(GetOwner());
    if(auto* Sword=Player->FindComponentByClass<URuneSwordComponent>();Sword&&Sword->IsGuarding())Sword->ReleaseGuard();
    QueuedSkill=Skill;MessageUntil=0;ServiceQueue();
}
bool UFPSFireMagicComponent::MeteorPreviewInputAvailable() const
{
    const auto* Player=Cast<AFPSGAMECharacter>(GetOwner());
    const auto* PC=Player?Cast<APlayerController>(Player->GetController()):nullptr;
    const auto* M=Model();
    if(!PC||AFPSGAMEPlayerController::BlocksOngoingActions(PC)||Player->IsChoosingAmmo())return false;
    if(const auto* Builder=PC->FindComponentByClass<UVoxelBuildComponent>();Builder&&Builder->IsBuilding())return false;
    return Player&&Player->IsLocallyControlled()&&PC&&!PC->bShowMouseCursor&&!PC->IsLookInputIgnored()&&!PC->IsMoveInputIgnored()
        &&M&&M->HasEquippedStaff()&&!Player->IsSpellHandHeld()&&!UBoundCongregateCaptureComponent::IsCaptured(GetOwner());
}
void UFPSFireMagicComponent::SetMeteorAimPreview(bool bActive)
{
    if(!bActive)
    {
        bMeteorAimPreview=bMeteorPreviewValid=false;
        if(MeteorAimDecal)MeteorAimDecal->SetHiddenInGame(true);
        return;
    }
    if(bMeteorAimPreview)return;
    // Hold remains active while background spell assets arrive; release still
    // requires the complete cast assets before it can spend mana.
    if(!PrepareCastRequest(TEXT("meteor"),MeteorPreviewSnapshot,false)||!MeteorPreviewInputAvailable())return;
    QueuedSkill=NAME_None;bMeteorAimPreview=true;MessageUntil=0;
    RefreshMeteorPreview();
}
void UFPSFireMagicComponent::RefreshMeteorPreview()
{
    if(!bMeteorAimPreview)return;
    MeteorPreviewFailure.Reset();
    bMeteorPreviewValid=SelectGround(MeteorPreviewSnapshot,LockedPoint,LockedNormal,MeteorPreviewFailure);
    if(!bMeteorPreviewValid||!MeteorAimMaterial)
    {
        if(!MeteorAimMaterial){bMeteorPreviewValid=false;MeteorPreviewFailure=TEXT("范围预览准备中");}
        if(MeteorAimDecal)MeteorAimDecal->SetHiddenInGame(true);
        return;
    }
    const bool bCreateDecal=!MeteorAimDecal;
    if(bCreateDecal)
    {
        MeteorAimDecal=NewObject<UDecalComponent>(GetOwner(),TEXT("MeteorAimDecal"));
        GetOwner()->AddInstanceComponent(MeteorAimDecal);
        MeteorAimDecal->SetDecalMaterial(MeteorAimMaterial);
        MeteorAimDecal->SetWorldRotation(FRotationMatrix::MakeFromX(-LockedNormal).Rotator());
        MeteorAimDecal->RegisterComponent();
        MeteorAimDecal->SetFadeScreenSize(0.f);
        MeteorAimMID=MeteorAimDecal->CreateDynamicMaterialInstance();
    }
    // Damage and fuel patches use the landing plane, including its 100 cm band.
    const FVector Location=LockedPoint+LockedNormal*4.f;
    const FRotator Rotation=FRotationMatrix::MakeFromX(-LockedNormal).Rotator();
    if(bCreateDecal||!MeteorAimDecal->GetComponentLocation().Equals(Location,.001f)
        ||!MeteorAimDecal->GetComponentRotation().Equals(Rotation,.001f))
    {
        MeteorAimDecal->SetWorldLocationAndRotation(Location,Rotation);
        if(MeteorAimMID)
        {
            MeteorAimMID->SetVectorParameterValue(TEXT("Center"),FLinearColor(LockedPoint));
            MeteorAimMID->SetVectorParameterValue(TEXT("SurfaceNormal"),FLinearColor(LockedNormal));
        }
    }
    // Radius is fixed for one hold. Do not rebuild decal bounds or resubmit
    // constant material parameters on every camera frame.
    const FVector2D Radii(MeteorPreviewSnapshot.Radius,MeteorPreviewSnapshot.AuraRadius);
    if(bCreateDecal||MeteorPreviewRadii!=Radii)
    {
        const FVector Size(104,Radii.X+16,Radii.X+16);
        if(MeteorAimDecal->DecalSize!=Size){MeteorAimDecal->DecalSize=Size;MeteorAimDecal->MarkRenderStateDirty();}
        if(MeteorAimMID)
        {
            MeteorAimMID->SetScalarParameterValue(TEXT("ImpactRadius"),Radii.X);
            MeteorAimMID->SetScalarParameterValue(TEXT("FieldRadius"),Radii.Y);
        }
        MeteorPreviewRadii=Radii;
    }
    if(MeteorAimDecal->bHiddenInGame)MeteorAimDecal->SetHiddenInGame(false);
}
void UFPSFireMagicComponent::ReleaseMeteorAimPreview()
{
    if(!bMeteorAimPreview)return;
    if(!MeteorPreviewInputAvailable()){SetMeteorAimPreview(false);return;}
    const bool Valid=bMeteorPreviewValid;const FString Failure=MeteorPreviewFailure;
    SetMeteorAimPreview(false);
    if(!Valid){Feedback(TEXT("meteor"),Failure);return;}
    // Keep exactly the last displayed point throughout queuing and the gesture.
    QueueCast(TEXT("meteor"),true);
}
void UFPSFireMagicComponent::ServiceQueue()
{
    if(QueuedSkill.IsNone()||bMeteorAimPreview)return;
    auto* Player=Cast<AFPSGAMECharacter>(GetOwner());auto* M=Model();auto* H=Hands();if(!Player||!M||!H)return;
    if(H->HasOtherPreparedSpell(this))
    {Feedback(QueuedSkill,TEXT("先释放已积蓄魔法"));QueuedSkill=NAME_None;return;}
    if(Player->IsSpellHandHeld()){RejectHeldHand(QueuedSkill);return;}
    const auto* PC=Cast<APlayerController>(Player->GetController());
    if(!PC||PC->IsLookInputIgnored()||PC->IsMoveInputIgnored()){QueuedSkill=NAME_None;return;}
    if(H->BlocksNewLeftHandAction()||Player->IsSpellHandBusy())return;
    const auto Spell=M->FireMagicStats(QueuedSkill);FString Failure;
    if(QueuedSkill==TEXT("meteor")&&FVector::Dist2D(Player->GetActorLocation(),LockedPoint)>Spell.Range)
    {Feedback(QueuedSkill,TEXT("超出施法距离"));QueuedSkill=NAME_None;return;}
    if(!Allowed(Spell,Failure))
    {Feedback(QueuedSkill,Failure);QueuedSkill=NAME_None;return;}
    if(QueuedSkill==TEXT("meteor")&&!MeteorGround::Validate(Player,Spell.Range,LockedPoint,LockedNormal,true,Failure))
    {Feedback(QueuedSkill,Failure);QueuedSkill=NAME_None;return;}
    if(QueuedSkill==TEXT("dragonBreath"))
    {
        if(PC->bShowMouseCursor){QueuedSkill=NAME_None;return;}
        if(!IsDragonBreathVisualReady()){QueuedSkill=NAME_None;Feedback(TEXT("dragonBreath"),TEXT("火焰准备中"));return;}
    }
    const bool bPushGesture=Spell.Skill!=TEXT("flameArmor");
    if(!H->TryBeginSpellGesture(this,bPushGesture,Spell.CastSpeed,FSimpleDelegate::CreateUObject(this,&ThisClass::ReleaseAtContact)))return;
    QueuedSkill=NAME_None;
    const float BeforeMana=M->Snapshot().Mana;
    if(!M->BeginFireMagicCast(Spell)){H->CancelSpellGesture(this);return;}
    H->RecordGesturePayment(BeforeMana,M->Snapshot().Mana,true);
    CastSnapshot=Spell;CommittedSkill=Spell.Skill;MessageUntil=0;
    if(auto* Status=Player->FindComponentByClass<UCombatStatusFormula>())Status->ConsumeChainSpell();
    // 联机客人：凝聚扣账上报；陨星落点/焰甲激活由服务端在释放相位结算。
    if(GetWorld()->GetNetMode()==NM_Client)
    {
        bNetPaid=true;const uint32 Sequence=Spell.Skill==TEXT("meteor")
            ?NetCast::Send(Player,Spell.Skill,0,LockedPoint,LockedNormal):NetCast::Send(Player,Spell.Skill,0);
        if(Spell.Skill==TEXT("meteor"))
        {
            MeteorLocalCastId=Sequence;MeteorPendingRefund=0.f;
            if(!Sequence){CancelPending();Feedback(Spell.Skill,TEXT("联机施法未就绪"));}
        }
        if(Spell.Skill==TEXT("flameArmor"))
        {
            ArmorLocalCastId=Sequence;ArmorPendingRefund=0.f;
            if(!Sequence){CancelPending();Feedback(Spell.Skill,TEXT("联机施法未就绪"));}
        }
        if(Spell.Skill==TEXT("dragonBreath"))
        {
            DragonLocalCastId=Sequence;DragonPrediction=FDragonBreathState();
            if(!Sequence){CancelPending();Feedback(Spell.Skill,TEXT("联机施法未就绪"));}
        }
    }
}
void UFPSFireMagicComponent::ReleaseAtContact()
{
    if(CommittedSkill.IsNone())return;const FName Skill=CommittedSkill;CommittedSkill=NAME_None;
    auto* Player=Cast<AFPSGAMECharacter>(GetOwner());if(!Player)return;
    if(Skill==TEXT("flameArmor"))
        if(const auto* Status=Player->FindComponentByClass<UCombatStatusFormula>();Status&&Status->IsImmune())
        {
            if(auto* M=Model())M->RefundUnreleasedCast(Hands()?Hands()->TakeGesturePayment():0.f,Skill);
            if(GetNetMode()==NM_Client&&bNetPaid)
                NetCast::Send(Player,Skill,2,FVector::ZeroVector,FVector::UpVector,0,nullptr,0,FVector::ForwardVector,ArmorLocalCastId);
            bNetPaid=false;if(auto* H=Hands())H->CancelSpellGesture(this);
            Feedback(Skill,TEXT("状态免疫"));return;
        }
    if(auto* M=Model();M&&CastSnapshot.bRequiresStaff&&!M->HasEquippedStaff())
    {
        CommittedSkill=Skill;CancelPending();
        Feedback(Skill,TEXT("需要法杖"));return;
    }
    if(Skill==TEXT("dragonBreath"))
    {
        const bool Client=GetWorld()->GetNetMode()==NM_Client;
        const FVector Nozzle=CaptureDragonNozzle();
        FString Failure;
        if(!StartDragonBreath(CastSnapshot,Client,Client?DragonLocalCastId:0,Nozzle,&Failure))
        {
            if(auto* M=Model())M->RefundUnreleasedCast(Hands()?Hands()->TakeGesturePayment():0.f,Skill);
            RequestDragonStop();bNetPaid=false;
            if(auto* H=Hands())H->CancelSpellGesture(this);
            Feedback(Skill,Failure);return;
        }
        if(Client)
        {
            bDragonAwaitingRelease=true;bNetPaid=false;
            NetCast::Send(Player,Skill,1,Nozzle,FVector::UpVector,0,nullptr,0,FVector::ForwardVector,DragonLocalCastId);
        }
        else if(auto* H=Hands())H->TakeGesturePayment();
    }
    else if(Skill==TEXT("meteor"))
    {
        FString Failure;
        if(!MeteorGround::Validate(Player,CastSnapshot.Range,LockedPoint,LockedNormal,false,Failure))
        {CommittedSkill=Skill;CancelPending();Feedback(Skill,Failure);return;}
        // 联机客人：落点/法线上报服务端，权威陨星复制回来；本地收尾预扣账。
        if(GetWorld()->GetNetMode()==NM_Client)
        {
            MeteorPendingRefund=Hands()?Hands()->TakeGesturePayment():0.f;
            MeteorReleasedCast=CastSnapshot;bMeteorAwaitingResult=true;bNetPaid=false;
            if(!NetCast::Send(Player,Skill,1,LockedPoint,LockedNormal,0,nullptr,0,FVector::ForwardVector,MeteorLocalCastId))
            {NetMeteorCastResult(1,7,MeteorLocalCastId);return;}
            UGameplayStatics::PlaySoundAtLocation(this,CastSound,Player->GetActorLocation());
            return;
        }
        FActorSpawnParameters P;P.Owner=Player;P.Instigator=Player;P.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        auto* Strike=GetWorld()->SpawnActor<AFPSMeteorStrike>(LockedPoint,FRotator::ZeroRotator,P);
        if(!Strike||!Strike->InitializeStrike(Player,CastSnapshot,LockedPoint,LockedNormal))
        {if(Strike)Strike->Destroy();CommittedSkill=Skill;CancelPending();Feedback(Skill,TEXT("陨星素材未就绪"));return;}
        Strikes.Add(Strike);
        if(auto* H=Hands())H->TakeGesturePayment();
    }
    else
    {
        // 联机客人：焰甲激活上报——服务端跑权威灼烧，远端副本靠 bNetArmor 演火环。
        if(GetWorld()->GetNetMode()==NM_Client)
        {
            ArmorPendingRefund=Hands()?Hands()->TakeGesturePayment():0.f;
            NetCast::Send(Player,Skill,1,FVector::ZeroVector,FVector::UpVector,0,nullptr,0,FVector::ForwardVector,ArmorLocalCastId);
            bNetPaid=false;
        }
        else if(auto* H=Hands())H->TakeGesturePayment();
        StartArmor();
    }
    if(Skill!=TEXT("dragonBreath"))if(auto* M=Model())M->NotifyMagicReleased();
    if(Skill!=TEXT("dragonBreath"))UGameplayStatics::PlaySoundAtLocation(this,CastSound,Player->GetActorLocation());
    if(auto* Status=UCombatStatusFormula::GetOrAdd(Player))
    {if(CastSnapshot.bGrantChain)Status->AddChainSpell();if(CastSnapshot.CastHasteStacks>0)Status->AddHaste(CastSnapshot.CastHasteStacks,CastSnapshot.CastHasteDuration);}
}
void UFPSFireMagicComponent::StartArmor(UColdSteelStatusModel* RewardModel,uint32 CastId)
{
    EndArmor(true);ArmorSnapshot=CastSnapshot;ArmorTime=ArmorSnapshot.Duration;AuraTimer=0;
    StarMarrow::CaptureSpell(GetOwner(),ArmorSnapshot.StarMarrow);
    if(GetOwner()->HasAuthority())ArmorRewardModel=RewardModel?RewardModel:NetCast::AuthorityModel(Cast<APawn>(GetOwner()),GetWorld()->GetGameInstance());
    else bArmorAwaitingReplication=ArmorLocalCastId!=0;
    SpawnArmorFX();
    TickArmor(0);
    // 旧 flame-armor-system：命中即刷 🔥 护盾卡片，duration 跟随技能面板。
    UStatusEffectsComponent::GetOrCreate(GetOwner())->SetTimed(TEXT("flameArmor"),ArmorSnapshot.Duration);
    if(GetOwner()->HasAuthority())
    {
        NetArmor.Cast=ArmorSnapshot;NetArmor.CastId=CastId;NetArmor.bActive=true;++NetArmor.Serial;
        NetArmor.StartedAt=GetWorld()->GetGameState()?GetWorld()->GetGameState()->GetServerWorldTimeSeconds():GetWorld()->GetTimeSeconds();
        GetOwner()->ForceNetUpdate();
    }
}
// 光环/武器火焰的 FX 壳——本地激活与远端 OnRep 共用。
void UFPSFireMagicComponent::SpawnArmorFX()
{
    if(GetNetMode()==NM_DedicatedServer||!AuraSystem||IsValid(AuraFX))return;
    AuraFX=UNiagaraFunctionLibrary::SpawnSystemAttached(AuraSystem,GetOwner()->GetRootComponent(),NAME_None,FVector::ZeroVector,FRotator::ZeroRotator,EAttachLocation::KeepRelativeOffset,false,false);
    if(AuraFX)
    {
        AuraFX->SetAbsolute(true,true,true);AuraFX->SetWorldRotation(FRotator::ZeroRotator);
        AuraFX->SetVariableFloat(TEXT("User.Fade"),0.f);
        AuraFX->SetCastShadow(false);AuraFX->SetVisibleInRayTracing(false);
        AuraFX->AddTickPrerequisiteComponent(this);AuraFX->SetTickBehavior(ENiagaraTickBehavior::UsePrereqs);
        // The ring component is now at the feet; the old torso-relative -55 cm
        // offset placed its thermal proxy underground. Match the V5 ring wall.
        const auto* Capsule=GetOwner()->FindComponentByClass<UCapsuleComponent>();
        const float RingRadius=1.2f*FMath::Max(62.f,(Capsule?Capsule->GetScaledCapsuleRadius():42.f)+28.f);
        UThermalTargetSubsystem::RegisterFire(AuraFX,FVector(RingRadius,RingRadius,28),FVector(0,0,28));
    }
}
void UFPSFireMagicComponent::RefreshArmorVisuals()
{
    if(const auto* Health=GetOwner()->FindComponentByClass<UFPSCombatHealthComponent>();Health&&Health->IsDead())return;
    // Asset arrival is not a rejection of a locally predicted release. The
    // reliable receipt / matching replicated cast owns that reconciliation.
    if(GetOwner()->HasAuthority()||bArmorAwaitingReplication)
    {if(ArmorTime>0){SpawnArmorFX();TickArmor(0.f);}return;}
    OnRep_Armor();
}
void UFPSFireMagicComponent::OnRep_Armor()
{
    if(bArmorAwaitingReplication&&NetArmor.CastId!=ArmorLocalCastId)return;
    if(NetArmor.CastId&&NetArmor.CastId==ArmorLocalCastId)
    {ArmorConfirmedCastId=NetArmor.CastId;ArmorPendingRefund=0.f;}
    bArmorAwaitingReplication=false;
    if(const auto* Health=GetOwner()->FindComponentByClass<UFPSCombatHealthComponent>();Health&&Health->IsDead())
    {EndArmor(false);AppliedArmorSerial=NetArmor.Serial;return;}
    const double Now=GetWorld()->GetGameState()?GetWorld()->GetGameState()->GetServerWorldTimeSeconds():GetWorld()->GetTimeSeconds();
    const float Remaining=FMath::Max(0.,NetArmor.StartedAt+NetArmor.Cast.Duration-Now);
    if(!NetArmor.bActive||Remaining<=0.f){EndArmor(false);AppliedArmorSerial=NetArmor.Serial;return;}
    if(AppliedArmorSerial!=NetArmor.Serial||ArmorTime<=0.f||(!AuraFX&&AuraSystem))
    {
        EndArmor(false);ArmorSnapshot=NetArmor.Cast;SpawnArmorFX();
        AppliedArmorSerial=NetArmor.Serial;
    }
    ArmorTime=Remaining;AuraTimer=0;
    auto* Status=UStatusEffectsComponent::GetOrCreate(GetOwner());
    Status->Remove(TEXT("flameArmor"));Status->SetTimed(TEXT("flameArmor"),Remaining);
    TickArmor(0.f);
}
void UFPSFireMagicComponent::Sparks(const FVector& Point)
{if(SparkSystem)UNiagaraFunctionLibrary::SpawnSystemAtLocation(this,SparkSystem,Point,FRotator::ZeroRotator,FVector(1),true,true,ENCPoolMethod::AutoRelease);}
void UFPSFireMagicComponent::OnWeaponHit(AActor* Target,const FVector& Point)
{
    if(ArmorTime<=0||!GetOwner()->HasAuthority())return;
    auto* Player=Cast<APawn>(GetOwner());auto* M=ArmorRewardModel.Get();
    if(M&&M->ApplyFireMagicHit(Player,Target,ArmorSnapshot,ArmorSnapshot.Damage,ArmorRewards))Sparks(Point);
}
void UFPSFireMagicComponent::TickArmor(float Delta)
{
    if(ArmorTime<=0)return;
    auto* Player=Cast<ACharacter>(GetOwner());
    const bool Authority=GetOwner()->HasAuthority();
    auto* M=Authority?ArmorRewardModel.Get():nullptr;
    if(!Player||(Authority&&!M)){EndArmor(false);return;}
    const float ActiveDelta=FMath::Min(Delta,ArmorTime);ArmorTime=FMath::Max(0.f,ArmorTime-Delta);AuraTimer+=ActiveDelta;
    if(!Authority&&!bArmorAwaitingReplication&&NetArmor.bActive&&AppliedArmorSerial==NetArmor.Serial)
    {
        const double Now=GetWorld()->GetGameState()?GetWorld()->GetGameState()->GetServerWorldTimeSeconds():GetWorld()->GetTimeSeconds();
        ArmorTime=FMath::Max(0.,NetArmor.StartedAt+NetArmor.Cast.Duration-Now);
    }
    const FVector Feet=Player->GetActorLocation()-FVector(0,0,Player->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()-5);
    while(Authority&&AuraTimer+UE_KINDA_SMALL_NUMBER>=ArmorSnapshot.TickSeconds)
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
    UpdateArmorBodyFX(Fade,Feet);
    UpdateArmorWeaponFX(Delta,Fade);
    if(ArmorTime<=0)EndArmor(true);
}
void UFPSFireMagicComponent::EndArmor(bool bTrain)
{
    if(GetOwner()->HasAuthority()&&NetArmor.bActive){NetArmor.bActive=false;GetOwner()->ForceNetUpdate();}
    auto* RewardModel=ArmorRewardModel.Get();const FFireMagicRewards Rewards=ArmorRewards;
    ArmorRewardModel.Reset();bArmorAwaitingReplication=false;
    if(auto* Status=GetOwner()->FindComponentByClass<UStatusEffectsComponent>())Status->Remove(TEXT("flameArmor"));
    ArmorTime=0;AuraTimer=0;ArmorRewards={};
    if(AuraFX){AuraFX->DestroyComponent();AuraFX=nullptr;}
    for(auto& FX:WeaponFX)if(FX)FX->DestroyComponent();WeaponFX.Reset();
    for(auto& History:WeaponHistory)History=FFlameArmorHistory();
    bArmorFeetValid=false;
    // Clear the batch before callbacks; removal and EndPlay may both settle it.
    const auto* Health=GetOwner()->FindComponentByClass<UFPSCombatHealthComponent>();
    if(bTrain&&GetOwner()->HasAuthority()&&RewardModel&&(!Health||!Health->IsDead()))RewardModel->FinishFireMagicCast(TEXT("flameArmor"),Rewards);
}
void UFPSFireMagicComponent::CancelPending()
{
    SetMeteorAimPreview(false);
    const bool PendingDragon=CommittedSkill==TEXT("dragonBreath");
    const bool PendingMeteor=CommittedSkill==TEXT("meteor");
    if(PendingDragon||CommittedSkill==TEXT("flameArmor")||PendingMeteor)
        if(auto* M=Model())M->RefundUnreleasedCast(Hands()?Hands()->TakeGesturePayment():0.f,CommittedSkill);
    if(PendingMeteor){MeteorResolvedCastId=MeteorLocalCastId;MeteorPendingRefund=0.f;}
    if(PendingDragon||IsDragonBreathActive()||bDragonAwaitingRelease)RequestDragonStop();
    if(!CommittedSkill.IsNone())Feedback(CommittedSkill,TEXT("施法中断"));
    // 联机客人：凝聚期中断——服务端按 Phase2 退预留。
    if(!PendingDragon&&GetWorld()&&GetWorld()->GetNetMode()==NM_Client&&bNetPaid&&!CommittedSkill.IsNone())
        NetCast::Send(GetOwner(),CommittedSkill,2,FVector::ZeroVector,FVector::UpVector,0,nullptr,0,FVector::ForwardVector,
            CommittedSkill==TEXT("flameArmor")?ArmorLocalCastId:PendingMeteor?MeteorLocalCastId:0);
    bNetPaid=false;
    QueuedSkill=NAME_None;CommittedSkill=NAME_None;if(auto* H=Hands())H->CancelSpellGesture(this);
}
void UFPSFireMagicComponent::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(UFPSFireMagicComponent,NetArmor);
    DOREPLIFETIME(UFPSFireMagicComponent,DragonState);
}
// ── 联机服务端入口：陨星定点生成（复制各端）/焰甲服务端权威激活 ──
bool UFPSFireMagicComponent::NetRelease(APawn* Caster,const FColdSteelNetCastRequest& Req,UColdSteelStatusModel* Shadow,const FFireMagicCast& Spell,bool bMeteorTargetLocked)
{
    if(!Caster||!Caster->HasAuthority()||!Shadow||
        (Shadow->FireMagicDefinition(Req.SkillId).FireMagic.bRequiresStaff&&!Shadow->HasEquippedStaff()))return false;
    if(Req.SkillId==TEXT("flameArmor"))
        if(const auto* Status=Caster->FindComponentByClass<UCombatStatusFormula>();Status&&Status->IsImmune())return false;
    CastSnapshot=Spell;
    if(Req.SkillId==TEXT("dragonBreath"))
    {
        if(!Req.CastId||!StartDragonBreath(Spell,false,Req.CastId,Req.AimPoint))return false;
        if(auto* Status=UCombatStatusFormula::GetOrAdd(Caster))
        {if(Spell.bGrantChain)Status->AddChainSpell();if(Spell.CastHasteStacks>0)Status->AddHaste(Spell.CastHasteStacks,Spell.CastHasteDuration);}
        return true;
    }
    if(Req.SkillId==TEXT("meteor"))
    {
        if(!Req.CastId||Spell.Skill!=Req.SkillId||Req.AimPoint.ContainsNaN()||Req.AimNormal.ContainsNaN()||Req.AimNormal.Z<.45f)return false;
        // A production release uses the point accepted by this server at prepare.
        // Direct callers still need initial sight validation.
        FVector Point=Req.AimPoint,Normal=Req.AimNormal;FString Failure;
        if(!MeteorGround::Validate(Caster,Spell.Range,Point,Normal,!bMeteorTargetLocked,Failure))return false;
        FActorSpawnParameters P;P.Owner=Caster;P.Instigator=Caster;P.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        auto* Strike=GetWorld()->SpawnActor<AFPSMeteorStrike>(Point,FRotator::ZeroRotator,P);
        if(!Strike||!Strike->InitializeStrike(Caster,Spell,Point,Normal))
        {if(Strike)Strike->Destroy();return false;}
        Strikes.Add(Strike);
        if(auto* Status=UCombatStatusFormula::GetOrAdd(Caster))
        {if(Spell.bGrantChain)Status->AddChainSpell();if(Spell.CastHasteStacks>0)Status->AddHaste(Spell.CastHasteStacks,Spell.CastHasteDuration);}
        // The strike owns one reward batch, settled at completion or removal.
        return true;
    }
    // flameArmor：服务端组件 TickArmor 走影子档案结算灼烧；bNetArmor 复制表现。
    if(Req.SkillId!=TEXT("flameArmor")||Spell.Skill!=Req.SkillId||!Req.CastId)return false;
    StartArmor(Shadow,Req.CastId);
    if(CastSound)UGameplayStatics::PlaySoundAtLocation(this,CastSound,Caster->GetActorLocation());
    if(auto* Status=UCombatStatusFormula::GetOrAdd(Caster))
    {if(Spell.bGrantChain)Status->AddChainSpell();if(Spell.CastHasteStacks>0)Status->AddHaste(Spell.CastHasteStacks,Spell.CastHasteDuration);}
    return true;
}
void UFPSFireMagicComponent::NetCastRejected(uint8 Phase,uint8 /*Code*/)
{
    if(Phase==1&&CastSnapshot.Skill==TEXT("flameArmor"))EndArmor(false);
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
void UFPSFireMagicComponent::NetMeteorCastResult(uint8 Phase,uint8 Code,uint32 CastId)
{
    if(!CastId||CastId!=MeteorLocalCastId||CastId==MeteorResolvedCastId||Phase>1)return;
    if(Code==0)
    {
        if(Phase!=1)return;
        MeteorResolvedCastId=CastId;MeteorPendingRefund=0.f;bMeteorAwaitingResult=false;
        if(auto* Status=UCombatStatusFormula::GetOrAdd(GetOwner()))
        {
            if(MeteorReleasedCast.bGrantChain)Status->AddChainSpell();
            if(MeteorReleasedCast.CastHasteStacks>0)Status->AddHaste(MeteorReleasedCast.CastHasteStacks,MeteorReleasedCast.CastHasteDuration);
        }
        return;
    }
    const bool Pending=CommittedSkill==TEXT("meteor");
    const float Refund=Pending&&Hands()?Hands()->TakeGesturePayment():MeteorPendingRefund;
    MeteorResolvedCastId=CastId;MeteorPendingRefund=0.f;bMeteorAwaitingResult=false;
    if(auto* M=Model())M->RefundUnreleasedCast(Refund,TEXT("meteor"));
    if(Pending){CommittedSkill=NAME_None;bNetPaid=false;if(auto* H=Hands())H->CancelSpellGesture(this);}
    if(QueuedSkill==TEXT("meteor"))QueuedSkill=NAME_None;
    Feedback(TEXT("meteor"),TEXT("施法失败，已退还消耗"));
}
void UFPSFireMagicComponent::NetArmorCastResult(uint8 Phase,uint8 Code,uint32 CastId)
{
    if(!CastId||CastId!=ArmorLocalCastId)return;
    if(Code==0)
    {
        if(Phase==1){ArmorConfirmedCastId=CastId;ArmorPendingRefund=0.f;}
        // Keep prediction until its matching state arrives, even if the RPC
        // receipt beat property replication to this client.
        if(Phase>=2&&CommittedSkill==TEXT("flameArmor"))bNetPaid=false;
        return;
    }
    if(Phase>1||ArmorConfirmedCastId==CastId||ArmorRejectedCastId==CastId)return;
    ArmorRejectedCastId=CastId;
    const bool Pending=CommittedSkill==TEXT("flameArmor");
    const float Refund=Pending&&Hands()?Hands()->TakeGesturePayment():ArmorPendingRefund;ArmorPendingRefund=0.f;
    if(auto* M=Model())M->RefundUnreleasedCast(Refund,TEXT("flameArmor"));
    if(bArmorAwaitingReplication)EndArmor(false);
    if(Pending){CommittedSkill=NAME_None;bNetPaid=false;if(auto* H=Hands())H->CancelSpellGesture(this);}
    if(QueuedSkill==TEXT("flameArmor"))QueuedSkill=NAME_None;
    // A rejected refresh must restore a still-active preceding authority cast.
    if(!GetOwner()->HasAuthority())OnRep_Armor();
    Feedback(TEXT("flameArmor"),TEXT("施法失败"));
}
void UFPSFireMagicComponent::FinishFireMagicForRemoval()
{
    if(!GetOwner()->HasAuthority())return;
    FinishDragonBreathForRemoval();
    EndArmor(true);
    auto Active=MoveTemp(Strikes);Strikes.Reset();
    for(auto& Strike:Active)if(Strike.IsValid())Strike->FinishForRemoval();
}
void UFPSFireMagicComponent::ClearEffects()
{
    // Notify the server before local death/teardown clears the predicted state.
    CancelPending();StopDragonBreath(false);bDragonAwaitingRelease=false;
    DestroyDragonBreathAudio();
    // Death, EndPlay and explicit effect cleanup do not leave a visual tail.
    if(DragonFX){DragonFX->DestroyComponent();DragonFX=nullptr;}DragonTailTime=0;
    EndArmor(false);for(auto& Strike:Strikes)if(Strike.IsValid())Strike->Destroy();Strikes.Reset();ImpactTime=-1;
}
void UFPSFireMagicComponent::NotifyMeteorImpact(const FVector& Point)
{
    ImpactTime=GetWorld()->GetTimeSeconds();
    const float Distance=float(FVector::Distance(GetOwner()->GetActorLocation(),Point));
    ImpactStrength=FMath::SmoothStep(0.f,1.f,FMath::Clamp(1.f-Distance/1800.f,0.f,1.f));
}
void UFPSFireMagicComponent::GetCameraMotion(FVector& Location,FRotator& Rotation) const
{
    if(ImpactTime<0||!GetWorld())return;
    const float Age=GetWorld()->GetTimeSeconds()-ImpactTime;
    if(Age<0||Age>=.28f)return;
    const float Kick=Age<.08f?FMath::Sin(UE_PI*Age/.08f):0.f;
    const float Rebound=Age>=.06f&&Age<.26f?FMath::Sin(UE_PI*(Age-.06f)/.20f):0.f;
    const float Rattle=FMath::Sin(Age*76.f)*FMath::Exp(-Age*24.f);
    Location+=FVector(0,Rattle*.10f,-1.4f*Kick+.42f*Rebound)*ImpactStrength;
    Rotation+=FRotator(.85f*Kick-.24f*Rebound,Rattle*.06f,Rattle*.08f)*ImpactStrength;
}
void UFPSFireMagicComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick)
{
    Super::TickComponent(Delta,Type,Tick);
    if(const auto* Health=GetOwner()->FindComponentByClass<UFPSCombatHealthComponent>();Health&&Health->IsDead())
    {if(!CommittedSkill.IsNone())if(auto* M=Model())M->RefundUnreleasedCast(Hands()?Hands()->TakeGesturePayment():0.f,CommittedSkill);ClearEffects();return;}
    if(!CommittedSkill.IsNone()&&(!Hands()||!Hands()->IsSpellGesture(this)))
    {
        if(CommittedSkill==TEXT("flameArmor")||CommittedSkill==TEXT("meteor"))CancelPending();
        else if(CommittedSkill==TEXT("dragonBreath"))
        {
            if(auto* M=Model())M->RefundUnreleasedCast(Hands()?Hands()->TakeGesturePayment():0.f,CommittedSkill);
            RequestDragonStop();
            bNetPaid=false;
        }
        CommittedSkill=NAME_None;
    }
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
    if(bMeteorAimPreview)
    {
        if(!MeteorPreviewInputAvailable()||(Hands()&&Hands()->HasOtherPreparedSpell(this)))SetMeteorAimPreview(false);
        // PostUpdateWork runs after the camera. A 100 ms timer here made the
        // target jump at 10 Hz regardless of the game's actual frame rate.
        else RefreshMeteorPreview();
    }
    Strikes.RemoveAll([](const auto& A){return !A.IsValid();});TickArmor(Delta);TickDragonBreath(Delta);ServiceQueue();
}
void UFPSFireMagicComponent::EndPlay(EEndPlayReason::Type Reason)
{
    FinishFireMagicForRemoval();ClearEffects();
    if(MeteorAimLoad)MeteorAimLoad->CancelHandle();MeteorAimLoad.Reset();
    if(MeteorAimDecal){MeteorAimDecal->DestroyComponent();MeteorAimDecal=nullptr;}
    MeteorAimMID=nullptr;
    if(DragonLoad)DragonLoad->CancelHandle();DragonLoad.Reset();Super::EndPlay(Reason);
}
