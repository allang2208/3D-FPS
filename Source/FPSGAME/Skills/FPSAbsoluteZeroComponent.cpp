#include "FPSAbsoluteZeroComponent.h"
#include "FPSAbsoluteZeroNova.h"
#include "FPSFrostSurfaceMesh.h"
#include "FPSFireballComponent.h"
#include "FPSIceArmorComponent.h"
#include "BlizzardEnvironment.h"
#include "PlayerSkillPreparation.h"
#include "NetCastUtils.h"
#include "../FPSGAMECharacter.h"
#include "../FPSGAMEPlayerController.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Monsters/BoundCongregateCaptureComponent.h"
#include "../Movement/PlayerKnockdownComponent.h"
#include "../Building/VoxelBuildComponent.h"
#include "../Weapons/RuneSwordComponent.h"
#include "../Weapons/Staff/StaffWeaponComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/DynamicMeshComponent.h"
#include "Components/PointLightComponent.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"
#include "Net/UnrealNetwork.h"
#include "NiagaraComponent.h"
#include "NiagaraFunctionLibrary.h"
#include "NiagaraSystem.h"
#include "Sound/SoundBase.h"

UFPSAbsoluteZeroComponent::UFPSAbsoluteZeroComponent()
{
    PrimaryComponentTick.bCanEverTick=true;
    PrimaryComponentTick.bStartWithTickEnabled=false;
    PrimaryComponentTick.TickGroup=TG_PostUpdateWork;
    SetIsReplicatedByDefault(true);
}

void UFPSAbsoluteZeroComponent::UpdateTickState()
{
    const bool bNeedTick=bQueued||bChanneling||bNetChanneling||bNetAwaitingRelease||bNetAwaitingCancel||SlamRecoveryAge>=0.f;
    if(IsComponentTickEnabled()!=bNeedTick)SetComponentTickEnabled(bNeedTick);
}

void UFPSAbsoluteZeroComponent::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(UFPSAbsoluteZeroComponent,bNetChanneling);
    DOREPLIFETIME(UFPSAbsoluteZeroComponent,NetChannelDuration);
    DOREPLIFETIME(UFPSAbsoluteZeroComponent,NetChannelReduction);
    DOREPLIFETIME(UFPSAbsoluteZeroComponent,bNetArmorSynergy);
    DOREPLIFETIME(UFPSAbsoluteZeroComponent,NetSigilColorSeed);
}

void UFPSAbsoluteZeroComponent::BeginPlay()
{
    Super::BeginPlay();
    AddTickPrerequisiteActor(GetOwner());
    const TCHAR* const* Paths=AFPSAbsoluteZeroNova::AssetPaths();
    TArray<FSoftObjectPath> Requests;
    for(int32 I=0;I<AFPSAbsoluteZeroNova::AssetCount;++I)Requests.Emplace(Paths[I]);
    PlayerSkillAssets::Defer(GetOwner(),TEXT("absoluteZero"),FSimpleDelegate::CreateWeakLambda(this,[this,Requests]()
    {
        Assets.Reset();
        for(const auto& Path:Requests)Assets.Add(Path.ResolveObject());
        bAssetsReady=AFPSAbsoluteZeroNova::HasBasicAssets(Assets);
    }),Requests);
}

UColdSteelStatusModel* UFPSAbsoluteZeroComponent::Model() const { return NetCast::LocalModel(*this); }
UFPSFireballComponent* UFPSAbsoluteZeroComponent::Hands() const { return GetOwner()->FindComponentByClass<UFPSFireballComponent>(); }

bool UFPSAbsoluteZeroComponent::InputAvailable(bool bContinuing) const
{
    const auto* P=Cast<AFPSGAMECharacter>(GetOwner());
    const auto* PC=P?Cast<APlayerController>(P->GetController()):nullptr;
    if(!PC||P->IsChoosingAmmo()||(bContinuing?AFPSGAMEPlayerController::BlocksActionContinuation(PC):
        (PC->bShowMouseCursor||AFPSGAMEPlayerController::BlocksOngoingActions(PC))))return false;
    const auto* Builder=PC->FindComponentByClass<UVoxelBuildComponent>();
    return !Builder||!Builder->IsBuilding();
}

