#include "DealerEnchantmentComponent.h"
#include "ColdSteelEnchantmentCombat.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelEnhancementSystem.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "Camera/CameraComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/AudioComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/StaticMesh.h"
#include "Engine/StreamableManager.h"
#include "Engine/GameInstance.h"
#include "Engine/GameViewportClient.h"
#include "Engine/LocalPlayer.h"
#include "GameFramework/PlayerController.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"
#include "SceneView.h"

UDealerEnchantmentComponent::UDealerEnchantmentComponent()
{
    SetIsReplicatedByDefault(true);
    PrimaryComponentTick.bCanEverTick=true;
    PrimaryComponentTick.bStartWithTickEnabled=false;
    PrimaryComponentTick.TickGroup=TG_PostUpdateWork;
}

void UDealerEnchantmentComponent::Configure(UColdSteelStatusModel* Profile)
{
    TArray<FString> Next;
    if(Profile&&!Profile->ActiveProductionTool())
    {
        const auto* E=GetOwner()->GetGameInstance()->GetSubsystem<UColdSteelEnhancementSystem>();
        const auto* Main=Profile->Equipped();
        if(ColdSteelCombat::Dealer(E,Main).Enabled)Next.Add(Main->InstanceId);
        if(Main&&(ColdSteelInventory::IsDualPistol(*Main)||ColdSteelInventory::Text(*Main,TEXT("weaponType"))==TEXT("staff")))
            if(const auto* Off=Profile->Equipped(Main->Cell==6?8:11);ColdSteelCombat::Dealer(E,Off).Enabled)Next.AddUnique(Off->InstanceId);
    }
    for(auto It=Hands.CreateIterator();It;++It)if(!Next.Contains(It.Key()))It.RemoveCurrent();
    EquippedInstances=MoveTemp(Next);
    if(!EquippedInstances.Contains(VisibleInstance))
    {VisibleCards.Reset();VisibleInstance.Reset();SelectedMask=0;bResult=bCardsSettled=false;HideDisplay();}
    const auto* Pawn=Cast<APawn>(GetOwner());
    SetComponentTickInterval(Pawn&&Pawn->IsLocallyControlled()?0.f:.2f);
    SetComponentTickEnabled(!EquippedInstances.IsEmpty());
    if(!EquippedInstances.IsEmpty())RequestAssets();
}

float UDealerEnchantmentComponent::Hit(const FString& Instance,const DealerPoker::FShot& Shot,bool bCritical)
{
    if(!GetOwner()->HasAuthority()||!Shot.Enabled||!EquippedInstances.Contains(Instance))return 1.f;
    auto& Hand=Hands.FindOrAdd(Instance);
    if(Hand.IsEmpty())
    {
        Hand.Reserve(DealerPoker::HoldemCardCount);
        for(int32 I=0;I<DealerPoker::HoleCardCount;++I)
            Hand.Add(DealerPoker::Draw(Hand,false,DealerPoker::HoldemCardCount));
    }
    Hand.Add(DealerPoker::Draw(Hand,bCritical,DealerPoker::HoldemCardCount));
    const bool Settled=Hand.Num()==DealerPoker::HoldemCardCount;
    TArray<uint8> BestFive;
    const auto Result=Settled?DealerPoker::EvaluateBest(Hand,BestFive):DealerPoker::EHand::HighCard;
    uint8 WinningSlots=0;
    if(Settled)
        for(int32 I=0;I<Hand.Num();++I)
            if(BestFive.Contains(Hand[I]))WinningSlots|=uint8(1u<<I);
    const float Multiplier=Settled?Shot.Multipliers[uint8(Result)]:1.f;
    // Send the dealt order unchanged; the seven-bit mask identifies the exact five used for damage.
    ClientHand(Instance,Hand,WinningSlots,uint8(Result),Settled);
    // Consume before damage callbacks; the fifth hit completes five board cards plus two hole cards.
    if(Settled)Hand.Reset(DealerPoker::HoldemCardCount);
    return Multiplier;
}

