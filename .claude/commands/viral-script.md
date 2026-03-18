# /viral:script — HookGenie Hook & Script Generator

You are running the Viral Command script engine. Your job is to generate battle-tested hooks from content angles using 6 proven patterns, score them, and build a persistent hook repository that improves over time. When run without arguments, you interactively guide the user through format selection (longform/shortform), angle picking, hook generation, script writing, and optional LinkedIn post creation.

**Arguments:** $ARGUMENTS

---

## Phase A: Load Context

Read the agent brain to understand the creator's identity and preferences:

```
@data/agent-brain.json
```

**Extract these fields:**
- `identity` — name, brand, niche, tone, differentiator
- `hook_preferences` — pattern weights (boost patterns the creator prefers)
- `visual_patterns` — visual performance data (top_visual_types, text_overlay_colors, pacing_performance) — may be empty
- `monetization` — primary_funnel, cta_strategy
- `platforms.posting[]` — where this creator publishes

**Parse $ARGUMENTS to determine input:**

**If an angle ID is provided (e.g., `/viral:script angle_20260304_001`):**
- Search `data/angles.jsonl` for matching ID
- Load the full angle object (contrast, platform, target_audience, proof_method, funnel_direction)
- If not found: "Angle not found: {id}. Run `/viral:angle` first to develop angles."

**If a topic/text is provided (e.g., `/viral:script "AI agents replacing call centers"`):**
- Search `data/angles.jsonl` for angles matching the topic title
- If match found: use that angle
- If no match: generate hooks directly from the topic text (treat as a freeform angle with user-provided contrast)

**If `--pick` flag:**
1. Scan `data/angles.jsonl` for angles with `status: "draft"` (not yet scripted)
2. Group by format and display:
   ```
   ═══════════════════════════════════════
   PICK AN ANGLE TO HOOK
   ═══════════════════════════════════════

   📺 LONGFORM
    #  │ Title                              │ Contrast
   ────┼────────────────────────────────────┼──────────
    1  │ {title}                            │ {strength}
    2  │ {title}                            │ {strength}

   ⚡ SHORTFORM
    3  │ {title}                            │ {strength}
    4  │ {title}                            │ {strength}

   💼 LINKEDIN
    5  │ {title}                            │ {strength}

   Enter number to select.
   ═══════════════════════════════════════
   ```
3. Wait for user selection before proceeding

**If `--longform` flag (combine with any input method above):**
- Note this flag for later — after hooks are generated (Phase E), continue to Phase F for full YouTube longform script generation
- Can combine: `/viral:script angle_id --longform`, `/viral:script --pick --longform`
- Only generates scripts for youtube_longform platform

**If `--shortform` flag (combine with any input method above):**
- Note this flag for later — after hooks are generated (Phase E), continue to Phase I for short-form script generation
- Can combine: `/viral:script angle_id --shortform`, `/viral:script --pick --shortform`
- Generates ONE cross-platform shortform script (not separate entries per platform)

**If `--pdf` flag (combine with --longform or --shortform):**
- Note this flag for later — after script persistence (Phase H or Phase J), continue to Phase K for PDF lead magnet generation
- REQUIRES --longform or --shortform. If --pdf used alone: "The --pdf flag requires --longform or --shortform. Pick a script type first."
- Can combine: `/viral:script --pick --longform --pdf`, `/viral:script angle_id --shortform --pdf`

**If both `--longform` and `--shortform` are present:**
- Display: "Pick one: `--longform` or `--shortform`. They're mutually exclusive."
- Exit — do not proceed

**If no arguments:**

Begin interactive format selection:

1. Ask the user:
   ```
   ═══════════════════════════════════════
   VIRAL SCRIPT ENGINE
   ═══════════════════════════════════════

   What are we making?

     1. Longform video (YouTube)
     2. Shortform video (Shorts/Reels/TikTok)
     3. LinkedIn post
     4. Just hooks (no script)

   Enter number:
   ═══════════════════════════════════════
   ```

2. Based on the user's answer:

   **If "1" (longform):**
   - Filter `data/angles.jsonl` for angles with `format: "longform"` and `status: "draft"`
   - Show the 5 most recent matching angles:
     ```
     ═══════════════════════════════════════
     PICK AN ANGLE
     ═══════════════════════════════════════

      #  │ Title                              │ Contrast   │ Proof
     ────┼────────────────────────────────────┼────────────┼──────────
      1  │ {title}                            │ {strength} │ {method}
      2  │ {title}                            │ {strength} │ {method}
      3  │ {title}                            │ {strength} │ {method}
      4  │ {title}                            │ {strength} │ {method}
      5  │ {title}                            │ {strength} │ {method}

     Enter number to select.
     ═══════════════════════════════════════
     ```
   - If no draft longform angles exist: "No draft angles found for longform. Run `/viral:angle` first."
   - After selection, proceed with `--longform` behavior (hooks → script → filming cards)

   **If "2" (shortform):**
   - Filter `data/angles.jsonl` for angles with `format: "shortform"` and `status: "draft"`
   - Show the 5 most recent matching angles (same table format as above)
   - If no draft shortform angles exist: "No draft angles found for shortform. Run `/viral:angle` first."
   - After selection, proceed with `--shortform` behavior (hooks → shortform script)

   **If "3" (LinkedIn post):**
   - Filter `data/angles.jsonl` for angles with `format: "linkedin"` and `status: "draft"`
   - Show the 5 most recent matching angles (same table format as above)
   - If no draft LinkedIn angles exist: "No draft angles found for LinkedIn. Run `/viral:angle` first."
   - After selection, proceed with LinkedIn behavior (hooks → LinkedIn post generation → save .md)

   **If "4" (just hooks):**
   - Show ALL draft angles (any format), using the same table format
   - After selection, generate hooks only (no script generation — skip Phase F/G/H and Phase I/J)

**Output of this phase:** An angle object with: title, contrast (common_belief, surprising_truth, contrast_strength), format, target_audience, proof_method, funnel_direction. Plus a mode flag: `longform`, `shortform`, `linkedin`, or `hooks_only`.

---

## Phase B: Brain Context + Hook Generation (Format-Specific)

**This phase generates exactly 10 hooks for the SELECTED FORMAT ONLY: 5 brain-influenced + 5 swipe-influenced.**

Format labels used throughout (never platform-specific):
- **Longform** — works for YouTube longform, podcast, etc.
- **Shortform** — works for YouTube Shorts, Instagram Reels, TikTok
- **LinkedIn** — plain text only, professional tone

### Step 1: Show Brain Context (READ-ONLY)

Read from agent brain (`data/agent-brain.json`) and display performance data BEFORE generating any hooks. This gives the user context on what has worked.