void UFPSAbsoluteZeroComponent::Feedback(const FString& Text)
{
    Message=Text;
    if(GetWorld())MessageUntil=GetWorld()->GetTimeSeconds()+1.6;
}

bool UFPSAbsoluteZeroComponent::IsHandOccupiedNotice() const
{
    const auto* P=Cast<AFPSGAMECharacter>(GetOwner());
    return P&&P->IsSpellHandHeld()&&GetWorld()&&HandNotice.Active(GetWorld()->GetTimeSeconds());
}
float UFPSAbsoluteZeroComponent::HandNoticeAlpha() const { return GetWorld()?HandNotice.Alpha(GetWorld()->GetTimeSeconds()):0.f; }
float UFPSAbsoluteZeroComponent::HandNoticeRise() const { return GetWorld()?HandNotice.Rise(GetWorld()->GetTimeSeconds()):0.f; }

float UFPSAbsoluteZeroComponent::ChannelDamageTakenMultiplier() const
{
    if(!bChanneling&&!bNetChanneling)return 1.f;
    const float Reduction=bChanneling?ActiveDamageReduction:NetChannelReduction;
    return FMath::Clamp(1.f-Reduction,.15f,1.f);
}

float UFPSAbsoluteZeroComponent::ChannelAlpha() const
{
    if(!bChanneling&&!bNetChanneling)return 0.f;
    const float Dur=FMath::Max(.15f,bChanneling?ChannelDuration:NetChannelDuration);
    return FMath::Clamp(ChannelAge/Dur,0.f,1.f);
}

bool UFPSAbsoluteZeroComponent::IsPresentingStaffSlam() const
{
    return bChanneling||(SlamRecoveryAge>=0.f&&SlamRecoveryAge<StaffCastMotion::AbsoluteZeroSlamRecoverSeconds);
}

FStaffCastPose UFPSAbsoluteZeroComponent::SampleStaffSlamPose(const FStaffCastPose& Current) const
{
    if(bChanneling)
        return StaffCastMotion::AbsoluteZeroChannel(StaffSlamEntry,ChannelAlpha(),ChannelAge);
    if(SlamRecoveryAge>=0.f&&SlamRecoveryAge<StaffCastMotion::AbsoluteZeroSlamRecoverSeconds)
        return StaffCastMotion::AbsoluteZeroRecover(Current,SlamRecoveryAge);
    return Current;
}

void UFPSAbsoluteZeroComponent::GetCameraMotion(FVector& OutLocation,FRotator& OutRotation,float* OutFov) const
{
    StaffCastMotion::AbsoluteZeroCamera(bChanneling,ChannelAlpha(),SlamRecoveryAge,OutLocation,OutRotation,OutFov);
}

float UFPSAbsoluteZeroComponent::CooldownFraction() const
{
    const auto* M=Model();
    return M&&!bCommitted?FMath::Clamp(M->AbsoluteZeroCooldown()/FMath::Max(.1f,M->AbsoluteZeroCooldownDuration()),0.f,1.f):0.f;
}

FString UFPSAbsoluteZeroComponent::StatusText() const
{
    if(IsHandOccupiedNotice())return TEXT("左手占用");
    if(GetWorld()&&GetWorld()->GetTimeSeconds()<MessageUntil)return Message;
    if(bChanneling)return CastSnapshot.bIceArmorSynergy?TEXT("冰甲蓄寒"):TEXT("蓄寒");
    if(bQueued)return TEXT("等待施法");
    if(const auto* M=Model();M&&M->AbsoluteZeroCooldown()>0.f)return FString::Printf(TEXT("%.1f"),M->AbsoluteZeroCooldown());
    return TEXT("");
}

