from pydantic import Field, TypeAdapter, field_validator, BaseModel
from pydantic.json_schema import SkipJsonSchema
from typing import Optional, Dict, Any, List, Literal, Annotated, Tuple
import pathway as pw
from .node import Node
import json

# NOTE: Instead of using tuple, using this special type to ensure correct rending mechanism on frontend
PairOfStrings = Annotated[List[str], Field(min_length=2, max_length=2)]
class ColumnType(BaseModel):
    key: str = Field(..., title="Column Name")
    value: str = Field(..., title="Type")
class IONode(Node):
    category: Literal['io']
    name: Optional[str] = Field(default="")

class InputNode(IONode):
    n_inputs : Literal[0] = 0
    # input_schema will be sent to frontend and will be converted in to the table_schema at backend for parsing
    input_schema: List[ColumnType] = Field(
        description="List of columns names and types (eg. `str`, `float`, `int` for more details refer [here](https://pathway.com/developers/user-guide/connect/schema/))",
    )
    table_schema: SkipJsonSchema[Any]
    datetime_columns: Optional[List[PairOfStrings]] = Field(
        default=None,
        description =( "List of tuples **[column_name, format_string]** to convert string columns to datetime. "
                    "Format strings follow strptime conventions `(e.g., '%Y-%m-%d %H:%M:%S')`. "
                    "Use 'unix_seconds', 'unix_milliseconds', or 'unix_microseconds' for Unix timestamps.")
    )

    @field_validator("table_schema", mode="before")
    @classmethod
    def validate_schema(cls, value):
        # If it's already a Pathway schema class, accept as-is
        if isinstance(value, type) and issubclass(value, pw.Schema):
            return value

        # If it's a JSON string, parse and convert
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if not isinstance(parsed, dict):
                    raise TypeError("Schema JSON must represent a dictionary.")
                return pw.schema_from_dict(parsed)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON for schema: {e}")
            except Exception as e:
                raise ValueError(f"Failed to construct Pathway schema: {e}")

        # If it's already a dict, support that too
        if isinstance(value, dict):
            try:
                return pw.schema_from_dict(value)
            except Exception as e:
                raise ValueError(f"Invalid Pathway schema dict: {e}")

        raise TypeError(
            f"table_schema must be either a Pathway Schema class, "
            f"a JSON string, or a dict — got {type(value).__name__}"
        )

class OutputNode(IONode):
    n_inputs: Literal[1] = 1

# ============ INPUT CONNECTORS ============

class KafkaNode(InputNode):
    topic: str
    node_id: Literal["kafka"]
    rdkafka_settings: Dict[str, Any]
    format: Literal["raw", "csv", "json", "plaintext"] = "json"
    json_field_paths: Optional[Dict[str, str]] = None


class RedpandaNode(InputNode):
    topic: str
    node_id: Literal["redpanda"]
    rdkafka_settings: Dict[str, Any]
    format: Literal["json"]
    with_metadata: bool = False



class CsvNode(InputNode):
    path: str
    node_id: Literal["csv"]



class JsonLinesNode(InputNode):
    path: str
    node_id: Literal["jsonlines"]


class AirbyteNode(InputNode):
    config_file_path: str
    streams: List[str] = Field(
        description="**Define the streams** from where you want to take input from"
    )
    node_id: Literal["airbyte"]
    env_vars: Optional[Dict[str, str]] = None
    enforce_method: Optional[str] = Field(
        default=None,
        description =( "when set to \"docker\", Pathway will not try to locate and run the latest connector version from PyPI. On the other hand, when set to \"pypi\", Pathway will prefer the usage of the latest image available on PyPI")
    )
    refresh_interval_ms: int = Field(
        default=60000,
        description="time in milliseconds between new data queries. Applicable if mode is set to \"streaming\""
        )


class DebeziumNode(InputNode):
    rdkafka_settings: Dict[str, Any]
    topic_name: str
    node_id: Literal["debezium"]
    db_type: Optional[str] = None



class S3Node(InputNode):
    path: str
    aws_s3_settings: Dict[str, Any] = Field(
        description="Connection parameters for the S3 account and the bucket."
    )
    format: str
    node_id: Literal["s3"]
    csv_settings: Optional[Dict[str, Any]] = None
    with_metadata: bool = Field(
        default=False,
        description="When set to true, the connector will add an additional column named '_metadata' to the table. This column will be a JSON field"
    )


class MinIONode(InputNode):
    path: str
    minio_settings: Dict[str, Any] = Field(
        description="Connection parameters for the MinIO account and the bucket."
    )
    format: str
    node_id: Literal["minio"]
    with_metadata: bool = Field(
        default=False,
        description="When set to true, the connector will add an additional column named _metadata to the table. This column will be a JSON field"
    )


class DeltaLakeNode(InputNode):
    uri: str
    node_id: Literal["deltalake"]
    version: Optional[int] = None
    datetime_column: Optional[str] = None


class IcebergNode(InputNode):
    catalog: str = Field(
        description="Settings for Iceberg catalog connection."
    )
    table_name: str
    node_id: Literal["iceberg"]

