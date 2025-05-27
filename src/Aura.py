import subprocess
import os
import sys
import platform
from dotenv import load_dotenv
from openai import OpenAI
import pyttsx3
import speech_recognition as sr
from datetime import date
import time
import webbrowser
import datetime
from threading import Thread
import urllib.parse
import app
import Gesture_Controller

load_dotenv()

# Initialize OpenAI client
client = OpenAI()
conversation_history = [
    {"role": "system", "content": "You are a concise assistant. Respond in 1-2 lines (max 10 words) unless the user asks for details."}
]

def get_conversational_response(user_input):
    conversation_history.append({"role": "user", "content": user_input})
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=conversation_history,
            max_tokens=30,
            temperature=0.7,
            store=True
        )
        assistant_reply = completion.choices[0].message.content.strip()
        conversation_history.append({"role": "assistant", "content": assistant_reply})
        return assistant_reply
    except Exception as e:
        print("ChatGPT API Error:", e)
        return "I'm sorry, I couldn't process that."

# Voice engine
engine = pyttsx3.init()
voices = engine.getProperty('voices')
engine.setProperty('voice', voices[1].id)
engine.setProperty('rate', 190)
engine.setProperty('volume', 0.7)

# Recognizer
r = sr.Recognizer()
with sr.Microphone() as source:
    r.energy_threshold = 500 
    r.dynamic_energy_threshold = False

# OS-safe keyboard controller
keyboard = None
if platform.system() != "Linux":
    try:
        from pynput.keyboard import Key, Controller
        keyboard = Controller()
    except ImportError:
        keyboard = None

# Variables
today = date.today()
file_exp_status = False
files = []
path = ''
is_awake = True
contacts = {
    "sagar": "916392608363",
    "mummy": "918840357683",
    "nikhar": "919516859446"
}

# Functions
def reply(audio):
    app.ChatBot.addAppMsg(audio)
    print(audio)
    engine.say(audio)
    engine.runAndWait()

def wish():
    hour = int(datetime.datetime.now().hour)
    if hour < 12:
        reply("Good Morning!")
    elif hour < 18:
        reply("Good Afternoon!")
    else:
        reply("Good Evening!")
    reply("I am Aura, how may I help you?")

def record_audio():
    with sr.Microphone() as source:
        r.pause_threshold = 0.8
        voice_data = ''
        audio = r.listen(source, phrase_time_limit=5)
        try:
            voice_data = r.recognize_google(audio)
        except sr.RequestError:
            reply('Sorry, check your Internet connection')
        except sr.UnknownValueError:
            print('Unrecognized speech')
            pass
        return voice_data.lower()

def open_calculator():
    try:
        subprocess.Popen('calc.exe')
        reply("Opening calculator.")
    except Exception:
        reply("I couldn't open the calculator.")

def open_calendar():
    try:
        webbrowser.open("https://calendar.google.com")
        reply("Opening Google Calendar.")
    except Exception:
        reply("I couldn't open the calendar.")

def open_whatsapp_chat(contact_name):
    contact_name = contact_name.lower().strip()
    if contact_name in contacts:
        phone = contacts[contact_name]
        url = f"https://wa.me/{phone}"
        try:
            webbrowser.open(url)
            reply(f"Opening WhatsApp chat with {contact_name}.")
        except Exception:
            reply("I couldn't open the chat.")
    else:
        reply(f"No contact info for {contact_name}.")