bool UFPSAbsoluteZeroComponent::Allowed(const FAbsoluteZeroCast& Spell,FString& Failure) const
{
    const auto* M=Model();if(!M)return false;
    if(Spell.bRequiresStaff&&!M->HasEquippedStaff()){Failure=TEXT("需要法杖");return false;}
    if(M->AbsoluteZeroCooldown()>0.f){Failure=TEXT("冷却");return false;}
    if(!M->CanSpendMana(Spell.ManaCost)){Failure=TEXT("缺蓝");return false;}
    if(!bAssetsReady){Failure=TEXT("寒冰素材加载中");return false;}
    if(GetWorld()->GetNetMode()==NM_Client&&!NetCast::StateFor(Cast<APawn>(GetOwner())))
    {Failure=TEXT("等待联机角色就绪");return false;}
    return true;
}

void UFPSAbsoluteZeroComponent::Trigger()
{
    if(bChanneling||bCommitted||bNetAwaitingRelease||bNetAwaitingCancel)return;
    if(UBoundCongregateCaptureComponent::IsCaptured(GetOwner())||UPlayerKnockdownComponent::IsKnockedDown(GetOwner()))return;
    auto* P=Cast<AFPSGAMECharacter>(GetOwner());auto* M=Model();
    if(!P||!M||!P->IsLocallyControlled()||!InputAvailable())return;
    if(const auto* Health=P->FindComponentByClass<UFPSCombatHealthComponent>();Health&&Health->IsDead())return;
    if(M->AbsoluteZeroDefinition().AbsoluteZero.bRequiresStaff&&!M->HasEquippedStaff())
    {Feedback(TEXT("需要法杖"));return;}
    if(const auto* H=Hands();H&&H->HasOtherPreparedSpell(this))
    {bQueued=false;Feedback(TEXT("先释放已积蓄魔法"));return;}
    if(P->IsSpellHandHeld()){bQueued=false;HandNotice.Show(GetWorld()->GetTimeSeconds());return;}
    FString Failure;
    if(!Allowed(M->AbsoluteZeroStats(),Failure)){Feedback(Failure);return;}
    if(auto* Sword=P->FindComponentByClass<URuneSwordComponent>();Sword&&Sword->IsGuarding())Sword->ReleaseGuard();
    bQueued=true;MessageUntil=0.;
    UpdateTickState();
    ServiceQueue();
}

void UFPSAbsoluteZeroComponent::ServiceQueue()
{
    if(!bQueued||bCommitted||bNetAwaitingRelease||bNetAwaitingCancel)return;
    auto* P=Cast<AFPSGAMECharacter>(GetOwner());auto* M=Model();auto* H=Hands();
    if(!P||!M||!H)return;
    if(M->AbsoluteZeroDefinition().AbsoluteZero.bRequiresStaff&&!M->HasEquippedStaff())
    {bQueued=false;Feedback(TEXT("需要法杖"));return;}
    if(H->HasOtherPreparedSpell(this)){bQueued=false;Feedback(TEXT("先释放已积蓄魔法"));return;}
    if(!InputAvailable()){bQueued=false;return;}
    if(P->IsSpellHandHeld()){bQueued=false;HandNotice.Show(GetWorld()->GetTimeSeconds());return;}
    if(H->BlocksNewLeftHandAction()||P->IsSpellHandBusy())return;

    const FAbsoluteZeroCast Spell=M->AbsoluteZeroStats();
    FString Failure;
    if(!Allowed(Spell,Failure)){bQueued=false;Feedback(Failure);return;}
    if(const auto* Staff=P->FindComponentByClass<UStaffWeaponComponent>())
        StaffSlamEntry=Staff->CarryPoseInCamera();
    if(!H->TryBeginSpellGesture(this,false,Spell.CastSpeed,FSimpleDelegate::CreateUObject(this,&ThisClass::OnGestureContact)))return;
    bQueued=false;
    const float Before=M->Snapshot().Mana;
    if(!M->BeginAbsoluteZeroCast(Spell)){H->CancelSpellGesture(this);return;}

    CastSnapshot=Spell;
    bCommitted=true;
    bChanneling=true;
    SlamRecoveryAge=-1.f;
    PaidMana=FMath::Max(0.f,Before-M->Snapshot().Mana);
    ChannelAge=0.f;
    SigilColorSeed=FMath::FRandRange(0.f,97.f);
    const float BaseDur=Spell.bIceArmorSynergy?Spell.ArmorChannelSeconds:Spell.ChannelSeconds;
    ChannelDuration=FMath::Clamp(BaseDur/FMath::Max(.25f,Spell.CastSpeed),.2f,3.5f);
    ActiveDamageReduction=Spell.bIceArmorSynergy?Spell.ArmorChannelDamageReduction:Spell.ChannelDamageReduction;
    P->StopMovementForMeleeSkill();
    if(auto* Status=P->FindComponentByClass<UCombatStatusFormula>())Status->ConsumeChainSpell();
    if(GetOwner()->HasAuthority())
    {
        bNetChanneling=true;NetChannelDuration=ChannelDuration;
        NetChannelReduction=ActiveDamageReduction;bNetArmorSynergy=Spell.bIceArmorSynergy;
        NetSigilColorSeed=SigilColorSeed;
        GetOwner()->ForceNetUpdate();
    }
    StartChannelVisuals();
    if(GetWorld()->GetNetMode()==NM_Client)
    {
        bNetPaid=true;bNetPrepared=false;
        NetWaitSince=GetWorld()->GetTimeSeconds();
        NetCast::Send(P,TEXT("absoluteZero"),0);
    }
    UpdateTickState();
}

