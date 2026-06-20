import pathway as pw
from .helpers import MappingValues, get_this_col

output_connector_mappings: dict[str, MappingValues] = {
    "kafka_write": {
        "node_fn": lambda inputs, node: pw.io.kafka.write(
            inputs[0],
            topic_name=node.topic_name,
            rdkafka_settings=node.rdkafka_settings,
            format=getattr(node, "format", "json"),
        ),
    },
    "redpanda_write": {
        "node_fn": lambda inputs, node: pw.io.redpanda.write(
            inputs[0],
            topic_name=node.topic_name,
            rdkafka_settings=node.rdkafka_settings,
            format=getattr(node, "format", "json"),
        ),
    },
    "csv_write": {
        "node_fn": lambda inputs, node: pw.io.csv.write(inputs[0], node.filename),
    },
    "jsonlines_write": {
        "node_fn": lambda inputs, node: pw.io.jsonlines.write(inputs[0], node.filename),
    },
    "postgres_write": {
        "node_fn": lambda inputs, node: pw.io.postgres.write(
            inputs[0],
            table_name=node.table_name,
            postgres_settings=node.postgres_settings,
            primary_key=[get_this_col(col_name) for col_name in node.primary_keys] if node.primary_keys else None,
            output_table_type=node.output_table_type,
            init_mode="replace"
        ),
    },
    "mysql_write": {
        "node_fn": lambda inputs, node: pw.io.mysql.write(
            inputs[0],
            table_name=node.table_name,
            mysql_settings=node.mysql_settings,
            primary_keys=node.primary_keys,
        ),
    },
    "mongodb_write": {
        "node_fn": lambda inputs, node: pw.io.mongodb.write(
            inputs[0],
            uri=node.uri,
            database=node.database,
            collection=node.collection,
        ),
    },
    "bigquery_write": {
        "node_fn": lambda inputs, node: pw.io.bigquery.write(
            inputs[0],
            credentials_file=node.credentials_file,
            project_id=node.project_id,
            dataset=node.dataset,
            table=node.table,
        ),
    },
    "elasticsearch_write": {
        "node_fn": lambda inputs, node: pw.io.elasticsearch.write(
            inputs[0],
            hosts=node.hosts,
            index=node.index,
            username=getattr(node, "username", None),
            password=getattr(node, "password", None),
        ),
    },
    "dynamodb_write": {
        "node_fn": lambda inputs, node: pw.io.dynamodb.write(
            inputs[0],
            table_name=node.table_name,
            aws_credentials=node.aws_credentials,
        ),
    },
    "pubsub_write": {
        "node_fn": lambda inputs, node: pw.io.pubsub.write(
            inputs[0],
            topic=node.topic,
            credentials_file=node.credentials_file,
        ),
    },
    "kinesis_write": {
        "node_fn": lambda inputs, node: pw.io.kinesis.write(
            inputs[0],
            stream_name=node.stream_name,
            aws_credentials=node.aws_credentials,
        ),
    },
    "nats_write": {
        "node_fn": lambda inputs, node: pw.io.nats.write(
            inputs[0],
            uri=node.uri,
            topic=node.topic,
            format=node.format,
        ),
    },
    "mqtt_write": {
        "node_fn": lambda inputs, node: pw.io.mqtt.write(
            inputs[0],
            broker=node.broker,
            topic=node.topic,
        ),
    },
    "logstash_write": {
        "node_fn": lambda inputs, node: pw.io.logstash.write(inputs[0], node.endpoint),
    },
    "questdb_write": {
        "node_fn": lambda inputs, node: pw.io.questdb.write(
            inputs[0],
            host=node.host,
            port=node.port,
        ),
    },
}
