"""Lesson content: letters, vowels (niqqud) and example words.

All content is hand-curated here (no external word source) so that every
word is age-appropriate for first grade and carries full, correct niqqud.

To add a word: append (word_with_niqqud, emoji) to the letter's "words" list,
then run generate_audio.py (run.cmd does that automatically).
"""

DAGESH = "ּ"
SHIN_DOT = "ׁ"
SIN_DOT = "ׂ"

# Vowels taught in first grade. "say" builds TTS-friendly text for a
# syllable: a lone consonant+vowel is often misread by TTS engines, so we
# append a silent/mater letter that forces the right sound (בָּ -> "בָּה").
VOWELS = [
    {"id": "kamatz", "mark": "ָ", "name": "קָמַץ", "sound": "a", "say": "{c}ָה"},
    {"id": "patach", "mark": "ַ", "name": "פַּתָּח", "sound": "a", "say": "{c}ַה"},
    {"id": "tsere", "mark": "ֵ", "name": "צֵירֵה", "sound": "e", "say": "{c}ֵה"},
    {"id": "segol", "mark": "ֶ", "name": "סֶגּוֹל", "sound": "e", "say": "{c}ֶה"},
    {"id": "hiriq", "mark": "ִ", "name": "חִירִיק", "sound": "i", "say": "{c}ִי"},
    {"id": "holam", "mark": "ֹ", "name": "חוֹלָם", "sound": "o", "say": "{c}וֹ"},
    {"id": "kubutz", "mark": "ֻ", "name": "קֻבּוּץ", "sound": "u", "say": "{c}וּ"},
]

# Letters whose syllables need special TTS text (ו followed by וֹ/וּ would be
# read as a single vowel, so double the vav).
SAY_OVERRIDES = {
    ("vav", "holam"): "ווֹ",
    ("vav", "kubutz"): "ווּ",
}

