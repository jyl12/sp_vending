import json  #parse json
import csv  #read write csv
import datetime
import os  #get file name and extension
# import xml.etree.ElementTree as ET #parse xml
# from dicttoxml import dicttoxml
# from xml.dom.minidom import parseString
# import xmltodict
import paho.mqtt.client as mqtt
#os.system('python handle.py')
import requests #http
import zmq
import time
import random
import querymodel
# os.environ['GPIOZERO_PIN_FACTORY'] = os.environ.get('GPIOZERO_PIN_FACTORY', 'mock')
from gpiozero.pins.native import NativeFactory
from gpiozero import LED
from time import sleep
factory = NativeFactory()
led1=LED(21,pin_factory=factory) #gpio21, voice listening indicator
led2=LED(26,pin_factory=factory) #gpio26, voice listening indicator duplicate
led2.off()
led1.off()

CONFIG_MENU = "menu.json"
CONFIG_ORDER = "orders.csv"
CURRENT_ORDER_ID = 1
CURRENT_CUSTOMER_ID = 1
USER_FILE = "user.json"
HTTP_COMM = 1 # enable http communication
LIKELIHOOD = 0.75
DICT_ITEMMAP = 1 # enable item mapping from speech to item name
DICT_ITEM={'face mask':['fm1'], 'drill':['drill'], 'sapphire nozzle':['sp']}

MQTT_BROKER = os.environ['MQTT_BROKER'] or "localhost"
print("MQTT Broker: ", MQTT_BROKER)

get_state, post_operation, post_item, post_quantity = range(0,4) #http command
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

context = zmq.Context()
socket = context.socket(zmq.PUB)
socket.bind(zmq_config['pub_ep'])
pullsocket2 = context.socket(zmq.PULL)
pullsocket2.bind(zmq_config_return['sub_ep'])
querymodel.StateModel(zmq_config).start()

def result_collector():
    msg = pullsocket2.recv_multipart()
    print("returnmsg:", msg)
    try:
        json_msg = json.loads(msg[-1])
        print('returnedjson:',json_msg)
    except Exception as e:
        print("ERROR1")
        print(e)
    return json_msg

class order (object):
    def __init__(self,userid,orderid_):
        self.state = -1
        self.order = {}
        self.orderID = orderid_
        self.customerID = userid
        self.lastDialogue = ""
        self.api_call = ""
        self.resp = {}
        self.orderCost = 0
        self.instructions = []
#         self.loadUserData()

    def loadUserData(self):
        try:
            print("loadUserData(Dummy)")
        except:
            pass

    def repeatLastOrder(self):
        print("func::repeat last order")
        dialogue = ""
        if order:
            dialogue = self.reciteOrder()
        else:
            dialogue = "I can't find your old order.  Please make a new one"
        return dialogue

    def payment_status_callback(self, msg):
        print("func::payment status callback: Assuming successsful.")
        dialogue = ""
#         if int(msg.payload) == 0:
#             self.state = 8
#             dialogue = "Sorry, your order cannot be processed."
#         elif int(msg.payload) == 1:
#             dialogue = "Thank you for your order."
#             self.state = 7
        dialogue = "Bypass:Thank you for your order."
        self.state = 7
        self.lastDialogue = dialogue

    def issue_status_callback(self, msg):# might call 2 times for item and amount
        print("func::issue status callback:")
        dialogue = ""
        if int(msg["mqtt_msg"]) == 0:
            self.state = 8
            dialogue = "Sorry, your order cannot be processed."
        elif int(msg["mqtt_msg"]) == 1:
            dialogue = "Thank you for your order."
            self.state = 9
        elif int(msg["mqtt_msg"]) == 2: #item list found
            self.state = 11
        elif int(msg["mqtt_msg"]) == 3: #quantity found
            self.state = 13
        elif int(msg["mqtt_msg"]) == 4: #collect item
            self.state = 17
        self.lastDialogue = dialogue

    def payment(self): #bypass payment for testing
        print("func::payment")
#         kiosk.mqtt.publish("voice/payment/start",self.orderCost)
###################for bypass demo
        self.payment_status_callback("0")
        self.lastDialogue += "Your order ID is " + str(self.orderID)
        print(self.lastDialogue)
        self.orderCompleted()
        self.deliver()
#################

    def deliver(self):
        print("func::deliver")
        #send signals to actuator
        #self.state = 11

    def calOrder(self):
        print("func::calculate order.")
        self.orderCost = 0
        for item,amount in self.order.items():
            self.orderCost += kiosk.menu[item] * amount

    def writeOrderFile(self):
        print("func::writeorderfile")
        time_stamp = datetime.datetime.now()
        with open(CONFIG_ORDER, 'a') as f:
            for item,quantity in self.order.items():
                fields = [time_stamp, self.orderID, self.customerID, item, quantity]
                writer = csv.writer(f)
                writer.writerow(fields)

    def writeUserFile(self):
        print("func::writeuserfile")
        if self.customerID in kiosk.user.keys():
            kiosk.user[self.customerID]["lastOrder"] = self.order
        else:
            d = {"customerID":self.customerID, "lastOrder":self.order}
            kiosk.user[self.customerID] = d
        file_name, file_extension = os.path.splitext(USER_FILE)
        if file_extension == ".json":
            with open('user.json', 'w') as json_file:
                json.dump(kiosk.user, json_file)