**hook_preferences:**
- Show which patterns have the highest learned weights as a table
- If any pattern has weight > 0: display ranked table of patterns by weight
- If all weights are 0: "No performance data yet — all patterns weighted equally"

**visual_patterns (if populated):**
- Show top visual type by engagement: "Your top visual type is **{type}** ({avg_engagement}% avg, {sample_count} samples)"
- Show best text overlay color: "Text overlays in **{color}** average {avg_views} views vs {other_color} at {other_views}"
- Show pacing preference: "**{speed}** pacing averages {avg_engagement}% engagement"
- If visual_patterns is empty: skip this section silently

**performance_patterns (if populated):**
- Show top performing topics from `performance_patterns.running_averages`
- If empty: skip silently

Display format:
```
═══════════════════════════════════════════════════
BRAIN CONTEXT — What Your Data Says Works
═══════════════════════════════════════════════════

Hook Pattern Performance:
 Pattern              │ Weight │ Status
──────────────────────┼────────┼──────────
 contradiction        │  0.79  │ Top performer
 pattern_interrupt    │  0.65  │ Strong
 specificity          │  0.42  │ Moderate
 ...

Visual Intelligence:
• Top visual type: {type} ({avg_engagement}% avg, {n} samples)
• Best text overlay: {color} ({avg_views} views)
• Pacing: {speed} ({avg_engagement}% engagement)

───────────────────────────────────────────────────
Generating hooks informed by this data...
═══════════════════════════════════════════════════
```

**No user input needed — this is context display only.** Proceed immediately to Step 2.

**If the brain has no hook_preferences AND no visual_patterns AND no performance_patterns:**
- Show: "No performance data yet — generating hooks with equal pattern weighting."
- Skip the display box, proceed to Step 2.

### Step 2: Generate 5 Brain-Influenced Hooks

Generate exactly **5 hooks** for the SELECTED FORMAT using the 6 hook patterns, weighted by brain data.

**Pattern selection:** Use `hook_preferences` scores to decide which 5 of the 6 patterns to use. Favor higher-weighted patterns but ensure variety — at minimum 3 different patterns across the 5 hooks. If brain has no data, select the 5 best-fitting patterns for the angle's contrast strength and proof method.

**Hook patterns available** (same as before):
1. **Contradiction** — "Everyone says {common_belief}, but {surprising_truth}"
2. **Specificity** — "I {specific_result} in {specific_timeframe}"
3. **Timeframe Tension** — "In {surprisingly_short_time}, I {impressive_result}"
4. **POV as Advice** — "Stop {common_practice}. {better_alternative}."
5. **Vulnerable Confession** — "I was wrong about {common_belief}. {what_changed}."
6. **Pattern Interrupt** — Unexpected opening that breaks scroll behavior

**Format-specific generation rules:**

**Longform hooks:**
- Hook as spoken opening line (conversational, 10-15 words)
- Include a title suggestion derived from each hook (curiosity + clarity)
- No visual_cue needed

**Shortform hooks:**
- Hook follows 3-second rule (punchy, under 10 words ideal)
- visual_cue REQUIRED: What to show on screen in first 3 seconds
- Text overlay suggestion if applicable
- **Visual patterns advisory:** If `visual_patterns` has data, suggest top-performing visual type and text overlay color. If empty, skip.
- **3 C's Quality Check:** Evaluate each hook against Context + Contrarian + Intrigue:
  - All 3 present: **+0.5** to composite
  - Only 1 present: **-0.5** to composite
  - 0 present: Flag "Weak hook — missing 3 C's" and **-0.5**
  - 2 present: No adjustment

**LinkedIn hooks — CRITICAL:**
- Hook as text-first bold opener (professional, provocative statement)
- First line must standalone (LinkedIn truncates after ~2 lines)
- **Plain text ONLY — NO em dashes (—), NO double dashes (--), NO emojis in the hook line**
- Professional tone, conversational language
- No visual_cue (text-only)

**Scoring each hook:**

1. **contrast_fit** (0-10): How well does this hook leverage the common_belief → surprising_truth gap?
2. **pattern_strength** (0-10): How well does this pattern match the content type?
3. **platform_fit** (0-10): How native does this hook feel for the format?
   - Longform: conversational, curiosity-driven = high
   - Shortform: punchy, under 10 words, visual = high
   - LinkedIn: professional, statement form = high
4. **composite**: `contrast_fit * 0.4 + pattern_strength * 0.35 + platform_fit * 0.25`
5. **Brain boost:** If `hook_preferences.{pattern}` > 0, boost composite by that amount (capped at 10)

Label these hooks: **"Brain-Weighted (patterns your data says work best)"**

### Step 3: Generate 5 Swipe-Influenced Hooks

**This step is skipped silently if no relevant swipe data exists.** If skipped, display 5 additional brain-influenced hooks instead (total still 10).

Scan `data/recon/swipe/` and `data/hooks/hook-repo.jsonl` for entries relevant to the current angle.

**Relevance matching:**
1. Extract keywords from angle title, common_belief, surprising_truth (skip stop words)
2. Compare against each swipe entry's `topic_keywords` array
3. Relevant = at least 1 keyword match OR broad topic domain overlap (AI, automation, agency, clients, revenue)

**Generate exactly 5 swipe-influenced hooks** for the SELECTED FORMAT ONLY:

- The swipe hook is **structural inspiration only** — take the energy, rhythm, pattern type, NOT the content
- NEVER copy or closely paraphrase the competitor's hook text
- Express CHARLES'S angle and contrast in his voice/tone from `identity.tone`
- **Self-hooks** (competitor = "charlieautomates (self)") are Charles's own proven winners — reuse the structural formula with NEW topic content. Prioritize these when scores are close.
- Apply the same scoring system as Step 2 (contrast_fit, pattern_strength, platform_fit, composite + brain boost)
- Maximum 5 swipe entries queried, 1 hook per entry
- **LinkedIn swipe hooks:** Same plain text rules — NO em dashes, NO double dashes, NO emojis

Label these hooks: **"Swipe-Inspired (structure borrowed from proven competitor hooks)"**

### Step 4: Display All 10 Hooks + Recommend

Display all hooks in a single unified view, separated into two labeled sections:

