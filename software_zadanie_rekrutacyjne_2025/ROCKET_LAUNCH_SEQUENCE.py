''' MÓJ CEL: Chcę, żeby ten skrypt samodzielnie kontrolował rakietę, reagował na odczyty z sensorówi przestrzegał zasady bezpieczeństwa'''
#Otrzymane ciśnienie: 30.0 ONO WGL NIE ROŚNIE, PRZEZ CO FUNKCJA 3 NIE CHCE SIE NIGDY ODPALIĆ, CZY TOK OKEJ?
from communication_library.communication_manager import CommunicationManager, TransportType
from communication_library.tcp_transport import TcpSettings
from communication_library.frame import Frame
from communication_library import ids
from communication_library.exceptions import TransportTimeoutError, TransportError, UnregisteredCallbackError
import time
import sys
import logging

#-----------------------STAŁE--------------------
oxidizer_full=False
fuel_full=False
pressure_good_for_launch=False
MAX_TANKING_TIME=2*60#sec tanking oxidizer
MAX_TANKING_FUEL_TIME=5*60#sec
MAX_SEARCHING_FOR_PRESSURE_FOR_LAUNCH_TIME=5*60#sec
PRESSURE_MIN=28.0
PRESSURE_MAX=32.0
MAX_WAIT_AFTER_APOGEE=10 #sec
logging.basicConfig(filename="rocket.log", 
                    level=logging.INFO, 
                    format="%(asctime)s [%(levelname)s] %(message)s")

cm = CommunicationManager() # tworzę obiekt komunikacji
cm.change_transport_type(TransportType.TCP)#typ połączenia TCP
cm.connect(TcpSettings("127.0.0.1", 3000))#łącze z proxy działającym na porcie 3000

#-------------------------KOD-------------------------------
def on_oxidizer_level(frame:Frame): 
    '''Callback do monitorowania POZIOMU utleniacza'''
    level=frame.payload[0]
    print(f"Pobieram poziom utleniacza z sensora {level}")
    logging.info(f"Pobieram poziom utleniacza z sensora {level}")
    if level >= 100.0: # poziom %
        global oxidizer_full
        oxidizer_full=True        

def check_pressure(frame):
    pressure = frame.payload[0]
    print(f"Ciśnienie: {pressure}")

