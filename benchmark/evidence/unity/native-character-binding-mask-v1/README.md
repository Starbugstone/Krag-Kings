# Actual Unity binding mask identity

The raw FBX eligibility mask and actual Unity color-alpha readback identify the same 102,736 nondegenerate skin triangles. All imported binary alpha values agree with authored geometry, accounting for Unity render-vertex splitting: 51,374 source eligible points become 56,679 imported eligible vertices. Maximum mapped point error is 0.480115 micrometres.

The independent audit uses the [actual v3 position/index buffers](../native-character-import-v3/README.md) and alpha readback retained with the [failed first character render](../native-character-render-v1-shader-failed/README.md). Exact input hashes are recorded. The initial lightweight audit attempted in-place translation of a read-only parser array; corrected code allocates the transformed array, then passes. This is eligibility identity, not a native root attachment or animated rendering result.
