# Zadanie-rekrutacyjne-AGH-Space-Systems-Rocket-Software-jesien-2025:   Automatyczny start i lądowanie rakiety  
## Opis projektu
Program **automatycznie steruje sekwencją startu, lotu i lądowania rakiety**.
Komunikuje się z systemem pokładowym rakiety przez sieć TCP```(tcp_proxy.py)```, odczytuje dane z czujników (poziomy paliwa, ciśnienie, wysokość)  

Steruje zaworami, przekaźnikami oraz zapłonem, reagując w czasie rzeczywistym na zmiany parametrów rakiety.  

W przypadku nieprawidłowości (np. zbyt wysokie ciśnienie lub nieprawidłowa kolejność otwarcia zaworów) program przerywa misję.
Wszystkie działania i zdarzenia są logowane w pliku rocket.log w celu bezpieczeństwa i analizy.

## Uruchamianie  
1. Uruchom serwer proxy: ```python tcp_proxy.py```
2. Uruchom symulator rakiety:```python tcp_simulator.py --verbose```
3. Uruchom kontroler rakiety:```python rocket_controller.py```

## Działanie programu    
Program łączy się z serwerem proxy i wysyła ramki do symulatora zgodnie z kolejnością procedury startu.
Monitoruje wartości sensorów w czasie rzeczywistym.
Loguje wszystkie operacje do pliku ```rocket.log```.
W razie błędów (np. zbyt wysokie ciśnienie lub złe otwarcie zaworów) wyświetla komunikat ostrzegawczy.

Program z **sukcesem** przeprowadza całą sekwencę startu rakiety, lotu oraz lądowania:
<img width="725" height="417" alt="image" src="https://github.com/user-attachments/assets/a33c657e-a069-4fb2-9407-242987807c74" />

## Planowane rozszerzenia kodu:   
- Dodanie testów jednostkowych
- Optymalizacja kodu
- Pomiar parametrów w locie  

Dodatkowo:
- Interfejs graficzny GUI w NiceGUI
- Automatyczne powiadomienia o ryzyku awarii


