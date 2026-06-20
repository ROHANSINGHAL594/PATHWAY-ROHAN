from typing import Dict, Literal, Optional
from typing_extensions import TypedDict

class RdKafkaSettings(TypedDict, total=False):
    """TypedDict for rdkafka configuration settings.
    
    Common settings:
    - bootstrap.servers: Kafka broker addresses
    - security.protocol: Security protocol (PLAINTEXT, SSL, SASL_SSL, etc.)
    - sasl.mechanism: SASL mechanism (PLAIN, SCRAM-SHA-256, etc.)
    - sasl.username: SASL username
    - sasl.password: SASL password
    - group.id: Consumer group ID
    - auto.offset.reset: Offset reset policy (earliest, latest)
    """
    bootstrap_servers: str
    security_protocol: Optional[str]
    sasl_mechanism: Optional[str]
    sasl_username: Optional[str]
    sasl_password: Optional[str]
    group_id: Optional[str]
    auto_offset_reset: Optional[str] = "earliest"
    # Add any other rdkafka settings as needed