class PlainTextNode(InputNode):
    path: str
    node_id: Literal["plaintext"]
    object_pattern: str = Field(
        default="*",
        description="Unix shell style pattern for filtering only certain files in the directory. Ignored in case a path to a single file is specified")
    with_metadata: bool = Field(
        default=True,
        description="When set to true, the connector will add an additional column named _metadata to the table. This column will be a JSON field"
    )

class HTTPNode(InputNode):
    url: str
    node_id: Literal["http"]
    method: Literal["GET", "POST", "PUT", "DELETE"] = "GET"
    headers: Optional[Dict[str, str]] = None
    allow_redirects: bool = True
    format : Literal["raw","json"] = "json"

class MongoDBNode(InputNode):
    uri: str
    database: str
    collection: str
    node_id: Literal["mongodb"]

class PostgreSQLNode(InputNode):
    rdkafka_settings: Dict[str, Any]
    topic_name: str
    node_id: Literal["postgres"]


class SQLiteNode(InputNode):
    path: str
    table_name: str
    node_id: Literal["sqlite"]


class GoogleDriveNode(InputNode):
    object_id: str
    service_user_credentials_file: str
    node_id: Literal["gdrive"]
    with_metadata: bool = Field(
        default=False,
        description="when set to True, the connector will add an additional column named _metadata to the table. This column will contain file metadata, such as: id, name, mimeType, parents, modifiedTime, thumbnailLink, lastModifyingUser."
    )


class KinesisNode(InputNode):
    stream_name: str
    format: Literal["plaintext", "raw", "json"]
    aws_credentials: Dict[str, Any]
    node_id: Literal["kinesis"]



class NATSNode(InputNode):
    servers: List[str]
    format: Literal["plaintext", "raw", "json"]
    subject: str
    node_id: Literal["nats"]



class MQTTNode(InputNode):
    broker: str
    topic: str
    node_id: Literal["mqtt"]
    port: int = Field(default=1883)



class PythonConnectorNode(InputNode):
    subject: Any
    node_id: Literal["python"]


# ============ OUTPUT CONNECTORS ============

class KafkaWriteNode(OutputNode):
    rdkafka_settings: Dict[str, Any]
    topic_name: str
    format: Literal["json"] = "json"
    node_id: Literal["kafka_write"]


class RedpandaWriteNode(OutputNode):
    rdkafka_settings: Dict[str, Any]
    topic_name: str
    format: Literal["json"] = "json"
    node_id: Literal["redpanda_write"]


class CsvWriteNode(OutputNode):
    filename: str
    node_id: Literal["csv_write"]


class JsonLinesWriteNode(OutputNode):
    filename: str
    node_id: Literal["jsonlines_write"]


class PostgreSQLWriteNode(OutputNode):
    postgres_settings: Dict[str, Any]
    table_name: str
    primary_keys: List[str] = Field(
        description="When using snapshot mode, one or more columns that form the primary key in the target Postgres table."
    )
    node_id: Literal["postgres_write"]
    output_table_type : Literal['stream_of_changes', 'snapshot'] = 'stream_of_changes'


class MySQLWriteNode(OutputNode):
    mysql_settings: Dict[str, Any]
    table_name: str
    primary_keys: List[str] = Field(description="When using snapshot mode, one or more columns that form the primary key in the target MySQL table.")
    node_id: Literal["mysql_write"]


class MongoDBWriteNode(OutputNode):
    uri: str
    database: str
    collection: str
    node_id: Literal["mongodb_write"]


class BigQueryWriteNode(OutputNode):
    credentials_file: str
    project_id: str
    dataset: str
    table: str
    node_id: Literal["bigquery_write"]



class ElasticsearchWriteNode(OutputNode):
    hosts: List[str] = Field(
        description="the host and port, on which Elasticsearch server works."
    )
    index: str
    node_id: Literal["elasticsearch_write"]
    username: Optional[str] = None
    password: Optional[str] = None


class DynamoDBWriteNode(OutputNode):
    table_name: str
    aws_credentials: Dict[str, Any]
    node_id: Literal["dynamodb_write"]


class PubSubWriteNode(OutputNode):
    topic: str
    credentials_file: str
    node_id: Literal["pubsub_write"]


class KinesisWriteNode(OutputNode):
    stream_name: str
    aws_credentials: Dict[str, Any]
    node_id: Literal["kinesis_write"]


class NATSWriteNode(OutputNode):
    uri: str = Field(
        description="The URI of the NATS server."
    )
    topic: str
    format: Literal["json", "dsv", "plaintext", "raw"] = Field(
        description="The input data format, which can be \"raw\", \"plaintext\", or \"json\"."
    )
    node_id: Literal["nats_write"]


class MQTTWriteNode(OutputNode):
    broker: str
    topic: str
    node_id: Literal["mqtt_write"]


class LogstashWriteNode(OutputNode):
    endpoint: str = Field(
        description="Logstash endpoint, accepting entries"
    )
    node_id: Literal["logstash_write"]


class QuestDBWriteNode(OutputNode):
    host: str
    port: int
    node_id: Literal["questdb_write"]
