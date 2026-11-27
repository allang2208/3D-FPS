#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "ResidentConversation.h"
#include "../Characters/FPSOutfitSecondaryMotion.h"
#include "../Characters/FPSOutfitStairVisibility.h"
#include "ChapelNun.generated.h"

class UCapsuleComponent;
class USkeletalMeshComponent;
class UGroomComponent;
class UPhysicsAsset;
struct FStreamableHandle;

/** Stationary chapel resident; each world assembles the same authored appearance. */
UCLASS(Blueprintable)
class FPSGAME_API AChapelNun : public AActor
{
    GENERATED_BODY()
public:
    AChapelNun();
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    /** Presentation only: never replicate a conversation target or actor yaw. */
    void SetLocalConversation(APlayerController* Player);
private:
    void AssembleAppearance();
    void CreateHairCollision();
    void UpdateCoreHairDetail(double EffectiveDistance);
    UPROPERTY(VisibleAnywhere) TObjectPtr<UCapsuleComponent> Collision;
    UPROPERTY(VisibleAnywhere) TObjectPtr<USkeletalMeshComponent> Body;
    UPROPERTY(VisibleAnywhere) TObjectPtr<USkeletalMeshComponent> Head;
    UPROPERTY(VisibleAnywhere) TObjectPtr<USkeletalMeshComponent> NapeHair;
    UPROPERTY(VisibleAnywhere) TObjectPtr<USkeletalMeshComponent> Robe;
    UPROPERTY(VisibleAnywhere) TObjectPtr<USkeletalMeshComponent> Trim;
    UPROPERTY(VisibleAnywhere) TObjectPtr<USkeletalMeshComponent> Boots;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UGroomComponent> HairCore;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UGroomComponent> HairLoose;
    UPROPERTY(Transient) TObjectPtr<UPhysicsAsset> HairCollision;
    TSharedPtr<FStreamableHandle> AppearanceLoad;
    FFPSOutfitSecondaryMotion CuffMotion;
    FFPSRobeHemEnvelope HemEnvelope;
    FFPSRobeStairSections BodyInner, BootInner;
    bool bAppearanceReady=false;
    bool bCoreHairActive=true;
    bool bLooseHairActive=true;
    bool bBodyRTVisible=true;
    bool bBodyURO=false;
    TRefCountPtr<FRefCountedObject> BudgetedCoreGroup;
    int32 CoreHairTier=INDEX_NONE;
    FResidentConversationFacing ConversationFacing;
};
