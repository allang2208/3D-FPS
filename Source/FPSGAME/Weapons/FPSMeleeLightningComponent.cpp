#include "FPSMeleeLightningComponent.h"
#include "RuneSwordComponent.h"
#include "../Production/ProductionToolComponent.h"
#include "../Skills/FPSLightningArc.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelEnhancementSystem.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Engine/OverlapResult.h"
#include "Engine/World.h"
#include "Engine/GameInstance.h"
#include "GameFramework/Pawn.h"
#include "NiagaraSystem.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SceneComponent.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInstanceDynamic.h"

UFPSMeleeLightningComponent::UFPSMeleeLightningComponent()
{
    PrimaryComponentTick.bCanEverTick=true;
    PrimaryComponentTick.bStartWithTickEnabled=false;
    PrimaryComponentTick.TickGroup=TG_PostUpdateWork;
    ChainAsset=TSoftObjectPtr<UNiagaraSystem>(FSoftObjectPath(TEXT("/Game/Skills/Lightning/NS_LightningChain.NS_LightningChain")));
    BladeAsset=TSoftObjectPtr<UNiagaraSystem>(FSoftObjectPath(TEXT("/Game/Weapons/ElectrifiedMelee/NS_ElectrifiedBlade.NS_ElectrifiedBlade")));
    OrbitMeshAsset=TSoftObjectPtr<UStaticMesh>(FSoftObjectPath(TEXT("/Game/Weapons/ElectrifiedMelee/OrbitV2/SM_ElectrifiedOrbit.SM_ElectrifiedOrbit")));
    OrbitMaterialAsset=TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(TEXT("/Game/Weapons/ElectrifiedMelee/OrbitV2/M_ElectrifiedOrbit.M_ElectrifiedOrbit")));
}

void UFPSMeleeLightningComponent::BeginPlay()
{
    Super::BeginPlay();AddTickPrerequisiteActor(GetOwner());
    if(auto* Sword=GetOwner()->FindComponentByClass<URuneSwordComponent>())AddTickPrerequisiteComponent(Sword);
    if(auto* Tool=GetOwner()->FindComponentByClass<UProductionToolComponent>())AddTickPrerequisiteComponent(Tool);
    CosmeticRandom.Initialize(int32(FPlatformTime::Cycles()));
    Profile=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(auto* M=Profile.Get())ProfileChanged=M->OnChanged.AddUObject(this,&ThisClass::RefreshEquipment);
    if(GetNetMode()!=NM_DedicatedServer)
        LoadHandle=UAssetManager::GetStreamableManager().RequestAsyncLoad(
            TArray<FSoftObjectPath>{ChainAsset.ToSoftObjectPath(),BladeAsset.ToSoftObjectPath(),OrbitMeshAsset.ToSoftObjectPath(),OrbitMaterialAsset.ToSoftObjectPath()},
            FStreamableDelegate::CreateWeakLambda(this,[this]()
            {
                ChainSystem=ChainAsset.Get();BladeSystem=BladeAsset.Get();
                OrbitMesh=OrbitMeshAsset.Get();OrbitMaterial=OrbitMaterialAsset.Get();
            }));
    RefreshEquipment();
}

bool UFPSMeleeLightningComponent::IsEnemy(AActor* Target,AActor* Owner)
{
    if(!IsValid(Target)||Target==Owner||Target->IsActorBeingDestroyed()||!Target->CanBeDamaged()
        ||Target->ActorHasTag(TEXT("Friendly"))||Target->ActorHasTag(TEXT("Companion"))||Target->ActorHasTag(TEXT("Player")))return false;
    if(const auto* Pawn=Cast<APawn>(Target);Pawn&&Pawn->IsPlayerControlled())return false;
    const auto* Combat=Target->FindComponentByClass<UMonsterCombatComponent>();
    return Combat&&!Combat->IsDead();
}

void UFPSMeleeLightningComponent::QueueDischarge(const FHitResult& Hit,float RadiusCM,int32 MinimumLevel)
{
    auto* M=Profile.Get();const auto* Pawn=Cast<APawn>(GetOwner());
    if(!M||!Pawn||!Pawn->HasAuthority()||!Pawn->IsPlayerControlled()||RadiusCM<=0.f||MinimumLevel<=0)return;
    // Called only after a confirmed melee hit. The original victim may already be dead.
    FWave Wave;Wave.Chain=MakeShared<FChain>();Wave.Chain->Radius=RadiusCM;
    Wave.Chain->Spell=M->LightningStats(FMath::Max(MinimumLevel,M->LightningProgress().Level));
    Wave.Origin=Hit.GetActor();Wave.Start=IsValid(Hit.GetActor())?Hit.GetActor()->GetActorLocation():FVector(Hit.ImpactPoint);Wave.bRandomFirst=true;
    if(Hit.GetActor())Wave.Chain->Visited.Add(Hit.GetActor());
    Wave.Due=GetWorld()->GetTimeSeconds();Waves.Add(MoveTemp(Wave));SetComponentTickEnabled(true);
    // Damage waits until the melee transaction has unwound. No nested weapon
    // mastery/armor procs, and no manipulation of the active spell's snapshot.
}

