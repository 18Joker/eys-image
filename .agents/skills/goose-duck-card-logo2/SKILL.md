---
name: goose-duck-card-logo
description: Design and generate Goose Goose Duck role logo batches for the eys-image project. Use when the user invokes /goose-duck-card-logo, asks to create role logos from official assets, or needs style.md-driven prompt generation, batch_tasks.json creation, image_generate_v4.py execution, gallery review, and selected-image archival for goose/duck/neutral card logo sets.
---

# Goose Duck Card Logo

## Overview

Use this skill to turn one role request into production-ready batch image tasks across one or more style sets in the `eys-image` project. The workflow has seven phases: (1) discover style sets, (2) determine generation mode, (3) visually analyze the official asset, (4) ask which sets to generate then design six distinct prompts per selected set using mandatory canvas-design, (5) strictly validate every prompt against style.md line-by-line, (6) write `py/batch_tasks.json`, (7) run `py/image_generate_v4.py`, open the gallery, then archive, redesign, or discard based on the user's review.

Do not copy the `canvas-design` skill into this skill. Duplicated skill folders become stale.

## Canvas-Design Skill — Discovery and Invocation

The `canvas-design` skill is **mandatory** for both initial prompt design and any redesign iteration. It may be installed by a different AI tool (e.g., Claude Code) and therefore not visible in the current tool's skill registry. Follow this discovery order before every design or redesign phase:

1. **Try the Skill tool first.** Call `Skill("canvas-design")` (or the platform equivalent such as `$canvas-design`). If the tool loads the skill successfully, follow its instructions and skip to prompt design.
2. **Search common skill directories on disk.** If step 1 fails, look for a `canvas-design/SKILL.md` file in these locations (check all, not just the first):
   - `.claude/skills/canvas-design/SKILL.md` (Claude Code)
   - `.agents/skills/canvas-design/SKILL.md` (QoderWork / other agents)
   - `~/.qoderworkcn/skills/canvas-design/SKILL.md` (QoderWork global)
   - `~/.claude/skills/canvas-design/SKILL.md` (Claude Code global)
   - Any other `*/skills/canvas-design/SKILL.md` found via glob from the project root and user home
3. **Read and follow the discovered SKILL.md.** If found on disk, read the full file and apply its instructions as if the Skill tool had loaded it. The canvas-design output still defines the character concept — do not treat it as a request to create final artwork unless the user explicitly asks.
4. **Fail loudly if not found anywhere.** If no canvas-design skill is discovered after checking all locations, tell the user: "canvas-design skill not found in any known location. Please install it or provide the skill file path manually." Do **not** silently skip this step and design prompts without the canvas-design character concept process.

This discovery must run at the start of **every** design and redesign cycle — not just the first time. When the user says "重新设计" (redesign), re-invoke canvas-design with updated constraints before generating new prompt variants.

## Project Discovery

Start in the current workspace. If the project root is unclear, locate the directory that contains all of these:

- `py/image_generate_v4.py`
- `py/batch_tasks.json`
- `official/`
- one or more `*/style.md` files

Discover style sets with `rg --files -g style.md` or the platform equivalent. Treat each parent folder of a `style.md` file as a style set, for example `official_v3` or `american_retro_style_v2`.

Read every discovered `style.md` before asking the user which sets to use. Summarize the available set names and generation modes only; keep the question short. If the user already named style sets, still verify that each requested folder has a `style.md`.

Infer the role from the official asset filename when possible:

```text
{faction}_{role}.png
goose_殡仪员.png -> faction=goose, role=殡仪员
duck_刺客.png -> faction=duck, role=刺客
neutral_鸽子.png -> faction=neutral, role=鸽子
```

Require a real official asset path for any style set whose `style.md` requires image-to-image generation.

## Generation Mode

Choose `type` from the selected style set's `style.md`:

- Use `image_to_image` when `style.md` says 图生图, img2img, image-to-image, or requires using the official original logo as a reference.
- Use `text_to_image` when `style.md` says 文生图, txt2img, text-to-image, or does not require the reference image as model input.
- If a `style.md` is ambiguous, ask the user whether to use text-to-image or image-to-image before writing tasks.

