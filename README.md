# DeepSeek V4.1 Flash — Procedural Running Sneaker Test

**This repository is the record of a capability test.** The model **DeepSeek V4.1 Flash** was given one brief: design and render a photorealistic studio photograph of a performance running sneaker, built entirely in code with Blender's Python API — no mesh files, no texture maps, no HDRI, no photo references, no manual modelling. Everything below — the last/profile maths, the meshes, the procedural materials, the studio lighting rig and every render — was produced by the model in a single agent session.

![Hero render — 3/4 lateral view](sneaker/renders/hero-3q-lateral.png)

<p align="center">
  <em>2400 × 1350 · Cycles (CUDA) · 160 spp · AgX — rendered from the script in this repository</em>
</p>

---

## About the test

| | |
| --- | --- |
| **Model** | DeepSeek V4.1 Flash (`deepseek-v4.1-flash-free`) |
| **Harness** | OpenCode — agentic coding session with shell, file and browser tools |
| **Task** | one text brief: build a photorealistic 3D performance sneaker in Blender from scratch, procedurally, and render it as a studio photograph |
| **Session** | 15–19 Oct 2026, one continuous session (build → preview → diagnose → fix → final renders) |
| **Produced** | 2,532 lines of Python across 21 files; 124,315 faces at render time |
| **Process** | the model installed its own environment, rendered **121 distinct preview/diagnostic images**, wrote its own geometry audit scripts (`probe_*.py`), and iterated on visual evidence |
| **Diagnosed & fixed in-session** | a fin/flap at the toe pole (traced to a midsole ramp breaking pole convergence + Solidify offsetting along degenerate pole normals), collar tube caps showing at the throat, a cord-like lace bow, foam specular blowout, clipped highlights |
| **Deliverables** | 2400 × 1350 hero, two extra angles, four detail crops, `.blend` scene, glTF 2.0 export |

The repository is kept as-is as an evaluation artifact: the code, renders and exports are what the session produced, with only a README, license and ignore rules added for publishing.

### The brief it was given

- **Original design**, no brands, logos or trademarks. Palette: off-white, charcoal black, cool grey, small reflective silver accents.
- **Required construction:** tapered toe box, padded low collar, heel counter, engineered-knit upper, tongue, evenly spaced eyelets, 3D criss-cross laces, toe bumper, layered overlays, sculpted foam midsole, separate treaded rubber outsole, heel pull tab, stitching.
- **One material per component** — textile matte, foam diffuse, rubber darker/rougher/non-metallic, restrained metal highlights. No single shader for everything.
- **Camera:** 3/4 side view slightly above the centreline, whole shoe uncropped, negative space, landscape, high resolution.
- **Lighting:** light-grey seamless cyclorama, soft key upper-front-left, restrained fill, subtle rim, soft contact shadows, ambient occlusion in the seams, no blown highlights, no coloured lights.
- **Clean geometry:** no polygon artefacts, no gaps between upper and sole, no floating overlays, no intersections, no texture stretching.
- **Reproducible runtime:** must produce real geometry, real materials and a real render — no substituted photos, flat images or placeholders.

## Gallery

| Front-low three-quarter | Medial three-quarter |
| --- | --- |
| ![Front-low view](sneaker/renders/front-low.png) | ![Medial view](sneaker/renders/medial-3q.png) |

| Toe box & rand | Lacing, eyelets & bow |
| --- | --- |
| ![Toe box detail](sneaker/renders/detail-toe-box.png) | ![Lacing detail](sneaker/renders/detail-lacing.png) |

| Sculpted midsole & outsole | Heel counter, pull tab & reflective trim |
| --- | --- |
| ![Midsole detail](sneaker/renders/detail-midsole.png) | ![Heel detail](sneaker/renders/detail-heel-counter.png) |

Full-resolution stills and detail crops live in [`sneaker/renders/`](sneaker/renders); the scene file and glTF export live in [`sneaker/models/`](sneaker/models).

## What the model built

