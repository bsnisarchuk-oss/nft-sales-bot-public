import asyncio
import json
import os

from dotenv import load_dotenv

load_dotenv()
from utils.tonapi import TonApiClient  # noqa: E402


async def check():
    client = TonApiClient(
        base_url=os.getenv('TONAPI_BASE_URL', 'https://tonapi.io'),
        api_key=os.getenv('TONAPI_KEY', ''),
        min_interval=0.3,
    )
    import sqlite3
    conn = sqlite3.connect('data/bot.db')
    rows = conn.execute(
        'SELECT DISTINCT cc.collection_raw, col.name FROM chat_collections cc '
        'JOIN collections col ON col.raw = cc.collection_raw'
    ).fetchall()
    conn.close()

    # Check ALL action types across all collections with full structure
    for raw, name in rows:
        print(f'\n{"="*60}')
        print(f'Collection: {name} ({raw[:30]}...)')
        print(f'{"="*60}')
        payload = await client.get_account_events(raw, limit=10)
        events = payload.get('events') or []

        for ev in events[:3]:
            actions = ev.get('actions') or []
            for a in actions:
                atype = a.get('type', '')
                print(f'\n--- Action type: {atype} ---')
                # Print the action-specific data
                action_data = a.get(atype, {})
                if isinstance(action_data, dict):
                    # Print key fields
                    for k, v in action_data.items():
                        if isinstance(v, dict):
                            print(f'  {k}: {json.dumps(v, ensure_ascii=False)[:200]}')
                        elif isinstance(v, str) and len(v) > 200:
                            print(f'  {k}: {v[:200]}...')
                        else:
                            print(f'  {k}: {v}')
            print('---')

    # Also check if AuctionBid has price info
    print(f'\n{"="*60}')
    print('SPECIAL: Telegram Usernames AuctionBid details')
    print(f'{"="*60}')
    username_raw = '0:80d78a35f955a14b679faa887ff4cd5bfc0f43b4a4eea2a7e6927f3701b273c2'
    payload = await client.get_account_events(username_raw, limit=5)
    events = payload.get('events') or []
    for ev in events[:3]:
        print('\nFull event:')
        print(json.dumps(ev, indent=2, ensure_ascii=False)[:2000])

    await client.close()

asyncio.run(check())
