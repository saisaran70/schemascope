# SchemaScope Work Plan

## Goal

Build SchemaScope into a public web app that helps people understand database schemas, generate ER diagrams, identify design issues, and improve their data models.

## Public MVP

The first public version should focus on one clear workflow:

1. User uploads or pastes SQL schema text.
2. SchemaScope parses tables, columns, primary keys, foreign keys, and relationships.
3. The app generates an ER diagram.
4. The app explains the schema in plain language.
5. The app highlights improvement opportunities.
6. User can export or copy the results.

## Priority 1: Product Definition

Before writing core application code, define exactly what the first version will and will not do.

- Confirm the first supported input format: SQL DDL files and pasted SQL text.
- Define the target user: students, developers, analysts, data engineers, or database designers.
- Decide the first supported SQL dialects: start with PostgreSQL-style SQL, then expand later.
- Define the main output types: ER diagram, schema summary, issues, and suggestions.
- Decide whether uploaded schemas are stored or processed temporarily only.

## Priority 2: Project Foundation

Set up a clean structure that can grow without becoming messy.

- Create a backend API.
- Create a frontend app.
- Add a parser module for turning SQL into structured schema data.
- Add a diagram generation module.
- Add tests for parser behavior.
- Add project documentation and local setup instructions.
- Add sample schemas for testing and demos.

Suggested structure:

```text
schemascope/
  backend/
    app/
      main.py
      parser/
      analyzer/
      diagram/
      models/
    tests/
  frontend/
  examples/
  docs/
```

## Priority 3: SQL Schema Parser

This is the heart of the MVP.

- Parse `CREATE TABLE` statements.
- Extract table names.
- Extract column names and data types.
- Detect primary keys.
- Detect foreign keys.
- Detect nullable and unique columns where possible.
- Return clean JSON that the frontend can display.
- Handle invalid SQL with useful error messages.

Success criteria:

- A sample SQL file can be uploaded or pasted.
- The backend returns a structured list of tables, columns, and relationships.
- Parser behavior is covered by tests.

## Priority 4: ER Diagram Generation

Once schema data exists, make it visible.

- Convert parsed schema JSON into a diagram-friendly format.
- Start with Mermaid ER diagram output for speed.
- Show entities, columns, and relationships.
- Support copy/export of Mermaid text.
- Later, add an interactive visual diagram with pan, zoom, and selection.

Success criteria:

- A parsed schema produces a readable ER diagram.
- Relationships are visible and correctly labeled.

## Priority 5: Schema Analysis

Add useful feedback beyond visualization.

- Detect tables without primary keys.
- Detect foreign key columns without declared constraints.
- Detect suspicious duplicate column patterns.
- Detect overly generic table or column names.
- Detect missing indexes for likely foreign keys.
- Detect nullable columns that may need review.
- Provide plain-language improvement suggestions.

Success criteria:

- The app produces a concise report with actionable findings.
- Each finding explains why it matters.

## Priority 6: Web Interface

Build the actual public-facing experience.

- Create a focused single-page workflow.
- Add SQL paste area.
- Add file upload for `.sql`.
- Show parser results.
- Show ER diagram.
- Show analysis report.
- Add loading, empty, and error states.
- Add sample schema button for first-time users.

Success criteria:

- A user can try SchemaScope without reading instructions.
- The first screen is the working tool, not a marketing page.

## Priority 7: Export And Sharing

Make results portable.

- Copy schema summary.
- Copy Mermaid diagram.
- Download analysis report as Markdown.
- Download parsed schema as JSON.
- Later, add PNG/PDF diagram export.
- Later, add shareable private links.

Success criteria:

- Users can take the output into docs, tickets, or presentations.

## Priority 8: Public Readiness

Prepare the project for real users.

- Improve README with screenshots, setup, examples, and roadmap.
- Add license.
- Add privacy note for uploaded schema data.
- Add contribution guidelines.
- Add basic issue templates.
- Add deployment instructions.
- Add demo data.
- Add clear limits for unsupported SQL features.

Success criteria:

- A stranger can understand, run, and try the project from GitHub.

## Priority 9: Deployment

Get the MVP online.

- Deploy frontend.
- Deploy backend API.
- Configure environment variables.
- Add simple health check endpoint.
- Add request size limits.
- Add basic logging.
- Add CORS configuration.

Suggested early deployment path:

- Frontend: Vercel or Netlify.
- Backend: Render, Railway, Fly.io, or a small VPS.

Success criteria:

- A public URL exists and can process a sample schema end to end.

## Priority 10: Later Enhancements

After the MVP is working, expand carefully.

- Support MySQL, SQLite, SQL Server, and Oracle dialects.
- Add database connection import.
- Add ER diagram image upload.
- Add AI-powered schema explanation.
- Add schema version comparison.
- Add normalization checks.
- Add index recommendations.
- Add team workspaces.
- Add saved projects.
- Add authentication.
- Add role-based access control for teams.

## Recommended Build Order

1. Create backend skeleton.
2. Add SQL parser.
3. Add parser tests.
4. Add example SQL schemas.
5. Add analysis rules.
6. Add Mermaid diagram generation.
7. Create frontend tool interface.
8. Connect frontend to backend.
9. Add export options.
10. Improve README and public docs.
11. Deploy MVP.

## First Milestone

The first milestone should be:

> Paste SQL into SchemaScope and receive parsed tables, relationships, an ER diagram, and a short improvement report.

This gives the project a complete and useful loop before adding accounts, storage, payments, or advanced AI features.
