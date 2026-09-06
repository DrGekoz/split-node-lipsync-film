# Split Node Lip Sync FILM

A local-first audio-to-lip-sync video pipeline for a single animated character. It uses PocketTTS (or any WAV), Allosaurus `eng2102` phoneme detection, custom mouth-state artwork, Google FILM interpolation through a CUDA 13 PyTorch port, and Remotion at 2560x1440 / 24 fps.

## What it does

`audio.wav` -> timestamped phonemes -> 20-state mouth keyframes -> FILM-generated transition frames -> Remotion composition -> film grain -> final video with original audio.

FILM is used only between mouth-state transitions. The output remains 24 fps. It does not generate a permanent image for every frame.

## Credits and licenses

- Google Research FILM: https://github.com/google-research/frame-interpolation
- Allosaurus by Xin Li: https://github.com/xinjli/allosaurus
- FILM PyTorch inference port used here: https://github.com/dajes/frame-interpolation-pytorch
- Remotion: https://www.remotion.dev/
- PocketTTS: https://github.com/kyutai-labs/pocket-tts

Read each upstream license before redistribution. The included FILM TorchScript and Allosaurus model files are included for reproducible local use and remain subject to their upstream terms.

## Requirements

Windows 10/11, NVIDIA GPU recommended, Node.js 20+, npm, Git, FFmpeg in PATH, Python 3.13-compatible Python, and an NVIDIA driver supporting the installed CUDA runtime. This distribution uses an existing CUDA-capable PyTorch installation. Recommended: ComfyUI portable Python with PyTorch CUDA already installed.

Minimum practical hardware: 8 GB VRAM. Full 2560x1440 FILM inference is VRAM-heavy. Do not run multiple FILM workers simultaneously.

## Included models

- `models/film_net_fp16.pt`: FILM TorchScript model, approximately 69 MB.
- `models/allosaurus-eng2102/model.pt`: English Allosaurus model, approximately 42 MB, with its model configuration and phone inventory.

No model download is required for the included detector/interpolator. A fresh installation still needs the Python packages and Node packages below.

## Installation

1. Clone the repository.
2. Install Node dependencies:

```bat
cd remotion
npm install
```

3. Install Python dependencies into the Python environment that will run the scripts:

```bat
python -m pip install torch pillow numpy opencv-python
python -m pip install --no-deps allosaurus==1.0.2 panphon==0.20.0
```

Allosaurus has old dependencies. If `unicodecsv` fails to install on Python 3.13, create `unicodecsv.py` in that environment's site-packages containing:

```python
from csv import *
```

The supplied Windows setup in the original development environment used the ComfyUI portable Python. Set its path in commands rather than installing a second Torch stack.

4. Check CUDA:

```bat
python -c "import torch; print(torch.__version__, torch.version.cuda, torch.cuda.is_available())"
```

The expected result is a CUDA-capable Torch build and `True`.

## Required character images

You must supply one original character reference image first. This is the identity anchor. Use a clean front-facing or near-front-facing image with the whole head, hair, skin, clothing, background, camera framing, and lighting visible. PNG is preferred.

Create these canonical images in both reference sets:

- A, B, C, D, E, F, G, H, X: the standard Rhubarb-compatible mouth states
- M_idle
- M_closed_pressed
- M_neutral_consonant
- M_smile_ee
- M_small_open_eh
- M_wide_open_ae
- M_wide_open_aa
- M_rounded_oh
- M_puckered_oo
- M_fv
- M_th_voiced
- M_th_unvoiced
- M_sh
- M_ch
- M_l
- M_r
- M_nasal
- M_back
- M_teeth
- M_breath

Every renderer-used image must be exactly 2560x1440 and RGB or RGBA PNG.

There are two sets because the quote composition has a separate narrator artwork set:

```text
refs/narration-lip-sync/
refs/narration-quote-lip-sync/
```

If starting from nothing, an AI agent should ask for the original character image, then offer to generate the complete list of 20 M states with Codex CLI. Each generated image must use the original character image as its only identity/style anchor, change only the mouth/jaw/tongue, and preserve framing, hair, face, clothing, background, lighting, and canvas. Generate idempotently: never replace an existing image without a backup and explicit approval.

Recommended special states: natural eye blink only on `M_l` and `M_th_voiced`; subtle head variation may be used sparingly. Do not introduce different characters, camera crops, text, logos, or backgrounds.

## Audio workflow

Use an existing WAV or generate it with PocketTTS using the approved voice reference. Keep the original WAV unchanged. It may be 24 kHz mono. Allosaurus resamples supported WAV input automatically; the old Rhubarb 44.1 kHz restriction does not apply to this detector.

Optionally inspect it:

```bat
ffprobe -v error -show_entries stream=codec_name,sample_rate,channels:format=duration -of json audio.wav
```

