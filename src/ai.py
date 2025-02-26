# src/ai.py
from huggingface_hub import InferenceClient
from src.config import config

from src.logging_utils import get_logger  
logger = get_logger(__name__)

# Initialize the Hugging Face Inference Client
client = InferenceClient(api_key=config.hf_key_api)

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
            logger.info(f"Cleared all accuracy_data history for user {username} ({user_id})")
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
    You are a Telegram bot assistant. The user asked: "{user_input}".
    {context_prompt}
    {accuracy_prompt}
    Interpret their intent strictly:
    - Use the provided facts to refine your understanding or responses where applicable.
    - If the user's input contains a specific command (e.g., './bin/cstool ...') as part of an example or instruction, return a response that includes the full command exactly as provided, prefixed with: "In order to export the list of Wave accounts with their respective features enabled for JIG-SAW, use the following command:" followed by the command in a new line (e.g., "./bin/cstool export --env prod --type wave_meta --msp MSP-5bc04603c8303"). Do not truncate or rephrase the command unless explicitly asked.
    - If they likely want a command from this list—{", ".join(COMMAND_MAP.keys())}—return *only* the command name (e.g., "weather") or the command with its full parameter if provided (e.g., "weather London").
    - Otherwise, answer the user's question naturally and concisely, performing calculations or providing information as needed, mandatory prefixed with "CHAT:" (e.g., "CHAT: The result of 5 x 7 - 2 is 33").
    Do not add extra text beyond the specified format unless it's a "CHAT:" response.
    """

    messages = [{"role": "user", "content": prompt}]
    try:
        stream = client.chat.completions.create(
            model="mistralai/Mistral-7B-Instruct-v0.3",
            messages=messages,
            max_tokens=200,  # Increased from 100 to avoid truncation of longer responses
            stream=True,
        )
        response = ""
        for chunk in stream:
            if chunk.choices[0].delta.content:
                response += chunk.choices[0].delta.content

        logger.info(f"User input from {username} ({user_id}): {user_input}")
        logger.info(f"Raw AI response from {username} ({user_id}): {response}")

        response = response.strip()
        if response in COMMAND_MAP or any(
            response.startswith(cmd + " ") for cmd in COMMAND_MAP
        ):
            command = response.split(" ")[0]
            params = (
                response[len(command) :].strip()
                if len(response) > len(command)
                else None
            )
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
        elif response.startswith("CHAT:"):
            final_response = response.replace("CHAT:", "").strip()
        else:
            final_response = response  # Use raw response if it matches expected format

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
