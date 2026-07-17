1. every type of 1 thing is encompased by a single class representing the core thing
    - the core thing is independent of any attribuites 
        - i.e. ignore adjectives and any descriptor words
        - realy the core of a thing should only be a single word
    - if two things are differnt type of the same core thing, those should all have the same class for the core thing, and any differrnce must be accounted for as different attribuite values
        - i.e. 24 well plate + 12 well plate + 12 well deep plate -> plate class
            - plate.well.name = "12 well deep plate"
            - plate.well.manufacturer =  #could have templates for every plate type and just leave manufactureout
            - plate.well.depth = deep: propagated to nested well classes
            - plate.well.bottom
            - plate.well.volume = then a given volume
                technicaly this is easier then saying its a 12 well well, and more reliable, tho could solve if you knew it was a 12 well well, depthc type and bottom type, but unreliable accorss manufactures
            - where well is the well class
                - which provides well.{bottom; depth; volume;}

        - adjectives are attribuites:
            - "deep" in   12 well deep plate
    - no specific details should be in the schemas


- we have enums for permisable attribute values



- alot of this enum could be derived from developed templates or inventory lists
linkml shoudnt be responsible for specifying any availible media type: growth_medium_enum
that should be a check against a json list of medias from the inventory


notes on: /home/ash/Documents/work/evolver_code/data/known_external_examples/20260213_bio_automation_metadata_schema_v1.0.5.json
    - .types.* should be imported from a seperate resources



usefull components:
aliases

Arrays - critical for defining well ussage


Dynamic Enums !!!!! # what linkml are we using
Starting with LinkML 1.3, enums do not have to be a static hardcoded list; instead they can be dynamic, populated by a query.

This allows the enum to be synced with some upstream source, and avoids hardcoding very long lists where there are a lot of possibilities.

The following example defines an enumeration that selects any subtype of “neuron” from the OBO cell type ontology: