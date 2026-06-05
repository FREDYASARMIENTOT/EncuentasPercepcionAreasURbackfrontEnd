import React from 'react'
import '@testing-library/jest-dom'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import App from './App'

const makeResponse = (payload: any) => ({
  ok: true,
  status: 200,
  json: async () => payload,
  text: async () => JSON.stringify(payload)
})

const defaultFetchResponse = async (input: RequestInfo | URL) => {
  const url = typeof input === 'string' ? input : input.toString()

  if (url.includes('/api/jobs/running')) {
    return makeResponse({ running: false, count: 0, jobs: [], latest_history: [], latest_executions: [] })
  }
  if (url.includes('/api/jobs/runtime-log')) {
    return makeResponse({ running: false, count: 0, state: 'En pausa', execution_status: 'En pausa', log: '' })
  }
  if (url.includes('/api/areas')) {
    return makeResponse([{ AreaId: 1, CodigoArea: 'CRAI', NombreArea: 'CRAI', Activo: true }])
  }
  if (url.includes('/api/history')) {
    return makeResponse([])
  }
  if (url.includes('/api/job-params')) {
    return makeResponse([])
  }
  if (url.includes('/api/jobs')) {
    return makeResponse([])
  }
  if (url.includes('/api/launchers')) {
    return makeResponse({ launchers: ['EncuestatExcelxAreasMesAnioV34.py'] })
  }
  if (url.includes('/api/schedules')) {
    return makeResponse([])
  }
  return makeResponse({})
}

const waitForInitialLoad = async () => {
  await waitFor(() => {
    expect(global.fetch).toHaveBeenCalledWith(expect.stringContaining('/api/history?limit=10&offset=0'))
    expect(global.fetch).toHaveBeenCalledWith('/api/jobs/running')
  })
}

describe('Portal Encuestas Percepcion', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    global.fetch = vi.fn(defaultFetchResponse) as any
  })

  it('renderiza el inicio del portal', async () => {
    render(<App />)
    await waitForInitialLoad()
    expect(screen.getByRole('heading', { name: /Portal Encuestas Percepcion/i })).toBeTruthy()
    expect(screen.getByRole('heading', { name: /Inicio/i })).toBeTruthy()
    expect(screen.getByText(/Sin jobs en ejecucion/i)).toBeTruthy()
  })

  it('colapsa y recupera el menu hamburguesa', async () => {
    render(<App />)
    await waitForInitialLoad()
    const menuButton = screen.getByRole('button', { name: /Abrir menu de navegacion/i })
    expect(menuButton).toHaveAttribute('aria-expanded', 'true')
    fireEvent.click(menuButton)
    expect(menuButton).toHaveAttribute('aria-expanded', 'false')
    fireEvent.click(menuButton)
    expect(menuButton).toHaveAttribute('aria-expanded', 'true')
  })

  it('carga historial con paginacion de 10 registros', async () => {
    const mockFetch = vi.fn(defaultFetchResponse)
    global.fetch = mockFetch as any

    render(<App />)
    fireEvent.click(screen.getByRole('button', { name: 'Historial' }))

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(expect.stringContaining('/api/history?limit=10&offset=0'))
    })
  })

  it('ejecuta el flujo automatico desde inicio', async () => {
    const mockFetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === 'string' ? input : input.toString()
      if (url.includes('/api/orquestador/run')) {
        return makeResponse({ status: 'started', pid: 12345, command: 'cmd.exe /c Lanzador_encuestapercepcion.bat' })
      }
      return defaultFetchResponse(input)
    })
    global.fetch = mockFetch as any

    render(<App />)
    fireEvent.click(screen.getByRole('button', { name: /Ejecutar automatico/i }))

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/orquestador/run',
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ area: 'TODAS', auto_date: true })
        })
      )
    })
  })

  it('ejecuta un job manual desde la pestaña de ejecucion', async () => {
    const mockFetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === 'string' ? input : input.toString()
      if (url.includes('/api/jobs/running')) {
        return defaultFetchResponse(input)
      }
      if (url.includes('/api/orquestador/run')) {
        return makeResponse({ status: 'started', pid: 99, command: 'cmd.exe /c Lanzador_encuestapercepcion.bat' })
      }
      return defaultFetchResponse(input)
    })
    global.fetch = mockFetch as any

    render(<App />)
    fireEvent.click(screen.getByRole('button', { name: 'Ejecucion' }))
    fireEvent.click(screen.getByRole('button', { name: /Ejecutar job manual/i }))

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/orquestador/run',
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' }
        })
      )
    })
  })
})
