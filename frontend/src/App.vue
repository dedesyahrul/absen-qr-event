<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { Bell, CalendarDays, Camera, CameraOff, Check, ChevronDown, CircleAlert, CircleCheck, Download, Eye, FileSpreadsheet, Grid3x3, LayoutDashboard, LogOut, Pencil, Plus, QrCode, RefreshCw, Search, Settings, ShieldCheck, Sparkles, Trash2, Undo2, Upload, UserRound, Users, X } from '@lucide/vue'
import QrScanner from 'qr-scanner'

const API = import.meta.env.VITE_API_URL || (window.location.port === '5173' || window.location.port === '18082' ? `http://${window.location.hostname}:18081/api` : `${window.location.origin}/api`)
const token = ref(localStorage.getItem('gatherly_token') || '')
const user = ref(JSON.parse(localStorage.getItem('gatherly_user') || 'null'))
const loading = ref(false)
const loginError = ref('')
const loginForm = ref({ email: 'admin@example.com', password: 'admin123' })
const activeView = ref('overview')
const event = ref(null)
const dashboard = ref(null)
const participants = ref([])
const vendors = ref([])
const search = ref('')
const scanToken = ref('')
const scanMessage = ref(null)
const showParticipantForm = ref(false)
const participantForm = ref({ name: '', position: '', phone: '', email: '', vendor_id: null, table_id: null, seat_number: null })

// QR Code viewer state
const showQrModal = ref(false)
const qrParticipant = ref(null)
const qrImageUrl = ref('')
const qrLoading = ref(false)

// Camera scanner state
const cameraActive = ref(false)
const videoEl = ref(null)
let qrScannerInstance = null

// Edit participant state
const showEditForm = ref(false)
const editForm = ref({ id: null, name: '', vendor_id: null, table_id: null, seat_number: null, position: '', phone: '', email: '' })

// Delete confirmation state
const showDeleteConfirm = ref(false)
const deleteTarget = ref(null)

// Import state
const showImportPreview = ref(false)
const importFile = ref(null)
const importPreview = ref(null)
const importLoading = ref(false)
const importDuplicateAction = ref('skip')

// Export dropdown state
const showExportDropdown = ref(false)

// Seating state
const tables = ref([])
const expandedTable = ref(null)
const showTableForm = ref(false)
const tableForm = ref({ table_number: '', table_label: '', capacity: 10, zone: '' })
const showBulkForm = ref(false)
const bulkForm = ref({ prefix: 'A', count: 10, capacity: 10, zone: '' })

// Undo check-in state
const showUndoConfirm = ref(false)
const undoTarget = ref(null)

const headers = () => ({ 'Content-Type': 'application/json', ...(token.value ? { Authorization: `Bearer ${token.value}` } : {}) })
async function api(path, options = {}) {
  const response = await fetch(`${API}${path}`, { ...options, headers: { ...headers(), ...(options.headers || {}) } })
  const body = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(body.detail || 'Terjadi kesalahan pada server')
  return body
}
async function login() {
  loading.value = true; loginError.value = ''
  try {
    const result = await api('/auth/login', { method: 'POST', body: JSON.stringify(loginForm.value) })
    token.value = result.access_token; user.value = result.user
    localStorage.setItem('gatherly_token', token.value); localStorage.setItem('gatherly_user', JSON.stringify(user.value))
    await loadData()
  } catch (error) { loginError.value = error.message } finally { loading.value = false }
}
function logout() { token.value = ''; user.value = null; localStorage.removeItem('gatherly_token'); localStorage.removeItem('gatherly_user') }
async function loadData() {
  loading.value = true
  try {
    const events = await api('/events')
    event.value = events[0]
    if (!event.value) return
    await refreshEventData()
  } catch (error) {
    if (error.message.includes('token') || error.message.includes('Authentication')) logout()
  } finally { loading.value = false }
}
async function refreshEventData() {
  if (!event.value) return
  const [dash, people, vendorList] = await Promise.all([api(`/events/${event.value.id}/dashboard`), api(`/events/${event.value.id}/participants?search=${encodeURIComponent(search.value)}`), api(`/events/${event.value.id}/vendors`)])
  dashboard.value = dash; participants.value = people; vendors.value = vendorList
}
async function refreshSearch() { if (event.value) participants.value = await api(`/events/${event.value.id}/participants?search=${encodeURIComponent(search.value)}`) }
async function checkIn(mode = 'qr', participantId = null) {
  if (!event.value) return
  try {
    const payload = mode === 'qr' ? { token: scanToken.value.trim() } : { participant_id: participantId, notes: 'Verified at registration desk' }
    const result = await api(`/events/${event.value.id}/attendance/${mode === 'qr' ? 'scan' : 'manual'}`, { method: 'POST', body: JSON.stringify(payload) })
    const p = result.participant
    const seatInfo = p.table_number ? ` • Meja ${p.table_number}${p.seat_number ? ', Kursi ' + p.seat_number : ''}` : ''
    scanMessage.value = { type: result.result === 'already_checked_in' ? 'warning' : 'success', title: result.result === 'already_checked_in' ? 'Peserta sudah check-in' : 'Check-in berhasil', text: `${p.name} • ${p.company_name}${seatInfo}` }
    scanToken.value = ''; await refreshEventData()
  } catch (error) { scanMessage.value = { type: 'error', title: 'Scan tidak berhasil', text: error.message } }
}
async function addParticipant() {
  if (!participantForm.value.name.trim()) return
  await api(`/events/${event.value.id}/participants`, { method: 'POST', body: JSON.stringify(participantForm.value) })
  participantForm.value = { name: '', position: '', phone: '', email: '', vendor_id: null, table_id: null, seat_number: null }; showParticipantForm.value = false; await refreshEventData()
}
function focusScanner() { activeView.value = 'scanner'; nextTick(() => document.querySelector('#scan-input')?.focus()) }