void UDealerEnchantmentComponent::ClientHand_Implementation(const FString& Instance,const TArray<uint8>& Hand,uint8 InSelectedMask,uint8 Result,bool Settled)
{
    if(!EquippedInstances.Contains(Instance))return;
    if(VisibleInstance!=Instance||Hand.Num()==DealerPoker::HoleCardCount+1)HoleRevealAge=0.f;
    VisibleInstance=Instance;VisibleCards=Hand;bCardsSettled=Settled;
    SelectedMask=Settled?InSelectedMask:0;
    // The last result has its own lifetime, so firing the next round never truncates the title or burst.
    if(Settled)
    {
        StopResultAudio();
        VisibleResult=Result;bResult=true;ResultAge=0.f;
        bPendingHighLaugh=Result>=uint8(DealerPoker::EHand::FullHouse);
    }
    RevealAge=0.f;
    RequestAssets();UpdateMaterials();
}

void UDealerEnchantmentComponent::RequestAssets()
{
    const auto* Pawn=Cast<APawn>(GetOwner());
    if(!Pawn||!Pawn->IsLocallyControlled()||bLoading||CardMesh)return;
    const TArray<FSoftObjectPath> Paths={
        FSoftObjectPath(TEXT("/Game/Weapons/Dealer20261004/Meshes/SM_DealerCard.SM_DealerCard")),
        FSoftObjectPath(TEXT("/Game/Weapons/Dealer20261004/Meshes/SM_DealerResult.SM_DealerResult")),
        FSoftObjectPath(TEXT("/Game/Weapons/Dealer20261004/Materials/M_DealerFace.M_DealerFace")),
        FSoftObjectPath(TEXT("/Game/Weapons/Dealer20261004/Materials/M_DealerBack.M_DealerBack")),
        FSoftObjectPath(TEXT("/Game/Weapons/Dealer20261004/Materials/M_DealerEdge.M_DealerEdge")),
        FSoftObjectPath(TEXT("/Game/Weapons/Dealer20261004/InfernalV2/Materials/M_DealerInfernalTitle.M_DealerInfernalTitle")),
        FSoftObjectPath(TEXT("/Game/Weapons/Dealer20261004/InfernalV2/Materials/M_DealerInfernalBurst.M_DealerInfernalBurst")),
        FSoftObjectPath(TEXT("/Game/Weapons/Dealer20261004/Audio/S_Dealer_DemonLaugh.S_Dealer_DemonLaugh")),
        FSoftObjectPath(TEXT("/Game/Weapons/Dealer20261004/SelectionV5/Materials/M_DealerSelectedFlame.M_DealerSelectedFlame"))};
    bLoading=true;
    AssetHandle=UAssetManager::GetStreamableManager().RequestAsyncLoad(Paths,FStreamableDelegate::CreateWeakLambda(this,[this,Paths]()
    {
        CardMesh=Cast<UStaticMesh>(Paths[0].ResolveObject());BadgeMesh=Cast<UStaticMesh>(Paths[1].ResolveObject());
        FaceMaterial=Cast<UMaterialInterface>(Paths[2].ResolveObject());BackMaterial=Cast<UMaterialInterface>(Paths[3].ResolveObject());
        EdgeMaterial=Cast<UMaterialInterface>(Paths[4].ResolveObject());BadgeMaterial=Cast<UMaterialInterface>(Paths[5].ResolveObject());
        BurstMaterial=Cast<UMaterialInterface>(Paths[6].ResolveObject());
        ResultLaugh=Cast<USoundBase>(Paths[7].ResolveObject());
        SelectedFlameMaterial=Cast<UMaterialInterface>(Paths[8].ResolveObject());
        // Failed requests are not retried per hit or frame.
        if(CardMesh&&BadgeMesh&&FaceMaterial&&BackMaterial&&EdgeMaterial&&BadgeMaterial&&BurstMaterial&&SelectedFlameMaterial)CreateDisplay();
    }));
}

