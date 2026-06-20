# Contract Parser Agent

LLM-powered pipeline builder that converts SLA metrics into Pathway flowcharts via interactive chat.

## Quick Start

# Set API key
set  ANTHROPIC_API_KEY="your-key" in env

```bash
# Run server
cd server && python server.py

# In another terminal, run test client
python test_the_client.py
```

## Testing (No LLM)

```bash
cd server
python mock_server.py      # Terminal 1
python test_mock_client.py # Terminal 2
```

## Metric Input Options

```bash
# From JSON file
python agent_builder.py --metrics_file metrics.json

# Extract from PDF
python agent_builder.py --pdf_path contract.pdf

# Interactive CLI
python agent_builder.py --interactive
```

## Components

| File | Purpose |
|------|---------|
| `agent_builder.py` | Two-phase pipeline builder (CLI mode) |
| `agent_prompts.py` | LLM prompts |
| `graph_builder.py` | Node generation and macro planning |
| `ingestion.py` | PDF extraction and metric loading |
| `node_catalog.json` | Node type definitions |
| `server/server.py` | WebSocket server |
| `server/mock_server.py` | Mock server for testing |

## How It Works

1. **Phase 1**: Negotiate input filters for OpenTelemetry spans
2. **Phase 2**: Build calculation nodes step-by-step with user approval

Output: `flowchart.json` compatible with the main pipeline system.