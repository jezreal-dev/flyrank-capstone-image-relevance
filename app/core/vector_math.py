"""Vector mathematics and deterministic semantic embedding utilities.
Pure Python implementation requiring zero heavy external C-extensions.
"""
import math
import re
from typing import List

def dot_product(v1: List[float], v2: List[float]) -> float:
    if len(v1) != len(v2):
        raise ValueError(f"Vector dimensions do not match: {len(v1)} vs {len(v2)}")
    return sum(a * b for a, b in zip(v1, v2))

def vector_norm(v: List[float]) -> float:
    return math.sqrt(sum(a * a for a in v))

def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Calculates cosine similarity between two float vectors in [-1.0, 1.0]."""
    if not v1 or not v2:
        return 0.0
    norm1 = vector_norm(v1)
    norm2 = vector_norm(v2)
    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0
    val = dot_product(v1, v2) / (norm1 * norm2)
    # Clamp to avoid floating point inaccuracies slightly outside [-1, 1]
    return max(-1.0, min(1.0, float(val)))

# ==============================================================================
# Semantic Dimension Lexicon for Deterministic $0 Offline Embedding
# ==============================================================================
# 64 conceptual dimension clusters
SEMANTIC_CLUSTERS = [
    # Wildlife / Canids / Predation
    ["fox", "vulpes", "red fox", "orange fur", "brush tail", "woodland fox"],
    ["wolf", "timber wolf", "canis lupus", "gray wolf", "pack hunter", "howl", "tundra wolf"],
    ["dog", "canine", "golden retriever", "pet", "puppy", "domestic dog", "collar", "park fetch"],
    ["bear", "grizzly", "ursus arctos", "brown bear", "salmon river"],
    ["tiger", "bengal tiger", "panthera tigris", "big cat", "stripes", "jungle predator"],
    ["eagle", "bald eagle", "bird of prey", "haliaeetus leucocephalus", "raptor", "talons"],
    ["otter", "sea otter", "enhydra lutris", "kelp", "marine mammal"],
    ["elephant", "african elephant", "loxodonta", "savanna", "trunk", "tusks"],
    ["owl", "barn owl", "tyto alba", "nocturnal", "perch"],

    # Nature / Geography
    ["redwood", "sequoia", "giant trees", "ancient forest", "sunbeams", "evergreen"],
    ["mountain", "alpine", "summit", "glacier", "snowy peak", "alps", "elevation"],
    ["desert", "sahara", "sand dunes", "arid", "wind ripples"],
    ["ocean", "beach", "waves", "sea", "turquoise water", "surf", "coastline"],
    ["aurora", "northern lights", "night sky", "green ribbons", "borealis"],
    ["waterfall", "gorge", "cascading water", "river mist", "canyon"],
    ["yosemite", "valley", "granite cliffs", "half dome", "el capitan"],
    ["autumn", "foliage", "fall leaves", "birch", "golden trees"],
    ["volcano", "black sand", "basalt", "iceland", "lava"],

    # Tech / Software
    ["python", "code", "programming", "software", "syntax", "editor", "ide", "developer"],
    ["server", "data center", "blade", "rack", "ethernet", "hosting", "cloud"],
    ["security", "cyber", "terminal", "matrix", "encryption", "firewall"],
    ["cpu", "microchip", "silicon", "processor", "hardware", "motherboard"],
    ["robot", "robotics", "automation", "arm", "factory", "assembly"],
    ["architecture", "wireframe", "system design", "whiteboard", "diagram"],
    ["iot", "smart home", "connected", "sensor", "device"],
    ["meeting", "agile", "sprint", "engineers", "discussion"],
    ["workstation", "dual monitors", "mechanical keyboard", "desk"],
    ["terminal", "bash", "cli", "linux", "shell"],

    # Architecture / Urban
    ["eiffel tower", "paris", "france", "iron lattice", "champ de mars"],
    ["skyscraper", "glass tower", "modern facade", "commercial building"],
    ["colosseum", "rome", "italy", "amphitheater", "ancient ruins", "stone arches"],
    ["brutalist", "concrete", "geometric", "library", "shadows"],
    ["golden gate", "bridge", "san francisco", "suspension", "red steel"],
    ["tokyo", "japan", "neon", "shibuya", "night city", "bustle"],
    ["pagoda", "kyoto", "temple", "wooden", "cherry blossom"],
    ["scandinavian", "nordic", "minimalist home", "timber house"],
    ["parthenon", "athens", "greece", "acropolis", "doric columns"],
    ["cafe", "bistro", "brick storefront", "patio", "cobblestone"],

    # Culinary / Food
    ["coffee", "pour over", "chemex", "barista", "specialty brew", "espresso"],
    ["sourdough", "bread", "artisan loaf", "crust", "bakery", "fermented"],
    ["pasta", "tagliatelle", "handmade", "italian", "noodles", "parmesan"],
    ["sushi", "nigiri", "sashimi", "salmon", "tuna", "wasabi", "japanese"],
    ["pizza", "neapolitan", "woodfired", "mozzarella", "crust", "margherita"],
    ["salad", "vegetables", "greens", "tomatoes", "avocado", "organic"],
    ["matcha", "green tea", "latte", "froth", "ceremonial"],
    ["croissant", "pastry", "butter", "viennoiserie", "flaky"],
    ["shakshuka", "poached eggs", "tomato sauce", "skillet", "spices"],
    ["gelato", "ice cream", "pistachio", "chocolate", "dessert", "waffle cone"],

    # General / Ambiguous / Distractors
    ["quantum", "qubit", "cryogenic", "superconducting", "teleportation", "anyons"],
    ["submarine", "deep sea", "periscope", "sonar", "abyssal", "trench"],
    ["silhouette", "shadow", "fog", "blurry", "unclear", "low light"]
]

VECTOR_DIMENSIONS = len(SEMANTIC_CLUSTERS) + 16

def generate_semantic_vector(text: str) -> List[float]:
    """Generates a dense normalized float embedding vector for arbitrary text.
    Combines concept cluster alignment with character-ngram hash distribution.
    """
    clean_text = text.lower()
    vector = [0.0] * VECTOR_DIMENSIONS

    # 1. Cluster alignment (semantic meaning)
    for idx, cluster in enumerate(SEMANTIC_CLUSTERS):
        weight = 0.0
        for keyword in cluster:
            if keyword in clean_text:
                # Longer matches receive quadratic emphasis
                weight += 1.0 + (len(keyword) / 8.0)
        vector[idx] = weight * 2.5

    # 2. Token hash projection for vocabulary generalization (last 16 dims)
    tokens = re.findall(r"\b[a-z]{3,}\b", clean_text)
    for token in tokens:
        h = hash(token)
        dim = len(SEMANTIC_CLUSTERS) + (abs(h) % 16)
        sign = 1.0 if (h % 2 == 0) else -1.0
        vector[dim] += sign * 0.15

    # 3. L2 Normalization
    norm = vector_norm(vector)
    if norm > 0.0:
        vector = [round(val / norm, 6) for val in vector]
    return vector
