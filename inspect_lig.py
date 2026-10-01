from fontTools.ttLib import TTFont
import io

font = TTFont('/mnt/c/workspace/planefont/PlaneSans.woff2')
gsub = font['GSUB'].table

for i, l in enumerate(gsub.LookupList.Lookup):
    if l.LookupType == 4:
        for st in l.SubTable:
            print("Coverage glyphs:", getattr(st, 'Coverage', None))
            if hasattr(st, 'Coverage') and st.Coverage:
                print("Coverage glyph list:", st.Coverage.glyphs[:10])
            print("Ligatures count:", len(st.ligatures))
            for k, liglist in list(st.ligatures.items())[:3]:
                for lig in liglist:
                    print(f"  {k} + {lig.Component} -> {lig.LigGlyph}")
