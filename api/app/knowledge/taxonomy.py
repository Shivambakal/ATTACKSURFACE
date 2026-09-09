"""CWE/OWASP taxonomy and normalization utilities for the Security Knowledge Base."""
from __future__ import annotations

import re
from typing import Optional

# ---------------------------------------------------------------------------
# CWE name lookup dictionary (50+ entries covering high-priority weaknesses)
# ---------------------------------------------------------------------------
CWE_NAMES: dict[str, str] = {
    "CWE-1": "Location",
    "CWE-16": "Configuration",
    "CWE-20": "Improper Input Validation",
    "CWE-22": "Path Traversal",
    "CWE-59": "Link Following",
    "CWE-77": "Command Injection",
    "CWE-78": "OS Command Injection",
    "CWE-79": "Cross-Site Scripting (XSS)",
    "CWE-89": "SQL Injection",
    "CWE-90": "LDAP Injection",
    "CWE-94": "Code Injection",
    "CWE-95": "Eval Injection",
    "CWE-119": "Buffer Errors",
    "CWE-120": "Buffer Copy without Checking Size of Input",
    "CWE-121": "Stack-based Buffer Overflow",
    "CWE-122": "Heap-based Buffer Overflow",
    "CWE-125": "Out-of-bounds Read",
    "CWE-134": "Use of Externally-Controlled Format String",
    "CWE-190": "Integer Overflow or Wraparound",
    "CWE-200": "Exposure of Sensitive Information to an Unauthorized Actor",
    "CWE-209": "Generation of Error Message Containing Sensitive Information",
    "CWE-250": "Execution with Unnecessary Privileges",
    "CWE-255": "Credentials Management Errors",
    "CWE-269": "Improper Privilege Management",
    "CWE-276": "Incorrect Default Permissions",
    "CWE-284": "Improper Access Control",
    "CWE-285": "Improper Authorization",
    "CWE-287": "Improper Authentication",
    "CWE-295": "Improper Certificate Validation",
    "CWE-306": "Missing Authentication for Critical Function",
    "CWE-307": "Improper Restriction of Excessive Authentication Attempts",
    "CWE-311": "Missing Encryption of Sensitive Data",
    "CWE-312": "Cleartext Storage of Sensitive Information",
    "CWE-319": "Cleartext Transmission of Sensitive Information",
    "CWE-326": "Inadequate Encryption Strength",
    "CWE-327": "Use of a Broken or Risky Cryptographic Algorithm",
    "CWE-330": "Use of Insufficiently Random Values",
    "CWE-352": "Cross-Site Request Forgery (CSRF)",
    "CWE-362": "Race Condition",
    "CWE-400": "Uncontrolled Resource Consumption",
    "CWE-401": "Missing Release of Memory after Effective Lifetime",
    "CWE-416": "Use After Free",
    "CWE-426": "Untrusted Search Path",
    "CWE-434": "Unrestricted Upload of File with Dangerous Type",
    "CWE-476": "NULL Pointer Dereference",
    "CWE-502": "Deserialization of Untrusted Data",
    "CWE-521": "Weak Password Requirements",
    "CWE-522": "Insufficiently Protected Credentials",
    "CWE-601": "URL Redirection to Untrusted Site ('Open Redirect')",
    "CWE-611": "Improper Restriction of XML External Entity Reference (XXE)",
    "CWE-639": "Authorization Bypass Through User-Controlled Key (IDOR)",
    "CWE-732": "Incorrect Permission Assignment for Critical Resource",
    "CWE-787": "Out-of-bounds Write",
    "CWE-798": "Use of Hard-coded Credentials",
    "CWE-824": "Access of Uninitialized Pointer",
    "CWE-862": "Missing Authorization",
    "CWE-863": "Incorrect Authorization",
    "CWE-917": "Improper Neutralization of Special Elements used in an Expression Language Statement",
    "CWE-918": "Server-Side Request Forgery (SSRF)",
    "CWE-943": "Improper Neutralization of Special Elements in Data Query Logic",
}

