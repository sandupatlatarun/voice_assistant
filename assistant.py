import os
import re
import time
import threading
import webbrowser
from datetime import datetime
from urllib.parse import quote_plus

import requests
import pyttsx3
import speech_recognition as sr
from dotenv import load_dotenv


# ============================================================
# CONFIGURATION
# ============================================================

load_dotenv()

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")


# ============================================================
# TEXT TO SPEECH
# ============================================================

engine = pyttsx3.init()

engine.setProperty("rate", 165)
engine.setProperty("volume", 1.0)


def speak(text):
    """Print text and speak it aloud."""

    print("Assistant:", text)

    engine.say(text)
    engine.runAndWait()


# ============================================================
# SPEECH RECOGNITION
# ============================================================

recognizer = sr.Recognizer()


def listen():
    """Listen through the microphone and convert speech to text."""

    try:

        with sr.Microphone() as source:

            print("\nListening...")

            recognizer.adjust_for_ambient_noise(
                source,
                duration=0.5
            )

            audio = recognizer.listen(
                source,
                timeout=5,
                phrase_time_limit=10
            )

        print("Recognizing...")

        command = recognizer.recognize_google(
            audio,
            language="en-IN"
        )

        print("You:", command)

        return command.lower().strip()

    except sr.WaitTimeoutError:

        speak(
            "I didn't hear anything. Please try again."
        )

        return ""

    except sr.UnknownValueError:

        speak(
            "Sorry, I couldn't understand you. "
            "Please repeat."
        )

        return ""

    except sr.RequestError:

        speak(
            "The speech recognition service is unavailable."
        )

        return ""

    except OSError:

        speak(
            "I cannot access your microphone. "
            "Please check your microphone."
        )

        return ""

    except Exception as error:

        print("Microphone error:", error)

        speak(
            "Something went wrong with the microphone."
        )

        return ""


# ============================================================
# INTENTS
# ============================================================

INTENTS = {

    "greeting": [
        "hello",
        "hi",
        "hey",
        "good morning",
        "good afternoon",
        "good evening"
    ],

    "time": [
        "what time",
        "current time",
        "tell me the time",
        "time right now",
        "what is the time",
        "what's the time"
    ],

    "date": [
        "what date",
        "today's date",
        "todays date",
        "current date",
        "what day is it",
        "what is today's date"
    ],

    "weather": [
        "weather",
        "temperature",
        "forecast"
    ],

    "reminder": [
        "remind me",
        "set a reminder",
        "reminder"
    ],

    "search": [
        "search for",
        "search",
        "google",
        "look up",
        "find information",
        "find out about"
    ],

    "exit": [
        "goodbye",
        "exit",
        "quit",
        "stop",
        "close assistant",
        "shut down"
    ]
}


# ============================================================
# INTENT CLASSIFICATION
# ============================================================

def classify_intent(command):
    """Determine the user's intended action."""

    scores = {}

    for intent, phrases in INTENTS.items():

        score = 0

        for phrase in phrases:

            if phrase in command:
                score += 1

        scores[intent] = score

    best_intent = max(
        scores,
        key=scores.get
    )

    if scores[best_intent] == 0:
        return "unknown"

    return best_intent


# ============================================================
# TIME
# ============================================================

def tell_time():

    current_time = datetime.now().strftime(
        "%I:%M %p"
    )

    speak(
        f"The current time is {current_time}."
    )


# ============================================================
# DATE
# ============================================================

def tell_date():

    current_date = datetime.now().strftime(
        "%A, %B %d, %Y"
    )

    speak(
        f"Today is {current_date}."
    )


# ============================================================
# WEB SEARCH
# ============================================================

def search_web(command):

    prefixes = [
        "search for",
        "search",
        "google",
        "look up",
        "find information",
        "find out about"
    ]

    topic = command

    for prefix in prefixes:

        if topic.startswith(prefix):

            topic = topic[
                len(prefix):
            ].strip()

            break

    if not topic:

        speak(
            "What would you like me to search for?"
        )

        topic = listen()

    if not topic:
        return

    speak(
        f"Searching for {topic}."
    )

    url = (
        "https://www.google.com/search?q="
        + quote_plus(topic)
    )

    webbrowser.open(url)


# ============================================================
# WEATHER
# ============================================================

