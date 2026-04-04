# NikkoParse Documentation Guide

This document provides an overview of all documentation files in the NikkoParse project.

## Documentation Files

### For Users

**[README.md](README.md)** - Start here!
- Quick start guide and installation
- Feature overview
- Usage instructions
- Auto-generate schema explanation (user-facing)
- AI-assisted workflow (optional)
- Troubleshooting

### For Developers

**[AGENTS.md](AGENTS.md)** - Developer guide for AI coding agents
- Project structure and architecture
- Build, test, and run commands
- Code style guidelines (Python & JavaScript)
- Common patterns and best practices
- Auto-generate schema overview (developer-facing)
- Testing guidelines

**[AUTO_GENERATE.md](AUTO_GENERATE.md)** - Deep technical documentation
- Complete algorithm explanation
- Pattern generation strategies
- Bug fixes and improvements
- Code reference with line numbers
- Examples and test cases
- Performance characteristics

### For Distribution

**[PACKAGING.md](PACKAGING.md)** - Distribution and packaging guide
- How to package as macOS app
- Distribution strategies
- Build scripts

## Quick Reference

### Understanding the Auto-Generate Feature

1. **User explanation**: See [README.md - Auto-Generate Schema](#auto-generate-schema-feature)
2. **Developer overview**: See [AGENTS.md - Auto-Generate Schema Feature](#auto-generate-schema-feature)
3. **Complete technical details**: See [AUTO_GENERATE.md](AUTO_GENERATE.md)

### Code Navigation

| Component | File | Lines |
|-----------|------|-------|
| Main orchestration | `static/js/project.js` | 1150-1299 |
| Pattern generation | `static/js/project.js` | 908-1086 |
| Value patterns | `static/js/project.js` | 1095-1144 |
| Smart selection | `static/js/project.js` | 1212-1232 |

### Getting Started

**First time?**
1. Read [README.md](README.md) - Quick start
2. Run `./setup.sh` to install dependencies
3. Run `./start.sh` to launch the app

**Want to contribute?**
1. Read [AGENTS.md](AGENTS.md) - Code style and patterns
2. Run tests with `pytest -v`
3. Check [AUTO_GENERATE.md](AUTO_GENERATE.md) if modifying pattern generation

**Want to package for distribution?**
1. Read [PACKAGING.md](PACKAGING.md)

## Archived Documentation

Older documentation files have been moved to `archive_docs/` for reference:
- `AI_WORKFLOW_*.md` - Implementation notes for AI workflow
- `DEVELOPMENT.md` - Duplicate of AGENTS.md
- `OPUS_PLAN.md` - Planning document
- `spec.md` - Original specification
- `field_entries.md` - Field dictionary entries
- `implementation_plan.md` - Implementation planning
- `QUICK_START_AI_WORKFLOW.md` - Quick start for AI workflow

These files contain historical context but are superseded by the current documentation.

## Documentation Standards

When updating documentation:

1. **README.md** - User-facing, no jargon, examples over explanation
2. **AGENTS.md** - Developer-facing, code patterns, file locations
3. **AUTO_GENERATE.md** - Technical depth, algorithm details, bug fixes
4. Keep code references up-to-date with line numbers
5. Update this file when adding new documentation

---

**Last Updated:** April 2026
