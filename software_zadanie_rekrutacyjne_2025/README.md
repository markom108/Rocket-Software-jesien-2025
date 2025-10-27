# Zadanie rekrutacyjne, AGH Space Systems Rocket Software jesień 2025

Gratulujemy w przejściu do kolejnego etapu rekrutacji do naszego koła!
Jako materiały do zadania przygotowaliśmy dla Ciebie uproszczony wycinek naszego stack'u komunikacyjnego dostępny w folderze ```communication_library```.
biblioteka zawiera implementacje ramki komunikacyjnej, kodowania/dekodowania, klasy zarządzającej komunikacją, numerów identyfikacyjnych specyficznych dla protokołu oraz klasy odpowiadającej za komunikację TCP w infrastrukturze.

Dodatkowo zawarliśmy tutaj prosty symulator rakiety ```tcp_simulator.py``` oraz narzędzie do połączenia się z nim ```tcp_proxy.py```.
Dokumentacja opisująca jak z nich korzystać jest dostępna poniżej pod treścią zadania.

## Zadanie

Celem zadania jest skorzystanie z dostępnych materiałów i przygotowanie kodu wchodzącego w interakcję z symulatorem rakiety. Zadanie nie posiada ścisłego punktu końcowego, to co w nim zrobisz zależy od Ciebie ;) 
Symulator pozwala na wysyłanie poleceń sterujących do rakiety oraz odbierania potwierdzeń operacji i odczytów z sensorów dostępnych na pokładzie. Za pomocą symulatora można przeprowadzić lot rakiety począwszy od tankowania aż po lądowanie na spadochronie. Konkrety odnośnie działania symulatora są dostępne poniżej w dokumentacji.

Istnieje wiele podejść do tego zadania, Twój kod nie musi nawet wykonywać z sukcesem lotu rakiety!.
Jeśli wizualizacja danych jest Twoją mocną stroną to możesz skupić się na stworzeniu aplikacji przedstawiającej stan rakiety w czytelny sposób.
Preferujesz skupić się na locie? Bez problemu, możesz stworzyć aplikację przede wszystkim skupioną na sterowaniu, zawierającą na przykład blokady przed wykonaniem niepoprawnej operacji w danym momencie startu lub całkowicie automatyzującą start i jedynie wyświetlającą progress wykonywanych operacji.
A może wolisz przerobić którąś z części ```communication_library``` na Rust'a, podpiąć ją do pythona i wykonać resztę lotu prostym skryptem? To również możliwe!