void UFPSAbsoluteZeroComponent::OnGestureContact()
{
    // Hold staff cast pose until grounding channel completes.
    if(bChanneling)
        if(auto* H=Hands())H->ContinueSpellRelease(this,FMath::Max(.08f,ChannelDuration-ChannelAge+.1f),false);
}

FVector UFPSAbsoluteZeroComponent::GroundPointBeneathCaster() const
{
    const AActor* Owner=GetOwner();
    if(!Owner)return FVector::ZeroVector;
    FVector Foot=Owner->GetActorLocation();
    if(const auto* Capsule=Owner->FindComponentByClass<UCapsuleComponent>())
        Foot.Z-=Capsule->GetScaledCapsuleHalfHeight();
    FHitResult Floor;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(AbsoluteZeroFloor),false,Owner);
    if(GetWorld()&&GetWorld()->LineTraceSingleByChannel(Floor,Owner->GetActorLocation()+FVector(0,0,40),Foot-FVector(0,0,220),ECC_Visibility,Query))
        return Floor.ImpactPoint;
    return Foot;
}

void UFPSAbsoluteZeroComponent::ReleaseNova()
{
    if(!bCommitted||!bChanneling||bNetAwaitingRelease)return;
    auto* P=Cast<APawn>(GetOwner());auto* M=Model();
    if(!P||!M||(CastSnapshot.bRequiresStaff&&!M->HasEquippedStaff()))
    {CancelPending();Feedback(TEXT("需要法杖"));return;}
    const FVector Ground=GroundPointBeneathCaster();

    if(GetWorld()->GetNetMode()==NM_Client)
    {
        bChanneling=false;
        bNetAwaitingRelease=true;
        NetWaitSince=GetWorld()->GetTimeSeconds();
        ClearChannelVisuals();
        UpdateTickState();
        NetCast::Send(P,TEXT("absoluteZero"),1,Ground,FVector::UpVector);
        return;
    }

    FActorSpawnParameters Params;
    Params.Owner=P;Params.Instigator=P;
    Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    auto* Nova=GetWorld()->SpawnActor<AFPSAbsoluteZeroNova>(Ground,FRotator::ZeroRotator,Params);
    if(!Nova||!Nova->InitializeNova(P,CastSnapshot,Ground,Assets)||!M->CommitAbsoluteZeroRelease())
    {
        if(Nova)Nova->Destroy();
        CancelPending();Feedback(TEXT("绝对零度释放失败"));return;
    }
    ActiveNovas.RemoveAll([](const auto& N){return !N.IsValid();});
    ActiveNovas.Add(Nova);
    Nova->ActivateNova();
    CompleteRelease();
}

