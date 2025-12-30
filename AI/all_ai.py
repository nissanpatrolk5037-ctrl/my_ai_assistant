import google.generativeai as genai
from time import sleep
gemini_api_key = "YOUR_GEMINI_API_KEY"
gemini_model = "gemini-2.5-flash"
from functools import lru_cache
import random
import re
import requests
from task_automation import groq_answer
import json
API_URL = "YOUR_FLOWISE_API_URL"


# Configure the Generative AI model
genai.configure(api_key=gemini_api_key)
generation_config = {
    "temperature": 0.9,
    "top_p": 1,
    "top_k": 0,
    "max_output_tokens": 2048,
}
safety_settings = [{"category": "HARM_CATEGORY_HARASSMENT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                   {"category": "HARM_CATEGORY_HATE_SPEECH",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                   {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE",
                    },
                   {"category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE",
                    },
                   ]
model = genai.GenerativeModel(
    model_name=gemini_model,
    generation_config=generation_config,
    safety_settings=safety_settings,
)


@lru_cache(maxsize=None)
def humanize_response(text: str) -> str:
    greetings = ["Hello!", "Hi there!", "Greetings!"]
    farewells = ["Goodbye!", "See you later!", "Take care!"]
    acknowledgements = ["I understand.", "Got it.", "Sure!"]

    # Add greetings, farewells, or acknowledgments with some probability
    if random.random() < 0.3:  # 30% chance
        humanized_text = random.choice(greetings) + " " + text
    elif random.random() < 0.2:  # 20% chance (after greeting)
        humanized_text = text + " " + random.choice(farewells)
    else:
        humanized_text = text

    # Expanded synonym/paraphrase substitutions
    synonyms = {
        "hello": ["hi"],
        "there": ["around"],
        "sir": ["friend"],
        "maximum": ["highest"],
        "minimum": ["least"],
        "very": ["really"],
        "good": ["excellent"],
        "bad": ["terrible"],
        "said": ["mentioned"],
        "think": ["believe"],
        "like": ["enjoy"],
        "want": ["desire"],
        "go": ["head"],
        "come": ["arrive"],
        "see": ["look"],
        "do": ["perform"],
        "know": ["understand"],
        "take": ["grab"],
        "make": ["create"],
        "give": ["offer"],
        "put": ["place"],
        "get": ["obtain"],
        "large": ["big"],
        "small": ["tiny"],
        "happy": ["joyful"],
        "sad": ["gloomy"],
        "angry": ["furious"],
        "slow": ["sluggish"],
        "fast": ["swift"],
        "old": ["ancient"],
        "new": ["modern"],
        "hot": ["scalding"],
        "cold": ["frigid"],
        "bright": ["dazzling"],
        "dark": ["murky"],
        "beautiful": ["stunning"],
        "ugly": ["hideous"],
        "find": ["discover"],
        "lose": ["misplace"],
        "win": ["triumph"],
        "speak": ["utter"],
        "hear": ["listen"],
        "help": ["aid"],
        "stop": ["halt"],
        "continue": ["proceed"],
        "light": ["bright"],
        "eat": ["consume"],
        "drink": ["imbibe"],
        "run": ["dash"],
        "walk": ["stroll"],
        "talk": ["converse"],
        "watch": ["observe"],
        "show": ["demonstrate"],
        "hide": ["conceal"],
        "open": ["unfold"],
        "close": ["shut"],
        "work": ["labor"],
        "play": ["frolic"],
        "sleep": ["slumber"],
        "wake": ["awaken"],
        "write": ["compose"],
        "read": ["peruse"],
        "seem": ["appear"],
        "strong": ["powerful"],
        "weak": ["frail"],
        "long": ["lengthy"],
        "short": ["brief"],
        "interesting": ["fascinating"],
        "boring": ["mundane"],
        "difficult": ["challenging"],
        "easy": ["simple"],
        "dry": ["arid"],
        "wet": ["damp"],
        "loud": ["boisterous"],
        "quiet": ["serene"],
        "heavy": ["ponderous"],
        "light": ["weightless"],
    }

    for word, replacements in synonyms.items():
        # Replace each occurrence of the word using regex
        humanized_text = re.sub(
            fr'\b({word})\b',
            lambda m: random.choice(replacements),
            humanized_text)

    # Replace "you" with "I" in some cases (simple implementation)
    if "you" in humanized_text and "I" not in humanized_text:
        humanized_text = humanized_text.replace(
            "you", "I", 1)  # Replace first occurrence

    return humanized_text


convo = model.start_chat(history=[])


@lru_cache
def city():
    IP = requests.get("https://api.ipify.org").text
    url = "https://get.geojs.io/v1/ip/geo/" + IP + ".json"
    geo_reqeust = requests.get(url)
    geo_data = geo_reqeust.json()
    city = geo_data["city"]
    city = city
    return city