#         elif file_extension == ".xml":
#             xml = dicttoxml(kiosk.user, attr_type = False)
#             xml_decode = xml.decode()
#             with open('user.xml', 'w') as xml_file:
#                 xmlfile.write(parseString(xml_decode).toprettyxml())

    def orderCompleted(self):
        print("func::ordercompleted")
        self.writeOrderFile()
#         self.writeUserFile()
        self.opState = 0

    def reciteOrder(self):
        print("func::reciteorder")
#         print(self.order.items())
        dialogue = "Your order contains "
        if sum(self.order.values()) == 1:
            dialogue += str(sum(self.order.values())) + " item "
        else:
            dialogue += str(sum(self.order.values())) + " items "
#         for i in self.order.items():
#             dialogue += str(i[1]) + " " + str(i[0]) + " "
        return dialogue

    def finaliseOrder(self):
        print("func::finaliseorder")
        if self.state <= 2:
            dialogue = self.reciteOrder()
            dialogue += ". "
        elif self.state <= 10:
            dialogue = self.reciteOrder()
            self.calOrder()
            dialogue += ". Your order cost " + str(self.orderCost) + ". Please proceed to payment. "
        elif ((self.state >= 11) and (self.state <= 20)):
            dialogue = self.reciteOrder()
            dialogue += ". "
        return dialogue

    def addItems(self, intent_message):
        print("func::addItems")
#         print(json.dumps(intent_message,indent =4))
        items = []
        amounts = []
        action = []
        enums = []
        for x in range(len(intent_message["slots"])):
            if intent_message["slots"][x]["slotName"] == "item":
                item = list(map(lambda x: str(x), intent_message["slots"][x]["value"].values()))
                item = [n.title() for n in item] # capitalise each word
                items.append(item[1])
            if intent_message["slots"][x]["slotName"] == "amount":
                amount = list(map(lambda x: str(x), intent_message["slots"][x]["value"].values()))
                amounts.append(int(amount[1]))
            if intent_message["slots"][x]["slotName"] == "action":
                action = list(map(lambda x: str(x), intent_message["slots"][x]["value"].values()))
                action = action[1:]
            if intent_message["slots"][x]["slotName"] == "enum":
                enum = list(map(lambda x: str(x), intent_message["slots"][x]["value"].values()))
                enums.append(enum[1])
        dialogue = ""
        if DICT_ITEMMAP == 1:  # map the speech item to the item name in vending
            print(items)
            items = items[0].lower()
            items = DICT_ITEM[items]
            print(items)
        try:
            if len(items) == len(enums):
                if HTTP_COMM == 0:
                    items = items[0].lower().split()
                    self.api_call = 'terms[]='+items[0]
                    for i in range (1,len(items)):
                        self.api_call += '&terms[]='+items[i]
                    self.api_call = '/voice_search?'+self.api_call+'&terms[]='+enums[0]
                    print('GET1 ', self.api_call)
                    self.resp = { "results": [ 577642 ], "matches": 1 }
                    items = items + enums
                    items[:] = [' '.join(items[:])]
                else:#HTTP_COMM == 1
                    items = items + enums
                    items[:] = [' '.join(items[:])]
                    socket.send_multipart([zmq_config['inbound_topic'].encode(), json.dumps('search').encode(), json.dumps(items).encode()])
#                     print('socket send')
#                     print('socket received')
                    self.resp = result_collector()
                    print('socket collected:', self.resp)
#                     self.resp = result_collector()
#                     print('second read:', self.resp)
#                     self.resp = result_collector()
#                     print('third read:', self.resp)
#                     if  'matches' not in self.resp:
#                         self.resp = result_collector()
#                         print('secondsocket collected:', self.resp)
                if self.resp['matches'] == 1:
                    if len(items) == len(amounts):
                        add={}
                        add = dict(zip(items,amounts))
                        for item,amount in add.items():
                            if item in self.order.keys():
                                self.order[item] = self.order[item] + amount
                            else:
                                self.order[item] = amount
                                dialogue += str(amount) + " " + str(item) + " "
