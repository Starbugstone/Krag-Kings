using UnrealBuildTool;
public class KragKingsBenchmarkEditorTarget : TargetRules
{
    public KragKingsBenchmarkEditorTarget(TargetInfo Target) : base(Target)
    {
        Type = TargetType.Editor;
        DefaultBuildSettings = BuildSettingsVersion.Latest;
        IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
        ExtraModuleNames.Add("KragKingsBenchmark");
    }
}
