#pragma once
#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "FleshHandChargeFX.generated.h"
class AFleshHandMonster; class UInstancedStaticMeshComponent; class UAudioComponent;
class UMaterialInterface; class UMaterialInstanceDynamic; class UStaticMesh;
enum class EFleshHandState : uint8;

/** Eight shared cosmetic slots. Combat clocks/collision remain owned by the hand. */
UCLASS()
class FPSGAME_API UFleshHandChargeFX : public UTickableWorldSubsystem
{
 GENERATED_BODY()
public:
 void Transition(AFleshHandMonster* Hand,EFleshHandState Previous);
 void Impact(AFleshHandMonster* Hand,const FHitResult& Hit,bool bDamagedPlayer);
 void Cancel(AFleshHandMonster* Hand);
 virtual void Tick(float Delta) override;
 virtual bool IsTickable() const override { return bReady&&ActiveSlots>0; }
 virtual TStatId GetStatId() const override;
 virtual void Deinitialize() override;
protected:
 virtual bool DoesSupportWorldType(EWorldType::Type Type) const override;
private:
 static constexpr int32 SlotCount=8;
 static constexpr int32 DustPerSlot=8;
 static constexpr int32 AirPerSlot=3;
 static constexpr int32 ChipsPerSlot=4;
 struct FPuff
 {
  FVector Position=FVector::ZeroVector,Velocity=FVector::ZeroVector;
  float Age=0,Life=0,Size=0,Seed=0; float FloorZ=0;
 };
 struct FSlot
 {
  TWeakObjectPtr<AFleshHandMonster> Hand;
  FPuff Dust[DustPerSlot],Chips[ChipsPerSlot];
  FVector ArcPosition=FVector::ZeroVector,ArcNormal=FVector::UpVector;
  float ArcAge=0,ArcLife=0,ArcSize=0,TrailClock=0,ReleaseAge=0;
  int32 Cursor=0; bool Used=false,Released=false,Impacted=false;
 };
 bool Prepare(AFleshHandMonster* Hand);
 int32 Find(AFleshHandMonster* Hand) const;
 void Release(int32 Index);
 void Dust(int32 Index,const FVector& Position,const FVector& Direction,int32 Count,float Strength);
 void Arc(int32 Index,const FVector& Position,const FVector& Normal,float Size,float Life);
 float ViewDistance(const FVector& Position) const;
 FVector Ground(AFleshHandMonster* Hand) const;
 void Hide(int32 Group,int32 Index);
 FSlot Slots[SlotCount];
 TArray<FTransform> Transforms[3];
 UPROPERTY(Transient) TArray<TObjectPtr<UInstancedStaticMeshComponent>> Renderers;
 UPROPERTY(Transient) TArray<TObjectPtr<UAudioComponent>> Audio;
 UPROPERTY(Transient) TArray<TObjectPtr<UMaterialInstanceDynamic>> Skin;
 UPROPERTY(Transient) TArray<TObjectPtr<UMaterialInterface>> PreviousSkin;
 UPROPERTY() TObjectPtr<UStaticMesh> Plane;
 UPROPERTY() TObjectPtr<UStaticMesh> Cube;
 FRandomStream Random{27092026};
 int32 ActiveSlots=0; bool bReady=false;
};
