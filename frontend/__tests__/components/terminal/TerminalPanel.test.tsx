import React from 'react'
import { render, screen, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { TerminalDrawer } from '@/components/terminal/TerminalDrawer'
import { TerminalContext } from '@/components/terminal/TerminalContext'

// ── Mock icons ────────────────────────────────────────────────────────────────

jest.mock('@hugeicons/react', () => ({
  HugeiconsIcon: ({ className }: { className?: string }) => (
    <span className={className} data-testid="icon" />
  ),
}))

jest.mock('@hugeicons/core-free-icons', () => ({
  RefreshIcon: 'RefreshIcon',
  Cancel01Icon: 'Cancel01Icon',
  MinusSignIcon: 'MinusSignIcon',
  ArrowUp01Icon: 'ArrowUp01Icon',
}))

// ── Mock xterm modules ────────────────────────────────────────────────────────

const mockWrite = jest.fn()
const mockOpen = jest.fn()
const mockLoadAddon = jest.fn()
const mockDispose = jest.fn()
const mockOnData = jest.fn()
const mockOnResize = jest.fn()
const mockOnSelectionChange = jest.fn()
const mockHasSelection = jest.fn().mockReturnValue(false)
const mockGetSelection = jest.fn().mockReturnValue('')
const mockScrollToBottom = jest.fn()
const mockAttachCustomKeyEventHandler = jest.fn()

jest.mock('@xterm/xterm', () => ({
  Terminal: jest.fn().mockImplementation(() => ({
    open: mockOpen,
    loadAddon: mockLoadAddon,
    write: mockWrite,
    dispose: mockDispose,
    onData: mockOnData,
    onResize: mockOnResize,
    onSelectionChange: mockOnSelectionChange,
    hasSelection: mockHasSelection,
    getSelection: mockGetSelection,
    scrollToBottom: mockScrollToBottom,
    attachCustomKeyEventHandler: mockAttachCustomKeyEventHandler,
  })),
}))

jest.mock('@xterm/addon-fit', () => ({
  FitAddon: jest.fn().mockImplementation(() => ({ fit: jest.fn() })),
}))

jest.mock('@xterm/addon-web-links', () => ({
  WebLinksAddon: jest.fn().mockImplementation(() => ({})),
}))

// ── Mock WebSocket ────────────────────────────────────────────────────────────

type WsHandler = ((e: MessageEvent | CloseEvent | Event) => void) | null

class MockWebSocket {
  static OPEN = 1
  readyState = MockWebSocket.OPEN
  binaryType = 'blob'
  onopen: WsHandler = null
  onmessage: WsHandler = null
  onclose: WsHandler = null
  onerror: WsHandler = null
  send = jest.fn()
  close = jest.fn()
}

let wsInstance: MockWebSocket

const MockWebSocketConstructor = jest.fn().mockImplementation(() => {
  wsInstance = new MockWebSocket()
  return wsInstance
})
// @ts-expect-error mock static
MockWebSocketConstructor.OPEN = 1

// ── Helper: render drawer in open state via context ───────────────────────────

function renderOpenDrawer() {
  const ctx = {
    open: true,
    toggle: jest.fn(),
    show: jest.fn(),
    hide: jest.fn(),
  }
  return {
    ...render(
      <TerminalContext.Provider value={ctx}>
        <TerminalDrawer />
      </TerminalContext.Provider>,
    ),
    ctx,
  }
}

async function flushEffects() {
  await act(async () => {
    await Promise.resolve()
    await Promise.resolve()
    await Promise.resolve()
  })
}

// ── Setup ─────────────────────────────────────────────────────────────────────

beforeEach(() => {
  jest.clearAllMocks()
  global.fetch = jest.fn().mockResolvedValue({
    ok: true,
    json: async () => ({ token: 'test-token' }),
  } as Response)
  // @ts-expect-error mock global WebSocket
  global.WebSocket = MockWebSocketConstructor
})

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('TerminalDrawer', () => {
  it('is hidden (aria-hidden) when closed', async () => {
    const ctx = { open: false, toggle: jest.fn(), show: jest.fn(), hide: jest.fn() }
    const { container } = render(
      <TerminalContext.Provider value={ctx}>
        <TerminalDrawer />
      </TerminalContext.Provider>,
    )
    await flushEffects()
    // Drawer is always mounted but aria-hidden when closed
    expect(container.firstChild).toHaveAttribute('aria-hidden', 'true')
  })

  it('shows title bar when open', async () => {
    renderOpenDrawer()
    await flushEffects()
    expect(screen.getByText('bash — server')).toBeInTheDocument()
  })

  it('does not show Reconnect button when connecting or connected', async () => {
    renderOpenDrawer()
    await flushEffects()
    await act(async () => { wsInstance?.onopen?.(new Event('open')) })
    expect(screen.queryByText('Reconnect')).not.toBeInTheDocument()
  })

  it('shows Reconnect button after ws.onclose fires', async () => {
    renderOpenDrawer()
    await flushEffects()
    await act(async () => { wsInstance?.onclose?.(new CloseEvent('close')) })
    expect(screen.getByRole('button', { name: /Reconnect now/i })).toBeInTheDocument()
    expect(screen.getByText(/Reconnecting|Disconnected|Failed/i)).toBeInTheDocument()
  })

  it('shows compact SSO hint and details trigger when SSO output detected', async () => {
    renderOpenDrawer()
    await flushEffects()

    await act(async () => {
      wsInstance?.onmessage?.({
        data: 'Open the browser to https://device.sso.ap-southeast-3.amazonaws.com/ and enter code ABCD-EFGH',
      } as unknown as MessageEvent)
    })

    expect(screen.getByText(/SSO Login detected/i)).toBeInTheDocument()
    expect(screen.getByText(/View details/i)).toBeInTheDocument()
  })

  it('close button calls hide()', async () => {
    const { ctx } = renderOpenDrawer()
    await flushEffects()
    await act(async () => {
      await userEvent.click(screen.getByLabelText('Close terminal'))
    })
    expect(ctx.hide).toHaveBeenCalled()
  })

  it('minimize button toggles label', async () => {
    renderOpenDrawer()
    await flushEffects()
    const minBtn = screen.getByLabelText('Minimize terminal')
    await act(async () => { await userEvent.click(minBtn) })
    expect(screen.getByLabelText('Expand terminal')).toBeInTheDocument()
  })
})
