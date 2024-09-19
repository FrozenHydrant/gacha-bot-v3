import asyncio
import threading

def timeformat(time, dayname, hourname, minutename):
    return str(time.days) + dayname + " " + str(time.seconds // 3600) + hourname + " " + str(time.seconds%3600//60) + minutename

# https://stackoverflow.com/questions/63858511/using-threads-in-combination-with-asyncio
class AsyncHelp:
    def _start_async(self):
        loop = asyncio.new_event_loop()
        threading.Thread(target=loop.run_forever).start()
        return loop

    def __init__(self):
        self._loop = self._start_async()

    # Submits awaitable to the event loop, but *doesn't* wait for it to
    # complete. Returns a concurrent.futures.Future which *may* be used to
    # wait for and retrieve the result (or exception, if one was raised)
    def submit_async(self, awaitable):
        return asyncio.run_coroutine_threadsafe(awaitable, self._loop)