void UFPSMeleeLightningComponent::Gather(const FWave& Wave,TArray<AActor*>& Out) const
{
    const float Radius=Wave.bOverload?Wave.Chain->Spell.OverloadRange:Wave.Chain->Radius;
    if(Radius<=0.f)return;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(ElectrifiedMeleeTargets),false,GetOwner());
    if(Wave.Origin.IsValid())Query.AddIgnoredActor(Wave.Origin.Get());
    TArray<FOverlapResult> Overlaps;
    GetWorld()->OverlapMultiByObjectType(Overlaps,Wave.Start,FQuat::Identity,
        FCollisionObjectQueryParams(ECC_Pawn),FCollisionShape::MakeSphere(Radius),Query);
    FCollisionQueryParams Sight(SCENE_QUERY_STAT(ElectrifiedMeleeSight),true,GetOwner());
    if(Wave.Origin.IsValid())Sight.AddIgnoredActor(Wave.Origin.Get());
    for(const auto& Previous:Wave.Chain->Visited)if(Previous.IsValid())Sight.AddIgnoredActor(Previous.Get());
    // Body geometry does not hide other fan-out targets; level geometry does.
    for(const auto& Hit:Overlaps)if(AActor* Target=Hit.GetActor())
    {
        Sight.AddIgnoredActor(Target);
        if(!Wave.Chain->Visited.Contains(Target)&&IsEnemy(Target,GetOwner())
            &&FVector::DistSquared(Wave.Start,Target->GetActorLocation())<=FMath::Square(Radius))Out.AddUnique(Target);
    }
    Out.RemoveAll([&](AActor* Target)
    {
        FHitResult Cover;
        return GetWorld()->LineTraceSingleByChannel(Cover,Wave.Start,Target->GetActorLocation(),ECC_Visibility,Sight);
    });
}

void UFPSMeleeLightningComponent::ProcessWave(const FWave& Wave)
{
    auto* M=Profile.Get();auto* Pawn=Cast<APawn>(GetOwner());if(!M||!Pawn||!Wave.Chain)return;
    TArray<AActor*> Targets;Gather(Wave,Targets);
    if(Wave.bRandomFirst&&!Targets.IsEmpty())
    {AActor* Chosen=Targets[FMath::RandHelper(Targets.Num())];Targets.Reset();Targets.Add(Chosen);}
    const auto& Spell=Wave.Chain->Spell;
    const float Damage=Wave.bOverload?Spell.OverloadDamage:
        FMath::FloorToFloat(Spell.Damage*FMath::Pow(1.f-Spell.ChainDecay,Wave.Depth));
    if(Damage<=0.f)return;
    FLightningRewards Rewards;
    for(AActor* Target:Targets)
    {
        if(!IsEnemy(Target,Pawn)||Wave.Chain->Visited.Contains(Target))continue;
        Wave.Chain->Visited.Add(Target);
        const FVector End=Target->GetActorLocation();
        ShowArc(Wave.Start,End,Spell,Wave.bOverload);
        // Automatic enchants grant normal kill rewards, but do not train the
        // active lightning skill or turn its saved level into the enchant floor.
        if(!M->ApplyLightningHit(Pawn,Target,Wave.Start,Spell,Damage,Rewards,false))continue;
        auto* Combat=IsValid(Target)?Target->FindComponentByClass<UMonsterCombatComponent>():nullptr;
        const bool Killed=!IsValid(Target)||Target->IsActorBeingDestroyed()||(Combat&&Combat->IsDead());
        FWave Next;Next.Chain=Wave.Chain;Next.Origin=Target;Next.Start=End;
        Next.Depth=Wave.Depth+1;Next.Due=GetWorld()->GetTimeSeconds()+.06;
        if(Killed){Waves.Add(MoveTemp(Next));continue;}
        if(!Combat)continue;
        auto* Status=UCombatStatusFormula::GetOrAdd(Target);
        if(Status->IsImmune())continue;
        if(!Wave.bOverload){Combat->ReceiveStun(Pawn,Spell.StunSeconds,0);Status->AddStun(Spell.StunSeconds);}
        if(Status->AddElectrified(Wave.bOverload?1:Spell.ElectrifyStacks,Spell.ElectrifyDuration,
            Spell.OverloadStacks,Spell.ElectricBonusPerStack))
        {
            Combat->ReceiveStun(Pawn,Spell.OverloadStun,0);Status->AddStun(Spell.OverloadStun);
            Next.bOverload=true;Waves.Add(MoveTemp(Next));
        }
    }
    if(!Rewards.KillRewards.IsEmpty())M->FinishLightningCast(Rewards);
}