#                         print('the order:',self.order)
                        dialogue += "is added to your order. "
                        self.api_call = '/vend_by_product_id/'+str(self.resp['results'][0])+'?quantity='+str(amount)
            else: #need filter
                if HTTP_COMM == 0:
                    if any(x in action for x in ["filter"]):
                        items = items[0].lower().split()
                        for i in range (len(items)):
                            self.api_call += '&terms[]='+items[i]
                        self.api_call = '/voice_search?'+self.api_call
                        print('GET12 ',self.api_call)
                        self.resp = { "results": [ 123375, 124344, 124345 ], "matches": 3 }
                        if self.resp['matches'] > 1:
                            dialogue += 'Multiple matches. '
                        else:
                            dialogue += ''
                    elif not items: #e.g."get{action} 1{amount} number 2{enum}"
                        items = self.resp['results'][int(enums[0]) - 1]
                        add={}
                        add = dict(zip([items],amounts))
                        for item,amount in add.items():
                            if item in self.order.keys():
                                self.order[item] = self.order[item] + amount
                            else:
                                self.order[item] = amount
                                dialogue += str(amount) + " item " + str(int(enums[0])) + " "
                        dialogue += "is added to your order. "
                        self.api_call = '/vend_by_product_id/'+str(self.resp['results'][int(enums[0]) - 1])+'?quantity='+str(amount)
                    else:
                        items = items[0].lower().split()
                        self.api_call = 'terms[]='+items[0]
                        for i in range (1,len(items)):
                            self.api_call += '&terms[]='+items[i]
                        self.api_call = '/voice_search?'+self.api_call
                        print('GET11 ', self.api_call)
                        self.resp = { "results": [ 123375, 124344, 124345, 124351, 124352 ], "matches": 5 }
                        if self.resp['matches'] == 1:
                            items = items + enums
                            items[:] = [' '.join(items[:])]
                            if len(items) == len(amounts):
                                add={}
                                add = dict(zip(items,amounts))
                                for item,amount in add.items():
                                    if item in self.order.keys():
                                        self.order[item] = self.order[item] + amount
                                    else:
                                        self.order[item] = amount
                                        dialogue += str(amount) + " " + str(item) + " "
                                dialogue += "is added to your order. "
                                self.api_call = '/vend_by_product_id/'+str(self.resp['results'])+'?quantity='+str(amount)
                        elif self.resp['matches'] > 1:
                            dialogue += 'Multiple matches. '
                else: #if HTTP_COMM == 1
                    if any(x in action for x in ["filter"]):
                        socket.send_multipart([zmq_config['inbound_topic'].encode(),
                                               json.dumps('filter').encode(),
                                               json.dumps(items).encode()])
                        self.resp = result_collector()
                        if self.resp['matches'] > 1:
                            dialogue += 'Multiple matches. '
                        else:
                            dialogue += ''
                    elif not items: #e.g."get{action} 1{amount} number 2{enum}"
                        items = self.resp['results'][int(enums[0]) - 1]
                        add={}
                        add = dict(zip([items],amounts))
                        for item,amount in add.items():
                            if item in self.order.keys():
                                self.order[item] = self.order[item] + amount
                            else:
                                self.order[item] = amount
                                dialogue += str(amount) + " item " + str(int(enums[0])) + " "
                        dialogue += "is added to your order. "
                        self.resp['results'][0] = items #put the item to first position for api-call
                    else:
                        socket.send_multipart([zmq_config['inbound_topic'].encode(),
                                               json.dumps('search').encode(),
                                               json.dumps(items).encode()])
                        self.resp = result_collector()
                        if self.resp['matches'] == 1:
                            items = items + enums
                            items[:] = [' '.join(items[:])]
                            if len(items) == len(amounts):
                                add={}
                                add = dict(zip(items,amounts))
                                for item,amount in add.items():
                                    if item in self.order.keys():
                                        self.order[item] = self.order[item] + amount
                                    else:
                                        self.order[item] = amount
                                        dialogue += str(amount) + " " + str(item) + " "
                                dialogue += "is added to your order. "
                        elif self.resp['matches'] > 1:
                            dialogue += 'Multiple matches.'
#             if len(items) == len(amounts):
#                 add={}
#                 add = dict(zip(items,amounts))
#                 for item,amount in add.items():
#                     if item in self.order.keys():
#                         self.order[item] = self.order[item] + amount
#                     else:
#                         self.order[item] = amount
#                         dialogue += str(amount) + " " + str(item) + " "
#                 dialogue += "is added to your order. "
#             elif len(items) != len(amounts):
#                 if self.state == 0:
#                     dialogue = "Please use number for quantity. "
#                 elif self.state == 13:
#                     self.state = 14
#                     for item,amount in self.order.items():
#                         self.order[item] = amounts
#                     dialogue += "Amount is " + str(amounts) + ". "
#                 else:
#                     self.state = 12
#                     #print("key is:",self.order.keys())
#                     for x in items:
#                         if x in self.order.keys():
#                             pass
#                         else:
# #                             print(kiosk.menu.keys())
#                             if x in kiosk.menu.keys():
#                                 self.order[x] = 0  #enter dictionary key with value = 0
#                     if (len(items) - len(amounts)) > 1:
#                         dialogue += str(items) + " are selected. "
#                     else:
#                         dialogue += str(items) + " is selected. "
#                     #print("before exit",self.order)
        except:
            dialogue = "Sorry, I didn't get that. "

        if self.state > 10:
            pass
        else:
            self.state = 0
        #print(dialogue)