void UDealerEnchantmentComponent::CreateDisplay()
{
    if(!Cards.IsEmpty())return;
    const auto Make=[&](const TCHAR* Name,UStaticMesh* Mesh)
    {
        auto* C=NewObject<UStaticMeshComponent>(GetOwner(),Name);
        C->SetMobility(EComponentMobility::Movable);C->SetStaticMesh(Mesh);
        C->SetCollisionEnabled(ECollisionEnabled::NoCollision);C->SetGenerateOverlapEvents(false);
        C->SetCastShadow(false);C->SetOnlyOwnerSee(true);C->SetVisibleInRayTracing(false);
        C->SetHiddenInGame(true);C->SetCanEverAffectNavigation(false);
        C->SetupAttachment(GetOwner()->GetRootComponent());C->RegisterComponent();
        return C;
    };
    const int32 FrontSlot=CardMesh->GetMaterialIndex(TEXT("DealerFace"));
    const int32 BackSlot=CardMesh->GetMaterialIndex(TEXT("DealerBack"));
    const int32 EdgeSlot=CardMesh->GetMaterialIndex(TEXT("DealerEdge"));
    for(int32 I=0;I<DealerPoker::HoldemCardCount;++I)
    {
        const FString Name=FString::Printf(TEXT("DealerCard%d"),I);
        auto* C=Make(*Name,CardMesh);Cards.Add(C);
        auto* Face=UMaterialInstanceDynamic::Create(FaceMaterial,this);Faces.Add(Face);C->SetMaterial(FrontSlot,Face);
        auto* Back=UMaterialInstanceDynamic::Create(BackMaterial,this);Backs.Add(Back);C->SetMaterial(BackSlot,Back);
        auto* Edge=UMaterialInstanceDynamic::Create(EdgeMaterial,this);Edges.Add(Edge);C->SetMaterial(EdgeSlot,Edge);
        C->SetTranslucentSortPriority(100+I);
        const FString FlameName=FString::Printf(TEXT("DealerSelectedFlame%d"),I);
        auto* Flame=Make(*FlameName,BadgeMesh);SelectedFlames.Add(Flame);
        auto* FlameMID=UMaterialInstanceDynamic::Create(SelectedFlameMaterial,this);SelectedFlameMIDs.Add(FlameMID);
        Flame->SetMaterial(0,FlameMID);Flame->SetTranslucentSortPriority(110+I);
    }
    Badge=Make(TEXT("DealerResult"),BadgeMesh);
    BadgeMID=UMaterialInstanceDynamic::Create(BadgeMaterial,this);Badge->SetMaterial(0,BadgeMID);
    Badge->SetTranslucentSortPriority(120);
    Burst=Make(TEXT("DealerInfernalBurst"),BadgeMesh);
    BurstMID=UMaterialInstanceDynamic::Create(BurstMaterial,this);Burst->SetMaterial(0,BurstMID);
    Burst->SetTranslucentSortPriority(99);
    Camera=GetOwner()->FindComponentByClass<UCameraComponent>();
    UpdateMaterials();
}

