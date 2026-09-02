Review memory analysis below and produce a concise non-mutating summary.
- [FILE] entries: state what should be added to the target file
- [FILE-REMOVE] entries: state what should be removed from the target file
- [SKILL] entries: state the recommended skill path under skills/<name>/SKILL.md

## File paths (relative to workspace root)
- SOUL.md
- USER.md
- memory/MEMORY.md
- skills/<name>/SKILL.md (for [SKILL] entries only)

Do NOT guess paths.

## Output rules
- Read-only mode: do not call write/edit tools
- File contents are provided below; avoid redundant read_file calls unless needed
- For each change, include target file + exact before/after snippet proposal
- If nothing to update, output "No changes required."

## Skill recommendation rules (for [SKILL] entries)
- Do not create files directly
- Read `{{ skill_creator_path }}` for format reference (frontmatter structure, naming conventions, quality standards)
- **Dedup check**: read existing skills listed below to verify the new skill is not functionally redundant. Skip creation if an existing skill already covers the same workflow.
- Include YAML frontmatter guidance with name and description fields
- Keep SKILL.md under 2000 words — concise and actionable
- Include: when to use, steps, output format, at least one example
- Do NOT overwrite existing skills — recommend skip if the skill directory already exists
- Reference specific tools available to runtime (read_file, exec, web_search, etc.)
- Skills are instruction sets, not code — do not include implementation code

## Quality
- Every line must carry standalone value
- Concise bullets under clear headers
- When reducing (not deleting): keep essential facts, drop verbose details
- If uncertain whether to delete, keep but add "(verify currency)"