def get_weather(city):

    if not OPENWEATHER_API_KEY:

        speak(
            "The weather API key is not configured."
        )

        return

    url = (
        "https://api.openweathermap.org/data/2.5/weather"
    )

    params = {
        "q": city,
        "appid": OPENWEATHER_API_KEY,
        "units": "metric"
    }

    try:

        response = requests.get(
            url,
            params=params,
            timeout=10
        )

        response.raise_for_status()

        data = response.json()

        temperature = data["main"]["temp"]

        humidity = data["main"]["humidity"]

        description = data["weather"][0]["description"]

        location = data.get(
            "name",
            city
        )

        speak(
            f"The weather in {location} is "
            f"{description}. "
            f"The temperature is "
            f"{temperature:.1f} degrees Celsius. "
            f"Humidity is {humidity} percent."
        )

    except requests.HTTPError as error:

        print("Weather HTTP error:", error)

        if response.status_code == 401:

            speak(
                "The weather API key is invalid "
                "or not activated yet."
            )

        elif response.status_code == 404:

            speak(
                f"I couldn't find the city {city}."
            )

        else:

            speak(
                "The weather service returned an error."
            )

    except requests.RequestException as error:

        print("Weather request error:", error)

        speak(
            "Sorry, I could not get the weather right now."
        )

    except (KeyError, ValueError) as error:

        print("Weather data error:", error)

        speak(
            "I received an unexpected weather response."
        )


# ============================================================
# EXTRACT CITY FROM WEATHER COMMAND
# ============================================================

def extract_city(command):

    phrases = [
        "weather in",
        "temperature in",
        "forecast in",
        "weather at",
        "temperature at",
        "forecast at"
    ]

    for phrase in phrases:

        if phrase in command:

            city = command.split(
                phrase,
                1
            )[1].strip()

            return city

    return ""


# ============================================================
# REMINDER
# ============================================================

def set_reminder(seconds, message):
    """Create a background reminder."""

    def reminder():

        time.sleep(seconds)

        speak(
            f"Reminder: {message}"
        )

    thread = threading.Thread(
        target=reminder,
        daemon=True
    )

    thread.start()

    if seconds < 60:

        duration = f"{seconds} seconds"

    elif seconds < 3600:

        minutes = seconds // 60

        duration = f"{minutes} minutes"

    else:

        hours = seconds // 3600

        duration = f"{hours} hours"

    speak(
        f"Okay. I will remind you in {duration}."
    )


# ============================================================
# CREATE REMINDER
# ============================================================

def create_reminder(command):

    pattern = (
        r"remind me in "
        r"(\d+)\s*"
        r"(seconds?|minutes?|hours?)"
    )

    match = re.search(
        pattern,
        command
    )

    if not match:

        speak(
            "Please say something like "
            "remind me in 10 seconds."
        )

        return

    amount = int(
        match.group(1)
    )

    unit = match.group(2)

    if "second" in unit:

        seconds = amount

    elif "minute" in unit:

        seconds = amount * 60

    else:

        seconds = amount * 60 * 60

    message = re.sub(
        pattern,
        "",
        command
    ).strip()

    if not message:

        message = "This is your reminder."

    set_reminder(
        seconds,
        message
    )


# ============================================================
# PROCESS COMMAND
# ============================================================

def process_command(command):

    intent = classify_intent(command)

    print(
        "Detected intent:",
        intent
    )

    # --------------------------------------------------------
    # GREETING
    # --------------------------------------------------------

    if intent == "greeting":

        speak(
            "Hello! How can I help you?"
        )

    # --------------------------------------------------------
    # TIME
    # --------------------------------------------------------

    elif intent == "time":

        tell_time()

    # --------------------------------------------------------
    # DATE
    # --------------------------------------------------------

    elif intent == "date":

        tell_date()

    # --------------------------------------------------------
    # WEATHER
    # --------------------------------------------------------

    elif intent == "weather":

        city = extract_city(
            command
        )

        if not city:

            speak(
                "Which city would you like "
                "the weather for?"
            )

            city = listen()

        if city:

            get_weather(city)

    # --------------------------------------------------------
    # REMINDER
    # --------------------------------------------------------

    elif intent == "reminder":

        create_reminder(command)

    # --------------------------------------------------------
    # WEB SEARCH
    # --------------------------------------------------------

    elif intent == "search":

        search_web(command)

    # --------------------------------------------------------
    # EXIT
    # --------------------------------------------------------

    elif intent == "exit":

        speak(
            "Goodbye! Have a great day."
        )

        return False

    # --------------------------------------------------------
    # UNKNOWN COMMAND
    # --------------------------------------------------------

    else:

        speak(
            "I don't understand that request yet. "
            "Please try another command."
        )

    return True


# ============================================================
# MAIN
# ============================================================

def main():

    speak(
        "Voice assistant started. "
        "How can I help you?"
    )

    while True:

        command = listen()

        if not command:
            continue

        should_continue = process_command(
            command
        )

        if not should_continue:
            break


# ============================================================
# START PROGRAM
# ============================================================

if __name__ == "__main__":

    main()