def tank_oxidizer():
    '''1.Tankowanie utleniacza (oxidizer):
        - Otwórz zawór tankowania utleniacza (oxidizer_intake)
        - Poczekaj aż zbiornik napełni się do 100%
        - Zamknij zawór tankowania utleniacza
        - Ciśnienie utleniacza powinno osiągnąć około 30 bar'''
    global oxidizer_full

    #---------------------Otworz zawor tankowania utleniacza
    oxidizer_open = Frame(ids.BoardID.ROCKET, #destination:  device that the frames is sent to
                           ids.PriorityID.LOW, 
                           ids.ActionID.SERVICE, #typ ramki
                           ids.BoardID.SOFTWARE, #source:       device that the frame is sent from
                           ids.DeviceID.SERVO, #typ urzadzenia
                           1, # nr id urzadzenia
                           ids.DataTypeID.INT16,#typ danych w payloadzie
                           ids.OperationID.SERVO.value.POSITION, #typ danych w payloadzie
                           (0,)#otwarty zawór
                           )
    cm.push(oxidizer_open)
    cm.send()
    print("Oxidizer refueling valve opened.")
    logging.info("Oxidizer refueling valve opened.")

    #----------------------Poczekaj aż zbiornik napełni się do 100%
    oxidizer_level_frame= Frame(ids.BoardID.SOFTWARE, 
                           ids.PriorityID.LOW, 
                           ids.ActionID.FEED, 
                           ids.BoardID.ROCKET, 
                           ids.DeviceID.SENSOR, 
                           1, 
                           ids.DataTypeID.FLOAT,
                           ids.OperationID.SENSOR.value.READ)
    
    print("Start tanking oxidizer...")
    logging.info("Start tanking oxidizer...")
    cm.register_callback(on_oxidizer_level, oxidizer_level_frame)#rejestruj callback: CommunicationManager nasłuchuje ramki przychodzące, gdzy przyjdzie ramka która pasuje do "oxidizer_level_frame" -> wywoła funkcję on_oxidizer_leveli przekaże do niej oxidizer_level_frame
    oxidizer_full=False
    start_time = time.time()
    while not oxidizer_full and time.time() - start_time < MAX_TANKING_TIME:
        try:
            cm.receive()#czekaj na nadejście ramek tych automatycznych FEED, dla wszystkich sensorów
        except TransportTimeoutError: #nie otrzymano ramki
            pass #ignoruj
        except UnregisteredCallbackError as e:  #wysłano ramkę, dla której nie zarejestrowano callbacku
            #print(f"unregistered frame received: {e.frame}")
            pass

    if not oxidizer_full:
        print(f"UWAGA: Czas tankowania utleniacza przekroczył {MAX_TANKING_TIME}")
        logging.error(f"UWAGA: Czas tankowania utleniacza przekroczył {MAX_TANKING_TIME}")
        logging.error("Launch aborted")
        sys.exit("Launch aborted")
    print("Stop tanking oxidizer")
    logging.info("Stop tanking oxidizer")
    
    #----------------------zamknij zawór
    oxidizer_close = Frame(ids.BoardID.ROCKET, #destination:  device that the frames is sent to
                           ids.PriorityID.LOW, 
                           ids.ActionID.SERVICE, 
                           ids.BoardID.SOFTWARE, #source:       device that the frame is sent from
                           ids.DeviceID.SERVO, 
                           1, 
                           ids.DataTypeID.INT16,#typ danych w payloadzie
                           ids.OperationID.SERVO.value.POSITION, #typ danych w payloadzie
                           (100,)#zamknięty zawór
                           )
    cm.push(oxidizer_close)
    cm.send()
    print("Oxidizer refueling valve closed")
    logging.info("Oxidizer refueling valve closed.")
    #---------------------odczyt ciśnienia w zbiorniku utleniacza
    pressure_frame = Frame(ids.BoardID.SOFTWARE, 
                            ids.PriorityID.LOW, 
                            ids.ActionID.FEED, 
                            ids.BoardID.ROCKET, 
                            ids.DeviceID.SENSOR, 
                            3, 
                            ids.DataTypeID.FLOAT,
                            ids.OperationID.SENSOR.value.READ)
    cm.unregister_callback(oxidizer_level_frame.as_reversed_frame())
    cm.register_callback(check_pressure, pressure_frame)
    cm.push(pressure_frame)
    cm.send()
    pressure = None
    while pressure is None:
        try:
            frame = cm.receive()  
            if frame.device_id == 3 and frame.action == ids.ActionID.FEED: #jest to sensor ciśnienia
                pressure=frame.payload[0]
                if pressure> PRESSURE_MAX or pressure<PRESSURE_MIN:
                    print(f"UWAGA: Ciśnienie utleniacza powinno osiągnąć około 30 bar, a osiąga {pressure:.2f} bar")
                    logging.error(f"ERROR: Launch aborted, ciśnienie utleniacza powinno osiągnąć około 30 bar, a osiąga {pressure:.2f} bar")
                    sys.exit("Launch aborted")
                else:
                    print(f"Ciśnienie utleniacza OK: {pressure:.2f} bar")
                    logging.info(f"Ciśnienie utleniacza OK: {pressure:.2f} bar")
                    break
        except TransportTimeoutError:
            pass
        except UnregisteredCallbackError:
            pass
    cm.unregister_callback(pressure_frame.as_reversed_frame())

#------------------------------------------------------------

def on_fuel_level(frame:Frame): 
    '''Callback do monitorowania POZIOMU paliwa'''
    level=frame.payload[0]
    print(f"Pobieram poziom paliwa z sensora {level}")
    logging.info(f"Pobieram poziom paliwa z sensora {level}")
    if level >= 100.0: # poziom %
        global fuel_full
        fuel_full=True        