void UFPSMeleeLightningComponent::ShowArc(const FVector& Start,const FVector& End,const FLightningCast& Spell,bool bOverload)
{
    if(!ChainSystem)return;
    WorldArcs.RemoveAll([](const auto& Arc){return !Arc.IsValid();});
    // A cosmetic budget only: every eligible enemy still receives damage.
    if(WorldArcs.Num()>=32){if(auto* Old=WorldArcs[0].Get())Old->Destroy();WorldArcs.RemoveAt(0);}
    FActorSpawnParameters Params;Params.Owner=GetOwner();Params.Instigator=Cast<APawn>(GetOwner());
    Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    if(auto* Arc=GetWorld()->SpawnActor<AFPSLightningArc>(Start,FRotator::ZeroRotator,Params))
    {
        auto Visual=Spell;if(bOverload){Visual.Duration=.3f;Visual.Fade=.2f;}
        Arc->InitializeArc(ChainSystem,Start,End,Visual,bOverload?.48f:.80f,false,68.f);WorldArcs.Add(Arc);
    }
}

void UFPSMeleeLightningComponent::RefreshEquipment()
{
    auto* M=Profile.Get();if(!M)return;
    const auto* Item=M->ActiveProductionTool();if(!Item)Item=M->Equipped();
    const FString Id=Item?Item->InstanceId:FString();const uint32 Hash=Item?GetTypeHash(Item->Data):0;
    if(Id==VisualItem&&Hash==VisualDataHash)return;
    VisualItem=Id;VisualDataHash=Hash;bBladeEnabled=false;ClearBlade();
    if(Item&&ColdSteelInventory::IsMeleeWeapon(*Item))
        if(const auto* E=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelEnhancementSystem>())
            bBladeEnabled=E->Effect(*Item,TEXT("electrifiedMelee"))>0.
                &&E->Effect(*Item,TEXT("electrifiedRadiusM"))>0.&&E->Effect(*Item,TEXT("electrifiedMinLevel"))>0.;
    SetComponentTickEnabled(bBladeEnabled||!Waves.IsEmpty());
}

void UFPSMeleeLightningComponent::TickBlade(float Delta)
{
    if(!bBladeEnabled||GetNetMode()==NM_DedicatedServer)return;
    USceneComponent* Parent=nullptr;FName Socket=NAME_None;
    FTransform LocalFrame;float Length=0.f;bool bVisible=false;
    if(const auto* Tool=GetOwner()->FindComponentByClass<UProductionToolComponent>();Tool&&Tool->IsEquipped())
        bVisible=Tool->GetEnchantmentBladeAttachment(Parent,Socket,LocalFrame,Length);
    else if(const auto* Sword=GetOwner()->FindComponentByClass<URuneSwordComponent>())
        bVisible=Sword->GetEnchantmentBladeAttachment(Parent,Socket,LocalFrame,Length);
    if(!bVisible||!IsValid(Parent)){ClearBlade();return;}
    if(BladeAnchor&&(BladeAnchor->GetAttachParent()!=Parent||BladeAnchor->GetAttachSocketName()!=Socket))ClearBlade();
    if(!BladeAnchor)
    {
        BladeAnchor=NewObject<USceneComponent>(GetOwner());
        BladeAnchor->SetMobility(EComponentMobility::Movable);
        BladeAnchor->SetupAttachment(Parent,Socket);
        BladeAnchor->SetRelativeTransform(LocalFrame);
        GetOwner()->AddInstanceComponent(BladeAnchor);BladeAnchor->RegisterComponent();
    }
    else BladeAnchor->SetRelativeTransform(LocalFrame);
    BladeAge+=Delta;
    UpdateBladeRings(Length);
    if(!BladeSystem)return;
    BladeArcs.RemoveAll([](const auto& Arc){return !Arc.IsValid();});
    BladeCountdown-=Delta;
    if(BladeCountdown>0.f)return;
    BladeCountdown=CosmeticRandom.FRandRange(.095f,.15f);
    FActorSpawnParameters Params;Params.Owner=GetOwner();Params.Instigator=Cast<APawn>(GetOwner());
    Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    if(auto* Arc=GetWorld()->SpawnActor<AFPSLightningArc>(BladeAnchor->GetComponentLocation(),BladeAnchor->GetComponentRotation(),Params))
    {
        Arc->AddTickPrerequisiteComponent(this);
        Arc->InitializeBladeArc(BladeSystem,BladeAnchor,Length,CosmeticRandom.RandRange(1,MAX_int32));
        // One short-range scene light for the held weapon, even while several
        // old ribbons are fading. Do not multiply lights by ribbon count.
        for(auto& Previous:BladeArcs)if(Previous.IsValid())Previous->SetBladeLightVisible(false);
        BladeArcs.Add(Arc);
    }
}