void UFPSAbsoluteZeroComponent::CompleteRelease()
{
    bCommitted=bChanneling=bNetPaid=bNetPrepared=bNetAwaitingRelease=false;
    PaidMana=0.f;ChannelAge=0.f;ActiveDamageReduction=0.f;
    SlamRecoveryAge=0.f; // Hold ground-slam thud briefly then recover smoothly back to carry pose.
    if(auto* H=Hands())H->CancelSpellGesture(this);
    if(GetOwner()->HasAuthority()){bNetChanneling=false;NetChannelReduction=0.f;GetOwner()->ForceNetUpdate();}
    ClearChannelVisuals();
    UpdateTickState();
    if(auto* P=Cast<APawn>(GetOwner()))
        if(auto* Status=UCombatStatusFormula::GetOrAdd(P))
        {
            if(CastSnapshot.bGrantChain)Status->AddChainSpell();
            if(CastSnapshot.CastHasteStacks>0)Status->AddHaste(CastSnapshot.CastHasteStacks,CastSnapshot.CastHasteDuration);
        }
}

void UFPSAbsoluteZeroComponent::CancelPending()
{
    bQueued=bChanneling=false;
    ChannelAge=0.f;ActiveDamageReduction=0.f;SlamRecoveryAge=-1.f;
    ClearChannelVisuals();
    if(auto* H=Hands())H->CancelSpellGesture(this);
    if(GetOwner()&&GetOwner()->HasAuthority()&&bNetChanneling)
    {bNetChanneling=false;NetChannelReduction=0.f;GetOwner()->ForceNetUpdate();}
    if(bNetAwaitingRelease)return;
    if(bCommitted)
    {
        bCommitted=false;
        if(auto* M=Model())M->RefundUnreleasedCast(PaidMana,TEXT("absoluteZero"));
        if(GetWorld()&&GetWorld()->GetNetMode()==NM_Client&&bNetPaid)
        {bNetAwaitingCancel=true;NetWaitSince=GetWorld()->GetTimeSeconds();NetCast::Send(GetOwner(),TEXT("absoluteZero"),2);}
    }
    bNetPaid=bNetPrepared=false;
    PaidMana=0.f;
    UpdateTickState();
}

void UFPSAbsoluteZeroComponent::InterruptPending(bool bCancelChannel)
{
    if(bCancelChannel||bChanneling||bCommitted)CancelPending();
    else bQueued=false;
}

void UFPSAbsoluteZeroComponent::FinishNovasForRemoval()
{
    CancelPending();
    for(const auto& WeakNova:ActiveNovas)
        if(auto* Nova=WeakNova.Get())Nova->FinishForRemoval();
    ActiveNovas.Reset();
}

bool UFPSAbsoluteZeroComponent::NetBeginChannel(APawn* Caster,const FAbsoluteZeroCast& Spell)
{
    if(Caster!=GetOwner()||!Caster->HasAuthority())return false;
    CastSnapshot=Spell;
    ChannelAge=0.f;
    bNetChanneling=true;
    NetChannelDuration=FMath::Clamp((Spell.bIceArmorSynergy?Spell.ArmorChannelSeconds:Spell.ChannelSeconds)/FMath::Max(.25f,Spell.CastSpeed),.2f,3.5f);
    NetChannelReduction=Spell.bIceArmorSynergy?Spell.ArmorChannelDamageReduction:Spell.ChannelDamageReduction;
    bNetArmorSynergy=Spell.bIceArmorSynergy;
    NetSigilColorSeed=FMath::FRandRange(0.f,97.f);
    Caster->ForceNetUpdate();
    // Listen Server does not auto-fire OnRep_Channel locally — drive guest channel visuals directly for host observer.
    if(GetNetMode()!=NM_DedicatedServer&&!Caster->IsLocallyControlled())StartChannelVisuals();
    UpdateTickState();
    return true;
}

void UFPSAbsoluteZeroComponent::NetCancelChannel()
{
    if(!GetOwner()||!GetOwner()->HasAuthority())return;
    bNetChanneling=false;NetChannelReduction=0.f;
    GetOwner()->ForceNetUpdate();
    if(GetNetMode()!=NM_DedicatedServer)ClearChannelVisuals();
    UpdateTickState();
}

