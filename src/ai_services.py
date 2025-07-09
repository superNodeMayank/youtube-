import google.generativeai as genai
from src.config import settings
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure the Gemini API key
if settings.GEMINI_API_KEY:
    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
    except Exception as e:
        logger.error(f"Failed to configure Gemini API: {e}")
        # Depending on strictness, could raise an error or allow app to run with AI features disabled.
else:
    logger.warning("GEMINI_API_KEY not found. AI features will be disabled.")

# Initialize the Generative Model (e.g., Gemini Pro)
# Choose a model appropriate for text generation/enhancement.
# Model availability might change, check Google AI documentation.
MODEL_NAME = "gemini-pro" # Or "gemini-1.0-pro", "gemini-1.5-flash", etc.
model = None
if settings.GEMINI_API_KEY:
    try:
        model = genai.GenerativeModel(MODEL_NAME)
        # Test with a simple generation to see if it works (optional, can be slow at startup)
        # model.generate_content("test")
        logger.info(f"Successfully initialized Gemini model: {MODEL_NAME}")
    except Exception as e:
        logger.error(f"Failed to initialize Gemini model '{MODEL_NAME}': {e}")
        model = None # Ensure model is None if initialization fails

def enhance_comment_with_ai(raw_comment: str, user_prompt_template: Optional[str] = None) -> str | None:
    """
    Sends a raw comment to the Gemini AI for enhancement.

    Args:
        raw_comment: The original comment text from the user.
        user_prompt_template: An optional template for the prompt.
                              If None, a default prompt is used.
                              Example: "Please make this comment more polite: {comment}"
                              The template must contain '{comment}' placeholder.

    Returns:
        The enhanced comment string from the AI, or None if an error occurs
        or AI features are disabled.
    """
    if not model:
        logger.warning("Gemini model not initialized. Cannot enhance comment.")
        return None

    if not raw_comment or not raw_comment.strip():
        logger.warning("Raw comment is empty. Skipping enhancement.")
        return None # Or return raw_comment

    if user_prompt_template:
        if "{comment}" not in user_prompt_template:
            logger.error("User prompt template does not contain '{comment}' placeholder.")
            # Fallback to default prompt or return error
            prompt = f"Enhance the following YouTube comment to be more engaging and constructive, while preserving the original intent. Keep it concise and suitable for a public forum. Original comment: \"{raw_comment}\""
        else:
            prompt = user_prompt_template.format(comment=raw_comment)
    else:
        # Default prompt (can be refined based on desired output)
        prompt = f"Enhance the following YouTube comment to be more engaging and constructive, while preserving the original intent. Keep it concise and suitable for a public forum. Original comment: \"{raw_comment}\""

    logger.info(f"Sending prompt to Gemini: \"{prompt[:100]}...\"") # Log a snippet

    try:
        # Generation configuration (optional, adjust as needed)
        generation_config = genai.types.GenerationConfig(
            # candidate_count=1, # Number of generated responses to return
            # stop_sequences=['x'], # Sequences to stop generation on
            # max_output_tokens=200, # Maximum number of tokens to generate
            temperature=0.7, # Controls randomness (0.0=deterministic, 1.0=max random)
            # top_p=1.0, # Nucleus sampling
            # top_k=1, # Top-k sampling
        )

        response = model.generate_content(
            prompt,
            generation_config=generation_config,
            # safety_settings can be configured here if needed
        )

        if response.candidates:
            # Assuming the first candidate is the most relevant
            # The structure of 'text' might vary based on model and response type.
            # For simple text generation, response.text might be available directly.
            # For others, it might be response.candidates[0].content.parts[0].text

            enhanced_text = ""
            if response.candidates[0].content and response.candidates[0].content.parts:
                enhanced_text = "".join(part.text for part in response.candidates[0].content.parts if hasattr(part, 'text'))

            if not enhanced_text.strip() and response.prompt_feedback.block_reason:
                 logger.warning(f"Gemini API blocked prompt. Reason: {response.prompt_feedback.block_reason}")
                 return None # Or raise an exception

            if not enhanced_text.strip() and response.candidates[0].finish_reason.name != "STOP":
                logger.warning(f"Gemini generation did not finish normally. Reason: {response.candidates[0].finish_reason.name}")
                # Potentially return None or the partial text based on the reason
                # For example, if it's MAX_TOKENS, the text might be usable but truncated.
                # If it's SAFETY, it's better to return None.
                if response.candidates[0].finish_reason.name == "SAFETY":
                    return None


            logger.info(f"Received enhanced comment from Gemini: \"{enhanced_text[:100]}...\"")
            return enhanced_text.strip() if enhanced_text else None
        else:
            # This case might occur if the prompt was blocked for safety or other reasons
            # and no candidates were returned.
            if response.prompt_feedback and response.prompt_feedback.block_reason:
                logger.warning(f"Gemini API blocked prompt. Reason: {response.prompt_feedback.block_reason}")
            else:
                logger.warning("Gemini API returned no candidates for enhancement.")
            return None

    except Exception as e:
        # More specific error handling can be added for API errors vs. other exceptions
        logger.error(f"Error during Gemini API call: {e}", exc_info=True)
        # Check for specific API errors if the library provides them
        # For example: if isinstance(e, google.api_core.exceptions.GoogleAPIError):
        # logger.error(f"Gemini API specific error: {e.details}")
        return None

# Example usage (for testing this module directly):
if __name__ == "__main__":
    if not settings.GEMINI_API_KEY:
        print("Please set the GEMINI_API_KEY environment variable in your .env file to test.")
    else:
        print(f"Gemini API Key found: {settings.GEMINI_API_KEY[:5]}...") # Print partial key for confirmation
        if not model:
            print("Gemini model could not be initialized. Check logs.")
        else:
            test_comment_1 = "This video is okay, I guess."
            enhanced_1 = enhance_comment_with_ai(test_comment_1)
            print(f"Original: {test_comment_1}\nEnhanced: {enhanced_1}\n")

            test_comment_2 = "I dont like this at all!! its bad"
            enhanced_2 = enhance_comment_with_ai(test_comment_2)
            print(f"Original: {test_comment_2}\nEnhanced: {enhanced_2}\n")

            test_comment_3 = "amazing work, loved every second of it, best thing ever"
            custom_prompt = "Shorten this comment and make it sound more casual: {comment}"
            enhanced_3 = enhance_comment_with_ai(test_comment_3, user_prompt_template=custom_prompt)
            print(f"Original: {test_comment_3}\nCustom Prompt Enhanced: {enhanced_3}\n")

            test_comment_4 = "" # Empty comment
            enhanced_4 = enhance_comment_with_ai(test_comment_4)
            print(f"Original: '{test_comment_4}'\nEnhanced: {enhanced_4}\n")

            # Test for prompt blocking (content might need to be adjusted to trigger it)
            # test_comment_5 = "some potentially harmful content"
            # enhanced_5 = enhance_comment_with_ai(test_comment_5)
            # print(f"Original: '{test_comment_5}'\nEnhanced: {enhanced_5}\n")

# To make this runnable for testing, ensure .env is in the project root,
# and run from project root: python -m src.ai_services
# The config.py expects .env to be in the CWD from where python is run.
# If running `python src/ai_services.py` directly from `src` dir,
# `load_dotenv()` in config might need `dotenv_path=Path('../.env')`.
# But `python -m src.ai_services` from root should work with current config.py.
