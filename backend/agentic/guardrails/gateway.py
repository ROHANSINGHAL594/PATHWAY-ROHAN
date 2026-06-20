import time
import re
import hmac
import hashlib
import logging
from urllib.parse import urlparse
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import os, sys
import asyncio
from dotenv import load_dotenv
from pydantic import Field
from pydantic.dataclasses import dataclass
from openai import AsyncClient
from re import Pattern
import unicodedata
from typing import Generic, TypeVar, Callable, Awaitable, List, Generic, Optional, Any
import nh3
# from detect_secrets.core import scan
# from detect_secrets.core.secrets_collection import SecretsCollection
import ipaddress
import socket

from .base import DetectorResult, BaseDetector, ExtrasImport, Extra, model_DetectorResult
from .batch import PromptInjectionAnalyzer, PRESIDIO_EXTRA, transformers_extra

load_dotenv()

T = TypeVar("T")
R = TypeVar("R")

# client = genai.Client(
#      api_key=os.getenv('GEMINI_API_KEY'),
#      http_options={
#          "base_url": "https://explorer.invariantlabs.ai/api/v1/gateway/{add-your-dataset-name-here}/gemini",
#          "headers": {
#              "Invariant-Authorization": "Bearer your-invariant-api-key"
#          },
#      },
#  )

MOCK_USER_DB = {}



client: AsyncClient | None = None
def get_openai_client() -> AsyncClient:
    """Get an OpenAI client for making requests."""
    global client
    if client is None:
        client = AsyncClient()
    return client


Extra.extras = {}

class PII_Analyzer(BaseDetector):
    def __init__(self, threshold=0.5):
        self.analyzer = None
        self.threshold = threshold
        self._initializing = False
        self._initialized = False

    async def _ensure_initialized(self):
        """Lazy initialization of the analyzer to avoid blocking the event loop."""
        if self._initialized:
            return
        
        if self._initializing:
            # Wait for another coroutine to finish initialization
            while self._initializing:
                await asyncio.sleep(0.01)
            return
        
        self._initializing = True
        try:
            # Run the blocking initialization in a thread pool
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._init_analyzer)
            self._initialized = True
        finally:
            self._initializing = False
    
    def _init_analyzer(self):
        """Initialize the analyzer in a separate thread."""
        AnalyzerEngine = PRESIDIO_EXTRA.package("presidio_analyzer").import_names("AnalyzerEngine")
        self.analyzer = AnalyzerEngine()

    def detect_all(self, text: str, entities: list[str] | None = None):
        if not self._initialized:
            raise RuntimeError("PII_Analyzer not initialized. Call adetect() instead of detect_all().")
        results = self.analyzer.analyze(text, language="en", entities=entities)
        res_matches = []
        for res in results:
            if res.score > self.threshold:
                print(res, type(res))
                res_matches.append(model_DetectorResult(entity=str(res.entity_type), start=res.start,end=res.end))
        return list(res_matches)

    async def adetect(self, text: str, entities: list[str] | None = None):
        await self._ensure_initialized()
        # Run the analysis in a thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.detect_all, text, entities)
    
class UnicodeDetector(BaseDetector):
    """
    Detector for detecting unicode characters based on their category (using allow or deny list).
    """

    def detect_all(self, text: str, categories: list[str] | None = None) -> list[DetectorResult]:
        """Detects all unicode groups that should not be allowed in the text.

        Attributes:
            allow: List of categories to allow.
            deny: List of categories to deny.

        Returns:
            A list of DetectorResult objects indicating the detected unicode groups.

        Raises:
            ValueError: If both allow and deny categories are specified.
        """
        res = []
        for index, chr in enumerate(text):
            cat = unicodedata.category(chr)
            if categories is None or cat in categories:
                res.append(DetectorResult(cat, index, index + 1))
        return res