void UDealerEnchantmentComponent::UpdateMaterials()
{
    for(int32 I=0;I<Cards.Num();++I)
    {
        Cards[I]->SetHiddenInGame(!VisibleCards.IsValidIndex(I));
        if(VisibleCards.IsValidIndex(I))
        {
            Faces[I]->SetScalarParameterValue(TEXT("CardIndex"),VisibleCards[I]);
            const bool Selected=bCardsSettled&&(SelectedMask&(1u<<I))!=0;
            Faces[I]->SetScalarParameterValue(TEXT("ResultGlow"),Selected?.16f:0.f);
            SelectedFlameMIDs[I]->SetScalarParameterValue(TEXT("Seed"),float(VisibleCards[I])*2.399963f+I*.731f);
        }
        SelectedFlames[I]->SetHiddenInGame(!VisibleCards.IsValidIndex(I)||!bCardsSettled||(SelectedMask&(1u<<I))==0);
    }
    if(Badge){Badge->SetHiddenInGame(!bResult);BadgeMID->SetScalarParameterValue(TEXT("CardIndex"),VisibleResult);}
    const float Tier=VisibleResult>=uint8(DealerPoker::EHand::FullHouse)?VisibleResult-5.f:0.f;
    if(BadgeMID)BadgeMID->SetScalarParameterValue(TEXT("Tier"),Tier);
    if(Burst){Burst->SetHiddenInGame(!bResult||Tier==0.f);BurstMID->SetScalarParameterValue(TEXT("Tier"),Tier);}
}

void UDealerEnchantmentComponent::HideDisplay()
{
    for(const auto& C:Cards)C->SetHiddenInGame(true);
    for(const auto& C:SelectedFlames)C->SetHiddenInGame(true);
    if(Badge)Badge->SetHiddenInGame(true);
    if(Burst)Burst->SetHiddenInGame(true);
    bPendingHighLaugh=false;StopResultAudio();
    bHaveYaw=false;
}

void UDealerEnchantmentComponent::StopResultAudio()
{
    if(IsValid(LaughAudio))LaughAudio->Stop();
    LaughAudio=nullptr;
}

void UDealerEnchantmentComponent::PlayHighResultAudio(float Tier,float DisplayAge)
{
    const auto* Pawn=Cast<APawn>(GetOwner());
    if(!Pawn||!Pawn->IsLocallyControlled()||!ResultLaugh)return;
    // One owner-local voice follows the camera effect; no world attenuation or gameplay RNG.
    const float Pitch=Tier>=3.f?.90f:(Tier>=2.f?.96f:1.f);
    const float Volume=Tier>=3.f?.85f:(Tier>=2.f?.75f:.65f);
    const float StartTime=DisplayAge*Pitch;
    if(StartTime>=ResultLaugh->GetDuration())return;
    StopResultAudio();
    LaughAudio=UGameplayStatics::CreateSound2D(this,ResultLaugh,Volume,Pitch,StartTime,nullptr,false,true);
    if(LaughAudio)
    {
        LaughAudio->bIsUISound=false;
        LaughAudio->Play(StartTime);
    }
}