// QR Code functions
async function showQr(person) {
  qrParticipant.value = person
  qrLoading.value = true
  showQrModal.value = true
  try {
    const response = await fetch(`${API}/events/${event.value.id}/participants/${person.id}/qr`, { headers: { Authorization: `Bearer ${token.value}` } })
    if (!response.ok) throw new Error('Gagal memuat QR Code')
    const blob = await response.blob()
    qrImageUrl.value = URL.createObjectURL(blob)
  } catch (error) {
    scanMessage.value = { type: 'error', title: 'Error', text: error.message }
    showQrModal.value = false
  } finally { qrLoading.value = false }
}
function closeQrModal() {
  showQrModal.value = false
  if (qrImageUrl.value) { URL.revokeObjectURL(qrImageUrl.value); qrImageUrl.value = '' }
  qrParticipant.value = null
}
function downloadQr() {
  if (!qrImageUrl.value || !qrParticipant.value) return
  const link = document.createElement('a')
  link.href = qrImageUrl.value
  link.download = `qr_${qrParticipant.value.name.replace(/\s+/g, '_')}_${qrParticipant.value.id}.png`
  link.click()
}
async function downloadAllQr() {
  if (!event.value) return
  try {
    const response = await fetch(`${API}/events/${event.value.id}/participants/qr-all`, { headers: { Authorization: `Bearer ${token.value}` } })
    if (!response.ok) throw new Error('Gagal mengunduh QR Code')
    const blob = await response.blob()
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `qr_codes_${event.value.name.replace(/\s+/g, '_')}.zip`
    link.click()
    URL.revokeObjectURL(url)
  } catch (error) { scanMessage.value = { type: 'error', title: 'Error', text: error.message } }
}

// Camera scanner functions
async function startCamera() {
  if (!videoEl.value) return
  try {
    qrScannerInstance = new QrScanner(videoEl.value, result => {
      const scannedToken = result.data.trim()
      if (scannedToken) {
        scanToken.value = scannedToken
        stopCamera()
        checkIn('qr')
      }
    }, {
      returnDetailedScanResult: true,
      highlightScanRegion: true,
      highlightCodeOutline: true,
      preferredCamera: 'environment',
      maxScansPerSecond: 5
    })
    await qrScannerInstance.start()
    cameraActive.value = true
  } catch (error) {
    scanMessage.value = { type: 'error', title: 'Kamera tidak tersedia', text: error.message || 'Pastikan izin kamera diberikan.' }
    cameraActive.value = false
  }
}
function stopCamera() {
  if (qrScannerInstance) { qrScannerInstance.stop(); qrScannerInstance.destroy(); qrScannerInstance = null }
  cameraActive.value = false
}
function toggleCamera() { cameraActive.value ? stopCamera() : startCamera() }

// Cleanup camera on view change or unmount
watch(activeView, (newView) => { if (newView !== 'scanner') stopCamera() })
onUnmounted(() => stopCamera())

// Edit participant functions
async function openEditForm(person) {
  await loadTables()
  editForm.value = { id: person.id, name: person.name, vendor_id: person.vendor_id || null, table_id: person.table_id || null, seat_number: person.seat_number || null, position: person.position || '', phone: person.phone || '', email: person.email || '' }
  showEditForm.value = true
}
async function saveEdit() {
  if (!editForm.value.name.trim()) return
  const { id, ...body } = editForm.value
  await api(`/events/${event.value.id}/participants/${id}`, { method: 'PUT', body: JSON.stringify(body) })
  showEditForm.value = false; await refreshEventData()
}

// Delete participant functions
function confirmDelete(person) { deleteTarget.value = person; showDeleteConfirm.value = true }
async function doDelete() {
  if (!deleteTarget.value) return
  await api(`/events/${event.value.id}/participants/${deleteTarget.value.id}`, { method: 'DELETE' })
  showDeleteConfirm.value = false; deleteTarget.value = null; await refreshEventData()
}

// Undo check-in functions
function confirmUndo(person) { undoTarget.value = person; showUndoConfirm.value = true }
async function doUndo() {
  if (!undoTarget.value) return
  await api(`/events/${event.value.id}/attendance/undo`, { method: 'POST', body: JSON.stringify({ participant_id: undoTarget.value.id, notes: 'Undo from admin panel' }) })
  showUndoConfirm.value = false; undoTarget.value = null; await refreshEventData()
}

