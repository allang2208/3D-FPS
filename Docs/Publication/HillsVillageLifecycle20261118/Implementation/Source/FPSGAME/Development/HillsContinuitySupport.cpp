#include "HillsContinuitySupport.h"
#include "HillsContinuityAudit.h"
#include "../FPSGAMECharacter.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "../Characters/FPSPlayerBodyAnimInstance.h"
#include "../Monsters/NurseZombie.h"
#include "../UI/ColdSteelWorldInteraction.h"
#include "Animation/AnimSequence.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "HAL/FileManager.h"
#include "InputKeyEventArgs.h"
#include "InputCoreTypes.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Misc/FileHelper.h"
#include "Serialization/JsonSerializer.h"
#include "UObject/UnrealType.h"

namespace HillsContinuity
{
bool Enabled()
{
#if UE_BUILD_SHIPPING
    return false;
#else
    return FParse::Param(FCommandLine::Get(),TEXT("HillsContinuityAudit"))
        &&FPaths::ConvertRelativePathToFull(FPaths::ProjectDir()).Contains(TEXT("HillsContinuity20261118"));
#endif
}
bool Restart(){return FParse::Param(FCommandLine::Get(),TEXT("HillsContinuityRestart"));}
void Save(const FString& Name,const TSharedRef<FJsonObject>& Json)
{
    FString Out,J;FParse::Value(FCommandLine::Get(),TEXT("HillsContinuityOutput="),Out);if(Out.IsEmpty())return;
    IFileManager::Get().MakeDirectory(*Out,true);FJsonSerializer::Serialize(Json,TJsonWriterFactory<>::Create(&J));
    FFileHelper::SaveStringToFile(J,*(Out/Name+TEXT(".json")));
}
AFPSGAMECharacter* Character(APlayerController* PC){return PC?Cast<AFPSGAMECharacter>(PC->GetPawn()):nullptr;}
FFurnitureRestState RestState(AActor* Pawn)
{
    auto* Rest=Pawn?Pawn->FindComponentByClass<UFPSFurnitureRestComponent>():nullptr;
    auto* Property=FindFProperty<FStructProperty>(UFPSFurnitureRestComponent::StaticClass(),TEXT("State"));
    return Rest&&Property?*Property->ContainerPtrToValuePtr<FFurnitureRestState>(Rest):FFurnitureRestState();
}
bool BodyReady(AActor* Pawn,FString* Detail)
{
    auto* Body=Pawn?Pawn->FindComponentByClass<UFPSPlayerBodyComponent>():nullptr;
    auto* Mesh=Body?Body->GetBodyMesh():nullptr;
    auto* Anim=Mesh?Cast<UFPSPlayerBodyAnimInstance>(Mesh->GetAnimInstance()):nullptr;
    if(!Anim||Body->IsAppearanceLoading())return false;
    for(const TCHAR* Phase:{TEXT("Enter"),TEXT("Idle"),TEXT("Exit")})
    {
        const auto* Clip=Anim->Clips.FindRef(FName(FString(TEXT("Rest.ChapelPew."))+Phase)).Get();
        if(!Clip)return false;
        if(Detail)*Detail+=FString::Printf(TEXT(" %s=%s"),Phase,*Clip->GetPathName());
    }
    if(Detail)*Detail+=TEXT(" body=")+Body->GetBodyType().ToString();return true;
}
bool Seated(AActor* Pawn,FString& Detail)
{
    const auto S=RestState(Pawn);FString Clips;const bool Ready=BodyReady(Pawn,&Clips);
    auto* P=Cast<AFPSGAMECharacter>(Pawn);
    Detail=FString::Printf(TEXT("phase=%d slot=%d kind=%s move=%d tick=%d%s"),S.Phase,S.SlotIndex,*S.Kind.ToString(),P?int32(P->GetCharacterMovement()->MovementMode):-1,
        Pawn&&Pawn->FindComponentByClass<UFPSFurnitureRestComponent>()->IsComponentTickEnabled(),*Clips);
    return Ready&&S.Phase==3&&S.Kind==TEXT("ChapelPew")&&P&&P->GetCharacterMovement()->MovementMode==MOVE_None;
}
void KeyE(APlayerController* PC)
{if(PC){PC->InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::E,IE_Pressed,1.f));PC->InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::E,IE_Released,0.f));}}
bool Aim(APlayerController* PC,const FVector& Point)
{
    if(!PC)return false;
    FVector Eye;FRotator View;ColdSteelWorldInteraction::GetReachViewPoint(PC,Eye,View);
    const FRotator Desired=(Point-Eye).Rotation(),Current=PC->GetControlRotation();
    // The anatomical eye moves around the capsule as it turns. Damped input
    // converges at close range instead of alternating across the target seat.
    PC->SetControlRotation(Current+(Desired-Current).GetNormalized()*.08f);
    return FVector::DotProduct(View.Vector(),(Point-Eye).GetSafeNormal())>.9998f;
}
FString InteractionTrace(APlayerController* PC,const FVector& Point)
{
    if(!PC||!PC->GetPawn())return TEXT("no pawn");
    FVector Eye;FRotator View;ColdSteelWorldInteraction::GetReachViewPoint(PC,Eye,View);
    FHitResult Hit;FCollisionQueryParams Q(SCENE_QUERY_STAT(ContinuityFocus),false,PC->GetPawn());
    PC->GetWorld()->LineTraceSingleByChannel(Hit,Eye,Eye+View.Vector()*250.,ECC_Visibility,Q);
    return FString::Printf(TEXT("pawn=%s eye=%s aim=%s range=%.1f hit=%s item=%d cursor=%d"),*PC->GetPawn()->GetActorLocation().ToString(),*Eye.ToString(),*View.ToString(),FVector::Distance(Eye,Point),*GetPathNameSafe(Hit.GetComponent()),Hit.Item,PC->bShowMouseCursor);
}
void Place(APlayerController* PC,const FVector& Feet,const FVector& Look,bool Damage)
{
    auto* P=Character(PC);if(!P)return;P->SetCanBeDamaged(Damage);
    P->GetCharacterMovement()->StopMovementImmediately();P->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
    P->SetActorLocation(Feet+FVector(0,0,P->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+3),false,nullptr,ETeleportType::TeleportPhysics);
    const auto R=(Look-P->GetMeleeAimTransform().GetLocation()).Rotation();PC->SetControlRotation(R);PC->ClientSetRotation(R,true);P->ForceNetUpdate();
}
TArray<ANurseZombie*> Raiders(UWorld* W)
{TArray<ANurseZombie*> R;for(TActorIterator<ANurseZombie> It(W);It;++It)if(It->ActorHasTag(TEXT("HillsNightRaider"))&&It->Health>0)R.Add(*It);return R;}

#if !UE_BUILD_SHIPPING
FAutoConsoleCommandWithWorld Command(TEXT("fps.Test.HillsContinuity"),TEXT("Copied-save UDP hills continuity checks."),FConsoleCommandWithWorldDelegate::CreateLambda([](UWorld* W)
{if(!Enabled()||!W||W->GetNetMode()!=NM_ListenServer)return;auto* R=W->SpawnActor<AHillsContinuityAudit>();R->Director=true;R->SetReplicates(false);}));
#endif
}