LETTERS = [
    {"id": "alef", "char": "א", "name": "אָלֶף", "words": [
        ("אַבָּא", "👨"), ("אִמָּא", "👩"), ("אַרְנָב", "🐇"), ("אֹזֶן", "👂")]},
    {"id": "bet", "char": "ב" + DAGESH, "name": "בֵּית", "words": [
        ("בַּיִת", "🏠"), ("בָּנָנָה", "🍌"), ("בַּלּוֹן", "🎈"), ("בֻּבָּה", "🪆")]},
    {"id": "vet", "char": "ב", "name": "וֵית", "words": [
        ("גְּבִינָה", "🧀"), ("דְּבוֹרָה", "🐝"), ("כֶּבֶשׂ", "🐑"), ("עֲנָבִים", "🍇")]},
    {"id": "gimel", "char": "ג", "name": "גִּימֶל", "words": [
        ("גָּמָל", "🐫"), ("גֶּזֶר", "🥕"), ("גְּלִידָה", "🍦"), ("גִּיטָרָה", "🎸")]},
    {"id": "dalet", "char": "ד", "name": "דָּלֶת", "words": [
        ("דָּג", "🐟"), ("דֹּב", "🐻"), ("דֶּלֶת", "🚪")]},
    {"id": "he", "char": "ה", "name": "הֵא", "words": [
        ("הַר", "⛰️"), ("הִפּוֹפּוֹטָם", "🦛"), ("הֶלִיקוֹפְּטֶר", "🚁")]},
    {"id": "vav", "char": "ו", "name": "וָו", "words": [
        ("וֶרֶד", "🌹"), ("וָפֶל", "🧇"), ("וִיטָמִין", "💊")]},
    {"id": "zayin", "char": "ז", "name": "זַיִן", "words": [
        ("זֶבְּרָה", "🦓"), ("זְאֵב", "🐺"), ("זַיִת", "🫒")]},
    {"id": "het", "char": "ח", "name": "חֵית", "words": [
        ("חָתוּל", "🐱"), ("חֲמוֹר", "🫏"), ("חָלָב", "🥛"), ("חַלָּה", "🍞")]},
    {"id": "tet", "char": "ט", "name": "טֵית", "words": [
        ("טֶלֶפוֹן", "📞"), ("טַוָּס", "🦚"), ("טִיל", "🚀")]},
    {"id": "yod", "char": "י", "name": "יוֹד", "words": [
        ("יָד", "✋"), ("יֶלֶד", "👦"), ("יַלְדָּה", "👧"), ("יָרֵחַ", "🌙")]},
    {"id": "kaf", "char": "כ" + DAGESH, "name": "כַּף", "words": [
        ("כַּדּוּר", "⚽"), ("כֶּלֶב", "🐕"), ("כּוֹבַע", "🎩"), ("כִּסֵּא", "🪑")]},
    {"id": "khaf", "char": "כ", "name": "כָף", "words": [
        ("מְכוֹנִית", "🚗"), ("עַכְבָּר", "🐭"), ("כּוֹכָב", "⭐")]},
    {"id": "lamed", "char": "ל", "name": "לָמֶד", "words": [
        ("לֵב", "❤️"), ("לֶחֶם", "🍞"), ("לִימוֹן", "🍋")]},
    {"id": "mem", "char": "מ", "name": "מֵם", "words": [
        ("מַיִם", "💧"), ("מָטוֹס", "✈️"), ("מֶלֶךְ", "🤴"), ("מְלָפְפוֹן", "🥒")]},
    {"id": "nun", "char": "נ", "name": "נוּן", "words": [
        ("נָחָשׁ", "🐍"), ("נֵר", "🕯️"), ("נְמָלָה", "🐜"), ("נַעַל", "👟")]},
    {"id": "samekh", "char": "ס", "name": "סָמֶךְ", "words": [
        ("סוּס", "🐴"), ("סֵפֶר", "📖"), ("סַבָּא", "👴"), ("סַבְתָּא", "👵")]},
    {"id": "ayin", "char": "ע", "name": "עַיִן", "words": [
        ("עֵץ", "🌳"), ("עוּגָה", "🎂"), ("עַיִן", "👁️"), ("עָנָן", "☁️")]},
    {"id": "pe", "char": "פ" + DAGESH, "name": "פֵּא", "words": [
        ("פִּיל", "🐘"), ("פֶּרַח", "🌸"), ("פָּרָה", "🐄"), ("פִּיצָה", "🍕")]},
    {"id": "fe", "char": "פ", "name": "פֵא", "words": [
        ("צְפַרְדֵּעַ", "🐸"), ("עֲפִיפוֹן", "🪁"), ("שׁוֹפָר", "📯")]},
    {"id": "tsadi", "char": "צ", "name": "צַדִי", "words": [
        ("צָב", "🐢"), ("צִפּוֹר", "🐦"), ("צֶבַע", "🎨"), ("צַלַּחַת", "🍽️")]},
    {"id": "qof", "char": "ק", "name": "קוֹף", "words": [
        ("קוֹף", "🐒"), ("קֶשֶׁת", "🌈"), ("קִיפּוֹד", "🦔"), ("קַרְנַף", "🦏")]},
    {"id": "resh", "char": "ר", "name": "רֵישׁ", "words": [
        ("רַכֶּבֶת", "🚂"), ("רֶגֶל", "🦵"), ("רוֹבּוֹט", "🤖")]},
    {"id": "shin", "char": "ש" + SHIN_DOT, "name": "שִׁין", "words": [
        ("שֶׁמֶשׁ", "☀️"), ("שָׁעוֹן", "⌚"), ("שׁוּעָל", "🦊"), ("שַׁבְּלוּל", "🐌")]},
    {"id": "sin", "char": "ש" + SIN_DOT, "name": "שִׂין", "words": [
        ("שִׂמְלָה", "👗"), ("שָׂפָם", "🥸"), ("שָׂמֵחַ", "😀")]},
    {"id": "tav", "char": "ת", "name": "תָּו", "words": [
        ("תַּפּוּחַ", "🍎"), ("תּוּת", "🍓"), ("תַּרְנְגוֹל", "🐓"), ("תִּינוֹק", "👶")]},
]


def syllable_say(letter, vowel):
    override = SAY_OVERRIDES.get((letter["id"], vowel["id"]))
    return override or vowel["say"].format(c=letter["char"])


def audio_items():
    """Every clip the app needs: (relative_path, text_to_speak, kind)."""
    items = []
    for letter in LETTERS:
        items.append((f"names/{letter['id']}.mp3", letter["name"], "name"))
        for vowel in VOWELS:
            items.append((f"syllables/{letter['id']}_{vowel['id']}.mp3",
                          syllable_say(letter, vowel), "syllable"))
        for i, (word, _emoji) in enumerate(letter["words"]):
            items.append((f"words/{letter['id']}_{i}.mp3", word, "word"))
    return items
