import sys
import zmq
import time
import json
import threading
import connection

# GET /voice_search?terms[]=saphire&terms[]=nozzle
# GET /vend_by_product_id/124345?quantity=1
# /vend_by_product_id/577642?quantity=2
zmq_config = {
                'inbound_topic':'wrapper_in',
                'outbound_topic':'wrapper_out',
                'pub_ep':'tcp://127.0.0.1:6000',
                'sub_ep':'tcp://127.0.0.1:6001',
                }
zmq_config_return = {
                'inbound_topic':'wrapper_in',
                'outbound_topic':'wrapper_out',
                'pub_ep':'tcp://127.0.0.1:7000',
                'sub_ep':'tcp://127.0.0.1:7001',
                }
rand_dict = {'item':'pen','quantity':2,'operation':'take','timestamp':5}
recv = {'getstate':0}
query = {'getstate':'/get/state/','search':'/voice_search?', 'filter':'/voice_search?', 'vend':'/vend_by_product_id/'} #from vendor

context = zmq.Context()
connection.StateModel(zmq_config).start()

class Msg: #receiving
    def __init__(self, msg_dict):
        self.item = msg_dict['item']
        self.quantity = msg_dict['quantity']
        self.operation = msg_dict['operation']
        self.timestamp = msg_dict['timestamp']
        
    def __str__(self):
        return f"{super().__str__()}:{self.item},{self.quantity},{self.operation},{self.timestamp}"
    
class StateModel:
    def __init__(self,zmq_config):
        self.subsocket = context.socket(zmq.SUB)
        self.subsocket.connect(zmq_config['pub_ep'])
        self.subsocket.setsockopt(zmq.SUBSCRIBE, zmq_config['inbound_topic'].encode())
        self.pushsocket = context.socket(zmq.PUSH)
        self.pushsocket.connect(zmq_config['sub_ep'])
#        from external system to internal
        self.subsocket2 = context.socket(zmq.SUB)
        self.subsocket2.connect(zmq_config_return['pub_ep'])
        self.subsocket2.setsockopt(zmq.SUBSCRIBE, zmq_config_return['inbound_topic'].encode())
        self.pushsocket2 = context.socket(zmq.PUSH)
        self.pushsocket2.connect(zmq_config_return['sub_ep'])
        self.api_call = ''
    
    def start(self):
        t = threading.Thread(target = self.run)
        t.start()
        t2 = threading.Thread(target = self.run2)
        t2.start()

    def run(self):
        while True:
            msg = self.subsocket.recv_multipart()
            print('query msg:',msg)
            try:
                json_msg = json.loads(msg[1])
                items = json.loads(msg[2]) #remove outermost square bracket if it is already a list
                if json_msg == 'search':
                    self.api_call = query[json_msg]
                    items = items[0].lower().split()
                    self.api_call += 'terms[]='+items[0]
                    for i in range (1,len(items)):
                        self.api_call += '&terms[]='+items[i]
#                     print(self.api_call)
                    self.pushsocket.send_multipart([zmq_config['inbound_topic'].encode(), json.dumps('get').encode(), json.dumps(self.api_call).encode()])
                elif json_msg == 'filter':
                    items = items[0].lower().split()
                    for i in range (len(items)):
                        self.api_call += '&terms[]='+items[i]
#                     print(self.api_call)
                    self.pushsocket.send_multipart([zmq_config['inbound_topic'].encode(), json.dumps('get').encode(), json.dumps(self.api_call).encode()])
                elif json_msg == 'vend':
                    amount = json.loads(msg[-1])
                    self.api_call = query[json_msg]
                    self.api_call += items[0]+'?quantity='+str(amount[0])
#                     print(self.api_call)
                    self.pushsocket.send_multipart([zmq_config['inbound_topic'].encode(), json.dumps('vend').encode(),  json.dumps(self.api_call).encode()])
            except Exception as e:
                print("ERROR2")
                print(e)

    def run2(self):
        while True:
            msg_return = self.subsocket2.recv_multipart()
            print('from external:',msg_return)
            try:
                json_msg_return = json.loads(msg_return[-1])
                print('query external:',json_msg_return)
                self.pushsocket2.send_multipart([zmq_config_return['inbound_topic'].encode(), json.dumps(json_msg_return).encode()])
            except Exception as e:
                print("ERROR2")
                print(e)
                
if __name__ == "__main__":
    for key in query.keys():
        if key == 'getstate':
            print(query[key])
#     socket = context.socket(zmq.SUB)
#     socket.connect ('tcp://127.0.0.1:6000')
#     #socket.subscribe("Tw") #Tw is the topic
#     topic = "11"
#     socket.setsockopt(zmq.SUBSCRIBE, topic.encode())
#     while True:
#         string = socket.recv()
#         print(string)