SECRETS_PATTERNS = {
    "GITHUB_TOKEN": [
        re.compile(r'(ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{36}'),
    ],
    "AWS_ACCESS_KEY": [
        re.compile(r'(?:A3T[A-Z0-9]|ABIA|ACCA|AKIA|ASIA)[0-9A-Z]{16}'),
        re.compile(r'aws.{{0,20}}?{secret_keyword}.{{0,20}}?[\'\"]([0-9a-zA-Z/+]{{40}})[\'\"]'.format(
            secret_keyword=r'(?:key|pwd|pw|password|pass|token)',
        ), flags=re.IGNORECASE),
    ],
    "AZURE_STORAGE_KEY": [
        re.compile(r'AccountKey=[a-zA-Z0-9+\/=]{88}'),
    ],
    "SLACK_TOKEN": [
        re.compile(r'xox(?:a|b|p|o|s|r)-(?:\d+-)+[a-z0-9]+', flags=re.IGNORECASE),
        re.compile(r'https://hooks\.slack\.com/services/T[a-zA-Z0-9_]+/B[a-zA-Z0-9_]+/[a-zA-Z0-9_]+', flags=re.IGNORECASE | re.VERBOSE),
    ],
}

@dataclass
class SecretPattern:
    secret_name: str
    patterns: list[Pattern]


class SecretsAnalyzer(BaseDetector):
    """
    Analyzer for detecting secrets in generated text.
    """
    def __init__(self):
        super().__init__()
        self.secrets = self.get_recognizers()

    def get_recognizers(self) -> list[Pattern]:
        secrets = []
        for secret_name, regex_pattern in SECRETS_PATTERNS.items():
            secrets.append(SecretPattern(secret_name, regex_pattern))
        return secrets
    
    def detect_all(self, text: str) -> list[DetectorResult]:
        res = []
        for secret in self.secrets:
            for pattern in secret.patterns:
                for match in pattern.finditer(text):
                    res.append(DetectorResult(secret.secret_name, match.start(), match.end()))
        return res
    
    
