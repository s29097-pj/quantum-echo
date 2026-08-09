# Quantum Echo
Projekt gry w pygame na przedmiot symulacje i gry decyzyjne

## Kluczowe Cechy

*   **Innowacyjna rozgrywka** oparta na mechanice Echa Czasowego i Kwantowej Zamiany.
*   **Poziomy zaprojektowane** jako złożone zagadki logiczno-zręcznościowe.
*   **Platformy czasowe**, które cyklicznie zmieniają swój stan, wymuszając idealne zgranie w czasie.
*   **System power-upów**: podwójny skok i tarcza nietykalności, które można wykorzystać strategicznie.
*   **Klucze i zamknięte wyjścia** dodające warstwę eksploracji i planowania.
*   **Estetyka Pixel Art** z dynamicznie generowanym, unikalnym tłem dla każdego poziomu.
*   **Efekty cząsteczkowe** i wizualne, które wzbogacają rozgrywkę.
*   **System rankingu** do śledzenia najlepszych wyników.
*   **Tryb treningowy** pozwalający na swobodne ćwiczenie na dowolnym poziomie.
*   **Pełne wsparcie dla dźwięku**: klimatyczna muzyka w menu i efekty dźwiękowe dla kluczowych akcji.

## Głębsze Spojrzenie na Mechaniki

`Quantum Echo` to więcej niż platformówka; to symulator podejmowania decyzji, w którym czas jest Twoim narzędziem, a przeszłość Twoim największym zasobem. Każdy element gry został zaprojektowany, aby zmusić gracza do myślenia w czterech wymiarach.

### 🧠 Myślenie Przyczynowo-Skutkowe: Echo jako Narzędzie

Twoje **Echo** nie jest pasywnym cieniem. To zapis Twoich działań sprzed 10 sekund, który posiada fizyczną obecność w świecie gry. Może ono wchodzić w kolizje z platformami, zbierać przedmioty czy aktywować mechanizmy. Każdy Twój ruch, skok czy postój to inwestycja w przyszłość. Musisz nieustannie zadawać sobie pytania:
*   "Gdzie moje Echo będzie za 10 sekund, jeśli teraz skoczę w to miejsce?"
*   "Czy mogę zostawić Echo na tej platformie czasowej, aby móc się z nim zamienić, gdy platforma zniknie pode mną?"
*   "Jak ustawić się teraz, aby za 10 sekund Echo mogło zebrać klucz, podczas gdy ja będę po drugiej stronie mapy?"

### ⚛️ Kwantowa Zamiana: Sedno Strategii

**Kwantowa Zamiana** to mechanika, która zamienia grę zręcznościową w grę logiczną. Jedno naciśnięcie klawisza `Q` pozwala na natychmiastową zamianę miejscami z Echem, co otwiera nieskończone możliwości taktyczne:
*   **Pokonywanie Pionowych Przeszkód:** Skocz najwyżej jak potrafisz, a następnie poczekaj. Gdy Twoje Echo powtórzy ten skok, zamień się z nim w najwyższym punkcie, aby wylądować na niedostępnej wcześniej półce.
*   **Ucieczka z Pułapek:** Wpadłeś w miejsce bez wyjścia? Jeśli 10 sekund temu byłeś w bezpiecznej pozycji, jeden przycisk może Cię tam przenieść, zostawiając Echo w pułapce.
*   **Manipulacja Obiektami:** Ustaw się na przycisku otwierającym drzwi. Odejdź, a gdy Echo zajmie Twoje miejsce na przycisku, zamień się z nim, aby znaleźć się za otwartymi już drzwiami.

### ⏳ Drugie Życie: Przeszłość Ratuje Przyszłość

Śmierć w `Quantum Echo` nie jest końcem, a lekcją. Po pierwszej porażce na poziomie przejmujesz kontrolę nad swoim Echem. Oznacza to, że dosłownie cofasz się w czasie o 10 sekund, aby przeżyć na nowo swoje ostatnie chwile, ale tym razem z pełną świadomością nadchodzącego zagrożenia. Daje Ci to unikalną szansę na naprawienie błędu i zmianę swojego przeznaczenia.

### 🧩 Świat Pełen Wyzwań Czasoprzestrzennych

