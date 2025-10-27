''' DESCRIPTION:The program automatically controls the rocket's launch, flight, and landing sequence. It communicates with the onboard rocket system via TCP (tcp_proxy.py) and reads data from sensors (fuel levels, pressure, altitude).
It controls valves, relays, and the igniter, reacting in real-time to changes in the rocket's parameters.
In case of any anomalies (e.g., excessively high pressure or incorrect valve operation sequence), the program aborts the mission. All actions and events are logged in the rocket.log file for safety and analysis purposes.'''
from communication_library.communication_manager import CommunicationManager, TransportType
from communication_library.tcp_transport import TcpSettings
from communication_library.frame import Frame
from communication_library import ids
from communication_library.exceptions import TransportTimeoutError, TransportError, UnregisteredCallbackError
import time
import sys
import logging

#-----------------------CONSTANT--------------------
oxidizer_full=False
fuel_full=False
pressure_good_for_launch=False
MAX_TANKING_TIME=2*60 #sec (tanking oxidizer)
MAX_TANKING_FUEL_TIME=5*60 #sec
MAX_SEARCHING_FOR_PRESSURE_FOR_LAUNCH_TIME=5*60 #sec
PRESSURE_MIN=28.0
PRESSURE_MAX=32.0
MAX_WAIT_AFTER_APOGEE=10 #sec
logging.basicConfig(filename="rocket.log", 
                    level=logging.INFO, 
                    format="%(asctime)s [%(levelname)s] %(message)s")

cm = CommunicationManager() 
cm.change_transport_type(TransportType.TCP) 
cm.connect(TcpSettings("127.0.0.1", 3000))

#---------------------------------------------------------------------------KOD-------------------------------

def on_oxidizer_level(frame:Frame): 
    '''Callback for oxidizer level monitoring'''
    level=frame.payload[0]
    print(f"Pobieram poziom utleniacza z sensora {level}")
    logging.info(f"Reading the oxidizer level from the sensor {level}")
    if level >= 100.0: # level[%]
        global oxidizer_full
        oxidizer_full=True        

def check_pressure(frame):
    pressure = frame.payload[0]
    print(f"Ciśnienie w zbiorniku utleniacza: {pressure}")

def tank_oxidizer():
    '''1.Oxidizer Tanking (oxidizer):
        - Open the oxidizer intake valve (oxidizer_intake)
        - Wait until the tank is filled to 100%
        - Close the oxidizer intake valve
        - The oxidizer pressure should reach approximately 30 bar'''
    global oxidizer_full

    #---------------------Open the oxidizer intake valve
    oxidizer_open = Frame(ids.BoardID.ROCKET, #destination:  device that the frames is sent to
                           ids.PriorityID.LOW, 
                           ids.ActionID.SERVICE, #type of the frame
                           ids.BoardID.SOFTWARE, #source:       device that the frame is sent from
                           ids.DeviceID.SERVO, #type of the device
                           1, # Device ID
                           ids.DataTypeID.INT16,#type of data in payload
                           ids.OperationID.SERVO.value.POSITION, 
                           (0,)#open valve
                           )
    cm.push(oxidizer_open)
    cm.send()
    print("Otwarty zawór tankowania utleniacza.")
    logging.info("Oxidizer refueling valve opened.")

    #----------------------Wait for the oxidizer tank to reach 100% capacity
    oxidizer_level_frame= Frame(ids.BoardID.SOFTWARE, 
                           ids.PriorityID.LOW, 
                           ids.ActionID.FEED, 
                           ids.BoardID.ROCKET, 
                           ids.DeviceID.SENSOR, 
                           1, 
                           ids.DataTypeID.FLOAT,
                           ids.OperationID.SENSOR.value.READ)
    
    print("Rozpocznij tankowanie utleniacza...")
    logging.info("Start tanking oxidizer...")
    cm.register_callback(on_oxidizer_level, oxidizer_level_frame)# When a frame matching oxidizer_level_frame arrives -> execute on_oxidizer_level(oxidizer_level_frame)
    oxidizer_full=False
    start_time = time.time()
    while not oxidizer_full and time.time() - start_time < MAX_TANKING_TIME:
        try:
            cm.receive()# Wait for automatic FEED frames sent by all sensors
        except TransportTimeoutError: # No frame received
            pass 
        except UnregisteredCallbackError as e: # A frame was received for which no callback is registered
            #print(f"unregistered frame received: {e.frame}")
            pass

    if not oxidizer_full:
        print(f"UWAGA: Czas tankowania utleniacza przekroczył {MAX_TANKING_TIME}")
        logging.error(f"WARNING Launch aborted: Oxidizer tanking time exceeded {MAX_TANKING_TIME}")
        sys.exit("Launch aborted")
    print("Zakończ tankowanie utleniacza")
    logging.info("Stop tanking oxidizer")
    
    #-----------------------Close oxidizer valve
    oxidizer_close = Frame(ids.BoardID.ROCKET, #destination
                           ids.PriorityID.LOW, 
                           ids.ActionID.SERVICE, 
                           ids.BoardID.SOFTWARE, #source
                           ids.DeviceID.SERVO, 
                           1, 
                           ids.DataTypeID.INT16,
                           ids.OperationID.SERVO.value.POSITION,
                           (100,)# closed valve
                           )
    cm.push(oxidizer_close)
    cm.send()
    print("Zamknięty zawór tankowania utleniacza.")
    logging.info("Oxidizer refueling valve closed.")
    #---------------------oxidizer tank pressure reading
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
            if frame.device_id == 3 and frame.action == ids.ActionID.FEED: #This is a pressure sensor
                pressure=frame.payload[0]
                if pressure> PRESSURE_MAX or pressure<PRESSURE_MIN:
                    print(f"UWAGA: Ciśnienie utleniacza powinno osiągnąć około 30 bar, a osiąga {pressure:.2f} bar")
                    logging.error(f"WARNING Launch aborted: The oxidizer pressure should reach approximately 30 bar, but it is currently {pressure:.2f} bar")
                    sys.exit("Launch aborted")
                else:
                    print(f"Ciśnienie utleniacza OK: {pressure:.2f} bar")
                    logging.info(f"Oxidizer pressure is within acceptable rang: {pressure:.2f} bar")
                    break
        except TransportTimeoutError:
            pass
        except UnregisteredCallbackError:
            pass
    cm.unregister_callback(pressure_frame.as_reversed_frame())

