#include "FPSElectricMagicComponent.h"
#include "../Monsters/BoundCongregateCaptureComponent.h"
#include "FPSFireballComponent.h"
#include "FPSLightningArc.h"
#include "LightningDamage.h"
#include "HolyLightTargets.h"
#include "IceWallLandingCameraShake.h"
#include "FPSIceWall.h"
#include "../FPSGAMECharacter.h"
#include "../FPSGAMEPlayerController.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Weapons/RuneSwordComponent.h"
#include "../Dungeons/WardBreakableGlass.h"
#include "Camera/CameraComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Engine/OverlapResult.h"
#include "Kismet/GameplayStatics.h"
#include "HAL/IConsoleManager.h"
#include "NiagaraComponent.h"
#include "NiagaraSystem.h"
#include "NiagaraFunctionLibrary.h"
#include "Sound/SoundBase.h"
#include "Net/UnrealNetwork.h"
#include "NetCastUtils.h"

UFPSElectricMagicComponent::UFPSElectricMagicComponent()
{
    PrimaryComponentTick.bCanEverTick=true;PrimaryComponentTick.TickGroup=TG_PostUpdateWork;
    SetIsReplicatedByDefault(true); // 雷云激活态复制
}
void UFPSElectricMagicComponent::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(UFPSElectricMagicComponent,bNetDomain);
    DOREPLIFETIME(UFPSElectricMagicComponent,NetDomainCast);
}
void UFPSElectricMagicComponent::BeginPlay()
{
    Super::BeginPlay();AddTickPrerequisiteActor(GetOwner());
    if(auto* H=Hands())AddTickPrerequisiteComponent(H);
    const TCHAR* Paths[]={TEXT("/Game/Skills/ElectricMagic/NS_StormDomainCloud.NS_StormDomainCloud"),TEXT("/Game/Skills/Lightning/NS_LightningChain.NS_LightningChain"),
        TEXT("/Game/Skills/ElectricMagic/LanceRay/Materials/M_ThunderLanceBeam.M_ThunderLanceBeam"),TEXT("/Game/Skills/ElectricMagic/NS_ThunderCharge.NS_ThunderCharge"),
        TEXT("/Game/Skills/ElectricMagic/NS_ElectricImpact.NS_ElectricImpact"),TEXT("/Game/Skills/ElectricMagic/S_ElectricCast1.S_ElectricCast1"),TEXT("/Game/Skills/ElectricMagic/S_ElectricCast2.S_ElectricCast2"),
        TEXT("/Game/Skills/ElectricMagic/ThunderLanceV2/M_ThunderLanceCircle.M_ThunderLanceCircle"),TEXT("/Engine/BasicShapes/Plane.Plane"),
        TEXT("/Game/Skills/ElectricMagic/LanceRay/FX/SM_ThunderLanceRibbon.SM_ThunderLanceRibbon"),TEXT("/Game/Skills/ElectricMagic/LanceRay/FX/SM_ThunderLanceIris.SM_ThunderLanceIris"),
        TEXT("/Game/Skills/ElectricMagic/LanceRay/Materials/M_ThunderLanceIris.M_ThunderLanceIris"),TEXT("/Game/Skills/ElectricMagic/LanceRay/NS_ThunderLanceGather.NS_ThunderLanceGather"),
        TEXT("/Game/Skills/ElectricMagic/S_ThunderLanceCharge.S_ThunderLanceCharge"),TEXT("/Game/Skills/ElectricMagic/S_ThunderLanceDischarge.S_ThunderLanceDischarge"),
        TEXT("/Game/Skills/ElectricMagic/NS_ThunderLanceMuzzle.NS_ThunderLanceMuzzle")};
    TArray<FSoftObjectPath> Requests;for(const auto* Path:Paths)Requests.Emplace(Path);
    AssetLoad=UAssetManager::GetStreamableManager().RequestAsyncLoad(Requests,FStreamableDelegate::CreateWeakLambda(this,[this,Requests]()
    {bAssetsReady=true;for(const auto& Path:Requests){auto* A=Path.ResolveObject();bAssetsReady&=A!=nullptr;Assets.Add(A);}}));
}
UColdSteelStatusModel* UFPSElectricMagicComponent::Model() const
{return GetWorld()&&GetWorld()->GetGameInstance()?GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr;}
UFPSFireballComponent* UFPSElectricMagicComponent::Hands() const{return GetOwner()->FindComponentByClass<UFPSFireballComponent>();}
bool UFPSElectricMagicComponent::Enemy(AActor* Actor) const
{const auto* C=IsValid(Actor)?Actor->FindComponentByClass<UMonsterCombatComponent>():nullptr;return Actor!=GetOwner()&&C&&!C->IsDead()&&!HolyLightTargets::IsFriendly(Actor);}
TArray<AActor*> UFPSElectricMagicComponent::Nearby(const FVector& Center,float Radius) const
{
    TArray<FOverlapResult> Hits;TArray<AActor*> Result;
    FCollisionObjectQueryParams Objects;Objects.AddObjectTypesToQuery(ECC_Pawn);Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
    FCollisionQueryParams Q(SCENE_QUERY_STAT(ElectricCandidates),false,GetOwner());
    GetWorld()->OverlapMultiByObjectType(Hits,Center,FQuat::Identity,Objects,FCollisionShape::MakeSphere(Radius),Q);
    for(const auto& H:Hits)if(Enemy(H.GetActor()))Result.AddUnique(H.GetActor());return Result;
}
bool UFPSElectricMagicComponent::Visible(AActor* Origin,AActor* Target,const FVector& Start) const
{
    FCollisionQueryParams Q(SCENE_QUERY_STAT(ElectricSight),false,Origin);Q.AddIgnoredActor(GetOwner());Q.AddIgnoredActor(Target);
    FHitResult H;return !GetWorld()->LineTraceSingleByChannel(H,Start,UWardBreakableGlass::TargetPoint(Target),ECC_Visibility,Q);
}
FVector UFPSElectricMagicComponent::CastOrigin() const
{
    const auto* Camera=GetOwner()->FindComponentByClass<UCameraComponent>();
    FVector P=Camera?Camera->GetComponentLocation()+Camera->GetForwardVector()*45-Camera->GetRightVector()*22-Camera->GetUpVector()*20:GetOwner()->GetActorLocation();
    if(Hands()&&Hands()->TryStaffCastOrigin(P))return P;
    TArray<USkeletalMeshComponent*> Meshes;GetOwner()->GetComponents(Meshes);
    for(const auto* Mesh:Meshes)if(Mesh&&Mesh->IsVisible()&&Mesh->DoesSocketExist(TEXT("hand_l")))return Mesh->GetSocketLocation(TEXT("hand_l"));return P;
}
FVector2D UFPSElectricMagicComponent::LanceCrosshairExtent(FVector2D LocalSize) const
{
    const auto* Pawn=Cast<APawn>(GetOwner());const auto* PC=Pawn?Cast<APlayerController>(Pawn->GetController()):nullptr;
    const auto* Camera=GetOwner()->FindComponentByClass<UCameraComponent>();
    if(!PC||!Camera)return FVector2D::ZeroVector;
    int32 Width=0,Height=0;PC->GetViewportSize(Width,Height);if(Width<=0||Height<=0)return FVector2D::ZeroVector;
    const FVector Center=Camera->GetComponentLocation()+Camera->GetForwardVector()*1000.f;
    const float Spread=LanceSpreadTangent()*1000.f;FVector2D C,R,U;
    if(!PC->ProjectWorldLocationToScreen(Center,C,true)||!PC->ProjectWorldLocationToScreen(Center+Camera->GetRightVector()*Spread,R,true)
        ||!PC->ProjectWorldLocationToScreen(Center+Camera->GetUpVector()*Spread,U,true))return FVector2D::ZeroVector;
    return FVector2D(FMath::Abs(R.X-C.X)*LocalSize.X/Width,FMath::Abs(U.Y-C.Y)*LocalSize.Y/Height);
}
void UFPSElectricMagicComponent::UpdateChargeVisual()
{
    const auto* Camera=GetOwner()->FindComponentByClass<UCameraComponent>();if(!Camera)return;
    const FVector Origin=CastOrigin();const FVector Fwd=Camera->GetForwardVector();
    const FRotator Facing=FRotationMatrix::MakeFromZX(Fwd,Camera->GetRightVector()).Rotator();
    const float Charge=LanceChargeFraction();
    if(ChargeFX){ChargeFX->SetWorldLocationAndRotation(Origin,Facing);ChargeFX->SetVariableFloat(TEXT("User.Charge"),Charge);}
    if(ChargeCircle)ChargeCircle->SetWorldLocationAndRotation(Origin+Fwd*24.f,Facing);
    if(ChargeCircleMaterial)ChargeCircleMaterial->SetScalarParameterValue(TEXT("Charge"),Charge);
    // 悬钟式积蓄：内卷粒子塌缩 + 虹膜光斑 + 周围丝束随充能汇聚到发射点。
    if(GatherFX)
    {
        GatherFX->SetWorldLocationAndRotation(Origin,FRotationMatrix::MakeFromX(Fwd).Rotator());
        GatherFX->SetVariableFloat(TEXT("User.Charge"),Charge);
    }
    if(ChargeIris)
    {
        ChargeIris->SetWorldTransform(FTransform(FRotationMatrix::MakeFromZ(-Fwd).ToQuat(),Origin+Fwd*4.f,FVector(FVector::OneVector*(9.f+16.f*Charge))));
        if(ChargeIrisMID){ChargeIrisMID->SetScalarParameterValue(TEXT("Strength"),.25f+.75f*Charge);ChargeIrisMID->SetScalarParameterValue(TEXT("Clock"),ChargeAge);ChargeIrisMID->SetScalarParameterValue(TEXT("FirePower"),Charge);}
    }
    // Lightning feeds converge into the cast point: real chain-bolt arcs
    // strike inward every ~130 ms once charge is underway.
    const float Now=float(GetWorld()->GetTimeSeconds());
    if(Charge>=.05f&&Now>=NextChargeArc)
    {
        NextChargeArc=Now+.13f;
        const FVector Right=Camera->GetRightVector(),Up=Camera->GetUpVector();
        const float A=FMath::FRandRange(0.f,2.f*PI),R=FMath::FRandRange(45.f,80.f);
        const FVector From=Origin+(Right*FMath::Cos(A)+Up*FMath::Sin(A))*R+Fwd*FMath::FRandRange(-15.f,35.f);
        FLightningCast Tendril;Tendril.Duration=.10f;Tendril.Fade=.16f;Tendril.Segments=6;Tendril.Jitter=.18f;
        SpawnArc(From,Origin,Tendril,false,1.f,.55f,false,38.f);
    }
}
void UFPSElectricMagicComponent::DestroyChargeVisual()
{
    if(ChargeFX){ChargeFX->DestroyComponent();ChargeFX=nullptr;}
    if(GatherFX){GatherFX->DestroyComponent();GatherFX=nullptr;}
    if(ChargeIris){ChargeIris->DestroyComponent();ChargeIris=nullptr;}ChargeIrisMID=nullptr;
    if(ChargeCircle){ChargeCircle->DestroyComponent();ChargeCircle=nullptr;}ChargeCircleMaterial=nullptr;
}
void UFPSElectricMagicComponent::Feedback(FName Skill,const FString& Text){MessageSkill=Skill;Message=Text;MessageUntil=GetWorld()->GetTimeSeconds()+2;}
bool UFPSElectricMagicComponent::IsHandOccupiedNotice(FName Skill) const
{const auto* P=Cast<AFPSGAMECharacter>(GetOwner());return NoticeSkill==Skill&&P&&P->IsSpellHandHeld()&&HandNotice.Active(GetWorld()->GetTimeSeconds());}
float UFPSElectricMagicComponent::HandNoticeAlpha() const{return HandNotice.Alpha(GetWorld()->GetTimeSeconds());}
float UFPSElectricMagicComponent::HandNoticeRise() const{return HandNotice.Rise(GetWorld()->GetTimeSeconds());}
float UFPSElectricMagicComponent::CooldownFraction(FName Skill) const
{const auto* M=Model();return M?FMath::Clamp(M->ElectricMagicCooldown(Skill)/FMath::Max(.1f,M->ElectricMagicCooldownDuration(Skill)),0.f,1.f):0;}
FString UFPSElectricMagicComponent::StatusText(FName Skill) const
{
    if(IsHandOccupiedNotice(Skill))return TEXT("左手占用");
    if(MessageSkill==Skill&&GetWorld()->GetTimeSeconds()<MessageUntil)return Message;
    if(QueuedSkill==Skill)return TEXT("等待施法");
    if(CommittedSkill==Skill)return IsCharging()?(LanceChargeFraction()>=1.f?TEXT("已充能完毕"):FString::Printf(TEXT("充能 %d%%"),FMath::FloorToInt(LanceChargeFraction()*100.f))):TEXT("施法");
    if(Skill==TEXT("stormDomain")&&bDomainActive)return FString::Printf(TEXT("雷云 %.1f"),FMath::Max(0.f,DomainCast.Duration-DomainAge));
    const auto* M=Model();return M&&M->ElectricMagicCooldown(Skill)>0?FString::Printf(TEXT("%.1f"),M->ElectricMagicCooldown(Skill)):TEXT("");
}
void UFPSElectricMagicComponent::Trigger(FName Skill)
{
    if(UBoundCongregateCaptureComponent::IsCaptured(GetOwner()))return;
    auto* P=Cast<AFPSGAMECharacter>(GetOwner());auto* M=Model();
    if(!ElectricMagic::IsSkill(Skill)||!P||!M||!P->IsLocallyControlled())return;
    if(CommittedSkill==TEXT("thunderLance")&&Skill==CommittedSkill){ReleaseLance();return;}
    if(!CommittedSkill.IsNone())return;
    if(const auto* H=P->FindComponentByClass<UFPSCombatHealthComponent>();H&&H->IsDead())return;
    if(const auto* H=Hands();H&&H->HasOtherPreparedSpell(this))
    {QueuedSkill=NAME_None;Feedback(Skill,TEXT("先释放已积蓄魔法"));return;}
    if(P->IsSpellHandHeld()){NoticeSkill=Skill;HandNotice.Show(GetWorld()->GetTimeSeconds());return;}
    if(M->ElectricMagicCooldown(Skill)>0){Feedback(Skill,TEXT("冷却"));return;}
    if(!bAssetsReady){Feedback(Skill,TEXT("素材准备中"));return;}
    if(!M->CanSpendMana(M->ElectricMagicStats(Skill).Hit.ManaCost)){Feedback(Skill,TEXT("缺蓝"));return;}
    if(auto* Sword=P->FindComponentByClass<URuneSwordComponent>();Sword&&Sword->IsGuarding())Sword->ReleaseGuard();
    QueuedSkill=Skill;MessageUntil=0;ServiceQueue();
}
void UFPSElectricMagicComponent::ServiceQueue()
{
    if(QueuedSkill.IsNone())return;
    auto* P=Cast<AFPSGAMECharacter>(GetOwner());auto* M=Model();auto* H=Hands();if(!P||!M||!H)return;
    if(H->HasOtherPreparedSpell(this))
    {Feedback(QueuedSkill,TEXT("先释放已积蓄魔法"));QueuedSkill=NAME_None;return;}
    const auto* PC=Cast<APlayerController>(P->GetController());
    if(P->IsSpellHandHeld()){NoticeSkill=QueuedSkill;HandNotice.Show(GetWorld()->GetTimeSeconds());QueuedSkill=NAME_None;return;}
    if(!PC||PC->bShowMouseCursor||PC->IsLookInputIgnored()||PC->IsMoveInputIgnored()||AFPSGAMEPlayerController::BlocksOngoingActions(PC)){QueuedSkill=NAME_None;return;}
    if(P->IsTraversing()||P->IsDodging()||P->IsSpellHandBusy()||H->BlocksNewLeftHandAction())return;
    const auto C=M->ElectricMagicStats(QueuedSkill);
    if(M->ElectricMagicCooldown(QueuedSkill)>0||!M->CanSpendMana(C.Hit.ManaCost)){Feedback(QueuedSkill,TEXT("未就绪"));QueuedSkill=NAME_None;return;}
    if(C.bRequiresStaff&&!M->HasEquippedStaff()){Feedback(QueuedSkill,TEXT("需要法杖"));QueuedSkill=NAME_None;return;}
    if(!H->TryBeginSpellGesture(this,true,C.Hit.CastSpeed,FSimpleDelegate::CreateUObject(this,&ThisClass::AtContact)))return;
    const float Before=M->Snapshot().Mana;
    if(!M->BeginElectricMagicCast(QueuedSkill,C)){H->CancelSpellGesture(this);QueuedSkill=NAME_None;return;}
    H->RecordGesturePayment(Before,M->Snapshot().Mana,true);
    CommittedSkill=QueuedSkill;QueuedSkill=NAME_None;PendingCast=C;bChargeAtContact=false;ChargeAge=0;
    if(auto* S=P->FindComponentByClass<UCombatStatusFormula>())S->ConsumeChainSpell();
    if(IsCharging())P->StopMovementForMeleeSkill();
    // 联机客人：凝聚扣账上报；雷云域/雷枪结算由服务端在释放相位执行。
    if(GetWorld()->GetNetMode()==NM_Client){bNetPaid=true;NetCast::Send(P,CommittedSkill,0);}
}
void UFPSElectricMagicComponent::GrantCastBuffs(const FLightningCast& C)
{if(auto* S=UCombatStatusFormula::GetOrAdd(GetOwner())){if(C.bGrantChain)S->AddChainSpell();if(C.CastHasteStacks>0)S->AddHaste(C.CastHasteStacks,C.CastHasteDuration);}}
void UFPSElectricMagicComponent::AtContact()
{
    if(CommittedSkill.IsNone())return;auto* M=Model();if(!M)return;
    if(IsCharging())
    {
        bChargeAtContact=true;ChargeAge=0;
        if(Hands())Hands()->ContinueSpellRelease(this,PendingCast.MaxCharge+.05f,false);
        ChargeFX=UNiagaraFunctionLibrary::SpawnSystemAtLocation(GetWorld(),Cast<UNiagaraSystem>(Assets[3]),CastOrigin(),FRotator::ZeroRotator,FVector(1),true,false);
        // 悬钟式积蓄粒子：内卷塌缩的电光粒子，复用 M09 凝视的 gather 配方。
        if(Assets.IsValidIndex(12)&&Assets[12])GatherFX=UNiagaraFunctionLibrary::SpawnSystemAtLocation(GetWorld(),Cast<UNiagaraSystem>(Assets[12]),CastOrigin(),FRotator::ZeroRotator,FVector(1.6f),true,false);
        if(Assets.IsValidIndex(11)&&Assets.IsValidIndex(10)&&Assets[11]&&Assets[10])
        {
            ChargeIris=NewObject<UStaticMeshComponent>(GetOwner());GetOwner()->AddInstanceComponent(ChargeIris);
            ChargeIris->SetupAttachment(GetOwner()->GetRootComponent());ChargeIris->SetAbsolute(true,true,true);
            ChargeIris->SetStaticMesh(Cast<UStaticMesh>(Assets[10]));ChargeIris->SetCollisionEnabled(ECollisionEnabled::NoCollision);
            ChargeIris->SetCanEverAffectNavigation(false);ChargeIris->SetCastShadow(false);ChargeIris->SetReceivesDecals(false);
            ChargeIrisMID=UMaterialInstanceDynamic::Create(Cast<UMaterialInterface>(Assets[11]),this);
            ChargeIris->SetMaterial(0,ChargeIrisMID);ChargeIris->RegisterComponent();
        }
        NextChargeArc=0;
        ChargeCircle=NewObject<UStaticMeshComponent>(GetOwner());
        GetOwner()->AddInstanceComponent(ChargeCircle);
        ChargeCircle->SetupAttachment(GetOwner()->FindComponentByClass<UCameraComponent>());
        ChargeCircle->SetStaticMesh(Cast<UStaticMesh>(Assets[8]));ChargeCircle->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        ChargeCircle->SetCanEverAffectNavigation(false);ChargeCircle->SetCastShadow(false);ChargeCircle->SetOnlyOwnerSee(true);
        ChargeCircle->SetReceivesDecals(false);ChargeCircle->SetWorldScale3D(FVector(.64f));
        ChargeCircleMaterial=UMaterialInstanceDynamic::Create(Cast<UMaterialInterface>(Assets[7]),this);
        ChargeCircle->SetMaterial(0,ChargeCircleMaterial);ChargeCircle->RegisterComponent();
        UpdateChargeVisual();if(ChargeFX)ChargeFX->Activate(true);
        UGameplayStatics::PlaySoundAtLocation(this,Cast<USoundBase>(Assets[6]),GetOwner()->GetActorLocation(),.55f);
        // Rising electrical crackle bed under the gather particles.
        if(Assets.IsValidIndex(13)&&Assets[13])UGameplayStatics::PlaySoundAtLocation(this,Cast<USoundBase>(Assets[13]),CastOrigin(),.9f);
        return;
    }
    if(!M->CommitElectricMagicRelease(CommittedSkill)){CancelPending();return;}
    const FName ActivatedSkill=CommittedSkill;
    FinishDomain(true);DomainCast=PendingCast;DomainRewards={};DomainAge=DomainVisualAge=NextStrike=0;bDomainActive=true;bDomainFading=false;
    SpawnDomainFX();
    UGameplayStatics::PlaySoundAtLocation(this,Cast<USoundBase>(Assets[5]),GetOwner()->GetActorLocation(),.6f);
    GrantCastBuffs(PendingCast.Hit);if(Hands())Hands()->TakeGesturePayment();CommittedSkill=NAME_None;
    // 联机：服务端激活时把雷云态写进复制字段（远端 OnRep 重演云）；客人则上报服务端激活权威域。
    if(GetOwner()->HasAuthority()){NetDomainCast=DomainCast;bNetDomain=true;}
    else NetCast::Send(GetOwner(),ActivatedSkill,1);
    bNetPaid=false;
    Strike();NextStrike=DomainCast.StrikeSeconds;
}
// 雷云 FX——本地/服务端/远端 OnRep 共用同一套参数。
void UFPSElectricMagicComponent::SpawnDomainFX()
{
    CloudFX=UNiagaraFunctionLibrary::SpawnSystemAtLocation(GetWorld(),Cast<UNiagaraSystem>(Assets[0]),GetOwner()->GetActorLocation(),FRotator::ZeroRotator,FVector(1),true,false);
    if(CloudFX)
    {
        CloudFX->SetVariablePosition(TEXT("User.CurrentPosition"),GetOwner()->GetActorLocation());
        CloudFX->SetVariableVec3(TEXT("User.Side"),FVector::ForwardVector);CloudFX->SetVariableVec3(TEXT("User.Up"),FVector::RightVector);
        CloudFX->SetVariableVec3(TEXT("User.SurfaceNormal"),FVector::UpVector);CloudFX->SetVariableVec3(TEXT("User.Wind"),FVector(10,4,0));
        CloudFX->SetVariableFloat(TEXT("User.RadiusX"),DomainCast.Radius);CloudFX->SetVariableFloat(TEXT("User.RadiusY"),DomainCast.Radius*.62f);
        CloudFX->SetVariableFloat(TEXT("User.CloudHeight"),330);CloudFX->SetVariableFloat(TEXT("User.StormDuration"),DomainCast.Duration);
        CloudFX->SetVariableFloat(TEXT("User.CloudEmission"),1);CloudFX->SetVariableFloat(TEXT("User.Strength"),1);
        CloudFX->SetVariableFloat(TEXT("User.DetailReduction"),0);CloudFX->Activate(true);
    }
}
void UFPSElectricMagicComponent::OnRep_Domain()
{
    // 远端副本：雷云出现——仅演云层；伤害 tick 由服务端 Strike() 结算。
    if(!bNetDomain||bDomainActive||Assets.Num()<1||!Assets[0])return;
    DomainCast=NetDomainCast;DomainRewards={};DomainAge=DomainVisualAge=NextStrike=0;bDomainActive=true;bDomainFading=false;
    SpawnDomainFX();
}
void UFPSElectricMagicComponent::SpawnArc(const FVector& Start,const FVector& End,const FLightningCast& Spell,bool bBeam,float ChargeRatio,float Width,bool bContactLight,float Brightness)
{
    Arcs.RemoveAll([](const auto& A){return !A.IsValid();});if(Arcs.Num()>=48)return;
    FActorSpawnParameters P;P.Owner=GetOwner();P.Instigator=Cast<APawn>(GetOwner());P.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    if(auto* A=GetWorld()->SpawnActor<AFPSLightningArc>(Start,FRotator::ZeroRotator,P))
    {
        if(bBeam)A->InitializeColumn(Cast<UStaticMesh>(Assets[9]),Cast<UStaticMesh>(Assets[10]),Cast<UMaterialInterface>(Assets[2]),Cast<UMaterialInterface>(Assets[11]),Start,End,Spell,ChargeRatio);
        else A->InitializeArc(Cast<UNiagaraSystem>(Assets[1]),Start,End,Spell,Width,bContactLight,Brightness);
        Arcs.Add(A);
    }
}
void UFPSElectricMagicComponent::SpawnBurst(const FVector& Point,float Size,const FRotator& Rotation,UObject* System)
{
    Bursts.RemoveAll([](const auto& B){return !B.IsValid();});if(Bursts.Num()>=24)return;
    UObject* Asset=System?System:(Assets.IsValidIndex(4)?Assets[4].Get():nullptr);
    if(auto* B=UNiagaraFunctionLibrary::SpawnSystemAtLocation(GetWorld(),Cast<UNiagaraSystem>(Asset),Point,Rotation,FVector(Size)))Bursts.Add(B);
}
void UFPSElectricMagicComponent::MuzzleFlashFX(const FVector& Start,const FVector& Dir,float Visual)
{
    // Oriented shock plate + forward-cone burst. Not replicated; the client's
    // own release path calls this too so the flash has no server round-trip.
    if(MuzzleIris){MuzzleIris->DestroyComponent();MuzzleIris=nullptr;MuzzleIrisMID=nullptr;}
    if(Assets.IsValidIndex(11)&&Assets.IsValidIndex(10)&&Assets[11]&&Assets[10])
    {
        MuzzleIris=NewObject<UStaticMeshComponent>(GetOwner());GetOwner()->AddInstanceComponent(MuzzleIris);
        MuzzleIris->SetupAttachment(GetOwner()->GetRootComponent());MuzzleIris->SetAbsolute(true,true,true);
        MuzzleIris->SetStaticMesh(Cast<UStaticMesh>(Assets[10]));MuzzleIris->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        MuzzleIris->SetCanEverAffectNavigation(false);MuzzleIris->SetCastShadow(false);MuzzleIris->SetReceivesDecals(false);
        MuzzleIrisMID=UMaterialInstanceDynamic::Create(Cast<UMaterialInterface>(Assets[11]),this);
        MuzzleIris->SetMaterial(0,MuzzleIrisMID);
        MuzzleIris->SetWorldTransform(FTransform(FRotationMatrix::MakeFromZ(-Dir).ToQuat(),Start+Dir*6.f,FVector(FVector::OneVector*26.f)));
        MuzzleIris->RegisterComponent();MuzzleFlashAge=0;MuzzleFlashScale=Visual;
    }
    if(Assets.IsValidIndex(15))SpawnBurst(Start,1.15f*Visual,FRotationMatrix::MakeFromX(Dir).Rotator(),Assets[15]);
    else SpawnBurst(Start,1.2f*Visual);
}
void UFPSElectricMagicComponent::Overload(AActor* Origin,const FLightningCast& Spell,FElectricMagicRewards& Rewards)
{
    auto* P=Cast<APawn>(GetOwner());auto* M=NetCast::AuthorityModel(P,GetWorld()?GetWorld()->GetGameInstance():nullptr);if(!M||!P)return;
    // The overloaded victim is stunned; the discharge damages nearby enemies.
    if(auto* S=UCombatStatusFormula::GetOrAdd(Origin);!S->IsImmune())
    {S->AddStun(Spell.OverloadStun);if(auto* C=Origin->FindComponentByClass<UMonsterCombatComponent>())C->ReceiveStun(P,Spell.OverloadStun,0);}
    SpawnBurst(UWardBreakableGlass::TargetPoint(Origin),.8f);
    UGameplayStatics::PlaySoundAtLocation(this,Cast<USoundBase>(Assets[5]),Origin->GetActorLocation(),.4f);
    if(Spell.OverloadDamage>0)UWardBreakableGlass::BreakInRadius(GetWorld(),Origin->GetActorLocation(),Spell.OverloadRange,P);
    for(auto* Target:Nearby(Origin->GetActorLocation(),Spell.OverloadRange))
        if(Target!=Origin&&Visible(Origin,Target,UWardBreakableGlass::TargetPoint(Origin)))
        {
            SpawnArc(UWardBreakableGlass::TargetPoint(Origin),UWardBreakableGlass::TargetPoint(Target),Spell);
            M->ApplyLightningHit(P,Target,Origin->GetActorLocation(),Spell,Spell.OverloadDamage,Rewards.Hit,false);
        }
}
void UFPSElectricMagicComponent::ApplyStatus(AActor* Target,const FLightningCast& Spell,FElectricMagicRewards& Rewards)
{
    auto* C=Target->FindComponentByClass<UMonsterCombatComponent>();if(!C||C->IsDead())return;
    auto* S=UCombatStatusFormula::GetOrAdd(Target);if(S->IsImmune())return;
    // Native stun and bell extension are shared by all electric damage hits.
    if(S->AddElectrified(Spell.ElectrifyStacks,Spell.ElectrifyDuration,Spell.OverloadStacks,Spell.ElectricBonusPerStack))Overload(Target,Spell,Rewards);
}
void UFPSElectricMagicComponent::Strike()
{
    // 权威端结算；客户端 bDomainActive 仅驱动云层与倒计时——电弧经复制到达。
    if(!GetOwner()->HasAuthority())return;
    auto* P=Cast<APawn>(GetOwner());auto* M=NetCast::AuthorityModel(P,GetWorld()?GetWorld()->GetGameInstance():nullptr);if(!M||!P)return;
    TArray<AActor*> Chain;AActor* Cursor=nullptr;
    for(int32 I=0;I<DomainCast.Hit.Count;++I)
    {
        const FVector Center=Cursor?Cursor->GetActorLocation():P->GetActorLocation();const float Radius=Cursor?DomainCast.Hit.ChainRange:DomainCast.Radius;
        AActor* Best=nullptr;double BestDistance=Radius*Radius;
        for(auto* T:Nearby(Center,Radius))
        {
            const double D=FVector::DistSquared(Center,T->GetActorLocation());
            if(!Chain.Contains(T)&&D<=BestDistance&&Visible(Cursor?Cursor:P,T,Cursor?UWardBreakableGlass::TargetPoint(Cursor):P->GetActorLocation())){Best=T;BestDistance=D;}
        }
        if(!Best)break;Chain.Add(Best);Cursor=Best;
    }
    FVector Start=P->GetActorLocation()+FVector(0,0,285);int32 Hits=0;
    for(int32 I=0;I<Chain.Num();++I)
    {
        auto* Target=Chain[I];if(!Enemy(Target))continue;const auto End=UWardBreakableGlass::TargetPoint(Target);
        SpawnArc(Start,End,DomainCast.Hit);SpawnBurst(End,.6f);
        if(M->ApplyLightningHit(P,Target,Start,DomainCast.Hit,FMath::FloorToFloat(DomainCast.Hit.Damage*FMath::Pow(1-DomainCast.Hit.ChainDecay,I)),DomainRewards.Hit))
        {++Hits;ApplyStatus(Target,DomainCast.Hit,DomainRewards);}Start=End;
    }
    DomainRewards.bMultiHit|=Hits>=2;
    if(Hits>0)UGameplayStatics::PlaySoundAtLocation(this,Cast<USoundBase>(Assets[5]),Start,.35f);
}
void UFPSElectricMagicComponent::FireLance()
{
    auto* P=Cast<AFPSGAMECharacter>(GetOwner());auto* M=Model();const auto* Camera=GetOwner()->FindComponentByClass<UCameraComponent>();
    if(!P||!M||!Camera||!M->CommitElectricMagicRelease(TEXT("thunderLance"))){CancelPending();return;}
    const auto Spell=PendingCast;const float Ratio=FMath::Clamp(ChargeAge/Spell.MaxCharge,.2f,1.f);
    // Uniform disk sampling matches the actual projected crosshair boundary.
    const float Radius=FMath::Sqrt(FMath::FRand())*LanceSpreadTangent(),Angle=FMath::FRand()*2.f*PI;
    const FVector Eye=Camera->GetComponentLocation(),Dir=(Camera->GetForwardVector()+Camera->GetRightVector()*Radius*FMath::Cos(Angle)
        +Camera->GetUpVector()*Radius*FMath::Sin(Angle)).GetSafeNormal();
    // 联机客人：充能量与视线方向上行，服务端权威重算命中链；本地收尾预扣账。
    if(GetWorld()->GetNetMode()==NM_Client)
    {
        NetCast::Send(P,TEXT("thunderLance"),1,Eye,Dir,0,nullptr,ChargeAge);
        M->FinishElectricMagicCast(TEXT("thunderLance"),FElectricMagicRewards());
        // Local release crack — the server-side discharge sound does not reach clients.
        if(Assets.IsValidIndex(14)&&Assets[14])UGameplayStatics::PlaySoundAtLocation(this,Cast<USoundBase>(Assets[14]),CastOrigin(),1.f);
        MuzzleFlashFX(CastOrigin(),Dir,FMath::Lerp(.55f,1.f,Ratio));
        bNetPaid=false;
        DestroyChargeVisual();if(Hands()){Hands()->TakeGesturePayment();Hands()->CancelSpellGesture(this);}
        CommittedSkill=NAME_None;bChargeAtContact=false;ChargeAge=0;
        if(auto* S=UCombatStatusFormula::GetOrAdd(P))if(Spell.Hit.CastHasteStacks>0)S->AddHaste(Spell.Hit.CastHasteStacks,Spell.Hit.CastHasteDuration);
        return;
    }
    FireLanceBody(P,M,Eye,Dir,Ratio,Spell);
    DestroyChargeVisual();if(Hands()){Hands()->TakeGesturePayment();Hands()->CancelSpellGesture(this);}
    CommittedSkill=NAME_None;bChargeAtContact=false;ChargeAge=0;
}
// 雷枪命中结算主体——本地/服务端共用；表现特效（柱/侧弧/爆点）经 AFPSLightningArc 复制到各端。
void UFPSElectricMagicComponent::FireLanceBody(APawn* P,UColdSteelStatusModel* M,const FVector& Eye,const FVector& Dir,float Ratio,const FElectricMagicCast& Spell)
{
    const float Visual=FMath::Lerp(.55f,1.f,Ratio);
    const FVector Start=CastOrigin();
    const auto Targets=Nearby(Eye+Dir*Spell.Hit.Range*.5f,Spell.Hit.Range*.5f+Spell.HalfWidth+120);
    FCollisionQueryParams Walls(SCENE_QUERY_STAT(ThunderLanceWalls),true,P);for(auto* T:Targets)Walls.AddIgnoredActor(T);
    FHitResult EndHit;const bool Blocked=GetWorld()->LineTraceSingleByChannel(EndHit,Eye,Eye+Dir*Spell.Hit.Range,ECC_Visibility,Walls);
    const FVector End=Blocked?EndHit.ImpactPoint:Eye+Dir*Spell.Hit.Range;
    const float Reach=FVector::DotProduct(End-Eye,Dir);
    SpawnArc(Start,End,Spell.Hit,true,Ratio);MuzzleFlashFX(Start,Dir,Visual);FElectricMagicRewards Rewards;
    // Radial lightning fan in the plane perpendicular to the launch axis —
    // the same real-arc language as the beam coils, not sprite shrapnel.
    {
        FLightningCast Fan=Spell.Hit;Fan.Duration=.09f;Fan.Fade=.2f;Fan.Segments=5;Fan.Jitter=.3f;
        FVector T1,T2;Dir.FindBestAxisVectors(T1,T2);
        for(int32 I=0;I<6;++I)
        {
            const float A=float(I)*1.0472f+FMath::FRandRange(-.35f,.35f);
            const FVector Out=(T1*FMath::Cos(A)+T2*FMath::Sin(A)).GetSafeNormal();
            SpawnArc(Start+Dir*8.f,Start+Dir*8.f+Out*FMath::FRandRange(150.f,260.f)*Visual,Fan,false,1.f,.85f,false,42.f);
        }
    }
    // Discharge crack at the muzzle; the existing tail plays at the endpoint below.
    if(Assets.IsValidIndex(14)&&Assets[14])UGameplayStatics::PlaySoundAtLocation(this,Cast<USoundBase>(Assets[14]),Start,1.f);
    // Real lightning bolts coiling the column: the same chain-arc renderer as
    // target-contact arcs, with a tight jitter envelope hugging the beam.
    {
        FLightningCast Wrap=Spell.Hit;Wrap.Duration=Spell.Hit.Duration+.1f;Wrap.Fade=FMath::Max(Spell.Hit.Fade,.5f);
        Wrap.Segments=26;Wrap.Jitter=.042f;
        for(int32 I=0;I<4;++I)SpawnArc(Start,End,Wrap,false,1.f,1.2f,false,52.f);
    }
    TArray<TPair<float,AActor*>> Ordered;
    for(auto* T:Targets)
    {
        const FVector Offset=UWardBreakableGlass::TargetPoint(T)-Eye;const float Along=FVector::DotProduct(Offset,Dir);
        FVector BoundsOrigin,Extent;T->GetActorBounds(true,BoundsOrigin,Extent);
        const float BodyRadius=FMath::Min(Extent.X,Extent.Y)*.6f;
        FHitResult Obstacle;
        if(Along>0&&Along<=Reach&&(Offset-Dir*Along).Size()<=Spell.HalfWidth+BodyRadius&&!GetWorld()->LineTraceSingleByChannel(Obstacle,Eye,UWardBreakableGlass::TargetPoint(T),ECC_Visibility,Walls))Ordered.Emplace(Along,T);
    }
    Ordered.Sort([](const auto& A,const auto& B){return A.Key<B.Key;});
    for(const auto& Entry:Ordered)
    {
        auto* T=Entry.Value;if(!Enemy(T))continue;const auto* Status=T->FindComponentByClass<UCombatStatusFormula>();const int32 Stacks=Status?Status->ElectrifiedCount():0;
        FCollisionQueryParams Direct(SCENE_QUERY_STAT(ThunderLanceWeakpoint),true,P);for(auto* Other:Targets)if(Other!=T)Direct.AddIgnoredActor(Other);
        FHitResult BoneHit;const bool DirectContact=GetWorld()->LineTraceSingleByChannel(BoneHit,Eye,End,ECC_Visibility,Direct)&&BoneHit.GetActor()==T;
        const float Damage=FMath::FloorToFloat(Spell.Hit.Damage*Ratio*Spell.ChargeBonus*(1+Stacks*Spell.StackDamage));
        if(M->ApplyLightningHit(P,T,Eye,Spell.Hit,Damage,Rewards.Hit,true,DirectContact?&BoneHit:nullptr))
        {
            const FVector HitPoint=UWardBreakableGlass::TargetPoint(T);
            // A short snapped bolt ties the beam to each pierced target.
            FLightningCast Side=Spell.Hit;Side.Duration=.10f;Side.Fade=.25f;Side.Segments=5;Side.Jitter=.22f;
            SpawnArc(Eye+Dir*Entry.Key,HitPoint,Side,false,1.f,1.1f,false,40.f);
            SpawnBurst(HitPoint,(1+FMath::Min(5,Stacks)*.08f)*Visual);
            if(auto* C=T->FindComponentByClass<UMonsterCombatComponent>();C&&!C->IsDead())C->ReceiveMeleeKnockback(P,Spell.Knockback);
            ApplyStatus(T,Spell.Hit,Rewards);
        }
    }
    Rewards.bMultiHit=Rewards.Hit.Hits>=2;
    if(Blocked)
    {
        if(auto* Pane=Cast<UWardBreakableGlass>(EndHit.GetComponent()))Pane->BreakAt(EndHit.ImpactPoint,Dir);
        else if(Cast<AFPSIceWall>(EndHit.GetActor()))UGameplayStatics::ApplyPointDamage(EndHit.GetActor(),Spell.Hit.Damage*Ratio*Spell.ChargeBonus,Dir,EndHit,P->GetController(),P,ULightningDamage::StaticClass());
    }
    const FVector ExitDir=Blocked?EndHit.ImpactNormal:-Dir;
    SpawnBurst(End,Spell.EndRadius/135.f*1.875f*Visual,ExitDir.Rotation());
    // Residual discharge arcs scatter off the endpoint: along the wall on a
    // block, or sprayed back down the flight cone on an air end.
    {
        FLightningCast Res=Spell.Hit;Res.Duration=.12f;Res.Fade=.3f;Res.Segments=4;Res.Jitter=.3f;
        FVector T1,T2;ExitDir.FindBestAxisVectors(T1,T2);
        for(int32 I=0;I<(Blocked?3:2);++I)
        {
            const FVector Scatter=(T1*FMath::FRandRange(-1.f,1.f)+T2*FMath::FRandRange(-1.f,1.f)+ExitDir*FMath::FRandRange(.15f,.6f)).GetSafeNormal();
            SpawnArc(End,End+Scatter*FMath::FRandRange(160.f,320.f),Res,false,1.f,.8f,false,35.f);
        }
    }
    UGameplayStatics::PlaySoundAtLocation(this,Cast<USoundBase>(Assets[5]),End,.8f);
    if(auto* PC=Cast<APlayerController>(P->GetController());PC&&PC->PlayerCameraManager)
    {const auto* Setting=IConsoleManager::Get().FindConsoleVariable(TEXT("fps.Camera.Shake"));const float Scale=Setting?Setting->GetFloat():1.f;if(Scale>0)PC->PlayerCameraManager->StartCameraShake(UIceWallLandingCameraShake::StaticClass(),.7f*Scale);}
    GrantCastBuffs(Spell.Hit);M->FinishElectricMagicCast(TEXT("thunderLance"),Rewards);
}
void UFPSElectricMagicComponent::ReleaseLance()
{
    if(QueuedSkill==TEXT("thunderLance")){QueuedSkill=NAME_None;return;}
    if(!IsCharging())return;
    if(PendingCast.bRequiresStaff)if(auto* M=Model();M&&!M->HasEquippedStaff()){CancelPending();Feedback(TEXT("thunderLance"),TEXT("需要法杖"));return;}
    if(bChargeAtContact&&ChargeAge>=PendingCast.MinCharge)FireLance();
    else{CancelPending();Feedback(TEXT("thunderLance"),TEXT("蓄力不足 0.5秒"));}
}
void UFPSElectricMagicComponent::CancelPending(bool bRefund)
{
    const FName Skill=CommittedSkill;QueuedSkill=CommittedSkill=NAME_None;bChargeAtContact=false;ChargeAge=0;
    DestroyChargeVisual();
    if(MuzzleIris){MuzzleIris->DestroyComponent();MuzzleIris=nullptr;MuzzleIrisMID=nullptr;}
    if(bRefund&&!Skill.IsNone())if(auto* M=Model())M->RefundUnreleasedCast(Hands()?Hands()->TakeGesturePayment():0.f,Skill);
    // 联机客人：凝聚/充能期取消——上报服务端退预留。
    if(bRefund&&!Skill.IsNone()&&GetWorld()&&GetWorld()->GetNetMode()==NM_Client&&bNetPaid)NetCast::Send(GetOwner(),Skill,2);
    bNetPaid=false;
    if(Hands())Hands()->CancelSpellGesture(this);
}
// ── 联机服务端入口：风暴域权威激活 / 雷枪充能射线重算 ──
bool UFPSElectricMagicComponent::NetRelease(APawn* Caster,const FColdSteelNetCastRequest& Req,UColdSteelStatusModel* Shadow)
{
    const auto Spell=Shadow->ElectricMagicStats(Req.SkillId);
    if(Spell.bRequiresStaff&&!Shadow->HasEquippedStaff())return false;
    if(Req.SkillId==TEXT("stormDomain"))
    {
        if(!Shadow->CommitElectricMagicRelease(Req.SkillId))return false;
        FinishDomain(true);PendingCast=Spell;DomainCast=Spell;DomainRewards={};DomainAge=DomainVisualAge=NextStrike=0;bDomainActive=true;bDomainFading=false;
        SpawnDomainFX();
        UGameplayStatics::PlaySoundAtLocation(this,Cast<USoundBase>(Assets[5]),Caster->GetActorLocation(),.6f);
        GrantCastBuffs(Spell.Hit);
        NetDomainCast=DomainCast;bNetDomain=true; // 远端副本 OnRep 演云
        Strike();NextStrike=DomainCast.StrikeSeconds;
        return true;
    }
    // thunderLance：客人上报充能量+视线方向，服务端重算命中链。
    if(!Shadow->CommitElectricMagicRelease(Req.SkillId))return false;
    const float Charge=FMath::Clamp(Req.Charge,0.f,Spell.MaxCharge);
    const float Ratio=FMath::Clamp(Charge/Spell.MaxCharge,.2f,1.f);
    const FVector Eye=Caster->GetPawnViewLocation();
    const FVector Dir=Req.AimNormal.IsNearlyZero()?Caster->GetViewRotation().Vector():Req.AimNormal.GetSafeNormal();
    PendingCast=Spell;
    FireLanceBody(Caster,Shadow,Eye,Dir,Ratio,Spell);
    return true;
}
void UFPSElectricMagicComponent::NetCastRejected(uint8 /*Phase*/,uint8 /*Code*/)
{
    bNetPaid=false;
    if(!CommittedSkill.IsNone())
    {
        if(auto* M=Model())M->RefundUnreleasedCast(Hands()?Hands()->TakeGesturePayment():0.f,CommittedSkill);
        Feedback(CommittedSkill,TEXT("施法失败"));
    }
    QueuedSkill=NAME_None;CommittedSkill=NAME_None;bChargeAtContact=false;DestroyChargeVisual();
    if(auto* H=Hands())H->CancelSpellGesture(this);
}
void UFPSElectricMagicComponent::NetCastCancelled(uint8 /*Phase*/)
{
    bNetPaid=false;
}
void UFPSElectricMagicComponent::FinishDomain(bool bTrain)
{
    if(bDomainActive&&bTrain)if(auto* M=NetCast::AuthorityModel(Cast<APawn>(GetOwner()),GetWorld()?GetWorld()->GetGameInstance():nullptr))M->FinishElectricMagicCast(TEXT("stormDomain"),DomainRewards);
    bDomainActive=false;bDomainFading=false;DomainRewards={};
    if(CloudFX){CloudFX->DestroyComponent();CloudFX=nullptr;}
}
void UFPSElectricMagicComponent::ClearEffects()
{
    CancelPending();FinishDomain(false);
    for(auto& A:Arcs)if(A.IsValid())A->Destroy();Arcs.Reset();
    for(auto& B:Bursts)if(B.IsValid())B->DestroyComponent();Bursts.Reset();
}
void UFPSElectricMagicComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick)
{
    Super::TickComponent(Delta,Type,Tick);
    if(const auto* H=GetOwner()->FindComponentByClass<UFPSCombatHealthComponent>();H&&H->IsDead()){ClearEffects();return;}
    const auto* PC=Cast<APlayerController>(Cast<APawn>(GetOwner())->GetController());const auto* S=GetOwner()->FindComponentByClass<UCombatStatusFormula>();
    if(!CommittedSkill.IsNone()&&((S&&(S->IsStunned()||S->IsFrozen()||S->IsPetrified()))||!Hands()||!Hands()->IsSpellGesture(this)||!PC||PC->bShowMouseCursor||AFPSGAMEPlayerController::BlocksOngoingActions(PC)))CancelPending();
    // 蓄力/手势期间切走法杖：未释放取消并按原路退蓝清冷却（与冰墙一致）。
    if(!CommittedSkill.IsNone()&&PendingCast.bRequiresStaff)
        if(const auto* M=Model();M&&!M->HasEquippedStaff()){const FName Skill=CommittedSkill;CancelPending();Feedback(Skill,TEXT("需要法杖"));}
    ServiceQueue();
    // Muzzle shock plate: ~160ms expand+fade along the launch axis.
    if(MuzzleIris)
    {
        MuzzleFlashAge+=Delta;const float FT=MuzzleFlashAge/.16f;
        if(FT>=1.f){MuzzleIris->DestroyComponent();MuzzleIris=nullptr;MuzzleIrisMID=nullptr;}
        else
        {
            const float Ease=1-FMath::Pow(1-FT,2.2f);
            MuzzleIris->SetWorldScale3D(FVector(FVector::OneVector*FMath::Lerp(26.f,230.f*MuzzleFlashScale,Ease)));
            if(MuzzleIrisMID){MuzzleIrisMID->SetScalarParameterValue(TEXT("Strength"),(1-FT)*1.7f);MuzzleIrisMID->SetScalarParameterValue(TEXT("Clock"),MuzzleFlashAge);MuzzleIrisMID->SetScalarParameterValue(TEXT("FirePower"),1.f-FT*.5f);}
        }
    }
    if(IsCharging()&&bChargeAtContact)
    {
        ChargeAge=FMath::Min(ChargeAge+Delta,PendingCast.MaxCharge);
        // Refresh the existing gesture endpoint hold; full charge waits for release.
        if(Hands())Hands()->ContinueSpellRelease(this,.75f,false);
        UpdateChargeVisual();
    }
    if(bDomainActive)
    {
        DomainAge+=Delta;DomainVisualAge+=Delta;
        if(CloudFX){CloudFX->SetWorldLocation(GetOwner()->GetActorLocation());CloudFX->SetVariablePosition(TEXT("User.CurrentPosition"),GetOwner()->GetActorLocation());}
        if(!bDomainFading&&DomainAge>=DomainCast.Duration)
        {if(auto* M=Model())M->FinishElectricMagicCast(TEXT("stormDomain"),DomainRewards);DomainRewards={};bDomainFading=true;if(CloudFX)CloudFX->SetVariableFloat(TEXT("User.CloudEmission"),0);}
        if(bDomainFading)
        {if(CloudFX)CloudFX->SetVariableFloat(TEXT("User.Strength"),FMath::Clamp(1-(DomainAge-DomainCast.Duration)/.6f,0.f,1.f));if(DomainAge>=DomainCast.Duration+.6f)FinishDomain(false);}
        else if(DomainAge>=NextStrike){Strike();NextStrike=DomainAge+DomainCast.StrikeSeconds;}
    }
}
void UFPSElectricMagicComponent::EndPlay(EEndPlayReason::Type Reason)
{if(AssetLoad)AssetLoad->CancelHandle();ClearEffects();Super::EndPlay(Reason);}