bool UFPSAbsoluteZeroComponent::NetCommitNova(APawn* Caster,const FColdSteelNetCastRequest& Req,UColdSteelStatusModel* Shadow,const FAbsoluteZeroCast& Spell)
{
    if(!Caster||Caster!=GetOwner()||!Caster->HasAuthority()||!Shadow||!bAssetsReady)return false;
    if(Spell.bRequiresStaff&&!Shadow->HasEquippedStaff())return false;
    bNetChanneling=false;NetChannelReduction=0.f;Caster->ForceNetUpdate();
    if(GetNetMode()!=NM_DedicatedServer)ClearChannelVisuals();
    UpdateTickState();
    const FVector Ground=GroundPointBeneathCaster();
    FActorSpawnParameters Params;
    Params.Owner=Caster;Params.Instigator=Caster;
    Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    auto* Nova=GetWorld()->SpawnActor<AFPSAbsoluteZeroNova>(Ground,FRotator::ZeroRotator,Params);
    if(!Nova||!Nova->InitializeNova(Caster,Spell,Ground,Assets)||!Shadow->CommitAbsoluteZeroRelease())
    {if(Nova)Nova->Destroy();return false;}
    ActiveNovas.RemoveAll([](const auto& N){return !N.IsValid();});
    ActiveNovas.Add(Nova);
    Nova->ActivateNova();
    if(auto* Status=UCombatStatusFormula::GetOrAdd(Caster))
    {
        if(Spell.bGrantChain)Status->AddChainSpell();
        if(Spell.CastHasteStacks>0)Status->AddHaste(Spell.CastHasteStacks,Spell.CastHasteDuration);
    }
    return true;
}

void UFPSAbsoluteZeroComponent::NetCastAccepted(uint8 Phase)
{
    if(Phase==0){if(bNetPaid&&!bNetAwaitingCancel)bNetPrepared=true;return;}
    if(Phase!=1||!bNetAwaitingRelease)return;
    if(auto* M=Model();M&&M->Snapshot().bAbsoluteZeroReserved)M->CommitAbsoluteZeroRelease();
    CompleteRelease();
}

void UFPSAbsoluteZeroComponent::NetCastRejected(uint8 Phase,uint8 /*Code*/)
{
    if(bNetAwaitingCancel&&Phase<2)return;
    if(!bNetPaid&&!bNetAwaitingRelease&&!bNetAwaitingCancel)return;
    bNetPaid=bNetAwaitingRelease=bNetAwaitingCancel=false;
    CancelPending();Feedback(TEXT("施法失败，已退还消耗"));
}

void UFPSAbsoluteZeroComponent::NetCastCancelled(uint8 /*Phase*/)
{
    bNetAwaitingCancel=false;
    UpdateTickState();
}

void UFPSAbsoluteZeroComponent::OnRep_Channel()
{
    const auto* P=Cast<APawn>(GetOwner());
    if(P&&P->IsLocallyControlled())return;
    if(bNetChanneling){ChannelAge=0.f;StartChannelVisuals();}
    else ClearChannelVisuals();
    UpdateTickState();
}

