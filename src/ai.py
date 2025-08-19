# src/ai.py
# from huggingface_hub import InferenceClient
from openai import OpenAI
from src.config import config

from src.logging_utils import get_logger

logger = get_logger(__name__)

# # Initialize the Hugging Face Inference Client
# client = InferenceClient(api_key=config.hf_key_api)

client = OpenAI(
    base_url="http://localhost:11434/v1",  # Point to your local Ollama server
    api_key="ollama",  # This is a placeholder key
)

# Store conversation history (question-answer pairs) per user
conversation_history = {}  # Format: {user_id: [{"question": str, "answer": str}, ...]}

# Store accuracy/correctness data per user as a list of facts
accuracy_data = {}  # Format: {user_id: ["fact1", "fact2", ...]}

# Command mapping with emojis
COMMAND_MAP = {
    "info": {"func": "info", "emoji": "📊"},
    "system info": {"func": "info", "emoji": "📊"},
    "uptime": {"func": "uptime", "emoji": "⏰"},
    "weather": {"func": "weather", "emoji": "🌦️"},
    "cpu": {"func": "cpu", "emoji": "📈"},
}


async def process_with_ai(user_input, update=None, context=None):
    from src.commands import info, uptime, weather, cpu

    user_id = update.message.from_user.id if update else None
    username = update.message.from_user.username or "Unknown" if update else "Unknown"

    # Handle conversation reset
    if user_input.lower() in [
        "clear",
        "create new conversation",
        "new conversation",
        "new section",
    ]:
        if user_id in conversation_history:
            del conversation_history[user_id]
            logger.info(f"Cleared conversation history for user {username} ({user_id})")

        if user_id in accuracy_data:
            del accuracy_data[user_id]
            logger.info(
                f"Cleared all accuracy_data history for user {username} ({user_id})"
            )
        return "🧹 All data cleared! Let's start fresh."

    # Initialize user data if not present
    if user_id and user_id not in conversation_history:
        conversation_history[user_id] = []
    if user_id and user_id not in accuracy_data:
        accuracy_data[user_id] = []  # Initialize as a list

    # Handle accuracy data input (e.g., "remember: <some fact>")
    remember_triggers = [
        "remember the fact: ",
        "remember this: ",
        "remember the following: ",
        "remember this one: ",
        "remember:",
        "remember:\n",  # Explicitly match with newline
        "please remember this: ",
    ]
    input_lower = user_input.strip().lower()
    logger.info(f"Raw input_lower: '{input_lower}'")  # Debug logging

    # Check for triggers in a multi-line safe way
    for trigger in remember_triggers:
        if input_lower.startswith(trigger):  # Use startswith for exact match at start
            logger.info(f"Matched trigger: '{trigger}'")
            fact_block = user_input[
                user_input.lower().index(trigger) + len(trigger) :
            ].strip()
            if not fact_block:
                return "🤔 Please provide a fact to remember (e.g., 'remember: The sky is blue')."

            # Split the fact block into individual lines/facts
            facts = [line.strip() for line in fact_block.split("\n") if line.strip()]
            if not facts:
                return "🤔 Please provide at least one valid fact to remember."

            # Ensure user_id has a list initialized
            if user_id not in accuracy_data:
                accuracy_data[user_id] = []

            # Append each fact individually
            for fact in facts:
                accuracy_data[user_id].append(fact)
                logger.info(f"Stored fact for {username} ({user_id}): '{fact}'")

            # Format the response with all facts
            response = "✅ Remembered the following mappings:\n" + "\n".join(
                f"* {fact}" for fact in facts
            )
            return response

    # Build context for conversation history
    context_prompt = ""
    if user_id and conversation_history[user_id]:
        context_prompt = "Previous conversation:\n"
        for entry in conversation_history[user_id]:
            context_prompt += f"User: {entry['question']}\nBot: {entry['answer']}\n"

    # Build context for accuracy data (list of facts)
    accuracy_prompt = ""
    if user_id and accuracy_data.get(user_id):
        accuracy_prompt = "User-provided facts to remember:\n"
        for i, fact in enumerate(accuracy_data[user_id], 1):
            accuracy_prompt += f"{i}. {fact}\n"

    # Direct command matching with parameters
    input_lower = user_input.strip().lower()
    logger.info(f"Checking direct command match for input: '{input_lower}'")

    logger.info(f"context_prompt: '{context_prompt}'")

    logger.info(f"accuracy_prompt: '{accuracy_prompt}'")

    for command, details in COMMAND_MAP.items():
        if input_lower == command or input_lower.startswith(command + " "):
            logger.info(f"Matched command: {command}")
            params = (
                input_lower[len(command) :].strip()
                if input_lower.startswith(command + " ")
                else None
            )

            if command == "weather" and params:
                param_words = params.split()
                if param_words and param_words[0] == "in":
                    params = " ".join(param_words[1:]).strip()
                if not params:
                    params = None

            if command == "weather" and not params:
                response = "🌦️ Please specify a city (e.g., 'weather London')."
                await update.message.reply_text(response)
                return None

            response = f"{details['emoji']} Executing {command} command..."
            await update.message.reply_text(response)

            func = locals()[details["func"]]
            await func(update, context, params=params)

            if user_id:
                conversation_history[user_id].append(
                    {"question": user_input, "answer": response}
                )
                if len(conversation_history[user_id]) > 10:
                    conversation_history[user_id] = conversation_history[user_id][-10:]
            return None

    # AI fallback with accuracy data included
    prompt = f"""
    You are a command detection engine for a Telegram bot. Your task is to analyze user requests and determine if their **intent** matches one of the provided commands.

    **Available Commands and Aliases:**
    {{
        "info": ["info", "system info", "stats", "system stats"],
        "uptime": ["uptime", "how long have you been on"],
        "weather": ["weather"],
        "cpu": ["cpu", "cpu usage", "what's the cpu at"],
    }}

    **Instructions:**
    1.  **Strictly evaluate the user's intent.** If the user is asking a question that is clearly a request for a command, such as a question about the weather, you must return a command.
    2.  **Extract Parameters:** If a command requires a parameter (like `weather`), you must extract it from the user's request.
    3.  **Adhere to the Output Format:**
        * If a command is detected, **output only the command name and any parameters**. Do not add any extra text or conversational phrases.
        * If **no command is detected**, respond to the user's query naturally. Your response **must begin with the prefix "CHAT:"**.
    4.  **Use these examples to guide your response:**

    **Examples:**
    User: How's the weather in London?
    Output: weather London

    User: What's the CPU usage like?
    Output: cpu

    User: Can you tell me some facts about the capital of Vietnam?
    Output: CHAT: The capital of Vietnam is Hanoi. It is famous for its centuries-old architecture and a rich history.

    User: Tell me about your system stats.
    Output: info

    User: Hi, are you a bot?
    Output: CHAT: I am a helpful Telegram bot. How can I assist you today?

    **User Query:**
    "{user_input}"

    **Response:
    """

    messages = [{"role": "user", "content": prompt}]
    try:
        stream = client.chat.completions.create(
            model="phi3:mini",
            messages=messages,
            max_tokens=200,  # Increased from 100 to avoid truncation of longer responses
            stream=True,
        )
        # response = ""
        # for chunk in stream:
        #     if chunk.choices[0].delta.content:
        #         response += chunk.choices[0].delta.content

        response = "".join(
            [
                chunk.choices[0].delta.content
                for chunk in stream
                if chunk.choices[0].delta.content
            ]
        )

        logger.info(f"User input from {username} ({user_id}): {user_input}")
        logger.info(f"Raw AI response from {username} ({user_id}): {response}")

        # --- NEW CODE LOGIC ---
        # 1. Clean the response: remove code block markers, newlines, and excess whitespace
        cleaned_response = (
            response.replace("```plaintext", "").replace("```", "").strip()
        )

        # 2. Check for command vs. chat
        is_command = False
        final_response = ""

        # Check for commands in the cleaned response
        for command in COMMAND_MAP.keys():
            # Check for exact command or command with a space
            if (
                cleaned_response.lower() == command
                or cleaned_response.lower().startswith(command + " ")
            ):
                is_command = True
                final_response = cleaned_response
                break

        # Check if it's a chat response (if not a command)
        if not is_command and cleaned_response.startswith("CHAT:"):
            final_response = cleaned_response.replace("CHAT:", "").strip()

        # If it's a command, execute it
        if is_command:
            command = final_response.split(" ")[0].lower()
            params = (
                final_response[len(command) :].strip()
                if len(final_response) > len(command)
                else None
            )

            # Additional logic for weather command with params
            if command == "weather" and params:
                param_words = params.split()
                if param_words and param_words[0].lower() == "in":
                    params = " ".join(param_words[1:]).strip()

            # Proceed to execute the command function
            final_response = (
                f"{COMMAND_MAP[command]['emoji']} Executing {command} command..."
            )
            await update.message.reply_text(final_response)
            func = locals()[COMMAND_MAP[command]["func"]]
            await func(update, context, params=params)

            if user_id:
                conversation_history[user_id].append(
                    {"question": user_input, "answer": final_response}
                )
                if len(conversation_history[user_id]) > 10:
                    conversation_history[user_id] = conversation_history[user_id][-10:]
            return None
        else:
            # It's a chat response, send it directly
            if user_id:
                conversation_history[user_id].append(
                    {"question": user_input, "answer": final_response}
                )
                if len(conversation_history[user_id]) > 10:
                    conversation_history[user_id] = conversation_history[user_id][-10:]
            return final_response

    except Exception as e:
        logger.error(f"AI processing error for {username} ({user_id}): {str(e)}")
        return f"😵 Sorry, something went wrong: {str(e)}. Try again!"
