using UnrealBuildTool;
public class KragKingsBenchmarkTarget : TargetRules
{
    public KragKingsBenchmarkTarget(TargetInfo Target) : base(Target)
    {
        Type = TargetType.Game;
        DefaultBuildSettings = BuildSettingsVersion.Latest;
        IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
        ExtraModuleNames.Add("KragKingsBenchmark");
    }
}