For `image_to_image`, include `local_image_path` as an absolute path to the official asset. For `text_to_image`, do not include `local_image_path`; use the official asset only to understand the role identity and icon details.

## Official Asset Visual Analysis

Before writing any prompts, use visual capabilities to read and analyze the official asset image file. Produce a structured analysis containing:

1. **Subject Type** — Determine whether the asset depicts an object icon (e.g., coffin, badge, magnifying glass, knife, crosshair) or a character representation (e.g., goose head, bird head, animal silhouette). If object: describe the object's shape, material, color palette, and key visual features. If character: describe the character's expression, color scheme, distinguishing features, and pose.
2. **Core Identifying Elements** — Extract 1–2 key visual anchors that make this role instantly recognizable. These are the essential design motifs that must be reflected in the generated logo, whether as held/worn items, pattern elements, or thematic atmosphere.
3. **Mood and Atmosphere** — Describe the overall tone conveyed by the asset (solemn, cute, dangerous, mysterious, heroic, etc.).

This analysis is mandatory input for all subsequent prompt design. Do not skip this step or substitute filename-based inference.

## Prompt Design

**Prerequisite: canvas-design must be loaded first.** Before writing any prompts, complete the canvas-design discovery process described in the previous section. If canvas-design was not found, do not proceed — resolve the missing skill first.

Feed the visual analysis results from the Official Asset Visual Analysis section as primary input to canvas-design, together with:

- the selected `style.md`
- the official role asset
- the faction and role name
- the project's WeChat mini-program compliance constraints

The canvas-design output defines the character concept and visual direction — not a request to create final PNG/PDF canvas artwork unless the user explicitly asks for that. All six prompt variants must be derived from this character concept, ensuring the generated logos reflect the official asset's visual identity rather than generic occupation stereotypes.

For each selected style set and role, create exactly six prompt variants. Each variant must be meaningfully different while obeying the style:

- vary concept, pose, material, lighting, expression, accessory treatment, texture, or background treatment — variations must stem from the canvas-design character concept, not from randomly swapping unrelated accessories
- preserve hard requirements from `style.md`, especially no border, square logo, faction identity, species constraints, safe/non-violent treatment, and style-specific background rules
- keep English prompts concise but rich enough for generation
- write `prompt_zh` as a natural Chinese translation of the English prompt, not a separate concept
- avoid merely swapping adjectives across otherwise identical prompts

Prompt quality target: creative, specific, style-faithful, and suitable for a polished mobile card logo. Every prompt must reflect the core identifying elements from the visual analysis and the canvas-design character concept. Do not allow prompts that are disconnected from the official asset's visual identity.

## Prompt Compliance Validation

Before writing `py/batch_tasks.json`, strictly validate every prompt against the style.md. This is a mandatory gate — no prompt may proceed with any unresolved violation.

**Step 1: Build the validation checklist.** Read the selected style.md in full, line by line. Extract every actionable rule from every section (fixed prefix, other requirements, generation requirements, character requirements, compliance red lines, file naming, etc.) into an individual checklist item. Do not summarize or skip any rule — each line that describes a constraint becomes its own check point.

**Step 2: Check every prompt against every item.** For each of the six prompt variants, evaluate every checklist item and output pass/fail with a specific reason. Use this format:

```text
[prompt 1] "American retro comic style, pop art, above the shoulders, ..."
  ✅ Contains fixed prefix "American retro comic style, pop art, above the shoulders"
  ✅ Describes radial burst background
  ❌ Contains border description "aged-paper border" → violates compliance red line #3 "absolutely no borders"
  ✅ No gore/horror content
  ❌ Contains occupation keyword "mortician" → violates red line #6 "avoid occupation-type keywords"
  ✅ Goose faction expression direction correct (cute/kind)
  ❌ Prompt content disconnected from official asset visual analysis → violates "prompts must be highly correlated with official asset"
  ...
```

