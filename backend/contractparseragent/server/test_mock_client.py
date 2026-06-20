"""
Interactive test client for the mock server.
Mirrors the exact flow of test_the_client.py but works with mock_server.py

Run mock_server.py first, then run this client.
"""

import asyncio
import json
import os
import sys
import websockets


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

    try:
        async with websockets.connect(uri, ping_interval=None) as websocket:
            # For mock server, we use pre-defined metrics (no PDF or interactive collection)
            print("\n=== Mock Server Test Client ===")
            print("This client mirrors test_the_client.py behavior with mock_server.py")
            print("=" * 50)
            
            # Send init payload with sample metrics
            init_payload = {
                "metrics": [
                    {
                        "metric_name": "Server Error Rate",
                        "description": "Percentage of server requests that result in errors (status_code >= 500)",
                        "category": "error_rate"
                    }
                ],
                "metrics_output_dir": "./generated_flowcharts"
            }
            
            print(f"\nSending metrics:")
            for m in init_payload["metrics"]:
                print(f"  - {m['metric_name']}: {m['description']}")

            await websocket.send(json.dumps(init_payload))
            
            print("\nSession started\n")
            
            # Track if we've shown the reject example
            reject_example_shown = False
            reject_at_step = 1  # Reject at step 2 (index 1) as example
            
            while True:
                try:
                    message = await websocket.recv()
                    data = json.loads(message)
                    msg_type = data.get("type")
                    
                    if msg_type == "session_id":
                        print(f"Session ID: {data.get('session_id')}\n")
                    
                    elif msg_type == "session_start":
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
                        current_step = data.get("step_index", 0)
                        
                        # Show example of rejecting at step 2
                        if current_step == reject_at_step and not reject_example_shown:
                            print("\n" + "=" * 50)
                            print(">>> SELECT 'n' HERE TO SEE REJECT FLOW <<<")
                            print("=" * 50)
                        
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
                            reject_example_shown = True
                            feedback = input("Feedback (optional): ").strip()
                            print(f"\n[Rejecting step {current_step + 1} - server will regenerate]\n")
                            await websocket.send(json.dumps({
                                "action": "reject",
                                "feedback": feedback
                            }))
                        
                        elif choice in ('q', 'quit'):
                            await websocket.send(json.dumps({"action": "quit"}))
                        
                        else:
                            print("Invalid choice, defaulting to approve")
                            await websocket.send(json.dumps({"action": "approve"}))
                    
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
                    
                    elif msg_type == "status":
                        print(f"Status: {data['message']}")
                    
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
                    
                    else:
                        print(f"[{msg_type}]: {json.dumps(data, indent=2)[:300]}")
                        
                except Exception as e:
                    print(f"Error: {e}")
                    import traceback
                    traceback.print_exc()
                    break
            
            print("\nConnection closed.")
    
    except ConnectionRefusedError:
        port = int(os.getenv("CONTRACT_PARSER_PORT", "8001"))
        print(f"\n!!! Cannot connect to mock server at ws://localhost:{port}/ws")
        print("Make sure mock_server.py is running first: python mock_server.py")
    except Exception as e:
        print(f"\n!!! Connection error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    try:
        asyncio.run(test_client())
    except KeyboardInterrupt:
        print("\n\n[Interrupted by user]")
        sys.exit(0)
