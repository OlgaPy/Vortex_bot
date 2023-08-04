from typing import Iterable


def plural_ru(number: int, word_forms: Iterable[str]) -> str:
    """Returns plural word, given word forms and number.
    
    >>> plural_ru(5, ["пост", "поста", "постов"])
    >>> "постов"
    """
    if number % 100 in (11, 12, 13, 14):
        return word_forms[2]
    if number % 10 == 1:
        return word_forms[0]
    if number % 10 in (2, 3, 4):
        return word_forms[1]
    return word_forms[2]