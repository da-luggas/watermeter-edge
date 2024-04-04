# Turn your old smartphone into a smart water meter for Home Assistant
The Home Assistant Energy Dashboard provides valuable insights into energy consumption patterns that can help reduce the household's energy usage. While the same is possible for water consumption, smart water meters are rare to find or ancient meters impossible to replace.

This project provides a flexible solution to repurpose old electronics to bring the analog water (or gas) meters into the smart, connected world.

## How It Works
The project is divided into two parts: Capture and Inference

**1. Capture**

We use an old Android smartphone and the free [IP Webcam](https://play.google.com/store/apps/details?id=com.pas.webcam) app that exposes the most recent camera image in the local network under `http://<ip-of-phone>:8080/photaf.jpg`. This endpoint provides a simple interface to retrieve image readings of the water meter and processing it using computer vision.

**2. Inference**

Inference is done on a second device running Docker. Correctly configured, it uses TensorFlow Lite and OpenCV to process the image and turn it into a number. After that, we are using MQTT to send the reading to Home Assistant.

# Installation
## Preparing the phone

1. Install the IP Webcam app
2. Adjust the settings to your likings, I recommend changing the following:

    Video Preferences
    - **Focus mode**: macro, manual
    - **Flash mode**: Always use flash

    Power Management
    - **Deactivate display**: on
    - **Keep screen active**: on
    - **Shallow sleep**: on

    Optional Permissions
    - **Allow streaming in background**: on
3. Mount the phone above the water meter to get a birds-eye view image (Position must not change!)
4. Press "Start Stream" in the app, activate the flash and set the focus point once

## Finding the Region Of Interest (ROI)
Next, we need to determine the coordinates of the pictures that are relevant for the neural networks. Each digit or analog gauge is a region. For now, I recommend downloading a sample image at `http://<ip-of-phone>:8080/photaf.jpg` and then using [Image Map Generator](https://www.image-map.net) to map the regions of interest.

## Running the backend
You need a system running docker, like unRAID or the Linux system your Home Assistant installation is running.

1. Create a configuration file `config.json` in a directory of your choice
    
    Paste the code of the example config file:
    ```json
    {
        "general": {
            "initial_value": 786.222, // current reading of the water meter during installation
            "max_flow": 1 // maximum change possible from one reading to the next
        },
        "mqtt": {
            "ip": "192.168.1.5", // ip of mqtt broker
            "port": 1883, // port of mqtt broker
            "topic": "water-meter/reading", // mqtt topic
            "interval": 10 // interval between readings (min)
        },
        "webcam": {
            "ip": "192.168.1.176", // ip of IP Webcam (phone)
            "port": "8080" // port of IP Webcam (phone)
        },
        "bounding_boxes": { // coordinates of region of interest

            // analog gauges
            "analog": [
                [2957,812,3945,1783],
                [2622,1950,3626,2961]
            ],

            // digits
            "digital": [
                [633,196,880,601],
                [1108,196,1355,595],
                [1576,190,1836,589],
                [2058,190,2305,601],
                [2533,177,2786,595]
            ]
        }
    }
    ```
2. Run the docker container:
    ```bash
    docker run -d --name watermeter-edge -v /path/to/config:/watermeter/config -e MQTT_USER=<USER> -e MQTT_PW=<PW> daluggas/watermeter-edge:latest
    ```

    Make sure to change the path to your config file on your system and to set the MQTT broker username and password.

## Integrating into Home Assistant
Edit your `configuration.yaml` to add a MQTT sensor:

```yaml
mqtt:
  sensor:
    - state_topic: watermeter/reading
      name: Water Meter
      unique_id: watermeter
      unit_of_measurement: m³
      device_class: water
      state_class: total
```
Again, make sure to change the entity and MQTT topic names

## Credits

This project is in big parts based and made possible by the amazing [AI-on-the-edge](https://github.com/jomjol/AI-on-the-edge-device) project, which also provides the pretrained model weights for this Docker container.

Definitely check out the work if you want a more streamlined all-in-one device for reading your meter values or if you don't have an old phone lying around.

## Planned features
- Webserver interface for easy configuration of the regions of interest
- Automatic collection of training samples to improve model performance
- Better value correction logic