def tank_fuel():
    '''2.Tankowanie paliwa (fuel):
    - Otwórz zawór tankowania paliwa (fuel_intake)
    - Poczekaj aż zbiornik napełni się do 100%
    - Zamknij zawór tankowania paliwa'''
    global oxidizer_full, fuel_full

    #---------------------Warunek tankowania paliwa
    if oxidizer_full==False:# Otwarcie zaworu paliwa (fuel_intake) przed napełnieniem zbiornika utleniacza=>WYBUCH
        print("ATTENTION: You are trying to open the fuel intake before filling the tank with oxidizer, which may cause an explosion.")
        logging.error("ATTENTION: You are trying to open the fuel intake before filling the tank with oxidizer, which may cause an explosion.")
        sys.exit()

    #---------------------Otworz zawor tankowania utleniacza

    fuel_open = Frame(ids.BoardID.ROCKET, #destination:  device that the frames is sent to
                        ids.PriorityID.LOW, 
                        ids.ActionID.SERVICE, #typ ramki
                        ids.BoardID.SOFTWARE, #source:       device that the frame is sent from
                        ids.DeviceID.SERVO, #typ urzadzenia
                        0, # nr id urzadzenia
                        ids.DataTypeID.INT16,#typ danych w payloadzie
                        ids.OperationID.SERVO.value.POSITION, #typ danych w payloadzie
                        (0,)#otwarty zawór
                        )
    cm.push(fuel_open)
    cm.send()
    print("Fuel refueling valve opened.")
    logging.info("Fuel refueling valve opened.")

    #----------------------Poczekaj aż zbiornik napełni się do 100%

    fuel_level_frame= Frame(ids.BoardID.SOFTWARE, 
                           ids.PriorityID.LOW, 
                           ids.ActionID.FEED, 
                           ids.BoardID.ROCKET, 
                           ids.DeviceID.SENSOR, 
                           0, 
                           ids.DataTypeID.FLOAT,
                           ids.OperationID.SENSOR.value.READ)
    
    print("Start tanking fuel...")
    logging.info("Start tanking fuel...")
    cm.register_callback(on_fuel_level, fuel_level_frame)#rejestruj callback: CommunicationManager nasłuchuje ramki przychodzące, gdzy przyjdzie ramka która pasuje do "oxidizer_level_frame" -> wywoła funkcję on_oxidizer_leveli przekaże do niej oxidizer_level_frame
    fuel_full=False
    start_time = time.time()
    while not fuel_full and time.time() - start_time < MAX_TANKING_FUEL_TIME:
        try:
            cm.receive()#czekaj na nadejście ramek tych automatycznych FEED, dla wszystkich sensorów
        except TransportTimeoutError: #nie otrzymano ramki
            pass #ignoruj
        except UnregisteredCallbackError as e:  #wysłano ramkę, dla której nie zarejestrowano callbacku
            #print(f"unregistered frame received: {e.frame}")
            pass 

    if not fuel_full:
        print(f"UWAGA: Czas tankowania paliwa przekroczył {MAX_TANKING_FUEL_TIME}")
        logging.error(f"ERROR: Launch aborted: Czas tankowania paliwa przekroczył {MAX_TANKING_FUEL_TIME}")
        sys.exit("Launch aborted")
    print("Stop tanking fuel")
    logging.info("Stop tanking fuel")
    
    #----------------------zamknij zawór
    fuel_close = Frame(ids.BoardID.ROCKET, #destination:  device that the frames is sent to
                           ids.PriorityID.LOW, 
                           ids.ActionID.SERVICE, 
                           ids.BoardID.SOFTWARE, #source:       device that the frame is sent from
                           ids.DeviceID.SERVO, 
                           0, 
                           ids.DataTypeID.INT16,#typ danych w payloadzie
                           ids.OperationID.SERVO.value.POSITION, #typ danych w payloadzie
                           (100,)#zamknięty zawór
                           )
    cm.push(fuel_close)
    cm.send()
    print("Fuel refueling valve closed")
    logging.info("Fuel refueling valve closed.")
    cm.unregister_callback(fuel_level_frame.as_reversed_frame())
