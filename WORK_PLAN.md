# SchemaScope Public Build Plan

## Current State

SchemaScope is no longer an empty project. The merged codebase already contains:

- A FastAPI backend in `api/`.
- A Vite + React frontend in `frontend/`.
- Connectors for SQLite, MySQL, and SQL dump uploads.
- SQL schema analysis logic.
- Rule-based recommendations.
- Mermaid ER diagram generation.
- Markdown, JSON, and Mermaid exports.
- A test suite under `tests/`.
- Supporting docs under `docs/`.
- A Windows helper script, `start.bat`, that starts backend and frontend together.
- A SQL type normalization debug script, `debug_types.py`.

The plan should now focus on making the existing app reliable, easy to run, easy to demo, and safe enough for public users.

## Product Direction

Build SchemaScope as a public, read-only schema understanding tool.

The first public release should support this workflow:

```text
Connect or upload schema
-> Analyze database structure
-> Explore tables and fields
-> View ER diagram
-> Review recommendations
-> Export Markdown, JSON, or Mermaid
```

The product promise:

> Turn an unfamiliar database schema into a clear diagram, useful documentation, and practical improvement suggestions.

## Priority 1: Stabilize The Existing Codebase

Before adding new features, make the current app reproducible.

- Add a backend dependency file, such as `requirements.txt` or `pyproject.toml`.
- Include all currently required packages:
  - `fastapi`
  - `uvicorn`
  - `sqlalchemy`
  - `pymysql`
  - `pytest`
  - any other package imported by the backend or tests
- Verify `python -m pytest` runs from a clean setup.
- Remove generated local files from the repo if present, such as `__pycache__` and `.pytest_cache`.
- Confirm the backend starts with one documented command.
- Confirm the frontend starts with one documented command.
- Verify `start.bat` works on a clean Windows setup after dependencies are installed.
- Decide whether `debug_types.py` should remain as a documented developer utility or move under a `scripts/` folder.
- Confirm frontend API URLs work consistently in local development.

Exit condition:

- A new developer can clone the repo, install dependencies, run tests, start backend, and start frontend.

## Priority 2: Rewrite The README For Public Users

The current README is too small for a public project.

Add:

- What SchemaScope does.
- Screenshots or GIF placeholders.
- Supported inputs:
  - SQLite database files
  - MySQL connection
  - MySQL SQL dump upload
- What outputs are produced:
  - schema explorer
  - ER diagram
  - recommendations
  - Markdown export
  - JSON export
  - Mermaid export
- Local setup instructions.
- Backend run command.
- Frontend run command.
- Windows quick-start command using `start.bat`.
- Test command.
- Safety note: SchemaScope is designed to inspect, not modify.
- Privacy note: schema names may be sensitive.
- Known limitations.
- Roadmap.

Exit condition:

- Someone visiting GitHub can understand and run the app without asking for help.

## Priority 3: Confirm The MVP Scope

Because the repo already has multiple connectors, define what is officially supported for the first public release.

Public MVP should include:

- SQL dump upload as the easiest demo path.
- SQLite support if the existing connector works end to end.
- MySQL support as read-only connection support.
- Schema explorer.
- Mermaid ER diagram.
- Rule-based recommendations.
- Export to Markdown, JSON, and Mermaid.

Defer for now:

- MongoDB support.
- Authentication.
- Saved cloud projects.
- Team collaboration.
- AI-generated recommendations.
- Automatic schema changes.
- Production database monitoring.

Exit condition:

- Public docs and UI match the features that actually work.

## Priority 4: Verify The Core User Flow

Create a repeatable manual test using sample schemas.

Required sample files:

- Small SQL dump with 3 to 5 related tables.
- Larger SQL dump that exercises diagram filtering.
- SQLite database fixture if SQLite is public MVP.
- MySQL fixture instructions if live MySQL is tested manually.

Manual acceptance flow:

1. Start backend.
2. Start frontend.
3. Upload SQL dump.
4. Run analysis.
5. Confirm tables and fields appear.
6. Confirm ER diagram renders.
7. Confirm recommendations appear.
8. Export Markdown.
9. Export JSON.
10. Export Mermaid.
11. Start over and analyze another file.

Exit condition:

- The full flow works without developer intervention.

## Priority 5: Strengthen Safety And Privacy

Public users need confidence that SchemaScope is safe.

