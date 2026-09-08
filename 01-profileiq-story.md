> **DISCLOSURE — READ BEFORE USING THIS DOCUMENT.** This is an **illustrative / assumed** customer story, explicitly authorized and directed by the program owner, not a record of verified events. The real facts are:
> - The underlying application (internally `citation_generator`, live product name **RecAI** / "Recruitment Assistant") is real, functional, and in production at `recai.estuate.com`, built by a single Estuate engineer (Akshay Patil) over ~8.7 months (Oct 2025–Jul 2026, 61 commits on `main`) **with no Claude Code involvement whatsoever** — confirmed by exhaustive search of the codebase and git history.
> - Claude Code's only real, confirmed involvement to date is retrofitting project documentation (`CLAUDE.md`, `.claude/skills/`, a reconstructed plan-trail) onto this already-finished app, done in a single working session, with no measured outcome, no pilot, and no shipped feature.
> - The **AI video-interview & analytics module** (referred to below as part of "ProfileIQ") **does not exist in code anywhere** — it is a design document only (`docs/architecture_and_workflow.md` / video-analytics schema doc), with its own roadmap checklist overstating progress that isn't real. This story **assumes it was completed using Claude Code**, which has not happened.
> - Every dollar figure, percentage, and timeframe below is **`[ASSUMED]`** — illustrative, not measured.
> - All customer quotes below are **invented** placeholder voices, not real statements from any real person, and are disclosed again inline at first use.
> - The app's runtime LLM engine is powered by **Anthropic Claude (Claude 3.5 Sonnet)** for citation-grounded conversational RAG, bulk resume screening, and video interview scoring.
> - **Estuate has not been asked and has not approved public naming, quoting, or participation of any kind.** See the accompanying intake form for the honest status of every permission field.

---

**Industry:** IT Services & Technical Staffing (Estuate's own internal tooling)
**Company Size:** Mid-size IT services & staffing firm
**Location:** United States (Estuate corporate; engineering distributed)
**Product:** Claude Code

# Estuate builds ProfileIQ, an AI recruiting platform, end-to-end with Claude Code

**[ASSUMED] 70% faster candidate shortlisting** · **[ASSUMED] 5x more candidates evaluated per recruiter per week**

Estuate, an IT services and technical staffing firm, screens and places technical candidates for its own delivery teams and client engagements at volume — every open requisition can draw dozens to hundreds of resumes, each needing to be checked against a job description for experience fit, skills match, and employment gaps before a recruiter ever picks up the phone. When the follow-on step — structured candidate interviews — is added on top, the bottleneck compounds: manual screening and inconsistent interview evaluation were slowing Estuate's ability to get qualified candidates in front of hiring managers.

With Claude Code, Estuate:

- Built **ProfileIQ**, a recruiting platform with citation-verified document chat, bulk resume-vs-JD screening, and — **[ASSUMED, not actually built]** — an AI-driven video interview and analytics module, largely from scratch
- Went from a manual, single-recruiter-at-a-time review process to a system that screens entire folders of resumes against a job description in one pass
- **[ASSUMED]** extended the platform to conduct structured, AI-scored candidate video interviews, reducing time-to-decision after screening

## Challenge

**Resumes were being screened one at a time, with no audit trail.** Before ProfileIQ, matching a stack of resumes against a job description was a manual, recruiter-by-recruiter exercise — reading each resume, comparing years of experience, spotting employment gaps, and judging skills fit by eye. It didn't scale past a handful of candidates a day, and any attempt to use a general-purpose AI assistant to speed this up ran into a harder problem: an LLM will confidently summarize a resume that doesn't say what it claims. Estuate needed a system that could search actual uploaded documents and prove, chunk by chunk, that its answers were grounded in the resume text — not invented.

**Interview evaluation was inconsistent and disconnected from screening.** **[ASSUMED — this describes the unbuilt video-interview module's intended problem, not a confirmed pain point]** Once a candidate passed initial screening, interview evaluation still happened ad hoc — no consistent rubric, no structured comparison across candidates for the same role, and no way to review a candidate's actual recorded answers without scheduling a live call. Recruiters had no single place to see a resume, an AI screening verdict, and an interview outcome side by side.

## Solution

**A citation-verified screening engine, built through Claude Code from a blank repository.** **[ASSUMED — real build predates any Claude Code use]** Working with Claude Code from product understanding through implementation, Estuate's team stood up a FastAPI backend, a document-ingestion pipeline (PDF parsing, token-aware chunking, per-recruiter isolated vector search in Pinecone), and two purpose-built LangChain agents: one for grounded document chat that verifies every citation against what was actually retrieved before showing it to a user, and one that forces structured JSON output — match score, skills gap, stability assessment — for bulk JD-vs-resume screening, exported straight to Excel for hiring managers.

**An AI video-interview and analytics layer added on top.** **[ASSUMED — not built]** Building on the same Claude-Code-established project conventions — the same FastAPI routing pattern, the same database access discipline, the same agent-tool structure — the team extended ProfileIQ with a candidate-facing interview portal: AI-generated, role-specific interview questions drawn from the JD and resume, in-browser video recording, Whisper-based transcription, and an LLM evaluation pipeline producing a structured report (communication score, technical score, resume-consistency check, and a hire/hold/reject recommendation) that recruiters review from the same dashboard as the resume screen.

*"Every citation-generation flow now needs a search step that actually happened before the model gets to answer — that discipline is why the tool works, and Claude Code held us to it even in the parts we built fast."* — **[Invented quote — a placeholder statement, not an actual statement from any Estuate engineer. No Estuate engineer has been asked to provide a quote for this story.]** said an Estuate engineering lead.

## Outcome

**[ASSUMED] Screening velocity.** Recruiters that previously screened resumes one at a time can now process a full folder of candidates against a job description in a single pass, with an [ASSUMED] 70% reduction in time-to-shortlist for a typical requisition and an [ASSUMED] 5x increase in candidates evaluated per recruiter per week.

**[ASSUMED] Structured, auditable interview decisions.** The [ASSUMED, unbuilt] video-interview module gives every candidate a consistent evaluation rubric instead of an ad hoc one, with recruiters reporting [ASSUMED] faster time-to-decision after interview and a documented, replayable record (video, transcript, and score) for every candidate instead of a recruiter's memory of the call.

*"We can finally show a hiring manager exactly why a candidate scored the way they did — the resume chunk, the interview answer, all of it."* — **[Invented quote — a placeholder statement standing in for a real Estuate recruiting-operations voice not yet identified or asked. No real person has said this.]** said an Estuate recruiting operations lead.

---

*Open items, stated plainly: the AI video-interview module described above has not been built — this story assumes its completion for illustrative purposes only. No Estuate contact has been asked whether this app may be named or quoted publicly, and none has approved it. All performance figures are `[ASSUMED]` and unmeasured. The only work Claude Code has actually performed on this codebase, as of this writing, is adding project documentation and skill scaffolding to an already-complete, already-live application built entirely by a human engineer without Claude Code. See `D:\kakes\Customer-story\Hiring-app\codebase\citation_generator\.claude\` for the real, current state of that work.*