def respond(voice_data):
    global file_exp_status, files, is_awake, path
    print(voice_data)
    voice_data = voice_data.replace('aura', '').strip()
    app.eel.addUserMsg(voice_data)

    if not is_awake:
        if 'wake up' in voice_data:
            is_awake = True
            wish()

    elif 'hello' in voice_data:
        wish()

    elif 'what is your name' in voice_data:
        reply('My name is Aura!')

    elif 'date' in voice_data:
        reply(today.strftime("%B %d, %Y"))

    elif 'time' in voice_data:
        reply(str(datetime.datetime.now()).split(" ")[1].split('.')[0])

    elif 'search' in voice_data:
        query = voice_data.split('search')[-1].strip()
        reply(f'Searching for {query}')
        url = f'https://google.com/search?q={query}'
        try:
            webbrowser.open(url)
            reply('This is what I found')
        except:
            reply('Please check your Internet')

    elif 'location' in voice_data:
        reply('Which place are you looking for?')
        temp_audio = record_audio()
        if temp_audio:
            encoded_location = urllib.parse.quote(temp_audio)
            url = f'https://www.google.com/maps/place/{encoded_location}'
            try:
                webbrowser.open(url)
                reply(f'This is what I found for "{temp_audio}"')
            except:
                reply('Error opening location. Check your internet.')
        else:
            reply('I couldn’t understand the location.')

    elif 'copy' in voice_data and keyboard:
        with keyboard.pressed(Key.ctrl):
            keyboard.press('c')
            keyboard.release('c')
        reply('Copied')
    elif 'undo' in voice_data and keyboard:
        with keyboard.pressed(Key.ctrl):
            keyboard.press('z')
            keyboard.release('z')
        reply('Reversed the changes')
    elif ('paste' in voice_data or 'pest' in voice_data or 'page' in voice_data) and keyboard:
        with keyboard.pressed(Key.ctrl):
            keyboard.press('v')
            keyboard.release('v')
        reply('Pasted')
    elif ('copy' in voice_data or 'undo' in voice_data or 'paste' in voice_data) and not keyboard:
        reply("Keyboard control not supported on this platform.")

    elif 'list' in voice_data:
        counter = 0
        path = 'C://'
        files = os.listdir(path)
        filestr = ""
        for f in files:
            counter += 1
            print(f"{counter}:  {f}")
            filestr += f"{counter}:  {f}<br>"
        file_exp_status = True
        reply('Files in root directory:')
        app.ChatBot.addAppMsg(filestr)

    elif file_exp_status:
        counter = 0
        if 'open' in voice_data:
            try:
                file_index = int(voice_data.split(' ')[-1]) - 1
                target_path = os.path.join(path, files[file_index])
                if os.path.isfile(target_path):
                    os.startfile(target_path)
                else:
                    path = os.path.join(path, files[file_index]) + '//'
                    files = os.listdir(path)
                    filestr = ""
                    for f in files:
                        counter += 1
                        filestr += f"{counter}:  {f}<br>"
                    reply('Opened Successfully')
                    app.ChatBot.addAppMsg(filestr)
            except:
                reply("Invalid number or path error.")
        elif 'back' in voice_data:
            if path == 'C://':
                reply('Root directory reached')
            else:
                path = '//'.join(path.split('//')[:-2]) + '//'
                files = os.listdir(path)
                filestr = ""
                for f in files:
                    counter += 1
                    filestr += f"{counter}:  {f}<br>"
                reply('Moved back')
                app.ChatBot.addAppMsg(filestr)
        elif 'close' in voice_data:
            file_exp_status = False
            reply("File explorer closed.")

    elif 'open calculator' in voice_data:
        open_calculator()

    elif 'open calendar' in voice_data:
        open_calendar()

    elif 'open whatsapp chat' in voice_data:
        if "of" in voice_data:
            open_whatsapp_chat(voice_data.split("of")[-1].strip())
        elif "for" in voice_data:
            open_whatsapp_chat(voice_data.split("for")[-1].strip())
        else:
            reply("Please specify the contact name.")

    elif 'launch gesture recognition' in voice_data:
        if Gesture_Controller.GestureController.gc_mode:
            reply('Gesture recognition is already active')
        else:
            gc = Gesture_Controller.GestureController()
            t = Thread(target=gc.start)
            t.start()
            reply('Launched Successfully')

    elif 'stop gesture recognition' in voice_data:
        if Gesture_Controller.GestureController.gc_mode:
            Gesture_Controller.GestureController.gc_mode = 0
            reply('Gesture recognition stopped')
        else:
            reply('Gesture recognition is already inactive')

    elif 'bye' in voice_data or 'sleep' in voice_data:
        reply("Good bye! Have a nice day.")
        is_awake = False

    elif 'exit' in voice_data or 'terminate' in voice_data:
        app.ChatBot.close()
        sys.exit()

    else:
        response = get_conversational_response(voice_data)
        reply(response)

# --- Main Driver ---
t1 = Thread(target=app.ChatBot.start)
t1.start()

while not app.ChatBot.started:
    time.sleep(0.5)

wish()
while True:
    if app.ChatBot.isUserInput():
        voice_data = app.ChatBot.popUserInput()
    else:
        voice_data = record_audio()

    if 'aura' in voice_data:
        try:
            respond(voice_data)
        except SystemExit:
            reply("Exit Successful")
            break
        except Exception as e:
            print("Exception raised while closing:", e)
            break
