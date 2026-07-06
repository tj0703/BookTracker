---
name: plan
description: Use when the user wants a technical plan, design, or set of options for a feature/change/requirement WITHOUT any code being written or files being modified — e.g. "plan out X", "how should we approach Y", "give me some options for Z", "review this spec". Read-only: produces a plan/analysis, never edits code.
---

# Plan

Produce a technical plan, design, or set of options for the requested
feature, change, or requirement — without modifying anything.

## Rules

- **Never edit or write files**, run code, install packages, or execute any
  command that changes repository or system state. This skill is read-only:
  investigate, reason, and report back in text.
- If asked to review a spec or requirement, evaluate it — don't rewrite it
  in place.
- If you need to inspect the codebase to ground the plan (existing
  architecture, conventions, constraints), read files and search the
  codebase, but stop at reading.

## What to produce

1. **Problem restated**: a one- or two-line restatement of what's being
   asked, surfacing any ambiguity you notice.
2. **Options**: 2–3 viable approaches where more than one reasonable path
   exists, each with the core tradeoff (what you gain, what it costs). If
   there's a clear best approach, lead with a recommendation instead of
   forcing artificial options.
3. **Plan**: for the recommended (or chosen) approach — the components
   involved, key interfaces/data changes, sequencing, and risks or open
   questions that should be resolved before implementation.
4. **Explicit non-action**: end by stating that no files were changed and
   this is ready for the user to review, redirect, or approve before any
   implementation begins.

## Operating principles

- Favor the simplest approach that satisfies the actual requirement — no
  speculative abstractions for hypothetical future needs.
- Surface unknowns as explicit open questions rather than silently assuming
  an answer.
- Keep the plan consistent with the existing system's architecture and
  conventions unless a deviation is justified and called out.
- Treat non-functional requirements (security, scalability, maintainability)
  as first-class when relevant, not afterthoughts.
- Do not proceed to implementation after presenting the plan — wait for the
  user to approve or redirect.