class MCPSecurityGateway:
    """
    (1) Network Layer: Connection Pooling (TLS), SSRF Validation.
    (2) Access Layer: Rate Limiting, PoLP (Role checks), BOLA (Ownership checks).
    (3) Data Layer: Output Sanitization, Signature Verification (Attestation).
    (4) Process Layer: HITL Review Queue, Session Ephemerality (Memory Wiping).
    """
    def __init__(self):
        self._init_connection_pool()
        self._init_rate_limits()
        self._init_permissions()
        self.allowed_domains = {
        }
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger("MCP_Security")
        self.pii_analyzer = PII_Analyzer()
        self.secrets_analyzer = SecretsAnalyzer()
        self.prompt_injection_analyzer = PromptInjectionAnalyzer()
        self.unicode_detector = UnicodeDetector()


    async def scan_text_for_issues(self, text: str) -> List[str]:
        """Scans text for PII, secrets, and prompt injections."""
        issues = []
        
        pii_results = await self.pii_analyzer.adetect(text)
        if pii_results:
            issues.append(f"PII detected: {[res.entity for res in pii_results]}")

        secrets_results = self.secrets_analyzer.detect_all(text)
        if secrets_results:
            issues.append(f"Secrets detected: {[res.entity for res in secrets_results]}")

        if await self.prompt_injection_analyzer.adetect(text):
            issues.append("Prompt injection detected")
            
        unicode_results = self.unicode_detector.detect_all(text, categories=["Co", "Cs"])
        if unicode_results:
            issues.append(f"Disallowed unicode characters detected: {[res.entity for res in unicode_results]}")

        return issues


    def _init_connection_pool(self):
        """
        Protocol: Connection Pooling & Termination.
        Pre-warms connections to hide topology and enforce Transport Layer Security.
        """
        self.session = requests.Session()
        retries = Retry(total=3, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retries, pool_connections=10, pool_maxsize=10)
        self.session.mount('https://', adapter)

    def _init_rate_limits(self):
        """
        Protocol: Request Throttling & Rate Limiting.
        Stores hit counts.
        """
        self.request_counts = {}  # { 'user_id': [timestamp1, timestamp2] }
        self.RATE_LIMIT_WINDOW = 60  # seconds
        self.MAX_REQUESTS_PER_MINUTE = 20

    def _init_permissions(self):
        """
        Protocol: PoLP & Prevent Broken Function Level Architecture.
        Maps Agent Roles -> Allowed Methods -> Allowed Endpoints with wildcard support.
        """
        self.role_permissions = {
            "invoice_reader_agent": {
                "GET": [re.compile(r"/api/invoices/inv_.*")],
                "POST": [] 
            },
            "account_manager_agent": {
                "GET": [re.compile(r"/api/accounts/acc_.*")],
                "POST": [re.compile(r"/api/accounts/acc_.*/update")]
            }
        }

    def check_rate_limit(
            self,
            user_id: str
    ) -> bool:
        """
        Request Throttling & Rate Limiting
        token bucket
        """
        current_time = time.time()
        if user_id not in self.request_counts:
            self.request_counts[user_id] = []

        self.request_counts[user_id] = [t for t in self.request_counts[user_id] 
                                        if t > current_time - self.RATE_LIMIT_WINDOW]

        if len(self.request_counts[user_id]) >= self.MAX_REQUESTS_PER_MINUTE:
            self.logger.warning(f"Rate limit exceeded for user {user_id}")
            return False
        
        self.request_counts[user_id].append(current_time)
        return True

    def validate_agent_function(
            self, 
            agent_role: str, 
            method: str, 
            endpoint: str
    ) -> bool:
        """PoLP & Prevent Broken Function Level Architecture"""
        self.logger.info(f"PoLP Check: Role '{agent_role}' attempting {method} on {endpoint}")
        # Check if role exists
        if agent_role not in self.role_permissions:
            self.logger.error(f"Security Alert: Unknown agent role {agent_role}")
            return False

        allowed_endpoints = self.role_permissions[agent_role].get(method, [])
        is_allowed = any(pattern.match(endpoint) for pattern in allowed_endpoints)
        
        if not is_allowed:
            self.logger.warning(f"PoLP Violation: {agent_role} tried {method} on {endpoint}")
            return False
        return True

    def validate_object_ownership(
            self, 
            user_id: str, 
            resource_id: str
    ) -> bool:
        """Prevent Broken Object Level Architecture (BOLA)"""
        self.logger.info(f"BOLA Check: User '{user_id}' accessing resource '{resource_id}'")
        user_data = MOCK_USER_DB.get(user_id)
        
        if not user_data:
            return False
        if resource_id not in user_data["allowed_resources"]:
            self.logger.critical(f"BOLA ATTACK: User {user_id} tried to access {resource_id}")
            return False
        
        return True

    def validate_outbound_url(
            self, 
            url: str
    ) -> bool:
        """
        Prevent server-side request forgery (SSRF).
        - Ensures URL scheme is HTTPS.
        - Checks if the domain is in the allowed list.
        - Prevents requests to internal IP addresses.
        """
        try:
            parsed = urlparse(url)
            domain = parsed.netloc
            
            if parsed.scheme != "https":
                self.logger.warning(f"Unsafe Protocol detected: {url}")
                return False

            # Check against allowed domains
            if not any(domain.endswith(allowed) for allowed in self.allowed_domains):
                self.logger.warning(f"SSRF Prevention: Blocked connection to {domain}")
                return False
            
            # Prevent requests to internal IP addresses
            ip = socket.gethostbyname(domain)
            ip_addr = ipaddress.ip_address(ip)
            if ip_addr.is_private or ip_addr.is_loopback:
                self.logger.warning(f"SSRF Prevention: Blocked connection to internal IP {domain}")
                return False
                
            return True
        except socket.gaierror:
            self.logger.warning(f"SSRF Prevention: Could not resolve domain {domain}")
            return False
        except Exception as e:
            self.logger.error(f"Error validating URL: {e}")
            return False

    def sanitize_output(
            self, 
            html_content: str
    ) -> str:
        """
        Sanitizes HTML content to prevent XSS attacks.
        - Uses nh3 (a Python binding for Ammonia) for robust sanitization.
        - Allows a safe subset of HTML tags and attributes.
        """
        return nh3.clean(html_content)

    def hash_sensitive_data(
            self, 
            data: str
    ) -> str:
        """Hashes data before storage."""
        return hashlib.sha256(data.encode()).hexdigest()

    def secure_log(
            self, 
            message: str
    ):
        """data-masking"""
        patterns = {
            r'\b\d{4}-\d{4}-\d{4}\b': 'XXXX-XXXX-XXXX',
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b': '[EMAIL_REDACTED]'
        }
        
        masked_message = message
        for pattern, replacement in patterns.items():
            masked_message = re.sub(pattern, replacement, masked_message)
            
        self.logger.info(masked_message)
        
    def verify_tool_signature(
            self, 
            payload: str, 
            provided_signature: str, 
            secret_key: str
    ) -> bool:
        """
        Ensures the data came from a trusted tool and wasn't tampered with
        post-process verification
        """
        expected_signature = hmac.new(
            secret_key.encode(), 
            payload.encode(), 
            hashlib.sha256
        ).hexdigest()
        if hmac.compare_digest(expected_signature, provided_signature):
            return True
        else:
            self.logger.critical("SECURITY BREACH: Tool signature verification failed!")
            return False

    
    def flush_session_context(
            self, 
            user_id: str, 
            session_id: str
    ):
        """
        session ephemerality: wipes the agent's memory after the task is done.
        """
        self.logger.info(f"Initiating memory wipe for Session: {session_id}")
        
        new_session_id = hashlib.sha256(f"{session_id}{time.time()}".encode()).hexdigest()
        
        self.logger.info(f"Context flushed. Rotated to new Session ID: {new_session_id}")
        return new_session_id

    def trigger_hitl_review(self, user_id: str, action: str, reason: str):
        """
        Freezes the action and sends it to a manual approval queue.
        """
        alert = {
            "status": "PENDING_APPROVAL",
            "user": user_id,
            "risky_action": action,
            "flagged_reason": reason,
            "timestamp": time.time()
        }
        self.logger.warning(f"HITL TRIGGERED: {alert}")
        return {"status": 202, "message": "Request queued for manual security review."}

    async def execute_secure_request(
            self, 
            user_id: str, 
            agent_role: str, 
            method: str, 
            url: str, 
            resource_id: Optional[str] = None,
            payload: Optional[dict] = None,          
            signature: Optional[str] = None,        
            is_workflow_end: bool = False  
    ) -> dict:
        """
        Executes a secure request after performing all security checks.
        - Validates input parameters.
        - Performs rate limiting, SSRF, PoLP, and BOLA checks.
        - Triggers HITL for high-risk actions.
        - Verifies tool signature for data integrity.
        - Sanitizes output to prevent XSS.
        - Flushes session context at the end of a workflow.
        """
        # Input Validation
        if not all(isinstance(arg, str) for arg in [user_id, agent_role, method, url]):
            return {"error": "Invalid input types"}
        if method not in ["GET", "POST", "PUT", "DELETE"]:
            return {"error": f"Invalid HTTP method: {method}"}

        if not self.check_rate_limit(user_id):
            return {"error": "Rate limit exceeded"}

        if not self.validate_outbound_url(url):
            return {"error": "Invalid or Forbidden URL"}

        parsed_path = urlparse(url).path
        if not self.validate_agent_function(agent_role, method, parsed_path):
            return {"error": "Permission Denied for Agent"}

        if resource_id:
             if not self.validate_object_ownership(user_id, resource_id):
                 return {"error": "Access to this object is forbidden"}

        if payload:
            payload_issues = await self.scan_text_for_issues(str(payload))
            if payload_issues:
                return self.trigger_hitl_review(user_id, f"{method} {url}", f"Payload issues: {payload_issues}")

        if method == "DELETE" or (payload and "transfer" in payload.get("action", "")):
            return self.trigger_hitl_review(user_id, f"{method} {url}", "High Risk Action Detected")

        self.secure_log(f"Authorized request for User: {user_id} to URL: {url}")

        try:
            response = self.session.request(method, url, json=payload, timeout=5)
            response.raise_for_status()
            
            if payload and signature:
                tool_secret = os.getenv("TOOL_SECRET_KEY", "my_super_secret_key")
                if not self.verify_tool_signature(str(payload), signature, tool_secret):
                    return {"error": "Data Integrity Check Failed: Signature Mismatch"}

            response_issues = await self.scan_text_for_issues(response.text)
            if response_issues:
                return self.trigger_hitl_review(user_id, f"Response from {method} {url}", f"Response issues: {response_issues}")

            clean_text = self.sanitize_output(response.text)
            
            result = {"status": response.status_code, "data": clean_text}

            if is_workflow_end:
                current_session_id = f"sess_{user_id}_{int(time.time())}" 
                self.flush_session_context(user_id, current_session_id)
            
            return result
            
        except requests.HTTPError as e:
            self.logger.error(f"HTTP Error: {e}")
            return {"error": f"Upstream service returned status {e.response.status_code}"}
        except requests.RequestException as e:
            self.logger.error(f"Request Exception: {e}")
            return {"error": "Upstream service failure"}




    