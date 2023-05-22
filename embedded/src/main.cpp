#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
//#include "env.h"
#include <OneWire.h>
#include <DallasTemperature.h>


#define ONE_WIRE_BUS 4
OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature sensors(&oneWire);	

const int fan = 2;
const int light = 3;
const int PIR = 5;
int pir_state;



void setup() {
  sensors.begin();
  Serial.begin(9600);
  pinMode(fan, OUTPUT);
  pinMode(light, OUTPUT);
  pinMode(PIR,INPUT);
  pinMode(ONE_WIRE_BUS,INPUT);

  WiFi.begin(WIFI_SSID, WIFI_CODE);
  Serial.println("Connecting");
  while(WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("The Bluetooth Device is Ready to Pair");
  Serial.println("Connected @");
  Serial.print(WiFi.localIP());
}


void loop() {

//READ TEMPERATURE
// Send the command to get temperatures
  sensors.requestTemperatures(); 

  //print the temperature in Celsius
  Serial.print("Temperature: ");
  float temp = sensors.getTempCByIndex(0);
  temp = sensors.getTempCByIndex(0);
  Serial.print(temp);
  Serial.print((char)176);//shows degrees character
  Serial.print("C "); 
  pir_state = digitalRead(PIR);
  Serial.print("");
  Serial.print(pir_state);
  Serial.println("");
  
//POST Request
  if(WiFi.status()== WL_CONNECTED){   
    
    HTTPClient http;
    String http_response;

    //POST REQUEST
    http.begin(endpoint);
    http.addHeader("Content-Type", "application/json");

    StaticJsonDocument<1024> doc; // Empty JSONDocument
    String httpRequestData; // Emtpy string to be used to store HTTP request data string
    
    doc["temperature"]=temp;
    doc["presence"]=!pirstate;
    serializeJson(doc, httpRequestData);

    int POSTResponseCode = http.POST(httpRequestData);


    if (POSTResponseCode>0) {
        Serial.print("Response:");
        Serial.print(POSTResponseCode);}

    else {
        Serial.print("Error: ");


        Serial.println(POSTResponseCode);}
      
      http.end();
      
    //GET REQUEST
    http.begin(endpoint);
  

    int httpResponseCode = http.GET();


    if (httpResponseCode>0) {
        Serial.print("Response:");
        Serial.print(httpResponseCode);
        http_response = http.getString();
        Serial.println(http_response);}
      else {
        Serial.print("Error: ");
        Serial.println(httpResponseCode);}
      http.end();

      
      StaticJsonDocument<1024> doc1;
      DeserializationError error = deserializeJson(doc1, http_response);

      if (error) 
      { Serial.print("deserializeJson() failed:");
        Serial.println(error.c_str());
        return;}
      
      bool light_state = doc1["light"];
      bool fan_state = doc1["fan"];
  
  
      Serial.println("Light:");
      Serial.println(light_state);
      Serial.println("Fan:");
      Serial.println(fan_state);

      digitalWrite(fan, fan_state);
      digitalWrite(light,light_state);
      
      Serial.println("Looks like its working");
      
      delay(1000);   
  }
  
  else {Serial.println("Not Connected");}

}
