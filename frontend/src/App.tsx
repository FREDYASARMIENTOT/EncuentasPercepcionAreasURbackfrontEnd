import { useEffect, useMemo, useState } from 'react'
import urosarioLogo from './assets/logoURrojoFondoTransparente.png'
import './App.css'

type PageKey = 'inicio' | 'historial' | 'schedules' | 'jobs' | 'ejecucion'

type OrquestadorResponse = {
  status: string
  area?: string
  anio?: number
  mes?: number
  auto_date?: boolean
  pid?: number
  command?: string
}

type Area = {
  AreaId: number
  CodigoArea: string
  NombreArea: string
  Activo: boolean
}

type JobParametro = {
  ParametroId: number
  Mes: number
  Anio: number
  AreaId?: number
  FechaProgramacion: string
  UsuarioProgramo?: string
}

type JobExecution = {
  EjecucionId: number
  ParametroId: number
  TipoCarga: string
  FechaEjecucion: string
  Estado: string
  Mensaje?: string
  ArchivoLanzado?: string
  AreaId?: number
}

type Schedule = {
  ScheduleId: number
  ParametroId?: number
  Nombre: string
  Activo: boolean
  Periodico: boolean
  ServicioActivo: boolean
  MesAnterior: boolean
  DiaDelMes?: number
  FechaEspecifica?: string
  Hora: string
  AreaId?: number
  TipoCarga: string
  Launcher: string
  UsuarioProgramo?: string
  FechaCreacion: string
}

type HistoryRecord = {
  CargaId: number
  FechaCarga: string
  Mes: number
  Anio: number
  AreaId?: number
  TipoCarga: string
  RegistrosProcesados?: number
  Estado: string
  Observaciones?: string
}

type RunningJob = {
  pid: number
  carga_id: number
  area?: string
  anio?: number
  mes?: number
  tipo_carga?: string
  started_at?: string
  status?: string
}

type RuntimeStatus = {
  running: boolean
  count: number
  jobs: RunningJob[]
  latest_history: HistoryRecord[]
  latest_executions: JobExecution[]
}

type RuntimeLog = {
  running: boolean
  count: number
  state: string
  execution_status: string
  refreshed_at?: string
  log: string
}

const HISTORY_PAGE_SIZE = 10

const NAV_ITEMS: Array<{ key: PageKey; label: string }> = [
  { key: 'inicio', label: 'Inicio' },
  { key: 'historial', label: 'Historial' },
  { key: 'schedules', label: 'Schedules' },
  { key: 'jobs', label: 'Jobs' },
  { key: 'ejecucion', label: 'Ejecucion' }
]

const MONTHS = [
  { value: 'all', label: 'Todos' },
  { value: '1', label: 'Enero' },
  { value: '2', label: 'Febrero' },
  { value: '3', label: 'Marzo' },
  { value: '4', label: 'Abril' },
  { value: '5', label: 'Mayo' },
  { value: '6', label: 'Junio' },
  { value: '7', label: 'Julio' },
  { value: '8', label: 'Agosto' },
  { value: '9', label: 'Septiembre' },
  { value: '10', label: 'Octubre' },
  { value: '11', label: 'Noviembre' },
  { value: '12', label: 'Diciembre' }
]

const LOAD_TYPES = [
  { value: 'all', label: 'Todos' },
  { value: 'mensual', label: 'Flujo integral mensual' },
  { value: 'manual', label: 'Manual' }
]

function formatDate(value?: string) {
  if (!value) return '-'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString()
}

function monthLabel(value?: number) {
  return MONTHS.find((item) => item.value === String(value))?.label ?? value ?? '-'
}

