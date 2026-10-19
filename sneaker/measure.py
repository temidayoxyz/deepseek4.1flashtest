"""Measure the rendered silhouette of a diag image (workbench render)."""
import sys, os
import numpy as np
import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
name = sys.argv[sys.argv.index('--') + 1] if '--' in sys.argv else 'diag_side.png'
path = os.path.join(HERE, name)
img = bpy.data.images.load(path)
w, h = img.size
px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)
px = px[::-1]                     # flip to top-down
lum = px[..., :3].mean(axis=2)
alpha = px[..., 3]
mask = (lum > 0.12) | (alpha > 0.5)   # object = lit (background is empty/black)
# ortho: 900 px = 0.36 m ; centre of the image = (0, 0, 0.06)
mm = 0.36 * 1000.0 / w
cx, cy = w / 2.0, h / 2.0
print("%s  %dx%d  %.3f mm/px" % (name, w, h, mm))
cols = [int(cx + d / mm) for d in (-140, -120, -100, -80, -60, -40, -20, 0,
                                   20, 40, 60, 80, 100, 120, 140)]
print(" y_mm    top_z_mm  bot_z_mm")
for c in cols:
    if c < 0 or c >= w:
        continue
    ys = np.where(mask[:, c])[0]
    if len(ys) == 0:
        print("%6.1f    ---      ---" % ((c - cx) * mm))
        continue
    top = (cy - ys.min()) * mm + 60.0
    bot = (cy - ys.max()) * mm + 60.0
    print("%6.1f  %8.1f  %8.1f" % ((c - cx) * mm, top, bot))