#-------------------------------------------------------------

def on_oxidizer_pressure(frame:Frame):
    global pressure_good_for_launch
    pressure=frame.payload[0]
    print(f"Otrzymane ciśnienie zbiornika utleniacza: {pressure}")
    if pressure>=55 and pressure<=65:
        pressure_good_for_launch=True
        print("Pressure is good for start.")
        logging.info("Pressure is good for start.")
    elif pressure>90:
        print("ATTENTION: Too much oxidizer pressure, caused by too long heating")
        logging.error("ATTENTION: Too much oxidizer pressure, caused by too long heating")
        sys.exit("Launch aborted:too much oxidizer pressure")

def heat_oxidizer():
    '''3. Podgrzewanie utleniacza:
    - Włącz grzałkę utleniacza (oxidizer_heater)
    - Monitoruj ciśnienie - zakres ciśnienia w jakim należy wykonać zapłon to 55-65 bar'''
    global pressure_good_for_launch
    #--------------------Włącz grzałkę-----------------
    heater_open=Frame(ids.BoardID.ROCKET, #destination:  device that the frames is sent to
                           ids.PriorityID.LOW, 
                           ids.ActionID.SERVICE, #typ ramki
                           ids.BoardID.SOFTWARE, #source:       device that the frame is sent from
                           ids.DeviceID.RELAY, #typ urzadzenia
                           0, # nr id urzadzenia
                           ids.DataTypeID.NO_DATA,#typ danych w payloadzie
                           ids.OperationID.SERVO.value.OPEN)
    cm.push(heater_open)
    cm.send()
    print("Oxidizer heater valve opened.")
    logging.info("Oxidizer heater valve opened.")

    #---------------------Monitorowanie ciśnienia potrzebnego do zapłonu
    oxidizer_pressure_frame= Frame(ids.BoardID.SOFTWARE, #dokąd
                           ids.PriorityID.LOW, 
                           ids.ActionID.FEED, 
                           ids.BoardID.ROCKET, #skąd
                           ids.DeviceID.SENSOR, 
                           3, 
                           ids.DataTypeID.FLOAT,
                           ids.OperationID.SENSOR.value.READ)
    
    print("Start monitoring pressure for launch...")
    logging.info("Start monitoring pressure for launch...")
    cm.register_callback(on_oxidizer_pressure, oxidizer_pressure_frame)#rejestruj callback: CommunicationManager nasłuchuje ramki przychodzące, gdzy przyjdzie ramka która pasuje do "oxidizer_level_frame" -> wywoła funkcję on_oxidizer_pressure przekaże do niej oxidizer_pressure_level
    
    pressure_good_for_launch=False
    start_time = time.time()
    while not pressure_good_for_launch and time.time() - start_time < MAX_SEARCHING_FOR_PRESSURE_FOR_LAUNCH_TIME:
        try:
            cm.receive()#czekaj na nadejście ramek tych automatycznych FEED, dla wszystkich sensorów
        except TransportTimeoutError: #nie otrzymano ramki
            pass #ignoruj
        except UnregisteredCallbackError as e:  #wysłano ramkę, dla której nie zarejestrowano callbacku
            #print(f"unregistered frame received: {e.frame}")
            pass
    
    cm.unregister_callback(oxidizer_pressure_frame.as_reversed_frame())
    if not pressure_good_for_launch:
        print("Launch aborted")
        logging.error("Launch aborted")
        sys.exit("Launch aborted")
    print("Stop monitoring pressure")
    logging.info("Stop monitoring pressure")

#-------------------------------------------------------------

