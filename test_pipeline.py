"""Manual test script for MCP pipeline."""

import asyncio
from src.mcp.client import call_nlp_tool, call_graph_tool


async def test_nlp():
    print("=" * 50)
    print("NLP TOOLS TEST")
    print("=" * 50)
    
    # Test detect_language
    result = await call_nlp_tool("detect_language", {"text": "Maza bhau Pune madhe rahto"})
    print(f"detect_language: {result}")
    
    # Test infer_gender
    result = await call_nlp_tool("infer_gender", {"name": "Padma"})
    print(f"infer_gender(Padma): {result}")
    
    result = await call_nlp_tool("infer_gender", {"name": "Ramesh"})
    print(f"infer_gender(Ramesh): {result}")
    
    # Test normalize_relation
    result = await call_nlp_tool("normalize_relation", {"term": "bhau"})
    print(f"normalize_relation(bhau): {result}")


async def test_graph():
    print("\n" + "=" * 50)
    print("GRAPH TOOLS TEST")
    print("=" * 50)
    
    # Add persons
    print("\nAdding persons...")
    r1 = await call_graph_tool("add_person", {"name": "Test Person 1", "gender": "M", "location": "Mumbai"})
    print(f"  add_person: {r1}")
    
    r2 = await call_graph_tool("add_person", {"name": "Test Person 2", "gender": "F", "location": "Mumbai"})
    print(f"  add_person: {r2}")
    
    # Add relationship
    print("\nAdding relationship...")
    r3 = await call_graph_tool("add_spouse", {"person1": "Test Person 1", "person2": "Test Person 2"})
    print(f"  add_spouse: {r3}")
    
    # Query
    print("\nQuerying graph...")
    persons = await call_graph_tool("get_all_persons", {})
    print(f"  Persons count: {persons.get('count', 0)}")
    for p in persons.get('persons', []):
        print(f"    - {p['name']} ({p.get('gender', '?')}) @ {p.get('location', '?')}")
    
    rels = await call_graph_tool("get_all_relationships", {})
    print(f"  Relationships count: {rels.get('count', 0)}")
    for r in rels.get('relationships', []):
        print(f"    - {r['from']} --{r.get('specific', r.get('type'))}--> {r['to']}")


async def cleanup():
    print("\n" + "=" * 50)
    print("CLEANUP")
    print("=" * 50)
    
    from src.graph import FamilyGraph
    graph = FamilyGraph()
    
    for p in graph.get_all_persons():
        if p.name.startswith("Test Person"):
            graph.delete_person(p.name)
            print(f"  Deleted: {p.name}")


async def main():
    await test_nlp()
    await test_graph()
    
    input("\nPress Enter to cleanup test data...")
    await cleanup()


if __name__ == "__main__":
    asyncio.run(main())
