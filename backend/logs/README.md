# Logs Directory

This directory contains log files for code analysis:

- `prompts.log` - All prompts sent to LLM for code analysis
- `failed_analyses.log` - Failed analyses with error details

Logs are automatically created when analysis runs. To disable logging, set in `.env`:
- `LOG_PROMPTS_TO_FILE=false`
- `LOG_FAILED_ANALYSES_TO_FILE=false`
