import tflite_runtime.interpreter as tflite
import cv2
import numpy as np
import paho.mqtt.client as mqtt
import os
import time
from time import sleep
import json
import urllib

class MeterReader():
    def __init__(self, config):
        self.last_reading = config['general']['initial_value']
        self.max_flow = config['general']['max_flow']
        self.digital_boxes = config['bounding_boxes']['digital']
        self.analog_boxes = config['bounding_boxes']['analog']

        self.model_digital = tflite.Interpreter('dig-cont_0700_s3_q.tflite')
        self.model_analog = tflite.Interpreter('ana-class100_0171_s1_q.tflite')

    def predict(self, image):
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        digital_part = self.__predict_analog(image)
        analog_part = self.__predict_digital(image)

        total = digital_part + analog_part
        if not self.__is_plausible_value(total):
            print(f"New value of {total} seems not plausible.")
            return self.last_reading

        self.last_reading = total
        return total
    
    def __is_plausible_value(self, reading):
        return (reading >= self.last_reading) & (abs(reading - self.last_reading) < self.max_flow)

    def __predict_analog(self, image):
        self.model_analog.allocate_tensors()

        result = 0
        multiplier = 0.1

        for idx, (x1, y1, x2, y2) in enumerate(self.analog_boxes):
            roi = image[y1:y2, x1:x2]
            resized_roi = cv2.resize(roi, (32, 32))
            img_array = resized_roi.astype('float32')
            img_array = np.expand_dims(img_array, axis=0)

            input_details = self.model_analog.get_input_details()
            output_details = self.model_analog.get_output_details()
            self.model_analog.set_tensor(input_details[0]['index'], img_array)
            self.model_analog.invoke()
            logits = self.model_analog.get_tensor(output_details[0]['index'])

            prediction = np.argmax(logits)
            if idx == len(self.analog_boxes) - 1:
                digit = prediction / 10 * multiplier
            else:
                digit = int(prediction / 10) * multiplier

            multiplier /= 10
            result += digit

        return result

    def __predict_digital(self, image):
        self.model_digital.allocate_tensors()

        result = 0
        position = 10 ** (len(self.digital_boxes) - 1)

        for idx, (x1, y1, x2, y2) in enumerate(self.digital_boxes):
            roi = image[y1:y2, x1:x2]
            resized_roi = cv2.resize(roi, (20, 32))
            # if idx == len(self.digital_boxes) - 1:
            #     cv2.imwrite(f"./training_data/{time.time()}.jpg", resized_roi)

            img_array = resized_roi.astype('float32')
            img_array = np.expand_dims(img_array, axis=0)

            input_details = self.model_digital.get_input_details()
            output_details = self.model_digital.get_output_details()
            self.model_digital.set_tensor(input_details[0]['index'], img_array)
            self.model_digital.invoke()
            logits = self.model_digital.get_tensor(output_details[0]['index'])
            prediction = np.argmax(logits)
            digit = prediction
            result += digit * position
            position /= 10

        return result
    
class MQTTHandler():
    def __init__(self, config):
        self.ip = config["mqtt"]["ip"]
        self.port = config["mqtt"]["port"]
        self.topic = config["mqtt"]["topic"]

        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.username_pw_set(os.getenv("MQTT_USER"), os.getenv("MQTT_PW"))

    def send(self, message):
        self.client.connect(self.ip, port=self.port)
        self.client.publish(self.topic, message)
        self.client.disconnect()

if __name__ == "__main__":
    with open("config/config.json", 'r') as file:
        config = json.load(file)

    WEBCAM = "http://" + config['webcam']['ip'] + ":" + config['webcam']['port'] + "/photoaf.jpg"
    INTERVAL = int(config['mqtt']['interval'] * 60)

    model = MeterReader(config)
    mqtt = MQTTHandler(config)

    while(True):
        try:
            req = urllib.request.urlopen(WEBCAM)
            arr = np.asarray(bytearray(req.read()), dtype=np.uint8)
            image = cv2.imdecode(arr, -1)

            reading = model.predict(image)
            print(f"Sending reading: {reading}")
            
            mqtt.send(str(reading))

        except Exception as e:
            print(f"An error occurred: {e}.")
            print("Retrying in 60s...")
            sleep(60)

        sleep(INTERVAL)