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
    """
    Process user input with Hugging Face Inference API, handle commands or continue conversation.
    Args:
        user_input (str): The user's message (e.g., "check the system info" or "info").
        update (telegram.Update): Telegram update object for command execution.
        context (telegram.ext.ContextTypes.DEFAULT_TYPE): Context for command execution.
    Returns:
        str: Response to send back to the user, or None if the command handles it.
    """
    # Import commands inside the function to avoid circular imports
    from src.commands import info, uptime, weather, cpu

    user_id = update.message.from_user.id if update else None
    username = update.message.from_user.username or "Unknown" if update else "Unknown"

    # Check for conversation reset
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

    # Initialize conversation history for this user if not present
    if user_id and user_id not in conversation_history:
        conversation_history[user_id] = []

    # Build context from previous conversation
    context_prompt = ""
    if user_id and conversation_history[user_id]:
        context_prompt = "Previous conversation:\n"
        for entry in conversation_history[user_id]:
            context_prompt += f"User: {entry['question']}\nBot: {entry['answer']}\n"

    # Check if the input directly matches a command
    input_lower = user_input.strip().lower()
    for command, details in COMMAND_MAP.items():
        if input_lower == command:
            response = f"{details['emoji']} Executing {command} command..."
            await update.message.reply_text(response)  # Send before execution
            func = locals()[details["func"]]
            await func(update, context)  # Command sends its own output
            # Log to history
            if user_id:
                conversation_history[user_id].append(
                    {"question": user_input, "answer": response}
                )
                if len(conversation_history[user_id]) > 10:
                    conversation_history[user_id] = conversation_history[user_id][-10:]
            return None  # No additional response needed

    # Define a prompt for natural language interpretation
    prompt = f"""
    You are a Telegram bot assistant. The user said: "{user_input}".
    {context_prompt}
    Interpret their intent:
    - If they want a command, return one of these: {", ".join(COMMAND_MAP.keys())}
    - If the command needs a parameter (e.g., weather needs a city), include it like "weather London"
    - If not, respond naturally as a conversational bot and return your response prefixed with "CHAT:"
    """

    # Prepare the message for the API
    messages = [{"role": "user", "content": prompt}]

    try:
        # Call the Hugging Face Inference API with streaming
        stream = client.chat.completions.create(
            model="google/gemma-2-2b-it",
            messages=messages,
            max_tokens=100,
            stream=True,
        )

        # Collect the streamed response
        response = ""
        for chunk in stream:
            if chunk.choices[0].delta.content:
                response += chunk.choices[0].delta.content

        # Log user prompt and AI response
        logger.info(f"User input from {username} ({user_id}): {user_input}")
        logger.info(f"AI response for {username} ({user_id}): {response}")

        # Clean up the response
        response = response.strip()

        # Check if the response indicates a command
        if response in COMMAND_MAP:
            final_response = (
                f"{COMMAND_MAP[response]['emoji']} Executing {response} command..."
            )
            await update.message.reply_text(final_response)  # Send before execution
            func = locals()[COMMAND_MAP[response]["func"]]
            await func(update, context)  # Command sends its own output
            # Log to history
            if user_id:
                conversation_history[user_id].append(
                    {"question": user_input, "answer": final_response}
                )
                if len(conversation_history[user_id]) > 10:
                    conversation_history[user_id] = conversation_history[user_id][-10:]
            return None  # No additional response needed
        elif response.startswith("CHAT:"):
            final_response = response.replace("CHAT:", "").strip()
        else:
            final_response = (
                "🤔 I don't quite get that. Try a command or ask me something else!"
            )

        # Log to conversation history
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
