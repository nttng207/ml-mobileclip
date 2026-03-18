"""
Maps dataset species prefixes (latin hyphenated names) to human-readable
group labels used for 3-D visualization colouring.

Any prefix not found in the table falls back to "other".
"""
from __future__ import annotations

# fmt: off
_GROUPS: dict[str, list[str]] = {
    "dog": [
        "canis-lupus-familiaris",
    ],
    "wolf / wild dog": [
        "canis-lupus",
    ],
    "cat": [
        "felis-catus",
    ],
    "big cat": [
        "panthera-leo", "panthera-tigris", "panthera-onca", "panthera-pardus",
        "puma-concolor", "acinonyx-jubatus",
    ],
    "bear": [
        "ursus-arctos-horribilis", "ursus-maritimus", "ailuropoda-melanoleuca",
    ],
    "primate": [
        "homo-sapiens", "gorilla-gorilla", "pongo-abelii", "lemur-catta",
        "tarsius-pumilus",
    ],
    "ungulate": [
        "bos-taurus", "bos-gaurus", "ovis-aries", "ovis-canadensis",
        "equus-caballus", "equus-quagga", "giraffa-camelopardalis",
        "connochaetes-gnou", "taurotragus-oryx", "alces-alces",
        "rusa-unicolor", "tapirus", "hippopotamus-amphibius",
        "ceratotherium-simum", "rhinoceros",
    ],
    "elephant": [
        "loxodonta-africana",
    ],
    "rodent / small mammal": [
        "sciurus-carolinensis", "rattus-rattus", "lepus-americanus",
        "dasypus-novemcinctus", "bradypus-variegatus",
    ],
    "mustelid / procyonid": [
        "enhydra-lutris", "martes-americana", "procyon-lotor",
    ],
    "bat": [
        "desmodus-rotundus", "eidolon-helvum",
    ],
    "red panda / other mammal": [
        "ailurus-fulgens", "okapia-johnstoni", "cryptoprocta-ferox",
    ],
    "bird of prey": [
        "aquila-chrysaetos", "haliaeetus-leucocephalus", "falco-peregrinus",
        "cathartes-aura", "circus-hudsonius", "phoebetria-fusca",
        "vultur-gryphus",
    ],
    "songbird": [
        "cardinalis-cardinalis", "cyanocitta-cristata", "mimus-polyglottos",
        "turdus-migratorius", "poecile-atricapillus", "icterus-galbula",
        "icterus-gularis", "icterus-spurius", "passerina-ciris",
        "thryothorus-ludovicianus", "tyrannus-tyrannus",
    ],
    "woodpecker / cuckoo": [
        "colaptes-auratus", "melanerpes-carolinus", "geococcyx-californianus",
        "crotophaga-sulcirostris",
    ],
    "waterfowl / wading bird": [
        "anas-platyrhynchos", "branta-canadensis", "ardea-herodias",
        "eudocimus-albus", "mergus-serrator", "phoenicopterus-ruber",
    ],
    "seabird / penguin": [
        "aethia-cristatella", "aptenodytes-forsteri", "spheniscus-demersus",
    ],
    "hummingbird": [
        "mellisuga-helenae",
    ],
    "parrot / macaw": [
        "ara-macao", "pavo-cristatus",
    ],
    "other bird": [
        "struthio-camelus",
    ],
    "snake": [
        "agkistrodon-contortrix", "crotalus-atrox", "eunectes-murinus",
        "lampropeltis-triangulum", "malayopython-reticulatus",
        "ophiophagus-hannah", "pantherophis-alleghaniensis",
        "pantherophis-guttatus",
    ],
    "lizard": [
        "correlophus-ciliatus", "heloderma-suspectum", "iguana-iguana",
        "varanus-komodoensis",
    ],
    "crocodilian": [
        "crocodylus-niloticus", "gavialis-gangeticus",
    ],
    "turtle / tortoise": [
        "centrochelys-sulcata", "chelonia-mydas", "chrysemys-picta",
        "dermochelys-coriacea",
    ],
    "frog / amphibian": [
        "agalychnis-callidryas", "dendrobatidae", "phyllobates-terribilis",
        "telmatobufo-bullocki",
    ],
    "shark": [
        "carcharodon-carcharias", "sphyrna-mokarran",
    ],
    "fish": [
        "betta-splendens", "pterois-mombasae", "pterois-volitans",
        "salmo-salar", "coelacanthiformes",
    ],
    "whale / dolphin": [
        "balaenoptera-musculus", "delphinapterus-leucas", "megaptera-novaeangliae",
        "monodon-monoceros", "orcinus-orca", "physeter-macrocephalus",
        "tursiops-truncatus", "inia-geoffrensis",
    ],
    "seal / walrus": [
        "hydrurga-leptonyx", "odobenus-rosmarus",
    ],
    "dugong / manatee": [
        "dugong-dugon",
    ],
    "octopus / squid": [
        "architeuthis-dux", "enteroctopus-dofleini", "hapalochlaena-maculosa",
    ],
    "jellyfish / invertebrate": [
        "physalia-physalis", "codium-fragile", "trilobita",
    ],
    "insect": [
        "apis-mellifera", "ceratitis-capitata", "danaus-plexippus",
        "formicidae", "heterocera", "musca-domestica", "papilio-glaucus",
        "periplaneta-americana",
    ],
    "scorpion / spider": [
        "centruroides-vittatus",
    ],
    "kangaroo / marsupial": [
        "macropus-giganteus", "phascolarctos-cinereus",
    ],
    "platypus": [
        "ornithorhynchus-anatinus",
    ],
    "dinosaur / prehistoric": [
        "ankylosaurus-magniventris", "diplodocus", "iguanodon-bernissartensis",
        "mammuthus-primigeniu", "pteranodon-longiceps", "smilodon-populator",
        "spinosaurus-aegyptiacus", "stegosaurus-stenops", "triceratops-horridus",
        "tyrannosaurus-rex",
    ],
}
# fmt: on

# Invert: prefix → group label
_PREFIX_TO_GROUP: dict[str, str] = {
    prefix: group
    for group, prefixes in _GROUPS.items()
    for prefix in prefixes
}


def get_group(prefix: str) -> str:
    """Return the group label for a species prefix, or 'other'."""
    return _PREFIX_TO_GROUP.get(prefix, "other")
