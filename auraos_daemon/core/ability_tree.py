"""
Ability tree for AuraOS Autonomous AI Daemon v8
Tracks available abilities and missing capabilities.
"""
import logging

class AbilityTree:
    def __init__(self):
        self.abilities = set()
        self.missing = set()

    def add_ability(self, name):
        self.abilities.add(name)
        if name in self.missing:
            self.missing.remove(name)
        logging.info(f"[AbilityTree] Added ability: {name}")

    def report_missing(self, name):
        if name not in self.abilities:
            self.missing.add(name)
            logging.warning(f"[AbilityTree] Missing ability: {name}")

    def has_ability(self, name):
        return name in self.abilities

    def get_missing(self):
        return list(self.missing)