#------------------------------------------------------------

def on_fuel_level(frame:Frame): 
    '''Callback for monitoring fuel level'''
    level=frame.payload[0]
    print(f"Pobieram poziom paliwa z sensora {level}")
    logging.info(f"Reading the fuel level from the sensor {level}")
    if level >= 100.0: # level[%]
        global fuel_full
        fuel_full=True        

def tank_fuel():
    '''2.Fuel Tanking (fuel):
    - Open the fuel intake valve (fuel_intake)
    - Wait until the tank is filled to 100%
    - Close the fuel intake valve'''
    global oxidizer_full, fuel_full

    #---------------------Fuel tanking condition
    if oxidizer_full==False:
        print("UWAGA: Próbujesz otworzyć fuel intake przed napełnieniem zbiornika utleniaczem, co grozi wybuchem.")
        logging.error("ATTENTION: You are trying to open the fuel intake before filling the tank with oxidizer, which may cause an explosion.")
        sys.exit()

    #---------------------Open the fuel intake valve
    fuel_open = Frame(ids.BoardID.ROCKET, #destination
                        ids.PriorityID.LOW, 
                        ids.ActionID.SERVICE, 
                        ids.BoardID.SOFTWARE, #source
                        ids.DeviceID.SERVO, 
                        0, # id 
                        ids.DataTypeID.INT16,
                        ids.OperationID.SERVO.value.POSITION, 
                        (0,)
                        )
    cm.push(fuel_open)
    cm.send()
    print("Zawór tankowania paliwa otwarty.")
    logging.info("Fuel refueling valve opened.")

    #----------------------Wait until the tank is filled to 100%

    fuel_level_frame= Frame(ids.BoardID.SOFTWARE, 
                           ids.PriorityID.LOW, 
                           ids.ActionID.FEED, 
                           ids.BoardID.ROCKET, 
                           ids.DeviceID.SENSOR, 
                           0, 
                           ids.DataTypeID.FLOAT,
                           ids.OperationID.SENSOR.value.READ)
    
    print("Zaczęto tankowanie paliwa...")
    logging.info("Start tanking fuel...")
    cm.register_callback(on_fuel_level, fuel_level_frame)
    fuel_full=False
    start_time = time.time()
    while not fuel_full and time.time() - start_time < MAX_TANKING_FUEL_TIME:
        try:
            cm.receive()
        except TransportTimeoutError: 
            pass 
        except UnregisteredCallbackError as e:  
            #print(f"unregistered frame received: {e.frame}")
            pass 

    if not fuel_full:
        print(f"UWAGA: Czas tankowania paliwa przekroczył {MAX_TANKING_FUEL_TIME}")
        logging.error(f"ERROR: Launch aborted: Fuel tanking time exceeded {MAX_TANKING_FUEL_TIME}")
        sys.exit("Launch aborted")
    print("Zakończono tankowanie paliwa.")
    logging.info("Stop tanking fuel")
    
    #----------------------Close the valve
    fuel_close = Frame(ids.BoardID.ROCKET, #destination
                           ids.PriorityID.LOW, 
                           ids.ActionID.SERVICE, 
                           ids.BoardID.SOFTWARE, #source
                           ids.DeviceID.SERVO, 
                           0, 
                           ids.DataTypeID.INT16,
                           ids.OperationID.SERVO.value.POSITION, 
                           (100,)
                           )
    cm.push(fuel_close)
    cm.send()
    print("Zawór tankowania paliwa zamknięty")
    logging.info("Fuel refueling valve closed.")
    cm.unregister_callback(fuel_level_frame.as_reversed_frame())
