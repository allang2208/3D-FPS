#pragma once

#include "CoreMinimal.h"

class AColdSteelAnimal;
class ATemperateHillsWorld;

struct FHillsWildlifeMember
{
    TWeakObjectPtr<AColdSteelAnimal> Animal;
    FVector Offset = FVector::ZeroVector;
    FVector Landing = FVector::ZeroVector;
    FVector FlightOrigin = FVector::ZeroVector;
    double FlightStart = 0.;
    double NextLandingSearch = 0.;
    float Phase = 0.f;
    float StartClearance = 0.f;
    bool bLanded = false;
    bool bNeedsFlightRoute = false;
};

struct FHillsWildlifeGroup
{
    TArray<FHillsWildlifeMember> Members;
    FVector Destination = FVector::ZeroVector;
    FVector Start = FVector::ZeroVector;
    FVector Bend = FVector::ZeroVector;
    FVector Threat = FVector::ZeroVector;
    double AlarmUntil = -1.;
    double NextMove = 0.;
    double RouteStart = 0.;
    double Duration = 0.;
    double PausedSince = -1.;
    bool bCrows = false;
    bool bTravelling = false;
    bool bEscaping = false;
};
