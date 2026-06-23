import pyttsx3

# Initialize the offline engine
engine = pyttsx3.init()

# Get list of all available system voices
voices = engine.getProperty('voices')

# Find and set a female voice
female_voice_found = False
for voice in voices:
    # Check if 'female' is in the voice name or gender metadata
    if 'female' in voice.name.lower() or (hasattr(voice, 'gender') and voice.gender == 'female'):
        engine.setProperty('voice', voice.id)
        female_voice_found = True
        break

# Fallback: Many systems list the male voice at index 0 and female voice at index 1
if not female_voice_found and len(voices) > 1:
    engine.setProperty('voice', voices[1].id)

# Optional: Adjust the speaking rate (speed)
engine.setProperty('rate', 150) 

# Test the TTS output
text_to_say = "Hello! This is a completely offline female voice running in Python."
engine.say(text_to_say)
engine.setProperty('voice', 'english+f2')

# Process and run the speech queue
engine.runAndWait()