Poziomy są zaprojektowane tak, aby w pełni wykorzystać te mechaniki:
*   **Platformy Czasowe:** Znikają i pojawiają się w regularnych cyklach, zmuszając do synchronizacji działań nie tylko z platformą, ale również z opóźnionym ruchem Echa.
*   **Klucze i Zamknięte Wyjścia:** Często klucz do wyjścia znajduje się w miejscu, które staje się niedostępne po jego zebraniu. Gracz musi zaplanować sekwencję ruchów i zamian, aby zarówno zdobyć klucz, jak i zapewnić sobie drogę ucieczki.
*   **Power-upy:** Przedmioty takie jak podwójny skok czy tarcza nietykalności dodają kolejną warstwę do podejmowania decyzji. Czy użyć ich od razu, czy może zostawić je dla Echa, aby mogło pokonać przeszkodę w przyszłości?

## Sterowanie

| Klawisz             | Akcja                  |
| ------------------- | ---------------------- |
| `A` / `D` / `←` / `→` | Ruch w lewo / w prawo  |
| `Spacja`            | Skok / Podwójny skok   |
| `Q`                 | Kwantowa Zamiana z Echem |
| `M`                 | Wycisz / Włącz dźwięk  |
| `ESC`               | Pauza / Powrót do menu |---

## Architektura Kodu (`quantumecho.py`)

Główny plik `quantumecho.py` stanowi serce całej aplikacji i zawiera kompletną logikę gry. Jego architektura opiera się na kilku kluczowych koncepcjach:

### 1. Maszyna Stanów Gry (`GameState`)
Gra jest zorganizowana jako maszyna stanów, co pozwala na czyste oddzielenie logiki różnych ekranów (menu, rozgrywka, pauza, ekran końca poziomu itp.). Enum `GameState` definiuje wszystkie możliwe stany, a główna pętla gry decyduje, którą logikę aktualizować i co rysować na ekranie w zależności od aktywnego stanu.

### 2. Główne Klasy
Projekt jest silnie zorientowany obiektowo, co ułatwia zarządzanie poszczególnymi elementami gry.

*   **Klasy Postaci:**
    *   `Player`: Najważniejsza klasa w grze. Zarządza pozycją, fizyką (grawitacja, kolizje), sterowaniem, power-upami oraz, co kluczowe, przechowuje historię swoich ruchów w kolejce (`deque`). Na podstawie tej historii tworzone i aktualizowane jest **Echo**.

*   **Klasy Elementów Poziomu:**
    *   `Platform`: Podstawowy, statyczny lub poruszający się blok.
    *   `TemporalPlatform`: Platforma czasowa, która cyklicznie zmienia swój stan między materialnym a niematerialnym, wprowadzając element rytmu do rozgrywki.
    *   `Hazard`: Obiekty śmiertelne dla gracza, np. kolce.
    *   `Collectible`: Przedmioty do zebrania (klejnoty, power-upy).
    *   `Key`: Klucz, który gracz musi zebrać, aby odblokować wyjście.
    *   `ExitZone`: Cel poziomu, który aktywuje się po zebraniu wszystkich kluczy.

*   **Klasy Zarządzające i Efektami:**
    *   `Level`: Odpowiada za wczytanie struktury poziomu z pliku `.json` i zainicjowanie wszystkich jego obiektów. Działa jako kontener na wszystkie elementy widoczne w grze.
    *   `LevelBackground`: Generuje unikalne, proceduralne tło w stylu pixel art dla każdego poziomu, włączając w to chmury i gwiazdy z efektem paralaksy.
    *   `ParticleSystem`: Zarządza efektami cząsteczkowymi, takimi jak eksplozje przy zamianie, ślady za postacią czy efekty przy zbieraniu przedmiotów, dodając grze dynamiki.

### 3. Projekt Sterowany Danymi (Data-Driven Design)
Zamiast "hardkodować" poziomy w kodzie, gra wykorzystuje zewnętrzne pliki `.json` do ich definiowania.
*   **Poziomy (`quantumecho_game/levels/*.json`)**: Każdy plik JSON opisuje pozycje i właściwości wszystkich platform, pułapek, przedmiotów, punktu startowego i końcowego. Pozwala to na niezwykle łatwe tworzenie, modyfikowanie i dodawanie nowych poziomów bez dotykania głównej logiki gry.
*   **Ranking (`ranking.json`)**: Najlepsze wyniki są przechowywane w pliku JSON, co pozwala na ich trwałe zapisywanie między sesjami gry.

