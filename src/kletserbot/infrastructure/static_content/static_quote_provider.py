class StaticQuoteProvider:
    _QUOTES = (
        "Dienen zit verre - Max Claeys",
        "Koekoek - Max Claeys",
        "Lolzi - Laurens Viaene",
        "@fabian18cm - Fabian Botterman",
        "Ik voel mij niet zo super chill - Kobe Viaene",
        "#Newshoes - Kobe Viaene",
        "Kga nog keer naar den Chapi - Matthieu Carrette",
        "We gaan allemaal olympisch kalm blijven - Boudewijn Carrette",
        "Muttn - Leander Viaene",
        "LVGA, LeanderViaeneGabber - Leander Viaene",
        "Iemand Playstation 4 kopen? - Joachim Slock",
        "Keer dienen Bangbros proberen? - Joachim Slock",
        "Zeeeeeeeeeven - Joachim Slock",
        "Ik ga ffkes een toerke wandelen - Freek De Vrieze",
        "Waarom zijn vegitariërs zo ambetant? - Nancy Quintyn",
        "Ben daar gelijk wel nog fan van, van dienen Dirty Harry - Fabian Botterman",
        "Doen we nog een slaapmutske? - Freek De Vrieze",
        "Slaapmuts der slaapmutsen?! - Freek De Vrieze",
        "Ahhh de Boyzz - Boudewijn Carrette",
        "Gasten, kheb kans op de Tricycle! - Matthieu Carrette",
    )

    def retrieve_quotes(self) -> tuple[str, ...]:
        return self._QUOTES