#         print('add_state is', self.state)
        return dialogue

    def removeItems(self, intent_message):
        print("func::removeitems")
        items = []
        amounts = []
        action = []
        enums = []
        for x in range(len(intent_message["slots"])):
            if intent_message["slots"][x]["slotName"] == "item":
                item = list(map(lambda x: str(x), intent_message["slots"][x]["value"].values()))
                item = [n.title() for n in item] # capitalise each word
                items.append(item[1])
            if intent_message["slots"][x]["slotName"] == "amount":
                amount = list(map(lambda x: str(x), intent_message["slots"][x]["value"].values()))
                amounts.append(int(amount[1]))
            if intent_message["slots"][x]["slotName"] == "action":
                action = list(map(lambda x: str(x), intent_message["slots"][x]["value"].values()))
                action = action[1:]
            if intent_message["slots"][x]["slotName"] == "enum":
                enum = list(map(lambda x: str(x), intent_message["slots"][x]["value"].values()))
                enums.append(enum[1])
        items = items + enums
        items[:] = [' '.join(items[:])]
        p = []
        try:
            p = list(map(lambda x: self.order.pop(x,""),items)) #return value of key
        except:
            pass
        dialogue = ""
        count = 0
        for i in range(len(p)):
            if p[i]:
                count += 1
                dialogue += " " + str(items[i]) + ", "
        if count == 1:
            dialogue += " is removed from your order."
        if count > 1:
            dialogue += " are removed from your order."
        if count == 0:
            dialogue = " Nothing to remove, "
        self.state = 0
        return dialogue

    def addInstructions(self, intent_message):
        print("func::add instructions") # special request
        dialogue = ""

    def response(self, intent_message):
        print("func::response")
        #print(json.dumps(intent_message,indent =4))
        for x in range(len(intent_message["slots"])):
            if intent_message["slots"][x]["slotName"] == "response":
                response = list(map(lambda x: str(x), intent_message["slots"][x]["value"].values()))
                response = response[1:]
        dialogue = ""
        if self.state == 0:
            if "yes" in response:
                self.state = 17 #original state is 6
                if self.order == {}:
                    self.state = 8
                elif self.order:
                    if (HTTP_COMM == 0):
                        print('VEND ', self.api_call)
                    elif (HTTP_COMM == 1):
                        socket.send_multipart([zmq_config['inbound_topic'].encode(),
                                               json.dumps('vend').encode(),
                                               json.dumps([str(self.resp['results'][0])]).encode(),
                                               json.dumps(list(self.order.values())).encode()])
                        self.resp = result_collector()
            elif any(x in response for x in ["stop" , "cancel"]):
                self.order == {}
                self.state = 8
            elif 'repeat' in response:
#                 print('repeat Current order',self.order)
                dialogue = self.repeatLastOrder()
            else:
                self.state = 0
                socket.send_multipart([zmq_config['inbound_topic'].encode(),
                                       json.dumps('search').encode(),
                                       json.dumps(['cancel']).encode()])
                self.resp = result_collector()
                if self.order == {}:
                    dialogue = " Please specify your items and quantity."
                else:
                    dialogue = " Please specify your new items and quantity. "
        elif self.state == 12:
            if "no" in response:
                self.state = 11
                self.order = {} #remove all order item.
            else:
                #self.state = 20 #waiting state
                self.state = 13
                #kiosk.mqtt.publish("voice/item","check_item_quantity")
                if(HTTP_COMM == 1):
                    pass
#                     for x in range(len(itemListHttp["Items"])): #test http
#                         if itemListHttp["Items"][x] == self.order.key():
#                             self.state = 13
#                             break
#                         else:
#                             self.state = 11
#                             self.order = {}
#                             dialogue = "Item unavailable. "
#                     resp = http_callback(post_item)#test http
#                     quantityListHttp = resp.json()
        elif self.state == 14:
            if "no" in response:
                self.state = 13
            else:
                #self.state = 20 #waiting state
                self.state = 17
                #kiosk.mqtt.publish("voice/amount","prepare_item")
                if (HTTP_COMM == 1):
                    pass
#                     maxQuantity = max(quantityListHttp["Quantities"])
#                     for x in range(len(quantityListHttp["Quantities"])):
#                         if quantityListHttp["Quantities"][x] == self.order.values():
#                             self.state = 17
#                             break
#                         else:
#                             self.state = 13
#                             dialogue = "Maximum number is " + str(maxQuantity) +". "
#                     resp = http_callback(post_quantity)#test http
#                     orderCompleteHttp = resp.json()
        else:
            print("res")
        return dialogue

    def order_intent_callback(self, intent_message):
        #print("func::order intent callback.")
        """Called each time a message is received on a subscribed topic."""
        nlu_payload = json.loads(intent_message.payload)