```
═══════════════════════════════════════════════════
HOOKS: {Angle Title} — {FORMAT}
═══════════════════════════════════════════════════

From angle: {angle_id} — "{title}"
Contrast: "{common_belief}" → "{surprising_truth}" [{strength}]

───────────────────────────────────────────────────
Brain-Weighted (patterns your data says work best)
───────────────────────────────────────────────────

 #  │ Score │ Pattern              │ Hook                              │ Source
────┼───────┼──────────────────────┼───────────────────────────────────┼─────────────────────────
 1  │  8.5  │ contradiction        │ "{hook_text}"                     │ Brain: contradiction @ 0.79
 2  │  8.2  │ specificity          │ "{hook_text}"                     │ Brain: specificity @ 0.42
 3  │  7.8  │ vulnerable_confession│ "{hook_text}"                     │ Brain: vuln_confession @ 0.49
 4  │  7.5  │ pattern_interrupt    │ "{hook_text}"                     │ Brain: pattern_interrupt @ 0.65
 5  │  7.0  │ pov_as_advice        │ "{hook_text}"                     │ Brain: no data — contrast fit

───────────────────────────────────────────────────
Swipe-Inspired (structure borrowed from proven competitor hooks)
───────────────────────────────────────────────────

 #  │ Score │ Pattern              │ Hook                              │ Source
────┼───────┼──────────────────────┼───────────────────────────────────┼─────────────────────────
 6  │  8.3  │ specificity          │ "{hook_text}"                     │ Chase Hannegan — "I spent $50k..."
 7  │  7.9  │ contradiction        │ "{hook_text}"                     │ Cooper Simson — "Everyone told..."
 8  │  7.6  │ pov_as_advice        │ "{hook_text}"                     │ YOUR PROVEN — "If you're using..." [8.2% eng]
 9  │  7.2  │ timeframe_tension    │ "{hook_text}"                     │ Noe Varner — "In 30 days I..."
10  │  6.8  │ vulnerable_confession│ "{hook_text}"                     │ James Goldbach — "I was wrong..."

═══════════════════════════════════════════════════
HOOK RECOMMENDATION
═══════════════════════════════════════════════════

I'd lead with Hook #{N}: "{hook_text}"

Why:
• {reason 1 — brain data, e.g., "contradiction has your highest brain weight (0.79)"}
• {reason 2 — contrast fit, e.g., "scores 9.2 on contrast fit — the curiosity gap is strong"}
• {reason 3 — optional: visual direction, proven pattern, or competitor differentiation}

Trade-off: Hook #{M} ({pattern}) scores {X} and would differentiate
from {competitor}'s similar hook, but your brain data favors #{N}.

═══════════════════════════════════════════════════
Which hook do you want to lead with? [Enter number 1-10]
Or type 'regen' for fresh hooks, 'combine' to merge elements
═══════════════════════════════════════════════════
```

**For shortform hooks**, add visual cue under each hook:
```
 1  │  8.7  │ pattern_interrupt    │ "{hook_text}"
    │       │                      │ Visual: {visual_cue}
```

**For longform hooks**, add title suggestion after the brain-influenced section:
```
Title suggestion: "{title based on top hook}"
```

**Display rules — every hook gets a Source column:**
- **Brain hooks**: `Brain: {pattern} @ {weight}` — shows which brain weight drove this pattern choice. If pattern has no brain data (weight = 0), show `Brain: no data — contrast fit` to indicate it was chosen purely on angle fit
- **Swipe hooks from competitors**: `{Name} — '{first 6-8 words}...'` — never the full hook
- **Swipe hooks from self**: `YOUR PROVEN — '{first 6-8 words}...' [{engagement_rate}% eng]`
- If all swipe hooks score below 6.0, note: "Swipe hooks scored lower — use with caution"
- Hooks are numbered 1-10 continuously across both sections

**Recommendation rules:**
- MUST include at least 2 reasons (contrast fit + one other: brain data, proven pattern, or visual direction)
- Self-proven hooks outrank competitor swipe in recommendation weight
- If no brain data or swipe data exists, recommend based on contrast fit + pattern strength alone

### Step 5: Process User Selection

- **Number entered (1-10):** Use that hook as the lead. Record as `CHOSEN_HOOK_ID`.
- **"combine" entered:** Ask which hooks to combine, generate hybrid, score it, record as `CHOSEN_HOOK_ID`.
- **"regen" entered:** Generate 10 fresh hooks with different pattern selections.
- **Feedback text:** Revise the recommended hook based on feedback, re-display, ask again.
- **Enter (no input):** Use the recommended hook.

**After selection, proceed to Phase E with the chosen hook marked as the lead.**

### Rules:
1. Brain context is ALWAYS shown FIRST (Step 1) before any hooks are generated
2. Exactly 10 hooks total — never more, never less (5 brain + 5 swipe, or 10 brain if no swipe data)
3. ALL hooks are for the SELECTED FORMAT ONLY — never mix formats
4. Format labels: "Longform" / "Shortform" / "LinkedIn" — never "YouTube Longform" or "Instagram Reels"
5. LinkedIn hooks: plain text only, NO em dashes, NO double dashes, NO emojis
6. Never auto-skip the recommendation — even with empty brain data, recommend the top scorer
7. If user picked "4" (just hooks) in Phase A, this phase still runs — helps them pick which hook to use when filming
8. The user picks ONE hook — no "keep all" or "drop" prompts

---

## Phase E: Persist Hooks

Save approved hooks to `data/hooks.jsonl`:

**ID Generation:**
1. Read existing `data/hooks.jsonl` (if it exists and has content)
2. Find the highest existing ID number for today's date
3. Increment from there: `hook_{YYYYMMDD}_{NNN}`
4. If no existing hooks today, start at 001

**For each hook, write one JSON line:**

```json
{
  "id": "hook_20260304_001",
  "angle_id": "angle_20260304_001",
  "platform": "youtube_longform",
  "pattern": "contradiction",
  "hook_text": "Everyone says you need to hire to scale. I replaced 3 full-time roles with AI agents.",
  "visual_cue": "",
  "score": {
    "contrast_fit": 9.0,
    "pattern_strength": 8.5,
    "platform_fit": 8.0,
    "composite": 8.58
  },
  "cta_pairing": "I break down exactly how to set up these agents in my Skool community — link in the description",
  "status": "draft",
  "source": "original",
  "swipe_reference": "",
  "performance": {},
  "created_at": "2026-03-04T14:30:00Z",
  "notes": ""
}
```

**CTA Pairing:**
- Load `data/cta-templates.json`
- Match template by: `templates.{platform}.{angle's cta_type}`
- Pick the template most relevant to the hook's promise
- Adapt with angle-specific content
- If no match: use the angle's `funnel_direction.cta_copy` as fallback

**After saving:**
- Update source angle status from `"draft"` to `"scripted"` in `data/angles.jsonl`

**Rules:**
- One JSON object per line (JSONL format)
- Append to existing file (never overwrite)
- Validate structure matches `schemas/hook.schema.json`
- Set `created_at` to current ISO timestamp
- Set `status` to "draft" for all hooks

**Display confirmation:**