void UFPSAbsoluteZeroComponent::StartChannelVisuals()
{
    if(GetNetMode()==NM_DedicatedServer||!bAssetsReady)return;
    ClearChannelVisuals();
    const FVector Ground=GroundPointBeneathCaster();
    CachedChannelGround=Ground;
    CachedChannelOwnerPos=GetOwner()?GetOwner()->GetActorLocation():Ground;
    bHasCachedGround=true;
    const bool bSynergy=bChanneling?CastSnapshot.bIceArmorSynergy:bNetArmorSynergy;
    const float ColorSeed=bChanneling?SigilColorSeed:NetSigilColorSeed;
    if(auto* SigilMat=Cast<UMaterialInterface>(Assets[1]))
    {
        // Enlarged 5.2 m high-tessellation (64x9) terrain-conforming arcane ring with clean unobstructed center.
        ChannelSigil=FrostSurfaceMesh::BuildConformingDisc(GetOwner(),GetOwner()->GetRootComponent(),Cast<APawn>(GetOwner()),
            Ground,FVector::ForwardVector,520.f,520.f,SigilMat,ChannelMID,64,9,true,3.6f);
        if(ChannelMID)
        {
            ChannelMID->SetScalarParameterValue(TEXT("Progress"),0.f);
            ChannelMID->SetScalarParameterValue(TEXT("Fade"),.95f);
            ChannelMID->SetScalarParameterValue(TEXT("Synergy"),bSynergy?1.f:0.f);
            ChannelMID->SetScalarParameterValue(TEXT("ColorSeed"),ColorSeed);
        }
    }
    if(auto* MistSys=Cast<UNiagaraSystem>(Assets[5]))
    {
        ChannelMist=UNiagaraFunctionLibrary::SpawnSystemAtLocation(GetWorld(),MistSys,Ground,FRotator::ZeroRotator,FVector(1.f),false,false);
        if(ChannelMist)
        {
            ChannelMist->SetVariablePosition(TEXT("User.Center"),Ground);
            ChannelMist->SetVariableFloat(TEXT("User.Progress"),0.f);
            ChannelMist->SetVariableFloat(TEXT("User.Strength"),1.f);
            ChannelMist->SetVariableFloat(TEXT("User.Radius"),520.f);
            ChannelMist->SetVariableFloat(TEXT("User.Synergy"),bSynergy?1.f:0.f);
            ChannelMist->Activate(true);
        }
    }
    ChannelLight=NewObject<UPointLightComponent>(GetOwner());
    GetOwner()->AddInstanceComponent(ChannelLight);
    ChannelLight->SetWorldLocation(Ground+FVector(0,0,90));
    ChannelLight->SetLightColor(bSynergy?FLinearColor(.42f,.88f,1.f):FLinearColor(.30f,.78f,1.f));
    ChannelLight->SetIntensity(3500.f);
    ChannelLight->SetAttenuationRadius(480.f);
    ChannelLight->SetCastShadows(false);
    ChannelLight->RegisterComponent();
    if(auto* CastSfx=Cast<USoundBase>(Assets[9]))
        UGameplayStatics::PlaySoundAtLocation(this,CastSfx,Ground,.88f,bSynergy?.92f:.82f);
}

void UFPSAbsoluteZeroComponent::UpdateChannelVisuals(float Delta)
{
    if(GetNetMode()==NM_DedicatedServer)return;
    const float Alpha=ChannelAlpha();
    const bool bSynergy=bChanneling?CastSnapshot.bIceArmorSynergy:bNetArmorSynergy;
    const FVector OwnerPos=GetOwner()?GetOwner()->GetActorLocation():CachedChannelOwnerPos;
    if(!bHasCachedGround||FVector::DistSquared(OwnerPos,CachedChannelOwnerPos)>25.f)
    {
        CachedChannelGround=GroundPointBeneathCaster();
        CachedChannelOwnerPos=OwnerPos;
        bHasCachedGround=true;
    }
    const FVector& Ground=CachedChannelGround;
    if(ChannelMID)
    {
        ChannelMID->SetScalarParameterValue(TEXT("Progress"),Alpha);
        ChannelMID->SetScalarParameterValue(TEXT("Fade"),FMath::Lerp(.65f,1.f,Alpha));
        ChannelMID->SetScalarParameterValue(TEXT("Synergy"),bSynergy?1.f:0.f);
    }
    if(ChannelMist)
    {
        ChannelMist->SetWorldLocation(Ground);
        ChannelMist->SetVariablePosition(TEXT("User.Center"),Ground);
        ChannelMist->SetVariableFloat(TEXT("User.Progress"),Alpha);
        ChannelMist->SetVariableFloat(TEXT("User.Strength"),1.f);
        ChannelMist->SetVariableFloat(TEXT("User.Synergy"),bSynergy?1.f:0.f);
    }
    if(ChannelLight)
    {
        // Match the ground light subtly to the shifting Blue/Violet/Cyan sigil palette.
        const float Seed=bChanneling?SigilColorSeed:NetSigilColorSeed;
        const float T=float(GetWorld()->GetTimeSeconds())*1.15f+Seed*1.73f;
        const float Seg=FMath::FloorToFloat(T);
        const float Frac=FMath::SmoothStep(.08f,.92f,T-Seg);
        auto PickCol=[Seed](float S)->FLinearColor
        {
            const float H=FMath::Frac(FMath::Sin(S*127.1f+Seed*311.7f)*43758.5453f);
            const int32 Idx=FMath::Clamp(int32(H*3.f),0,2);
            return Idx==0?FLinearColor(.16f,.56f,1.f):(Idx==1?FLinearColor(.66f,.24f,1.f):FLinearColor(.08f,.95f,1.f));
        };
        const FLinearColor LightTint=FMath::Lerp(PickCol(Seg),PickCol(Seg+1.f),Frac);
        ChannelLight->SetWorldLocation(Ground+FVector(0,0,90));
        ChannelLight->SetLightColor(LightTint);
        ChannelLight->SetIntensity(FMath::Lerp(3200.f,bSynergy?16000.f:12500.f,Alpha*Alpha));
    }
    (void)Delta;
}

