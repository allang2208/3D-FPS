// Registered in BeginStreaming's non-shipping block. Guest requests travel through
// the owning PlayerState; the authority chooses the current world's destination.
static FAutoConsoleCommandWithWorld VisitQuarryCommand(TEXT("fps.Hills.VisitQuarry"),
    TEXT("Visit the current world's white-cliff quarry after its collision is ready."),
    FConsoleCommandWithWorldDelegate::CreateStatic(&TemperateHillsQuarryTravel::Request));