void UFPSMeleeLightningComponent::UpdateBladeRings(float Length)
{
    if(!BladeAnchor||!OrbitMesh||!OrbitMaterial)return;
    // Three reusable open, forked electric fragments. Geometry and MIDs are
    // created only on equip; shader gaps and staggered travel break up the orbit.
    if(BladeRings.IsEmpty())
        for(int32 I=0;I<3;++I)
        {
            auto* Ring=NewObject<UStaticMeshComponent>(GetOwner());
            Ring->SetMobility(EComponentMobility::Movable);
            Ring->SetStaticMesh(OrbitMesh);
            Ring->SetCollisionEnabled(ECollisionEnabled::NoCollision);
            Ring->SetGenerateOverlapEvents(false);Ring->SetCanEverAffectNavigation(false);
            Ring->SetCastShadow(false);Ring->SetReceivesDecals(false);
            Ring->SetVisibleInRayTracing(false);Ring->SetOnlyOwnerSee(true);
            Ring->SetupAttachment(BladeAnchor);
            GetOwner()->AddInstanceComponent(Ring);Ring->RegisterComponent();
            auto* Material=UMaterialInstanceDynamic::Create(OrbitMaterial,Ring);
            Material->SetScalarParameterValue(TEXT("Phase"),I/3.f);
            Material->SetScalarParameterValue(TEXT("Speed"),I==1?-.23f:.27f+I*.035f);
            Ring->SetMaterial(0,Material);BladeRings.Add(Ring);
        }
    const float Radius=FMath::Clamp(Length*.06f,3.2f,6.5f);
    const float Flash=!BladeArcs.IsEmpty()&&BladeArcs.Last().IsValid()?BladeArcs.Last()->BladeFlash():0.f;
    for(int32 I=0;I<BladeRings.Num();++I)
    {
        const float Phase=I*2.f*PI/3.f;
        const float Along=.15f+.70f*FMath::Frac(BladeAge*(.19f+.027f*I)+I/3.f);
        const float Spin=Phase+BladeAge*(I==1?-2.4f:1.9f)+.28f*FMath::Sin(BladeAge*9.f+Phase);
        const FQuat Orbit=FQuat(FVector::ForwardVector,Spin)
            *FQuat(FVector::RightVector,.23f*FMath::Sin(BladeAge*2.f+Phase));
        // Authored fragments occupy only part of a 10 cm radius orbit. They
        // cannot form a solid hoop, even at the brightest instant.
        const float Scale=Radius*(I==1?1.05f:.98f)/10.f;
        BladeRings[I]->SetRelativeTransform(FTransform(Orbit,FVector(Length*Along,0,0),FVector(Scale)));
        if(auto* Material=Cast<UMaterialInstanceDynamic>(BladeRings[I]->GetMaterial(0)))
            Material->SetScalarParameterValue(TEXT("Flash"),Flash);
    }
}

void UFPSMeleeLightningComponent::ClearBlade()
{
    for(auto& Arc:BladeArcs)if(Arc.IsValid())Arc->Destroy();BladeArcs.Reset();
    for(auto& Ring:BladeRings)if(IsValid(Ring)){GetOwner()->RemoveInstanceComponent(Ring);Ring->DestroyComponent();}BladeRings.Reset();
    if(BladeAnchor){GetOwner()->RemoveInstanceComponent(BladeAnchor);BladeAnchor->DestroyComponent();BladeAnchor=nullptr;}
    BladeCountdown=0.f;BladeAge=0.f;
}

void UFPSMeleeLightningComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick)
{
    Super::TickComponent(Delta,Type,Tick);
    if(const auto* Health=GetOwner()->FindComponentByClass<UFPSCombatHealthComponent>();Health&&Health->IsDead())
    {Waves.Reset();ClearBlade();return;}
    // Move pending work out before processing: a kill may append a new wave.
    TArray<FWave> Ready=MoveTemp(Waves);Waves.Reset();
    for(const auto& Wave:Ready)
        if(Wave.Due<=GetWorld()->GetTimeSeconds())ProcessWave(Wave);else Waves.Add(Wave);
    TickBlade(Delta);
    SetComponentTickEnabled(bBladeEnabled||!Waves.IsEmpty());
}

void UFPSMeleeLightningComponent::EndPlay(EEndPlayReason::Type Reason)
{
    if(auto* M=Profile.Get())M->OnChanged.Remove(ProfileChanged);
    if(LoadHandle)LoadHandle->CancelHandle();LoadHandle.Reset();
    Waves.Reset();ClearBlade();for(auto& Arc:WorldArcs)if(Arc.IsValid())Arc->Destroy();WorldArcs.Reset();
    Super::EndPlay(Reason);
}