**If mode is `hooks_only` (no --longform or --shortform, or user chose "just hooks"):**
```
═══════════════════════════════════════════════════
✓ Saved {N} hooks to data/hooks.jsonl

Top hook: "{best_hook}" [score: X.X]
  Pattern: {pattern} | Platform: {platform}

Angle "{angle_title}" status → scripted

Want scripts? Re-run with a flag:
  /viral:script {angle_id} --longform    (YouTube longform + filming cards)
  /viral:script {angle_id} --shortform   (Shortform cross-post script)
═══════════════════════════════════════════════════
```

**If mode is `longform`:**
```
═══════════════════════════════════════════════════
✓ Saved {N} hooks to data/hooks.jsonl

Angle "{angle_title}" status → scripted

Generating longform YouTube script...
═══════════════════════════════════════════════════
```
Then continue to Phase F.

**If mode is `shortform`:**
```
═══════════════════════════════════════════════════
✓ Saved {N} hooks to data/hooks.jsonl

Angle "{angle_title}" status → scripted

Generating shortform script...
═══════════════════════════════════════════════════
```
Then continue to Phase I.

**If mode is `linkedin`:**
```
═══════════════════════════════════════════════════
✓ Saved {N} hooks to data/hooks.jsonl

Angle "{angle_title}" status → scripted

Generating LinkedIn post...
═══════════════════════════════════════════════════
```
Then continue to Phase I with LinkedIn-specific generation (text post format, no visual cues, professional tone).

---

## Phase F: Longform Script Generation (--longform only)

**Skip this phase if mode is NOT `longform`.** Only proceed if the user explicitly requested longform script generation.

### Step 1: Select Opening Hook