- **Analytic footwear last** — the whole shoe is built from profile tables sampled on a parametric `(u, q)` surface: `u` runs toe pole → heel pole, `q` runs sole seam → crest. Every width is scaled by an elliptical pole factor, so all profiles collapse to single points at both ends (no pinching, no fan artefacts).
- **Layered construction** — knit shell with an analytic inner wall, then 1.3 mm-proud overlay panels (quarter, eyestay, heel counter, toe rand), each with its own bound edge and its own stitch line made of real dash geometry.
- **Distinct procedural PBR material per component** — engineered knit, dense-weave textile, closed-cell foam, rubber, soft metal, padded collar, braided lace, thread. Nothing shares a "one shader fits all" surface.
- **Everything texture-scaled in millimetres** — object-space/UV textures are driven by mesh UVs measured in mm (`Scale = 1 / feature_size_mm`), so the knit rib, weave and foam grain keep a constant real-world size across the model.
- **Studio built in-scene** — seamless light-grey cyclorama, soft key upper-front-left, restrained fill, subtle rim, background wash, world colour tuned for ambient occlusion in the seams.
- **Audited geometry** — purpose-written probe scripts check pole convergence, stray vertices, anomalous edge lengths, surface clearance, panel outlines and tongue/wall clearance before delivery.

| Component | Construction | Material |
| --- | --- | --- |
| Tapered toe box & vamp | shell lofted from profile tables, closed analytic inner wall (0.4–2.2 mm, tapering to zero at the poles) | engineered knit, off-white |
| Quarter panel, eyestay, heel counter | overlay panels 1.3 mm proud, 1.0 mm bound edge, hand-built bumper edges | dense-weave textile, cool grey |
| Toe bumper / rand | wrap panel with a tapered lip and a stitched boundary | dense textile, light grey |
| Midsole | sculpted foam loft: heel flare, toe taper, moulding crease along the sidewall | closed-cell foam, diffuse, off-white |
| Outsole | separate forefoot + heel pads with radial lugs | rubber, charcoal, high roughness |
| Collar | padded roll following the throat's opening curve, ends sunk into the shell | padded knit, cool grey |
| Tongue | lofted panel tucked behind the shell wall | knit |
| Laces | flat-ribbon tubes in a criss-cross, plus a tied bow (knot bar, loops, tails) | braided lace, off-white |
| Eyelets | 6 per side, evenly spaced | metal, silver |
| Reflective trim | strip along the heel counter's top edge | soft metal, silver |
| Stitching | real dash geometry (≈2.1 mm dashes, 0.3 mm thread) | thread |
| Heel pull tab | strap loop | dense textile |

## How it is built

```
sneaker/
├── shoe.py        # the shoe: profile tables, last, shell, overlays, sole, laces, stitching
├── shoelib.py     # table/PCHIP maths, mesh builder, tube(), solidify(), modifiers
├── materials.py   # procedural PBR node graphs (knit, weave, foam, rubber, metal, …)
├── studio.py      # cyclorama, lights, world, camera, render settings
├── main.py        # CLI: build → studio → render → save .blend → export .glb
├── probe*.py      # geometry audits (poles, strays, edges, panels, tongue clearance,
│                  #   tip macros, per-part identity-colour passes)
├── check_profile.py, measure.py, diag.py
├── crop.ps1       # PowerShell crop/zoom helper used while reviewing renders
└── RENDER_NOTES.md  # engineering notes written for the delivery
```

1. **Tables → surface.** Continuous profile tables (`ZGB`, `ZST`, `ZRIM`, … widths) are interpolated with PCHIP and evaluated through an elliptical pole factor, giving a clean, closed last.
2. **Shell → wall.** The knit shell is lofted as a double grid: the outer surface, an inner surface offset along the analytic normal with a thickness profile that goes to zero at both poles, plus rim quads along the hem and collar. (Solidify was removed for this part — offsetting along degenerate pole normals produced fins.)
3. **Overlays.** Panels are generated as sub-grids of the same surface, pushed 1.3 mm outward, given a 1.0 mm bound edge, and stitched with dash geometry placed analytically inside each panel's outline.
4. **Materials.** Node graphs combine Gabor/wave/voronoi-based micro-structure for the knit, a tighter weave for the panels, soft noise for the foam, layered roughness breaks for the rubber, and restrained metallic highlights for the eyelets and trim. Base colours and roughness vary per component; nothing is a single-shader stand-in.
5. **Studio.** Cyclorama + six lights (key 820 W, fill, rim, top, front, background wash) and a cool-grey world; the camera is a 100 mm lens at a 3/4 angle slightly above the centreline, framed with negative space.
6. **Render.** Cycles on CUDA/OptiX, 2400 × 1350 at 160 spp with denoising, AgX view transform, exposure −3.7.

