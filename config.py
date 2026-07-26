"""Hardcoded constants shared by storage.py (and, transitively, every agent).

Deliberately does NOT include a Python structure for the CLAUDE.md agent
roster (Orchestrator, KB Manager, etc.) — nothing in code consumes such a
structure today, so it would just be unused scaffolding. CLAUDE.md's prose
is the source of truth for the roster; encode it here only once real code
actually needs to iterate over it (e.g. a dispatcher routing directives to
specific agents by name).
"""

CF_API_BASE = "https://api.cloudflare.com/client/v4"
EMBEDDING_MODEL = "@cf/baai/bge-base-en-v1.5"

ASSURANCE_OFFICES = {"review_critic", "safety_risk", "regulatory"}

# storage.py input validation bounds
MAX_BASELINE_CONFIG_BYTES = 10 * 1024 * 1024  # 10 MB
MIN_REQUIREMENT_TEXT_LENGTH = 1
MAX_REQUIREMENT_TEXT_LENGTH = 5000
MAX_SIGNOFF_NOTES_LENGTH = 1000

# Cloudflare Vectorize API limits
GET_BY_IDS_MAX_BATCH = 20  # error code 40007 above this
