"""NLP processing MCP server using FastMCP."""

from mcp.server.fastmcp import FastMCP
from typing import Optional

mcp = FastMCP("nlp-server")

RELATION_MAP = {
    "father": ("father", "parent", "M"),
    "mother": ("mother", "parent", "F"),
    "son": ("son", "child", "M"),
    "daughter": ("daughter", "child", "F"),
    "husband": ("husband", "spouse", "M"),
    "wife": ("wife", "spouse", "F"),
    "brother": ("brother", "sibling", "M"),
    "sister": ("sister", "sibling", "F"),
    "bhau": ("brother", "sibling", "M"),
    "bhaau": ("brother", "sibling", "M"),
    "bahin": ("sister", "sibling", "F"),
    "aai": ("mother", "parent", "F"),
    "baba": ("father", "parent", "M"),
    "navra": ("husband", "spouse", "M"),
    "bayko": ("wife", "spouse", "F"),
    "bhai": ("brother", "sibling", "M"),
    "behen": ("sister", "sibling", "F"),
    "pita": ("father", "parent", "M"),
    "mata": ("mother", "parent", "F"),
}


@mcp.tool()
def normalize_relation(term: str) -> dict:
    """Normalize relationship term to standard English form."""
    key = term.lower().strip()
    if key in RELATION_MAP:
        norm, rel_type, gender = RELATION_MAP[key]
        return {"term": norm, "type": rel_type, "implied_gender": gender}
    return {"term": key, "type": "unknown", "implied_gender": None}


@mcp.tool()
def infer_gender(name: str) -> dict:
    """Infer gender from name patterns."""
    if not name:
        return {"gender": None, "confidence": 0.0}
    
    first = name.lower().split()[0]
    
    female = ['padma', 'priya', 'sita', 'radha', 'lakshmi', 'kavya', 'ananya', 'sneha', 'jyoti']
    male = ['ramesh', 'suresh', 'mahesh', 'rajesh', 'krishna', 'ravi', 'vijay', 'vishrut', 'arjun']
    
    if first in female:
        return {"gender": "F", "confidence": 0.9}
    if first in male:
        return {"gender": "M", "confidence": 0.9}
    
    if first.endswith(('a', 'i', 'ee', 'devi', 'bai')):
        return {"gender": "F", "confidence": 0.6}
    if first.endswith(('sh', 'raj', 'kumar', 'deep', 'esh')):
        return {"gender": "M", "confidence": 0.6}
    
    return {"gender": None, "confidence": 0.0}


@mcp.tool()
def detect_language(text: str) -> dict:
    """Detect language from text using keyword matching."""
    text_lower = text.lower()
    detected = []
    
    indicators = {
        'marathi': ['maza', 'mazha', 'aahe', 'bhau', 'aai', 'baba', 'madhe', 'rahto'],
        'hindi': ['mera', 'meri', 'hai', 'hain', 'bhai', 'behen', 'mata', 'pita'],
        'tamil': ['enna', 'amma', 'appa', 'anna', 'akka', 'thambi', 'paati'],
        'telugu': ['naa', 'naaku', 'nanna', 'tammudu', 'chelli', 'ammamma'],
    }
    
    for lang, words in indicators.items():
        if any(word in text_lower for word in words):
            detected.append(lang)
    
    if not detected:
        detected.append('english')
    
    return {'languages': detected, 'primary': detected[0]}


@mcp.tool()
def extract_family_name(names: list[str]) -> dict:
    """Extract common family name from list of full names."""
    from collections import Counter
    
    last_names = []
    for name in names:
        parts = name.strip().split()
        if len(parts) > 1:
            last_names.append(parts[-1].title())
    
    if not last_names:
        return {"family_name": None, "confidence": 0.0}
    
    counts = Counter(last_names)
    most_common = counts.most_common(1)
    
    if most_common and most_common[0][1] >= 2:
        return {"family_name": most_common[0][0], "confidence": 0.9}
    
    return {"family_name": last_names[0], "confidence": 0.5}


if __name__ == "__main__":
    mcp.run()