# ---------------------------------------------------------------------------
# CWE -> Vulnerability Class mapping (high-level buckets for correlation)
# ---------------------------------------------------------------------------
CWE_TO_VULN_CLASS: dict[str, str] = {
    "CWE-20": "Input Validation",
    "CWE-22": "Path Traversal",
    "CWE-59": "Path Traversal",
    "CWE-77": "Command Injection",
    "CWE-78": "Command Injection",
    "CWE-79": "Cross-Site Scripting",
    "CWE-89": "SQL Injection",
    "CWE-90": "Injection",
    "CWE-94": "Code Injection",
    "CWE-95": "Code Injection",
    "CWE-119": "Memory Corruption",
    "CWE-120": "Memory Corruption",
    "CWE-121": "Memory Corruption",
    "CWE-122": "Memory Corruption",
    "CWE-125": "Memory Corruption",
    "CWE-134": "Memory Corruption",
    "CWE-190": "Memory Corruption",
    "CWE-200": "Information Disclosure",
    "CWE-209": "Information Disclosure",
    "CWE-250": "Privilege Escalation",
    "CWE-255": "Credential Exposure",
    "CWE-269": "Privilege Escalation",
    "CWE-284": "Broken Access Control",
    "CWE-285": "Broken Access Control",
    "CWE-287": "Authentication Bypass",
    "CWE-295": "Cryptographic Failure",
    "CWE-306": "Authentication Bypass",
    "CWE-307": "Authentication Bypass",
    "CWE-311": "Cryptographic Failure",
    "CWE-312": "Cryptographic Failure",
    "CWE-319": "Cryptographic Failure",
    "CWE-326": "Cryptographic Failure",
    "CWE-327": "Cryptographic Failure",
    "CWE-330": "Cryptographic Failure",
    "CWE-352": "CSRF",
    "CWE-362": "Race Condition",
    "CWE-400": "Denial of Service",
    "CWE-401": "Memory Corruption",
    "CWE-416": "Memory Corruption",
    "CWE-426": "Privilege Escalation",
    "CWE-434": "File Upload",
    "CWE-476": "Memory Corruption",
    "CWE-502": "Insecure Deserialization",
    "CWE-521": "Credential Exposure",
    "CWE-522": "Credential Exposure",
    "CWE-601": "Open Redirect",
    "CWE-611": "XXE",
    "CWE-639": "Broken Access Control",
    "CWE-732": "Broken Access Control",
    "CWE-787": "Memory Corruption",
    "CWE-798": "Credential Exposure",
    "CWE-862": "Broken Access Control",
    "CWE-863": "Broken Access Control",
    "CWE-917": "Injection",
    "CWE-918": "SSRF",
    "CWE-943": "Injection",
}

# ---------------------------------------------------------------------------
# OWASP Top 10 2021
# ---------------------------------------------------------------------------
OWASP_2021: list[dict] = [
    {"category_id": "A01:2021", "category_name": "Broken Access Control",
     "description": "Access control enforces policy such that users cannot act outside of their intended permissions.",
     "source_url": "https://owasp.org/Top10/A01_2021-Broken_Access_Control/"},
    {"category_id": "A02:2021", "category_name": "Cryptographic Failures",
     "description": "Failures related to cryptography which often lead to exposure of sensitive data.",
     "source_url": "https://owasp.org/Top10/A02_2021-Cryptographic_Failures/"},
    {"category_id": "A03:2021", "category_name": "Injection",
     "description": "SQL, NoSQL, OS, LDAP injection when untrusted data is sent to an interpreter.",
     "source_url": "https://owasp.org/Top10/A03_2021-Injection/"},
    {"category_id": "A04:2021", "category_name": "Insecure Design",
     "description": "Missing or ineffective control design representing a new category for 2021.",
     "source_url": "https://owasp.org/Top10/A04_2021-Insecure_Design/"},
    {"category_id": "A05:2021", "category_name": "Security Misconfiguration",
     "description": "Missing appropriate security hardening across the application stack.",
     "source_url": "https://owasp.org/Top10/A05_2021-Security_Misconfiguration/"},
    {"category_id": "A06:2021", "category_name": "Vulnerable and Outdated Components",
     "description": "Components such as libraries and frameworks used without knowing their vulnerabilities.",
     "source_url": "https://owasp.org/Top10/A06_2021-Vulnerable_and_Outdated_Components/"},
    {"category_id": "A07:2021", "category_name": "Identification and Authentication Failures",
     "description": "Authentication-related issues allowing attackers to assume identities.",
     "source_url": "https://owasp.org/Top10/A07_2021-Identification_and_Authentication_Failures/"},
    {"category_id": "A08:2021", "category_name": "Software and Data Integrity Failures",
     "description": "Code and infrastructure integrity failures including insecure deserialization.",
     "source_url": "https://owasp.org/Top10/A08_2021-Software_and_Data_Integrity_Failures/"},
    {"category_id": "A09:2021", "category_name": "Security Logging and Monitoring Failures",
     "description": "Missing or inadequate logging and monitoring to detect and respond to breaches.",
     "source_url": "https://owasp.org/Top10/A09_2021-Security_Logging_and_Monitoring_Failures/"},
    {"category_id": "A10:2021", "category_name": "Server-Side Request Forgery",
     "description": "SSRF flaws occur when a web application fetches a remote resource without validating the user-supplied URL.",
     "source_url": "https://owasp.org/Top10/A10_2021-Server-Side_Request_Forgery_%28SSRF%29/"},
]

