import os
import sys

# Ensure project root is in the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai.ai_engine import ask_ai, ask_ai_stream

def test_inference():
    print("=== Testing ask_ai (Non-streaming) ===")
    response = ask_ai("Write a one-sentence joke about programming.", save_to_memory=False, include_history=False)
    print(f"\nAI Response:\n{response}\n")

    print("=== Testing ask_ai_stream (Streaming) ===")
    print("AI: ", end="", flush=True)
    response_stream = ask_ai_stream("What is 1 + 1?", save_to_memory=False, include_history=False)
    print(f"\nAI Response Stream:\n{response_stream}\n")

if __name__ == "__main__":
    test_inference()