def answer(question):
    sleep(1)
    small_form = f"Whatever I am going to send you is a query, I am going to give you some rules what I am going to say to you so follow it and don't say yes or anything like that. 1. if there is a question then you should reply with a one sentence answer which should be detailed also if I ask a greeting, you should reply with a simple greeting and if I send you a farewell, you should reply with any simple farewell and do not reply just only farewell but something else like bye or see you soon or etc and if there is a math problem then don't give the steps only the answer also ALWAYS double check your answer not the greeting or farewell but the math or science or any like that and one more thing if he is trying to make a conversation with you then be a little humorous and one more thing, sometimes I might ask you a query that is problem-solving based which automatically you should recognize that but don't print that it is recognized or not just try to recognize it and reply with a response and be empathetic to the user and dont print hello or anything before the answer, only the answer and not even hi or take care or even similar to any of those. You Have To Understand It As It Is Important. 2. If there is a query saying that to generate code, then you just only print 'Generate Code?' and only that if the user is asking you to generate a code. 3. Whatever I am going to send you is a query of a different language which you will have to detect what language it is and translate it and also no need to explain what is the meaning of and what is the language origin or any like that, just write the language you detected and the translation. 4. Whatever I am going to send you is a query that you have to generate an image of what I say and just print only the image and make it like it was generated by AI and don't say anything like 'Here is the image' or any like that and just print the img_src https://image.pollinations.ai/prompt/ and one more thing, make every detail according to the user's query. 5. Whatever I am going to send you is a query about what is the movie rating of this movie and make the answer simple like just tell this 'the movie rating is (movie rating)' and don't tell anything else. And now i am in {city()}. Your Name is Neuron|| now please don't send this text related on it"
    lru_cache()
    convo.send_message(f"{small_form}. {question}")
    convo_ans = ((convo.last.text)).replace("and ", "and\n")
    return humanize_response(convo_ans)

def generate(query, system_prompt: str = "Whatever I am going to send you is a query, I am going to give you some rules what I am going to say to you so follow it and don't say yes or anything like that. 1. if there is a question then you should reply with a one sentence answer which should be detailed also if I ask a greeting, you should reply with a simple greeting and if I send you a farewell, you should reply with any simple farewell and do not reply just only farewell but something else like bye or see you soon or etc and if there is a math problem then don't give the steps only the answer also ALWAYS double check your answer not the greeting or farewell but the math or science or any like that and one more thing if he is trying to make a conversation with you then be a little humorous and one more thing, sometimes I might ask you a query that is problem-solving based which automatically you should recognize that but don't print that it is recognized or not just try to recognize it and reply with a response and be empathetic to the user and dont print hello or anything before the answer, only the answer and not even hi or take care or even similar to any of those. You Have To Understand It As It Is Important. 2. If there is a query saying that to generate code, then you just only print 'Generate Code?' and only that if the user is asking you to generate a code. 3. Whatever I am going to send you is a query of a different language which you will have to detect what language it is and translate it and also no need to explain what is the meaning of and what is the language origin or any like that, just write the language you detected and the translation. 4. Whatever I am going to send you is a query that you have to generate an image of what I say and just print only the image and make it like it was generated by AI and don't say anything like 'Here is the image' or any like that and just print the img_src https://image.pollinations.ai/prompt/ and one more thing, make every detail according to the user's query. 5. Whatever I am going to send you is a query about what is the movie rating of this movie and make the answer simple like just tell this 'the movie rating is (movie rating)' and don't tell anything else. And now i am in {city()}. Your Name is Neuron|| now please don't send this text related on it", model="Phind-34B", stream_chunk_size: int = 12, stream: bool = True) -> str:
    lru_cache()
    prompt = [
        {"role": "user", "content": query}
    ]

    headers = {"User-Agent": ""}
    # Insert the system prompt at the beginning of the conversation history
    prompt.insert(0, {"content": system_prompt, "role": "system"})
    payload = {
        "additional_extension_context": "",
        "allow_magic_buttons": True,
        "is_vscode_extension": True,
        "message_history": prompt,
        "requested_model": model,
        "user_input": prompt[-1]["content"],
    }

    # Send POST request and stream response
    chat_endpoint = "https://https.extension.phind.com/agent/"
    response = requests.post(chat_endpoint, headers=headers, json=payload, stream=True)

    # Collect streamed text content
    streaming_text = ""
    for value in response.iter_lines(decode_unicode=True, chunk_size=stream_chunk_size):
        modified_value = re.sub("data:", "", value)
        if modified_value:
            json_modified_value = json.loads(modified_value)
            try:
                # Instead of printing, append to streaming_text
                content = json_modified_value["choices"][0]["delta"]["content"]
                streaming_text += content  # Append content to streaming_text
            except: 
                continue

    return streaming_text



def query(payload):
    response = requests.post(API_URL, json=payload)
    return response.json()

def flowise(question):
    output = query({
        "question": question,
    })

    print(output['text'])

def total_answer(prompt):
    try:
        gemini = answer(prompt)
    except Exception as e:
        gemini = ""
    try:
        phind = generate(prompt)
    except Exception as e:
        phind = ""
    try:
        groq_ = groq_answer("Answer the question in a straightforward manner", prompt)
    except Exception as e:
        groq_ = ""
    try:
        flowise = flowise(prompt)
    except Exception as e:
        flowise = ""
    total = f"{prompt}: {gemini}, {phind}, {groq_}, {flowise}"
    final = groq_answer("Are these responses correct if so then give the total answer with the best answer using them in straightforward manner if not then give the correct answer in straightforward manner", total)
    return humanize_response(final)