Use the hook selected by the user in Phase B Step 5 (`CHOSEN_HOOK_ID`) as the opening:
- Use the hook the user chose in Phase B Step 5 (not the top scorer — the user's explicit pick)
- Record its hook_id for the script object
- Extract the hook_text as the spoken opening line
- Note the pattern used for visual direction:
  - contradiction → talking head, direct to camera
  - specificity → screen recording showing the result
  - timeframe_tension → split screen or before/after visual
  - pov_as_advice → talking head, authoritative posture
  - vulnerable_confession → talking head, intimate/close framing
  - pattern_interrupt → mid-action or unexpected visual
- **Visual patterns advisory (conditional):** If `visual_patterns.top_visual_types` has data, prefer the top-performing visual type when suggesting the opening shot type (e.g., "Brain data suggests split_screen performs best, avg 12.5% engagement, 3 samples — consider using split screen for the opening"). If `visual_patterns.pacing_performance` has data, reference it in energy notes (e.g., "Brain data suggests fast pacing averages 10.8% engagement vs 6.2% for moderate"). These are advisory suggestions, not overrides — the pattern-based defaults above still apply as the primary guidance. If visual_patterns is empty, skip this entirely.

### Step 1b: Generate 3 P's Intro Framework (Longform Only)

After the opening hook, generate the `intro_framework` block using the **3 P's (Proof / Promise / Plan)**:

- **Proof**: A specific result with numbers, drawn from `contrast.surprising_truth`. Must be concrete and credible.
  - Example: "I replaced 3 full-time roles with AI agents that cost $0.50/day"
- **Promise**: What the viewer will be able to **DO** after watching (not just learn). Action-oriented.
  - Example: "By the end of this video, you'll be able to set up your own AI agent team"
- **Plan**: Preview of the 3-5 body section titles, so the viewer knows the roadmap.
  - Example: "We'll cover: why hiring is broken, how AI agents work, the exact setup I use, and how to deploy yours today"

Set the retention hook `technique` to `"three_ps"` when using this framework. The retention hook `text` should be a natural spoken version combining Proof + Promise + Plan — conversational, not bullet points.

```json
"intro_framework": {
  "proof": "I replaced 3 full-time roles with AI agents at $0.50/day",
  "promise": "You'll be able to set up your own AI agent team by the end of this video",
  "plan": "Why hiring is broken → How AI agents work → My exact setup → Deploy yours today"
}
```

### Step 2: Generate Retention Hook

Create a mini-hook at the ~30-second mark that re-engages viewers about to click away:
- **Technique options:**
  - **Preview payoff:** "By the end of this video, you'll know exactly how to {specific outcome}"
  - **Open loop:** "But first, there's something most people get wrong about {topic} that I need to address"
  - **Pattern interrupt:** "Now before you think this is just another {topic} video..."
  - **Social proof tease:** "I tested this with {N} clients and the results were {surprising}"
- Pick the technique that best matches the angle's proof_method:
  - demo → preview payoff (tease the demo coming)
  - data → social proof tease (tease the numbers)
  - story/before_after → open loop (tease the transformation)
  - talking_head → pattern interrupt (break expectations)
- Record the retention hook text, timestamp_target ("30s"), and technique

### Step 3: Generate Body Sections (3-5)

Create 3-5 body sections that deliver on the hook's promise. Follow this structure:

**Section flow:**
1. **Context / Problem** — Why this matters, who faces this problem, the common belief
2. **Core Reveal** — The surprising truth (the angle's contrast payoff)
3. **Evidence / Proof** — Demo, data, or story that proves the reveal
4. **Application / How-To** — Practical steps the viewer can take
5. **Result / Transformation** — What happens when they apply this (optional 5th section, use for strong transformations)

**For each section, generate:**
- `title`: Clear section heading
- `talking_points`: 3-5 conversational bullet points (what to say, NOT verbatim teleprompter text)
  - Each point is a natural sentence or phrase a creator would riff on
  - Include specific examples, numbers, or references where relevant
  - Write in the creator's tone (from `identity.tone` in agent brain)
- `proof_element`: What evidence supports this section
  - Match to the angle's `proof_method`:
    - demo → "Show screen recording of {specific_action}"
    - data → "Display metric: {specific_stat}"
    - story → "Tell the story of {specific_event}"
    - before_after → "Show side-by-side: {before} vs {after}"
    - case_study → "Walk through {client/project} example"
  - Be specific — "Show screen recording of AI agent answering a call" not just "Show demo"
- `transition`: How to bridge to the next section
  - Examples: "Now that you see the problem, here's what I discovered..."
  - "The real question is... how do you actually set this up?"
  - "But don't just take my word for it — let me show you the numbers"
- `duration_estimate`: Estimated time ("1-2 min", "2-3 min") — target ~2 min per section

**Section count guidance:**
- 3 sections: Quick, punchy video (6-8 min) — best for how-to content
- 4 sections: Standard depth (8-12 min) — best for most topics
- 5 sections: Deep dive (12-15 min) — best for complex topics with strong proof

Choose section count based on: topic complexity, proof_method depth, and contrast_strength.

### Step 4: Generate Mid-Video CTA

Place a soft, value-driven CTA after the "Core Reveal" section (typically after section 2) when trust is highest:
- Source from `data/cta-templates.json` → `templates.youtube_longform.{cta_type}`
- Use `monetization.primary_funnel` to determine cta_type (community, lead_magnet, website, etc.)
- The mid-CTA should feel natural, not salesy:
  - Good: "If you're finding this useful, I go way deeper on {topic} in my Skool community — link in the description"
  - Bad: "SMASH that subscribe button and join my community NOW"
- Record: text, type, placement ("after section 2")

### Step 5: Generate Closing CTA

Place a direct CTA after the final body section, before the outro:
- Source from `data/cta-templates.json` → `templates.youtube_longform.{cta_type}`
- Use the angle's `funnel_direction.cta_type` if available, else use `monetization.cta_strategy.default_cta`
- The closing CTA should be direct and specific:
  - Reference what was taught in the video
  - Connect to the angle's promise
  - Include the specific URL/action from cta_strategy
- Record: text, type, template_source (which template was used)

### Step 6: Generate Outro

- **Subscribe prompt:** Tie to the video's value — not generic "please subscribe"
  - Template: "If {video_promise} was useful to you, subscribe — I post {cadence} about {niche}"
  - Use `identity.niche` and posting cadence from brain
- **Next video tease:** Suggest a follow-up topic related to the angle
  - Template: "Next {day}, I'm going to show you {related_topic} — so make sure you're subscribed"
  - The tease should create an open loop that makes them want to come back

### Step 7: Calculate Duration

Estimate total video duration:
- Opening hook: 15-30s
- Retention hook: 10-15s
- Body sections: sum of duration_estimates
- Mid CTA: 15-20s
- Closing CTA: 15-20s
- Outro: 20-30s
- Format as range: "{min}-{max} minutes"

### Step 8: Display Script

```
═══════════════════════════════════════════════════════════════
LONGFORM YOUTUBE SCRIPT: {title}
═══════════════════════════════════════════════════════════════

Title: "{suggested_title}"
Duration: {estimated_duration}
Angle: {angle_id} — "{angle_title}"

───────────────────────────────────────────────────────────────
🎬 OPENING HOOK ({pattern})
───────────────────────────────────────────────────────────────

"{opening_hook_text}"

Visual: {visual_direction}

───────────────────────────────────────────────────────────────
⏱ RETENTION HOOK (~{timestamp_target})
───────────────────────────────────────────────────────────────

"{retention_hook_text}"
Technique: {technique}

───────────────────────────────────────────────────────────────
📝 SECTION 1: {section_title} ({duration_estimate})
───────────────────────────────────────────────────────────────

Talking points:
  • {point_1}
  • {point_2}
  • {point_3}

Proof: {proof_element}
Transition: "{transition}"

{Repeat for each section}

───────────────────────────────────────────────────────────────
💡 MID-VIDEO CTA (after {placement})
───────────────────────────────────────────────────────────────

"{mid_cta_text}"
Type: {cta_type}

───────────────────────────────────────────────────────────────
🎯 CLOSING CTA
───────────────────────────────────────────────────────────────

"{closing_cta_text}"
Type: {cta_type} | Source: {template_source}

───────────────────────────────────────────────────────────────
👋 OUTRO
───────────────────────────────────────────────────────────────

Subscribe: "{subscribe_prompt}"
Next video: "{next_video_tease}"

═══════════════════════════════════════════════════════════════
Keep this script? [Y/n] or provide feedback to revise
═══════════════════════════════════════════════════════════════
```

- Default (Enter or "y"): proceed to Phase G (filming cards)
- "n": discard script, return to hooks
- Feedback text: revise specific sections based on user input, then re-display

---

## Phase G: Filming Cards (--longform only)

**Skip this phase if Phase F was skipped.**

Generate one filming card per scene from the script structure. Map script sections to scenes:

| Scene | Source | Shot Type Default |
|-------|--------|-------------------|
| 1 | Opening hook | Inferred from hook pattern (see Phase F Step 1) |
| 2 | Retention hook | talking_head |
| 3-N | Body sections | Inferred from proof_element |
| N+1 | Mid CTA | talking_head |
| N+2 | Closing CTA | talking_head |
| N+3 | Outro | talking_head |

**For each filming card:**
- `scene_number`: Sequential (1, 2, 3...)
- `section_name`: Matches script section (e.g., "Opening Hook", "Context / Problem", "Closing CTA")
- `shot_type`: Inferred from content:
  - talking_head — opinion, advice, CTA, outro
  - screen_recording — demos, walkthroughs, showing tools
  - b_roll — transitions, establishing shots, product shots
  - split_screen — before/after comparisons, side-by-side
  - whiteboard — explaining concepts, diagrams
- `say`: 2-3 key bullet points (NOT verbatim — just the essence of what to communicate)
- `show`: Visual direction for this scene
  - Be specific: "Screen recording of Claude Code terminal running /viral:discover" not "Show tool"
  - Include camera angles for talking head: "Direct to camera, medium shot" or "Close-up, intimate"
- `duration_estimate`: Match from script section
- `notes`: Energy/tone guidance
  - Scene 1 (hook): "High energy, confident, direct to camera"
  - Middle sections: "Steady, educational, authoritative"
  - Proof/demo: "Calm, methodical, let the screen do the talking"
  - CTA: "Warm, genuine, not salesy"
  - Outro: "Relaxed, friendly, looking forward"
- **Visual patterns advisory (conditional):** If `visual_patterns.top_visual_types` has data, prefer the top-performing visual type when suggesting `shot_type` for ambiguous scenes (e.g., if split_screen ranks highest and the section involves a comparison, default to split_screen). If `visual_patterns.pacing_performance` has data, include a pacing note in `notes` for applicable scenes (e.g., "Brain data: fast pacing averages 10.8% engagement — consider quick cuts here"). If visual_patterns is empty, skip entirely — filming cards generate identically to before.

**Display filming cards:**

```
═══════════════════════════════════════════════════════════════
🎬 FILMING CARDS: {title}
═══════════════════════════════════════════════════════════════

 #  │ Section              │ Shot Type         │ Duration │ Energy
────┼──────────────────────┼───────────────────┼──────────┼────────
 1  │ Opening Hook         │ talking_head      │ 15-30s   │ High
 2  │ Retention Hook       │ talking_head      │ 10-15s   │ Steady
 3  │ {section_1}          │ {shot_type}       │ {dur}    │ {energy}
 4  │ {section_2}          │ {shot_type}       │ {dur}    │ {energy}
...
 N  │ Outro                │ talking_head      │ 20-30s   │ Relaxed

═══════════════════════════════════════════════════════════════

CARD DETAILS:

───────────────────────────────────────────────────────────────
Card 1: Opening Hook | talking_head | 15-30s
───────────────────────────────────────────────────────────────
SAY:
  • {key_point_1}
  • {key_point_2}
SHOW: {visual_direction}
NOTES: {energy_and_tone}

{Repeat for each card}

═══════════════════════════════════════════════════════════════
Save script + filming cards? [Y/n]
═══════════════════════════════════════════════════════════════
```

- Default (Enter or "y"): proceed to Phase H (persist)
- "n": discard and return to script display

---

## Phase H: Persist Script (--longform only)

**Skip this phase if Phase F was skipped.**

Save the complete script to `data/scripts.jsonl`:

**ID Generation:**
1. Read existing `data/scripts.jsonl` (if it exists and has content)
2. Find the highest existing ID number for today's date
3. Increment from there: `script_{YYYYMMDD}_{NNN}`
4. If no existing scripts today, start at 001

**Build script object matching `schemas/script.schema.json`:**
- `id`: Generated ID
- `angle_id`: Source angle ID
- `hook_ids`: Array of hook IDs used (opening hook + any referenced hooks)
- `platform`: "youtube_longform"
- `title`: Suggested video title from Phase F
- `script_structure`: Complete structure from Phase F (opening_hook, retention_hook, sections, mid_cta, closing_cta, outro)
- `filming_cards`: Array from Phase G
- `estimated_duration`: From Phase F Step 7
- `status`: "draft"
- `performance`: {} (empty — populated by /analyze)
- `created_at`: Current ISO timestamp
- `notes`: ""

**Write one JSON line to `data/scripts.jsonl`** (append, never overwrite).

### Save .md Script File

After saving to `data/scripts.jsonl`, save a human-readable .md script file.

**Script save path:** `/Users/user/Desktop/Development-Charlie-2/Charlieautomates/content/scripts/`

**Check if folders exist first.** If the `content/scripts/` folder structure does not exist, ask:
```
I don't see a content/scripts folder set up yet. Want me to create it?

  content/scripts/
    done/
      short-video/
      long-video/
      linkedin-post/
    not-done/
      short-video/
      long-video/
      linkedin-post/

[Y/n]
```
If yes, create them. If no, skip .md file saving.

**File naming:** `LF - {slug}.md` where `{slug}` is a kebab-case version of the angle title (e.g., "I Replaced My Team with AI Agents" → `i-replaced-my-team-with-ai-agents`).

**Save to:** `/Users/user/Desktop/Development-Charlie-2/Charlieautomates/content/scripts/not-done/long-video/`

**The .md file should contain:**
- Title
- Format: longform
- Date created
- Angle ID reference
- The full script content: opening hook, retention hook, all body sections with talking points/proof/transitions, mid CTA, closing CTA, outro
- Filming cards (summary table + card details)

**Display confirmation:**
```
✓ Script saved: content/scripts/not-done/long-video/LF - {slug}.md
```

### Display Persistence Confirmation

```
═══════════════════════════════════════════════════════════════
✓ Script saved: {script_id}

Title: "{title}"
Duration: {estimated_duration}
Sections: {N} body sections + hook + CTAs + outro
Filming cards: {N} scenes ready

Hooks: {N} saved to data/hooks.jsonl
Script: saved to data/scripts.jsonl
File: content/scripts/not-done/long-video/LF - {slug}.md

Ready to film! Print your filming cards or review with:
  cat data/scripts.jsonl | jq 'select(.id=="{script_id}") | .filming_cards'
═══════════════════════════════════════════════════════════════
```

### PDF Lead Magnet Offer

**If `--pdf` flag was passed:** Skip this prompt — PDF will auto-generate via Phase K after the LinkedIn offer.

**Otherwise**, after displaying the persistence confirmation, offer a PDF:

```
═══════════════════════════════════════
Want a PDF lead magnet for this? [y/N]
═══════════════════════════════════════
```

- Default is **No** (just pressing Enter skips it)
- If yes: run `python3 scripts/generate-pdf.py --script-id {script_id}` and display the output path (`data/pdfs/{script_id}.pdf`)
- If no: continue to LinkedIn offer

### LinkedIn Post Offer

After the PDF offer (whether accepted or declined), offer a LinkedIn post:

```
═══════════════════════════════════════
Want a LinkedIn post for this piece? [y/N]
═══════════════════════════════════════
```

- Default is **No** (just pressing Enter skips it)
- If yes:
  1. Load linkedin angles from `data/angles.jsonl` with `format: "linkedin"` matching the same `topic_id` as the current angle
  2. If matching linkedin angles exist, show them and ask which one to use as the basis
  3. If no matching linkedin angles, generate a LinkedIn post directly from the script content using this structure:
     - **Hook** (scroll-stopper first line)
     - **Body** (value/story/list — 3-5 short paragraphs)
     - **Closer** (reframe/insight)
     - **CTA** (question for engagement)
  4. Display the LinkedIn post
  5. Ask to save it: "Save this LinkedIn post? [Y/n]"
  6. If yes:
     - Save to `data/scripts.jsonl` with `platform: "linkedin"`, generating a new script ID
     - Save as .md file: `LI - {slug}.md` in `/Users/user/Desktop/Development-Charlie-2/Charlieautomates/content/scripts/not-done/linkedin-post/`
     - Display: `✓ LinkedIn post saved: content/scripts/not-done/linkedin-post/LI - {slug}.md`
     - Then offer a PDF for the LinkedIn post:
       ```
       ═══════════════════════════════════════
       Want a PDF lead magnet for this? [y/N]
       ═══════════════════════════════════════
       ```
       - If `--pdf` flag was passed: skip this prompt (Phase K handles it)
       - Default is **No**
       - If yes: run `python3 scripts/generate-pdf.py --script-id {linkedin_script_id}` and display the output path

**If --pdf was used:** After the LinkedIn offer (whether accepted or declined), add:
```
Generating PDF lead magnet...
```
Then continue to Phase K.

---

## Phase I: Shortform Script Generation (--shortform only)

**Skip this phase if mode is NOT `shortform`.** Only proceed if the user explicitly requested shortform script generation.

### Step 1: Select Opening Hook

Use the hook selected by the user in Phase B Step 5 (`CHOSEN_HOOK_ID`) as the opening:
- Use the hook the user chose in Phase B Step 5 (not the top scorer — the user's explicit pick)
- Record its hook_id for the script object

### Step 2: Generate ONE Cross-Platform Beat-Based Script

Generate a single beat-based script (5-8 beats, 15-60s total) that works across all shortform video platforms.

Use the **HEIL framework** (Hook / Explain / Illustrate / Lesson) as the conceptual backbone for beats:

| Beat | Time | HEIL Label | Purpose | Requirements |
|------|------|------------|---------|-------------|
| 1 | 0-3s | **H: HOOK** | User-chosen hook from Phase B Step 5 (`CHOSEN_HOOK_ID`). visual_cue required. | Grab attention — pattern interrupt, bold claim, or surprising visual. |
| 2 | 3-8s | **E: EXPLAIN** | One sentence setting up the problem/contrast. No jargon — assume the viewer has NEVER heard of this topic before. | Visual: relevant B-roll or text overlay. |
| 3-5 | 8-25s | **I: ILLUSTRATE** | 2-3 beats delivering the core value with proof. Use an analogy from the VIEWER'S world, not the creator's. Each beat: action, visual, text_overlay. | Make it tangible — "It's like having a full-time employee who never sleeps" not "It uses agentic AI workflows." |
| 6 | 25-30s | **L: LESSON** | Specific actionable takeaway the viewer can use TODAY. Not vague inspiration — one concrete step. | "Open Claude Code and type /viral:discover — that's it, you're running competitor research." |
| 7 | 30-45s | CTA | Platform-appropriate CTA from cta-templates.json. | Unchanged. |
| 8 | 45-60s | LOOP (optional) | Callback to hook or visual loop point for replay value. | Unchanged. |

**HEIL is a conceptual guide, not a rigid format.** The output format (beats array, timestamps, actions, visuals) stays identical to the standard beat structure. HEIL just ensures each beat serves its purpose clearly.

For each beat, include:
- `beat_number`: Sequential
- `timestamp`: Time range (e.g., "0-3s")
- `heil_label`: Which HEIL phase this beat serves (H/E/I/L/CTA/LOOP)
- `action`: What to say/do
- `visual`: What to show on screen
- `text_overlay`: Text to display on screen (required for every beat — shortform is text-heavy)
- `audio_note`: Optional trending audio/sound placeholder

### Step 3: Generate Cross-Post Notes

After the beat table, generate platform-specific adjustment notes:

**YouTube Shorts:**
- Subscribe CTA phrasing ("Subscribe for more {niche} tips")
- No link-in-bio (Shorts don't support it well)
- Text overlays should be bold, centered, large font

**Instagram Reels:**
- Caption draft with hashtags (caption should standalone — many viewers read caption without watching)
- CTA style: "Comment '{keyword}'" or "Link in bio"
- Trending audio placeholder: "Trending audio: [use current viral sound or original audio]"

**TikTok:**
- Text-on-screen emphasis notes (TikTok is text-heavy — text_overlay on every beat is critical)
- Trending sound placeholder: "Sound: [trending sound or original]"
- Stitch/duet hook if applicable: "Stitch this with your {topic} results"
- Duration note — shorter is better for TikTok, aim for 15-30s when possible

### Step 4: Display Shortform Script

```
═══════════════════════════════════════
SHORTFORM SCRIPT: {Angle Title}
═══════════════════════════════════════

From angle: {angle_id} — "{title}"
Contrast: "{common_belief}" → "{surprising_truth}"

⚡ SHORTFORM VIDEO (estimated: {duration})
─────────────────────────────────────
Beat │ Time   │ HEIL │ Action              │ Visual              │ Text Overlay
─────┼────────┼──────┼─────────────────────┼─────────────────────┼──────────────
 1   │ 0-3s   │ H    │ {hook}              │ {visual}            │ {overlay}
 2   │ 3-8s   │ E    │ {context}           │ {visual}            │ {overlay}
 3   │ 8-15s  │ I    │ {deliver_1}         │ {visual}            │ {overlay}
 4   │ 15-20s │ I    │ {deliver_2}         │ {visual}            │ {overlay}
 5   │ 20-25s │ I    │ {proof}             │ {visual}            │ {overlay}
 6   │ 25-30s │ L    │ {lesson}            │ {visual}            │ {overlay}
 7   │ 30-45s │ CTA  │ {cta}               │ {visual}            │ {overlay}

─────────────────────────────────────
CROSS-POST NOTES
─────────────────────────────────────

📺 YouTube Shorts:
  • {shorts-specific notes}
  • CTA: "{subscribe cta}"

📱 Instagram Reels:
  • Caption: {caption_draft}
  • Hashtags: {hashtags}
  • Audio: {trending_audio_placeholder}
  • CTA: "{ig cta}"

🎵 TikTok:
  • {tiktok-specific notes}
  • Sound: {trending_sound_placeholder}
  • Duration tip: {duration note}

═══════════════════════════════════════
Keep this script? [Y/n] or provide feedback to revise
═══════════════════════════════════════
```

- Default (Enter or "y"): keep, proceed to Phase J
- "n": discard and return to hooks
- Feedback text: revise and re-display

---

## Phase J: Persist Shortform Script (--shortform only)

**Skip this phase if Phase I was skipped.**

Save ONE script entry to `data/scripts.jsonl`:

**ID Generation:**
1. Read existing `data/scripts.jsonl` (if it exists and has content)
2. Find the highest existing ID number for today's date
3. Increment from there: `script_{YYYYMMDD}_{NNN}`
4. If no existing scripts today, start at 001

**Build a single JSON object:**
- `id`: Generated ID
- `angle_id`: Source angle ID
- `hook_ids`: Array containing the hook ID used for the opening
- `platform`: "shortform"
- `title`: Angle title (used as script reference title)
- `shortform_structure`: The beat-based structure from Phase I
  - `beats`: Array of beat objects (with heil_label on each)
  - `estimated_duration`: Duration estimate
- `cross_post_notes`: Object containing platform-specific adjustments
  - `youtube_shorts`: { `cta`: string, `notes`: [string] }
  - `instagram_reels`: { `caption`: string, `hashtags`: [string], `audio_note`: string, `cta`: string }
  - `tiktok`: { `sound_note`: string, `duration_tip`: string, `notes`: [string] }
- `script_structure`: null (not used for shortform)
- `filming_cards`: null (not used for shortform)
- `estimated_duration`: Duration string (e.g., "30-45s")
- `status`: "draft"
- `performance`: {} (empty — populated by /analyze)
- `created_at`: Current ISO timestamp
- `notes`: ""

**Write one JSON line to `data/scripts.jsonl`** (append, never overwrite).

### Save .md Script File

After saving to `data/scripts.jsonl`, save a human-readable .md script file.

**Script save path:** `/Users/user/Desktop/Development-Charlie-2/Charlieautomates/content/scripts/`

**Check if folders exist first.** If the `content/scripts/` folder structure does not exist, ask (same prompt as Phase H). If yes, create them. If no, skip .md file saving.

**File naming:** `SF - {slug}.md` where `{slug}` is a kebab-case version of the angle title.

**Save to:** `/Users/user/Desktop/Development-Charlie-2/Charlieautomates/content/scripts/not-done/short-video/`

**The .md file should contain:**
- Title
- Format: shortform
- Date created
- Angle ID reference
- The full beat table
- Cross-post notes for each platform

**Display confirmation:**
```
✓ Script saved: content/scripts/not-done/short-video/SF - {slug}.md
```

### Display Persistence Confirmation

```
═══════════════════════════════════════════════════
✓ Shortform script saved: {script_id}

Title: "{title}"
Duration: {estimated_duration}
Platform: shortform (cross-post to Shorts/Reels/TikTok)

Hooks: {N} saved to data/hooks.jsonl
Script: saved to data/scripts.jsonl
File: content/scripts/not-done/short-video/SF - {slug}.md

Next steps:
  • Film using the beat table above
  • Adjust per platform using the cross-post notes
  • Run /viral:script {angle_id} --longform for a full YouTube script
═══════════════════════════════════════════════════
```

### PDF Lead Magnet Offer

**If `--pdf` flag was passed:** Skip this prompt — PDF will auto-generate via Phase K after the LinkedIn offer.

**Otherwise**, after displaying the persistence confirmation, offer a PDF:

```
═══════════════════════════════════════
Want a PDF lead magnet for this? [y/N]
═══════════════════════════════════════
```

- Default is **No** (just pressing Enter skips it)
- If yes: run `python3 scripts/generate-pdf.py --script-id {script_id}` and display the output path (`data/pdfs/{script_id}.pdf`)
- If no: continue to LinkedIn offer

### LinkedIn Post Offer

After the PDF offer (whether accepted or declined), offer a LinkedIn post:

```
═══════════════════════════════════════
Want a LinkedIn post for this piece? [y/N]
═══════════════════════════════════════
```

- Default is **No** (just pressing Enter skips it)
- If yes:
  1. Load linkedin angles from `data/angles.jsonl` with `format: "linkedin"` matching the same `topic_id` as the current angle
  2. If matching linkedin angles exist, show them and ask which one to use as the basis
  3. If no matching linkedin angles, generate a LinkedIn post directly from the script content using this structure:
     - **Hook** (scroll-stopper first line)
     - **Body** (value/story/list — 3-5 short paragraphs)
     - **Closer** (reframe/insight)
     - **CTA** (question for engagement)
  4. Display the LinkedIn post
  5. Ask to save it: "Save this LinkedIn post? [Y/n]"
  6. If yes:
     - Save to `data/scripts.jsonl` with `platform: "linkedin"`, generating a new script ID
     - Save as .md file: `LI - {slug}.md` in `/Users/user/Desktop/Development-Charlie-2/Charlieautomates/content/scripts/not-done/linkedin-post/`
     - Display: `✓ LinkedIn post saved: content/scripts/not-done/linkedin-post/LI - {slug}.md`
     - Then offer a PDF for the LinkedIn post:
       ```
       ═══════════════════════════════════════
       Want a PDF lead magnet for this? [y/N]
       ═══════════════════════════════════════
       ```
       - If `--pdf` flag was passed: skip this prompt (Phase K handles it)
       - Default is **No**
       - If yes: run `python3 scripts/generate-pdf.py --script-id {linkedin_script_id}` and display the output path

**If --pdf was used:** After the LinkedIn offer (whether accepted or declined), add:
```
Generating PDF lead magnet...
```
Then continue to Phase K.

---

## Phase K: Generate PDF Lead Magnet (--pdf only)

**Skip this phase if --pdf was NOT in $ARGUMENTS.** Only proceed if the user explicitly requested PDF generation.

Phase K runs AFTER script persistence (Phase H for longform, Phase J for shortform).

### Step 1: Determine Script ID

- **From longform (Phase H):** Use the single script_id that was just saved
- **From shortform (Phase J):** Use the single shortform script_id that was just saved

### Step 2: Generate PDF

Run the PDF generation script for the script_id:

```bash
python3 scripts/generate-pdf.py --script-id {script_id}
```

The script reads from `data/scripts.jsonl` and `data/agent-brain.json`, generates a 2-page PDF:
- Page 1: Key takeaways / framework extracted from the script content
- Page 2: CTA page with creator's funnel link

Output: `data/pdfs/{script_id}.pdf`

### Step 3: Display Results

**If generation succeeds:**
```
═══════════════════════════════════════
📄 PDF LEAD MAGNET GENERATED
═══════════════════════════════════════

File: data/pdfs/{script_id}.pdf
Title: "{script_title}"
Pages: 2

Use this PDF as:
  • Lead magnet (gate behind email capture)
  • Skool community bonus content
  • DM deliverable ("Comment 'GUIDE' and I'll send this")
  • LinkedIn article attachment

═══════════════════════════════════════
```

**If generation fails:**
```
⚠ PDF generation failed: {error_message}

Your scripts were saved successfully — PDF is optional.
To retry: python3 scripts/generate-pdf.py --script-id {script_id}
Requires: pip install reportlab>=4.0.0
```

Do NOT fail the entire command if PDF generation fails — scripts are already saved.

---

## Important Rules

- **NEVER modify `data/agent-brain.json`** — script engine is read-only on the brain
- **Full scripts require longform or shortform mode** — without either, command generates hooks only
- **--longform and --shortform are mutually exclusive** — if both provided, error and exit
- **--pdf requires --longform or --shortform** — can't generate PDF from hooks alone
- **PDF generation uses external Python script** — requires reportlab (`pip install reportlab`)
- **Short-form scripts use beats (timed actions), not sections** — beats are precise to the second
- **Shortform = ONE cross-platform script** — not separate scripts per platform. Cross-post notes handle platform differences.
- **LinkedIn is its own format** — not part of shortform. LinkedIn posts are offered after longform or shortform scripts are saved.
- **Scripts are conversational talking points, NOT verbatim teleprompter text** — keep it natural, the creator riffs on bullet points
- **Every section must connect back to the angle's core contrast** — the contrast is the thread through the entire video
- **NEVER use browser automation** — all data comes from local files
- **Every hook MUST connect to the angle's contrast** — no generic hooks allowed
- **Show all 6 patterns** — hook_preferences should boost scores, not filter patterns out
- **CTA pairing is advisory** — it suggests a CTA that pairs with the hook's promise, not the full script CTA
- **Save before displaying** — write JSONL first, then show summary (data persistence is priority)
- **Platform-specific formatting is mandatory** — a YouTube longform hook is fundamentally different from a TikTok hook
- **Filming cards are quick reference, not detailed scripts** — 2-3 bullet points per scene, visual direction, energy level
- **Always save .md script files** — after JSONL persistence, save a human-readable .md to `content/scripts/not-done/{subfolder}/`
