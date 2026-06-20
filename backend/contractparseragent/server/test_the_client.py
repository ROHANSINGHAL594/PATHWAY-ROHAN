
"""
Simple WebSocket test client for the new agentic server.
"""
import asyncio
import json
import os
import sys
from pathlib import Path
import websockets
from anthropic import Anthropic
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(env_path)

# Add backend to path for imports
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def format_metric_with_llm(metric_input: str) -> dict:
    """Use Claude to format a natural language metric description into proper JSON."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY environment variable required")
    
    client = Anthropic(api_key=api_key)
    
    prompt = f"""Convert this SLA metric description into a properly formatted JSON object.

Input: {metric_input}

Output format (strict JSON only):
{{
  "metric_name": "Brief name for the metric",
  "description": "Detailed description of what is measured and requirements",
  "category": "latency|uptime|error_rate"
}}

Rules:
- Choose the most appropriate category: latency (time measurements), uptime (availability %), error_rate (failure rates)
- Make the metric_name concise but descriptive
- Include all measurement details in the description
- Return only valid JSON, no extra text
"""

    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )
    
    text = response.content[0].text.strip()
    if text.startswith("```"):
        text = text.strip("`").strip()
        if text.startswith("json"):
            text = text[4:].strip()
    
    return json.loads(text)


def collect_metrics_interactively() -> list:
    """Interactively collect multiple SLA metrics from user input."""
    print("\n=== Interactive Metric Collection ===")
    
    metrics = []
    while True:
        print(f"\nCurrent metrics collected: {len(metrics)}")
        add_more = input("Add another metric? (y/n): ").strip().lower()
        if add_more not in ('y', 'yes'):
            break
        
        print("\nEnter metric description (natural language):")
        print("Example: 'API response time should be under 500ms for 95% of requests'")
        metric_input = input("> ").strip()
        
        if not metric_input:
            continue
        
        try:
            formatted_metric = format_metric_with_llm(metric_input)
            print(f"\nLLM formatted as:")
            print(f"  Name: {formatted_metric['metric_name']}")
            print(f"  Description: {formatted_metric['description']}")
            print(f"  Category: {formatted_metric['category']}")
            
            confirm = input("Accept this formatting? (y/n): ").strip().lower()
            if confirm in ('y', 'yes'):
                metrics.append(formatted_metric)
                print("✓ Metric added")
            else:
                print("✗ Metric skipped")
                
        except Exception as e:
            print(f"Error formatting metric: {e}")
            print("Please try rephrasing your metric description.")
    
    return metrics


async def test_client():
    # Use a different port for the contract parser agent server
    # Default to 8001 if not specified, to avoid conflict with main API server on 8000
    port = int(os.getenv("CONTRACT_PARSER_PORT", "8001"))
    uri = f"ws://localhost:{port}/ws"

    # Local tracking of macro plan steps so we can eagerly
    # print the next step description immediately after the user
    # approves a node, without waiting for the next server message.
    macro_steps = []
    last_step_header_index = None

    async with websockets.connect(uri, ping_interval=None) as websocket:
        # Ask user for metric loading mode
        print("\n=== Metric Loading Options ===")
        print("1) Load from PDF file")
        print("2) Enter descriptions interactively")
        
        while True:
            choice = input("\nChoose option (1 or 2): ").strip()
            if choice == "1":
                pdf_path = input("Enter PDF file path: ").strip()
                if not pdf_path:
                    continue
                init_payload = {"pdf_path": pdf_path}
                break
            elif choice == "2":
                metrics_list = collect_metrics_interactively()
                if not metrics_list:
                    print("No metrics collected. Exiting.")
                    return
                init_payload = {"metrics": metrics_list}
                break
            else:
                print("Invalid choice. Please enter 1 or 2.")

        await websocket.send(json.dumps(init_payload))
        
        print("\nSession started\n")
        
        while True:
            try:
                message = await websocket.recv()
                data = json.loads(message)
                msg_type = data.get("type")
                
                if msg_type == "session_start":
                    print(data.get("message", "Session started"))
                    for metric in data.get("metrics", []):
                        print(f"- {metric.get('metric_name')}: {metric.get('description')}")
                    print()
                elif msg_type == "metrics_summary":
                    print(data.get("message", "Loaded metrics"))
                    for metric in data.get("metrics", []):
                        print(f"  * {metric.get('metric_name')}")
                    print()
                elif msg_type == "metrics_loaded":
                    print(data.get("message"))
                
                elif msg_type == "phase":
                    print(f"\n{'='*70}")
                    print(f"{data['message']}")
                    print(f"{'='*70}\n")
                
                elif msg_type == "agent_response":
                    print(f"Agent: {data['message']}\n")
                
                elif msg_type == "await_input":
                    user_input = input("You: ").strip()
                    await websocket.send(json.dumps({
                        "message": user_input
                    }))
                
                elif msg_type == "phase1_complete":
                    print("Phase 1 Complete!")
                    print(f"Generated {len(data['flowchart']['nodes'])} nodes\n")
                
                elif msg_type == "macro_plan":
                    metric_idx = data.get("metric_index")
                    macro_steps = data.get("steps", [])
                    print(
                        f"\nMetric {metric_idx + 1}: Macro Plan ({data['total_steps']} steps)"
                    )
                    for i, step in enumerate(macro_steps, 1):
                        print(f"  {i}. {step}")
                    print()
                    last_step_header_index = None
                
                elif msg_type == "metric_start":
                    print(
                        f"\n=== Metric {data['metric_index'] + 1}: {data['metric_name']} ==="
                    )
                    if data.get("filter_context"):
                        print("Filters:")
                        print(data["filter_context"])
                    print()

                elif msg_type == "step_start":
                    # Trust the server as source of truth for which
                    # step index and total are current. Only print the
                    # header if we haven't already printed it from the
                    # optimistic client-side logic.
                    idx = data.get("step_index", 0)
                    total = data.get("total_steps", len(macro_steps) or 0)
                    if last_step_header_index != idx:
                        print(f"\nStep {idx + 1}/{total}")
                        print(f"   {data['step']}\n")
                        last_step_header_index = idx
                
                elif msg_type == "node_proposed":
                    print("Proposed Node:")
                    print(json.dumps(data['node'], indent=2))
                    print("\nProposed Edges:")
                    print(json.dumps(data['edges'], indent=2))
                
                elif msg_type == "await_approval":
                    choice = input("\nAccept this node? [y/n/q]: ").strip().lower()
                    if choice in ('y', 'yes'):
                        # Optimistic update: print approval and next step immediately
                        idx_to_approve = last_step_header_index if last_step_header_index is not None else 0
                        print(f"Step {idx_to_approve + 1} approved\n")
                        
                        next_index = idx_to_approve + 1
                        total = len(macro_steps)
                        if next_index < total:
                             print(f"\nStep {next_index + 1}/{total}")
                             print(f"   {macro_steps[next_index]}\n")
                        
                        # Update tracking so we don't duplicate prints when server confirms
                        last_step_header_index = next_index

                        await websocket.send(json.dumps({"action": "approve"}))
                    elif choice in ('n', 'no'):
                        feedback = input("Feedback: ").strip()
                        await websocket.send(json.dumps({
                            "action": "reject",
                            "feedback": feedback
                        }))
                    elif choice in ('q', 'quit'):
                        await websocket.send(json.dumps({"action": "quit"}))
                    else:
                        print("Invalid choice, please try again")
                        continue
                
                elif msg_type == "node_approved":
                    approved_idx = data.get("step_index", 0)
                    
                    # Only print if we haven't advanced past this step (i.e. we didn't do optimistic update)
                    if last_step_header_index == approved_idx:
                        print(f"{data['message']}\n")

                    # Proactively show the next step description in the
                    # terminal right after approval, so it feels like
                    # the LLM is now working on that step.
                    next_index = approved_idx + 1
                    total = len(macro_steps)
                    if 0 <= next_index < total:
                        # Only print if we haven't already printed this
                        # header yet; also record it so that a later
                        # step_start from the server for the same index
                        # doesn't duplicate the output.
                        if last_step_header_index != next_index:
                            print(f"\nStep {next_index + 1}/{total}")
                            print(f"   {macro_steps[next_index]}\n")
                            last_step_header_index = next_index
                
                elif msg_type == "phase2_complete":
                    print(f"\n{data['message']}\n")
                
                elif msg_type == "final":
                    print(f"Final flowchart saved to: {data['path']}")
                    print(f"   Total nodes: {len(data['flowchart']['nodes'])}")
                
                elif msg_type == "done":
                    reason = data.get("reason", "unknown")
                    print(f"\nSession ended: {reason}")
                    break
                
                elif msg_type == "error":
                    print(f"Error: {data['message']}")
                
                elif msg_type == "status":
                    print(f"Info: {data['message']}")
                
                else:
                    print(f"Unknown message type: {msg_type}")
                    print(json.dumps(data, indent=2))
                    
            except Exception as e:
                print(f"Error: {e}")
                break
        
        print("\nConnection closed.")


if __name__ == "__main__":
    asyncio.run(test_client())
