def get_gemini_heartbeat():
    try:
        client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
        prompt = (
            "You are Sensei 2MUCH813. The market is quiet. "
            "1. Confirm we are still scanning for the GOALDEN setup. "
            "2. Teach a random complex technical indicator. "
            "Keep it hyped and professional. Use emojis like 🦅, 🎯, and ⚡️."
        )
        # 2026 Model ID Correction:
        response = client.models.generate_content(
            model="gemini-3-flash-preview", 
            contents=prompt
        )
        return response.text
    except Exception as e:
        return f"📡 HEARTBEAT: Scanning for the GOALDEN setup... (Sensei is meditating. System: {e})"
