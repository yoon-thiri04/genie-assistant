from db import db

users_collection = db["users"]
async def get_user_by_email(email:str):
    user = await users_collection.find_one(
        {"email":email}
    )
    if user:
        return user
    return None
