from fontTools.ttLib import TTFont
from fontTools.ttLib.tables import otTables

font = TTFont('/mnt/c/workspace/planefont/PlaneSans.woff2')
gsub = font['GSUB'].table

# Check Lookup 0 (the one we inserted)
print("Lookup 0 type:", gsub.LookupList.Lookup[0].LookupType)
st = gsub.LookupList.Lookup[0].SubTable[0]
print("Subtable ligatures keys count:", len(st.ligatures))
print("Subtable coverage:", getattr(st, 'Coverage', None))

if hasattr(st, 'Coverage') and st.Coverage:
    print("Coverage glyphs count:", len(st.Coverage.glyphs))
    print("Coverage samples:", st.Coverage.glyphs[:10])
