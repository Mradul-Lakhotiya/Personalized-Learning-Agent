import asyncio
from dotenv import load_dotenv
load_dotenv()
from app.Agent.Tools.Database import Database
from app.Agent.Tools.Database import Database
async def main():
    db = Database()
    res = await asyncio.to_thread(db.client.table('user_profiles').select('id').limit(1).execute)
    print(res.data[0]['id'] if res.data else 'No users')
asyncio.run(main())
