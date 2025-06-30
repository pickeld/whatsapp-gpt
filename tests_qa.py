from time import sleep
import requests


conversation = [
    "?? Hi, my name is David",
    "?? What is my name?",
    "?? i was born on 9th of February 1986",
    "?? What is my birth date?",
    "?? What is my age?",
    "?? My kids are called Mia and Ben",
    "?? What are my kids names?",
]



for sentence in conversation:
    print(f"Sending: {sentence}")
    response = requests.post(
        "http://localhost:5002/webhook",
        json={
            "payload":
                {
                    "fromMe": True,
                    "body":sentence,
                    "to": "120363401685799472@g.us",
                }
                
        }
    )
    print(f"Response: {response.status_code} - {response.text}")
    sleep(1)  # Sleep to avoid overwhelming the server
    