void UDealerEnchantmentComponent::TickComponent(float Delta,ELevelTick TickType,FActorComponentTickFunction* Tick)
{
    Super::TickComponent(Delta,TickType,Tick);
    if(const auto* H=GetOwner()->FindComponentByClass<UFPSCombatHealthComponent>();H&&H->IsDead())
    {Hands.Reset();VisibleCards.Reset();VisibleInstance.Reset();SelectedMask=0;bResult=bCardsSettled=false;HideDisplay();return;}
    const auto* Pawn=Cast<APawn>(GetOwner());
    if(!Pawn||!Pawn->IsLocallyControlled())return;
    FloatAge=FMath::Fmod(FloatAge+Delta,3600.f);
    if(VisibleCards.IsEmpty()&&!bResult)return;
    auto* PC=Cast<APlayerController>(Pawn->GetController());
    if(!PC||PC->GetViewTarget()!=Pawn){HideDisplay();return;}
    RevealAge+=Delta;
    HoleRevealAge+=Delta;
    const float Tier=VisibleResult>=uint8(DealerPoker::EHand::FullHouse)?VisibleResult-5.f:0.f;
    const float ResultDuration=Tier>0.f?3.f:2.4f;
    if(bResult)
    {
        ResultAge+=Delta;
        if(ResultAge>=ResultDuration)
        {bResult=false;bPendingHighLaugh=false;StopResultAudio();if(Badge)Badge->SetHiddenInGame(true);if(Burst)Burst->SetHiddenInGame(true);}
    }
    if(bCardsSettled&&RevealAge>=2.2f)
    {
        VisibleCards.Reset();SelectedMask=0;bCardsSettled=false;
        for(const auto& C:Cards)C->SetHiddenInGame(true);
        for(const auto& C:SelectedFlames)C->SetHiddenInGame(true);
    }
    if(VisibleCards.IsEmpty()&&!bResult){HideDisplay();return;}
    if(Cards.IsEmpty()||!Camera.IsValid())return;
    const auto* Local=PC->GetLocalPlayer();
    FSceneViewProjectionData Projection;
    if(!Local||!Local->ViewportClient||!Local->GetProjectionData(Local->ViewportClient->Viewport,Projection))return;
    const float TanH=1.f/FMath::Max(.01f,float(Projection.ProjectionMatrix.M[0][0]));
    const float TanV=1.f/FMath::Max(.01f,float(Projection.ProjectionMatrix.M[1][1]));
    FVector Eye;FRotator View;PC->GetPlayerViewPoint(Eye,View);
    const FQuat Rotation=View.Quaternion();
    const FVector Forward=Rotation.GetAxisX(),Right=Rotation.GetAxisY(),Up=Rotation.GetAxisZ();
    const float YawVelocity=bHaveYaw?FMath::FindDeltaAngleDegrees(LastYaw,View.Yaw)/FMath::Max(.001f,Delta):0.f;
    LastYaw=View.Yaw;bHaveYaw=true;
    const float TargetSway=FMath::Clamp(-YawVelocity*.012f+FVector::DotProduct(Pawn->GetVelocity(),Right)*.003f,-3.f,3.f);
    Sway=FMath::FInterpTo(Sway,TargetSway,Delta,9.f);
    constexpr float Depth=80.f;
    // Two centered upper hole slots and five fixed lower board slots retain their dealt positions.
    // A 7.55 cm pitch and 11.5 cm row gap leave air around the card-edge flames and bounded hover.
    const float Scale=FMath::Min(Depth*TanH*.52f/37.7f,Depth*TanV*.25f/10.f);
    const float Fade=bCardsSettled?1.f-FMath::Clamp((RevealAge-1.65f)/.55f,0.f,1.f):1.f;
    const FVector RowCenter=Eye+Forward*Depth-Right*(Depth*TanH*.65f)-Up*(Depth*TanV*.13f);
    for(int32 I=0;I<VisibleCards.Num();++I)
    {
        if(Cards[I]->bHiddenInGame)Cards[I]->SetHiddenInGame(false);
        const bool Hole=I<DealerPoker::HoleCardCount;
        const float Offset=Hole?float(I)-.5f:float(I-DealerPoker::HoleCardCount)-2.f;
        const float Seed=float(VisibleCards[I])*2.399963f+I*.731f;
        const float Bob=FMath::Sin(FloatAge*(1.45f+.09f*(VisibleCards[I]%7))+Seed)*(.28f+.025f*(VisibleCards[I]%5));
        const bool Newest=I==VisibleCards.Num()-1;
        const float EntryAge=Hole?HoleRevealAge:RevealAge;
        const float Enter=(Hole||Newest)?1.f-FMath::Pow(1.f-FMath::Clamp(EntryAge/.28f,0.f,1.f),3.f):1.f;
        const FVector Position=RowCenter+Right*(Offset*7.55f*Scale)+Up*(Scale*((Hole?11.5f:0.f)+Bob-(1.f-Enter)*1.6f))
            +Forward*(Scale*.16f*FMath::Sin(FloatAge*.9f+Seed));
        const FQuat Hover=FQuat(Forward,FMath::DegreesToRadians(Sway*.32f+.45f*FMath::Sin(FloatAge*.81f+Seed)))
            *FQuat(Up,FMath::DegreesToRadians(-5.f+1.f*FMath::Sin(FloatAge*.67f+Seed)-(1.f-Enter)*28.f));
        const FQuat CardRotation=Hover*Rotation;
        Cards[I]->SetWorldTransform(FTransform(CardRotation,Position,FVector(Scale)));
        Faces[I]->SetScalarParameterValue(TEXT("Reveal"),Fade*Enter);
        Backs[I]->SetScalarParameterValue(TEXT("Reveal"),Fade*Enter);
        Edges[I]->SetScalarParameterValue(TEXT("Reveal"),Fade*Enter);
        const bool Selected=bCardsSettled&&(SelectedMask&(1u<<I))!=0;
        auto* Flame=SelectedFlames[I].Get();
        Flame->SetHiddenInGame(!Selected);
        if(Selected)
        {
            // Reuse the authored YZ result quad, with the same rotation as the card and a tiny eye-side offset.
            Flame->SetWorldTransform(FTransform(CardRotation,Position-CardRotation.GetAxisX()*(.10f*Scale),
                FVector(Scale,Scale*7.5f/20.f,Scale*10.4f/3.5f)));
            SelectedFlameMIDs[I]->SetScalarParameterValue(TEXT("Age"),RevealAge);
            SelectedFlameMIDs[I]->SetScalarParameterValue(TEXT("Reveal"),Fade*Enter);
        }
    }
    if(bResult&&Badge)
    {
        if(Badge->bHiddenInGame)Badge->SetHiddenInGame(false);
        const float ResultFade=1.f-FMath::Clamp((ResultAge-(ResultDuration-.6f))/.6f,0.f,1.f);
        const float Appear=1.f-FMath::Pow(1.f-FMath::Clamp(ResultAge/.22f,0.f,1.f),3.f);
        const float TitlePulse=1.f+.045f*FMath::Exp(-ResultAge*3.f)*FMath::Sin(ResultAge*11.f);
        // The transparent glyph plane has a 4:1 tile; no plaque, panel or border.
        const FVector TitleCenter=RowCenter-Forward*(2.f*Scale)-Up*(8.4f*Scale);
        Badge->SetWorldTransform(FTransform(Rotation,TitleCenter,FVector(Scale,Scale*1.8f*TitlePulse,Scale*2.57f*TitlePulse)));
        BadgeMID->SetScalarParameterValue(TEXT("Reveal"),ResultFade*Appear);
        BadgeMID->SetScalarParameterValue(TEXT("Age"),ResultAge);
        if(Tier>0.f&&Burst)
        {
            if(Burst->bHiddenInGame)Burst->SetHiddenInGame(false);
            Burst->SetWorldTransform(FTransform(Rotation,TitleCenter+Forward*(.8f*Scale)+Up*(2.6f*Scale),
                FVector(Scale,Scale*2.1f,Scale*6.f)));
            BurstMID->SetScalarParameterValue(TEXT("Reveal"),ResultFade*Appear);
            BurstMID->SetScalarParameterValue(TEXT("Age"),ResultAge);
            if(bPendingHighLaugh)
            {
                // Start on the first frame that actually displays the burst, never on each draw/tick.
                bPendingHighLaugh=false;
                PlayHighResultAudio(Tier,FMath::Max(0.f,ResultAge-Delta));
            }
        }
    }
}

void UDealerEnchantmentComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    bPendingHighLaugh=false;StopResultAudio();
    if(AssetHandle)AssetHandle->CancelHandle();AssetHandle.Reset();
    for(const auto& C:Cards)if(C)C->DestroyComponent();Cards.Reset();
    for(const auto& C:SelectedFlames)if(C)C->DestroyComponent();SelectedFlames.Reset();SelectedFlameMIDs.Reset();
    if(Badge)Badge->DestroyComponent();
    if(Burst)Burst->DestroyComponent();
    Super::EndPlay(Reason);
}
