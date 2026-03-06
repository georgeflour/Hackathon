
from fastapi import APIRouter
from pydantic import BaseModel
# import torch
# from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
# from peft import PeftModel

BASE_MODEL_ID = "Qwen/Qwen2.5-3B-Instruct"
ADAPTER_PATH = "./qwen-billing-lora"

router = APIRouter()

# bnb_config = BitsAndBytesConfig(
#     load_in_4bit=True,
#     bnb_4bit_compute_dtype=torch.bfloat16,
#     bnb_4bit_quant_type="nf4",
#     bnb_4bit_use_double_quant=True,
# )

# tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL_ID)

# try:
#     print("Attempting to load model with BitsAndBytes (GPU required)...")
#     base_model = AutoModelForCausalLM.from_pretrained(
#         BASE_MODEL_ID,
#         device_map="auto",
#         torch_dtype=torch.bfloat16,
#         quantization_config=bnb_config,
#     )
#     print("Successfully loaded model with 4-bit quantization.")
# except Exception as e:
#     print(f"Failed to load with BitsAndBytes config (likely on Windows/CPU). Falling back. Error: {e}")
#     base_model = AutoModelForCausalLM.from_pretrained(
#         BASE_MODEL_ID,
#         device_map="cpu",
#     )
#     print("Loaded model with standard CPU precision.")

# try:
#     model = PeftModel.from_pretrained(
#         base_model,
#         ADAPTER_PATH,
#     )
#     print("Successfully loaded LoRA weights.")
# except Exception as e:
#     print(f"Failed to load LoRA weights. Error: {e}. Using raw base model instead.")
#     model = base_model

SYSTEM_PROMPT = """
Είσαι βοηθός εξυπηρέτησης πελατών λογαριασμών ενέργειας.
Απαντάς πάντα στα ελληνικά.
Χρησιμοποιείς μόνο τα παρεχόμενα facts από SQL και RAG.
Αν δεν υπάρχουν αρκετά στοιχεία, το λες καθαρά.
Δεν επινοείς αριθμούς, χρεώσεις, ημερομηνίες ή πολιτικές.
"""

class ChatRequest(BaseModel):
    question: str
    rag_context: str = ""
    sql_context: str = ""

@router.post("/chat")
def chat(req: ChatRequest):
    # user_prompt = f"""
    # Ερώτηση χρήστη:
    # {req.question}
    # 
    # Δεδομένα από SQL:
    # {req.sql_context if req.sql_context else "Δεν υπάρχουν."}
    # 
    # Δεδομένα από knowledge base:
    # {req.rag_context if req.rag_context else "Δεν υπάρχουν."}
    # 
    # Οδηγίες:
    # - Απάντησε στα ελληνικά.
    # - Αν τα δεδομένα δεν αρκούν, ζήτησε διευκρίνιση.
    # - Μη χρησιμοποιήσεις εξωτερική γνώση.
    # - Δώσε σύντομη, σαφή απάντηση.
    # """
    # 
    # messages = [
    #     {"role": "system", "content": SYSTEM_PROMPT},
    #     {"role": "user", "content": user_prompt},
    # ]
    # 
    # inputs = tokenizer.apply_chat_template(
    #     messages,
    #     tokenize=True,
    #     add_generation_prompt=True,
    #     return_tensors="pt",
    # ).to(model.device)
    # 
    # with torch.no_grad():
    #     outputs = model.generate(
    #         inputs,
    #         max_new_tokens=400,
    #         do_sample=False,
    #         temperature=0.0,
    #         pad_token_id=tokenizer.eos_token_id,
    #     )
    # 
    # generated = outputs[0][inputs.shape[-1]:]
    # answer = tokenizer.decode(generated, skip_special_tokens=True)

    # Mock response
    answer = "Αυτή είναι μια δοκιμαστική απάντηση (Mock response). Η σύνδεση με το μοντέλο είναι προσωρινά απενεργοποιημένη."
    return {"answer": answer.strip()}