# ---------------------------------------------------------------------------
# CWE -> OWASP 2021 category mapping
# ---------------------------------------------------------------------------
CWE_TO_OWASP_2021: dict[str, str] = {
    # A01 Broken Access Control
    "CWE-22": "A01:2021",
    "CWE-59": "A01:2021",
    "CWE-200": "A01:2021",
    "CWE-250": "A01:2021",
    "CWE-276": "A01:2021",
    "CWE-284": "A01:2021",
    "CWE-285": "A01:2021",
    "CWE-352": "A01:2021",
    "CWE-362": "A01:2021",
    "CWE-601": "A01:2021",
    "CWE-639": "A01:2021",
    "CWE-732": "A01:2021",
    "CWE-862": "A01:2021",
    "CWE-863": "A01:2021",
    # A02 Cryptographic Failures
    "CWE-261": "A02:2021",
    "CWE-296": "A02:2021",
    "CWE-310": "A02:2021",
    "CWE-311": "A02:2021",
    "CWE-312": "A02:2021",
    "CWE-319": "A02:2021",
    "CWE-321": "A02:2021",
    "CWE-322": "A02:2021",
    "CWE-323": "A02:2021",
    "CWE-324": "A02:2021",
    "CWE-325": "A02:2021",
    "CWE-326": "A02:2021",
    "CWE-327": "A02:2021",
    "CWE-328": "A02:2021",
    "CWE-329": "A02:2021",
    "CWE-330": "A02:2021",
    "CWE-331": "A02:2021",
    "CWE-335": "A02:2021",
    "CWE-338": "A02:2021",
    "CWE-340": "A02:2021",
    "CWE-347": "A02:2021",
    "CWE-523": "A02:2021",
    "CWE-720": "A02:2021",
    "CWE-757": "A02:2021",
    "CWE-759": "A02:2021",
    "CWE-760": "A02:2021",
    "CWE-780": "A02:2021",
    "CWE-818": "A02:2021",
    "CWE-916": "A02:2021",
    # A03 Injection
    "CWE-20": "A03:2021",
    "CWE-77": "A03:2021",
    "CWE-78": "A03:2021",
    "CWE-79": "A03:2021",
    "CWE-89": "A03:2021",
    "CWE-90": "A03:2021",
    "CWE-94": "A03:2021",
    "CWE-116": "A03:2021",
    "CWE-138": "A03:2021",
    "CWE-184": "A03:2021",
    "CWE-470": "A03:2021",
    "CWE-471": "A03:2021",
    "CWE-564": "A03:2021",
    "CWE-610": "A03:2021",
    "CWE-643": "A03:2021",
    "CWE-644": "A03:2021",
    "CWE-652": "A03:2021",
    "CWE-917": "A03:2021",
    "CWE-943": "A03:2021",
    # A07 Identification and Authentication Failures
    "CWE-255": "A07:2021",
    "CWE-259": "A07:2021",
    "CWE-287": "A07:2021",
    "CWE-288": "A07:2021",
    "CWE-290": "A07:2021",
    "CWE-294": "A07:2021",
    "CWE-295": "A07:2021",
    "CWE-297": "A07:2021",
    "CWE-300": "A07:2021",
    "CWE-302": "A07:2021",
    "CWE-304": "A07:2021",
    "CWE-305": "A07:2021",
    "CWE-306": "A07:2021",
    "CWE-307": "A07:2021",
    "CWE-346": "A07:2021",
    "CWE-384": "A07:2021",
    "CWE-521": "A07:2021",
    "CWE-522": "A07:2021",
    "CWE-524": "A07:2021",
    "CWE-525": "A07:2021",
    "CWE-539": "A07:2021",
    "CWE-579": "A07:2021",
    "CWE-598": "A07:2021",
    "CWE-620": "A07:2021",
    "CWE-640": "A07:2021",
    "CWE-798": "A07:2021",
    "CWE-940": "A07:2021",
    "CWE-1216": "A07:2021",
    # A08 Software and Data Integrity Failures
    "CWE-345": "A08:2021",
    "CWE-353": "A08:2021",
    "CWE-426": "A08:2021",
    "CWE-494": "A08:2021",
    "CWE-502": "A08:2021",
    "CWE-565": "A08:2021",
    "CWE-784": "A08:2021",
    "CWE-829": "A08:2021",
    "CWE-830": "A08:2021",
    "CWE-913": "A08:2021",
    # A10 SSRF
    "CWE-918": "A10:2021",
    # A05 Security Misconfiguration
    "CWE-16": "A05:2021",
    "CWE-209": "A05:2021",
    "CWE-400": "A05:2021",
    # A06 Vulnerable and Outdated Components
    "CWE-611": "A06:2021",
    # Memory corruption -> A04 Insecure Design
    "CWE-119": "A04:2021",
    "CWE-787": "A04:2021",
    "CWE-416": "A04:2021",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_cwe_name(cwe_id: str) -> str:
    """Return the human-readable name for a CWE ID, or a generic fallback."""
    normalized = normalize_cwe_id(cwe_id)
    return CWE_NAMES.get(normalized, f"Unknown Weakness ({normalized})")


def normalize_cwe_id(raw: str) -> str:
    """Normalize a raw CWE string to canonical form 'CWE-NNN'.

    Handles inputs like: 'cwe-79', '79', 'CWE79', 'CWE:79', 'CWE_79'.
    """
    if not raw:
        return ""
    raw = raw.strip()
    # If already in canonical form
    if re.match(r"^CWE-\d+$", raw, re.IGNORECASE):
        digits_match = re.search(r"\d+", raw)
        return f"CWE-{digits_match.group()}" if digits_match else raw.upper()
    # Extract digits
    digits = re.search(r"\d+", raw)
    if digits:
        return f"CWE-{digits.group()}"
    return raw.upper()



def normalize_cve_id(raw: str) -> Optional[str]:
    """Normalize a CVE ID string to canonical 'CVE-YYYY-NNNNN' form.

    Returns None if the string does not match a valid CVE pattern.
    """
    if not raw:
        return None
    raw = raw.strip().upper()
    match = re.search(r"CVE-(\d{4})-(\d{4,})", raw)
    if match:
        return f"CVE-{match.group(1)}-{match.group(2)}"
    return None


def get_owasp_2021_category_for_cwe(cwe_id: str) -> Optional[str]:
    """Return the OWASP 2021 category ID for a given CWE, or None."""
    normalized = normalize_cwe_id(cwe_id)
    return CWE_TO_OWASP_2021.get(normalized)


def get_vuln_class_for_cwe(cwe_id: str) -> Optional[str]:
    """Return a high-level vulnerability class string for a given CWE, or None."""
    normalized = normalize_cwe_id(cwe_id)
    return CWE_TO_VULN_CLASS.get(normalized)
