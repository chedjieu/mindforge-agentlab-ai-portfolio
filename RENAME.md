# Portfolio rename

| | |
|--|--|
| **New display name** | MindForge AgentLab AI Portfolio |
| **New folder** | `mindforge-agentlab-ai-portfolio` |
| **Old folder** | `set-of-designed-projects` |
| **Sibling** | `dataforge-flowlab-pipeline-portfolio` |

Docs (`README.md`, `PROJECTS.md`, `docs/PORTFOLIO.md`) already use the new name.

The directory could not be renamed while Cursor has it open. After closing the workspace:

```powershell
cd "C:\Users\deched\projects(ml-ai)"
Rename-Item -LiteralPath ".\set-of-designed-projects" -NewName "mindforge-agentlab-ai-portfolio"
```

Or: `.\set-of-designed-projects\scripts\rename-portfolio-folder.ps1`

Then **File → Open Folder** → `mindforge-agentlab-ai-portfolio`.
