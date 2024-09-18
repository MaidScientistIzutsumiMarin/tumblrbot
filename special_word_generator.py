import json

# this program should be pretty self explainatory. have fun with these defaults.

special_words = {
    'noun': [
        "TIGERMAN",
        "TIGERMANHOOD",
        "TIGERMANLINESS",
        "TIGERMANIZATION",
        "dr jekyll and mr hyde",
        "dr jekyll and mr hydehood",
        "dr jekyll and mr hydelikeness",
        "dr jekyll and mr hyde-ization",
        "mummy",
        "mummy",
        "mummy",
        "MUMMY",
        "MUMMY",
        ],
    'verb': [
        "TIGERMANNED",
        "TIGERMANNING",
        "TIGERMANIZED",
        "dr jekyll and mr hyde-ed",
        "dr jekyll and mr hyde-ing",
        "dr jekyll and mr hyde-ized",
        ],
    'adjective': [
        "TIGERMANLIKE",
        "TIGERMANISH",
        "TIGERMANLY",
        "TIGERMANESQUE",
        "TIGERMANIC",
        "TIGERMANIAN",
        "TIGERMAN-LESS",
        "TIGERMANFUL",
        "dr jekyll and mr hyde-like",
        "dr jekyll and mr hyde-ish",
        "dr jekyll and mr hyde-ly",
        "dr jekyll and mr hyde-esque",
        "dr jekyll and mr hydeic",
        "dr jekyll and mr hydean",
        "dr jekyll and mr hydeful",
        "dr jekyll and mr hyde-less",
        ],
}

with open('special_words.json', 'w') as file:
    json.dump(special_words, file, indent=4)