#         if intent_message.topic == "hermes/nlu/intentNotRecognized":
#             self.state = 21
#         elif intent_message.topic == "hermes/hotword/porcupine/detected":#porcupine only
#             print("Hotword detected.")
#             return
        if intent_message.topic == "hermes/intent/AddItems":
            print("Got intent::", nlu_payload["intent"]["intentName"])
            self.lastDialogue = self.addItems(nlu_payload)
        elif intent_message.topic == "hermes/intent/RemoveItems":
            print("Got intent::", nlu_payload["intent"]["intentName"])
            self.lastDialogue = self.removeItems(nlu_payload)
        elif intent_message.topic == "hermes/intent/Response":
            print("Got intent::", nlu_payload["intent"]["intentName"])
            self.lastDialogue = self.response(nlu_payload)
        elif intent_message.topic == "hermes/intent/GetActionsItems":
            print("Got intent::", nlu_payload["intent"]["intentName"])
            self.lastDialogue = self.addItems(nlu_payload)
        else:
            # Intent
            print("else Got intent:", nlu_payload["intent"]["intentName"])
        self.stateSpace(nlu_payload)

    def stateSpace(self, intent_message):#state action
        #print(json.dumps(intent_message,indent=4))
        print("func::statespace")
        if self.state == 0:
            self.lastDialogue += " Is this correct?"
            print (self.lastDialogue)
            kiosk.mqtt.publish("hermes/dialogueManager/continueSession", json.dumps({"sessionId": intent_message["sessionId"], "text": self.lastDialogue}))
        elif self.state == 1:
            self.lastDialogue += " Would you like to remove these items?"
            kiosk.mqtt.publish("hermes/dialogueManager/continueSession", json.dumps({"sessionId": intent_message["sessionId"], "text": self.lastDialogue}))
        elif self.state == 6:
            self.lastDialogue  = self.finaliseOrder()
            self.lastDialogue += "Please place your card near the card reader."
            print(self.lastDialogue)
            kiosk.mqtt.publish("hermes/dialogueManager/endSession", json.dumps({"sessionId": intent_message["sessionId"], "text": self.lastDialogue}))
            self.payment()
        elif self.state == 7:
            self.lastDialogue += "Your order ID is " + str(self.orderID)
            kiosk.mqtt.publish("hermes/dialogueManager/startSession", json.dumps({"init":{"type": "notification", "text": self.lastDialogue}, "siteId": intent_message["siteId"]}))
            self.orderCompleted()
        elif self.state == 8:
            self.lastDialogue += ""
            kiosk.mqtt.publish("hermes/dialogueManager/startSession", json.dumps({"init":{"type": "notification", "text": self.lastDialogue}, "siteId": intent_message["siteId"]}))
            kiosk.mqtt.publish("hermes/hotword/toggleOff", json.dumps({"siteId": "default"}))
            led1.off()
            led2.off()
        elif self.state == 9:
            self.lastDialogue = "Order number " + str(self.orderID) + " please collect your order."
            kiosk.mqtt.publish("hermes/dialogueManager/startSession", json.dumps({"init":{"type": "notification", "text": self.lastDialogue}, "siteId": intent_message["siteId"]}))
        elif self.state == 10:
            print("Delivering order.")
            self.deliver()
        ###try the supply point vending flow from here onwards
        elif self.state == 11:
            #print("state 11")
            intent_message["siteId"] = "default"
            self.lastDialogue += "Please specify your item. "
            print (self.lastDialogue)
            kiosk.mqtt.publish("hermes/dialogueManager/continueSession", json.dumps({"sessionId": intent_message["sessionId"], "text": self.lastDialogue}))
        elif self.state == 12:
            #print("state 12")
            self.lastDialogue += " Is this the correct item? "
            print (self.lastDialogue)
            kiosk.mqtt.publish("hermes/dialogueManager/continueSession", json.dumps({"sessionId": intent_message["sessionId"], "text": self.lastDialogue}))
        elif self.state == 13:
            #print("state 13")
            intent_message["siteId"] = "default"
            self.lastDialogue += "Please specify your amount. "
            print (self.lastDialogue)
            kiosk.mqtt.publish("hermes/dialogueManager/continueSession", json.dumps({"sessionId": intent_message["sessionId"], "text": self.lastDialogue}))
        elif self.state == 14:
            #print("state 14")
            self.lastDialogue += " Is this the correct amount? "
            print (self.lastDialogue)
            kiosk.mqtt.publish("hermes/dialogueManager/continueSession", json.dumps({"sessionId": intent_message["sessionId"], "text": self.lastDialogue}))
        elif self.state == 17:
            #print("state17")
            intent_message["siteId"] = "default"
            self.lastDialogue  = self.finaliseOrder()
            self.lastDialogue += "Your order ID is " + str(self.orderID) + ". Please collect your order."
            print(self.lastDialogue)
