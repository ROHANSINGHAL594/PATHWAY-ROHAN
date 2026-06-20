import asyncio
from dataclasses import dataclass, field
from typing import List, Tuple
from .gateway import (
    DetectorResult,
    PII_Analyzer,
    PromptInjectionAnalyzer,
    SecretsAnalyzer,
)
from lib.logger import custom_logger
from .gateway import MCPSecurityGateway

gateway = MCPSecurityGateway()

@dataclass
class ScanResult:
    is_safe: bool
    sanitized_input: str
    findings: List[DetectorResult] = field(default_factory=list)
    is_sanitized: bool = False

class InputScanner:
    """Scans and sanitizes text inputs before they are sent to an LLM."""

    def __init__(
            self
    ):
        self.prompt_injection_detector = PromptInjectionAnalyzer()
        self.pii_detector = PII_Analyzer()
        self.secrets_detector = SecretsAnalyzer()

    async def preload_models(
            self,
    ):
        """
        Preloads detector models for lower latency on first use.
        """
        # Preload both prompt injection and PII analyzers
        await asyncio.gather(
            self.prompt_injection_detector.preload(),
            self.pii_detector._ensure_initialized()
        )

    async def scan(
            self, 
            text: str
    ) -> ScanResult:
        """
        Scans user input for threats and redacts sensitive data.

        Args:
            text: The input string to scan.

        Returns:
            A ScanResult object containing the outcome.
        """
        try:
            # Run async detectors in parallel
            # Note: PromptInjectionAnalyzer.adetect returns bool, PII_Analyzer.adetect returns list
            injection_task = self.prompt_injection_detector.adetect(text)
            pii_task = self.pii_detector.adetect(text)  # Fixed: use adetect not adetect_all

            injection_detected, pii_results = await asyncio.gather(
                injection_task, pii_task
            )
            
            # Run synchronous secrets detector separately
            secrets_results = self.secrets_detector.detect_all(text)
            
            if injection_detected:
                return ScanResult(is_safe=False, sanitized_input="Invalid input.", findings=[injection_detected])

            all_findings = (pii_results or []) + (secrets_results or [])
            if not all_findings:
                return ScanResult(is_safe=True, sanitized_input=text)

            sanitized_input = self._sanitize_text(text, all_findings)

            return ScanResult(
                is_safe=True,
                sanitized_input=sanitized_input,
                findings=all_findings,
                is_sanitized=True,
            )

        except Exception as e:
            return ScanResult(is_safe=False, sanitized_input="Error during security scan.")

    @staticmethod
    def _sanitize_text(
        text: str, 
        findings: List[DetectorResult]
    ) -> str:
        """
        Robustly redacts findings from text.

        It sorts findings by start index in reverse to avoid issues with
        string index changes during replacement.
        """
        if not findings:
            return text
        findings.sort(key=lambda f: f.start, reverse=True)

        sanitized_text = list(text)
        for finding in findings:
            redaction_str = f"[{finding.entity}_REDACTED]"
            sanitized_text[finding.start : finding.end] = redaction_str

        return "".join(sanitized_text)
    

async def detect(text :str):
    pii_results = await gateway.pii_analyzer.adetect(text)
    print(pii_results)
    secrets_results = gateway.secrets_analyzer.detect_all(text)
    
    if pii_results:
        custom_logger.critical("PII Data detected in agent description")
    
    if secrets_results:
        custom_logger.critical("Secret Data detected in agent description")

    # Filter out DATE_TIME entities to prevent timestamp redaction
    all_findings = (pii_results or []) + (secrets_results or [])
    filtered_findings = [f for f in all_findings if f.entity != 'DATE_TIME']
    sanitized_description = InputScanner._sanitize_text(text, filtered_findings)
    
    if filtered_findings:
        custom_logger.info("Input data was sanitized for PII/secrets.")
    
    return sanitized_description

# async def main():
#     """Demonstrates the InputScanner functionality."""
#     scanner = InputScanner()
#     # await scanner.preload_models()


# if __name__ == "__main__":
#     asyncio.run(main())