from openai import OpenAI
import os

# Set your API key directly here OR through environment variable
#openai.api_key = os.getenv("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") or "sk-..."

client = OpenAI(api_key  = "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")

MODEL = "gpt-4o"

system_prompt = """
You are ChatGPT, a large language model trained by OpenAI.
You are helpful and accurate. If unsure, you say so clearly.
Your knowledge cutoff is April 2024, and you do not browse the internet.
"""






def chat_with_gpt(prompt):
    try:
        response = client.chat.completions.create(
               model= MODEL,
               temperature=0.2,
                messages=[
                    {"role": "system", "content": "You are ChatGPT, a large language model trained by OpenAI. You are helpful, honest, and provide answers based on knowledge up to April 2024."},              
                    {"role": "user", "content": prompt}
                    ]
            )

        #return response['choices'][0]['message']['content']
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ Error: {str(e)}"

if __name__ == "__main__":
    while True:
        user_input = input("🧠 You: ")
        if user_input.strip().lower() in ["exit", "quit"]:
            break

        reply = chat_with_gpt(user_input)
        print(f"🤖 GPT-4o: {reply}\n")