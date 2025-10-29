import asyncio
import json
import websockets

async def main():
    uri = "ws://localhost:8000/ws"
    try:
        async with websockets.connect(uri) as ws:
            print('Connected to', uri)
            # Receive initial state
            msg = await ws.recv()
            print('INITIAL_STATE:', msg)

            # Register a test voter
            register = {"action": "register", "voter_id": "TEST123", "name": "Tester"}
            await ws.send(json.dumps(register))
            resp = await ws.recv()
            print('REGISTER_RESP:', resp)

            # Cast a vote for candidate c1
            vote = {"action": "vote", "voter_id": "TEST123", "candidate_id": "c1"}
            await ws.send(json.dumps(vote))
            resp = await ws.recv()
            print('VOTE_RESP:', resp)

            # There may be a broadcast results_update after a successful vote
            try:
                broadcast = await asyncio.wait_for(ws.recv(), timeout=1.5)
                print('BROADCAST:', broadcast)
            except asyncio.TimeoutError:
                print('No extra broadcast received (ok).')

            # Request audit log
            await ws.send(json.dumps({"action": "get_audit"}))
            resp = await ws.recv()
            print('AUDIT_RESP:', resp)

    except Exception as e:
        print('ERROR:', e)

if __name__ == '__main__':
    asyncio.run(main())