def ignition_sequence():
    '''4. Sekwencja zapłonu:
    - Otwórz zawór główny paliwa (fuel_main)
    - Otwórz zawór główny utleniacza (oxidizer_main)
    - Włącz igniter (nie później niż 1 s po otwarciu zaworów)
    - Rakieta startuje'''
    print("Ignition sequence start.")
    logging.info("Inition sequence start.")
    
    #--------------------Otwórz zawór główny paliwa (fuel_main)
    open_fuel_main=Frame( ids.BoardID.ROCKET, #sent to
                        ids.PriorityID.LOW,
                        ids.ActionID.SERVICE,
                        ids.BoardID.SOFTWARE,
                        ids.DeviceID.SERVO,
                        2,
                        ids.DataTypeID.INT16,
                        ids.OperationID.SERVO.value.POSITION,
                        (0,))
    cm.push(open_fuel_main)
    cm.send()
    time_open_fuel=time.time()
    print(f"Main fuel valve opened at {time_open_fuel:.2f}")
    logging.info(f"Main fuel valve opened at {time_open_fuel:.2f}")

    #--------------------Otwórz zawór główny utleniacza (oxidizer_main)
    open_oxidizer_main=Frame(ids.BoardID.ROCKET,
                            ids.PriorityID.LOW,
                            ids.ActionID.SERVICE,
                            ids.BoardID.SOFTWARE,
                            ids.DeviceID.SERVO,
                            3,
                            ids.DataTypeID.INT16,
                            ids.OperationID.SERVO.value.POSITION,
                            (0,))
    cm.push(open_oxidizer_main)
    cm.send()
    time_open_oxidizer=time.time()
    print(f"Main oxidizer valve open at {time_open_oxidizer:.2f}")
    logging.info(f"Main oxidizer valve open at {time_open_oxidizer:.2f}")

    #--------------------Zawory muszą być otwarte w odstępie <= 1 s
    if time_open_oxidizer-time_open_fuel<=1:
        print(f"Main valves opened safely within: {time_open_oxidizer-time_open_fuel:.2f}")
        logging.info(f"Main valves opened safely within: {time_open_oxidizer-time_open_fuel:.2f}")
    else:
        print(f"ERROR: Delay between valves opening = {time_open_oxidizer-time_open_fuel:.2f}s (>1s). Explosion risk!")
        logging.error(f"Delay between valves opening = {time_open_oxidizer-time_open_fuel:.2f}s. Explosion risk! Launch aborted.")
        sys.exit("Launch aborted due to unsafe valve timing.")
    
    #--------------------Włącz igniter (nie później niż 1 s po otwarciu zaworów)
    igniter_on=Frame(ids.BoardID.ROCKET,
                    ids.PriorityID.LOW,
                    ids.ActionID.SERVICE,
                    ids.BoardID.SOFTWARE,
                    ids.DeviceID.RELAY,
                    1,
                    ids.DataTypeID.NO_DATA, # nie wysyłamy danych (relay tylko stan)
                    ids.OperationID.RELAY.value.OPEN# komenda: włącz przekaźnik (zapłon)
                )
    cm.push(igniter_on)
    cm.send()
    time_igniter_on=time.time()
    print("Igniter ON")
    logging.info("Igniter ON")

    #-------------------- Sprawdź czas między otwarciem zaworów a igniterem
    if time_igniter_on-time_open_oxidizer<=1:
        print("IGNITION SUCCESSFUL: LIFTOFF!")
        print("LOT RAKIETY")
        logging.info("IGNITION SUCCESSFUL: LIFTOFF!")
        logging.info("LOT RAKIETY")
    else:
        print(f"ERROR: IGNITION FAIL. Delay between valves opening and switching on igniter = {time_open_oxidizer-time_open_fuel:.2f}s (>1s). Explosion risk!")
        logging.error(f"ERROR: IGNITION FAIL. Delay between valves opening and switching on igniter ={time_open_oxidizer-time_open_fuel:.2f}s. Explosion risk! Launch aborted.")
        sys.exit("IGNITION FAIL!:the combustion chamber flooded due to too much time between valves opening and switching on igniter")

#-------------------------------------------------------------
#flags
apogee_reached=False
apogee_time=0
parachute_open=False
#global
last_altitude=0
last_altitude_time=0
aproximate_velocity=0