### 4. Główna Pętla Gry (`main()`)
Funkcja `main()` jest centrum operacyjnym. W pętli `while running:` wykonuje trzy główne zadania w każdej klatce:
1.  **Obsługa Zdarzeń:** Przetwarza wszystkie wejścia od użytkownika (klawiatura, zamknięcie okna).
2.  **Aktualizacja Logiki:** Na podstawie aktualnego `GameState` wywołuje odpowiednie metody `.update()` dla gracza, poziomu i innych aktywnych obiektów. Tutaj odbywa się cała fizyka, sprawdzanie kolizji i zmiana stanów obiektów.
3.  **Renderowanie:** Czyści ekran i wywołuje metody `.draw()` dla wszystkich widocznych elementów, od tła, przez obiekty poziomu, po interfejs użytkownika (HUD).

## Dodatkowa Dokumentacja Projektu

### Analiza Fragmentu Kodu: Wczytywanie Poziomów (Data-Driven Design)

Wybranym fragmentem do analizy jest konstruktor klasy `Level` (`__init__`). Jest to doskonały przykład podejścia **Data-Driven Design** zastosowanego w projekcie.

```python
# W klasie Level
def __init__(self, level_data, level_index):
    # ... inicjalizacja pustych grup i list ...
    self.background = LevelBackground(level_index, SCREEN_WIDTH, SCREEN_HEIGHT)

    # Wczytujemy platformy, przeszkody, przedmioty i strefę wyjścia
    for platform_data in level_data.get('platforms', []):
        self.platforms.add(Platform(**platform_data))
    # ... (podobne pętle dla 'temporal_platforms', 'hazards', 'collectibles', 'keys') ...

    # Wczytujemy strefę wyjścia
    self.start_pos = (level_data['start']['x'], level_data['start']['y'])
    end_data = level_data.get('end', {})
    self.exit_zone = ExitZone(end_data.get('x', 900), end_data.get('y', 100))
    self.exit_zone.locked = bool(self.keys)
```

Analiza:
Analiza: Ten fragment pokazuje, jak kod gry jest oddzielony od danych definiujących poziom. Konstruktor nie tworzy "na sztywno" żadnych obiektów. Zamiast tego iteruje po danych wczytanych z pliku .json i dynamicznie tworzy instancje odpowiednich klas, rozpakowując ich właściwości (**platform_data) jako argumenty. Takie podejście jest niezwykle elastyczne i pozwala na tworzenie nowych poziomów przez edycję plików tekstowych, bez zmiany kodu gry.

### Proceduralne Generowanie Tła
Kolejnym interesującym fragmentem jest konstruktor klasy LevelBackground, który odpowiada za tworzenie unikalnego, dynamicznego tła dla każdego poziomu.

```python
# W klasie LevelBackground
def __init__(self, level_index, width, height):
    random.seed(level_index) # Użycie indeksu poziomu jako ziarna losowości
    
    # Generowanie koloru nieba
    base_blue = random.randint(10, 40)
    self.sky_color = (random.randint(0, 15), random.randint(0, 15), base_blue)

    # Generowanie gwiazd
    self.stars = []
    for _ in range(random.randint(100, 250)):
        self.stars.append({
            'pos': (random.randint(0, width), random.randint(0, height)),
            'size': random.uniform(0.5, 2)
        })

    # Generowanie chmur z różnymi prędkościami dla efektu paralaksy
    self.clouds = []
    for _ in range(random.randint(5, 15)):
        self.clouds.append({
            'rect': pygame.Rect(random.randint(-100, width + 100), random.randint(20, height // 2), 
                                random.randint(100, 300), random.randint(20, 50)),
            'speed': random.uniform(0.1, 0.5)
        })
    random.seed() # Reset ziarna losowości
```

Analiza: Ten kod jest doskonałym przykładem generowania proceduralnego, które nadaje grze wizualnej głębi i różnorodności bez potrzeby tworzenia i wczytywania dziesiątek osobnych plików graficznych.


### Deterministyczna Losowość: 
Kluczowym elementem jest linia **random.seed(level_index)**. Ustawienie "ziarna" generatora liczb losowych na podstawie numeru poziomu sprawia, że dla danego poziomu tło będzie zawsze wyglądać tak samo, ale tła różnych poziomów będą się od siebie różnić.

