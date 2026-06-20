/**
 * WebSocket utility for connecting to the contract parser agent server
 * Handles the complete flow from metric input to final flowchart generation
 */

// Use mock server by default for testing (set VITE_USE_MOCK_SERVER=false to use real server)
const USE_MOCK_SERVER = import.meta.env.VITE_USE_MOCK_SERVER !== "false";
// Get the base URL and construct WebSocket URL
const BASE_URL = import.meta.env.VITE_CONTRACT_PARSER || "http://localhost:8001";
// Convert http:// to ws:// and ensure /ws endpoint
const CONTRACT_PARSER_WS_URL = BASE_URL.replace(/^http/, "ws") + (BASE_URL.includes("/ws") ? "" : "/ws");

export class ContractParserWebSocket {
  constructor(callbacks = {}) {
    this.ws = null;
    this.callbacks = {
      onMessage: callbacks.onMessage || (() => {}),
      onError: callbacks.onError || (() => {}),
      onClose: callbacks.onClose || (() => {}),
      onOpen: callbacks.onOpen || (() => {}),
      onNodeProposed: callbacks.onNodeProposed || (() => {}),
      onFlowchartUpdate: callbacks.onFlowchartUpdate || (() => {}),
      onPhaseComplete: callbacks.onPhaseComplete || (() => {}),
      onFinal: callbacks.onFinal || (() => {}),
    };
    this.isConnected = false;
    this.sessionId = null;
  }

  /**
   * Connect to the WebSocket server
   * @param {Array|Object} initialData - Optional metrics array or object with {metrics, pdf_path, description}
   */
  connect(initialData = null) {
    return new Promise((resolve, reject) => {
      try {
        console.log(`[WebSocket] Attempting to connect to: ${CONTRACT_PARSER_WS_URL}`);
        this.ws = new WebSocket(CONTRACT_PARSER_WS_URL);

        this.ws.onopen = () => {
          this.isConnected = true;
          console.log(`[WebSocket] ✓ Connected to contract parser agent at ${CONTRACT_PARSER_WS_URL}`);
          console.log(`[WebSocket] Using ${USE_MOCK_SERVER ? 'MOCK' : 'REAL'} server mode`);
          
          // Send initial data immediately if provided
          if (initialData) {
            try {
              let payload;
              
              // Handle different input formats
              if (Array.isArray(initialData)) {
                // Legacy format: array of metrics
                payload = { metrics: initialData };
              } else if (initialData.pdf_path) {
                // PDF path provided - include description if available
                payload = { pdf_path: initialData.pdf_path };
                if (initialData.description && initialData.description.trim()) {
                  payload.description = initialData.description;
                  console.log("[WebSocket] Including description with PDF for combined metric extraction");
                }
                if (initialData.anthropic_api_key) {
                  payload.anthropic_api_key = initialData.anthropic_api_key;
                }
              } else if (initialData.metrics && initialData.metrics.length > 0) {
                // Metrics object
                payload = { metrics: initialData.metrics };
                console.log(`[WebSocket] Sending metrics payload with ${initialData.metrics.length} metric(s)`);
              } else if (initialData.description) {
                // Description only - convert to metrics
                payload = { 
                  metrics: ContractParserWebSocket.formatDescriptionToMetrics(initialData.description)
                };
                console.log("[WebSocket] Converted description to metrics payload");
              }
              
              if (payload) {
                const payloadStr = JSON.stringify(payload);
                this.ws.send(payloadStr);
                console.log("[WebSocket] ✓ Sent initial data to server:", payload);
                console.log("[WebSocket] Payload string length:", payloadStr.length);
              } else {
                console.warn("[WebSocket] No payload to send - initialData format not recognized:", initialData);
              }
            } catch (error) {
              console.error("[WebSocket] ❌ Error sending initial data:", error);
              reject(error);
            }
          } else {
            console.warn("[WebSocket] No initial data provided - connection established but no data sent");
          }
          
          this.callbacks.onOpen();
          resolve();
        };

        this.ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            this.handleMessage(data);
          } catch (error) {
            console.error("Error parsing WebSocket message:", error);
          }
        };

        this.ws.onerror = (error) => {
          console.error("[WebSocket] ❌ Connection error:", error);
          console.error("[WebSocket] URL attempted:", CONTRACT_PARSER_WS_URL);
          this.callbacks.onError(error);
          reject(error);
        };

        this.ws.onclose = () => {
          this.isConnected = false;
          console.log("WebSocket disconnected");
          this.callbacks.onClose();
        };
      } catch (error) {
        console.error("Error connecting WebSocket:", error);
        reject(error);
      }
    });
  }

  /**
   * Handle incoming WebSocket messages
   */
  handleMessage(data) {
    const msgType = data.type;

    switch (msgType) {
      case "session_id":
        this.sessionId = data.session_id;
        break;

      case "session_start":
      case "metrics_summary":
      case "metrics_loaded":
      case "phase":
      case "agent_response":
      case "await_input":
      case "phase1_complete":
      case "macro_plan":
      case "metric_start":
      case "step_start":
      case "node_approved":
      case "phase2_complete":
      case "status":
      case "error":
        this.callbacks.onMessage(data);
        break;

      case "node_proposed":
        this.callbacks.onNodeProposed(data);
        break;

      case "flowchart_update":
        // Flowchart update - merge with existing nodes
        if (this.callbacks.onFlowchartUpdate) {
          this.callbacks.onFlowchartUpdate(data);
        } else {
          // Fallback to onMessage if callback not provided
          this.callbacks.onMessage(data);
        }
        break;

      case "final":
        // Final flowchart is ready - save it before it's deleted
        this.callbacks.onFinal(data);
        break;

      case "done":
        this.callbacks.onMessage(data);
        break;

      default:
        console.log("Unknown message type:", msgType, data);
        this.callbacks.onMessage(data);
    }
  }

  /**
   * Send initial payload with metrics (option 2: interactive metrics from description)
   */
  sendMetrics(metricsList) {
    if (!this.isConnected || !this.ws) {
      throw new Error("WebSocket not connected");
    }

    const payload = {
      metrics: metricsList,
    };

    this.ws.send(JSON.stringify(payload));
  }

  /**
   * Send user input (for Phase 1 interactive negotiation)
   */
  sendUserInput(message) {
    if (!this.isConnected || !this.ws) {
      throw new Error("WebSocket not connected");
    }

    this.ws.send(JSON.stringify({ message }));
  }

  /**
   * Send node approval (y/n/q)
   */
  sendApproval(action, feedback = null) {
    if (!this.isConnected || !this.ws) {
      throw new Error("WebSocket not connected");
    }

    const payload = { action };
    if (feedback) {
      payload.feedback = feedback;
    }

    this.ws.send(JSON.stringify(payload));
  }

  /**
   * Disconnect from WebSocket
   */
  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
      this.isConnected = false;
    }
  }

  /**
   * Format description into metrics (simplified version)
   * In a real implementation, this could use LLM to format the description
   */
  static formatDescriptionToMetrics(description) {
    // For now, create a simple metric from the description
    // In production, this should use the LLM formatting like in test_the_client.py
    return [
      {
        metric_name: "Workflow Metric",
        description: description || "Workflow description",
        category: "unspecified",
      },
    ];
  }
}

export default ContractParserWebSocket;