**Step 3: Fix and re-validate.** If any prompt fails any checklist item, revise that prompt and re-run the full validation. Repeat until every prompt passes every item. No prompt with an unresolved failure may be written to the batch JSON.

**Step 4: Confirm.** After all prompts pass, output a confirmation line:

```text
All 6 prompts pass all N rules from style.md — proceeding to batch JSON.
```

## Batch Task JSON

Write UTF-8 JSON to `py/batch_tasks.json`. Prefer replacing the file for the current run after creating a timestamped backup if the file already has tasks. Use structured JSON APIs rather than manual string concatenation.

Use `1024x1024` unless the user or `style.md` requests otherwise.

For text-to-image:

```json
{
  "task_id": "{style_set}_{faction}_{role}_{index}",
  "type": "text_to_image",
  "prompt": "English prompt",
  "prompt_zh": "中文提示词",
  "size": "1024x1024",
  "output_path": "output/{style_set}/{faction}/{faction}_{role}_{index}.png"
}
```

For image-to-image:

```json
{
  "task_id": "{style_set}_{faction}_{role}_{index}",
  "type": "image_to_image",
  "prompt": "English prompt based on the reference image",
  "prompt_zh": "中文提示词",
  "size": "1024x1024",
  "local_image_path": "D:/absolute/path/to/official/{faction}/{faction}_{role}.png",
  "output_path": "output/{style_set}/{faction}/{faction}_{role}_{index}.png"
}
```

Use forward slashes in JSON paths on Windows to avoid escaping mistakes. Keep `output_path` relative to the project root because `image_generate_v4.py` runs from the project context.

Before running generation, validate:

- every task has a unique `task_id`
- every task has `prompt`, `prompt_zh`, `size`, and `output_path`
- every `image_to_image` task has an existing `local_image_path`
- the task count is `6 * selected_style_set_count * role_count`

## Run And Review

Run the generator from the project root:

```powershell
python .\py\image_generate_v4.py
```

The script writes `py/image_gallery.html`. If the browser does not open automatically, open it explicitly:

```powershell
Start-Process .\py\image_gallery.html
```

Tell the user to review the gallery and reply with one of these actions:

- `保留`: provide exact generated filenames or paths to archive
- `重新设计`: provide what to change; keep any liked filenames first if applicable
- `全部弃用`: discard only the images generated by the current batch

## Post-Review Actions

Track the current run's generated output paths from `batch_tasks.json`; only operate on those paths.

For `保留`, resolve each user-provided filename under `output/{style_set}/{faction}/`. Copy liked files into `{style_set}/{faction}/` while preserving the generated basename, for example:

```text
output/american_retro_style_v2/goose/goose_殡仪员_3.png
-> american_retro_style_v2/goose/goose_殡仪员_3.png
```

If the user says a selected image is the final version, copy it to the canonical style-set filename `{style_set}/{faction}/{faction}_{role}.png`. Before replacing an existing canonical file, create a timestamped backup or ask for confirmation.

For `重新设计`, keep and archive any named favorites first, then **re-run the canvas-design discovery and invocation** (mandatory — do not skip) with the user's critique and previous results as additional constraints before generating a new six-variant batch. Do not repeat failed concepts unless the user asks for small refinements.

For `全部弃用`, delete only the output files listed in the current run's task JSON. Do not delete official assets, style-set folders, archived selections, or unrelated output folders.

## Example Trigger

User:

```text
/goose-duck-card-logo 帮我设计和生成一下 官方素材D:\program\project\front\eys-image\official\goose\goose_殡仪员.png 的logo
```

Expected behavior:

1. Read all discovered `style.md` files.
2. Visually analyze the official asset image to extract subject type, core identifying elements, and mood.
3. Ask which style sets to generate, for example `official_v3` and/or `american_retro_style_v2`.
4. Invoke `$canvas-design` with the visual analysis results to design the character concept.
5. For each selected set, create six prompt variants derived from the character concept.
6. Validate all six prompts line-by-line against each style.md's rules; fix and re-validate until all pass.
7. Write `py/batch_tasks.json`, run `py/image_generate_v4.py`, open `py/image_gallery.html`, and wait for the user's review decision.
