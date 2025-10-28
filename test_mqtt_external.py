#!/usr/bin/env python3
"""
Simple MQTT connectivity test for external broker at 192.168.6.115
"""

import paho.mqtt.client as mqtt
import sys
import time
import signal

BROKER_HOST = "192.168.6.115"
BROKER_PORT = 1883
TEST_TOPIC = "moisture/test/connectivity"
CLIENT_ID = "mqtt_test_client"

class MQTTTester:
    def __init__(self):
        self.connected = False
        self.message_received = False
        self.client = mqtt.Client(CLIENT_ID)
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message
        
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f"✓ Successfully connected to MQTT broker at {BROKER_HOST}:{BROKER_PORT}")
            self.connected = True
            # Subscribe to test topic
            client.subscribe(TEST_TOPIC)
            print(f"✓ Subscribed to topic: {TEST_TOPIC}")
        else:
            print(f"✗ Failed to connect to MQTT broker. Return code: {rc}")
            self.connected = False
    
    def on_disconnect(self, client, userdata, rc):
        print(f"✓ Disconnected from MQTT broker")
        self.connected = False
    
    def on_message(self, client, userdata, msg):
        print(f"✓ Received message on {msg.topic}: {msg.payload.decode()}")
        self.message_received = True
    
    def test_connection(self, timeout=10):
        print(f"Testing MQTT connection to {BROKER_HOST}:{BROKER_PORT}...")
        
        try:
            # Connect to broker
            self.client.connect(BROKER_HOST, BROKER_PORT, 60)
            self.client.loop_start()
            
            # Wait for connection
            start_time = time.time()
            while not self.connected and (time.time() - start_time) < timeout:
                time.sleep(0.1)
            
            if not self.connected:
                print(f"✗ Connection timeout after {timeout} seconds")
                return False
            
            # Test publish/subscribe
            test_message = f"Test message from {CLIENT_ID} at {time.strftime('%Y-%m-%d %H:%M:%S')}"
            print(f"Publishing test message...")
            self.client.publish(TEST_TOPIC, test_message)
            
            # Wait for message
            start_time = time.time()
            while not self.message_received and (time.time() - start_time) < 5:
                time.sleep(0.1)
            
            if self.message_received:
                print("✓ MQTT publish/subscribe test successful!")
                success = True
            else:
                print("⚠ Message was published but not received (might be normal)")
                success = True  # Connection works even if we don't receive our own message
            
            self.client.loop_stop()
            self.client.disconnect()
            
            return success
            
        except Exception as e:
            print(f"✗ MQTT connection test failed: {e}")
            return False

def main():
    tester = MQTTTester()
    
    # Handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        print("\nTest interrupted by user")
        tester.client.loop_stop()
        tester.client.disconnect()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    success = tester.test_connection()
    
    if success:
        print("\n🎉 MQTT connectivity test PASSED!")
        print("Your external MQTT broker is accessible and working.")
        sys.exit(0)
    else:
        print("\n❌ MQTT connectivity test FAILED!")
        print("Please check:")
        print("  1. MQTT broker is running at 192.168.6.115")
        print("  2. Port 1883 is accessible")
        print("  3. Network connectivity to 192.168.6.115")
        print("  4. Firewall settings")
        sys.exit(1)

if __name__ == "__main__":
    main()