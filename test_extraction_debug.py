"""Test extraction to see what's being captured."""

from src.agents.adk.extraction_agent import ExtractionAgent
import json

# Sample text with phone, email, activities
test_text = """
Hi, I'm Rajesh Kumar from Mumbai. My phone is 98765-43210 and email is rajesh@example.com.
I volunteer at the temple every Sunday and enjoy yoga and meditation.
I also participate in community service projects.
"""

print("Testing Extraction Agent...")
print("=" * 60)
print(f"Input text:\n{test_text}")
print("=" * 60)

agent = ExtractionAgent(model_id="ollama/llama3")
result = agent.extract(test_text)

print(f"\nExtraction Success: {result.success}")
print(f"Speaker: {result.speaker_name}")
print(f"\nPersons extracted: {len(result.persons)}")

for i, person in enumerate(result.persons, 1):
    print(f"\n--- Person {i} ---")
    print(f"Name: {person.name}")
    print(f"Gender: {person.gender}")
    print(f"Age: {person.age}")
    print(f"Location: {person.location}")
    print(f"Occupation: {person.occupation}")
    print(f"Phone: {person.phone}")  # NEW FIELD
    print(f"Email: {person.email}")  # NEW FIELD
    print(f"Interests: {person.interests}")  # NEW FIELD
    print(f"Is Speaker: {person.is_speaker}")

print(f"\nRelationships extracted: {len(result.relationships)}")

if result.error:
    print(f"\nError: {result.error}")