## Reproducing the test output

Requires Python 3.11 and Blender's `bpy` module wheel (CPU fallback works, GPU is much faster).

```powershell
git clone https://github.com/temidayoxyz/deepseek4.1flashtest.git
cd deepseek4.1flashtest

python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

cd sneaker
# fast preview
.\.venv\Scripts\python.exe main.py -- --res 1100x620 --samples 72 --out preview.png

# final hero + scene + glTF export
.\.venv\Scripts\python.exe main.py -- --res 2400x1350 --samples 160 --lens 100 `
    --out hero.png --save-blend models\sneaker-studio.blend --glb models\sneaker.glb `
    --views "36,19,1.00,hero"
```

Useful flags: `--res WxH`, `--samples`, `--az/--el/--dist/--lens` (single view), `--views "az,el,dist,name;…"` (several views in one build), `--exposure`, `--cpu`, `--save-blend`, `--glb`.
Camera azimuth convention: `0°` = lateral (+X), `90°` = toe, `180°` = medial, `270°` = heel.

The session ran on a GTX 1050 Ti (4 GB) — roughly 70–100 s to build the scene and ≈3.5 min for the 2400 × 1350 hero.

## Quality checks the session ran

| Script | What it verifies |
| --- | --- |
| `check_profile.py` | every profile table converges to a single point at both poles (spread 0.0000 mm) |
| `probe_spike.py` | no stray/duplicate vertices anywhere in the build |
| `probe_edges.py` | no anomalous edge lengths (catches fins, torn rims, bad welds) |
| `probe_crest.py` | nothing rides above the toe box's crest line except the rand's intended offset |
| `probe_panel.py` | overlay outlines are sane and their bottom edges hide behind the foam flare |
| `probe_tongue.py` | the tongue clears the shell wall and the liner (0 problems) |
| `probe_tip_multi.py`, `probe_tint.py` | tip macros and per-part identity-colour passes used to trace and fix the toe-pole fin |
| `measure.py`, `diag.py`, `probe*.py` | silhouette measurements, part bounds, per-view sanity renders |

The final hero's histogram was also measured: pixels at 255 occur only in ~0.002 % of the frame (tiny specular maxima on metal parts), i.e. no clipped areas on the shoe body.

## Deliverables

| Path | What |
| --- | --- |
| `sneaker/renders/hero-3q-lateral.png` | 2400 × 1350 hero still |
| `sneaker/renders/medial-3q.png`, `front-low.png` | 1800 × 1010 extra angles |
| `sneaker/renders/detail-*.png` | 1.5–1.7× detail crops of the delivered hero |
| `sneaker/models/sneaker-studio.blend` | full scene: shoe + cyclorama + lights + camera + render settings |
| `sneaker/models/sneaker.glb` | shoe only, glTF 2.0 binary (procedural node textures are not exported; base colours are) |
| `sneaker/RENDER_NOTES.md` | engineering notes: decisions, audits, accepted details |

## Notes & known limitations

- Panel edges are real cut edges (about 1 mm thick); at 3× zoom the bump-mapped edge reads slightly bound/scalloped. That is a deliberate look, not a tear.
- The interior is closed by a liner panel rather than an anatomically modelled footbed — it is never visible from any published angle.
- The midsole-to-upper transition is an intentional tangent discontinuity (two different materials meeting at a seam).
- The glTF export carries geometry and flat PBR values; the procedural micro-structure lives in the Blender scene, so the `.glb` looks simpler than the renders.
- Tread detail faces the ground and shows only from low/front angles by design.
- This is an evaluation artifact rather than a maintained package: there is no CI, test suite or release process, and the scene files are snapshots of the test's output.

## License

MIT — see [`LICENSE`](LICENSE).
