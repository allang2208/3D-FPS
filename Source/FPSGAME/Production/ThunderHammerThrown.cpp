#include "ThunderHammerThrown.h"
#include "ThunderHammerThrow.h"
#include "ThunderHammerGroundContacts.h"
#include "ThunderHammerTuning.h"
#include "ThunderHammerStaticField.h"
#include "ThunderHammerCoil.h"
#include "TimerManager.h"
#include "ThunderHammerRecallAudio.h"
#include "WarhammerAudioPaths.h"
#include "WarhammerShockwave.h"
#include "ProductionToolComponent.h"
#include "../Weapons/ModularSwordVisual.h"
#include "../FPSGAMECharacter.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "Components/SceneComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Engine/World.h"
#include "GameFramework/GameStateBase.h"
#include "GameFramework/WorldSettings.h"
#include "Net/UnrealNetwork.h"
#include "Sound/SoundBase.h"

AThunderHammerThrown::AThunderHammerThrown()
{
    bReplicates=true;SetReplicateMovement(true);SetNetUpdateFrequency(60.f);PrimaryActorTick.bCanEverTick=true;
    auto* Root=CreateDefaultSubobject<USceneComponent>(TEXT("FlightRoot"));SetRootComponent(Root);
    Visual=CreateDefaultSubobject<USceneComponent>(TEXT("SpinningAssembly"));Visual->SetupAttachment(Root);
    Mesh=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("ThrownHeadMount"));Mesh->SetupAttachment(Visual);
    Mesh->SetRelativeLocation(FVector(0,0,-ThunderHammerThrow::CenterZ));
    Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);Mesh->SetCanEverAffectNavigation(false);Mesh->SetCastShadow(true);
    // Outbound terrain contact and recall damage use explicit queries. Neither
    // the assembly nor subsequently attached modules are blocking physics bodies.
    SetActorEnableCollision(false);
}
double AThunderHammerThrown::Clock() const
{
    const auto* GS=GetWorld()->GetGameState();return GS?GS->GetServerWorldTimeSeconds():GetWorld()->GetTimeSeconds();
}
void AThunderHammerThrown::Launch(const FColdSteelItem& Item,const FColdSteelSkillShot& Shot,float Magic)
{
    Weapon=Item;DamageShot=Shot;MagicDamage=FMath::Max(0.f,Magic);StartedAt=Clock();
    const auto* Pawn=Cast<APawn>(GetOwner());FVector Start;ThunderHammerThrow::Launch(Pawn,Start,Velocity,&Weapon);
    if(!DamageShot.ZhenTingForward.IsNearlyZero())
    {
        const FVector FlightDirection=Velocity.GetSafeNormal2D();
        if(!FlightDirection.IsNearlyZero())DamageShot.ZhenTingForward=FlightDirection;
    }
    SetActorLocation(Start);InitialRotation=ThunderHammerThrow::LaunchFrame(Pawn).GetRotation();FlightYaw=Pawn->GetViewRotation().Yaw;
    PrepareVisual();ForceNetUpdate();
    if(HasAuthority()&&DamageShot.bHammerStaticField)
    {
        PulseStaticField();
        GetWorld()->GetTimerManager().SetTimer(StaticFieldTimer,this,&AThunderHammerThrown::PulseStaticField,ThunderHammerStaticField::PulseSeconds,true);
    }
    if(HasAuthority()&&DamageShot.bHammerCoil)
    {
        PulseCoil();
        GetWorld()->GetTimerManager().SetTimer(CoilTimer,this,&AThunderHammerThrown::PulseCoil,ThunderHammerCoil::PulseSeconds,true);
    }
}
void AThunderHammerThrown::PulseCoil()
{
    auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());
    const auto* Profile=ColdSteelAuthority::ForPawn(Pawn);
    const auto* Item=Profile?Profile->FindItem(Weapon.InstanceId):nullptr;
    const auto* Health=Pawn?Pawn->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
    if(!HasAuthority()||Phase>1||!Item||Item->Place!=1||Item->Definition!=Weapon.Definition||
        !ThunderHammerCoil::Installed(Item)||(Health&&Health->IsDead()))
    {GetWorld()->GetTimerManager().ClearTimer(CoilTimer);return;}
    ThunderHammerCoil::Discharge(Pawn,GetActorLocation(),DamageShot,ThunderHammerCoil::RadiusCM,1);
}
void AThunderHammerThrown::PulseStaticField()
{
    auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());
    const auto* Profile=ColdSteelAuthority::ForPawn(Pawn);
    const auto* Item=Profile?Profile->FindItem(Weapon.InstanceId):nullptr;
    const auto* Health=Pawn?Pawn->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
    if(!HasAuthority()||Phase>1||!Item||Item->Place!=1||Item->Definition!=Weapon.Definition||
        !ThunderHammerStaticField::Installed(Item)||(Health&&Health->IsDead()))
    {GetWorld()->GetTimerManager().ClearTimer(StaticFieldTimer);return;}
    ThunderHammerStaticField::Pulse(Pawn,GetActorLocation(),DamageShot,ThunderHammerStaticField::RadiusCM,2);
}
void AThunderHammerThrown::PrepareVisual()
{
    if(GetOwner())if(auto* Tool=GetOwner()->FindComponentByClass<UProductionToolComponent>())AddTickPrerequisiteComponent(Tool);
    if(GetNetMode()==NM_DedicatedServer||Weapon.Definition.IsEmpty())return;
    TArray<FSoftObjectPath> Paths;ColdSteelModularSword::GatherVisualResources(Weapon,Paths);
    Assets=UAssetManager::GetStreamableManager().RequestAsyncLoad(Paths,FStreamableDelegate::CreateUObject(this,&AThunderHammerThrown::BuildVisual));
    // Sound readiness must not wait for every high-resolution material/mesh.
    // A fast recall can otherwise destroy the actor before its shared visual
    // load completes, silently losing the catch even after the contact RPC.
    BuildRecallAudio();Paths.Reset();
    for(const auto* Path:{ThunderHammerRecallAudio::Metal,ThunderHammerRecallAudio::Air,ThunderHammerRecallAudio::Catch})Paths.Emplace(Path);
    Paths.Add(WarhammerAudioPaths::Uppercut);
    AudioAssets=UAssetManager::GetStreamableManager().RequestAsyncLoad(Paths,FStreamableDelegate::CreateUObject(this,&AThunderHammerThrown::BuildRecallAudio),FStreamableManager::AsyncLoadHighPriority);
}
void AThunderHammerThrown::BuildRecallAudio()
{
    RecallMetalSound=Cast<USoundBase>(FSoftObjectPath(ThunderHammerRecallAudio::Metal).ResolveObject());
    RecallAirSound=Cast<USoundBase>(FSoftObjectPath(ThunderHammerRecallAudio::Air).ResolveObject());
    RecallCatchSound=Cast<USoundBase>(FSoftObjectPath(ThunderHammerRecallAudio::Catch).ResolveObject());
    RecallThrowWhooshSound=Cast<USoundBase>(WarhammerAudioPaths::Uppercut.ResolveObject());
    if(Phase==3)PlayRecallCatchAudio();
}
void AThunderHammerThrown::BuildVisual()
{
    ColdSteelModularSword::Apply(Mesh,Weapon);Mesh->SetOnlyOwnerSee(false);Mesh->SetOwnerNoSee(false);
    for(auto* Part:ColdSteelModularSword::Components(Mesh)){Part->SetOnlyOwnerSee(false);Part->SetOwnerNoSee(false);Part->SetVisibility(true);}
}
void AThunderHammerThrown::Land(const FHitResult& Hit)
{
    const FVector Normal=Hit.ImpactNormal.GetSafeNormal(UE_SMALL_NUMBER,FVector::UpVector);
    FVector Forward=FVector::VectorPlaneProject(Velocity,Normal).GetSafeNormal();
    if(Forward.IsNearlyZero())
        Forward=FVector::VectorPlaneProject(FRotator(0,FlightYaw,0).Vector(),Normal).GetSafeNormal();
    const FQuat SurfaceFrame=FRotationMatrix::MakeFromXZ(Forward,Normal).ToQuat();
    GroundRotation=(SurfaceFrame*FRotator(ThunderHammerThrow::GroundPitch,0,0).Quaternion()).GetNormalized();

    // Use a surface point on the installed striking head, not an assembly AABB
    // or the flight sphere. Baked anchors keep dedicated servers mesh-free and
    // produce the same pose even when a client's visual assets arrive late.
    FVector Contact=ThunderHammerThrow::GroundHeadContact(FString())+FVector(0,0,91.6f);
    for(const auto& Part:ColdSteelModularSword::DescribeGeometry(Weapon))
        if(Part.Slot==TEXT("hammer_heads"))
        {
            Contact=Part.RelativeTransform.TransformPosition(ThunderHammerThrow::GroundHeadContact(Part.Mesh));
            break;
        }
    Contact.Z-=ThunderHammerThrow::CenterZ;
    Phase=1;Velocity=FVector::ZeroVector;
    SetActorLocation(Hit.ImpactPoint-Normal*ThunderHammerThrow::GroundEmbedCM-GroundRotation.RotateVector(Contact));
    Visual->SetRelativeLocation(FVector::ZeroVector);Visual->SetWorldRotation(GroundRotation);ForceNetUpdate();
    FActorSpawnParameters Params;Params.Owner=GetOwner();Params.Instigator=GetInstigator();Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    if(auto* Wave=GetWorld()->SpawnActor<AWarhammerShockwave>(Hit.ImpactPoint+Hit.ImpactNormal*2.f,FRotationMatrix::MakeFromZ(Hit.ImpactNormal).Rotator(),Params))
        Wave->Setup(DamageShot,ThunderHammer::RadiusCM,ThunderHammer::StunSeconds,MagicDamage);
}
bool AThunderHammerThrown::IsStillEquipped(const FColdSteelProfile& Profile) const
{
    return Profile.Items.ContainsByPredicate([&](const FColdSteelItem& Item)
        {return Item.InstanceId==Weapon.InstanceId&&Item.Definition==Weapon.Definition&&Item.Place==1;});
}
void AThunderHammerThrown::ReturnToStorage()
{
    if(!HasAuthority()||Phase==4)return;
    MulticastRetireFromEquipment();Destroy();
}
void AThunderHammerThrown::MulticastRetireFromEquipment_Implementation()
{
    // The equipment transaction already owns the item. This actor is only a
    // temporary combat representation, never a pickup or a second inventory item.
    // Send the retirement reason before closing its channel, so an owner in
    // the short docking phase cannot mistake destruction for a completed catch.
    Phase=4;Velocity=FVector::ZeroVector;StopRecallAudio(0.f);
    SetActorHiddenInGame(true);
    if(auto* Pawn=GetOwner())if(auto* Tool=Pawn->FindComponentByClass<UProductionToolComponent>())
        Tool->ThunderHammerReturned(this,false);
}
void AThunderHammerThrown::Tick(float Delta)
{
    Super::Tick(Delta);if(Phase==4)return;
    auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());if(!Pawn){if(HasAuthority())Destroy();return;}
    if(HasAuthority()&&Phase!=4)
    {
        OwnerCheck-=Delta;
        if(OwnerCheck<=0.f)
        {
            OwnerCheck=.2f;const auto* Profile=ColdSteelAuthority::ForPawn(Pawn);const auto* Health=Pawn->FindComponentByClass<UFPSCombatHealthComponent>();
            const auto* Item=Profile?Profile->FindItem(Weapon.InstanceId):nullptr;
            if(!Item||(Health&&Health->IsDead())||Item->Place!=1||Item->Definition!=Weapon.Definition)
            {ReturnToStorage();return;}
        }
        if(Phase==0)
        {
            // Query-driven flight has no movement component to run the engine's
            // world-bounds retirement. A miss into the void must not strand the
            // equipped instance in an unrecallable outbound phase forever.
            const auto* Settings=GetWorld()->GetWorldSettings();
            if(Settings&&Settings->bEnableWorldBoundsChecks&&
                (GetActorLocation().Z<Settings->KillZ||GetActorLocation().GetAbsMax()>HALF_WORLD_MAX))
            {ReturnToStorage();return;}
            Accumulator+=Delta;
            for(int32 I=0;Accumulator>=ThunderHammerThrow::Step&&I<16&&Phase==0;++I)
            {
                Accumulator-=ThunderHammerThrow::Step;FVector P=GetActorLocation();FHitResult Floor;
                const bool Ground=ThunderHammerThrow::Advance(Pawn,this,P,Velocity,Floor);SetActorLocation(P);
                if(Ground)Land(Floor);
            }
        }
        else if(Phase==2)AdvanceRecall(Delta);
    }
    if(Phase==3)
    {
        const auto Frame=ThunderHammerThrow::CatchFrame(Pawn,CatchAge());
        SetActorLocation(Frame.GetLocation());Visual->SetRelativeLocation(FVector::ZeroVector);Visual->SetWorldRotation(Frame.GetRotation());
        TickRecallAudio();
        if(HasAuthority()&&CatchAge()>=ThunderHammerThrow::CatchAttachSeconds)Destroy();
        return;
    }
    FQuat Rotation;
    if(Phase==0)
    {
        // The striking caps span local X; the medallion faces local Y. Roll
        // the detached hammer 90 degrees around its shaft so the striking
        // caps enter the forward tumble plane instead of rolling the seat
        // face toward the target. Blend only after separation: frame zero
        // remains exactly the authored release grip on every client.
        const float Age=FMath::Max(0.f,float(Clock()-StartedAt));
        const float Align=FMath::SmoothStep(0.f,1.f,Age/.10f);
        const FVector Axis=InitialRotation.GetAxisX();
        const FQuat HeadForward=InitialRotation*FQuat(FVector::UpVector,HALF_PI*Align);
        Rotation=FQuat(Axis,FMath::DegreesToRadians(Age*1080.f))*HeadForward;
    }
    else if(Phase==1)Rotation=GroundRotation;
    else Rotation=RecallRotation();
    Visual->SetRelativeLocation(FVector::ZeroVector);
    // While awaiting the authoritative catch receipt, finish the owner's tiny
    // final gap at the rendered palm instead of jittering against replication.
    if(Phase==2&&Pawn->IsLocallyControlled()&&RecallAge()>=RecallDuration)
    {
        const auto Frame=ThunderHammerThrow::CatchFrame(Pawn);
        if(FVector::DistSquared(GetActorLocation(),Frame.GetLocation())<FMath::Square(20.f))Visual->SetWorldLocation(Frame.GetLocation());
    }
    Visual->SetWorldRotation(Rotation);
    TickRecallAudio();
}
void AThunderHammerThrown::EndPlay(const EEndPlayReason::Type Reason)
{
    if(GetWorld())GetWorld()->GetTimerManager().ClearTimer(StaticFieldTimer);
    if(GetWorld())GetWorld()->GetTimerManager().ClearTimer(CoilTimer);
    // A catch receipt can retire the actor before its next presentation tick.
    // The one-shot lives in the world so its damped tail survives the handoff.
    if(Reason==EEndPlayReason::Destroyed&&Phase==3)PlayRecallCatchAudio();
    StopRecallAudio(0.f);
    if(auto* Pawn=GetOwner())if(auto* Tool=Pawn->FindComponentByClass<UProductionToolComponent>())Tool->ThunderHammerReturned(this,Phase==3);
    if(Assets){Assets->CancelHandle();Assets.Reset();}
    if(AudioAssets){AudioAssets->CancelHandle();AudioAssets.Reset();}Super::EndPlay(Reason);
}
void AThunderHammerThrown::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);DOREPLIFETIME(AThunderHammerThrown,Weapon);DOREPLIFETIME(AThunderHammerThrown,Phase);
    DOREPLIFETIME(AThunderHammerThrown,StartedAt);DOREPLIFETIME(AThunderHammerThrown,InitialRotation);DOREPLIFETIME(AThunderHammerThrown,FlightYaw);
    DOREPLIFETIME(AThunderHammerThrown,GroundRotation);
    DOREPLIFETIME(AThunderHammerThrown,RecallAt);DOREPLIFETIME(AThunderHammerThrown,RecallDuration);DOREPLIFETIME(AThunderHammerThrown,RecallFrom);
    DOREPLIFETIME(AThunderHammerThrown,CaughtAt);DOREPLIFETIME(AThunderHammerThrown,RecallAxis);
}
