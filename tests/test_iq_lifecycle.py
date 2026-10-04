"""Control interleavings at the last-viewer boundary without network timing assumptions."""
import asyncio
from types import SimpleNamespace

import pytest
from iq import IQDistributor
from tests.test_stream import frame
from iq_protocol import validate_frame


@pytest.mark.asyncio
async def test_new_viewer_cancels_a_pending_idle_notification_without_reconnecting():
    sockets = []
    class Socket:
        def __init__(self):
            self.incoming = asyncio.Queue()
            self.receiving = asyncio.Event()
            self.closed = False
        def setsockopt(self, *_): pass
        def connect(self, _): pass
        def recv(self):
            self.receiving.set()
            return asyncio.create_task(self.incoming.get())
        def close(self, **_): self.closed = True
    def socket(_):
        result = Socket()
        sockets.append(result)
        return result
    distributor = IQDistributor(SimpleNamespace(socket=socket), 'unused')
    queue = distributor.subscribe()
    task = asyncio.create_task(distributor.run())
    try:
        for _ in range(10):
            if sockets: break
            await asyncio.sleep(0)
        await sockets[0].receiving.wait()
        # Let the idle waiter finish, then join before the receive loop handles it.
        distributor.unsubscribe(queue)
        await asyncio.sleep(0)
        queue = distributor.subscribe()
        for _ in range(10): await asyncio.sleep(0)
        assert len(sockets) == 1 and not sockets[0].closed
        sockets[0].incoming.put_nowait(frame())
        assert validate_frame(await asyncio.wait_for(queue.get(), 1)).epoch == 1
    finally:
        distributor.unsubscribe(queue)
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
    assert sockets[0].closed and not distributor.diagnostics()['receiving']


@pytest.mark.asyncio
async def test_shutdown_during_idle_cleanup_always_closes_the_upstream_socket():
    receiving = asyncio.Event()
    cancelling = asyncio.Event()
    class Socket:
        closed = False
        def setsockopt(self, *_): pass
        def connect(self, _): pass
        async def recv(self):
            receiving.set()
            try:
                await asyncio.Event().wait()
            finally:
                cancelling.set()
                await asyncio.Event().wait()
        def close(self, **_): self.closed = True
    socket = Socket()
    distributor = IQDistributor(SimpleNamespace(socket=lambda _: socket), 'unused')
    queue = distributor.subscribe()
    task = asyncio.create_task(distributor.run())
    try:
        await asyncio.wait_for(receiving.wait(), 1)
        distributor.unsubscribe(queue)
        await asyncio.wait_for(cancelling.wait(), 1)
        # Application shutdown cancels run() while it awaits receiver cleanup.
        task.cancel()
        await asyncio.wait_for(asyncio.gather(task, return_exceptions=True), 1)
        assert socket.closed and distributor.socket is None
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