def on_altitude(frame:Frame):
    global apogee_reached, apogee_time
    global last_altitude,altitude
    
    altitude=frame.payload[0]
    altitude_time=time.time()
    if(altitude<=last_altitude and not apogee_reached):#wysokość nie rośnie
        apogee_time=time.time()
        apogee_reached=True
        print(f"The APOGEE has been reached")
        logging.error("The APOGEE has been reached")
    
    if apogee_reached:
        aproximate_velocity=abs(last_altitude-altitude)/abs(last_altitude_time-altitude_time)
    last_altitude=altitude
    last_altitude_time=altitude_time

def landing():
    '''6. Lądowanie:
    - Wyrzuć spadochron (parachute), gdy takie warunki spełnione:
        *Otwieramy go max 10 sec po osiągnięciu apogee, ale nie przed osiągnięciem apogee
        *gdy silnik nie pracuje
        *gdy prędkość mniejsza niż 30 m/s (spadochron się zerwie)
    - Poczekaj aż rakieta bezpiecznie wyląduje
        Uwagi:
    - Ciśnienie utleniacza w zakresie 55-65 bar zapewnia optymalny ciąg (100%)
    - Ciśnienie utleniacza w zakresie 40-55 zapewnia zmniejszony ciąg (50-100%)'''
    global apogee_reached,last_altitude, apogee_time
    #--------------------------Znalezienie momentu w którym rakieta jest w apogeum
    altitude_frame=Frame(
                    ids.BoardID.SOFTWARE,
                    ids.PriorityID.LOW,
                    ids.ActionID.FEED,
                    ids.BoardID.ROCKET,
                    ids.DeviceID.SENSOR,
                    2,
                    ids.DataTypeID.FLOAT,
                    ids.OperationID.SENSOR.value.READ)

    cm.register_callback(on_altitude, altitude_frame)

    while not apogee_reached:
        try:
            cm.receive()
        except TransportTimeoutError: #nie otrzymano ramki
            pass #ignoruj
        except UnregisteredCallbackError as e:  #wysłano ramkę, dla której nie zarejestrowano callbacku
            #print(f"unregistered frame received: {e.frame}")
            pass
    
    if not apogee_reached:
        print("Nie osiągnięto apogeum")
        logging.error("Nie osiągnięto apogeum")
    
    #---------------------------Rakieta spada-> otwieramy PARACHUTE
    # gdy silnik nie pracuje
    # gdy prędkość mniejsza niż 30 
    while time.time()-apogee_time<=MAX_WAIT_AFTER_APOGEE :  #Spadochron otwieramy w max 10 sec po apogee
        try:
            cm.recive()#odbieranie jednej ramki danych od symulatora
            if aproximate_velocity<30:
                parachute_open_frame=Frame(
                                    ids.BoardID.ROCKET,
                                    ids.PriorityID.LOW,
                                    ids.ActionID.SERVICE,
                                    ids.DeviceID.RELAY,
                                    2,
                                    ids.DataTypeID.FLOAT,
                                    ids.OperationID.RELAY.value.OPEN)
                cm.push(parachute_open_frame)
                cm.send()
                print("Spadachron otwaorozny.")
                logging.info("parachute open")
                parachute_open=True
                break
        except TransportTimeoutError:
            pass
        except UnregisteredCallbackError as e:
            print(f"Unregistered frame received: {e.frame}")

    if not parachute_open:
        print("ERROR: Spadochron nie otworzył się. CRASH LANDING!")
        logging.error("ERROR: Spadochron nie otworzył się. CRASH LANDING!")
        sys.exit("CRASH LANDING!")

    cm.unregister_callback(altitude_frame.as_reversed_frame())





if __name__ == "__main__":
    tank_oxidizer()
    tank_fuel()
    heat_oxidizer()
    ignition_sequence()
    '''5. Faza lotu:
    - Rakieta będzie spalać paliwo i nabierać wysokości
    - Po wypaleniu paliwa rakieta będzie lecieć jeszcze jakiś czas wytracając prędkość
    - Po osiągnięciu apogeum (najwyższego punktu) rakieta zacznie opadać'''
    #landing()
