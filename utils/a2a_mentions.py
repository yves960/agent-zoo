"""
A2A (Animal-to-Animal) mentions parser for Zoo Multi-Agent System.

Handles parsing @mentions in the format: @雪球 @六六 @小黄
"""

import re
from typing import List


ANIMAL_CONFIGS = {
    "xueqiu": {
        "name": "雪球",
        "patterns": ["@雪球", "@xueqiu", "@雪纳瑞"],
    },
    "liuliu": {
        "name": "六六",
        "patterns": ["@六六", "@liuliu", "@蓝鹦鹉"],
    },
    "xiaohuang": {
        "name": "小黄",
        "patterns": ["@小黄", "@xiaohuang", "@黄鹦鹉"],
    },
    "meiqiu": {
        "name": "煤球",
        "patterns": ["@煤球", "@meiqiu"],
    },
}

# Pre-compute reverse mapping from pattern to animal key
PATTERN_TO_ANIMAL = {}
for animal_key, config in ANIMAL_CONFIGS.items():
    for pattern in config["patterns"]:
        PATTERN_TO_ANIMAL[pattern] = animal_key


def parse_a2a_mentions(text: str, current_animal: str) -> List[str]:
    """
    Parse @mentions from text for A2A routing.
    
    Args:
        text: The text potentially containing @mentions
        current_animal: The current animal's key (cannot mention self)
        
    Returns:
        List of animal keys to route to (max 2 targets)
    """
    # Strip code blocks to avoid false positives in code
    text_without_code = re.sub(r'```[\s\S]*?```', '', text)
    text_without_code = re.sub(r'`[^`]+`', '', text_without_code)
    
    # Find all @mentions at line start or after whitespace
    # Pattern matches @ followed by animal name patterns
    mention_patterns = list(PATTERN_TO_ANIMAL.keys())
    
    # Build combined pattern with word boundary support
    escaped_patterns = [re.escape(p) for p in mention_patterns]
    combined_pattern = r'(?:^|\s)(' + '|'.join(escaped_patterns) + r')\b'
    
    matches = re.finditer(combined_pattern, text_without_code)
    
    # Track unique targets in order of appearance
    targets = []
    seen = set()
    
    for match in matches:
        mention = match.group(1)
        animal_key = PATTERN_TO_ANIMAL.get(mention)
        
        if animal_key and animal_key != current_animal and animal_key not in seen:
            targets.append(animal_key)
            seen.add(animal_key)
            
            # Limit to 2 targets
            if len(targets) >= 2:
                break
    
    return targets


def get_animal_names() -> dict:
    """Return animal key to name mapping."""
    return {key: config["name"] for key, config in ANIMAL_CONFIGS.items()}


def get_animal_patterns(animal_key: str) -> List[str]:
    """Get all mention patterns for a specific animal."""
    return ANIMAL_CONFIGS.get(animal_key, {}).get("patterns", [])
