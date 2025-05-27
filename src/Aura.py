
import subprocess

import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.getenv("API_KEY"))
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

import pyttsx3
import speech_recognition as sr
from datetime import date
import time
import webbrowser
import datetime
from pynput.keyboard import Key, Controller
import sys
import os
from os import listdir
from os.path import isfile, join
import app
from threading import Thread
import urllib.parse
import Gesture_Controller


# -------------Object Initialization---------------
today = date.today()
r = sr.Recognizer()
keyboard = Controller()
engine = pyttsx3.init('sapi5')
engine = pyttsx3.init()
voices = engine.getProperty('voices')
engine.setProperty('voice', voices[1].id)

engine.setProperty('rate', 190)   # default= 200
engine.setProperty('volume', 0.7) # max = 1

# ----------------Variables------------------------
file_exp_status = False
files =[]
path = ''
is_awake = True  #Bot status

# ------------------Functions----------------------
def reply(audio):
    app.ChatBot.addAppMsg(audio)

    print(audio)
    engine.say(audio)
    engine.runAndWait()

def wish():
    hour = int(datetime.datetime.now().hour)

    if hour>=0 and hour<12:
        reply("Good Morning!")
    elif hour>=12 and hour<18:
        reply("Good Afternoon!")   
    else:
        reply("Good Evening!")  
        
    reply("I am Aura, how may I help you?")

# Microphone parameters
with sr.Microphone() as source:
        r.energy_threshold = 500 
        r.dynamic_energy_threshold = False

# Audio to String
def record_audio():
    with sr.Microphone() as source:
        r.pause_threshold = 0.8
        voice_data = ''
        audio = r.listen(source, phrase_time_limit=5)

        try:
            voice_data = r.recognize_google(audio)
        except sr.RequestError:
            reply('Sorry my Service is down. Plz check your Internet connection')
        except sr.UnknownValueError:
            print('Can\'t recognize')
            pass
        return voice_data.lower()
    
def open_calculator():
    try:
        subprocess.Popen('calc.exe')
        reply("Opening calculator.")
    except Exception as e:
        reply("I couldn't open the calculator.")

def open_calendar():
    try:
        webbrowser.open("https://calendar.google.com")
        reply("Opening Google Calendar.")
    except Exception as e:
        reply("I couldn't open the calendar.")

# Mapping of contact names to phone numbers (with country code, without '+')
contacts = {
    "sagar": "916392608363",
    "mummy": "918840357683",
    "nikhar": "919516859446",
    # we can add more
}

def open_whatsapp_chat(contact_name):
    contact_name = contact_name.lower().strip()
    if contact_name in contacts:
        phone = contacts[contact_name]

        url = f"https://wa.me/{phone}"
        try:
            print("Opening URL:", url)
            webbrowser.open(url)
            reply(f"Opening WhatsApp chat with {contact_name}.")
        except Exception as e:
            reply("I couldn't open the chat.")
    else:
        reply(f"I don't have contact info for {contact_name}.")


