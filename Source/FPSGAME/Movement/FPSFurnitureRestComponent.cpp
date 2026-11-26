#include "FPSFurnitureRestComponent.h"
#include "../FPSGAMECharacter.h"
#include "../FPSGAMEPlayerController.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "../Characters/FPSPlayerBodyAnimInstance.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../UI/ColdSteelWorldInteraction.h"
#include "Components/StaticMeshComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/CapsuleComponent.h"
#include "Camera/CameraComponent.h"
#include "Camera/CameraTypes.h"
#include "Animation/AnimSequence.h"
#include "Engine/StaticMesh.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Materials/MaterialInterface.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/GameStateBase.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/PlayerState.h"
#include "Net/UnrealNetwork.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"
#include "Dom/JsonObject.h"

DEFINE_LOG_CATEGORY_STATIC(LogFurnitureRest,Log,All);

namespace FurnitureRest
{
struct FSlot { FVector Seat,Focus; float Yaw=90.f; FName Kind; FString Label; bool bMirror=false; };
struct FProfile
{
    FString Caption;
    TArray<FSlot> Slots;
    FVector Scale=FVector::OneVector;
    TArray<FName> FittedComponentTags;
    bool bAutoSelectFreeSlot=false, bBackless=false, bEitherBedSide=false;
};
struct FClip { float Duration=1.f; TArray<FVector> Eyes; TArray<float> Pitches,Yaws; };
struct FType { float SurfaceHeight=0.f,EntryYaw=0.f; FVector EntryOffset=FVector::ZeroVector; bool bLying=false; };
FVector EntryOffset(const FType& Type,bool bMirror)
{FVector V=Type.EntryOffset;if(bMirror)V.Y=-V.Y;return V;}
float EntryYaw(const FType& Type,bool bMirror){return bMirror?-Type.EntryYaw:Type.EntryYaw;}
struct FLibrary
{
    TMap<FString,FProfile> Profiles;
    TMap<FName,FClip> Clips;
    TMap<FName,FType> Types;
    TArray<TWeakObjectPtr<UFPSFurnitureRestComponent>> Occupants;
    FLibrary()
    {
        Load(TEXT("furniture_rest.json"));
        Load(TEXT("apartment_furniture_rest.json"));
        Load(TEXT("village_furniture_rest.json"));
    }
    void Load(const TCHAR* File)
    {
        FString Text;TSharedPtr<FJsonObject> Json;
        if(!FFileHelper::LoadFileToString(Text,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData")/File))||
            !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Json)||!Json)return;
        if(!Json->HasTypedField<EJson::Object>(TEXT("types")))return;
        const auto Vec=[](const TArray<TSharedPtr<FJsonValue>>& A){return FVector(A[0]->AsNumber(),A[1]->AsNumber(),A[2]->AsNumber());};
        for(const auto& Pair:Json->GetObjectField(TEXT("types"))->Values)
        {
            const auto O=Pair.Value->AsObject();FType T;T.SurfaceHeight=O->GetNumberField(TEXT("surface_height"));
            T.EntryYaw=O->GetNumberField(TEXT("entry_yaw"));T.bLying=O->GetBoolField(TEXT("lying"));
            const FVector V=Vec(O->GetArrayField(TEXT("entry_offset")));T.EntryOffset=FVector(V.Y,-V.X,V.Z);
            Types.Add(FName(*Pair.Key),T);
        }
        for(const auto& Value:Json->GetArrayField(TEXT("furniture")))
        {
            const auto O=Value->AsObject();FProfile P;P.Caption=O->GetStringField(TEXT("caption"));
            if(O->HasTypedField<EJson::Array>(TEXT("scale")))P.Scale=Vec(O->GetArrayField(TEXT("scale")));
            O->TryGetBoolField(TEXT("auto_select_free_slot"),P.bAutoSelectFreeSlot);
            O->TryGetBoolField(TEXT("backless"),P.bBackless);
            O->TryGetBoolField(TEXT("either_bed_side"),P.bEitherBedSide);
            const TArray<TSharedPtr<FJsonValue>>* Tags=nullptr;
            if(O->TryGetArrayField(TEXT("fitted_component_tags"),Tags))
                for(const auto& Tag:*Tags)P.FittedComponentTags.Add(FName(*Tag->AsString()));
            for(const auto& V:O->GetArrayField(TEXT("slots")))
            {
                const auto S=V->AsObject();FSlot Slot;Slot.Seat=Vec(S->GetArrayField(TEXT("seat")));Slot.Focus=Slot.Seat;
                if(S->HasTypedField<EJson::Array>(TEXT("focus")))Slot.Focus=Vec(S->GetArrayField(TEXT("focus")));
                Slot.Yaw=S->GetNumberField(TEXT("yaw"));Slot.Kind=FName(*S->GetStringField(TEXT("kind")));
                S->TryGetBoolField(TEXT("mirror"),Slot.bMirror);S->TryGetStringField(TEXT("label"),Slot.Label);P.Slots.Add(MoveTemp(Slot));
            }
            Profiles.Add(O->GetStringField(TEXT("mesh")),MoveTemp(P));
        }
        for(const auto& Pair:Json->GetObjectField(TEXT("clips"))->Values)
        {
            const auto O=Pair.Value->AsObject();FClip C;C.Duration=O->GetNumberField(TEXT("duration"));
            for(const auto& V:O->GetArrayField(TEXT("camera")))
            {const auto& A=V->AsArray();C.Eyes.Add(Vec(A));C.Pitches.Add(A[3]->AsNumber());C.Yaws.Add(A.Num()>4?A[4]->AsNumber():0.f);}
            Clips.Add(FName(*Pair.Key),MoveTemp(C));
        }
    }
};
FLibrary& Library(UWorld* World)
{
    // A new play world must read the newly published timing and entry anchors.
    // Keep file reads out of focus/camera ticks and do not change an active rest.
    static TMap<TWeakObjectPtr<UWorld>,TSharedPtr<FLibrary>> Libraries;
    const TWeakObjectPtr<UWorld> Key(World);
    if(const auto* Found=Libraries.Find(Key))return **Found;
    for(auto It=Libraries.CreateIterator();It;++It)if(!It.Key().IsValid())It.RemoveCurrent();
    const auto Data=MakeShared<FLibrary>();Libraries.Add(Key,Data);return *Data;
}
float Ease(float T){T=FMath::Clamp(T,0.f,1.f);return T*T*(3.f-2.f*T);}
FName ClipKey(FName Kind,const TCHAR* Phase){return FName(FString::Printf(TEXT("Rest.%s.%s"),*Kind.ToString(),Phase));}
float Duration(UWorld* World,FName Kind,const TCHAR* Phase)
{const auto* C=Library(World).Clips.Find(ClipKey(Kind,Phase));return C?C->Duration:1.f;}
}