void UFPSAbsoluteZeroComponent::ClearChannelVisuals()
{
    bHasCachedGround=false;
    if(ChannelSigil){ChannelSigil->DestroyComponent();ChannelSigil=nullptr;ChannelMID=nullptr;}
    if(ChannelMist){ChannelMist->DestroyComponent();ChannelMist=nullptr;}
    if(ChannelLight){ChannelLight->DestroyComponent();ChannelLight=nullptr;}
}

void UFPSAbsoluteZeroComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick)
{
    Super::TickComponent(Delta,Type,Tick);
    const auto* Health=GetOwner()->FindComponentByClass<UFPSCombatHealthComponent>();
    if(Health&&Health->IsDead()){CancelPending();return;}

    if(SlamRecoveryAge>=0.f)
    {
        SlamRecoveryAge+=Delta;
        if(SlamRecoveryAge>=StaffCastMotion::AbsoluteZeroSlamRecoverSeconds||
           (Model()&&!Model()->HasEquippedStaff()))
            SlamRecoveryAge=-1.f;
    }

    // Multiplayer client RPC timeout safety: never lock the player permanently in channeling or awaiting state.
    if(GetWorld()&&GetWorld()->GetNetMode()==NM_Client)
    {
        const double Now=GetWorld()->GetTimeSeconds();
        if(bNetAwaitingRelease&&Now-NetWaitSince>3.5)
        {
            bNetAwaitingRelease=false;bNetPaid=false;
            CancelPending();Feedback(TEXT("施法超时"));
            return;
        }
        if(bNetAwaitingCancel&&Now-NetWaitSince>3.5)
        {
            bNetAwaitingCancel=false;
        }
    }

    if(bQueued)ServiceQueue();
    if(bChanneling)
    {
        const auto* Status=GetOwner()->FindComponentByClass<UCombatStatusFormula>();
        if(UBoundCongregateCaptureComponent::IsCaptured(GetOwner())||UPlayerKnockdownComponent::IsKnockedDown(GetOwner())||
           (Status&&Status->BlocksMovement()))
        {CancelPending();Feedback(TEXT("施法被打断"));return;}
        if(const auto* M=Model();M&&CastSnapshot.bRequiresStaff&&!M->HasEquippedStaff())
        {CancelPending();Feedback(TEXT("需要法杖"));return;}

        ChannelAge+=Delta;
        if(auto* H=Hands())H->ContinueSpellRelease(this,.25f,false);
        UpdateChannelVisuals(Delta);
        const bool bNetReady=GetWorld()->GetNetMode()!=NM_Client||bNetPrepared;
        if(ChannelAge>=ChannelDuration)
        {
            if(bNetReady)ReleaseNova();
            else if(GetWorld()->GetTimeSeconds()-NetWaitSince>3.5)
            {
                bNetPaid=false;CancelPending();Feedback(TEXT("施法超时"));
                return;
            }
        }
    }
    else if(bNetChanneling)
    {
        ChannelAge+=Delta;
        UpdateChannelVisuals(Delta);
    }
    UpdateTickState();
}

void UFPSAbsoluteZeroComponent::EndPlay(EEndPlayReason::Type Reason)
{
    FinishNovasForRemoval();
    Super::EndPlay(Reason);
}