function App() {
  const [activePage, setActivePage] = useState<PageKey>('inicio')
  const [menuOpen, setMenuOpen] = useState(false)
  const [desktopNavOpen, setDesktopNavOpen] = useState(true)
  const [status, setStatus] = useState('')
  const [commandPreview, setCommandPreview] = useState('')
  const [isBusy, setIsBusy] = useState(false)

  const [areas, setAreas] = useState<Area[]>([])
  const [history, setHistory] = useState<HistoryRecord[]>([])
  const [jobParams, setJobParams] = useState<JobParametro[]>([])
  const [jobExecutions, setJobExecutions] = useState<JobExecution[]>([])
  const [schedules, setSchedules] = useState<Schedule[]>([])
  const [launchers, setLaunchers] = useState<string[]>([])
  const [runtime, setRuntime] = useState<RuntimeStatus>({ running: false, count: 0, jobs: [], latest_history: [], latest_executions: [] })
  const [runtimeLog, setRuntimeLog] = useState<RuntimeLog>({ running: false, count: 0, state: 'En pausa', execution_status: 'En pausa', log: '' })
  const [logExpanded, setLogExpanded] = useState(false)

  const [historyPage, setHistoryPage] = useState(0)
  const [filterYear, setFilterYear] = useState('all')
  const [filterMonth, setFilterMonth] = useState('all')
  const [filterAreaId, setFilterAreaId] = useState('all')
  const [filterTipo, setFilterTipo] = useState('all')
  const [historyStatus, setHistoryStatus] = useState('Cargando historial...')

  const [jobEditId, setJobEditId] = useState<number | null>(null)
  const [jobAreaId, setJobAreaId] = useState('')
  const [jobAnio, setJobAnio] = useState('2026')
  const [jobMes, setJobMes] = useState('5')
  const [jobUsuario, setJobUsuario] = useState('sistema')
  const [jobStatus, setJobStatus] = useState('Cargando jobs...')

  const [scheduleEditId, setScheduleEditId] = useState<number | null>(null)
  const [scheduleParamId, setScheduleParamId] = useState('')
  const [scheduleNombre, setScheduleNombre] = useState('Programacion mensual')
  const [scheduleActivo, setScheduleActivo] = useState(true)
  const [schedulePeriodico, setSchedulePeriodico] = useState(true)
  const [scheduleServicioActivo, setScheduleServicioActivo] = useState(true)
  const [scheduleMesAnterior, setScheduleMesAnterior] = useState(true)
  const [scheduleDia, setScheduleDia] = useState('1')
  const [scheduleFecha, setScheduleFecha] = useState('')
  const [scheduleHora, setScheduleHora] = useState('00:05')
  const [scheduleLauncher, setScheduleLauncher] = useState('')
  const [scheduleAreaId, setScheduleAreaId] = useState('')
  const [scheduleUsuario, setScheduleUsuario] = useState('sistema')
  const [scheduleStatus, setScheduleStatus] = useState('Cargando schedules...')

  const [manualAreaId, setManualAreaId] = useState('')
  const [manualAnio, setManualAnio] = useState('2026')
  const [manualMes, setManualMes] = useState('5')
  const [manualUsuario, setManualUsuario] = useState('sistema')

  const areaMap = useMemo(() => Object.fromEntries(areas.map((item) => [item.AreaId, item.NombreArea])), [areas])
  const historyHasNext = history.length === HISTORY_PAGE_SIZE
  const latestHistory = runtime.latest_history?.length ? runtime.latest_history : history.slice(0, 10)
  const latestExecutions = runtime.latest_executions?.length ? runtime.latest_executions : jobExecutions.slice(0, 10)
  const selectedManualArea = manualAreaId ? areaMap[Number(manualAreaId)] ?? 'TODAS' : 'TODAS'

  const readJson = async <T,>(response: Response): Promise<T> => {
    const text = await response.text()
    return text ? JSON.parse(text) : ({} as T)
  }

  const openPage = (page: PageKey) => {
    setActivePage(page)
    setMenuOpen(false)
  }

  const toggleNavigation = () => {
    if (typeof window.matchMedia === 'function' && window.matchMedia('(max-width: 820px)').matches) {
      setMenuOpen((value) => !value)
      return
    }
    setDesktopNavOpen((value) => !value)
  }

  const areaName = (areaId?: number) => areaId ? areaMap[areaId] ?? `ID ${areaId}` : 'Todas'

  const fetchAreas = async () => {
    try {
      const response = await fetch('/api/areas')
      if (!response.ok) throw new Error(`Error ${response.status}`)
      setAreas(await response.json())
    } catch {
      setAreas([])
    }
  }

  const fetchRuntime = async () => {
    try {
      const response = await fetch('/api/jobs/running')
      if (!response.ok) throw new Error(`Error ${response.status}`)
      const data = await response.json()
      setRuntime({
        running: Boolean(data.running),
        count: Number(data.count ?? 0),
        jobs: Array.isArray(data.jobs) ? data.jobs : [],
        latest_history: Array.isArray(data.latest_history) ? data.latest_history : [],
        latest_executions: Array.isArray(data.latest_executions) ? data.latest_executions : [],
      })
    } catch {
      setRuntime({ running: false, count: 0, jobs: [], latest_history: [], latest_executions: [] })
    }
  }

  const fetchRuntimeLog = async () => {
    try {
      const response = await fetch('/api/jobs/runtime-log')
      if (!response.ok) throw new Error(`Error ${response.status}`)
      const data = await response.json()
      setRuntimeLog({
        running: Boolean(data.running),
        count: Number(data.count ?? 0),
        state: data.state ?? 'En pausa',
        execution_status: data.execution_status ?? 'En pausa',
        refreshed_at: data.refreshed_at,
        log: data.log ?? ''
      })
    } catch {
      setRuntimeLog((current) => ({ ...current, running: false, state: 'En pausa' }))
    }
  }

  const fetchHistory = async (page = historyPage) => {
    setHistoryStatus('Cargando historial...')
    const query = new URLSearchParams({
      limit: String(HISTORY_PAGE_SIZE),
      offset: String(page * HISTORY_PAGE_SIZE)
    })
    if (filterYear !== 'all') query.set('anio', filterYear)
    if (filterMonth !== 'all') query.set('mes', filterMonth)
    if (filterAreaId !== 'all') query.set('area_id', filterAreaId)
    if (filterTipo !== 'all') query.set('tipo_carga', filterTipo)

    try {
      const response = await fetch(`/api/history?${query.toString()}`)
      if (!response.ok) throw new Error(`Error ${response.status}`)
      const data = await readJson<HistoryRecord[]>(response)
      setHistory(Array.isArray(data) ? data : [])
      setHistoryStatus(data.length ? '' : 'No hay registros para los filtros seleccionados')
    } catch (error: any) {
      setHistory([])
      setHistoryStatus(`Error cargando historial: ${error?.message ?? error}`)
    }
  }

  const fetchJobParams = async () => {
    try {
      const response = await fetch('/api/job-params?limit=200')
      if (!response.ok) throw new Error(`Error ${response.status}`)
      const data = await readJson<JobParametro[]>(response)
      setJobParams(Array.isArray(data) ? data : [])
      setJobStatus(data.length ? '' : 'No hay jobs creados')
    } catch (error: any) {
      setJobParams([])
      setJobStatus(`Error cargando jobs: ${error?.message ?? error}`)
    }
  }

  const fetchJobExecutions = async () => {
    try {
      const response = await fetch('/api/jobs?limit=100')
      if (!response.ok) throw new Error(`Error ${response.status}`)
      const data = await readJson<JobExecution[]>(response)
      setJobExecutions(Array.isArray(data) ? data : [])
    } catch {
      setJobExecutions([])
    }
  }

  const fetchLaunchers = async () => {
    try {
      const response = await fetch('/api/launchers')
      if (!response.ok) throw new Error(`Error ${response.status}`)
      const data = await response.json()
      const names = Array.isArray(data.launchers) ? data.launchers : []
      setLaunchers(names)
      if (!scheduleLauncher && names.length) setScheduleLauncher(names[0])
    } catch {
      setLaunchers([])
    }
  }

  const fetchSchedules = async () => {
    try {
      const response = await fetch('/api/schedules')
      if (!response.ok) throw new Error(`Error ${response.status}`)
      const data = await readJson<Schedule[]>(response)
      setSchedules(Array.isArray(data) ? data : [])
      setScheduleStatus(data.length ? '' : 'No hay schedules configurados')
    } catch (error: any) {
      setSchedules([])
      setScheduleStatus(`Error cargando schedules: ${error?.message ?? error}`)
    }
  }

  const refreshPortal = async () => {
    await Promise.all([fetchRuntime(), fetchRuntimeLog(), fetchHistory(), fetchJobParams(), fetchJobExecutions(), fetchSchedules()])
  }

  const ejecutarAutomatico = async () => {
    setIsBusy(true)
    setStatus('Iniciando ejecucion automatica...')
    try {
      const response = await fetch('/api/orquestador/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ area: 'TODAS', auto_date: true })
      })
      if (!response.ok) throw new Error(`Error ${response.status}`)
      const data = await readJson<OrquestadorResponse>(response)
      setStatus(`Job automatico iniciado. PID: ${data.pid ?? 'desconocido'}`)
      setCommandPreview(data.command ?? '')
      await refreshPortal()
    } catch (error: any) {
      setStatus(`Fallo al iniciar job automatico: ${error?.message ?? error}`)
      setCommandPreview('')
    } finally {
      setIsBusy(false)
    }
  }

  const ejecutarManual = async () => {
    setIsBusy(true)
    setStatus('Iniciando job manual...')
    try {
      const response = await fetch('/api/orquestador/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          area: selectedManualArea,
          anio: Number(manualAnio),
          mes: Number(manualMes),
          auto_date: false
        })
      })
      if (!response.ok) {
        const errorText = await response.text()
        throw new Error(`Error ${response.status}: ${errorText}`)
      }
      const data = await readJson<OrquestadorResponse>(response)
      setStatus(`Job manual iniciado. PID: ${data.pid ?? 'desconocido'}`)
      setCommandPreview(data.command ?? '')
      await refreshPortal()
    } catch (error: any) {
      setStatus(`Fallo al ejecutar job manual: ${error?.message ?? error}`)
      setCommandPreview('')
    } finally {
      setIsBusy(false)
    }
  }

  const saveJob = async () => {
    setJobStatus(jobEditId ? 'Actualizando job...' : 'Creando job...')
    try {
      const response = await fetch(jobEditId ? `/api/job-params/${jobEditId}` : '/api/job-params', {
        method: jobEditId ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          area_id: jobAreaId ? Number(jobAreaId) : null,
          anio: Number(jobAnio),
          mes: Number(jobMes),
          tipo_carga: 'mensual',
          usuario: jobUsuario
        })
      })
      if (!response.ok) {
        const errorText = await response.text()
        throw new Error(`Error ${response.status}: ${errorText}`)
      }
      resetJobForm()
      await fetchJobParams()
      setJobStatus(jobEditId ? 'Job actualizado' : 'Job creado')
    } catch (error: any) {
      setJobStatus(`Error guardando job: ${error?.message ?? error}`)
    }
  }

  const editJob = (job: JobParametro) => {
    setJobEditId(job.ParametroId)
    setJobAreaId(job.AreaId ? String(job.AreaId) : '')
    setJobAnio(String(job.Anio))
    setJobMes(String(job.Mes))
    setJobUsuario(job.UsuarioProgramo ?? 'sistema')
    setActivePage('jobs')
  }

  const resetJobForm = () => {
    setJobEditId(null)
    setJobAreaId('')
    setJobAnio('2026')
    setJobMes('5')
    setJobUsuario('sistema')
  }

  const deleteJob = async (id: number) => {
    setJobStatus('Eliminando job...')
    try {
      const response = await fetch(`/api/job-params/${id}`, { method: 'DELETE' })
      if (!response.ok) {
        const errorText = await response.text()
        throw new Error(`Error ${response.status}: ${errorText}`)
      }
      await fetchJobParams()
      setJobStatus('Job eliminado')
    } catch (error: any) {
      setJobStatus(`Error eliminando job: ${error?.message ?? error}`)
    }
  }

  const runSavedJob = async (id: number) => {
    setJobStatus('Ejecutando job guardado...')
    try {
      const response = await fetch(`/api/job-params/${id}/run`, { method: 'POST' })
      if (!response.ok) {
        const errorText = await response.text()
        throw new Error(`Error ${response.status}: ${errorText}`)
      }
      await refreshPortal()
      setJobStatus('Job guardado ejecutado')
    } catch (error: any) {
      setJobStatus(`Error ejecutando job: ${error?.message ?? error}`)
    }
  }

  const saveSchedule = async () => {
    setScheduleStatus(scheduleEditId ? 'Actualizando schedule...' : 'Creando schedule...')
    const payload = {
      parametro_id: scheduleParamId ? Number(scheduleParamId) : null,
      nombre: scheduleNombre,
      activo: scheduleActivo,
      periodico: schedulePeriodico,
      servicio_activo: scheduleServicioActivo,
      mes_anterior: scheduleMesAnterior,
      dia_del_mes: schedulePeriodico ? Number(scheduleDia) : null,
      fecha_especifica: !schedulePeriodico && scheduleFecha ? `${scheduleFecha}T${scheduleHora || '00:00'}:00` : null,
      hora: scheduleHora,
      area_id: scheduleAreaId ? Number(scheduleAreaId) : null,
      tipo_carga: 'mensual',
      launcher: scheduleLauncher,
      usuario: scheduleUsuario
    }

    try {
      const response = await fetch(scheduleEditId ? `/api/schedules/${scheduleEditId}` : '/api/schedules', {
        method: scheduleEditId ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
      if (!response.ok) {
        const errorText = await response.text()
        throw new Error(`Error ${response.status}: ${errorText}`)
      }
      resetScheduleForm()
      await fetchSchedules()
      setScheduleStatus(scheduleEditId ? 'Schedule actualizado' : 'Schedule creado')
    } catch (error: any) {
      setScheduleStatus(`Error guardando schedule: ${error?.message ?? error}`)
    }
  }

  const editSchedule = (schedule: Schedule) => {
    setScheduleEditId(schedule.ScheduleId)
    setScheduleParamId(schedule.ParametroId ? String(schedule.ParametroId) : '')
    setScheduleNombre(schedule.Nombre)
    setScheduleActivo(schedule.Activo)
    setSchedulePeriodico(schedule.Periodico)
    setScheduleServicioActivo(schedule.ServicioActivo)
    setScheduleMesAnterior(schedule.MesAnterior)
    setScheduleDia(String(schedule.DiaDelMes ?? 1))
    setScheduleFecha(schedule.FechaEspecifica ? schedule.FechaEspecifica.slice(0, 10) : '')
    setScheduleHora(schedule.Hora)
    setScheduleAreaId(schedule.AreaId ? String(schedule.AreaId) : '')
    setScheduleLauncher(schedule.Launcher)
    setScheduleUsuario(schedule.UsuarioProgramo ?? 'sistema')
  }

  const resetScheduleForm = () => {
    setScheduleEditId(null)
    setScheduleParamId('')
    setScheduleNombre('Programacion mensual')
    setScheduleActivo(true)
    setSchedulePeriodico(true)
    setScheduleServicioActivo(true)
    setScheduleMesAnterior(true)
    setScheduleDia('1')
    setScheduleFecha('')
    setScheduleHora('00:05')
    setScheduleAreaId('')
    setScheduleUsuario('sistema')
  }

  const triggerSchedule = async (id: number) => {
    setScheduleStatus('Ejecutando schedule...')
    try {
      const response = await fetch(`/api/schedules/${id}/trigger`, { method: 'POST' })
      if (!response.ok) {
        const errorText = await response.text()
        throw new Error(`Error ${response.status}: ${errorText}`)
      }
      await refreshPortal()
      setScheduleStatus('Schedule ejecutado')
    } catch (error: any) {
      setScheduleStatus(`Error ejecutando schedule: ${error?.message ?? error}`)
    }
  }

  const deleteSchedule = async (id: number) => {
    setScheduleStatus('Eliminando schedule...')
    try {
      const response = await fetch(`/api/schedules/${id}`, { method: 'DELETE' })
      if (!response.ok) throw new Error(`Error ${response.status}`)
      await fetchSchedules()
      setScheduleStatus('Schedule eliminado')
    } catch (error: any) {
      setScheduleStatus(`Error eliminando schedule: ${error?.message ?? error}`)
    }
  }

  const resetHistoryPage = () => setHistoryPage(0)

  useEffect(() => {
    fetchAreas()
    fetchJobParams()
    fetchJobExecutions()
    fetchSchedules()
    fetchLaunchers()
    fetchRuntime()
    fetchRuntimeLog()

    const interval = window.setInterval(() => {
      fetchRuntime()
      fetchJobExecutions()
    }, 30_000)

    return () => window.clearInterval(interval)
  }, [])

  useEffect(() => {
    fetchHistory(historyPage)
  }, [historyPage, filterYear, filterMonth, filterAreaId, filterTipo])

  useEffect(() => {
    if (activePage !== 'ejecucion') return
    fetchRuntimeLog()

    if (!runtime.running) {
      const timer = window.setTimeout(() => {
        fetchRuntimeLog()
        fetchJobExecutions()
      }, 3000)
      return () => window.clearTimeout(timer)
    }
    
    const interval = window.setInterval(() => {
      fetchRuntime()
      fetchRuntimeLog()
      fetchJobExecutions()
    }, 5_000)

    return () => window.clearInterval(interval)
  }, [activePage, runtime.running])

  return (
    <div className={`app-shell ${menuOpen ? 'menu-open' : ''} ${desktopNavOpen ? '' : 'sidebar-collapsed'}`}>
      {menuOpen && <button className="menu-backdrop" type="button" aria-label="Cerrar menu" onClick={() => setMenuOpen(false)} />}

      <aside className="sidebar" aria-label="Menu principal">
        <div className="sidebar-brand">
          <img src={urosarioLogo} alt="Universidad del Rosario" className="sidebar-logo" />
          <div>
            <span className="sidebar-title">Encuestas Percepcion</span>
            <span className="sidebar-subtitle">Orquestacion DWH</span>
          </div>
        </div>
        <nav className="sidebar-nav">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.key}
              type="button"
              className={`nav-link ${activePage === item.key ? 'active' : ''}`}
              onClick={() => openPage(item.key)}
            >
              {item.label}
            </button>
          ))}
        </nav>
      </aside>

      <main className="content">
        <header className="topbar">
          <button
            className="hamburger"
            type="button"
            onClick={toggleNavigation}
            aria-label="Abrir menu de navegacion"
            aria-expanded={menuOpen || desktopNavOpen}
          >
            <span />
            <span />
            <span />
          </button>
          <div className="brand-inline">
            <img src={urosarioLogo} alt="UR logo" className="brand-logo" />
            <div>
              <h1>Portal Encuestas Percepcion</h1>
              <p>Jobs, schedules e historial de ejecucion del flujo de encuestas.</p>
            </div>
          </div>
          <div className={`runtime-pill ${runtime.running ? 'running' : 'idle'}`}>
            {runtime.running ? `${runtime.count} job en ejecucion` : 'Sin jobs en ejecucion'}
          </div>
        </header>

        {activePage === 'inicio' && (
          <section className="page-stack">
            <div className="page-title">
              <div>
                <h2>Inicio</h2>
                <p>Resumen operativo del portal y de los ultimos movimientos registrados.</p>
              </div>
              <button type="button" className="primary-button" onClick={ejecutarAutomatico} disabled={isBusy || runtime.running}>
                {runtime.running ? 'Job en curso' : 'Ejecutar automatico'}
              </button>
            </div>

            <div className="metric-grid">
              <article className="metric-card">
                <span>Estado actual</span>
                <strong>{runtime.running ? 'En ejecucion' : 'Disponible'}</strong>
              </article>
              <article className="metric-card">
                <span>Schedules</span>
                <strong>{schedules.length}</strong>
              </article>
              <article className="metric-card">
                <span>Jobs creados</span>
                <strong>{jobParams.length}</strong>
              </article>
              <article className="metric-card">
                <span>Ultimas cargas visibles</span>
                <strong>{latestHistory.length}</strong>
              </article>
            </div>

            {runtime.running && (
              <section className="panel">
                <div className="section-heading">
                  <h3>Jobs en ejecucion</h3>
                </div>
                <div className="table-wrapper">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>PID</th>
                        <th>Area</th>
                        <th>Periodo</th>
                        <th>Tipo</th>
                        <th>Inicio</th>
                      </tr>
                    </thead>
                    <tbody>
                      {runtime.jobs.map((job) => (
                        <tr key={job.pid}>
                          <td>{job.pid}</td>
                          <td>{job.area ?? 'Todas'}</td>
                          <td>{job.mes}/{job.anio}</td>
                          <td>{job.tipo_carga ?? '-'}</td>
                          <td>{job.started_at ?? '-'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            )}

            <section className="panel">
              <div className="section-heading">
                <h3>Historial de ejecucion reciente</h3>
                <button type="button" className="secondary-button" onClick={() => openPage('historial')}>Ver historial</button>
              </div>
              <HistoryTable rows={latestHistory} areaName={areaName} />
            </section>

            <section className="panel">
              <div className="section-heading">
                <h3>Ultimos jobs ejecutados</h3>
                <button type="button" className="secondary-button" onClick={() => openPage('ejecucion')}>Ir a ejecucion</button>
              </div>
              <ExecutionTable rows={latestExecutions} areaName={areaName} />
            </section>
          </section>
        )}

        {activePage === 'historial' && (
          <section className="page-stack">
            <div className="page-title">
              <div>
                <h2>Historial</h2>
                <p>Registros cargados desde base de datos, ordenados del mas reciente al mas antiguo.</p>
              </div>
            </div>
            <div className="filters-grid">
              <label>
                Anio
                <select value={filterYear} onChange={(event) => { setFilterYear(event.target.value); resetHistoryPage() }}>
                  <option value="all">Todos</option>
                  {[2026, 2025, 2024, 2023].map((year) => <option key={year} value={String(year)}>{year}</option>)}
                </select>
              </label>
              <label>
                Mes
                <select value={filterMonth} onChange={(event) => { setFilterMonth(event.target.value); resetHistoryPage() }}>
                  {MONTHS.map((month) => <option key={month.value} value={month.value}>{month.label}</option>)}
                </select>
              </label>
              <label>
                Area
                <select value={filterAreaId} onChange={(event) => { setFilterAreaId(event.target.value); resetHistoryPage() }}>
                  <option value="all">Todas</option>
                  {areas.map((item) => <option key={item.AreaId} value={String(item.AreaId)}>{item.NombreArea}</option>)}
                </select>
              </label>
              <label>
                Tipo
                <select value={filterTipo} onChange={(event) => { setFilterTipo(event.target.value); resetHistoryPage() }}>
                  {LOAD_TYPES.map((type) => <option key={type.value} value={type.value}>{type.label}</option>)}
                </select>
              </label>
            </div>
            <section className="panel">
              {historyStatus ? <p className="empty-state">{historyStatus}</p> : <HistoryTable rows={history} areaName={areaName} />}
              <div className="pagination-bar">
                <button type="button" className="secondary-button" disabled={historyPage === 0} onClick={() => setHistoryPage((page) => Math.max(0, page - 1))}>
                  Anterior
                </button>
                <span>Pagina {historyPage + 1} | {HISTORY_PAGE_SIZE} registros por pagina</span>
                <button type="button" className="secondary-button" disabled={!historyHasNext} onClick={() => setHistoryPage((page) => page + 1)}>
                  Siguiente
                </button>
              </div>
            </section>
          </section>
        )}

        {activePage === 'jobs' && (
          <section className="page-stack">
            <div className="page-title">
              <div>
                <h2>CRUD de Jobs</h2>
                <p>Crea, edita, elimina y ejecuta parametros reutilizables para el flujo mensual integral.</p>
              </div>
            </div>
            <section className="form-panel">
              <h3>{jobEditId ? `Editar job ${jobEditId}` : 'Crear job'}</h3>
              <div className="form-grid">
                <label>
                  Area
                  <select value={jobAreaId} onChange={(event) => setJobAreaId(event.target.value)}>
                    <option value="">Todas</option>
                    {areas.map((item) => <option key={item.AreaId} value={String(item.AreaId)}>{item.NombreArea}</option>)}
                  </select>
                </label>
                <label>
                  Anio
                  <input value={jobAnio} onChange={(event) => setJobAnio(event.target.value)} />
                </label>
                <label>
                  Mes
                  <input value={jobMes} onChange={(event) => setJobMes(event.target.value)} />
                </label>
                <label>
                  Usuario
                  <input value={jobUsuario} onChange={(event) => setJobUsuario(event.target.value)} />
                </label>
              </div>
              <div className="button-row">
                <button type="button" className="primary-button" onClick={saveJob}>{jobEditId ? 'Actualizar job' : 'Crear job'}</button>
                {jobEditId && <button type="button" className="secondary-button" onClick={resetJobForm}>Cancelar edicion</button>}
              </div>
              {jobStatus && <p className="status-text">{jobStatus}</p>}
            </section>

            <section className="panel">
              <div className="section-heading">
                <h3>Jobs guardados</h3>
              </div>
              <div className="table-wrapper">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>Periodo</th>
                      <th>Area</th>
                      <th>Usuario</th>
                      <th>Creado</th>
                      <th>Acciones</th>
                    </tr>
                  </thead>
                  <tbody>
                    {jobParams.map((job) => (
                      <tr key={job.ParametroId}>
                        <td>{job.ParametroId}</td>
                        <td>{monthLabel(job.Mes)} {job.Anio}</td>
                        <td>{areaName(job.AreaId)}</td>
                        <td>{job.UsuarioProgramo ?? '-'}</td>
                        <td>{formatDate(job.FechaProgramacion)}</td>
                        <td className="actions-cell">
                          <button type="button" className="secondary-button" onClick={() => editJob(job)}>Editar</button>
                          <button type="button" className="secondary-button" onClick={() => runSavedJob(job.ParametroId)}>Ejecutar</button>
                          <button type="button" className="danger-button" onClick={() => deleteJob(job.ParametroId)}>Eliminar</button>
                        </td>
                      </tr>
                    ))}
                    {!jobParams.length && (
                      <tr>
                        <td colSpan={6}>No hay jobs guardados.</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </section>
          </section>
        )}

        {activePage === 'schedules' && (
          <section className="page-stack">
            <div className="page-title">
              <div>
                <h2>CRUD de Schedules</h2>
                <p>Administra programaciones y asocialas a jobs guardados; cada ejecucion genera mensual, acumulado y correo.</p>
              </div>
            </div>
            <section className="form-panel">
              <h3>{scheduleEditId ? `Editar schedule ${scheduleEditId}` : 'Crear schedule'}</h3>
              <div className="form-grid wide">
                <label>
                  Job asociado
                  <select value={scheduleParamId} onChange={(event) => setScheduleParamId(event.target.value)}>
                    <option value="">Sin job asociado</option>
                    {jobParams.map((job) => (
                      <option key={job.ParametroId} value={String(job.ParametroId)}>
                        #{job.ParametroId} - {monthLabel(job.Mes)} {job.Anio} - {areaName(job.AreaId)}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Nombre
                  <input value={scheduleNombre} onChange={(event) => setScheduleNombre(event.target.value)} />
                </label>
                <label>
                  Launcher
                  <select value={scheduleLauncher} onChange={(event) => setScheduleLauncher(event.target.value)}>
                    {launchers.map((launcher) => <option key={launcher} value={launcher}>{launcher}</option>)}
                  </select>
                </label>
                <label>
                  Area
                  <select value={scheduleAreaId} onChange={(event) => setScheduleAreaId(event.target.value)}>
                    <option value="">Todas</option>
                    {areas.map((item) => <option key={item.AreaId} value={String(item.AreaId)}>{item.NombreArea}</option>)}
                  </select>
                </label>
                <label>
                  Hora
                  <input type="time" value={scheduleHora} onChange={(event) => setScheduleHora(event.target.value)} />
                </label>
                <label>
                  Dia del mes
                  <input type="number" min="1" max="28" value={scheduleDia} onChange={(event) => setScheduleDia(event.target.value)} disabled={!schedulePeriodico} />
                </label>
                <label>
                  Fecha especifica
                  <input type="date" value={scheduleFecha} onChange={(event) => setScheduleFecha(event.target.value)} disabled={schedulePeriodico} />
                </label>
                <label>
                  Usuario
                  <input value={scheduleUsuario} onChange={(event) => setScheduleUsuario(event.target.value)} />
                </label>
              </div>
              <div className="toggle-grid">
                <label><input type="checkbox" checked={scheduleActivo} onChange={(event) => setScheduleActivo(event.target.checked)} /> Activo</label>
                <label><input type="checkbox" checked={scheduleServicioActivo} onChange={(event) => setScheduleServicioActivo(event.target.checked)} /> Servicio activo</label>
                <label><input type="checkbox" checked={schedulePeriodico} onChange={(event) => setSchedulePeriodico(event.target.checked)} /> Periodico</label>
                <label><input type="checkbox" checked={scheduleMesAnterior} onChange={(event) => setScheduleMesAnterior(event.target.checked)} /> Mes anterior</label>
              </div>
              <div className="button-row">
                <button type="button" className="primary-button" onClick={saveSchedule} disabled={!scheduleLauncher}>{scheduleEditId ? 'Actualizar schedule' : 'Crear schedule'}</button>
                {scheduleEditId && <button type="button" className="secondary-button" onClick={resetScheduleForm}>Cancelar edicion</button>}
              </div>
              {scheduleStatus && <p className="status-text">{scheduleStatus}</p>}
            </section>

            <section className="panel">
              <div className="section-heading">
                <h3>Schedules guardados</h3>
              </div>
              <div className="table-wrapper">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Nombre</th>
                      <th>Job</th>
                      <th>Launcher</th>
                      <th>Area</th>
                      <th>Hora</th>
                      <th>Estado</th>
                      <th>Acciones</th>
                    </tr>
                  </thead>
                  <tbody>
                    {schedules.map((schedule) => (
                      <tr key={schedule.ScheduleId}>
                        <td>{schedule.Nombre}</td>
                        <td>{schedule.ParametroId ? `#${schedule.ParametroId}` : '-'}</td>
                        <td>{schedule.Launcher}</td>
                        <td>{areaName(schedule.AreaId)}</td>
                        <td>{schedule.Hora}</td>
                        <td>{schedule.Activo && schedule.ServicioActivo ? 'Activo' : 'Inactivo'}</td>
                        <td className="actions-cell">
                          <button type="button" className="secondary-button" onClick={() => editSchedule(schedule)}>Editar</button>
                          <button type="button" className="secondary-button" onClick={() => triggerSchedule(schedule.ScheduleId)}>Ejecutar</button>
                          <button type="button" className="danger-button" onClick={() => deleteSchedule(schedule.ScheduleId)}>Eliminar</button>
                        </td>
                      </tr>
                    ))}
                    {!schedules.length && (
                      <tr>
                        <td colSpan={7}>No hay schedules guardados.</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </section>
          </section>
        )}

        {activePage === 'ejecucion' && (
          <section className="page-stack">
            <div className="page-title">
              <div>
                <h2>Ejecucion de Jobs</h2>
                <p>Ejecuta el flujo mensual integral por anio, mes y area, o lanza el automatico del mes anterior.</p>
              </div>
              <button type="button" className="primary-button" onClick={ejecutarAutomatico} disabled={isBusy || runtime.running}>
                Ejecutar automatico
              </button>
            </div>
            <section className="form-panel">
              <h3>Ejecutar manualmente</h3>
              <div className="form-grid">
                <label>
                  Area
                  <select value={manualAreaId} onChange={(event) => setManualAreaId(event.target.value)}>
                    <option value="">Todas</option>
                    {areas.map((item) => <option key={item.AreaId} value={String(item.AreaId)}>{item.NombreArea}</option>)}
                  </select>
                </label>
                <label>
                  Anio
                  <input data-testid="manual-anio" value={manualAnio} onChange={(event) => setManualAnio(event.target.value)} />
                </label>
                <label>
                  Mes
                  <input data-testid="manual-mes" value={manualMes} onChange={(event) => setManualMes(event.target.value)} />
                </label>
                <label>
                  Usuario
                  <input value={manualUsuario} onChange={(event) => setManualUsuario(event.target.value)} />
                </label>
              </div>
              <button type="button" className="primary-button" onClick={ejecutarManual} disabled={isBusy}>
                {isBusy ? 'Ejecutando...' : 'Ejecutar job manual'}
              </button>
              {commandPreview && <p className="status-text">Archivo lanzado: <strong>{commandPreview}</strong></p>}
            </section>
            <section className={`panel runtime-log-panel ${logExpanded ? 'expanded' : ''}`}>
              <div className="section-heading">
                <div>
                  <h3>Log de ejecucion</h3>
                  <p className="log-status">
                    Estado: <strong>{runtimeLog.execution_status}</strong> | Refresco: {runtime.running ? 'cada 5 segundos' : 'detenido'} | Ultima lectura: {runtimeLog.refreshed_at ?? '-'}
                  </p>
                </div>
                <button type="button" className="secondary-button" onClick={() => setLogExpanded((value) => !value)}>
                  {logExpanded ? 'Contraer log' : 'Expandir log'}
                </button>
              </div>
              <textarea
                className="runtime-log"
                readOnly
                wrap="off"
                value={runtimeLog.log || 'Sin log disponible para la ultima ejecucion.'}
                aria-label="Log de ejecucion del job"
              />
              {runtimeLog.log && runtimeLog.log.includes('[EMAIL_STATUS] FAILED') && (
                <div style={{ marginTop: '15px', padding: '15px', backgroundColor: '#fff3cd', color: '#856404', border: '1px solid #ffeeba', borderRadius: '4px' }}>
                  <strong>⚠️ Atención:</strong> El sistema no pudo confirmar que los correos se enviaron con éxito a los usuarios. Por favor verifique la configuración SMTP o los permisos de red si este entorno es de pruebas o App Service.
                </div>
              )}
              {runtimeLog.log && runtimeLog.log.includes('[EMAIL_STATUS] SUCCESS') && (
                <div style={{ marginTop: '15px', padding: '15px', backgroundColor: '#d4edda', color: '#155724', border: '1px solid #c3e6cb', borderRadius: '4px' }}>
                  <strong>✅ Confirmación:</strong> Los correos electrónicos se han enviado con éxito a los usuarios.
                </div>
              )}
            </section>
            <section className="panel">
              <div className="section-heading">
                <h3>Historial de ejecucion de jobs</h3>
              </div>
              <ExecutionTable rows={jobExecutions} areaName={areaName} />
            </section>
          </section>
        )}

        {status && <p className="main-status">{status}</p>}
      </main>
    </div>
  )
}

function HistoryTable({ rows, areaName }: { rows: HistoryRecord[]; areaName: (areaId?: number) => string }) {
  return (
    <div className="table-wrapper">
      <table className="data-table">
        <thead>
          <tr>
            <th>Fecha carga</th>
            <th>Periodo</th>
            <th>Area</th>
            <th>Tipo</th>
            <th>Estado</th>
            <th>Registros</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.CargaId}>
              <td>{formatDate(row.FechaCarga)}</td>
              <td>{monthLabel(row.Mes)} {row.Anio}</td>
              <td>{areaName(row.AreaId)}</td>
              <td>{row.TipoCarga}</td>
              <td><span className={`state ${row.Estado.toLowerCase()}`}>{row.Estado}</span></td>
              <td>{row.RegistrosProcesados ?? '-'}</td>
            </tr>
          ))}
          {!rows.length && (
            <tr>
              <td colSpan={6}>No hay registros para mostrar.</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}

function ExecutionTable({ rows, areaName }: { rows: JobExecution[]; areaName: (areaId?: number) => string }) {
  return (
    <div className="table-wrapper">
      <table className="data-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Job</th>
            <th>Tipo</th>
            <th>Area</th>
            <th>Estado</th>
            <th>Fecha</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.EjecucionId}>
              <td>{row.EjecucionId}</td>
              <td>{row.ParametroId}</td>
              <td>{row.TipoCarga}</td>
              <td>{areaName(row.AreaId)}</td>
              <td><span className={`state ${row.Estado.toLowerCase()}`}>{row.Estado}</span></td>
              <td>{formatDate(row.FechaEjecucion)}</td>
            </tr>
          ))}
          {!rows.length && (
            <tr>
              <td colSpan={6}>No hay ejecuciones registradas.</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}

export default App
