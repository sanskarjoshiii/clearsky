# AGENTS.md

Instructions for any AI coding assistant (Codex, Cursor, Copilot, Gemini, Claude, …) working on **clearsky**. Claude Code reads `CLAUDE.md`, which has the same rules.

1. **Read `CONTEXT.md` first.** It is the living summary of what's built, what's decided, and what's next.
2. Then read `README.md`, `IMPLEMENTATION.md` (design source of truth), `PLAN.md` (order and scope) and `PROGRESS.md` (once it exists).
3. **After every change you make, update `CONTEXT.md`** following the rules at the top of that file. A change isn't done until `CONTEXT.md` reflects it.
4. Key constraints:
   - Monorepo: backend, infra, dashboard, data, satellite, video in one repo.
   - WhatsApp serves **farmers only**. Operators, buyers and officers use the web dashboard.
   - Never invent secrets, model IDs, phone numbers or real-world statistics; ask.
   - Never deploy, delete or create paid AWS resources without explicit approval.
   - Never commit `.env` or secrets.
5. "Implement phase N" means: follow `PLAN.md` §0 exactly.
