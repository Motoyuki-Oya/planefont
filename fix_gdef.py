from fontTools.ttLib import TTFont
from fontTools.ttLib.tables import otTables

gen = TTFont('/mnt/c/workspace/planefont/PlaneSans.woff2')

# Ensure GDEF and GlyphClassDef
if 'GDEF' not in gen:
    from fontTools.ttLib.tables.G_D_E_F_ import table_G_D_E_F_
    gen['GDEF'] = table_G_D_E_F_()
    gen['GDEF'].table = otTables.GDEF()
    gen['GDEF'].table.Version = 0x00010000

gdef = gen['GDEF'].table
if not hasattr(gdef, 'GlyphClassDef') or gdef.GlyphClassDef is None:
    gdef.GlyphClassDef = otTables.GlyphClassDef()

# Build class definitions: 1 = Base, 3 = Mark
classes = {}
mark_glyphs = {'uni0305', 'uni0332', 'uni0336'}
for gn in gen.getGlyphOrder():
    if gn in mark_glyphs:
        classes[gn] = 3  # Mark glyph
    elif gn != '.notdef':
        classes[gn] = 1  # Base glyph

gdef.GlyphClassDef.classDefs = classes

gen.save('/mnt/c/workspace/planefont/PlaneSans-fixed.woff2')
print("Saved PlaneSans-fixed.woff2 with GDEF classes!")
