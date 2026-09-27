#include "FPSPotionUseComponent.h"
#include "PotionVisuals.h"
#include "../FPSGAMECharacter.h"
#include "../FPSGAMEPlayerController.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelHUDWidget.h"
#include "../Skills/FPSCastingMeshComponent.h"
#include "../Movement/FPSTraversalRules.h"
#include "../Weapons/Bow/BowWeaponComponent.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "Camera/CameraComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Materials/MaterialInterface.h"

UFPSPotionUseComponent::UFPSPotionUseComponent()
{
    PrimaryComponentTick.bCanEverTick=true;
    PrimaryComponentTick.bStartWithTickEnabled=false;
    PrimaryComponentTick.TickGroup=TG_PostUpdateWork;
}
bool UFPSPotionUseComponent::IsPotion(const FString& Definition)
{
    return Definition==TEXT("hp_potion")||Definition.StartsWith(TEXT("hp_potion_"))||
        Definition==TEXT("mp_potion")||Definition.StartsWith(TEXT("mp_potion_"));
}
void UFPSPotionUseComponent::BeginPlay()
{
    Super::BeginPlay();AddTickPrerequisiteActor(GetOwner());
    if(auto* Bow=GetOwner()->FindComponentByClass<UBowWeaponComponent>())AddTickPrerequisiteComponent(Bow);
    HealthMotion.Load(false);ManaMotion.Load(true);
    TArray<FSoftObjectPath> Paths;
    for(const auto& Tier:PotionVisuals::Tiers())
    {
        Paths.Add(FSoftObjectPath(Tier.Shell));Paths.Add(FSoftObjectPath(Tier.Liquid));Paths.Add(FSoftObjectPath(Tier.Stopper));
    }
    const int32 MeshCount=Paths.Num();
    Paths.Add(FSoftObjectPath(PotionVisuals::LiquidMaterial(false)));
    Paths.Add(FSoftObjectPath(PotionVisuals::LiquidMaterial(true)));
    LoadHandle=UAssetManager::GetStreamableManager().RequestAsyncLoad(Paths,FStreamableDelegate::CreateWeakLambda(this,[this,Paths,MeshCount]()
    {
        Assets.Reset();LiquidMaterials.Reset();
        for(int32 I=0;I<MeshCount;++I)Assets.Add(Cast<UStaticMesh>(Paths[I].ResolveObject()));
        for(int32 I=MeshCount;I<Paths.Num();++I)LiquidMaterials.Add(Cast<UMaterialInterface>(Paths[I].ResolveObject()));
    }));
    auto* Camera=GetOwner()->FindComponentByClass<UCameraComponent>();if(!Camera)return;
    const auto MakePart=[&](const TCHAR* Name)
    {
        auto* Part=NewObject<UStaticMeshComponent>(GetOwner(),Name);GetOwner()->AddInstanceComponent(Part);
        Part->SetupAttachment(Camera);Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Part->SetCanEverAffectNavigation(false);Part->SetCastShadow(false);Part->SetOnlyOwnerSee(true);
        Part->bReceivesDecals=false;Part->SetVisibility(false);Part->RegisterComponent();return Part;
    };
    Bottle=MakePart(TEXT("HeldPotionBottle"));Liquid=MakePart(TEXT("HeldPotionLiquid"));Stopper=MakePart(TEXT("HeldPotionStopper"));
    FallbackHands=NewObject<UFPSCastingMeshComponent>(GetOwner(),TEXT("PotionFallbackLeftArm"));
    GetOwner()->AddInstanceComponent(FallbackHands);FallbackHands->SetupAttachment(Camera);
    FallbackHands->SetRelativeRotation(FRotator(0,90,0));
    FallbackHands->SetSkeletalMesh(GetDefault<UFPSTraversalSettings>()->ArmsMesh.LoadSynchronous());
    FallbackHands->SetCollisionEnabled(ECollisionEnabled::NoCollision);FallbackHands->SetCanEverAffectNavigation(false);
    FallbackHands->SetCastShadow(false);FallbackHands->SetOnlyOwnerSee(true);FallbackHands->SetVisibility(false);
    FallbackHands->RegisterComponent();FallbackHands->SetComponentTickEnabled(false);
    FallbackHands->HideBoneByName(TEXT("clavicle_r"),EPhysBodyOp::PBO_None);
}
bool UFPSPotionUseComponent::TryBegin(const FString& ItemId,const FString& Definition)
{
    auto* Player=Cast<AFPSGAMECharacter>(GetOwner());
    auto* Model=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!Player||!Player->IsLocallyControlled()||GetNetMode()!=NM_Standalone||!Model||!Bottle||!IsPotion(Definition))return false;
    if(bActive){Model->Message=TEXT("正在喝药水");return false;}
    if(Player->IsLeftHandHeldForCast()||Player->IsLeftHandBusyForCast()||Player->IsCastBlockingLeftHandAction())
    {Model->Message=TEXT("左手当前被占用");return false;}
    const bool bMana=Definition.StartsWith(TEXT("mp_"));
    const int32 TierIndex=PotionVisuals::FindTier(Definition);
    if(TierIndex==INDEX_NONE){Model->Message=TEXT("药水瓶型尚未配置");return false;}
    const int32 Base=TierIndex*3;
    if(!Assets.IsValidIndex(Base+2)||!Assets[Base]||!Assets[Base+1]||!Assets[Base+2]||
        LiquidMaterials.Num()!=2||!LiquidMaterials[bMana?1:0])
    {Model->Message=TEXT("药水动作资源正在加载");return false;}
    // Bottle geometry is shared by HP/MP. Keep a common grasp and the existing
    // mouth-to-hand distance; height differences move only the bottle's bottom.
    Motion=HealthMotion;
    Motion.GripHeight=PotionVisuals::Tiers()[TierIndex].GripHeightCm;
    if(Motion.Keys.IsEmpty()){Model->Message=TEXT("药水动作尚未加载");return false;}
    auto* PC=Cast<AFPSGAMEPlayerController>(Player->GetController());
    if(PC&&PC->GetColdSteelHUD()&&PC->GetColdSteelHUD()->IsInventoryOpen())PC->GetColdSteelHUD()->ToggleInventory();
    if(AFPSGAMEPlayerController::BlocksOngoingActions(PC))return false;
    Bottle->SetStaticMesh(Assets[Base]);Liquid->SetStaticMesh(Assets[Base+1]);Stopper->SetStaticMesh(Assets[Base+2]);
    Liquid->SetMaterial(0,LiquidMaterials[bMana?1:0]);
    UsingItem=ItemId;bCommitted=bUncapped=bDiscarded=false;StartTime=GetWorld()->GetTimeSeconds();
    ArmPose.Reset();ActiveHands.Reset();
    // Bow's existing left-hand action gate stows the bow; use the accepted bare
    // arm during that gap. Firearms/melee/tools keep their own native hand mesh.
    const auto* Bow=Player->FindComponentByClass<UBowWeaponComponent>();
    if(!Bow||!Bow->IsEquipped())
    {
        TInlineComponentArray<UFPSCastingMeshComponent*> Meshes(Player);
        for(auto* Mesh:Meshes)if(Mesh!=FallbackHands&&Mesh->bApplyLeftHandCast&&Mesh->GetSkeletalMeshAsset()&&
            Mesh->IsVisible()&&!Mesh->bHiddenInGame&&Mesh->GetBoneIndex(TEXT("hand_l"))>=0)
        {ActiveHands=Mesh;break;}
    }
    if(!ActiveHands.IsValid())ActiveHands=FallbackHands;
    bActive=true;SetComponentTickEnabled(true);Model->Message=TEXT("饮用药水");return true;
}
float UFPSPotionUseComponent::Age() const{return bActive?float(GetWorld()->GetTimeSeconds()-StartTime):0.f;}
void UFPSPotionUseComponent::ApplyHandPose(UFPSCastingMeshComponent& Mesh)
{
    if(!bActive||ActiveHands.Get()!=&Mesh)return;
    FTransform PalmWorld;
    if(ArmPose.Apply(Mesh,Motion,Age(),PalmWorld))UpdateBottle(PalmWorld);
}
void UFPSPotionUseComponent::UpdateBottle(const FTransform& PalmWorld)
{
    const float T=Age();
    // Follow the solved hand (including this rig's entry blend), never a socket
    // from the previous frame or an independently animated bottle trajectory.
    const FQuat Upright=FRotationMatrix::MakeFromXZ(FVector::ForwardVector,FVector::RightVector).ToQuat();
    const FQuat Rotation=PalmWorld.GetRotation()*Upright.Inverse();
    const FVector Grip=PalmWorld.TransformPosition(Motion.GripInPalm);
    const FTransform World(Rotation,Grip-Rotation.RotateVector(FVector(0,0,Motion.GripHeight)));
    const bool Show=T>=Motion.Grab&&T<Motion.Release&&!bDiscarded;
    Bottle->SetWorldTransform(World);Bottle->SetVisibility(Show);
    Stopper->SetWorldTransform(World);Stopper->SetVisibility(Show&&T<Motion.Uncap&&!bUncapped);
    const float Fill=1.f-FPotionUseMotion::Ease((T-Motion.DrinkStart)/(Motion.DrinkEnd-Motion.DrinkStart));
    FTransform Fluid=World;Fluid.SetScale3D(FVector(1,1,FMath::Max(.015f,Fill)));
    Fluid.AddToTranslation(Rotation.RotateVector(FVector(0,0,.62f*(1.f-Fill))));
    Liquid->SetWorldTransform(Fluid);Liquid->SetVisibility(Show&&!bCommitted&&Fill>.015f);
}
void UFPSPotionUseComponent::Discard(UStaticMeshComponent* Visual,const FVector& Velocity,float Lifetime)
{
    if(!Visual||!Visual->GetStaticMesh())return;
    const auto* Camera=GetOwner()->FindComponentByClass<UCameraComponent>();if(!Camera)return;
    FActorSpawnParameters Params;Params.Owner=GetOwner();Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    auto* Prop=GetWorld()->SpawnActor<AStaticMeshActor>(AStaticMeshActor::StaticClass(),Visual->GetComponentTransform(),Params);
    if(!Prop)return;
    auto* Mesh=Prop->GetStaticMeshComponent();Mesh->SetMobility(EComponentMobility::Movable);Mesh->SetStaticMesh(Visual->GetStaticMesh());
    Mesh->SetCanEverAffectNavigation(false);Mesh->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
    Mesh->SetCollisionObjectType(ECC_PhysicsBody);Mesh->SetCollisionResponseToAllChannels(ECR_Ignore);
    Mesh->SetCollisionResponseToChannel(ECC_WorldStatic,ECR_Block);Mesh->SetCollisionResponseToChannel(ECC_WorldDynamic,ECR_Block);
    Mesh->SetSimulatePhysics(true);Mesh->SetMassOverrideInKg(NAME_None,.12f,true);Mesh->SetUseCCD(true);
    Mesh->SetPhysicsLinearVelocity(GetOwner()->GetVelocity()+Camera->GetComponentTransform().TransformVectorNoScale(Velocity));
    Mesh->SetPhysicsAngularVelocityInDegrees(Camera->GetComponentTransform().TransformVectorNoScale(FVector(-210,360,180)));
    Prop->SetLifeSpan(Lifetime);
}
void UFPSPotionUseComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick)
{
    Super::TickComponent(Delta,Type,Tick);if(!bActive)return;
    const auto* Player=Cast<AFPSGAMECharacter>(GetOwner());
    const auto* Health=GetOwner()->FindComponentByClass<UFPSCombatHealthComponent>();
    if(!Player||!Health||Health->IsDead()||Player->IsTraversing()||
        AFPSGAMEPlayerController::BlocksOngoingActions(Cast<APlayerController>(Player->GetController())))
    {Cancel();return;}
    if(ActiveHands==FallbackHands)
    {
        FallbackHands->SetVisibility(true);FallbackHands->TickAnimation(0.f,false);FallbackHands->RefreshBoneTransforms();
    }
    const float T=Age();
    if(T>=Motion.Uncap&&!bUncapped){bUncapped=true;Discard(Stopper,FVector(80,-140,160),2.5f);Stopper->SetVisibility(false);}
    if(T>=Motion.Contact&&!bCommitted)
    {
        auto* Model=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
        // Publication calls ApplyColdSteelProfile and UI listeners synchronously.
        // Mark contact before that callback so any nested interruption cannot
        // treat an already consumed bottle as an uncommitted action.
        bCommitted=true;
        const bool Applied=Model&&Model->UseConsumableAtContact(UsingItem,true);
        if(!bActive)return;
        if(!Applied){bCommitted=false;Cancel();return;}
        Liquid->SetVisibility(false);
    }
    if(T>=Motion.Release&&!bDiscarded){bDiscarded=true;Discard(Bottle,FVector(540,-360,190),7.f);Bottle->SetVisibility(false);Liquid->SetVisibility(false);}
    if(T>=Motion.Duration)Finish();
}
void UFPSPotionUseComponent::Cancel()
{
    if(!bActive)return;
    // Before contact there is no inventory mutation. After contact the empty
    // bottle can drop, but the successful save/effect must never be refunded.
    if(bCommitted&&!bDiscarded)Discard(Bottle,FVector(40,-40,-50),5.f);
    Finish();
}
void UFPSPotionUseComponent::Finish()
{
    bActive=false;UsingItem.Reset();ActiveHands.Reset();ArmPose.Reset();SetComponentTickEnabled(false);
    if(Bottle)Bottle->SetVisibility(false);if(Liquid)Liquid->SetVisibility(false);if(Stopper)Stopper->SetVisibility(false);
    if(FallbackHands)FallbackHands->SetVisibility(false);
}
void UFPSPotionUseComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    Finish();LoadHandle.Reset();Super::EndPlay(Reason);
}
