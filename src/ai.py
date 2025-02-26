# src/ai.py
from huggingface_hub import InferenceClient
from src.config import config, logger

# Initialize the Hugging Face Inference Client
client = InferenceClient(api_key=config.hf_key_api)

# Store conversation history (question-answer pairs) per user
conversation_history = {}  # Format: {user_id: [{"question": str, "answer": str}, ...]}

# Command mapping with emojis
COMMAND_MAP = {
    "info": {"func": "info", "emoji": "📊"},  # System info
    "uptime": {"func": "uptime", "emoji": "⏰"},  # Uptime
    "weather": {"func": "weather", "emoji": "🌦️"},  # Weather info
    "cpu": {"func": "cpu", "emoji": "📈"},  # CPU info
}


async def process_with_ai(user_input, update=None, context=None):
    from src.commands import info, uptime, weather, cpu

    user_id = update.message.from_user.id if update else None
    username = update.message.from_user.username or "Unknown" if update else "Unknown"

    if user_input.lower() in [
        "clear",
        "create new conversation",
        "new conversation",
        "new section",
    ]:
        if user_id in conversation_history:
            del conversation_history[user_id]
            logger.info(f"Cleared conversation history for user {username} ({user_id})")
        return "🧹 Conversation cleared! Let's start fresh."

    if user_id and user_id not in conversation_history:
        conversation_history[user_id] = []

    context_prompt = ""
    if user_id and conversation_history[user_id]:
        context_prompt = "Previous conversation:\n"
        for entry in conversation_history[user_id]:
            context_prompt += f"User: {entry['question']}\nBot: {entry['answer']}\n"

    # Direct command matching with parameters
    input_lower = user_input.strip().lower()
    logger.info(f"Checking direct command match for input: '{input_lower}'")
    for command, details in COMMAND_MAP.items():
        if input_lower == command or input_lower.startswith(command + " "):
            logger.info(f"Matched command: {command}")
            params = (
                input_lower[len(command) :].strip()
                if input_lower.startswith(command + " ")
                else None
            )

            # Special handling for weather command to clean up "in"
            if command == "weather" and params:
                # Split params into words and remove "in" if it's the first word
                param_words = params.split()
                if param_words and param_words[0] == "in":
                    params = " ".join(param_words[1:]).strip()
                # If params is now empty, treat it as no params
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

    # AI fallback
    prompt = f"""
    You are a Telegram bot assistant. The user asked: "{user_input}".
    {context_prompt}
    Interpret their intent strictly:
    - If they likely want a command from this list—{", ".join(COMMAND_MAP.keys())}—return *only* the command name (e.g., "weather") or the command with its full parameter if provided (e.g., "weather London or weather in London or how the weather in London").
    - If a command like "weather" is implied and includes a location, return the full phrase (e.g., "weather London").
    - Otherwise, answer the user's question naturally and concisely, performing calculations or providing information as needed, mandatory prefixed with "CHAT:" (e.g., "CHAT: The result of 5 x 7 - 2 is 33" or "CHAT: I don't have enough info to answer that!").
    Do not add extra text beyond the command with parameters unless it's a "CHAT:" response.
    """

    messages = [{"role": "user", "content": prompt}]
    try:
        stream = client.chat.completions.create(
            model="mistralai/Mistral-7B-Instruct-v0.3",
            messages=messages,
            max_tokens=100,
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
            final_response = (
                "🤔 I don't quite get that. Try a command or ask me something else!"
            )

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