#             while orderCompleteHttp["Complete"] != 'true':
#                 pass
            kiosk.mqtt.publish("hermes/dialogueManager/startSession", json.dumps({"init":{"type": "notification", "text": self.lastDialogue}, "siteId": intent_message["siteId"]}))
            self.orderCompleted()
            kiosk.mqtt.publish("hermes/hotword/toggleOff", json.dumps({"siteId": "default"}))
            led1.off()
            led2.off()
            print("----------")
        elif self.state == 20:  #waiting state
            self.lastDialogue = " "
            kiosk.mqtt.publish("hermes/dialogueManager/continueSession", json.dumps({"sessionId": intent_message["sessionId"], "text": self.lastDialogue}))
        elif self.state == 21: #unrecognised intent
            self.lastDialogue = " Unrecognised intent. Session ended. "
            kiosk.mqtt.publish("hermes/dialogueManager/endSession", json.dumps({"sessionId": intent_message["sessionId"], "text": self.lastDialogue}))
        else:
            # Speak the text from the intent
            self.lastDialogue = intent_message["input"]
            #kiosk.mqtt.publish("hermes/tts/say", json.dumps({"text": self.lastDialogue, "siteId": intent_message["siteId"]}))

class kiosk(object):
    def on_connect(self, client, userdata, flags, rc):
        """Called when connected to MQTT broker."""
#         kiosk.mqtt.subscribe("hermes/hotword/#")
        kiosk.mqtt.subscribe("hermes/intent/#")
        kiosk.mqtt.subscribe("hermes/nlu/intentNotRecognized")
        kiosk.mqtt.subscribe("hermes/dialogueManager/#")
        kiosk.mqtt.subscribe('hermes/asr/textCaptured' )
        kiosk.mqtt.subscribe("machine/hotword/on")
#         kiosk.mqtt.subscribe("machine/issue/status")
#         kiosk.mqtt.subscribe("machine/login/status")
#         kiosk.mqtt.subscribe("machine/payment/status")

    #     kiosk.mqtt.subscribe("hermes/asr/#")
    #     kiosk.mqtt.subscribe("hermes/nlu/#")
    #     kiosk.mqtt.subscribe("hermes/tts/#")
    #     kiosk.mqtt.subscribe("hermes/dialogueManager/#")
    #     kiosk.mqtt.subscribe("hermes/audioServer/#")
        print("Connected. Waiting for intents.")

    def on_disconnect(self, client, userdata, flags, rc):
        """Called when disconnected from MQTT broker."""
        kiosk.mqtt.reconnect()

    def loadMqtt(self):
        print("func::load mqtt")
        kiosk.mqtt.on_connect = self.on_connect
        kiosk.mqtt.on_message = self.on_message
        #kiosk.mqtt.on_message = self.mqtt_callback
        kiosk.mqtt.on_disconnect = self.on_disconnect
        kiosk.mqtt.connect(MQTT_BROKER, 1883)  # 12183 internal, 1883 external
        kiosk.mqtt.loop_start()

    def __init__(self):
        self.mqtt_addr = MQTT_BROKER + ":1883"
        kiosk.currentOrder = []
#         kiosk.menu = self.loadMenu()
#         kiosk.user = self.loadUserFile()
#         kiosk.quantity = self.loadQuantity()
        kiosk.mqtt = mqtt.Client()
        self.loadMqtt()
        self.opState = 0
        self.operation = 0
        self.attempt = 0 #for likelihood retry
        self.likelihood = 0 #for likelihood retry
        self.asr_text=''
        kiosk.mqtt.publish("hermes/hotword/toggleOff", json.dumps({"siteId": "default"}))
        led1.on()
        led2.on()
        sleep(3)
        led2.off()
        led1.off()
        print("kiosk init done")

    def loadMenu(self):
        print("func::loadmenu")
        file_exists = os.path.isfile(CONFIG_MENU)
        if file_exists:
            file_name,file_extension = os.path.splitext(CONFIG_MENU)
            menuDict = {}
            if file_extension == ".json":
                with open(CONFIG_MENU) as config_menu_file:
                    menu = json.load(config_menu_file)
                    for section in menu.values():
                        list(map(lambda x,y: menuDict.update({x:y["price"]}),section[0].keys(),section[0].values()))
#             elif file_extension == ".xml":
#                 menu_items = []
#                 menu_prices = []
#                 tree = ET.parse(CONFIG_MENU)
#                 root = tree.getroot()
#                 for item in root.iter('name'):
#                     item = item.text
#                     menu_items.append(item)
#                 for price in root.iter('price'):
#                     price = price.text
#                     menu_prices.append(float(price))
#                 menuDict = dict(zip(menu_items,menu_prices))
        else:
            print("Error: Menu file does not exist.")
        #print("menuDict is",menuDict)
        return menuDict

    def loadQuantity(self):
        print("func::loadquantity")
        file_exists = os.path.isfile(CONFIG_MENU)
        if file_exists:
            file_name,file_extension = os.path.splitext(CONFIG_MENU)
            quantityDict = {}
            if file_extension == ".json":
                with open(CONFIG_MENU) as config_menu_file:
                    menu = json.load(config_menu_file)
                    for section in menu.values():
                        list(map(lambda x,y: quantityDict.update({x:y["quantity"]}),section[0].keys(),section[0].values()))
