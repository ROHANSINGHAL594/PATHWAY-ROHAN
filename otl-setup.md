Here is the comprehensive summary of all changes, formatted as a **README.md**. You can save this file in your project root for future reference.

This setup allows you to run the OpenTelemetry Demo on a Cloud VM, pipe logs to a custom Kafka container, and view those logs from your local laptop.

-----

# OpenTelemetry Demo with Custom External Kafka

This setup decouples the Kafka broker from the standard OpenTelemetry Demo. It runs a custom Kafka instance that is accessible both **internally** (by OTel microservices) and **externally** (by your local machine/Kafka UI).

## Prerequisites

1.  **Cloud VM** (Debian/Linux) with Docker & Docker Compose installed.
2.  **Firewall/Security Groups:** Allow Inbound traffic on port **9092** (TCP).
3.  **Public IP:** Note your VM's Public IP address.

-----

## Step 1: Network Setup

Create a shared network so the Demo and Kafka can communicate.

```bash
docker network create opentelemetry-demo
```

-----

## Step 2: Custom Kafka Setup

Create a file named `kafka-compose.yml`. This runs Kafka with "Dual Listeners" (Internal for Docker, External for you).

**File:** `kafka-compose.yml`

> **IMPORTANT:** Replace `<YOUR_VM_PUBLIC_IP>` below with your actual IP address.

```yaml
version: '3.8'

networks:
  opentelemetry-demo:
    external: true

services:
  kafka:
    image: confluentinc/cp-kafka:latest
    hostname: kafka
    container_name: main_kafka
    networks:
      - opentelemetry-demo
    ports:
      - "9092:9092"
    environment:
      # --- Networking & Listeners ---
      KAFKA_NODE_ID: 1
      KAFKA_PROCESS_ROLES: controller,broker
      KAFKA_CONTROLLER_LISTENER_NAMES: CONTROLLER
      
      # 1. Listen on all interfaces
      KAFKA_LISTENERS: INTERNAL://0.0.0.0:29092,EXTERNAL://0.0.0.0:9092,CONTROLLER://0.0.0.0:9093
      
      # 2. Advertise: Internal uses container name, External uses Public IP
      KAFKA_ADVERTISED_LISTENERS: INTERNAL://main_kafka:29092,EXTERNAL://<YOUR_VM_PUBLIC_IP>:9092,CONTROLLER://kafka:9093
      
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: CONTROLLER:PLAINTEXT,INTERNAL:PLAINTEXT,EXTERNAL:PLAINTEXT
      KAFKA_INTER_BROKER_LISTENER_NAME: INTERNAL
      KAFKA_CONTROLLER_QUORUM_VOTERS: "1@kafka:9093"
      
      # --- Standard Defaults ---
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
      KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR: 1
      KAFKA_TRANSACTION_STATE_LOG_MIN_ISR: 1
      KAFKA_DEFAULT_REPLICATION_FACTOR: 1
      KAFKA_MIN_INSYNC_REPLICAS: 1
```

-----

## Step 3: OTel Collector Configuration

Create a config file to tell the Collector to send logs to our custom Kafka.

**File:** `otelcol-config-extras.yml`
*(Place this in the `opentelemetry-demo` folder)*

```yaml
exporters:
  kafka:
    brokers:
      - "main_kafka:29092" # Connects to the internal listener
    protocol_version: 2.0.0
    topic: otel_logs_topic
    encoding: otlp_json

service:
  pipelines:
    logs:
      exporters: [kafka]
```

-----

## Step 4: Update `docker-compose.yml`

Edit the main `docker-compose.yml` file in the demo directory. We are making **4 specific changes**.

### Change A: Use Existing Network

Find the `networks:` block (usually at the top or bottom). Change `driver: bridge` to `external: true`.

```yaml
networks:
  default:
    name: opentelemetry-demo
    external: true  # <--- CHANGED FROM driver: bridge
```

### Change B: Update `otel-collector`

Add the volume mount for the extras config and update the command.

```yaml
  otel-collector:
    # ...
    command: [ "--config=/etc/otelcol-config.yml", "--config=/etc/otelcol-config-extras.yml" ] # <--- UPDATED
    volumes:
      # ... other volumes ...
      - ./otelcol-config-extras.yml:/etc/otelcol-config-extras.yml  # <--- ADDED
```

### Change C: Update Service Dependencies

For **`accounting`**, **`checkout`**, and **`fraud-detection`**, perform the following:

1.  **Remove** `kafka` from the `depends_on` list.
2.  **Add** `KAFKA_ADDR=main_kafka:29092` to the `environment` list.

**Example (apply similar logic to all three):**

```yaml
  fraud-detection:
    # ...
    environment:
      - KAFKA_ADDR=main_kafka:29092  # <--- ADDED
    depends_on:
      otel-collector:
        condition: service_started
      # kafka:                       # <--- REMOVED
      #  condition: service_healthy
```

### Change D: Disable Internal Kafka (Optional)

Find the `kafka` service block and comment it out or delete it to save memory.

-----

## Step 5: Start Up

1.  **Start Kafka first:**

    ```bash
    docker compose -f kafka-compose.yml up -d
    ```

2.  **Start the Demo:**

    ```bash
    docker compose up -d
    ```

-----

## Step 6: Connect from Local Machine

You can now connect to Kafka from your laptop using the VM's Public IP.

**Connection Details:**

  * **Bootstrap Server:** `<YOUR_VM_PUBLIC_IP>:9092`
  * **Topic:** `otel_logs_topic`

**Example (Docker Compose for Local Kafka UI):**

```yaml
services:
  kafka-ui:
    image: provectuslabs/kafka-ui:latest
    ports:
      - 8080:8080
    environment:
      KAFKA_CLUSTERS_0_NAME: Cloud-Demo
      KAFKA_CLUSTERS_0_BOOTSTRAPSERVERS: <YOUR_VM_PUBLIC_IP>:9092
```