## Generate Allosaurus cues

The adapter uses the real `eng2102` model and timestamped phoneme output from Allosaurus:

```bat
python scripts/allosaurus_mouth_cues.py audio.wav -o build/mouth_cues.json --device 0
```

The output contains detector metadata, every source phoneme, timestamps, mapped M state, and merged adjacent states. The mapping is deterministic and can be audited without rerunning the model.

## Hardened preflight

Run before every render:

```bat
python scripts/harden_lipsync.py audio.wav
```

It verifies the audio, all 58 canonical images across both sets, FILM model presence, CUDA backend metadata, and Allosaurus cue cache. It creates:

```text
.cache/allosaurus/<audio-and-adapter-key>.json
.cache/asset_hashes.json
lipsync_pipeline_manifest.json
```

Caches are reused only when the source hashes and file metadata remain valid. Cue files are written atomically and schema-checked. If audio, adapter, model, or a canonical image changes, the relevant cache is invalidated.

The manifest locks:

- audio SHA-256 and duration
- Allosaurus model/detector identity
- FILM model SHA-256
- every canonical image SHA-256
- output 2560x1440 / 24 fps policy
- post-FILM grain policy

## FILM worker

Start one worker for on-demand interpolation:

```bat
python scripts/film_worker.py
```

It reads one JSON request per line from stdin and returns one JSON response per line. Example request:

```json
{"frame1":"refs/narration-lip-sync/narration_lip_sync_M_idle.png","frame2":"refs/narration-lip-sync/narration_lip_sync_M_smile_ee.png","time":0.5}
```

The worker loads `models/film_net_fp16.pt` once, uses CUDA when available, processes the full image without high-resolution tiling, and returns the PNG as base64. Do not run multiple workers on an 8 GB GPU.

## Remotion

The Remotion project is in `remotion/`. It is 2560x1440 at 24 fps. The production compositions are:

- `SplitNodeNarrationLipSync`
- `SplitNodeNarrationQuoteLipSync`

The quote card is left-anchored. Film grain must be applied after the FILM-generated image is selected, never before interpolation.

A complete production runner should:

1. Run hardened preflight.
2. Load the locked cue manifest.
3. Build an ordered timeline from cue intervals.
4. Hold a mouth image while its state remains unchanged.
5. Request one FILM frame only at a state transition when the transition is worth interpolating.
6. Reuse an identical transition from the deterministic cache.
7. Keep hard cuts, long holds, and unchanged states free of unnecessary FILM calls.
8. Render Remotion at exactly 24 fps.
9. Apply the animated seeded grain overlay after interpolation.
10. Preserve and mux the original audio.
11. Probe the final file and fail if any required stream or timing property is wrong.

## Resumability and safety rules

- Never overwrite an existing character asset without creating a `.bak` first.
- Never overwrite a completed video by default. Write to a temporary output and atomically rename after validation.
- Keep per-run manifests and deterministic cache keys.
- Reuse valid cues, transitions, and images.
- Regenerate only missing, corrupt, or hash-invalid artifacts.
- Use one GPU-heavy FILM worker at a time.
- Never silently fall back to CPU for a production render. Fail clearly if CUDA is unavailable.
- Never interpolate across a hard scene/quote cut.
- Never add grain before FILM.
- Never alter the original audio to compensate for visual timing.

## Final verification

```bat
ffprobe -v error -show_entries stream=codec_type,codec_name,width,height,r_frame_rate,sample_rate,channels:format=duration,size -of json output.mp4
```

Accept only when:

- video is 2560x1440
- video is 24/1 fps
- audio and video streams are both present
- duration matches the source audio within normal container rounding
- decode succeeds through the final frame
- no unexpected permanent frame archive was created
- the manifest and output hashes are recorded
- Allosaurus and FILM report the intended models
- the renderer used the locked canonical image hashes

## Troubleshooting

`ModuleNotFoundError: allosaurus`: run the adapter with the same Python where Allosaurus was installed.

`ModuleNotFoundError: unicodecsv`: use the standard-library shim described above.

`CUDA out of memory`: close other GPU workloads, ensure only one FILM worker exists, and use a controlled tiled fallback only if required. Do not silently lower output resolution.

`FILM output looks wrong`: verify the two input frames are the intended canonical assets, verify both are 2560x1440, and inspect the transition pair. Do not add grain before FILM.

`cache unexpectedly reruns`: inspect `.cache`, audio SHA, adapter SHA, and asset modification metadata. This is intentional when an input changes.

## Development status

The detector, custom mouth-state mapping, CUDA 13 FILM worker, model assets, and hardened preflight are included. A project-specific timeline runner may adapt the Remotion source to its own UI, quote-card design, and audio manifest format while retaining the locked pipeline rules above.
