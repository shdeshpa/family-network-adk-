# Testing Guide - Storage Agent & CRM UI

## 🎯 What We Built

1. **Storage Agent** - Automatically stores extracted family data into CRM V2
2. **CRM UI V2** - Beautiful family-based interface to view stored data
3. **Full Pipeline** - Text Input → Extraction → Storage → Display

## 🚀 How to Test

### Step 1: Start the UI

The UI is already running at:
- **http://localhost:8080**

Open this URL in your browser.

### Step 2: Process Some Text

1. Go to the **"📝 Text Input"** tab
2. Enter some family information, for example:

```
My name is Ramesh Kumar from Bangalore.
I am an engineer. My wife Lakshmi Kumar is a doctor.
We have two children: Arun and Divya.
```

3. Click **"🚀 Process"**
4. You'll see:
   - ✅ Extraction results (persons found, relationships)
   - 💾 Storage summary (families created, persons added)
   - Button to "View in CRM →"

### Step 3: View in CRM

1. Click **"View in CRM →"** or go to the **"📇 CRM"** tab
2. You'll see:
   - **Statistics**: Number of families and persons
   - **Family Cards**: Expandable cards grouped by family code (e.g., KUMAR-Bangalore-001)
   - **Member Tables**: All persons in each family with details
   - **Unassigned Section**: Persons without family assignment

### Step 4: Explore Person Details

1. In any person row, click the **"👁️"** (eye) icon
2. A dialog opens showing:
   - Full profile information
   - Contact details
   - Family code
   - Notes (includes "raw mentions" from extraction)
   - Donations (if any)

### Step 5: Test More Examples

Try different text inputs to see how the system groups families:

**Example 1 - Same Family:**
```
Sarah Patel and Raj Patel live in Mumbai.
They have a daughter named Priya Patel.
```
→ Should create PATEL-Mumbai-001 family with 3 members

**Example 2 - Different Family:**
```
John Smith from New York works at Google.
His brother Mike Smith also lives in New York.
```
→ Should add to SMITH-New York family

**Example 3 - Multiple Families:**
```
I'm Dev Sharma from Hyderabad, and my friend
Amit Kumar from Bangalore visited me.
```
→ Should create two separate families:
- SHARMA-Hyderabad
- KUMAR-Bangalore

## 📊 What to Look For

### ✅ Success Indicators:

1. **Extraction works**
   - Persons are correctly identified
   - Relationships are detected

2. **Storage works**
   - Families are automatically created
   - Persons are grouped by surname + city
   - Family codes are generated (SURNAME-CITY-###)

3. **CRM UI shows data**
   - Family cards appear
   - Members are listed under families
   - Person details are viewable

### ⚠️ Known Issues:

1. **Family Grouping**: Some persons may appear in "Unassigned" if:
   - They don't have a clear surname
   - Location is not extracted
   - Solution: Will be refined in future iterations

2. **Duplicate Entries**: Processing the same text twice may create duplicates
   - This is expected for now
   - Search/deduplication coming soon

## 🧪 Quick Test Command

If you want to test programmatically:

```bash
PYTHONPATH=. uv run python tests/test_storage_agent.py
```

This runs the automated test suite showing:
- Storage agent functionality
- Full orchestrator pipeline
- Sample data being stored

## 🔄 Refresh CRM Data

After processing new text:
1. Go to CRM tab
2. Click **"🔄 Refresh"** button
3. New data appears immediately

## 🎨 UI Features

### CRM V2 Tab:
- **V2 (New)** button - Shows family-based CRM
- **V1 (Legacy)** button - Shows old CRM format
- **Search** - Find persons by name
- **Family Filter** - Filter by specific family code
- **View Details** - See complete person information
- **Statistics** - Overview of families and persons

### Text Input Tab:
- **Text Input** - Enter family descriptions
- **Process** - Run through the full pipeline
- **History** - See all past inputs with results
- **Reprocess** - Re-run any previous text

## 🛑 Stop the UI

When done testing:

```bash
# Find the process
ps aux | grep run_ui.py

# Kill it
pkill -f run_ui.py
```

Or just close the terminal.

## 📝 Next Steps

After testing, consider:
1. Debugging family grouping logic (if issues found)
2. Adding edit functionality for persons
3. Adding family creation UI
4. Implementing donation tracking
5. Adding bulk operations (merge, delete, etc.)

## 🐛 Troubleshooting

**UI won't load:**
```bash
# Check if port 8080 is in use
lsof -i :8080

# If needed, kill the process and restart
pkill -f run_ui.py
uv run python run_ui.py
```

**No data showing in CRM:**
- Make sure you processed text first
- Click "🔄 Refresh" in CRM tab
- Check database: `sqlite3 data/crm/crm_v2.db "SELECT * FROM profiles;"`

**Errors during processing:**
- Check that Ollama is running (if using local LLM)
- Check console for error messages
- Try simpler text first

## ✨ Success!

You've now tested the complete Priority 1 implementation:
- ✅ Storage Agent created
- ✅ Orchestrator integrated
- ✅ CRM UI built
- ✅ Full pipeline working

Ready to move to Priority 2 or tackle specific improvements!