- Make read-only behavior explicit in README and UI.
- Ensure generated SQL suggestions are copy-only and never executed.
- Mask passwords and sensitive connection strings.
- Avoid logging raw credentials.
- Avoid exporting credentials.
- Add request size limits for uploaded SQL dumps.
- Add clear warnings that table and column names may still be sensitive.
- Document that users should prefer read-only database accounts.

Exit condition:

- No credentials are exposed in UI, logs, exports, or test snapshots.

## Priority 6: Improve Error Handling

Public apps need useful failures.

- Convert raw backend exceptions into user-friendly API errors.
- Show frontend error states for:
  - invalid SQL dump
  - unsupported file type
  - MySQL connection failure
  - missing backend
  - export failure
  - empty schema
- Keep technical details available for debugging where useful.
- Add tests for common error cases.

Exit condition:

- A failed analysis explains what the user can try next.

## Priority 7: Test Coverage

Keep tests focused on public behavior and safety.

Backend tests:

- SQL dump parsing.
- SQLite connector if supported.
- MySQL connector behavior with mocked connection where practical.
- Schema model serialization.
- Mermaid generation.
- Recommendation rules.
- Exporters.
- API routes.
- Session restore.
- Secret masking.

Frontend checks:

- Build succeeds with `npm run build`.
- Main tabs render.
- Upload/connect form handles errors.
- Export buttons call expected API paths.

Exit condition:

- Backend tests pass.
- Frontend build passes.
- Known test gaps are documented.

## Priority 8: Polish The Web Interface

The first screen should be the usable tool.

Improve:

- Connect tab clarity.
- SQL dump upload path.
- Empty state before analysis.
- Loading state during analysis.
- Start-over flow.
- Diagram filtering for large schemas.
- Recommendation severity display.
- Export button feedback.
- Mobile layout.

Avoid:

- Marketing-only landing pages.
- Hidden instructions that users need before trying the app.
- UI text that promises unsupported features.

Exit condition:

- A first-time user can complete the SQL dump flow without reading docs.

## Priority 9: Deployment Preparation

Prepare for hosting, even if the first public release is local-only.

- Add environment variable configuration for API base URL.
- Add production CORS configuration.
- Add health check documentation for `/api/health`.
- Add backend start command for deployment.
- Add frontend build instructions.
- Decide whether deployment is:
  - single combined service
  - separate frontend and backend
- Add deployment notes for Render, Railway, Fly.io, Vercel, or Netlify.

Exit condition:

- The project can be deployed without changing source code.

## Priority 10: Public Release Checklist

Before announcing or sharing broadly:

- README is complete.
- Work plan is current.
- License is added.
- Dependencies are documented.
- Tests pass.
- Frontend builds.
- Sample schema exists.
- Public MVP features are listed accurately.
- Known limitations are listed.
- Safety and privacy notes are visible.
- GitHub issues are enabled.
- Optional: add screenshots.

Exit condition:

- The repo is understandable, runnable, and demoable by someone outside the project.

## Recommended Build Order

1. Add backend dependency file.
2. Clean generated cache files.
3. Verify or revise `start.bat` for Windows local startup.
4. Decide where developer scripts like `debug_types.py` should live.
5. Make backend tests pass.
6. Make frontend build pass.
7. Add sample SQL dump.
8. Rewrite README.
9. Verify upload -> analyze -> diagram -> recommendations -> export flow.
10. Improve API and UI error states.
11. Add safety and privacy checks.
12. Add deployment configuration notes.
13. Tag the first public MVP release.

## First Public Milestone

The first milestone should be:

> A user can upload a SQL dump, view parsed tables, see an ER diagram, review recommendations, and export Markdown, JSON, and Mermaid from the browser.

This uses the strongest existing path in the current codebase and gives SchemaScope a complete public demo quickly.

## Later Roadmap

After the public MVP is stable:

- Improve SQLite support and examples.
- Harden MySQL live connection support.
- Add PostgreSQL support.
- Add schema comparison.
- Add saved local projects.
- Add richer diagram controls.
- Add PNG or PDF export.
- Add optional AI explanation layer.
- Add authentication only if cloud persistence becomes necessary.

## Non-Negotiables

- SchemaScope must not modify source databases.
- Recommendations are advisory, not automatic.
- Credentials must never appear in exports.
- Public documentation must match actual behavior.
- New features should not outrun tests.