#             elif file_extension == ".xml":
#                 menu_items = []
#                 menu_quantity = []
#                 tree = ET.parse(CONFIG_MENU)
#                 root = tree.getroot()
#                 for item in root.iter('name'):
#                     item = item.text
#                     menu_items.append(item)
#                 for quantity in root.iter('quantity'):
#                     quantity = quantity.text
#                     menu_quantity.append(float(quantity))
#                 quantityDict = dict(zip(menu_items,menu_quantity))
        else:
            print("Error: Menu file does not exist.")
        #print("menuDict is",menuDict)
        return quantityDict

    def loadUserFile(self):
        print("func::loaduserfile")
        file_name, file_extension = os.path.splitext(USER_FILE)
        if file_extension == ".json":
            with open(USER_FILE) as file:
                user = json.load(file)
#         elif file_extension == ".xml":# need to test
#             with open(USER_FILE) as xmlfile:
#                 data_dict = xmltodict.parse(xmlfile.read())
#                 user = json.dumps(data_dict['root'])
        #print(user)
        return user

    def newOrder(self):
        print("func::neworder")
        global CURRENT_ORDER_ID, CURRENT_CUSTOMER_ID
        userid = CURRENT_CUSTOMER_ID
        CURRENT_CUSTOMER_ID += 1
        if self.operation == 1:
            kiosk.currentOrder.append(order(userid, CURRENT_ORDER_ID))
            CURRENT_ORDER_ID += 1
        elif self.operation == 2:
            print("new return order")
#             kiosk.currentOrder.append(APP_return.ReturnOrder(userid, CURRENT_ORDER_ID))
#             CURRENT_ORDER_ID += 1
#             print("new return order1")
        else:
            pass

    def login(self):
        print("func::login start")
        kiosk.mqtt.publish("voice/login/start","1")

    def login_status_callback(self, msg):
        print("func::login status callback")
        dialogue = ""
        if int(msg["mqtt_msg"]) == 0:
            self.opState = 0
            dialogue = "Sorry, please try again."
        elif int(msg["mqtt_msg"]) == 1:
            dialogue = "Login successful. "
            self.opState = 1
        self.lastDialogue = dialogue

    def getActions(self, intent_message):
        print("func::get action")
#         print('msg',intent_message)
        if (HTTP_COMM == 0):
            for x in range(len(intent_message["slots"])):
                if intent_message["slots"][x]["slotName"] == "action":
                    action = list(map(lambda x: str(x), intent_message["slots"][x]["value"].values()))
                    action = action[1:]
            if any(x in action for x in ["take" , "issue" , "dispense" , "withdraw" , 'give', 'get', 'filter']):
                self.opState = 2
                self.operation = 1
                self.state = 0 #11 # bypass: skip publish and wait response
                #kiosk.mqtt.publish("voice/issue/start","check_item_availability")
#             elif "return" in action:
#                 print("return action")
#                 #self.opState = 2
#                 #self.operation = 2
#                 #self.state = 40
#                 #kiosk.mqtt.publish("voice/return/start","1")
#             elif "locate" in action:
#                 #print("locate action")
#                 #kiosk.mqtt.publish("voice/locate/start","1")
#                 self.operation = 3
#             elif "admin" in action:
#                 #print("admin action")
#                 #kiosk.mqtt.publish("voice/admin/start","1")
#                 self.operation = 4
            else:
                pass
            dialogue =  str(action) + " operation is selected. "
            self.lastDialogue = dialogue
        elif (HTTP_COMM == 1):
#         resp = http_callback(get_state)#test http
#         data = resp.json()
#         if data["State"] != "login":
#             self.opState = 0
#         elif data["State"] == "login":
#             if self.opState == 0:
#                 self.opState = 1
#             elif self.opState == 1:
            for x in range(len(intent_message["slots"])):
                if intent_message["slots"][x]["slotName"] == "action":
                    action = list(map(lambda x: str(x), intent_message["slots"][x]["value"].values()))
                    action = action[1:]
            if any(x in action for x in ["take" , "issue" , "dispense" , "withdraw" , 'give', 'get', 'filter']):
                self.opState = 2
                self.operation = 1
                self.state = 0 # bypass: skip publish and wait response
                #kiosk.mqtt.publish("voice/issue/start","check_item_availability")
#                 resp = http_callback(post_operation)#test http
#                 itemListHttp = resp.json()
#             elif "return" in action:
#                 #print("return action")
#                 #kiosk.mqtt.publish("voice/return/start","1")
#                 self.operation = 2
#             elif "locate" in action:
#                 #print("locate action")
#                 #kiosk.mqtt.publish("voice/locate/start","1")
#                 self.operation = 3
#             elif "admin" in action:
#                 #print("admin action")
#                 #kiosk.mqtt.publish("voice/admin/start","1")
#                 self.operation = 4
            else:
                pass
            dialogue =  str(action) + " operation is selected. "
            self.lastDialogue = dialogue
