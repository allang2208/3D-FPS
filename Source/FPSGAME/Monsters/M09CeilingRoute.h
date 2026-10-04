#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "M09CeilingRoute.generated.h"
class AHangingBellM09;
/** Optional authored routes; physical ceilings also support placement and local movement. */
UCLASS(Blueprintable)
class FPSGAME_API AM09CeilingRoute : public AActor
{
 GENERATED_BODY()
public:
 AM09CeilingRoute();
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Ceiling") TArray<FVector> GripCenters;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Ceiling") TArray<FIntPoint> Links;
 FVector Point(int32 Index) const;
 bool FindPath(const AHangingBellM09* Monster,FVector Destination,TArray<FVector>& Out) const;
 // Project onto nearby real undersides; body collision is independent of support.
 static bool FindSupport(UWorld* World,FVector Near,const AActor* Ignore,FVector& Contact,FVector* Normal=nullptr);
 static bool Supported(UWorld* World,FVector Contact,const AActor* Ignore);
 static bool ClearBody(UWorld* World,FVector Ceiling,const AActor* Ignore);
 static bool ClearSegment(UWorld* World,FVector From,FVector To,const AActor* Ignore);
 static bool FindPlacement(UWorld* World,FVector Near,const AActor* Ignore,FVector& Center,AM09CeilingRoute*& OptionalRoute);
 static AM09CeilingRoute* FindRoute(UWorld* World,FVector Ceiling);
 static bool FindLocalPath(const AHangingBellM09* Monster,FVector Destination,TArray<FVector>& Out);
};