UFPSFurnitureRestComponent::UFPSFurnitureRestComponent()
{
    PrimaryComponentTick.bCanEverTick=true;PrimaryComponentTick.TickGroup=TG_PrePhysics;
    PrimaryComponentTick.bStartWithTickEnabled=false;SetIsReplicatedByDefault(true);
}
void UFPSFurnitureRestComponent::BeginPlay()
{
    Super::BeginPlay();Character=Cast<AFPSGAMECharacter>(GetOwner());
    (void)FurnitureRest::Library(GetWorld());
    if(Character.IsValid())Character->GetCharacterMovement()->AddTickPrerequisiteComponent(this);
    // Initial replicated state can arrive before this component's BeginPlay.
    if(IsResting())ApplyState();
    if(Character.IsValid()&&Character->IsLocallyControlled())
        OutlineLoad=UAssetManager::GetStreamableManager().RequestAsyncLoad(
            FSoftObjectPath(TEXT("/Game/Dungeons/StaffLiving20261002/ScenePolishV4/Materials/M_Staff_ContainerOutline_V4.M_Staff_ContainerOutline_V4")),
            FStreamableDelegate::CreateUObject(this,&ThisClass::OutlineLoaded));
}
void UFPSFurnitureRestComponent::OutlineLoaded()
{
    OutlineMaterial=Cast<UMaterialInterface>(FSoftObjectPath(TEXT("/Game/Dungeons/StaffLiving20261002/ScenePolishV4/Materials/M_Staff_ContainerOutline_V4.M_Staff_ContainerOutline_V4")).ResolveObject());
    if(OutlineMaterial&&Character.IsValid()&&Character->FirstPersonCamera)
        Character->FirstPersonCamera->AddOrUpdateBlendable(OutlineMaterial,1.f);
}
bool UFPSFurnitureRestComponent::IsResting(const AActor* Actor)
{const auto* Rest=Actor?Actor->FindComponentByClass<UFPSFurnitureRestComponent>():nullptr;return Rest&&Rest->IsResting();}
bool UFPSFurnitureRestComponent::IsRestingInBed() const
{
    if(State.Phase!=3)return false;
    const auto* Type=FurnitureRest::Library(GetWorld()).Types.Find(State.Kind);
    return Type&&Type->bLying;
}
void UFPSFurnitureRestComponent::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{Super::GetLifetimeReplicatedProps(OutLifetimeProps);DOREPLIFETIME(UFPSFurnitureRestComponent,State);}
float UFPSFurnitureRestComponent::Clock() const
{const auto* GS=GetWorld()->GetGameState();return GS?GS->GetServerWorldTimeSeconds():GetWorld()->GetTimeSeconds();}
float UFPSFurnitureRestComponent::PhaseDuration() const
{
    if(State.Phase==1)return .6f;
    return FurnitureRest::Duration(GetWorld(),State.Kind,State.Phase==4?TEXT("Exit"):State.Phase==3?TEXT("Idle"):TEXT("Enter"));
}
bool UFPSFurnitureRestComponent::ResolveFocus(FHitResult& Hit,FTransform& Transform,int32& Slot,FName& Kind,FVector& Seat,float& Yaw,bool& bOccupied) const
{
    bOccupied=false;
    const auto* Pawn=Character.Get();const auto* PC=Pawn?Cast<APlayerController>(Pawn->GetController()):nullptr;
    if(!PC||PC->bShowMouseCursor)return false;
    // A remote controller's camera cache can lag behind its authoritative pawn.
    // Use the same server eye/aim contract as door reach; keep local camera modes.
    FVector Eye=Pawn->GetMeleeAimTransform().GetLocation();FRotator View=Pawn->GetControlRotation();
    if(Pawn->IsLocallyControlled())ColdSteelWorldInteraction::GetReachViewPoint(PC,Eye,View);
    FCollisionQueryParams Q(SCENE_QUERY_STAT(FurnitureRestFocus),false,Pawn);
    if(!GetWorld()->LineTraceSingleByChannel(Hit,Eye,Eye+View.Vector()*250.f,ECC_Visibility,Q))return false;
    const auto* Mesh=Cast<UStaticMeshComponent>(Hit.GetComponent());
    if(!Mesh||!Mesh->GetStaticMesh())return false;
    const auto* Profile=FurnitureRest::Library(GetWorld()).Profiles.Find(Mesh->GetStaticMesh()->GetPathName());
    if(!Profile)return false;
    Transform=Mesh->GetComponentTransform();
    if(const auto* Instances=Cast<UInstancedStaticMeshComponent>(Mesh))
    {
        if(Hit.Item<0||!Instances->GetInstanceTransform(Hit.Item,Transform,true))return false;
    }
    else Hit.Item=INDEX_NONE; // Only instanced meshes use the collision item as a furniture identity.
    // Fallen/scattered furniture is scenery, never an upside-down rest anchor.
    if(FVector::DotProduct(Transform.GetUnitAxis(EAxis::Z),FVector::UpVector)<.96f)return false;
    // Furniture size is explicit in its profile; the pawn and bone lengths stay native.
    if(Profile->FittedComponentTags.IsEmpty())
    {
        if(!Transform.GetScale3D().Equals(Profile->Scale,.02f))return false;
    }
    else if(Transform.GetScale3D().GetMin()<=0. ||
        !Profile->FittedComponentTags.ContainsByPredicate([Mesh](FName Tag){return Mesh->ComponentHasTag(Tag);}))return false;
    float Best=TNumericLimits<float>::Max(),BestFree=Best;Slot=INDEX_NONE;int32 FreeSlot=INDEX_NONE;
    TBitArray<TInlineAllocator<1>> Occupied(false,Profile->Slots.Num());
    const bool bAuthority=GetOwner()->HasAuthority();
    const auto RecordOccupied=[&](const UFPSFurnitureRestComponent* Other)
    {
        if(!Other||Other==this||!Other->IsResting())return;
        const int32 Index=Other->State.SlotIndex;
        if(!Profile->Slots.IsValidIndex(Index))return;
        if(bAuthority)
        {
            if(Other->ActiveMesh.Get()==Mesh&&Other->ActiveInstance==Hit.Item)Occupied[Index]=true;
        }
        else if(Other->State.SlotLocation.Equals(Transform.TransformPosition(Profile->Slots[Index].Focus),1.f))Occupied[Index]=true;
    };
    if(bAuthority)
    {
        for(const auto& Occupant:FurnitureRest::Library(GetWorld()).Occupants)
            RecordOccupied(Occupant.Get());
    }
    else if(const auto* GameState=GetWorld()->GetGameState())
    {
        for(const APlayerState* Player:GameState->PlayerArray)
            if(const auto* OtherPawn=Player?Player->GetPawn():nullptr)
                RecordOccupied(OtherPawn->FindComponentByClass<UFPSFurnitureRestComponent>());
    }
    for(int32 I=0;I<Profile->Slots.Num();++I)
    {
        const auto& S=Profile->Slots[I];const FVector P=Transform.TransformPosition(S.Focus);
        const float Distance=FVector::DistSquared(P,Hit.ImpactPoint);
        const bool Taken=Occupied[I];
        if(Distance<Best){Best=Distance;Slot=I;bOccupied=Taken;}
        if(!Taken&&Distance<BestFree){BestFree=Distance;FreeSlot=I;}
    }
    if(Slot==INDEX_NONE)return false;
    if(bOccupied&&Profile->bAutoSelectFreeSlot&&FreeSlot!=INDEX_NONE){Slot=FreeSlot;bOccupied=false;}
    const auto& Selected=Profile->Slots[Slot];Kind=Selected.Kind;Seat=Transform.TransformPosition(Selected.Seat);
    Yaw=Transform.Rotator().Yaw+Selected.Yaw;return true;
}
void UFPSFurnitureRestComponent::ClearFocus()
{
    FocusMesh.Reset();FocusInstance=FocusSlot=INDEX_NONE;
    CachedPrompt.Reset();LastFocusTime=-1.;
    if(Outline && Outline->GetStaticMesh())
    {
        Outline->SetVisibility(false);
        Outline->EmptyOverrideMaterials();
        Outline->SetStaticMesh(nullptr);
    }
}
FString UFPSFurnitureRestComponent::UpdateFocus(bool bAllowed)
{
    if(!Character.IsValid()||!Character->IsLocallyControlled()||!bAllowed){ClearFocus();return FString();}
    if(IsResting())
    {
        ClearFocus();
        return State.Phase==4?TEXT("起身中"):State.Phase==1||State.Phase==2?TEXT("就位中"):TEXT("起身离开");
    }
    const double Now=GetWorld()->GetTimeSeconds();
    if(LastFocusTime>=0.&&Now>=LastFocusTime&&Now-LastFocusTime<.06)return CachedPrompt;
    LastFocusTime=Now;
    FHitResult Hit;FTransform T;int32 Slot;FName Kind;FVector Seat;float Yaw;bool bOccupied;
    if(!ResolveFocus(Hit,T,Slot,Kind,Seat,Yaw,bOccupied)){ClearFocus();LastFocusTime=Now;return FString();}
    auto* Mesh=CastChecked<UStaticMeshComponent>(Hit.GetComponent());
    const auto& Profile=FurnitureRest::Library(GetWorld()).Profiles.FindChecked(Mesh->GetStaticMesh()->GetPathName());
    if(bOccupied){ClearFocus();LastFocusTime=Now;CachedPrompt=Profile.Caption+TEXT(" · 已被占用");return CachedPrompt;}
    if(FocusMesh!=Mesh||FocusInstance!=Hit.Item||!T.Equals(FocusTransform))
    {
        if(!Outline)
        {
            Outline=NewObject<UStaticMeshComponent>(GetOwner(),TEXT("FurnitureFocusOutline"),RF_Transient);
            GetOwner()->AddInstanceComponent(Outline);Outline->SetMobility(EComponentMobility::Movable);
            Outline->SetCollisionEnabled(ECollisionEnabled::NoCollision);Outline->SetGenerateOverlapEvents(false);
            Outline->SetCanEverAffectNavigation(false);Outline->SetCastShadow(false);
            Outline->SetRenderInMainPass(false);Outline->SetRenderInDepthPass(false);
            Outline->SetVisibleInRayTracing(false);Outline->SetOnlyOwnerSee(true);
            Outline->SetCustomDepthStencilValue(201);Outline->SetRenderCustomDepth(true);
            Outline->RegisterComponent();
        }
        Outline->EmptyOverrideMaterials();
        Outline->SetStaticMesh(Mesh->GetStaticMesh());
        for(int32 I=0;I<Mesh->GetNumMaterials();++I)Outline->SetMaterial(I,Mesh->GetMaterial(I));
        Outline->SetWorldTransform(T);
    }
    if(Outline)Outline->SetVisibility(true);
    FocusMesh=Mesh;FocusInstance=Hit.Item;FocusSlot=Slot;FocusTransform=T;
    const auto* Type=FurnitureRest::Library(GetWorld()).Types.Find(Kind);
    const FString& Label=Profile.Slots[Slot].Label;
    CachedPrompt=Profile.Caption+(Label.IsEmpty()?FString():TEXT(" · ")+Label)+(Type&&Type->bLying?TEXT(" · 躺下"):TEXT(" · 坐下"));return CachedPrompt;
}
bool UFPSFurnitureRestComponent::Interact()
{
    if(IsResting()){RequestLeave();return true;}
    FHitResult Hit;FTransform T;int32 Slot;FName Kind;FVector Seat;float Yaw;bool bOccupied;
    if(!ResolveFocus(Hit,T,Slot,Kind,Seat,Yaw,bOccupied))return false;
    if(bOccupied)return true;
    // Each initiating player owns presentation readiness. A listen server can
    // legitimately have the remote player's full-body animation unloaded.
    const auto* Body=Character->FindComponentByClass<UFPSPlayerBodyComponent>();
    const auto* Anim=Body&&Body->GetBodyMesh()?Cast<UFPSPlayerBodyAnimInstance>(Body->GetBodyMesh()->GetAnimInstance()):nullptr;
    if(!Anim)return true;
    for(const TCHAR* Phase:{TEXT("Enter"),TEXT("Idle"),TEXT("Exit")})
        if(!Anim->Clips.FindRef(FurnitureRest::ClipKey(Kind,Phase)))return true;
    if(GetOwner()->HasAuthority())StartRest();else ServerInteract();
    return true;
}
void UFPSFurnitureRestComponent::ServerInteract_Implementation(){StartRest();}
bool UFPSFurnitureRestComponent::ExitClear(const FVector& Position) const
{
    if(!Character.IsValid())return false;
    const auto* Cap=Character->GetCapsuleComponent();
    FCollisionQueryParams Q(SCENE_QUERY_STAT(FurnitureRestExit),false,GetOwner());
    return !GetWorld()->OverlapBlockingTestByChannel(Position,FQuat::Identity,ECC_Pawn,
        FCollisionShape::MakeCapsule(Cap->GetScaledCapsuleRadius(),Cap->GetScaledCapsuleHalfHeight()),Q);
}
bool UFPSFurnitureRestComponent::FindExit(const FTransform& Root,FVector& Exit,FName Kind,bool bMirror,bool bFitted) const
{
    const auto* Cap=Character->GetCapsuleComponent();const float H=Cap->GetScaledCapsuleHalfHeight();
    FCollisionQueryParams Q(SCENE_QUERY_STAT(FurnitureRestFloor),false,GetOwner());
    const auto* Type=FurnitureRest::Library(GetWorld()).Types.Find(Kind);if(!Type)return false;
    // The animation ends at its authored entry point; validate that destination.
    const FVector Candidate=Root.TransformPosition(FurnitureRest::EntryOffset(*Type,bMirror));
    FHitResult Floor;
    const float Up=bFitted?34.f:100.f, Down=bFitted?38.f:220.f;
    if(!GetWorld()->LineTraceSingleByChannel(Floor,Candidate+FVector(0,0,Up),Candidate-FVector(0,0,Down),ECC_Visibility,Q)
        ||Floor.ImpactNormal.Z<.7f)return false;
    // A standing spot on the other side of a wall or a table is not a usable transfer.
    if(bFitted)
    {
        const FVector Clearance(0,0,Type->bLying?98.:68.);
        if(GetWorld()->LineTraceTestByChannel(Root.GetLocation()+Clearance,Candidate+Clearance,ECC_Visibility,Q))return false;
    }
    const FVector P=Floor.ImpactPoint+FVector(0,0,H+2.f);
    if(!ExitClear(P))return false;
    Exit=P;return true;
}
void UFPSFurnitureRestComponent::StartRest()
{
    if(IsResting()||!Character.IsValid())return;
    auto* Pawn=Character.Get();const auto* PC=Cast<APlayerController>(Pawn->GetController());
    const auto* Health=Pawn->FindComponentByClass<UFPSCombatHealthComponent>();
    if(!PC||AFPSGAMEPlayerController::BlocksOngoingActions(PC)||(Health&&Health->IsDead())||
        !Pawn->GetCharacterMovement()->IsMovingOnGround()||Pawn->IsTraversing()||Pawn->bIsCrouched)
    {UE_LOG(LogFurnitureRest,Verbose,TEXT("Start denied pawn=%s controller=%d blocked=%d dead=%d grounded=%d traversal=%d crouched=%d"),*Pawn->GetName(),PC!=nullptr,PC&&AFPSGAMEPlayerController::BlocksOngoingActions(PC),Health&&Health->IsDead(),Pawn->GetCharacterMovement()->IsMovingOnGround(),Pawn->IsTraversing(),Pawn->bIsCrouched);return;}
    FHitResult Hit;FTransform T;int32 Slot;FName Kind;FVector Seat;float Yaw;bool bOccupied;
    if(!ResolveFocus(Hit,T,Slot,Kind,Seat,Yaw,bOccupied)||bOccupied)
    {UE_LOG(LogFurnitureRest,Verbose,TEXT("Start denied pawn=%s focus/occupied=%d"),*Pawn->GetName(),bOccupied);return;}
    const auto* TargetMesh=CastChecked<UStaticMeshComponent>(Hit.GetComponent());
    const auto& Profile=FurnitureRest::Library(GetWorld()).Profiles.FindChecked(TargetMesh->GetStaticMesh()->GetPathName());
    const auto& Selected=Profile.Slots[Slot];
    const auto* Type=FurnitureRest::Library(GetWorld()).Types.Find(Kind);if(!Type)return;
    const FVector Anchor=Seat-FVector(0,0,Type->SurfaceHeight);
    SavedTransform=Pawn->GetActorTransform();
    FFurnitureRestState Next;Next.Kind=Kind;Next.Root=FTransform(FRotator(0,Yaw,0),Anchor);
    Next.SlotIndex=Slot;Next.SlotLocation=T.TransformPosition(Selected.Focus);Next.bMirror=Selected.bMirror;
    const bool bFitted=!Profile.FittedComponentTags.IsEmpty();
    const float HalfHeight=Pawn->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
    FCollisionQueryParams Route(SCENE_QUERY_STAT(FurnitureRestApproach),false,Pawn);
    const auto TryRoute=[&](float Facing,bool bMirror)
    {
        const FTransform Root(FRotator(0,Facing,0),Anchor);
        FVector Exit;
        if(!FindExit(Root,Exit,Kind,bMirror,bFitted))return false;
        if(!Type->bLying&&GetWorld()->SweepTestByChannel(Pawn->GetActorLocation(),Exit,FQuat::Identity,ECC_Pawn,
            FCollisionShape::MakeCapsule(Pawn->GetCapsuleComponent()->GetScaledCapsuleRadius(),HalfHeight-2.f),Route))return false;
        Next.Root=Root;Next.Exit=Exit;Next.bMirror=bMirror;return true;
    };
    bool bFound=false;
    if(Profile.bEitherBedSide)
    {
        const auto Entry=[&](bool bMirror){return Next.Root.TransformPosition(FurnitureRest::EntryOffset(*Type,bMirror));};
        const bool bNearMirror=FVector::DistSquared2D(Pawn->GetActorLocation(),Entry(true))<FVector::DistSquared2D(Pawn->GetActorLocation(),Entry(false));
        bFound=TryRoute(Yaw,bNearMirror)||TryRoute(Yaw,!bNearMirror);
    }
    else if(Profile.bBackless)
    {
        // Try the installed orientation, then the two open sides of the table.
        const float ApproachYaw=(Pawn->GetActorLocation()-Seat).Rotation().Yaw;
        const float Side=FMath::FindDeltaAngleDegrees(Yaw,ApproachYaw)>=0.f?1.f:-1.f;
        for(float Offset:{0.f,60.f*Side,-60.f*Side,90.f*Side,-90.f*Side})
            if(TryRoute(Yaw+Offset,false)){bFound=true;break;}
        if(!bFound)bFound=TryRoute(ApproachYaw,false);
    }
    else bFound=TryRoute(Yaw,Selected.bMirror);
    if(!bFound)return;
    Next.GroundZ=Next.Exit.Z-Pawn->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()-2.f;
    if(bFitted&&!Type->bLying)
        Next.SeatFloorCorrection=FMath::Clamp(float(Anchor.Z-Next.GroundZ),-10.f,10.f);
    if(Type->bLying)
    {
        // The focus trace already validates reach and visibility, and FindExit
        // validates the destination. Beds reposition directly from any side.
        const FQuat EntryTurn(FVector::UpVector,FMath::DegreesToRadians(FurnitureRest::EntryYaw(*Type,Next.bMirror)));
        Next.Approach=FTransform(Next.Root.GetRotation()*EntryTurn,Next.Root.TransformPosition(FurnitureRest::EntryOffset(*Type,Next.bMirror)));
    }
    else
    {
        Next.Approach=FTransform(Pawn->GetActorRotation(),Pawn->GetActorLocation()-FVector(0,0,HalfHeight));
    }
    State=Next;ActiveMesh=Cast<UStaticMeshComponent>(Hit.GetComponent());ActiveInstance=Hit.Item;ActiveTransform=T;bActiveFitted=bFitted;
    FurnitureRest::Library(GetWorld()).Occupants.AddUnique(this);
    LastHealth=Health?Health->Health:0.f;
    UE_LOG(LogTemp,Display,TEXT("FurnitureRest: mesh=%s kind=%s slot=%d direct_bed_align=%d"),
        *GetNameSafe(ActiveMesh->GetStaticMesh()),*Kind.ToString(),Slot,Type->bLying);
    SetPhase(1);
}
void UFPSFurnitureRestComponent::SetPhase(uint8 Phase)
{State.Phase=Phase;State.Started=Clock();ApplyState();GetOwner()->ForceNetUpdate();}
void UFPSFurnitureRestComponent::RequestLeave()
{if(GetOwner()->HasAuthority())ServerLeave_Implementation();else ServerLeave();}
void UFPSFurnitureRestComponent::ServerLeave_Implementation()
{
    if(!IsResting()||State.Phase==4)return;
    // E during entry waits until the seated pose, avoiding a pose discontinuity.
    if(State.Phase!=3)return;
    FVector Exit;if(!FindExit(State.Root,Exit,State.Kind,State.bMirror,bActiveFitted))return;
    State.Exit=Exit;SetPhase(4);
}
void UFPSFurnitureRestComponent::OnRep_State(){ApplyState();}
void UFPSFurnitureRestComponent::ApplyState()
{
    if(!Character.IsValid())return;
    auto* Pawn=Character.Get();auto* Move=Pawn->GetCharacterMovement();
    if(IsResting()&&!bApplied)
    {
        bApplied=true;SavedCollision=Pawn->GetCapsuleComponent()->GetCollisionEnabled();
        // Rest begins on ground. A late replica may already have received MOVE_None.
        SavedMovement=Move->MovementMode==MOVE_None?uint8(MOVE_Walking):uint8(Move->MovementMode);bSavedControllerYaw=Pawn->bUseControllerRotationYaw;
        if(Pawn->IsLocallyControlled())Pawn->InterruptActionsForPriority(false);
        if(auto* PC=Cast<APlayerController>(Pawn->GetController()))
        {SavedControlRotation=PC->GetControlRotation();PC->SetIgnoreMoveInput(true);LockedController=PC;}
        BeginRestCamera();
        Pawn->bUseControllerRotationYaw=false;
        Move->StopMovementImmediately();Move->DisableMovement();
        Pawn->GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
        if(const auto* Type=FurnitureRest::Library(GetWorld()).Types.Find(State.Kind);Type&&Type->bLying&&State.Phase==1)
            Pawn->SetActorLocationAndRotation(State.Approach.GetLocation()+FVector(0,0,Pawn->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()),
                State.Approach.GetRotation(),false,nullptr,ETeleportType::TeleportPhysics);
        // Keep damage queries enabled. Movement is disabled; no capsule sweep drives the pose.
        SetComponentTickEnabled(true);ClearFocus();
    }
    else if(!IsResting()&&bApplied)
    {
        bApplied=false;
        const auto* Health=Pawn->FindComponentByClass<UFPSCombatHealthComponent>();
        const bool Dead=Health&&Health->IsDead();
        EndRestCamera(Dead);
        if(!Dead)Pawn->GetCapsuleComponent()->SetCollisionEnabled(SavedCollision);
        Pawn->bUseControllerRotationYaw=bSavedControllerYaw;
        if(!Dead)Move->SetMovementMode(EMovementMode(SavedMovement));
        if(auto* PC=Cast<APlayerController>(LockedController.Get()))PC->SetIgnoreMoveInput(false);
        LockedController.Reset();SetComponentTickEnabled(false);
    }
    if(auto* Body=Pawn->FindComponentByClass<UFPSPlayerBodyComponent>())Body->RefreshViewMode();
}
void UFPSFurnitureRestComponent::FinishRest()
{
    if(!Character.IsValid())return;
    FurnitureRest::Library(GetWorld()).Occupants.RemoveSingleSwap(this);
    Character->SetActorLocation(State.Exit,false,nullptr,ETeleportType::TeleportPhysics);
    SetPhase(0);ActiveMesh.Reset();
}
void UFPSFurnitureRestComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick)
{
    Super::TickComponent(Delta,Type,Tick);if(!Character.IsValid()||!IsResting())return;
    auto* Pawn=Character.Get();
    if(GetOwner()->HasAuthority())
    {
        const auto* Health=Pawn->FindComponentByClass<UFPSCombatHealthComponent>();
        bool Gone=!ActiveMesh.IsValid()||!ActiveMesh->IsQueryCollisionEnabled()||!ActiveMesh->GetOwner()->GetActorEnableCollision();
        if(!Gone)
        {
            FTransform Current=ActiveMesh->GetComponentTransform();
            if(const auto* Instances=Cast<UInstancedStaticMeshComponent>(ActiveMesh.Get()))
                Gone=!Instances->GetInstanceTransform(ActiveInstance,Current,true);
            Gone|=!Current.Equals(ActiveTransform,.5f);
        }
        if(Gone||!Pawn->GetController()||(Health&&Health->IsDead())){FinishRest();return;}
        if(Health&&Health->Health<LastHealth&&State.Phase==3)ServerLeave_Implementation();
        if(Health)LastHealth=Health->Health;
        // Damage may have just changed Idle to Exit and reset Started. Never
        // reuse the old idle age to finish the newly started exit this tick.
        const float Age=FMath::Max(0.f,Clock()-State.Started);
        if(Age>=PhaseDuration()&&State.Phase!=3)
        {
            if(State.Phase==4)
            {
                if(!ExitClear(State.Exit)&&!FindExit(State.Root,State.Exit,State.Kind,State.bMirror,bActiveFitted)){SetPhase(3);return;}
                FinishRest();return;
            }
            SetPhase(State.Phase+1);
        }
    }
    FTransform Root=State.Root;
    const auto* RestType=FurnitureRest::Library(GetWorld()).Types.Find(State.Kind);if(!RestType)return;
    const FVector EntryOffset=FurnitureRest::EntryOffset(*RestType,State.bMirror);
    const float EntryYaw=FurnitureRest::EntryYaw(*RestType,State.bMirror);
    const float CurrentAge=FMath::Max(0.f,Clock()-State.Started);
    if(State.Phase==1)
    {
        const float Weight=FurnitureRest::Ease(CurrentAge/.18f);
        const FQuat EntryTurn(FVector::UpVector,FMath::DegreesToRadians(EntryYaw));
        const FTransform Entry(State.Root.GetRotation()*EntryTurn,State.Root.TransformPosition(EntryOffset));
        Root.Blend(State.Approach,Entry,FurnitureRest::Ease(CurrentAge/.6f));
        Root.SetRotation(Root.GetRotation()*FQuat(FVector::UpVector,FMath::DegreesToRadians(-EntryYaw*Weight)));
        Root.AddToTranslation(-Root.GetRotation().RotateVector(EntryOffset)*Weight);
    }
    if(State.Phase==4)
    {
        const float End=PhaseDuration();
        const FVector Feet=State.Exit-FVector(0,0,Pawn->GetCapsuleComponent()->GetScaledCapsuleHalfHeight());
        const float PoseWeight=1.f-FurnitureRest::Ease((CurrentAge-(End-.18f))/.18f);
        Root.SetRotation(Root.GetRotation()*FQuat(FVector::UpVector,FMath::DegreesToRadians(EntryYaw*(1.f-PoseWeight))));
        const FVector EntryFeet=State.Root.TransformPosition(EntryOffset);
        Root.SetLocation(EntryFeet-Root.GetRotation().RotateVector(EntryOffset)*PoseWeight+(Feet-EntryFeet)*(1.f-PoseWeight));
    }
    Pawn->SetActorLocationAndRotation(Root.GetLocation()+FVector(0,0,Pawn->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()),Root.GetRotation(),false,nullptr,ETeleportType::TeleportPhysics);
    if(auto* PC=Cast<APlayerController>(Pawn->GetController());PC&&Pawn->IsLocallyControlled())
    {
        FRotator Look=PC->GetControlRotation();
        // First-person neck limits are applied in the body frame by the camera;
        // keep the ordinary world-space controls for third-person observation.
        const auto* Body=Pawn->FindComponentByClass<UFPSPlayerBodyComponent>();
        if(Body&&!Body->IsThirdPersonViewEnabled())return;
        Look.Yaw=FRotator::NormalizeAxis(Look.Yaw);
        Look.Pitch=FMath::Clamp(FRotator::NormalizeAxis(Look.Pitch),-85.f,85.f);Look.Roll=0.f;
        PC->SetControlRotation(Look);
    }
}
void UFPSFurnitureRestComponent::AnimationSample(FName& Clip,float& Seconds,float& Weight) const
{
    Clip=NAME_None;Seconds=Weight=0.f;if(!IsResting())return;
    const float Age=FMath::Max(0.f,Clock()-State.Started);
    Clip=FurnitureRest::ClipKey(State.Kind,State.Phase==4?TEXT("Exit"):State.Phase==3?TEXT("Idle"):TEXT("Enter"));
    Seconds=State.Phase==1?0.f:State.Phase==3?FMath::Fmod(Age,PhaseDuration()):FMath::Min(Age,PhaseDuration());
    Weight=State.Phase==1?FurnitureRest::Ease(Age/.18f):State.Phase==4?1.f-FurnitureRest::Ease((Age-(PhaseDuration()-.18f))/.18f):1.f;
}
void UFPSFurnitureRestComponent::ApplyCamera(FMinimalViewInfo& View)
{
    if(!Character.IsValid())return;
    if(!IsResting()){ApplyRestCameraReturn(View);return;}
    FName Clip;float Seconds,Weight;AnimationSample(Clip,Seconds,Weight);
    const auto* Data=FurnitureRest::Library(GetWorld()).Clips.Find(Clip);if(!Data||Data->Eyes.IsEmpty())return;
    const float Sample=FMath::Clamp(Seconds/Data->Duration,0.f,1.f)*(Data->Eyes.Num()-1);
    const int32 A=FMath::FloorToInt(Sample),B=FMath::Min(A+1,Data->Eyes.Num()-1);
    FVector Eye=FMath::Lerp(Data->Eyes[A],Data->Eyes[B],Sample-A);
    const auto* Body=Character->FindComponentByClass<UFPSPlayerBodyComponent>();
    if(!Body||!Body->GetBodyMesh())return;
    Body->SampleFurnitureEye(Clip,Seconds,Eye);
    if(State.bMirror)Eye.X=-Eye.X;
    View.Location=FMath::Lerp(View.Location,Body->GetBodyMesh()->GetComponentTransform().TransformPosition(Eye),Weight);
    // Authored eye tracks supply position; the first-person camera below owns
    // a bounded neck-local look, without adding authored head Euler angles.
    if(const auto* PC=Cast<APlayerController>(Character->GetController()))
        View.Rotation=PC->GetControlRotation();
    const auto* Type=FurnitureRest::Library(GetWorld()).Types.Find(State.Kind);
    if(Type&&!Body->IsThirdPersonViewEnabled())
        ApplyRestCamera(View,*Body->GetBodyMesh(),Type->bLying);
    else
        bRestCameraActive=bRestCameraHasView=false;
    View.bUseFirstPersonParameters=false;
}
float UFPSFurnitureRestComponent::FootDrop() const
{
    // Fit the existing ankle IK to the shop's stool height without moving the pelvis.
    if(!IsResting()||FMath::IsNearlyZero(State.SeatFloorCorrection))return 0.f;
    const float Blend=State.Phase==1?FurnitureRest::Ease((Clock()-State.Started)/.6f):1.f;
    return State.SeatFloorCorrection*Blend;
}
void UFPSFurnitureRestComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    if(IsResting()&&GetOwner()->HasAuthority())
        FurnitureRest::Library(GetWorld()).Occupants.RemoveSingleSwap(this);
    State.Phase=0;ApplyState();ClearFocus();if(Outline)Outline->DestroyComponent();
    if(OutlineLoad)OutlineLoad->CancelHandle();
    if(OutlineMaterial&&Character.IsValid()&&Character->FirstPersonCamera)
        Character->FirstPersonCamera->RemoveBlendable(OutlineMaterial);
    Super::EndPlay(Reason);
}
