from task_automation import *
from memory_manager import *
import socket

# ===============================
# INTERNET CHECK FUNCTION
# ===============================
def check_internet(host="8.8.8.8", port=53, timeout=3):
    """
    Check if the internet is available.
    """
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except Exception:
        return False

# ===============================
# COMMAND INSTRUCTIONS
# ===============================
COMMAND_INSTRUCTIONS = """
You are an AI assistant that converts natural language requests into executable commands.
Return only commands prefixed with ^ for known tasks. Use ^none if no command is needed.
Supported tasks (fully up-to-date):
- YouTube & Video: ^youtube_summarizer, ^ytDownloader, ^yt_search, ^instagram_video_downloader, ^facebook_video_downloader
- Music/Audio: ^playMusic, ^transcribe_audio, ^melody, ^video_to_audio
- Images: ^download_images, ^analyze_image, ^change_wallpaper, ^bg_remover, ^plot_spectrogram, ^wordcloud_generator
- OCR/Document: ^ocr, ^ocr_screen, ^read_pdf, ^summarize_pdf, ^summarize_text, ^convert_text_to_pdf, ^translate_document, ^translate_image, ^csv_to_excel, ^xml_to_csv_converter
- System Utilities: ^clean_system, ^lock_screen, ^enable_game_mode, ^dim_light, ^smart_battery, ^create_system_restore_point, ^find_and_delete_duplicates, ^exec_safe
- Clipboard & Files: ^copy_to_clipboard, ^paste_from_clipboard, ^clean_clipboard, ^backup_clipboard, ^restore_clipboard, ^file_organizer, ^file_manager, ^open_file, ^create_file, ^encrypt_file
- Networking & Web: ^search_google, ^fetch_page, ^get_page_title, ^get_meta_description, ^extract_links, ^internet_speed, ^ip_geolocator, ^upload_to_drive, ^send_discord_message, ^send_whatsapp_message
- Automation & Macros: ^record_macro, ^play_macro, ^repeat_macro, ^chain_commands, ^schedule_task, ^schedule_calendar, ^run_task, ^smart_decide, ^predictive_tasks
- Keyboard & Mouse: ^click, ^double_click, ^right_click, ^type_text, ^press_key, ^hotkey, ^drag, ^scroll, ^move_cursor_to_image, ^safe_click, ^safe_type
- Window Management: ^focus_window, ^center_window, ^maximize_window, ^minimize_window, ^get_window_position, ^get_screen_size, ^wait_for_window, ^wait_for_image, ^click_image, ^double_click_image, ^drag_image, ^highlight_image, ^click_text, ^drag_text
- Email & Productivity: ^send_email, ^send_multiple_emails, ^download_email_attachments, ^remember_birthday, ^check_birthdays, ^scrape_best_sellers, ^track_amazon_product_price
- AI Utilities: ^adaptive_auto_coder, ^nlp_qna, ^summarize_excel_with_groq, ^analyze_and_report, ^analyze_data, ^plot_data, ^generate_chart_from_data, ^generate_report, ^smart_decide
- OS Context: ^os_context, ^window_finder, ^file_finder, ^check_process_status
- Other: ^qrCodeGenerator, ^dim_light, ^reload_plugins
- Multi-command: Use semicolons to separate multiple commands
- Remember: Only one command per output, no explanations, always prefix ^
"""

CASUAL_INSTRUCTIONS = "Respond casually to the user's question if it is not a command."

MULTI_COMMAND_INSTRUCTIONS = """
Rewrite the user's request into a list of executable commands separated by semicolons (;).
Rules:
- Each command must be short and executable
- Do NOT explain anything
- Do NOT number the commands
- Use simple verbs
- Example:
User: Open Chrome then search cats and copy result
Output: open chrome; search cats on google; copy result
Return ONLY the commands.
"""