#-------------------------------------------------------------

def on_oxidizer_pressure(frame:Frame):
    global pressure_good_for_launch
    pressure=frame.payload[0]
    print(f"Otrzymane ciśnienie zbiornika utleniacza: {pressure}")
    if pressure>=55 and pressure<=65:
        pressure_good_for_launch=True
        print("Ciśnienie utleniacza mieści się w zakresie optymalnym do startu.")
        logging.info("Oxidizer pressure is within the optimal range for launch.")
    elif pressure>90:
        print("UWAGA: Zbyt duże ciśnienie utleniacza, spowodowane zbyt długim nagrzewaniem")
        logging.error("ATTENTION: Too much oxidizer pressure, caused by too long heating")
        sys.exit("Launch aborted:too much oxidizer pressure")

def heat_oxidizer():
    '''3. Oxidizer Heating:
    - Turn on the oxidizer heater (oxidizer_heater)
    - Monitor the pressure  the pressure range for ignition is 55–65 bar'''
    global pressure_good_for_launch
    #-------------------------------------Turn on the heater
    heater_open=Frame(ids.BoardID.ROCKET, #destination
                           ids.PriorityID.LOW, 
                           ids.ActionID.SERVICE, 
                           ids.BoardID.SOFTWARE, #source
                           ids.DeviceID.RELAY, 
                           0, 
                           ids.DataTypeID.NO_DATA,
                           ids.OperationID.SERVO.value.OPEN)
    cm.push(heater_open)
    cm.send()
    print("Zawór grzałki utleniacza otwarty.")
    logging.info("Oxidizer heater valve opened.")

    #--------------------------------------Monitoring pressure required for ignition
    oxidizer_pressure_frame= Frame(ids.BoardID.SOFTWARE, #dokąd
                           ids.PriorityID.LOW, 
                           ids.ActionID.FEED, 
                           ids.BoardID.ROCKET, #skąd
                           ids.DeviceID.SENSOR, 
                           3, 
                           ids.DataTypeID.FLOAT,
                           ids.OperationID.SENSOR.value.READ)
    
    print("Rozpoczęto monitorowanie ciśnienia przed startem...")
    logging.info("Start monitoring pressure for launch...")
    cm.register_callback(on_oxidizer_pressure, oxidizer_pressure_frame)
    pressure_good_for_launch=False
    start_time = time.time()
    while not pressure_good_for_launch and time.time() - start_time < MAX_SEARCHING_FOR_PRESSURE_FOR_LAUNCH_TIME:
        try:
            cm.receive()
        except TransportTimeoutError: 
            pass 
        except UnregisteredCallbackError as e:  
            #print(f"unregistered frame received: {e.frame}")
            pass
    
    cm.unregister_callback(oxidizer_pressure_frame.as_reversed_frame())
    if not pressure_good_for_launch:
        print("Start przerwany")
        logging.error("Launch aborted")
        sys.exit("Launch aborted")
    print("Przerwano monitorowanie ciśnienia")
    logging.info("Stop monitoring pressure")

#-------------------------------------------------------------