// Import functions
async function downloadTemplate() {
  if (!event.value) return
  try {
    const response = await fetch(`${API}/events/${event.value.id}/import/template`, { headers: { Authorization: `Bearer ${token.value}` } })
    if (!response.ok) throw new Error('Gagal mengunduh template')
    const blob = await response.blob()
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url; link.download = `import_template_${event.value.name.replace(/\s+/g, '_')}.xlsx`; link.click()
    URL.revokeObjectURL(url)
  } catch (error) { scanMessage.value = { type: 'error', title: 'Error', text: error.message } }
}
async function handleImportFile(e) {
  const file = e.target.files?.[0]
  if (!file) return
  importFile.value = file; importLoading.value = true
  try {
    const fd = new FormData(); fd.append('file', file)
    const result = await fetch(`${API}/events/${event.value.id}/import/preview`, { method: 'POST', headers: { Authorization: `Bearer ${token.value}` }, body: fd })
    const body = await result.json().catch(() => ({}))
    if (!result.ok) throw new Error(body.detail || 'Gagal memproses file')
    importPreview.value = body; showImportPreview.value = true
  } catch (error) { scanMessage.value = { type: 'error', title: 'Import gagal', text: error.message } }
  finally { importLoading.value = false; e.target.value = '' }
}
async function confirmImport() {
  if (!importPreview.value) return
  importLoading.value = true
  try {
    const result = await api(`/events/${event.value.id}/import/confirm`, { method: 'POST', body: JSON.stringify({ rows: importPreview.value.rows, duplicate_action: importDuplicateAction.value }) })
    scanMessage.value = { type: 'success', title: 'Import berhasil', text: `${result.created} dibuat, ${result.skipped} dilewati, ${result.updated} diperbarui` }
    showImportPreview.value = false; importPreview.value = null; importFile.value = null; await refreshEventData()
  } catch (error) { scanMessage.value = { type: 'error', title: 'Import gagal', text: error.message } }
  finally { importLoading.value = false }
}

// Export functions
async function exportFile(type) {
  if (!event.value) return
  showExportDropdown.value = false
  const endpoints = { participants: 'participants', attendance: 'attendance', vendors: 'vendors', seating: 'seating', audit: 'audit-log' }
  try {
    const response = await fetch(`${API}/events/${event.value.id}/export/${endpoints[type]}`, { headers: { Authorization: `Bearer ${token.value}` } })
    if (!response.ok) throw new Error('Gagal mengunduh file')
    const blob = await response.blob()
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url; link.download = `${type}_${event.value.name.replace(/\s+/g, '_')}.xlsx`; link.click()
    URL.revokeObjectURL(url)
  } catch (error) { scanMessage.value = { type: 'error', title: 'Error', text: error.message } }
}

// Seating functions
async function loadTables() {
  if (!event.value) return
  tables.value = await api(`/events/${event.value.id}/tables`)
}
async function addTable() {
  if (!tableForm.value.table_number) return
  await api(`/events/${event.value.id}/tables`, { method: 'POST', body: JSON.stringify(tableForm.value) })
  tableForm.value = { table_number: '', table_label: '', capacity: 10, zone: '' }; showTableForm.value = false; await loadTables()
}
async function bulkCreateTables() {
  if (!bulkForm.value.prefix || !bulkForm.value.count) return
  await api(`/events/${event.value.id}/tables/bulk`, { method: 'POST', body: JSON.stringify(bulkForm.value) })
  bulkForm.value = { prefix: 'A', count: 10, capacity: 10, zone: '' }; showBulkForm.value = false; await loadTables()
}
async function deleteTable(tid) {
  if (!confirm('Hapus meja ini?')) return
  await api(`/events/${event.value.id}/tables/${tid}`, { method: 'DELETE' })
  if (expandedTable.value === tid) expandedTable.value = null
  await loadTables()
}
function toggleExpandTable(tid) { expandedTable.value = expandedTable.value === tid ? null : tid }
function seatedParticipants(tid) { return participants.value.filter(p => p.table_id === tid) }

// Load tables when switching to seating view
watch(activeView, async (v) => { if (v === 'seating') { await loadTables(); await refreshEventData() } })

// Close export dropdown on click outside
function closeExportDropdown(e) { if (showExportDropdown.value && !e.target.closest('.export-wrap')) showExportDropdown.value = false }
onMounted(() => { document.addEventListener('click', closeExportDropdown) })
onUnmounted(() => { document.removeEventListener('click', closeExportDropdown) })

const checkedIn = computed(() => dashboard.value?.summary?.checked_in || 0)
const total = computed(() => dashboard.value?.summary?.total || 0)
const lastCheckins = computed(() => dashboard.value?.recent || [])
onMounted(() => { if (token.value) loadData() })
</script>

