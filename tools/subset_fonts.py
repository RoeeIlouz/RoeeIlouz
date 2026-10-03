"""One-off: subset JetBrains Mono TTFs to the glyphs the panels use.

    python tools/subset_fonts.py <dir with 400.ttf 700.ttf 800.ttf>
TTFs: https://github.com/JetBrains/JetBrainsMono/tree/master/fonts/ttf
"""
import sys
from pathlib import Path

from fontTools import subset

TEXT = "".join(chr(c) for c in range(0x20, 0x7F)) + "·▸●■Σ↑→—…°×"
OUT = Path(__file__).resolve().parent / "fonts"

for w in (400, 700, 800):
    opts = subset.Options()
    opts.flavor = "woff2"
    opts.layout_features = []
    opts.name_IDs = [0, 1, 2]
    font = subset.load_font(str(Path(sys.argv[1]) / f"{w}.ttf"), opts)
    s = subset.Subsetter(opts)
    s.populate(text=TEXT)
    s.subset(font)
    subset.save_font(font, str(OUT / f"jbm-{w}.woff2"), opts)
    print(w, (OUT / f"jbm-{w}.woff2").stat().st_size)