Zadanie pozostawia Ci dowolność w wykonaniu tego co zechcesz, chętnie zobaczymy co zdecydujesz się nam przedstawić :)
Jeśli zabrakło by Ci czasu na dokończenie zadania to bez obaw, śmiało możecie przysyłać zadania nawet jeśli są work in progress albo nie wszystko działa.
W przypadku jeśli zastanawiasz się z jakiego UI frameworka skorzystać to polecamy NiceGUI (https://nicegui.io/), z którego również sami korzystamy. Jeśli jednak wolisz użyć czegoś innego to też nie ma problemu.

W razie pytań prosimy kontaktować się na adres mailowy z którego otrzymano informację o przejściu do drugiego etapu, lub zrobić issue w tym repozytorium z pytaniem (szczególnie preferowane jeśli pytanie odnosi się do kodu).

Zadania prosimy wrzucać na publiczne repozytorium i przesłanie nam linku do niego na adres mailowy z którego otrzymano informację o przejściu do drugiego etapu. Jeśli nie chcesz wrzucać kodu na publiczne repozytorium to również możesz nam przesłać zip z kodem, chociaż repozytoria bardzo ułatwiłyby nam weryfikację zadań.

## Dokumentacja

### Setup

Aby skorzystać z repozytorium zinstaluj następujące biblioteki:
```bash
pip install crccheck bitstruct pyyaml
```

Kod symulatora jest zawarty w pliku ```tcp_simulator.py```, po uruchomieniu go z argumentem --help zobaczysz dostępne argumenty startowe.
Domyślne wartości argumentów są w pełni wystarczające do działania.

Aby uruchomić symulator należy uruchomić pierwsze serwer proxy, odpowiedzialny za pośredniczenie w komunikacji między oprogramowaniem kontrolii misji a infrastrukturą sprzętową rakiety. To repozytorium zawiera uproszczoną implementację serwera proxy dostępną w pliku ```tcp_proxy.py```. Możesz ją uruchomić w następujący sposób:
```bash
python tcp_proxy.py
```
Dodatkowe argumenty nie są wymagane ale również możesz uzyskać do nich dostęp za pomocą argumentu --help.

mając uruchomione proxy, możesz uruchomić symulator:
```bash
python tcp_simulator.py
```

Symulator automatycznie połączy się z serwerem proxy, co powinno zostać przez niego wyprintowane.

Plik ```frame_sending_receiving_example.py``` zawiera przykład jak możesz skorzystać z communication_library do zaimplementowania swojego rozwiązania. Są tam przedstawione wszystkie elementy potrzebne do wysłania polecenia do symulatora i odebrania od niego informacji.

### Działanie symulatora

**Disclaimer**:
Symulator skupia się przede wszystkim na zapewnieniu podstawowych funkcjonalności odnośnie obsługi stack'a komunikacyjnego. Działanie rakiety nie zostało zaimplementowane z myślą o poprawności fizycznej, stąd też możliwe że wartości wyświetlane przez niego nie będą mieć pełnego odzwierciedlenia w rzeczywistości. Symulator **nie** przedstawia żadnej z naszych istniejących rakiet, osiągi rakiety przedstawionej w symulatorze są ściśle poglądowe a procedury i obostrzenia z nimi związane wymagane do startu zostaly uproszczone na potrzeby zadania.

#### Podzespoły pokładowe obecne w symulowanej rakiecie:

Serwomechanizmy (servo):
- fuel_intake <-- odpowiedzialny za zawór do tankowania paliwa
- oxidizer_intake <-- odpowiedzialny za zawór do tankowania utleniacza
- fuel_main <-- zawór główny paliwa
- oxidizer_main <-- zawór główny utleniacza

Operacje możliwe do wykonania:
- POSITION <-- ustawienie pozycji serwomechanizmu (0 to pozycja otwarta, 100 to pozycja zamknięta)

Przekaźniki (relay):
- oxidizer_heater <-- sterowanie grzałką utleniacza
- igniter <-- sterowanie zapalnikiem
- parachute <-- sterowanie wyrzutem spadochronu

Operacje możliwe do wykonania:
- OPEN <-- przekaźnik w pozycji przewodzącej
- CLOSE <-- przekaźnik w pozycji nieprzewodzącej

Sensory:
- fuel_level <-- procentowa ilość paliwa w zbiorniku
- oxidizer_level <-- procentowa ilość utleniacza w zbiorniku
- altitude <-- wysokość na jakiej jest rakieta
- oxidizer_pressure <-- ciśnienie utleniacza w jego zbiorniku
- angle <-- kąt pod jakim nachylona jest rakieta (0 stopni to nosecone zwrócony pionowo, 90 stopni to pozycja horyzontalna)

Operacje możliwe do wykonania:
- READ

Przykłady wywołania tych operacji zostały przedstawione w pliku ```frame_sending_receiving_example.py```

Aby określić z jakiego ID urządzenia musisz skorzystać aby wysłać do niego ramkę, skorzystaj z pliku ```simulator_config.yml``` gdzie wylistowane są wszystkie podzespoły obecne w symulatorze.
Numery identyfikacyjne są widoczne w polach "device_id".
Każdy typ urządzenia ma swoją osobną przestrzeń identyfikatorów, co oznacza że identyfikatory urządzeń mogą się pokrywać jeśli dwa urządzenia są różnego typu.


#### Protokół komunikacyjny

Repozytorium zawiera okrojoną wersję protokołu komunikacyjnego z jakiego korzystamy. Konkretne pola jakie znajdują się w ramce protokołu oraz za co odpowiadają możesz zobaczyć w pliku ```communication_library/frame.py```.

Ramki jakie wysyła i odbiera symulator możesz zobaczyć po uruchomieniu go z argumentem ```--verbose```. Będzie on przydatny jeśli symulator nie będzie rozpoznawał ramki jaką do niego wysyłasz.

Ważnym polem w naszej ramce komunikacyjnej jest pole ```action```, odpowiada ono za tym akcji jaki jest podejmowany za pośrednictwem danej ramki.
W tym repozytorium wykorzystujemy tylko akcje: SERVICE, ACK, NACK oraz FEED.

- SERVICE <-- Odpowiada za zlecenie operacji w podzespołach rakiety, z prośbą o potwierdznie czy zostały wykonane pomyślnie lub nie. W sytuacji gdy operacja zostanie wykonana pomyślnie symulator odeśle taką samą ramkę jak do niego wysłaliśmy, tylko z zamienionymi polami destination i source (bo wysyła ją od siebie do nas), oraz z akcją ACK w polu action. W sytuacji gdyby operacja się nie powiodła to zamiast ACK znajdziesz tam operację NACK. W tym zadaniu możesz dokonać lotu rakiety bez weryfikacji ACK'ów, ale doceniamy sprawdzanie czy operacja została zatwierdzona lub odrzucona przez symulator :)

- FEED <-- Odczyt z sensora, bądź informacja diagnostyczna. Ramki z akcją feed są ramkami wysyłanymi przez symulator bez "proszenia" go o to. Symulator wysyła FEED'y co sekundę, możesz jednak zmniejszyć lub zwiększyć interwał z jakim są one wysyłane za pomocą argumentu ```--feed-interval``` w symulatorze.

#### Jak wykonać start rakiety?

Opis ten przedstawia jak wykonać procedurę tankowania i lotu w opisanym w tym repozytorium symulatorze.
Lot rakiety może się nie powieść, prosimy się jednak nie martwić ponieważ możesz próbować tyle razy ile chcesz i nie wpływa to negatywnie na ocene (kod nie zawiera żadnych elemtnów śledzących postępy).

##### Procedura tankowania i startu:

1. **Tankowanie utleniacza (oxidizer)**:
   - Otwórz zawór tankowania utleniacza (oxidizer_intake)
   - Poczekaj aż zbiornik napełni się do 100%
   - Zamknij zawór tankowania utleniacza
   - Ciśnienie utleniacza powinno osiągnąć około 30 bar

2. **Tankowanie paliwa (fuel)**:
   - Otwórz zawór tankowania paliwa (fuel_intake)
   - Poczekaj aż zbiornik napełni się do 100%
   - Zamknij zawór tankowania paliwa

3. **Podgrzewanie utleniacza**:
   - Włącz grzałkę utleniacza (oxidizer_heater)
   - Monitoruj ciśnienie - zakres ciśnienia w jakim należy wykonać zapłon to 55-65 bar

4. **Sekwencja zapłonu**:
   - Otwórz zawór główny paliwa (fuel_main)
   - Otwórz zawór główny utleniacza (oxidizer_main)
   - Otwarcie zaworów należy wykonać w przeciągu maksymalnie jednej sekundy od siebie, inaczej skończy się to wybuchem rakiety.
   - Włącz igniter, uruchomienie ignitera powinno wydarzyć się po otwarciu zaworów ale nie później niż 1 sekundę, inaczej komora spalania zostanie zalana i zapłon się nie powiedzie.
   - Rakieta startuje

5. **Faza lotu**:
   - Rakieta będzie spalać paliwo i nabierać wysokości
   - Po wypaleniu paliwa rakieta będzie lecieć jeszcze jakiś czas wytracając prędkość
   - Po osiągnięciu apogeum (najwyższego punktu) rakieta zacznie opadać

6. **Lądowanie**:
   - Wyrzuć spadochron (parachute) w odpowiednim momencie po apogeum
   - Poczekaj aż rakieta bezpiecznie wyląduje
   - wyrzucenie spadochronu przy prędkości większej niż 30 m/s spowoduje jego urwanie.

##### Warunki prowadzące do eksplozji/awarii:

**Podczas tankowania:**
- Otwarcie zaworu paliwa (fuel_intake) przed napełnieniem zbiornika utleniacza
- Przekroczenie ciśnienia utleniacza powyżej 90 bar (zbyt długie podgrzewanie)

**Podczas sekwencji zapłonu:**
- Otwarcie zaworów głównych z różnicą czasu większą niż 1 sekunda przy włączonym zapłonniku
- Włączenie zapłonnika z opóźnieniem większym niż 1 sekunda po otwarciu zaworów głównych
- Włączenie zapłonnika przed otwarciem zaworów głównych
- Ciśnienie utleniacza poniżej 40 bar przy zapłonie (silnik się nie zapali)
- Ciśnienie utleniacza powyżej 65 bar przy zapłonie (eksplozja silnika)
- Pozostawienie otwartych zaworów tankowania (fuel_intake lub oxidizer_intake) podczas zapłonu

**Podczas lotu:**
- Otwarcie spadochronu przy pracującym silniku
- Otwarcie spadochronu przy prędkości przekraczającej 30 m/s (spadochron się zerwie)
- Nieotwarcie spadochronu w ciągu 10 sekund od osiągnięcia apogeum (lądowanie bez spadochronu)

**Uwagi:**
- Ciśnienie utleniacza w zakresie 55-65 bar zapewnia optymalny ciąg (100%)
- Ciśnienie utleniacza w zakresie 40-55 zapewnia zmniejszony ciąg (50-100%)
- Symulator wyświetla komunikaty o błędach i aktualnym stanie rakiety
- Argument `--verbose` przy uruchomieniu symulatora pozwala śledzić wszystkie wysyłane i odbierane ramki
