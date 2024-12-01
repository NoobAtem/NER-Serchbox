import yaml, os, spacy, logging
import numpy as np
from spacy.matcher import PhraseMatcher
from logging.handlers import RotatingFileHandler

"""
    This version of nlp collects different
    variation that follows the same philosophy
    which is POS, Info Extract and NER with indexing, 
    keywords, and espcially, not subjected to training.
"""

LOG: object = logging.getLogger(__name__)
LOG.setLevel(logging.INFO)

file_handler:object = RotatingFileHandler("log/model.log", maxBytes=5*1024*1024, backupCount=5)
stream_handler = logging.StreamHandler()

formatter: object = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s: %(message)s")
file_handler.setFormatter(formatter)
stream_handler.setFormatter(formatter)

LOG.addHandler(file_handler)
LOG.addHandler(stream_handler)

CONFIG_LS: list = [
    "settings"
] # will be used when fetch_config is called and will load all yaml config listed
nlp: object = spacy.load('en_core_web_sm')

def fetch_config() -> dict:
    ls: list = {}
    try: 
        for f in CONFIG_LS:
            LOG.debug(f"---> Config name: {f}")
            with open("config/"+f+".yaml", "r") as conf:
                ls[f] = yaml.safe_load(conf)
    except:
        LOG.error("*** Something went wrong loading configs ***")
        sys.exit()
    LOG.info("---> Succesful loading of config")
    return ls

class ModelType1:
    """
        Uses the POS and Dependency Parsing which is
        enchanced with predefined keywords that identifies
        different pattern matches that is used for
        information extraction, and semantics
    """
    def __init__(self):
        LOG.info("---> Model class initializing") 
        self.dict: dict = fetch_config()
        LOG.debug(f"---> Config: {self.dict['settings']}")
        self.allergens: list = self.dict['settings']["lookupTable"]["allergens"]
        self.valid_species: list = self.dict['settings']["lookupTable"]["species"]
        self.positive: list = self.dict['settings']["lookupTable"]["positive"]
        self.negative: list = self.dict['settings']["lookupTable"]["negative"]

    def is_negated(self, token: object, negative_words: list) -> bool:
        LOG.info("---> Verifying token negativity")
        return token.dep_ == "neg" or token.lemma_.lower() in negative_words

    def is_positive(self, token: object, positive_words: list) -> bool:
        LOG.info("---> Verifying token positivity")
        return token.lemma_.lower() in positive_words

    def phrase_match_gen(self, phrases: list) -> object:
        LOG.info("---> Generating a phrases matcher")
        phrase_matcher: object = PhraseMatcher(nlp.vocab, attr="LOWER")
        phrase_patterns: list = [nlp.make_doc(phrase) for phrase in phrases]
        phrase_matcher.add("ALLERGENS", None, *phrase_patterns)
        return phrase_matcher

    def fit(self, text: str) -> list:
        LOG.debug(f"---> POS: {text}")

        doc: object = nlp(text)

        # Initialize the PhraseMatcher for allergens
        allergen_matcher: object = self.phrase_match_gen(self.allergens)

        # Initialize the PhraseMatcher for species
        species_matcher: object = self.phrase_match_gen(self.valid_species)

        detected_species_allergens: list = []

        # Apply the species matcher to detect species
        species_matches: object = species_matcher(doc)

        species_positions: list = []
        for match_id, start, end in species_matches:
            species_name = doc[start:end].text.lower()
            species_positions.append((start, end, species_name, doc[start].idx, doc[end - 1].idx))

        allergen_matches = allergen_matcher(doc)

        allergen_sentiment_map = {}
        for allergen_match_id, allergen_start, allergen_end in allergen_matches:
            allergen_phrase = doc[allergen_start:allergen_end].text.lower()
            sentiment = "neutral"

            context_range = 3
            context = doc[max(0, allergen_start - context_range):min(len(doc), allergen_end + context_range)]
            is_neg = any(self.is_negated(token, self.negative) for token in context)
            is_pos = any(self.is_positive(token, self.positive) for token in context)

            if is_neg:
                sentiment = "negative"
            elif is_pos:
                sentiment = "positive"

            allergen_sentiment_map[allergen_phrase] = sentiment

        for allergen_phrase, sentiment in allergen_sentiment_map.items():
            closest_species = None
            allergen_start_pos = None

            # Get the allergen start position
            for allergen_match_id, allergen_start, allergen_end in allergen_matches:
                if allergen_phrase == doc[allergen_start:allergen_end].text.lower():
                    allergen_start_pos = doc[allergen_start].idx

            # Find the closest species before the allergen
            for species_start, species_end, species, species_start_idx, species_end_idx in species_positions:
                species_end_pos = species_end_idx  # Get the species' end position

                if species_end_pos < allergen_start_pos:  # Species appears before allergen
                    closest_species = (species, species_start_idx, species_end_idx)
                else:
                    break  # No need to check further species

            if closest_species:
                species_name, species_start_idx, species_end_idx = closest_species
                allergen_start = doc[allergen_start].idx
                allergen_end = doc[allergen_end - 1].idx
                detected_species_allergens.append((species_name, allergen_phrase, sentiment, species_start_idx, species_end_idx, allergen_start, allergen_end))

        return detected_species_allergens