#             else:
#                 pass
#         else:
#             pass

    def on_message(self, client, userdata, intent_message):
#         print("func::on message")
        nlu_payload = json.loads(intent_message.payload)
#         print("-----intent_msg:",intent_message)
#         print("intent_msg-payload:",intent_message.payload)
#         print("nlu:",json.dumps(nlu_payload,indent=4))
#         print('topic:',intent_message.topic)
#         print('qos:',intent_message.qos)
#         print('retain flag:',intent_message.retain)
        if intent_message.topic == "machine/hotword/on":
            if nlu_payload['mqtt_msg'] == '1':
                kiosk.mqtt.publish("hermes/hotword/toggleOn", json.dumps({"siteId": "default"}))
                led1.on()
                led2.on()
            else:
                kiosk.mqtt.publish("hermes/hotword/toggleOff", json.dumps({"siteId": "default"}))
                led1.off()
                led2.off()
        elif intent_message.topic =='hermes/asr/textCaptured':
            self.likelihood = nlu_payload['likelihood']
            self.asr_text = nlu_payload['text']
#             print('asr text:',self.asr_text)
            if nlu_payload['likelihood'] <= LIKELIHOOD:
                if self.attempt > 2:
                    self.lastDialogue = " Unrecognised command. Session ended. "
                    kiosk.mqtt.publish("hermes/dialogueManager/endSession", json.dumps({"sessionId": nlu_payload["sessionId"], "text": self.lastDialogue}))
                    self.attempt = 0
                else:
                    print('likelihood less:',nlu_payload['likelihood'])
                    self.lastDialogue = " I did not get that. Please repeat. "
                    print("TTS:", self.lastDialogue)
                    kiosk.mqtt.publish("hermes/dialogueManager/continueSession", json.dumps({"sessionId": nlu_payload["sessionId"], "text": self.lastDialogue}))
                    self.attempt += 1
                    print('retry attempt:', self.attempt)
            else:
                if 'unk' in nlu_payload['text']:
                    print('unk detected')
                    self.lastDialogue = " I did not get that. Please repeat. "
                    print("TTS unk:", self.lastDialogue)
                    kiosk.mqtt.publish("hermes/dialogueManager/continueSession", json.dumps({"sessionId": nlu_payload["sessionId"], "text": self.lastDialogue}))
                    self.attempt += 1
#         elif intent_message.topic == "hermes/nlu/intentNotRecognized":
#             print("Recognition failure ")
#             self.lastDialogue += "I did not get that. Please repeat. "
#             print("TTS:", self.lastDialogue)
#             kiosk.mqtt.publish("hermes/dialogueManager/continueSession", json.dumps({"sessionId": nlu_payload["sessionId"], "text": 'continue. '}))
        elif intent_message.topic == "hermes/intent/GetActionsItems":
#             print('enter, likelihood:', self.likelihood)
#             print('asr:',self.asr_text)
#             print('nlu',nlu_payload['rawInput'])
            if self.asr_text == nlu_payload['rawInput'] and self.likelihood > LIKELIHOOD:
#                 print('before enter',nlu_payload)
                print("Got intent k::", nlu_payload["intent"]["intentName"])
                self.getActions(nlu_payload)
            else:
#                 print('pass')
                pass
        else:
            pass

        if self.asr_text == nlu_payload.get('rawInput') and self.likelihood > LIKELIHOOD and self.operation == 1: #Issue operation
#             print("kiosk.urentorder issue:", kiosk.currentOrder)
            self.attempt = 0 #reset the attempt
            if not kiosk.currentOrder:
                self.newOrder()
                kiosk.currentOrder[-1].order_intent_callback(intent_message)
            elif (kiosk.currentOrder[-1].state > 6):
                self.newOrder()
                kiosk.currentOrder[-1].order_intent_callback(intent_message)
            else:
                kiosk.currentOrder[-1].order_intent_callback(intent_message)
        else:
            pass

    def opStateSpace(self, intent_message):
        print("func::operation statespace")
        if self.opState == 0:
            self.lastDialogue = "Please swipe your card."
            print("TTS:", self.lastDialogue)
            kiosk.mqtt.publish("hermes/tts/say", json.dumps({"text": self.lastDialogue, "siteId": intent_message["siteId"]}))
        elif self.opState == 1: #card swiped
            self.lastDialogue += "Please choose your operation."
            print("TTS:", self.lastDialogue)
            kiosk.mqtt.publish("hermes/dialogueManager/continueSession", json.dumps({"sessionId": intent_message["sessionId"], "text": self.lastDialogue}))
        elif self.opState == 2: #operation selected, select item
            self.lastDialogue += "Please specify your item. "
            print("TTS:", self.lastDialogue)
            kiosk.mqtt.publish("hermes/dialogueManager/continueSession", json.dumps({"sessionId": intent_message["sessionId"], "text": self.lastDialogue}))
        else:
            pass

if __name__ == "__main__":
    kiosk()
