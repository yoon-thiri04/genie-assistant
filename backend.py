from fastapi import FastAPI, HTTPException, UploadFile, File,Depends
from fastapi.middleware.cors import CORSMiddleware
from db import db
import bcrypt, datetime, os

from sentence_transformers import SentenceTransformer
import chromadb
from utils.authentication import call_llm, generate_jwt_token,decode_jwt_token
from fastapi import HTTPException,status
from utils.password import verify_password,hash_password
import json

# Chroma setup
chroma_client = chromadb.Client()
embedding_model = SentenceTransformer("./models/all-MiniLM-L6-v2")  


app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# -------- AUTH --------
@app.post("/register")
async def register(email: str, password: str,confirm_password:str, name: str):
    
    if await db.users.find_one({"email":email}):
        raise HTTPException(status_code=400, detail="Email exists")
    
    hashed_password = hash_password(password)
    if password != confirm_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Passwords do not match")

    user = {"email": email, "password": hashed_password, "name": name}
    await db.users.insert_one(user)
    return {"msg": "User registered"}

@app.post("/login")
async def login(email: str, password: str):
    db_user = await db.users.find_one({"email": email})
    print("DB user", db_user)
    print(db_user["password"])
    
    if not db_user or not verify_password(password, db_user["password"]):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Credential!")
    
    token =generate_jwt_token(
        {
            "user_id":str(db_user["_id"]),
            "email":db_user["email"],
        }
    )
    print("TOken created", token)
    return {"token": token, "name": db_user["name"]}

