import pathway as pw
from .helpers import MappingValues

input_connector_mappings: dict[str, MappingValues] = {
    "kafka": {
        "node_fn": lambda _tables, node: pw.io.kafka.read(
            topic=node.topic,
            rdkafka_settings=node.rdkafka_settings,
            format=node.format,
            json_field_paths=node.json_field_paths,
            schema=node.table_schema,
        )
    },
    "redpanda": {
        "node_fn": lambda _tables, node: pw.io.redpanda.read(
            topic=node.topic,
            rdkafka_settings=node.rdkafka_settings,
            format=node.format,
            schema=node.table_schema,
            with_metadata=node.with_metadata,
        )
    },
    "csv": {
        "node_fn": lambda _tables, node: pw.io.csv.read(
            path=node.path,
            schema=node.table_schema,
        )
    },
    "jsonlines": {
        "node_fn": lambda _tables, node: pw.io.jsonlines.read(
            path=node.path,
            schema=node.table_schema,
        )
    },
    "airbyte": {
        "node_fn": lambda _tables, node: pw.io.airbyte.read(
            config_file_path=node.config_file_path,
            streams=node.streams,
            env_vars=node.env_vars,
            enforce_method=node.enforce_method,
            refresh_interval_ms=node.refresh_interval_ms,
            schema=node.table_schema,
        )
    },
    "debezium": {
        "node_fn": lambda _tables, node: pw.io.debezium.read(
            topic_name=node.topic_name,
            rdkafka_settings=node.rdkafka_settings,
            db_type=node.db_type,
            schema=node.table_schema,
        )
    },
    "s3": {
        "node_fn": lambda _tables, node: pw.io.s3.read(
            path=node.path,
            format=node.format,
            aws_s3_settings=node.aws_s3_settings,
            csv_settings=node.csv_settings,
            schema=node.table_schema,
            with_metadata=node.with_metadata,
        )
    },
    "minio": {
        "node_fn": lambda _tables, node: pw.io.minio.read(
            path=node.path,
            format=node.format,
            minio_settings=node.minio_settings,
            schema=node.table_schema,
            with_metadata=node.with_metadata,
        )
    },
    "deltalake": {
        "node_fn": lambda _tables, node: pw.io.deltalake.read(
            uri=node.uri,
            version=node.version,
            datetime_column=node.datetime_column,
            schema=node.table_schema,
        )
    },
    "iceberg": {
        "node_fn": lambda _tables, node: pw.io.iceberg.read(
            catalog=node.catalog,
            table_name=node.table_name,
            schema=node.table_schema,
        )
    },
    "plaintext": {
        "node_fn": lambda _tables, node: pw.io.text.read(
            path=node.path,
            object_pattern=node.object_pattern,
            schema=node.table_schema,
            with_metadata=node.with_metadata,
        )
    },
    "http": {
        "node_fn": lambda _tables, node: pw.io.http.read(
            url=node.url,
            method=node.method,
            headers=node.headers,
            allow_redirects=node.allow_redirects,
            schema=node.table_schema,
        )
    },
    "mongodb": {
        "node_fn": lambda _tables, node: pw.io.mongodb.read(
            uri=node.uri,
            database=node.database,
            collection=node.collection,
            schema=node.table_schema,
        )
    },
    "postgres": {
        "node_fn": lambda _tables, node: pw.io.postgres.read(
            topic_name=node.topic_name,
            rdkafka_settings=node.rdkafka_settings,
            schema=node.table_schema,
        )
    },
    "sqlite": {
        "node_fn": lambda _tables, node: pw.io.sqlite.read(
            path=node.path,
            table_name=node.table_name,
            schema=node.table_schema,
        )
    },
    "gdrive": {
        "node_fn": lambda _tables, node: pw.io.gdrive.read(
            object_id=node.object_id,
            service_user_credentials_file=node.service_user_credentials_file,
            schema=node.table_schema,
            with_metadata=node.with_metadata,
        )
    },
    "kinesis": {
        "node_fn": lambda _tables, node: pw.io.kinesis.read(
            stream_name=node.stream_name,
            format=node.format,
            aws_credentials=node.aws_credentials,
            schema=node.table_schema,
        )
    },
    "nats": {
        "node_fn": lambda _tables, node: pw.io.nats.read(
            servers=node.servers,
            subject=node.subject,
            format=node.format,
            schema=node.table_schema,
        )
    },
    "mqtt": {
        "node_fn": lambda _tables, node: pw.io.mqtt.read(
            broker=node.broker,
            topic=node.topic,
            port=node.port,
            schema=node.table_schema,
        )
    },
    "python": {
        "node_fn": lambda _tables, node: pw.io.python.read(
            node.subject, schema=node.table_schema
        )
    },
}