<template>
  <div v-if="!token" class="login-page">
    <div class="login-art"><div class="art-orbit orbit-one"></div><div class="art-orbit orbit-two"></div><div class="art-content"><div class="brand large"><span class="brand-mark"><QrCode :size="21" /></span>gatherly<span class="brand-dot">.</span></div><p class="art-kicker">EVENT OPERATIONS, REIMAGINED</p><h1>Make every arrival<br /><em>feel effortless.</em></h1><p class="art-description">A calm, intelligent command center for your most important gatherings.</p><div class="art-stat"><ShieldCheck :size="18" /><span>Trusted attendance records<br /><b>Secure by design</b></span></div></div></div>
    <div class="login-panel"><div class="login-inner"><div class="mobile-logo brand">gatherly<span class="brand-dot">.</span></div><p class="eyebrow">Welcome back</p><h2>Sign in to your workspace</h2><p class="login-subtitle">Manage your event, vendors, and attendance in one place.</p><form @submit.prevent="login"><label>Email address<input v-model="loginForm.email" type="email" placeholder="you@company.com" /></label><label>Password<div class="password-input"><input v-model="loginForm.password" type="password" placeholder="Your password" /><ShieldCheck :size="16" /></div></label><div v-if="loginError" class="form-error"><CircleAlert :size="15" />{{ loginError }}</div><button class="primary-button full" :disabled="loading">{{ loading ? 'Signing in...' : 'Continue to workspace' }} <span>→</span></button></form><p class="login-hint">Development access: <b>admin@example.com</b> / <b>admin123</b></p></div><span class="copyright">© 2026 Gatherly. Built for better events.</span></div>
  </div>

  <div v-else class="app-shell">
    <aside class="sidebar"><div class="brand"><span class="brand-mark"><QrCode :size="20" /></span>gatherly<span class="brand-dot">.</span></div><p class="eyebrow">Workspace</p><nav><button :class="['nav-item', { active: activeView === 'overview' }]" @click="activeView = 'overview'"><LayoutDashboard :size="18" />Overview</button><button :class="['nav-item', { active: activeView === 'scanner' }]" @click="focusScanner"><QrCode :size="18" />Scan attendance<span class="nav-badge">LIVE</span></button><button :class="['nav-item', { active: activeView === 'participants' }]" @click="activeView = 'participants'"><Users :size="18" />Participants</button><button :class="['nav-item', { active: activeView === 'seating' }]" @click="activeView = 'seating'"><Grid3x3 :size="18" />Seating</button><button :class="['nav-item', { active: activeView === 'vendors' }]" @click="activeView = 'vendors'"><UserRound :size="18" />Vendors</button><button class="nav-item" @click="refreshEventData"><Settings :size="18" />Refresh data</button></nav><div v-if="event" class="sidebar-event"><div class="event-icon"><CalendarDays :size="18" /></div><div><small>Current event</small><strong>{{ event.name }}</strong><span>{{ event.event_date }} · {{ event.location }}</span></div></div><div class="user-card"><div class="avatar">{{ user?.name?.slice(0, 2).toUpperCase() }}</div><div><strong>{{ user?.name }}</strong><span>{{ user?.role }}</span></div><button @click="logout" title="Sign out"><LogOut :size="15" /></button></div></aside>
    <main class="main-content"><header class="topbar"><div class="mobile-brand brand">gatherly<span class="brand-dot">.</span></div><div class="top-actions"><span class="live-indicator"><i></i> System online</span><button class="icon-button"><Bell :size="19" /></button><div class="top-avatar">{{ user?.name?.slice(0, 2).toUpperCase() }}</div></div></header>
      <section class="content"><div class="heading-row"><div><p class="eyebrow">{{ event?.event_date }} · Event command center</p><h1>{{ activeView === 'overview' ? `Good morning, ${user?.name?.split(' ')[0]}` : activeView === 'scanner' ? 'Attendance scanner' : activeView === 'participants' ? 'Participants' : activeView === 'seating' ? 'Seating' : 'Vendor directory' }}<span class="wave">✦</span></h1><p class="subtitle">{{ activeView === 'overview' ? 'Here is what is happening at your event today.' : 'Everything you need to keep the room moving.' }}</p></div><button class="primary-button" @click="focusScanner"><QrCode :size="18" /> Open scanner</button></div>

        <template v-if="activeView === 'overview'">
          <div class="event-banner"><div class="banner-copy"><span class="live-pill"><span></span> {{ event?.status || 'Live' }} event</span><h2>{{ event?.name }}</h2><p>{{ event?.location }} <span>•</span> {{ event?.start_time }} – {{ event?.end_time }} WIB</p></div><div class="banner-date"><strong>{{ event?.event_date?.slice(8, 10) }}</strong><span>{{ event?.event_date?.slice(5, 7) }}</span></div></div>
          <div class="stats-grid"><article class="stat-card"><div class="stat-icon blue-icon"><Users :size="19" /></div><span>Total invitees</span><strong>{{ total }}</strong><small>Across {{ vendors.length }} companies</small></article><article class="stat-card"><div class="stat-icon green-icon"><CircleCheck :size="19" /></div><span>Checked in</span><strong>{{ checkedIn }}</strong><small class="positive">{{ dashboard?.summary?.rate || 0 }}% <em>attendance rate</em></small></article><article class="stat-card"><div class="stat-icon orange-icon"><QrCode :size="19" /></div><span>Remaining</span><strong>{{ dashboard?.summary?.remaining || 0 }}</strong><small>Ready for arrival</small></article><article class="stat-card accent-card"><span>System status</span><strong class="online-text">Live</strong><small>Updates on refresh</small><div class="progress"><span :style="{ width: `${dashboard?.summary?.rate || 0}%` }"></span></div></article></div>
          <div class="section-grid"><section class="panel chart-panel"><div class="panel-heading"><div><h3>Attendance progress</h3><p>Live snapshot of event arrivals</p></div><button class="select-button" @click="refreshEventData"><RefreshCw :size="13" /> Refresh</button></div><div class="big-progress"><div class="ring"><strong>{{ dashboard?.summary?.rate || 0 }}<small>%</small></strong><span>attended</span></div><div class="progress-copy"><strong>{{ checkedIn }} of {{ total }}</strong><span>participants have checked in</span><div class="bar large"><i :style="{ width: `${dashboard?.summary?.rate || 0}%` }"></i></div><small>Keep the welcome desk moving.</small></div></div></section><section class="panel progress-panel"><div class="panel-heading"><div><h3>Vendor attendance</h3><p>Participation by company</p></div><button class="text-button" @click="activeView = 'vendors'">View all</button></div><div v-for="vendor in (dashboard?.vendors || []).slice(0, 5)" :key="vendor.id" class="vendor-row"><div class="vendor-meta"><span>{{ String(vendor.id).padStart(2, '0') }}</span><strong>{{ vendor.company_name }}</strong><b>{{ vendor.checked_in }} / {{ vendor.total }}</b></div><div class="bar"><i :style="{ width: `${vendor.rate}%` }"></i></div></div></section></div>
          <section class="panel activity-panel"><div class="panel-heading"><div><h3>Latest check-ins</h3><p>Real-time attendance activity</p></div><button class="text-button" @click="focusScanner">Scan next <span>→</span></button></div><div v-if="lastCheckins.length" class="table-wrap"><table><thead><tr><th>Attendee</th><th>Company</th><th>Check-in time</th><th>Status</th></tr></thead><tbody><tr v-for="person in lastCheckins" :key="person.id"><td><div class="person"><span class="person-avatar coral">{{ person.name.slice(0, 2).toUpperCase() }}</span><strong>{{ person.name }}</strong></div></td><td>{{ person.company_name }}</td><td>{{ new Date(person.check_in_at).toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' }) }} WIB</td><td><span class="status"><i></i>Checked in</span></td></tr></tbody></table></div><div v-else class="empty-state"><Sparkles :size="24" /><strong>No check-ins yet</strong><span>Scanned participants will appear here.</span></div></section>
        </template>

        <template v-else-if="activeView === 'scanner'"><section class="scanner-layout"><div class="panel scanner-panel"><div class="scanner-head"><div><span class="live-pill dark"><span></span> Scanner ready</span><h2>Scan a participant QR</h2><p>Point the camera at a QR Code or enter its token below.</p></div><div class="scanner-icon"><QrCode :size="35" /></div></div><div class="camera-container"><video ref="videoEl" class="camera-video" playsinline muted></video><div v-if="!cameraActive" class="camera-placeholder" @click="toggleCamera"><div class="scan-corners"></div><Camera :size="52" /><span>Tap to activate camera scanner</span><small>Or use the token field below</small></div></div><div class="camera-controls"><button :class="['camera-toggle', { active: cameraActive }]" @click="toggleCamera"><Camera v-if="!cameraActive" :size="17" /><CameraOff v-else :size="17" /> {{ cameraActive ? 'Stop camera' : 'Start camera' }}</button></div><div class="scan-form"><label id="scan-input">QR token<input v-model="scanToken" @keyup.enter="checkIn('qr')" placeholder="Paste or type participant token" autofocus /></label><button class="primary-button" @click="checkIn('qr')" :disabled="!scanToken.trim()"><Check :size="17" /> Confirm check-in</button></div><div v-if="scanMessage" :class="['scan-result', scanMessage.type]"><CircleCheck v-if="scanMessage.type === 'success'" :size="22" /><CircleAlert v-else :size="22" /><div><strong>{{ scanMessage.title }}</strong><span>{{ scanMessage.text }}</span></div><button @click="scanMessage = null"><X :size="16" /></button></div></div><div class="panel quick-panel"><h3>Quick manual check-in</h3><p>Use this fallback when a guest cannot show their QR Code.</p><div class="search-field"><Search :size="16" /><input v-model="search" @input="refreshSearch" placeholder="Find a participant" /></div><div class="quick-list"><div v-for="person in participants.slice(0, 5)" :key="person.id" class="quick-person"><div class="person"><span class="person-avatar blue">{{ person.name.slice(0, 2).toUpperCase() }}</span><div><strong>{{ person.name }}</strong><span>{{ person.company_name }}</span></div></div><button v-if="person.attendance_status !== 'checked_in'" class="tiny-button" @click="checkIn('manual', person.id)">Check in</button><span v-else class="status"><i></i>Done</span></div></div></div></section></template>

        <template v-else-if="activeView === 'participants'"><section class="panel activity-panel"><div class="panel-heading"><div><h3>All participants</h3><p>{{ participants.length }} records in this event</p></div><div class="panel-actions"><label class="select-button import-btn"><Upload :size="15" /> Import Excel<input type="file" accept=".xlsx,.xls" @change="handleImportFile" hidden /></label><div class="export-wrap" style="position:relative"><button class="select-button" @click.stop="showExportDropdown = !showExportDropdown"><FileSpreadsheet :size="15" /> Export <ChevronDown :size="13" /></button><div v-if="showExportDropdown" class="dropdown-menu"><button @click="exportFile('participants')">Peserta</button><button @click="exportFile('attendance')">Kehadiran</button><button @click="exportFile('vendors')">Vendor</button><button @click="exportFile('seating')">Seating</button><button @click="exportFile('audit')">Audit Log</button><button @click="downloadTemplate">Template Import</button></div></div><button class="select-button" @click="downloadAllQr"><Download :size="15" /> Download all QR</button><button class="primary-button small" @click="loadTables().then(() => showParticipantForm = true)"><Plus :size="16" /> Add participant</button></div></div><div class="toolbar"><div class="search-field"><Search :size="16" /><input v-model="search" @input="refreshSearch" placeholder="Search name, phone, or email..." /></div><button class="select-button" @click="refreshEventData"><RefreshCw :size="13" /> Refresh</button></div><div class="table-wrap"><table><thead><tr><th>Participant</th><th>Company</th><th>Contact</th><th>Table / Seat</th><th>QR Code</th><th>Status</th><th>Action</th></tr></thead><tbody><tr v-for="person in participants" :key="person.id"><td><div class="person"><span class="person-avatar coral">{{ person.name.slice(0, 2).toUpperCase() }}</span><strong>{{ person.name }}</strong></div></td><td>{{ person.company_name }}</td><td>{{ person.phone || person.email || '—' }}</td><td>{{ person.table_number ? `Meja ${person.table_number}${person.seat_number ? ' / ' + person.seat_number : ''}` : '—' }}</td><td><button class="qr-button" @click="showQr(person)" title="Lihat QR Code"><Eye :size="14" /> <span>QR</span></button></td><td><span :class="['status', person.attendance_status === 'checked_in' ? '' : 'pending']"><i></i>{{ person.attendance_status === 'checked_in' ? 'Checked in' : 'Not arrived' }}</span></td><td><div class="action-buttons"><button v-if="person.attendance_status !== 'checked_in'" class="tiny-button" @click="checkIn('manual', person.id)">Check in</button><button v-if="person.attendance_status === 'checked_in'" class="icon-btn undo" @click="confirmUndo(person)" title="Undo check-in"><Undo2 :size="14" /></button><span v-if="person.attendance_status === 'checked_in' && !showUndoConfirm" class="muted">{{ new Date(person.check_in_at).toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' }) }}</span><button class="icon-btn edit" @click="openEditForm(person)" title="Edit"><Pencil :size="14" /></button><button class="icon-btn delete" @click="confirmDelete(person)" title="Hapus"><Trash2 :size="14" /></button></div></td></tr></tbody></table></div></section></template>

        <template v-else-if="activeView === 'seating'"><section class="panel activity-panel"><div class="panel-heading"><div><h3>Table management</h3><p>{{ tables.length }} tables configured</p></div><div class="panel-actions"><button class="select-button" @click="showBulkForm = true"><Plus :size="15" /> Bulk create</button><button class="primary-button small" @click="showTableForm = true"><Plus :size="16" /> Add table</button></div></div><div class="seating-grid"><article v-for="tbl in tables" :key="tbl.id" class="panel table-card" @click="toggleExpandTable(tbl.id)"><div class="table-card-head"><div><strong>{{ tbl.table_label || tbl.table_number }}</strong><span v-if="tbl.zone" class="zone-badge">{{ tbl.zone }}</span></div><button class="icon-btn delete" @click.stop="deleteTable(tbl.id)" title="Hapus meja"><Trash2 :size="14" /></button></div><div class="table-card-stats"><span>{{ tbl.seated }} / {{ tbl.capacity }}</span><small>terisi</small></div><div class="bar"><i :style="{ width: `${tbl.capacity ? (tbl.seated / tbl.capacity) * 100 : 0}%` }"></i></div><div v-if="expandedTable === tbl.id" class="table-expanded" @click.stop><div v-if="seatedParticipants(tbl.id).length" class="seated-list"><div v-for="p in seatedParticipants(tbl.id)" :key="p.id" class="seated-person"><span class="person-avatar coral">{{ p.name.slice(0, 2).toUpperCase() }}</span><div><strong>{{ p.name }}</strong><small>Kursi {{ p.seat_number || '—' }} · {{ p.company_name }}</small></div></div></div><div v-else class="empty-state small"><span>Belum ada peserta di meja ini.</span></div></div></article></div></section></template>

        <template v-else><section class="vendor-cards"><article v-for="vendor in vendors" :key="vendor.id" class="panel vendor-card"><div class="vendor-avatar"><Users :size="19" /></div><h3>{{ vendor.company_name }}</h3><span>{{ vendor.category }}</span><div class="vendor-count"><strong>{{ vendor.participant_count }}</strong><small>participants</small></div><div class="bar"><i :style="{ width: `${dashboard?.vendors?.find(v => v.id === vendor.id)?.rate || 0}%` }"></i></div></article></section></template>
      </section>
    </main>
    <div v-if="showParticipantForm" class="modal-backdrop" @click.self="showParticipantForm = false"><form class="modal" @submit.prevent="addParticipant"><button type="button" class="modal-close" @click="showParticipantForm = false"><X :size="18" /></button><p class="eyebrow">New registration</p><h2>Add participant</h2><p class="subtitle">Create a QR token automatically for this guest.</p><label>Full name<input v-model="participantForm.name" required placeholder="e.g. Raka Pratama" /></label><label>Company<select v-model="participantForm.vendor_id"><option :value="null">Select company</option><option v-for="vendor in vendors" :key="vendor.id" :value="vendor.id">{{ vendor.company_name }}</option></select></label><label>Position<input v-model="participantForm.position" placeholder="Vendor representative" /></label><label>Phone<input v-model="participantForm.phone" placeholder="08xx" /></label><label>Email<input v-model="participantForm.email" type="email" placeholder="email@company.com" /></label><label>Table<select v-model="participantForm.table_id"><option :value="null">No table assigned</option><option v-for="tbl in tables" :key="tbl.id" :value="tbl.id">{{ tbl.table_label || tbl.table_number }} ({{ tbl.zone || 'No zone' }})</option></select></label><label>Seat number<input v-model.number="participantForm.seat_number" type="number" min="1" placeholder="e.g. 3" /></label><button class="primary-button full" type="submit"><Plus :size="17" /> Create participant</button></form></div>
    <div v-if="showQrModal" class="modal-backdrop" @click.self="closeQrModal"><div class="modal qr-modal"><button type="button" class="modal-close" @click="closeQrModal"><X :size="18" /></button><p class="eyebrow">QR Code</p><h2>{{ qrParticipant?.name }}</h2><p class="subtitle">{{ qrParticipant?.company_name }} &bull; Token: <code>{{ qrParticipant?.qr_token?.slice(0, 12) }}...</code></p><div class="qr-preview"><div v-if="qrLoading" class="qr-loading"><RefreshCw :size="28" class="spin" /><span>Generating QR Code...</span></div><img v-else-if="qrImageUrl" :src="qrImageUrl" :alt="`QR Code ${qrParticipant?.name}`" /></div><div class="qr-actions"><button class="primary-button" @click="downloadQr"><Download :size="17" /> Download PNG</button><button class="select-button" @click="closeQrModal">Tutup</button></div></div></div>
    <div v-if="showEditForm" class="modal-backdrop" @click.self="showEditForm = false"><form class="modal" @submit.prevent="saveEdit"><button type="button" class="modal-close" @click="showEditForm = false"><X :size="18" /></button><p class="eyebrow">Edit data</p><h2>Edit participant</h2><p class="subtitle">Update participant information.</p><label>Full name<input v-model="editForm.name" required placeholder="Full name" /></label><label>Company<select v-model="editForm.vendor_id"><option :value="null">Select company</option><option v-for="vendor in vendors" :key="vendor.id" :value="vendor.id">{{ vendor.company_name }}</option></select></label><label>Table<select v-model="editForm.table_id"><option :value="null">No table assigned</option><option v-for="tbl in tables" :key="tbl.id" :value="tbl.id">{{ tbl.table_label || tbl.table_number }} ({{ tbl.zone || 'No zone' }})</option></select></label><label>Seat number<input v-model.number="editForm.seat_number" type="number" min="1" placeholder="e.g. 3" /></label><label>Position<input v-model="editForm.position" placeholder="Position" /></label><label>Phone<input v-model="editForm.phone" placeholder="08xx" /></label><label>Email<input v-model="editForm.email" type="email" placeholder="email@company.com" /></label><button class="primary-button full" type="submit"><Check :size="17" /> Save changes</button></form></div>
    <div v-if="showDeleteConfirm" class="modal-backdrop" @click.self="showDeleteConfirm = false"><div class="modal modal-sm"><button type="button" class="modal-close" @click="showDeleteConfirm = false"><X :size="18" /></button><p class="eyebrow">Konfirmasi</p><h2>Hapus peserta?</h2><p class="subtitle">{{ deleteTarget?.name }} akan dihapus secara permanen dari event ini.</p><div class="qr-actions"><button class="primary-button danger" @click="doDelete"><Trash2 :size="17" /> Hapus</button><button class="select-button" @click="showDeleteConfirm = false">Batal</button></div></div></div>
    <div v-if="showUndoConfirm" class="modal-backdrop" @click.self="showUndoConfirm = false"><div class="modal modal-sm"><button type="button" class="modal-close" @click="showUndoConfirm = false"><X :size="18" /></button><p class="eyebrow">Konfirmasi</p><h2>Undo check-in?</h2><p class="subtitle">Status kehadiran {{ undoTarget?.name }} akan dikembalikan ke belum hadir.</p><div class="qr-actions"><button class="primary-button" @click="doUndo"><Undo2 :size="17" /> Undo check-in</button><button class="select-button" @click="showUndoConfirm = false">Batal</button></div></div></div>
    <div v-if="showImportPreview" class="modal-backdrop" @click.self="showImportPreview = false"><div class="modal modal-lg"><button type="button" class="modal-close" @click="showImportPreview = false"><X :size="18" /></button><p class="eyebrow">Import preview</p><h2>Preview data import</h2><p class="subtitle">{{ importPreview?.total_rows }} baris ditemukan · {{ importPreview?.errors?.length || 0 }} error · {{ importPreview?.new_vendors?.length || 0 }} vendor baru · {{ importPreview?.new_tables?.length || 0 }} meja baru</p><div v-if="importPreview?.errors?.length" class="import-errors"><div v-for="(err, i) in importPreview.errors" :key="i" class="scan-result error"><CircleAlert :size="16" /><span>{{ err }}</span></div></div><div class="table-wrap" style="max-height:300px;overflow-y:auto"><table><thead><tr><th>Nama</th><th>Company</th><th>Phone</th><th>Email</th><th>Table</th><th>Seat</th></tr></thead><tbody><tr v-for="(row, i) in (importPreview?.rows || []).slice(0, 50)" :key="i"><td>{{ row.name }}</td><td>{{ row.company_name || row.vendor_name || '—' }}</td><td>{{ row.phone || '—' }}</td><td>{{ row.email || '—' }}</td><td>{{ row.table_number || '—' }}</td><td>{{ row.seat_number || '—' }}</td></tr></tbody></table></div><div class="import-actions"><label>Duplikat:<select v-model="importDuplicateAction"><option value="skip">Lewati</option><option value="update">Perbarui</option></select></label><div class="qr-actions"><button class="primary-button" @click="confirmImport" :disabled="importLoading"><Check :size="17" /> {{ importLoading ? 'Importing...' : 'Confirm import' }}</button><button class="select-button" @click="showImportPreview = false">Batal</button></div></div></div></div>
    <div v-if="showTableForm" class="modal-backdrop" @click.self="showTableForm = false"><form class="modal" @submit.prevent="addTable"><button type="button" class="modal-close" @click="showTableForm = false"><X :size="18" /></button><p class="eyebrow">New table</p><h2>Add table</h2><p class="subtitle">Add a single table to the seating plan.</p><label>Table number<input v-model="tableForm.table_number" required placeholder="e.g. A1" /></label><label>Label (optional)<input v-model="tableForm.table_label" placeholder="e.g. VIP Table 1" /></label><label>Capacity<input v-model.number="tableForm.capacity" type="number" min="1" required /></label><label>Zone (optional)<input v-model="tableForm.zone" placeholder="e.g. VIP, Regular" /></label><button class="primary-button full" type="submit"><Plus :size="17" /> Create table</button></form></div>
    <div v-if="showBulkForm" class="modal-backdrop" @click.self="showBulkForm = false"><form class="modal" @submit.prevent="bulkCreateTables"><button type="button" class="modal-close" @click="showBulkForm = false"><X :size="18" /></button><p class="eyebrow">Bulk create</p><h2>Bulk create tables</h2><p class="subtitle">Generate multiple tables with a prefix and numbering.</p><label>Prefix<input v-model="bulkForm.prefix" required placeholder="e.g. A" /></label><label>Count<input v-model.number="bulkForm.count" type="number" min="1" required /></label><label>Capacity per table<input v-model.number="bulkForm.capacity" type="number" min="1" required /></label><label>Zone (optional)<input v-model="bulkForm.zone" placeholder="e.g. VIP, Regular" /></label><button class="primary-button full" type="submit"><Plus :size="17" /> Create {{ bulkForm.count }} tables</button></form></div>
  </div>
</template>

<style scoped>
.action-buttons{display:flex;align-items:center;gap:6px;flex-wrap:wrap}
.icon-btn{background:transparent;border:1px solid #d7dfe6;border-radius:7px;padding:5px 7px;display:inline-flex;align-items:center;color:#546e7a;transition:all .15s}
.icon-btn:hover{background:#f0f4f8}
.icon-btn.edit:hover{color:#1976d2;border-color:#1976d2}
.icon-btn.delete:hover{color:#d32f2f;border-color:#d32f2f}
.icon-btn.undo:hover{color:#e86b4f;border-color:#e86b4f}
.import-btn{cursor:pointer}
.export-wrap{position:relative;display:inline-block}
.dropdown-menu{position:absolute;top:100%;right:0;margin-top:5px;background:#fff;border:1px solid #d7dfe6;border-radius:9px;box-shadow:0 8px 24px rgba(0,0,0,.1);z-index:100;min-width:170px;padding:5px 0;display:flex;flex-direction:column}
.dropdown-menu button{background:transparent;border:0;padding:9px 16px;text-align:left;font-size:13px;color:#172a3a;transition:background .15s}
.dropdown-menu button:hover{background:#f0f4f8}
.seating-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:16px;margin-top:18px}
.table-card{cursor:pointer;transition:box-shadow .2s;padding:18px}
.table-card:hover{box-shadow:0 4px 16px rgba(0,0,0,.08)}
.table-card-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:10px}
.table-card-head strong{font-size:16px}
.zone-badge{font-size:10px;background:#e3f2fd;color:#1565c0;padding:2px 8px;border-radius:20px;margin-left:8px;font-weight:600}
.table-card-stats{display:flex;align-items:baseline;gap:6px;margin-bottom:8px}
.table-card-stats span{font-size:20px;font-weight:700;color:#172a3a}
.table-card-stats small{color:#8da5b9;font-size:12px}
.table-expanded{margin-top:14px;border-top:1px solid #e8edf2;padding-top:12px}
.seated-list{display:flex;flex-direction:column;gap:8px}
.seated-person{display:flex;align-items:center;gap:10px}
.seated-person div{display:flex;flex-direction:column}
.seated-person strong{font-size:12px}
.seated-person small{color:#8da5b9;font-size:10px}
.empty-state.small{padding:10px 0}
.empty-state.small span{font-size:12px;color:#8da5b9}
.modal-sm{max-width:400px;text-align:center}
.modal-lg{max-width:700px}
.primary-button.danger{background:#d32f2f}
.primary-button.danger:hover{background:#b71c1c}
.import-errors{margin-bottom:14px;display:flex;flex-direction:column;gap:6px}
.import-errors .scan-result{padding:8px 12px;font-size:12px}
.import-actions{display:flex;align-items:center;justify-content:space-between;margin-top:16px;gap:12px;flex-wrap:wrap}
.import-actions label{display:flex;align-items:center;gap:8px;font-size:13px;font-weight:500}
.import-actions select{padding:6px 10px;border:1px solid #d7dfe6;border-radius:7px;font-size:13px}
</style>