def ignition_sequence():
    '''4. Ignition Sequence:
    - Open the main fuel valve (fuel_main)
    - Open the main oxidizer valve (oxidizer_main)
    - Turn on the igniter (no later than 1 second after opening the valves)
    - Rocket liftoff'''
    print("Rozpoczęcie sekwencji zapłonu.")
    logging.info("Inition sequence start.")
    
    #--------------------Open the main fuel valve (fuel_main)
    open_fuel_main=Frame( ids.BoardID.ROCKET,
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
    print(f"Główny zawór paliwa otwarty o {time_open_fuel:.2f}")
    logging.info(f"Main fuel valve opened at {time_open_fuel:.2f}")

    #--------------------Open the main oxidizer valve (oxidizer_main)
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
    print(f"Główny zawór utleniacza otwarty o {time_open_oxidizer:.2f}")
    logging.info(f"Main oxidizer valve open at {time_open_oxidizer:.2f}")

    #--------------------Valves must be opened within ≤ 1 second of each other
    if time_open_oxidizer-time_open_fuel<=1:
        print(f"Główne zawory otwarte bezpiecznie w czasie: {time_open_oxidizer-time_open_fuel:.2f}")
        logging.info(f"Main valves opened safely within: {time_open_oxidizer-time_open_fuel:.2f}")
    else:
        print(f"BŁĄD: Opóźnienie w otwarciu zaworów = {time_open_oxidizer-time_open_fuel:.2f}s (>1s). Ryzyko wybuchu!")
        logging.error(f"Delay between valves opening = {time_open_oxidizer-time_open_fuel:.2f}s. Explosion risk! Launch aborted.")
        sys.exit("Launch aborted due to unsafe valve timing.")
    
    #--------------------Turn on the igniter (no later than 1 second after opening the valves)
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
    print("Zapłon WŁĄCZONY")
    logging.info("Igniter ON")

    #-------------------- Check the time between opening the valves and activating the igniter
    if time_igniter_on-time_open_oxidizer<=1:
        print("Zapłon zakończony sukcesem: Start rakiety!")
        logging.info("IGNITION SUCCESSFUL: LIFTOFF!")
    else:
        print(f"BŁĄD: NIEUDANY ZAPŁON. Opóźnienie między otwarciem zaworów a włączeniem zapłonu = {time_open_oxidizer-time_open_fuel:.2f}s (>1s). Ryzyko wybuch!")
        logging.error(f"ERROR: IGNITION FAIL. Delay between valves opening and switching on igniter ={time_open_oxidizer-time_open_fuel:.2f}s. Explosion risk! Launch aborted.")
        sys.exit("IGNITION FAIL!:the combustion chamber flooded due to too much time between valves opening and switching on igniter")

#-------------------------------------------------------------
#flags
apogee_reached=False
apogee_time=0
parachute_open=False

last_altitude=0
last_altitude_time=0
aproximate_velocity=0

def on_altitude(frame:Frame):
    global apogee_reached, apogee_time
    global last_altitude,altitude,last_altitude_time, aproximate_velocity
    
    altitude=frame.payload[0]
    altitude_time=time.time()
    if(altitude<=last_altitude and not apogee_reached):# altitude is not increasing
        apogee_time=time.time()
        apogee_reached=True
        print(f"Apogeum zostało osiągnięte!")
        logging.error("The APOGEE has been reached")
    
    if apogee_reached and (last_altitude_time-altitude_time)!=0:
        aproximate_velocity=abs(last_altitude-altitude)/abs(last_altitude_time-altitude_time)
        print(f"Przybliżona prędkość aktualnie: {aproximate_velocity}")
    last_altitude=altitude
    last_altitude_time=altitude_time

def landing():
    '''6. Landing:
    - Deploy the parachute when the following conditions are met:
        No earlier than reaching apogee and within 10 seconds after apogee
        Engine is not running
        Velocity is less than 30 m/s (otherwise the parachute may tear)
    -Wait until the rocket lands safely'''
    global apogee_reached,last_altitude, apogee_time
    #--------------------------Determining the moment when the rocket reaches apogee
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
        except TransportTimeoutError:
            pass 
        except UnregisteredCallbackError as e:  
            #print(f"unregistered frame received: {e.frame}")
            pass
    
    if not apogee_reached:
        print("Nie osiągnięto apogeum")
        logging.error("Apogee was not reached")
    
    #---------------------------Rocket descending -> deploy the PARACHUTE
    while time.time()-apogee_time<=MAX_WAIT_AFTER_APOGEE :  # Deploy the parachute within a maximum of 10 seconds after apogee
        try:
            cm.receive()
            if abs(aproximate_velocity)<30:
                parachute_open_frame=Frame(
                                    ids.BoardID.ROCKET,
                                    ids.PriorityID.LOW,
                                    ids.ActionID.SERVICE,
                                    ids.BoardID.SOFTWARE,
                                    ids.DeviceID.RELAY,
                                    2,
                                    ids.DataTypeID.NO_DATA,
                                    ids.OperationID.RELAY.value.OPEN)
                cm.push(parachute_open_frame)
                cm.send()
                print("Spadachron otworzył się.")
                logging.info("parachute is open")
                parachute_open=True
                break
        except TransportTimeoutError:
            pass
        except UnregisteredCallbackError as e:
            pass
            #print(f"Unregistered frame received: {e.frame}")

    if not parachute_open:
        print("ERROR: Spadochron nie otworzył się. CRASH LANDING!")
        logging.error("ERROR: Parachute did not deploy. CRASH LANDING!")
        sys.exit("CRASH LANDING!")

    cm.unregister_callback(altitude_frame.as_reversed_frame())

if __name__ == "__main__":
    tank_oxidizer()
    tank_fuel()
    heat_oxidizer()
    ignition_sequence()
    
    print("RAKIETA LECI...")
    logging.info("ROCKET IN FLIGHT...")

    landing()
