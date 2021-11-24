import sys
import zmq
import time
import json
import threading
import requests
import pprint
import os

# "https://asdfasdf.free.beeceptor.com"
base_url = os.environ["KIOSK_API"] or 'https://bfcd4d26-ec62-4d24-ac89-c8ea1b048bb9.mock.pstmn.io'
print("base url: ", base_url)

zmq_config_return = {
                'inbound_topic':'wrapper_in',
                'outbound_topic':'wrapper_out',
                'pub_ep':'tcp://127.0.0.1:7000',
                'sub_ep':'tcp://127.0.0.1:7001',
                }

context = zmq.Context()

class Msg: #from external
    def __init__(self, msg_dict):
        self.item = msg_dict['item']
        self.quantity = msg_dict['quantity']
        self.operation = msg_dict['operation']
        self.timestamp = msg_dict['timestamp']

    def __str__(self):
        return f"{super().__str__()}:{self.item},{self.quantity},{self.operation},{self.timestamp}"

class StateModel:
    def __init__(self,zmq_config):
        self.pullsocket = context.socket(zmq.PULL)
        self.pullsocket.bind(zmq_config['sub_ep'])

        self.pubsocket2 = context.socket(zmq.PUB)
        self.pubsocket2.bind(zmq_config_return['pub_ep'])
        self.api_call=''

    def start(self):
        t = threading.Thread(target = self.run)
        t.start()

    def run(self):
        while True:
            msg = self.pullsocket.recv_multipart()
            print("connect msg:", msg)
            try:
                json_msg = json.loads(msg[-2])
                self.api_call = json.loads(msg[-1])
                if json_msg == "get":
#                     print('gett')
                    resp = self.get(self.api_call)
#                     print(resp.json())
                    self.pubsocket2.send_multipart([zmq_config_return['inbound_topic'].encode(), json.dumps(resp.json()).encode()])
                elif json_msg == 'vend':
#                     print('vend')
                    resp = self.get(self.api_call)
#                     print(resp.json())
                    self.pubsocket2.send_multipart([zmq_config_return['inbound_topic'].encode(), json.dumps(resp.json()).encode()])
            except Exception as e:
                print("ERROR3")
                print(e)

    def get_machine_state(self, endpoint):
        print("machine state")
        return requests.get(_url(endpoint))
    def get(self, endpoint):
        print("get request")
        return requests.get(_url(endpoint))
#     def post_mode(self): #notify withdraw,restock, etc
#         print("mode")
#         pass
#     def get_item_quantity(self):
#         print("iteam and quantity")
#         return requests.get(_url('/itemquantity/'))
#     def post_item_quantity(self):
#         print("item quantity") #notify item and quantity
#         pass
#     def order_complete(self):
#         return requests.post(_url('/ordercomplete'), json = {'complete': True})
#     def database(self, msg):
#         print("databse access")

def _url(path):
    return base_url + path

if __name__ == "__main__":
    topic = "frommachine"
    resp = requests.get(_url('/get/state/'))
    print(resp) #<Response [200]>
    print(resp.json())
#     socket = context.socket(zmq.SUB)
#     socket.connect ('tcp://127.0.0.1:6000')
#     #socket.subscribe("Tw") #Tw is the topic
#     topic = "11"
#     socket.setsockopt(zmq.SUBSCRIBE, topic.encode())
#     while True:
#         string = socket.recv()
#         print(string)

# if resp.status_code != 200: #get
#     raise ApiError('cannot find: {}'.format(resp.status_code))
