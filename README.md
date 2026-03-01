# Hackathon
Hack to the Future 

Challenge 
Image -> Extract -> Matching with DWH -> RAG -> Answer with citations + confidence

Requirements
•	Multimodal vision model για extraction πληροφοριών από εικόνα bill (PNG/JPG)
•	Structured data extraction σε machine-readable format (JSON/XML) με entities: customer ID, billing period, line items, consumption, tariff
•	Matching engine για σύνδεση extracted IDs με DWH tables (Billing_Header, Billing_Lines, Customer_Context)
•	Χειρισμός cases: 1 match / κανένα match
•	RAG pipeline με retrieval queries, metadata filters και knowledge corpus (FAQs, policies, regulated charges)
•	Confidence scoring σε κάθε στάδιο (extraction, matching, retrieval, answer)
•	Citation mechanism — κάθε απάντηση να references συγκεκριμένα documents
•	Hallucination prevention: το LLM να απαντά ΜΟΝΟ βάσει retrieved context
•	Modular αρχιτεκτονική (κάθε step ανεξάρτητο component)
•	API ή application interface για demo

Δυνατότητες της Εφαρμογής
•	Upload εικόνας λογαριασμού και αυτόματη ανάλυσή της
•	Εμφάνιση structured summary των extracted δεδομένων
•	Αυτόματη αναγνώριση και σύνδεση με το προφίλ πελάτη από το DWH
•	Εξήγηση ανάλυσης χρεώσεων (energy / regulated / taxes)
•	Σύγκριση τρέχοντος λογαριασμού με ιστορικό (avg 6 μηνών, last 3 bills)
•	Εντοπισμός λόγων αύξησης λογαριασμού
•	Grounded απαντήσεις με citations από knowledge base
•	Clarifying questions όταν υπάρχει αμφιβολία ή ελλιπή στοιχεία
•	Υποστήριξη για residential και business segment
•	(Bonus) Multi-query retrieval και re-ranking αποτελεσμάτων
•	(Bonus) Explainability UI — εμφάνιση γιατί έγινε κάθε retrieval decision
•	(Bonus) Hallucination detection flag στην απάντηση
