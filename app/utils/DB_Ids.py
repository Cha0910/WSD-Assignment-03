from .DB_Utils import load_tags_to_memory, load_locations_to_memory

global locations, tags
locations = load_locations_to_memory()
tags = load_tags_to_memory()