@app.post("/process")
async def process_command(token: str, message: str, file: UploadFile = None):
    user_payload = decode_jwt_token(token)
    if not user_payload:
        raise HTTPException(401, "Invalid token")
    user_id = user_payload["user_id"]

   
    pending = await db.pending_actions.find_one({"user_id": user_id})
    if pending:
        
        if pending["type"] == "add_note":
            title = message if message.strip() else "Untitled"
            folder = pending.get("folder", "General")
            note_doc = {"user_id": user_id, "folder": folder, "title": title,
                        "text": pending["content"], "created": datetime.datetime.utcnow()}
            await db.notes.insert_one(note_doc)

            
            coll = chroma_client.get_or_create_collection(name=f"{user_id}_notes")
            emb = embedding_model.encode(pending["content"]).tolist()
            coll.add(documents=[pending["content"]], metadatas=[{"folder": folder, "title": title}], ids=[str(note_doc["_id"])])

            await db.pending_actions.delete_one({"_id": pending["_id"]})
            return {"reply": f"Note '{title}' saved under '{folder}'. Do you need anything else?"}

        elif pending["type"] == "add_file":
            if not file:
                raise HTTPException(400, "No file uploaded to complete save")
            title = message if message.strip() else file.filename
            folder = pending.get("folder", "General")

            os.makedirs("uploads", exist_ok=True)
            filepath = f"uploads/{user_id}_{file.filename}"
            with open(filepath, "wb") as f:
                f.write(file.file.read())

            file_doc = {"user_id": user_id, "folder": folder, "title": title,
                        "filename": file.filename, "filepath": filepath, "created": datetime.datetime.utcnow()}
            await db.files.insert_one(file_doc)

            
            coll = chroma_client.get_or_create_collection(name=f"{user_id}_files")
            emb = embedding_model.encode(title).tolist()
            coll.add(documents=[title], metadatas=[{"folder": folder, "title": title, "filepath": filepath}], ids=[str(file_doc["_id"])])

            await db.pending_actions.delete_one({"_id": pending["_id"]})
            return {"reply": f"File '{title}' saved under '{folder}'. Do you need anything else?"}

    
        few_shot_prompt = f"""
You are an assistant that extracts structured commands from user input.
Always respond ONLY in JSON with keys:
{{
  "intent": "add_note / add_file / store_user_info / chat / list_storage / retrieve_item",
  "type": "note / file / info",  
  "title": "...",
  "folder": "...",
  "content": "...",
  "file_attached": true/false,
  "keywords": []
}}

Examples: 
1) 
User input: "Show me my note about JVM" 
Output JSON: 
{{ 
 "intent": "retrieve_item",
 "type": "note", "title": "",
   "folder": "", "content": "",
     "file_attached": false, "keywords": ["JVM"] }}

2) 
User input: "Save this image as 'me with mom'" 
Output JSON: 
{{ "intent": "add_file",
 "type": "file",
   "title": "me with mom",
     "folder": "", "content": "", 
     "file_attached": true, 
     "keywords": ["me","mom"] 
     }} 
3) 
User input: "Remember that my friend Su is a SWE engineer" 
Output JSON: 
{{ "intent": "store_user_info",
 "type": "info", "title": "",
   "folder": "",
     "content": "my friend Su is a SWE engineer",
       "file_attached": false,
         "keywords": ["Su","SWE engineer"] 
         }} 
Now process this user input: "{message}"
"""

    # Call LLM 
    
    try: 
        data = json.loads(call_llm(user_id,few_shot_prompt))
        print(data)
    except:
        
        data = {"intent": "chat", 
                "content": message, 
                "file_attached": bool(file),
                  "keywords": message.split()[:5]}

    print(data)
    if data["intent"] == "add_note":
        content = data.get("content", message)
        
        if not data.get("title"):
            await db.pending_actions.insert_one({"user_id": user_id, "type": "add_note", "content": content, "folder": data.get("folder","General"), "created": datetime.datetime.utcnow()})
            return {"reply": "Do you want to give a title to save this note? If not, it will be saved under General."}
        
        title = data["title"]
        folder = data.get("folder", "General")
        note_doc = {"user_id": user_id, "folder": folder, "title": title, "text": content, "created": datetime.datetime.utcnow()}
        await db.notes.insert_one(note_doc)
        coll = chroma_client.get_or_create_collection(name=f"{user_id}_notes")
        emb = embedding_model.encode(content).tolist()
        coll.add(documents=[content], metadatas=[{"folder": folder, "title": title}], ids=[str(note_doc["_id"])])
        return {"reply": f"Note '{title}' saved under '{folder}'. Do you need anything else?"}

    elif data["intent"] == "add_file":
        
        if not file:
            return {"reply": "Please upload the file to save."}
        if not data.get("title"):
            await db.pending_actions.insert_one({"user_id": user_id, "type": "add_file", "content": "", "folder": data.get("folder","General"), "created": datetime.datetime.utcnow()})
            return {"reply": f"Do you want to give a title to the file '{file.filename}'? Otherwise, it will be saved with its filename."}
        
        title = data["title"]
        folder = data.get("folder", "General")
        os.makedirs("uploads", exist_ok=True)
        filepath = f"uploads/{user_id}_{file.filename}"
        with open(filepath, "wb") as f_obj:
            f_obj.write(file.file.read())
        file_doc = {"user_id": user_id, "folder": folder, "title": title, "filename": file.filename, "filepath": filepath, "created": datetime.datetime.utcnow()}
        await db.files.insert_one(file_doc)
        coll = chroma_client.get_or_create_collection(name=f"{user_id}_files")
        emb = embedding_model.encode(title).tolist()
        coll.add(documents=[title], metadatas=[{"folder": folder, "title": title, "filepath": filepath}], ids=[str(file_doc["_id"])])
        return {"reply": f"File '{title}' saved under '{folder}'. Do you need anything else?"}

    elif data["intent"] == "store_user_info":
        content = data.get("content", message)
        doc = {"user_id": user_id, "content": content, "created": datetime.datetime.utcnow()}
        await db.user_info.insert_one(doc)
        coll = chroma_client.get_or_create_collection(name=f"{user_id}_info")
        emb = embedding_model.encode(content).tolist()
        coll.add(documents=[content], metadatas=[{}], ids=[str(doc["_id"])])
        return {"reply": "Got it! Your info has been stored. Do you need anything else?"}

    elif data["intent"] == "list_storage":
        notes = await db.notes.find({"user_id":user_id}).to_list(None)
        files = await db.files.find({"user_id": user_id}).to_list(None)
        info = await db.user_info.find({"user_id": user_id}).to_list(None)
        storage = {}
        for n in notes: storage.setdefault(n.get("folder","General"),[]).append({"type":"note","title":n["title"],"content":n["text"]})
        for f in files: storage.setdefault(f.get("folder","General"),[]).append({"type":"file","title":f["title"],"filepath":f["filepath"]})
        storage["User Info"] = [{"type":"info","content":i["content"]} for i in info]
        return {"reply": storage}

    elif data["intent"] == "retrieve_item":
        keywords = data.get("keywords", []) or message.split()[:5]
        item_type = data.get("type", "note")
        coll_name = f"{user_id}_notes" if item_type=="note" else f"{user_id}_files" if item_type=="file" else f"{user_id}_info"
        coll = chroma_client.get_or_create_collection(name=coll_name)
        emb = embedding_model.encode(" ".join(keywords)).tolist()
        results = coll.query(query_embeddings=[emb], n_results=5)
        items=[]
        for doc, meta in zip(results['documents'][0], results['metadatas'][0]):
            if item_type=="note": items.append({"title":meta.get("title","Untitled"),"content":doc})
            elif item_type=="file": items.append({"title":meta.get("title","Untitled"),"filepath":meta.get("filepath","")})
            elif item_type=="info": items.append({"content":doc})
        return {"reply": items}

    else:
        
        context_text = ""
        for coll_name in [f"{user_id}_notes", f"{user_id}_files", f"{user_id}_info"]:
            coll = chroma_client.get_or_create_collection(name=coll_name)
            results = coll.query(query_embeddings=[embedding_model.encode(message).tolist()], n_results=5)
            if results['documents'][0]: context_text += "\n".join(results['documents'][0]) + "\n"
        chat_prompt = f"""
You are a friendly personal assistant. Greet the user and ask what they want to store or retrieve.
Use the following context to answer questions:
{context_text}
User: {message}
Assistant:"""
        answer = call_llm(user_id,chat_prompt)
        return {"reply": answer}
