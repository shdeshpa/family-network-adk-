"""Text processing utilities for agents."""

from typing import Optional
from collections import Counter


class TextUtils:
    """Utilities for text processing."""
    
    @staticmethod
    def clean_name(name: str) -> str:
        """Clean and normalize a name."""
        if not name:
            return ""
        return " ".join(name.split()).strip().title()
    
    @staticmethod
    def extract_family_name(names: list[str]) -> Optional[str]:
        """Extract common family name from list of names."""
        if not names:
            return None
        
        last_names = []
        for name in names:
            parts = name.strip().split()
            if len(parts) > 1:
                last_names.append(parts[-1].title())
        
        if not last_names:
            return None
        
        counts = Counter(last_names)
        most_common = counts.most_common(1)
        
        if most_common and most_common[0][1] >= 2:
            return most_common[0][0]
        
        return last_names[0] if last_names else None
    
    @staticmethod
    def detect_language_hints(text: str) -> list[str]:
        """Detect language hints from text."""
        text_lower = text.lower()
        languages = []
        
        # Marathi
        if any(w in text_lower for w in ['maza', 'mazha', 'aahe', 'bhau', 'aai', 'baba', 'kaku', 'madhe']):
            languages.append('marathi')
        
        # Hindi
        if any(w in text_lower for w in ['mera', 'meri', 'hai', 'bhai', 'behen', 'mata', 'pita']):
            languages.append('hindi')
        
        # Tamil
        if any(w in text_lower for w in ['enna', 'amma', 'appa', 'anna', 'akka', 'thambi', 'paati']):
            languages.append('tamil')
        
        # Telugu
        if any(w in text_lower for w in ['naa', 'naaku', 'nanna', 'tammudu', 'chelli', 'ammamma']):
            languages.append('telugu')
        
        if not languages:
            languages.append('english')
        
        return languages
    
    @staticmethod
    def infer_gender_from_name(name: str) -> Optional[str]:
        """Infer gender from common Indian name patterns."""
        if not name:
            return None
        
        first_name = name.lower().strip().split()[0] if name else ""
        
        female_names = ['padma', 'priya', 'sita', 'gita', 'radha', 'lakshmi', 'kavya', 'ananya', 'sneha', 'pooja', 'neha', 'riya']
        male_names = ['ramesh', 'suresh', 'mahesh', 'rajesh', 'krishna', 'ram', 'ravi', 'anil', 'vijay', 'vishrut', 'arjun', 'amit']
        
        if first_name in female_names:
            return 'F'
        if first_name in male_names:
            return 'M'
        
        # Check endings
        if first_name.endswith(('a', 'i', 'ee', 'ya', 'devi', 'bai', 'ben')):
            return 'F'
        if first_name.endswith(('sh', 'raj', 'kumar', 'deep', 'esh', 'an', 'ar')):
            return 'M'
        
        return None
    
    @staticmethod
    def split_full_name(full_name: str) -> tuple[str, str]:
        """Split full name into first and last name."""
        parts = full_name.strip().split()
        if len(parts) == 1:
            return parts[0], ""
        return parts[0], " ".join(parts[1:])
