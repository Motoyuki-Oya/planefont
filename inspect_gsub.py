from fontTools.ttLib import TTFont

font = TTFont('/mnt/c/workspace/planefont/PlaneSans.woff2')
gsub = font['GSUB'].table

print("Feature list count:", len(gsub.FeatureList.FeatureRecord))
for i, fr in enumerate(gsub.FeatureList.FeatureRecord):
    if fr.FeatureTag in ['ccmp', 'liga', 'calt']:
        print(f"  [{i}] {fr.FeatureTag} lookups={fr.Feature.LookupListIndex}")

for sr in gsub.ScriptList.ScriptRecord:
    print(f"Script: {sr.ScriptTag}")
    if sr.Script.DefaultLangSys:
        print(f"  DefaultLangSys features: {sr.Script.DefaultLangSys.FeatureIndex}")
    for lsr in (sr.Script.LangSysRecord or []):
        print(f"  LangSys {lsr.LangSysTag} features: {lsr.LangSys.FeatureIndex}")

# Check lookups
for i, l in enumerate(gsub.LookupList.Lookup):
    print(f"Lookup {i}: Type={l.LookupType}")
    if l.LookupType == 4:
        for st in l.SubTable:
            print("  LigatureSubst keys count:", len(st.ligatures))
            for k in list(st.ligatures.keys())[:5]:
                print(f"    base={k} -> {[lig.LigGlyph for lig in st.ligatures[k]]}")