# ===============================
# OFFLINE LLM ROUTER
# ===============================
def offline_llm_router(prompt, intent="general"):
    """
    Dynamically routes to all available offline LLMs based on intent.
    """
    if intent == "judge":
        return llm_judge_answer(prompt)
    if intent == "fact_check":
        return llm_truth_check(prompt)
    if intent == "math":
        return llm_solve_math(prompt)
    if intent == "code":
        return llm_code(prompt)
    if intent == "medical":
        return llm_biomedical(prompt)
    if intent == "legal":
        return llm_legal(prompt)
    if intent == "creative":
        return llm_creative_write(prompt)
    if intent == "translate":
        return llm_multilingual(prompt)
    if intent == "knowledge":
        return llm_world_knowledge(prompt)
    if intent == "function":
        return llm_function_call(prompt)
    if intent == "fast":
        return llm_ultra_fast(prompt)
    if intent == "micro":
        return llm_micro_tasks(prompt)
    if intent == "compact":
        return llm_compact_reason(prompt)
    if intent == "precise":
        return llm_precise_instruction(prompt)
    if intent == "light":
        return llm_lightweight_instruction(prompt)
    if intent == "research":
        return llm_base_research(prompt)
    if intent == "synthetic":
        return llm_synthetic_data(prompt)
    if intent == "long":
        return llm_long_context(prompt)
    if intent == "supreme":
        return llm_supreme_intelligence(prompt)
    if intent == "discussion":
        return llm_open_discussion(prompt)
    if intent == "friendly":
        return llm_friendly_chat(prompt)
    if intent == "experiment":
        return llm_experimental_reason(prompt)

    return llm_general_assistant(prompt)

# ===============================
# HYBRID MULTI-COMMAND FUNCTION
# ===============================
def hybrid_rewrite(prompt):
    """
    Returns commands string for online/offline mode dynamically.
    Uses Groq for online, Function-calling LLM for offline.
    """
    if check_internet():
        return groq_answer(MULTI_COMMAND_INSTRUCTIONS, prompt)
    # Offline mode: use function-calling LLM for multi-command parsing
    return llm_function_call(MULTI_COMMAND_INSTRUCTIONS + "\nUser: " + prompt)

# ===============================
# HYBRID CASUAL FUNCTION
# ===============================
def hybrid_casual(prompt, intent="general"):
    """
    Returns a casual response using Groq (online) or offline LLM (offline)
    """
    if check_internet():
        return groq_answer(CASUAL_INSTRUCTIONS, prompt)
    return offline_llm_router(prompt, intent)

# ===============================
# MAIN FUNCTION
# ===============================
def main():
    mode = "ONLINE" if check_internet() else "OFFLINE"
    print(f"=== AI Task Assistant ({mode} MODE) ===")

    while True:
        user_input = input("Enter your command or question: ").strip()
        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit"):
            print("Exiting...")
            break

        # NLP Preprocessing
        nlp = full_nlp_pipeline(user_input)
        polished = nlp["polished"]
        intent = nlp.get("intent", "general")
        entities = nlp.get("entities", {})

        print(f"[NLP] Intent={intent}, Entities={entities}")

        # OS Context
        os_data = skill.execute("os_context", raw_input=polished)
        print(f"[OS CONTEXT] Active Window: {os_data['active_window']}, Top Apps: {os_data['running_apps']}")

        # Rewrite to commands
        rewritten = hybrid_rewrite(polished)

        # No command detected → casual response
        if not rewritten or "^" not in rewritten:
            reply = hybrid_casual(polished, intent)
            print(f"[AI] {reply}")
            continue

        # Execute commands
        commands = [c.strip() for c in rewritten.split(";") if c.strip()]
        for cmd in commands:
            try:
                skill.execute(cmd, raw_input=polished)
                record_task(polished, cmd, "success")

            except KeyError:
                print(f"[AUTO] Creating skill for: {cmd}")
                try:
                    adaptive_auto_coder(cmd)
                    skill.execute(cmd, raw_input=polished)
                    record_task(polished, cmd, "auto-created")
                    learn_user_pattern(cmd)
                except Exception as e:
                    print(f"[ERROR] Auto-skill failed: {e}")
                    record_task(polished, cmd, "failed")

            except Exception as e:
                print(f"[ERROR] {cmd}: {e}")
                record_task(polished, cmd, "failed")

# ===============================
# BOOTSTRAP
# ===============================
if __name__ == "__main__":
    load_plugins(skill)
    main()