### Dynamiczny Kolor Nieba: 
Kolor nieba nie jest stały. Jest losowany, co pozwala uzyskać różne odcienie, od głębokiego granatu po jaśniejszy błękit, nadając każdemu poziomowi unikalny nastrój.
Generowanie Gwiazd i Chmur: Pozycje, rozmiary i liczba gwiazd oraz chmur są losowane w określonych przedziałach. Co ważne, chmury otrzymują losową prędkość (speed), co jest później wykorzystywane do stworzenia efektu paralaksy – chmury na różnych planach poruszają się z różną prędkością względem gracza, co tworzy iluzję głębi.

### Efektywność: 
Takie podejście jest niezwykle wydajne. Zamiast wczytywać duże pliki graficzne, gra generuje całą scenerię w ułamku sekundy, używając jedynie kilku prostych operacji matematycznych.
Wyzwania i Napotkane Problemy
Podczas tworzenia projektu napotkano kilka kluczowych wyzwań:


### Implementacja Echa: 
**Największym wyzwaniem** było efektywne przechowywanie i odtwarzanie historii ruchów gracza. Zastosowanie struktury **collections.deque** z ograniczoną długością **(maxlen=ECHO_DELAY_FRAMES)** okazało się idealnym rozwiązaniem, które jest wydajne i automatycznie zarządza "oknem czasowym" 10 sekund.
Fizyka i Kolizje z Platformami Czasowymi: Obsługa kolizji z platformami, które mogą być materialne lub nie, wymagała dynamicznego podejścia. Problem rozwiązano przez stworzenie metody **level.get_solid_platforms()**, która w każdej klatce zwraca grupę tylko tych platform, z którymi można wejść w interakcję. 
Gracz sprawdza kolizje tylko z tą dynamicznie generowaną grupą.

### Zarządzanie Stanami Gry: 
Gra posiada wiele ekranów **(menu, gra, pauza, ranking)**. Początkowo prowadziło to do skomplikowanych warunków **if/else**. 
Wprowadzenie **Enum** dla **GameState** i oparcie głównej pętli na tej maszynie stanów znacząco uprościło kod i uczyniło go bardziej czytelnym


### Kluczowe Elementy Fragmentu
1. **Inicjalizacja Tła:** `self.background = LevelBackground(level_index, SCREEN_WIDTH, SCREEN_HEIGHT)` tworzy unikalne tło dla poziomu, co jest kluczowe dla estetyki gry.
2. **Wczytywanie Elementów:** Pętle `for` iterują przez dane z pliku JSON, tworząc instancje odpowiednich klas (`Platform`, `Hazard`, `Collectible` itp.). Dzięki temu kod jest czysty i łatwy do rozszerzenia.
3. **Zarządzanie Strefą Wyjścia:** `self.exit_zone.locked = bool(self.keys)` ustawia stan strefy wyjścia w zależności od tego, czy gracz zebrał wszystkie klucze, co jest kluczowym elementem rozgrywki.
4. **Elastyczność i Rozszerzalność:** Dzięki temu podejściu, dodanie nowego poziomu polega jedynie na stworzeniu nowego pliku JSON, co znacznie ułatwia rozwój gry i pozwala na łatwe testowanie nowych pomysłów.
5. **Czytelność i Utrzymanie:** Kod jest czytelny i łatwy do zrozumienia, co jest kluczowe w większych projektach. Dzięki zastosowaniu słowników i argumentów słów kluczowych (`**platform_data`), można łatwo dodawać nowe właściwości do platform bez konieczności zmiany logiki wczytywania.
6. **Separacja Logiki i Danych:** Logika gry jest oddzielona od danych poziomu, co pozwala na łatwe modyfikowanie poziomów bez ingerencji w kod gry. To podejście jest kluczowe dla skalowalności projektu.
7. **Wydajność:** Wczytywanie danych z pliku JSON jest efektywne i pozwala na szybkie ładowanie poziomów, co jest istotne dla płynności rozgrywki.

## Wnioski
`Quantum Echo` to projekt, który łączy w sobie innowacyjne mechaniki rozgrywki z solidną architekturą kodu. Dzięki zastosowaniu podejścia Data-Driven Design, gra jest łatwa do rozszerzenia i modyfikacji, co pozwala na szybkie wprowadzanie nowych poziomów i funkcji. Mechaniki takie jak Echo Czasowe i Kwantowa Zamiana wprowadzają unikalne wyzwania, które zmuszają graczy do myślenia w nowy sposób, czyniąc każdą sesję gry świeżą i ekscytującą.
