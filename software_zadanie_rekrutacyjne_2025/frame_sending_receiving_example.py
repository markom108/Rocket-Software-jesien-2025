from communication_library.communication_manager import CommunicationManager, TransportType
from communication_library.tcp_transport import TcpSettings
from communication_library.frame import Frame
from communication_library import ids
from communication_library.exceptions import TransportTimeoutError, TransportError, UnregisteredCallbackError

def on_altitude(frame: Frame):
    print(f"Registered frame received: {frame}")

if __name__ == "__main__":
    cm = CommunicationManager() # Class responsible for communication handling
    cm.change_transport_type(TransportType.TCP)
    # We must create a frame that will serve as a pattern indicating what kind of frames we want to receive
    # During frame equality comparison the following fields are excluded: priority, data_type, payload
    # You can find more information in communication_library/frame.py

    altitude_frame = Frame(ids.BoardID.SOFTWARE, 
                           ids.PriorityID.LOW, 
                           ids.ActionID.FEED, 
                           ids.BoardID.ROCKET, 
                           ids.DeviceID.SENSOR, 
                           2, # altitude sensor
                           ids.DataTypeID.FLOAT,
                           ids.OperationID.SENSOR.value.READ)
    cm.register_callback(on_altitude, altitude_frame)
    cm.connect(TcpSettings("127.0.0.1", 3000))

    relay_open_frame = Frame(ids.BoardID.ROCKET, 
                           ids.PriorityID.LOW, 
                           ids.ActionID.SERVICE, 
                           ids.BoardID.SOFTWARE, 
                           ids.DeviceID.RELAY, 
                           0, # oxidizer heater
                           ids.DataTypeID.FLOAT,
                           ids.OperationID.RELAY.value.OPEN,
                           ()
                           )
    cm.push(relay_open_frame) # We need to push the frame onto the send queue
    cm.send() # Send queue first in the send queue

    servo_open_frame = relay_open_frame = Frame(ids.BoardID.ROCKET, 
                           ids.PriorityID.LOW, 
                           ids.ActionID.SERVICE, 
                           ids.BoardID.SOFTWARE, 
                           ids.DeviceID.SERVO, 
                           1, # oxidizer intake 
                           ids.DataTypeID.INT16,
                           ids.OperationID.SERVO.value.POSITION,
                           (0,) # 0 is for open position, 100 is for closed
                           )
    cm.push(servo_open_frame)
    cm.send()

    while True:
        try:
            frame = cm.receive() # We can handle frames using callbacks or by getting frame right from receive() call
        except TransportTimeoutError:
            pass
        except UnregisteredCallbackError as e:
            print(f"unregistered frame received: {e.frame}")
    