# Executes Commands (input: string)
def respond(voice_data):
    global file_exp_status, files, is_awake, path
    print(voice_data)
    voice_data.replace('aura','').strip() 
    app.eel.addUserMsg(voice_data)

    if is_awake==False:
        if 'wake up' in voice_data:
            is_awake = True
            wish()

    # STATIC CONTROLS
    elif 'hello' in voice_data:
        wish()

    elif 'what is your name' in voice_data:
        reply('My name is Aura!')

    elif 'date' in voice_data:
        reply(today.strftime("%B %d, %Y"))

    elif 'time' in voice_data:
        reply(str(datetime.datetime.now()).split(" ")[1].split('.')[0])

    elif 'search' in voice_data:
        reply('Searching for ' + voice_data.split('search')[1])
        url = 'https://google.com/search?q=' + voice_data.split('search')[1]
        try:
            webbrowser.get().open(url)
            reply('This is what I found')
        except:
            reply('Please check your Internet')

    elif 'location' in voice_data:
        reply('Which place are you looking for?')
        temp_audio = record_audio()  
        
        if temp_audio:  
            reply('Locating...')
            temp_audio.replace('aura','').strip() 
            
            encoded_location = urllib.parse.quote(temp_audio)
            
            url = f'https://www.google.com/maps/place/{encoded_location}'
            
            try:
                webbrowser.open(url)
                reply(f'This is what I found for "{temp_audio}"')
            except Exception as e:
                reply('There was an error opening the location. Please check your internet connection.')
                print(str(e)) 
        else:
            reply('I couldn’t understand the location. Could you please repeat it?')
        
    elif 'copy' in voice_data:
        with keyboard.pressed(Key.ctrl):
            keyboard.press('c')
            keyboard.release('c')
        reply('Copied')
    
    elif 'undo' in voice_data:
        with keyboard.pressed(Key.ctrl):
            keyboard.press('z')
            keyboard.release('z')
        reply('reversed the changes')
          
    elif 'page' in voice_data or 'pest'  in voice_data or 'paste' in voice_data:
        with keyboard.pressed(Key.ctrl):
            keyboard.press('v')
            keyboard.release('v')
        reply('Pasted')
        
    elif 'list' in voice_data:
        counter = 0
        path = 'C://'
        files = listdir(path)
        filestr = ""
        for f in files:
            counter+=1
            print(str(counter) + ':  ' + f) 
            filestr += str(counter) + ':  ' + f + '<br>'
        file_exp_status = True
        reply('These are the files in your root directory')
        app.ChatBot.addAppMsg(filestr)
    
    elif file_exp_status == True:
        counter = 0   
        if 'open' in voice_data:
            last_word = voice_data.split(' ')[-1]
            if last_word.isdigit():
                file_index = int(last_word) - 1 
                try:
                    target_path = join(path, files[file_index])
                    if isfile(target_path):
                        os.startfile(target_path)
                    else:
                        path = path + files[file_index] + '//'
                        files = listdir(path)
                        filestr = ""
                        for f in files:
                            counter += 1
                            filestr += f"{counter}:  {f}<br>"
                            print(f"{counter}:  {f}")
                        reply('Opened Successfully')
                        app.ChatBot.addAppMsg(filestr)
                except IndexError:
                    reply("The number you provided is out of range. Please try again.")
            else:
                reply("Please provide a valid number after 'open'.")
        elif 'back' in voice_data:
            filestr = ""
            if path == 'C://':
                reply('Sorry, this is the root directory')
            else:
                a = path.split('//')[:-2]
                path = '//'.join(a) + '//'
                files = listdir(path)
                for f in files:
                    counter += 1
                    filestr += f"{counter}:  {f}<br>"
                    print(f"{counter}:  {f}")
                reply('ok')
                app.ChatBot.addAppMsg(filestr)
        elif 'close' in voice_data:
            file_exp_status = False
            reply("File explorer closed.")

    elif 'open calculator' in voice_data:
        open_calculator()

    elif 'open calendar' in voice_data:
        open_calendar()

    elif 'open whatsapp chat' in voice_data:
        if ("of" in voice_data):
            contact_name = voice_data.split("of")[-1].strip() 
            open_whatsapp_chat(contact_name)

        elif ("for" in voice_data):
            contact_name = voice_data.split("for")[-1].strip() 
            open_whatsapp_chat(contact_name)

        else:
            reply("Please specify the contact name.")

    elif 'launch gesture recognition' in voice_data:
        if Gesture_Controller.GestureController.gc_mode:
            reply('Gesture recognition is already active')
        else:
            gc = Gesture_Controller.GestureController()
            t = Thread(target = gc.start)
            t.start()
            reply('Launched Successfully')

    elif ('stop gesture recognition' in voice_data) or ('top gesture recognition' in voice_data):
        if Gesture_Controller.GestureController.gc_mode:
            Gesture_Controller.GestureController.gc_mode = 0
            reply('Gesture recognition stopped')
        else:
            reply('Gesture recognition is already inactive')

    elif ('bye' in voice_data) or ('sleep' in voice_data):
        reply("Good bye! Have a nice day.")
        is_awake = False

    elif ('exit' in voice_data) or ('terminate' in voice_data):
        app.ChatBot.close()
        sys.exit()

    else:
        # reply("Can't Recognize")
        response = get_conversational_response(voice_data)
        reply(response)

# ------------------Driver Code--------------------

t1 = Thread(target = app.ChatBot.start)
t1.start()

# Lock main thread until Chatbot has started
while not app.ChatBot.started:
    time.sleep(0.5)

wish()
voice_data = None
while True:
    if app.ChatBot.isUserInput():
        #take input from GUI
        voice_data = app.ChatBot.popUserInput()
    else:
        #take input from Voice
        voice_data = record_audio()

    #process voice_data
    if 'aura' in voice_data:
        try:
            #Handle sys.exit()
            respond(voice_data)
        except SystemExit:
            reply("Exit Successfull")
            break
        except:
            #some other exception got raised
            print("EXCEPTION raised while closing.") 
            break
        