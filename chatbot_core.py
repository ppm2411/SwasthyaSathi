import pandas as pd
import json
from datetime import datetime
import ollama  # ✅ Using Ollama locally

# 📂 File paths
HOSPITAL_PATH = "datasets/modified_hospital_data.csv"
BED_PATH = "datasets/bed_inventory.csv"
DOCTOR_PATH = "datasets/doctor_schedule.csv"
DISCHARGED_PATH = "datasets/discharged_patients.csv"
MEDICINE_PATH = "datasets/mock_medicine_inventory_extended.csv"


# 📥 Load datasets
def load_data():
    hospital_df = pd.read_csv(HOSPITAL_PATH)
    bed_df = pd.read_csv(BED_PATH)
    doctor_df = pd.read_csv(DOCTOR_PATH)
    medicine_df = pd.read_csv(MEDICINE_PATH)
    discharged_df = pd.read_csv(DISCHARGED_PATH)
    return hospital_df, bed_df, doctor_df, medicine_df, discharged_df


# 🧠 Intent Parser using Ollama (Mistral)
def analyze_query_with_llm(user_input):
    system_prompt = """
You are a hospital assistant chatbot. Return intent and entities in strict JSON only.

Supported intents:
- bed_status
- doctor_info
- medicine_info
- patient_status
- discharge
- update_doctor_availability

Respond only like this:
{
  "intent": "doctor_info",
  "entities": {
    "doctor": "Dr. A. Patel"
  }
}
No explanation. No markdown. No prose.
"""
    try:
        response = ollama.chat(
            model="mistral",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input},
            ],
        )
        content = response["message"]["content"].strip()
        start = content.find("{")
        end = content.rfind("}")
        json_block = content[start : end + 1]
        if "'" in json_block and '"' not in json_block:
            json_block = json_block.replace("'", '"')
        return json.loads(json_block)
    except Exception as e:
        return {"intent": "unknown", "entities": {}, "error": str(e)}


# 💬 Main Handler
def get_response(user_input):
    translations = {
        "kete bed available achhi": "how many beds are available",
        "paracetamol achi ki": "is paracetamol available",
        "ramesh kie": "who is ramesh",
        "discharge karideba ramesh ku": "discharge ramesh",
        "doctor sahu available nuhanti": "doctor sahu not available",
        "general ward re kete bed achhi": "how many beds are available in general ward",
        "is dr. c. mishra": "is Dr. C. Mishra available?",
    }

    if user_input.lower().startswith("is dr.") and not user_input.lower().endswith(
        "available"
    ):
        user_input += " available?"

    user_input = translations.get(user_input.lower().strip(), user_input)

    hospital_df, bed_df, doctor_df, medicine_df, discharged_df = load_data()
    result = analyze_query_with_llm(user_input)

    intent = result.get("intent")
    entities = result.get("entities", {})

    # 🛏️ BED STATUS
    if intent == "bed_status":
        ward = entities.get("ward", "").strip().lower()

        # Clean up for consistent filtering
        bed_df["status"] = bed_df["status"].astype(str).str.strip().str.lower()
        bed_df["ward"] = bed_df["ward"].astype(str).str.strip().str.lower()

        filtered = bed_df[bed_df["status"] == "available"]
        if ward:
            filtered = filtered[filtered["ward"] == ward]

        if filtered.empty:
            return "❌ No available beds."

        # Format as table
        table = "| Bed No | Ward | Type |\n|--------|------|------|\n"
        for _, row in filtered.iterrows():
            table += f"| {row['bed_no']} | {row['ward'].title()} | {row['bed_type'].title()} |\n"
        return f"🏥 **Available Beds:**\n\n{table}"

    # 👨‍⚕️ DOCTOR INFO
    elif intent == "doctor_info":
        available = doctor_df[
            doctor_df["is_available"].str.lower().str.strip() == "yes"
        ]
        doc_name = entities.get("doctor", "").strip().lower()
        if doc_name:
            match = available[
                available["doctor_name"].str.lower().str.contains(doc_name)
            ]
            if not match.empty:
                row = match.iloc[0]
                return f"✅ Yes, {row['doctor_name']} is available in {row['ward']}."
            return f"❌ {entities.get('doctor')} is not currently available."
        return (
            f"👨‍⚕️ Available Doctors:\n{available[['doctor_name', 'ward', 'shift_start', 'shift_end']].to_string(index=False)}"
            if not available.empty
            else "❌ No doctors available."
        )

    # 💊 MEDICINE INFO
    elif intent == "medicine_info":
        med_name = entities.get("medicine", "").lower()
        match = medicine_df[
            medicine_df["medicine_name"].str.lower().str.contains(med_name)
        ]
        if match.empty:
            return "❌ Medicine not found."
        row = match.iloc[0]
        return (
            f"💊 {row['medicine_name']} | Category: {row['category']} | "
            f"Quantity Available: {row['quantity_available']} | Expiry: {row['expiry_date']}"
        )

    # 🧍 PATIENT STATUS
    elif intent == "patient_status":
        name = entities.get("name", "").lower()
        match = hospital_df[hospital_df["name"].str.lower() == name]
        if match.empty:
            return "❌ Patient not found."
        row = match.iloc[0]
        return (
            f"👤 {row['name']} is in Ward {row['ward']}, Bed {row['bed_no']}, "
            f"Disease: {row['status']}, Admitted on: {row['admitted_on']}, "
            f"Condition: {row['critical']}"
        )

    # 🏁 DISCHARGE PATIENT
    elif intent == "discharge":
        name = entities.get("name", "").lower()
        match = hospital_df[hospital_df["name"].str.lower() == name]
        if match.empty:
            return "❌ Patient not found for discharge."
        row = match.iloc[0]
        discharge_row = row.copy()
        discharge_row["discharge_date"] = datetime.today().strftime("%Y-%m-%d")
        discharged_df = pd.concat(
            [discharged_df, pd.DataFrame([discharge_row])], ignore_index=True
        )
        hospital_df = hospital_df[hospital_df["name"].str.lower() != name]
        hospital_df.to_csv(HOSPITAL_PATH, index=False)
        discharged_df.to_csv(DISCHARGED_PATH, index=False)
        return f"✅ {row['name']} has been discharged."

    # 🚫 UPDATE DOCTOR
    elif intent == "update_doctor_availability":
        doc_name = entities.get("doctor", "")
        if not doc_name:
            return "❌ Doctor name missing."
        doctor_df.loc[
            doctor_df["doctor_name"].str.lower() == doc_name.lower(), "is_available"
        ] = "No"
        try:
            doctor_df.to_csv(DOCTOR_PATH, index=False)
        except PermissionError:
            return "🚫 Could not update doctor availability – file is locked."
        return f"🚫 {doc_name} marked as unavailable."

    # ❓ Unknown intent fallback
    error = result.get("error", "")
    return (
        f"🤖 Sorry, I didn't understand the query. {f'Error: {error}' if error else ''}"
    )
