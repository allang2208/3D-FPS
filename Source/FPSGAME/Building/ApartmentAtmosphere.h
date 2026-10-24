#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "ApartmentAtmosphere.generated.h"

class AFPSWeatherManager;
class UAudioComponent;
class UBoxComponent;
class UMaterialInstanceDynamic;
class UPostProcessComponent;
class USoundBase;
class ULightComponent;
class AColdSteelSlidingDoor;
class AApartmentDeviceControl;

USTRUCT(BlueprintType)
struct FApartmentLightBinding
{
    GENERATED_BODY()
    UPROPERTY(EditAnywhere, BlueprintReadWrite) TObjectPtr<AActor> Actor;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float BaseIntensity = 1000.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float DayFactor = .3f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float NightFactor = .8f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) int32 RoomIndex = INDEX_NONE;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) TArray<TObjectPtr<AActor>> Fixtures;
    UPROPERTY(Transient) TObjectPtr<ULightComponent> Component;
    UPROPERTY(Transient) TArray<TObjectPtr<UMaterialInstanceDynamic>> Materials;
    float Relevance = 1.f;
    float LastFactor = -1.f;
    float OriginalIntensity = 0.f;
    double LastWanted = 0.;
    bool bOriginalVisible = true;
};

USTRUCT(BlueprintType)
struct FApartmentRoom
{
    GENERATED_BODY()
    UPROPERTY(EditAnywhere,BlueprintReadWrite) FName Name;
    UPROPERTY(EditAnywhere,BlueprintReadWrite) FVector Minimum=FVector::ZeroVector;
    UPROPERTY(EditAnywhere,BlueprintReadWrite) FVector Maximum=FVector::ZeroVector;
    UPROPERTY(EditAnywhere,BlueprintReadWrite) bool bKeepLit=false;
};

USTRUCT(BlueprintType)
struct FApartmentPortal
{
    GENERATED_BODY()
    UPROPERTY(EditAnywhere,BlueprintReadWrite) int32 RoomA=INDEX_NONE;
    UPROPERTY(EditAnywhere,BlueprintReadWrite) int32 RoomB=INDEX_NONE;
    UPROPERTY(EditAnywhere,BlueprintReadWrite) FVector Center=FVector::ZeroVector;
    UPROPERTY(EditAnywhere,BlueprintReadWrite) TObjectPtr<AColdSteelSlidingDoor> Door;
};

USTRUCT(BlueprintType)
struct FApartmentDeviceBinding
{
    GENERATED_BODY()
    UPROPERTY(EditAnywhere, BlueprintReadWrite) TObjectPtr<AActor> Station;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) TArray<TObjectPtr<AActor>> Rotors;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float WakeRadius = 230.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) bool bWorkout = false;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) TObjectPtr<AApartmentDeviceControl> Control;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) TArray<TObjectPtr<AActor>> MaterialActors;
    UPROPERTY(Transient) TArray<TObjectPtr<UMaterialInstanceDynamic>> Materials;
    UPROPERTY(Transient) float Activity = 0.f;
    TArray<FQuat> RotorBases;
    UPROPERTY(Transient) float Phase = 0.f;
    float LastMaterialActivity = -1.f;
    float LastPower = -1.f;
    float Elapsed = 0.f;
    bool bAnimate = false;
};

/** Map-authored presentation only. Uses the existing replicated weather clock. */
UCLASS()
class FPSGAME_API AApartmentAtmosphere : public AActor
{
    GENERATED_BODY()
public:
    AApartmentAtmosphere();
    virtual void Tick(float DeltaSeconds) override;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Apartment") TArray<FApartmentLightBinding> Lights;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Apartment") TArray<FApartmentDeviceBinding> Devices;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Apartment") TArray<TObjectPtr<AActor>> Windows;
    UPROPERTY(EditAnywhere, Category="Apartment") TObjectPtr<class UMaterialParameterCollection> AnimationClock;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Apartment|Rooms") TArray<FApartmentRoom> Rooms;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Apartment|Rooms") TArray<FApartmentPortal> Portals;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Apartment|Audio") TObjectPtr<AColdSteelSlidingDoor> BalconyDoor;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Apartment|Audio") int32 HarborRoomIndex=1;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Apartment|Audio") TObjectPtr<USoundBase> InteriorSound;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Apartment|Audio") TObjectPtr<USoundBase> HarborSound;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Apartment|Audio") TObjectPtr<USoundBase> DeviceSound;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Apartment|Audio") float FacadeY = 0.f;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Apartment") TObjectPtr<UBoxComponent> LivingReflectionBounds;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Apartment") TObjectPtr<UBoxComponent> BathReflectionBounds;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Apartment") TObjectPtr<UPostProcessComponent> LivingReflections;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Apartment") TObjectPtr<UPostProcessComponent> BathReflections;
protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    UPROPERTY(Transient) TArray<TObjectPtr<UMaterialInstanceDynamic>> WindowMaterials;
    UPROPERTY(Transient) TArray<TObjectPtr<UAudioComponent>> DeviceAudio;
    UPROPERTY(Transient) TObjectPtr<UAudioComponent> InteriorAudio;
    UPROPERTY(Transient) TObjectPtr<UAudioComponent> HarborAudio;
    TWeakObjectPtr<AFPSWeatherManager> Weather;
    FTimerHandle PresentationTimer;
    float LastNight = -1.f;
    float LastRain = -1.f;
    float BindRetryLeft = 0.f;
    float LastHarborExposure = -1.f;
    float LastOutside = -1.f;
    double LastPresentationTime = 0.;
    void UpdatePresentation();
    void UpdateRoomLights(float Night,float Delta);
    int32 FindRoom(const FVector& Eye) const;
    float RoomSoundTransmission(int32 Room) const;
    UAudioComponent* MakeAudio(USoundBase* Sound, const FVector& Location, bool bSpatial);
};
